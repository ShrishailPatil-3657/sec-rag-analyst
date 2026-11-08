"""Run a question set through the pipeline and save one line per question.

usage: uv run python scripts/run_eval.py quick [--no-llm]
--no-llm scores retrieval only (fast); without it each question also gets a local-model answer.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from sec_rag_analyst.generation import MODEL, ask_ollama, build_prompt
from sec_rag_analyst.metrics import gold_pages, retrieval_scores, summarize
from sec_rag_analyst.prep import CHUNK_SIZE, OVERLAP
from sec_rag_analyst.retrieval import MODEL_NAME, load_index, search

TOP_K = 5
split_name = sys.argv[1]
use_llm = "--no-llm" not in sys.argv

split = json.loads(Path("data/eval/split.json").read_text())
rows = Path("data/financebench/data/financebench_open_source.jsonl").read_text().splitlines()
questions = {q["financebench_id"]: q for q in map(json.loads, rows)}

run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{split_name}"
out_path = Path("data/processed/runs") / f"{run_id}.jsonl"
out_path.parent.mkdir(parents=True, exist_ok=True)

config = {
    "run_id": run_id,
    "split": split_name,
    "top_k": TOP_K,
    "chunk_size": CHUNK_SIZE,
    "overlap": OVERLAP,
    "embedding_model": MODEL_NAME,
    "generation_model": MODEL if use_llm else None,
    "git_commit": subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip(),
}

all_scores = []
with out_path.open("w") as f:
    f.write(json.dumps({"config": config}) + "\n")
    for qid in split[split_name]:
        q = questions[qid]
        chunks, vectors = load_index(q["doc_name"])
        hits = search(q["question"], chunks, vectors, top_k=TOP_K)
        scores = retrieval_scores(gold_pages(q), [h["page_index"] for h in hits], k=TOP_K)
        all_scores.append(scores)
        answer = ask_ollama(build_prompt(q["question"], hits)) if use_llm else None
        f.write(
            json.dumps(
                {
                    "id": qid,
                    "doc_name": q["doc_name"],
                    "question": q["question"],
                    "gold_answer": q["answer"],
                    "gold_pages": sorted(gold_pages(q)),
                    "retrieved_pages": [h["page_index"] for h in hits],
                    "scores": scores,
                    "answer": answer,
                }
            )
            + "\n"
        )

print(f"saved to {out_path}")
print(summarize(all_scores))
