"""LLM judge: grade one answer for correctness, and for whether the retrieved pages support it."""
import json
import re
import urllib.request

from sec_rag_analyst.generation import MODEL, OLLAMA_URL

VERDICTS = ("correct", "incorrect", "not_found")

# These rules come from hand grading 12 answers (see docs/judge-rules-draft.md).
RULES = """You are grading an answer from a question-answering system over SEC filings.
You get the question, the gold (reference) answer, the model's answer, and the excerpts the model was given.
Decide two things.

1. verdict, one of:
- "correct": the model answer gives the same final answer as the gold answer.
  * Numbers match if they are within 1% of the gold number, or equal after rounding to the gold answer's precision.
  * Units must agree: $1.6 billion is 1,600 million; figures "in thousands" differ from "in millions".
  * Numbers in brackets, like (1,577), are negative.
  * The answer must state the final quantity the question asks for. Giving only the parts (for example two
    credit facilities without their total) is NOT correct.
  * Extra explanation is fine. If the gold answer is a yes/no, the model must give the same yes/no.
- "not_found": the model says the answer is not found or not in the excerpts, and gives no answer. This is
  always "not_found", even when the gold answer is 0 or "none": saying "not found" is not the same as answering 0.
- "incorrect": anything else, including a confident but wrong answer.

2. supported (true or false): can the GOLD answer be derived from the excerpts alone?
  * First copy into "evidence" the exact text from the excerpts that shows the gold answer (or the numbers
    needed to compute it). If the excerpts do not contain it, write "none".
  * supported is true only if that evidence is really written in the excerpts. Facts that are merely related
    to the question do not count, and you must not assume facts that are not written there.
  * It does not matter whether the model's own answer is right. A model answer that happens to match the gold
    answer is not supported unless the excerpts show it. A yes/no answer needs evidence in the excerpts.
  * For "largest/highest/biggest" questions, the excerpts must show all the candidates.

Reply with JSON only, in this form:
{"verdict": "correct" | "incorrect" | "not_found", "evidence": "exact quote or none", "supported": true | false, "reason": "one short sentence"}"""


def build_judge_prompt(question: str, gold_answer: str, answer: str, chunks: list[dict]) -> str:
    """Rules, then the question, gold answer, model answer, and the excerpts the model saw."""
    excerpts = "\n\n".join(f"[page {c['page_number']}]\n{' '.join(c['text'].split())}" for c in chunks)
    return (
        f"{RULES}\n\nQuestion: {question}\n\nGold answer: {gold_answer}\n\nModel answer: {answer}\n\n"
        f"Excerpts the model was given:\n\n{excerpts}\n\nJSON:"
    )


def parse_judgement(text: str) -> dict:
    """Turn the judge's reply into {"verdict", "supported", "reason"}. Anything unreadable becomes verdict 'error'."""
    try:
        data = json.loads(text)
        verdict = data["verdict"]
        supported = data["supported"]
        if isinstance(supported, str):
            supported = supported.strip().lower() in ("true", "yes")
        if verdict not in VERDICTS or not isinstance(supported, bool):
            raise ValueError("unexpected values")
        return {"verdict": verdict, "supported": supported, "reason": str(data.get("reason", "")), "evidence": str(data.get("evidence", ""))}
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return {"verdict": "error", "supported": None, "reason": text[:200]}


def ask_judge(prompt: str, model: str = MODEL) -> dict:
    """Send the prompt to the local Ollama server and parse the JSON reply."""
    body = json.dumps(
        {
            "model": model,
            "stream": False,
            "think": False,
            "format": "json",  # ask Ollama to return valid JSON
            "options": {"temperature": 0},
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    request = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        text = json.load(response)["message"]["content"].strip()
    return parse_judgement(text)


NOT_FOUND = re.compile(r"\bnot found\b", re.IGNORECASE)
# Abstentions in other words. These are only looked for in the last two sentences, where the model states its conclusion.
ABSTAIN_PHRASES = re.compile(
    r"\bthe (answer|information|figure|value) (is|was) not found\b"
    r"|\bnot possible to (determine|assess|calculate|answer|tell)\b"
    r"|\b(cannot|can't|can not) be (determined|calculated|answered|assessed)\b"
    r"|\bunable to (determine|calculate|answer|find)\b",
    re.IGNORECASE,
)
PAGE_TAIL = re.compile(r"\s*\(\s*page[^)]*\)\s*\.?\s*$", re.IGNORECASE)


def is_not_found(answer: str) -> bool:
    """True if the model abstained. The generation prompt tells it to reply "not found", so a short answer
    containing those words counts. Longer answers often abstain in their own words after starting to explain
    ("Therefore, it is not possible to determine..."), so their last two sentences are checked for such phrases.
    Only the end is checked, so an answer that merely mentions a missing detail in the middle is not an abstention."""
    if len(answer) < 200 and NOT_FOUND.search(answer):
        return True
    sentences = re.split(r"(?<=[.!?])\s+", PAGE_TAIL.sub("", answer.strip()))
    return bool(ABSTAIN_PHRASES.search(" ".join(sentences[-2:])))


def judge_answer(question: str, gold_answer: str, answer: str, chunks: list[dict]) -> dict:
    """Judge one answer. The LLM decides 'supported' (and the verdict); code decides 'not_found'."""
    result = ask_judge(build_judge_prompt(question, gold_answer, answer, chunks))
    if is_not_found(answer):
        result["verdict"] = "not_found"
    return result
