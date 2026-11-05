"""Build the prompt from retrieved chunks and ask a local model (Ollama) to answer."""
import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:8b"

RULES = (
    "You are a financial analyst assistant. Answer the question using only the excerpts below, "
    "which come from one SEC filing. Amounts are in millions of US dollars unless the text says otherwise. "
    "Numbers in brackets, like (1,577), are negative. "
    "If the excerpts do not contain the answer, reply exactly: not found. "
    "Keep the answer short and end it with the page number(s) you used, like (page 60)."
)


def build_prompt(question: str, hits: list[dict]) -> str:
    """Rules, then each excerpt labelled with its page, then the question."""
    excerpts = []
    for hit in hits:
        text = " ".join(hit["text"].split())  # the PDF text is full of blank lines; squeeze them
        excerpts.append(f"[page {hit['page_number']}]\n{text}")
    return f"{RULES}\n\nExcerpts:\n\n" + "\n\n".join(excerpts) + f"\n\nQuestion: {question}"


def ask_ollama(prompt: str, model: str = MODEL) -> str:
    """Send the prompt to the local Ollama server and return the reply text."""
    body = json.dumps(
        {
            "model": model,
            "stream": False,
            "think": False,  # skip Qwen3's long reasoning so answers stay short
            "options": {"temperature": 0},  # same question, same answer
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    request = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["message"]["content"].strip()
