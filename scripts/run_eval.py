"""Run a question set through the pipeline and save one line per question.

usage: uv run python scripts/run_eval.py quick [--no-llm] [--resume RUN_FILE]
--no-llm scores retrieval only (fast); without it each question also gets a local-model answer.
--resume continues an interrupted run: questions already in RUN_FILE are skipped, new rows are appended.
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
resume_path = Path(sys.argv[sys.argv.index("--resume") + 1]) if "--resume" in sys.argv else None

split = json.loads(Path("data/eval/split.json").read_text())
rows = Path("data/financebench/data/financebench_open_source.jsonl").read_text().splitlines()
questions = {q["financebench_id"]: q for q in map(json.loads, rows)}

if resume_path:
    out_path = resume_path
    done_rows = [json.loads(line) for line in out_path.read_text().splitlines()[1:]]
    done_ids = {r["id"] for r in done_rows}
    all_scores = [r["scores"] for r in done_rows]
    print(f"resuming {out_path.name}: {len(done_ids)} questions already done")
else:
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
        # set on the Ollama server (not here); update this if you start `ollama serve` differently
        "ollama_settings": {"flash_attention": True, "kv_cache_type": "q8_0", "num_ctx": 4096, "keep_alive": "5m"},
        "git_commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
        ).stdout.strip(),
    }
    out_path.write_text(json.dumps({"config": config}) + "\n")
    done_ids, all_scores = set(), []
    print(f"writing to {out_path}  (to resume after Ctrl+C: add --resume {out_path})", flush=True)

todo = [qid for qid in split[split_name] if qid not in done_ids]
with out_path.open("a") as f:  # append, so rows already saved are never lost
    for n, qid in enumerate(todo, start=1):
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
                    "chunks": [{"page_number": h["page_number"], "text": h["text"]} for h in hits],
                    "scores": scores,
                    "answer": answer,
                }
            )
            + "\n"
        )
        f.flush()  # on disk before the next question starts
        print(f"[{n}/{len(todo)}] {qid[-5:]}", flush=True)

print(f"saved to {out_path}")
print(summarize(all_scores))
