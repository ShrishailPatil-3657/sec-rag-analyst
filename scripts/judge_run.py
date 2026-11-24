"""Judge every answer in a run file and print accuracy, abstention and faithfulness rates.

usage: uv run python scripts/judge_run.py RUN_FILE
Writes <RUN_FILE without .jsonl>.judged.jsonl next to it (the original rows plus a "judge" field).
The run file must have been made with the LLM on (answers) and saved chunks (run_eval.py does this).
Resumable: if the .judged.jsonl file already exists, questions already judged there are skipped.
"""
import json
import sys
from collections import Counter
from pathlib import Path

from sec_rag_analyst.judge import judge_answer
from sec_rag_analyst.metrics import summarize

run_file = Path(sys.argv[1])
lines = [json.loads(line) for line in run_file.read_text().splitlines()]
config, rows = lines[0]["config"], lines[1:]
questions = {q["financebench_id"]: q for q in map(json.loads, open("data/financebench/data/financebench_open_source.jsonl"))}

out = run_file.with_suffix("").with_suffix(".judged.jsonl")
judged = []  # rows that already have a verdict
if out.exists():
    judged = [json.loads(line) for line in out.read_text().splitlines()[1:]]
    print(f"resuming {out.name}: {len(judged)} already judged")
else:
    out.write_text(json.dumps({"config": config, "judge_model": "qwen3:8b"}) + "\n")

done_ids = {r["id"] for r in judged}
todo = [r for r in rows if r["id"] not in done_ids]
with out.open("a") as f:  # append, so verdicts already saved are never lost
    for n, row in enumerate(todo, start=1):
        j = judge_answer(questions[row["id"]]["question"], row["gold_answer"], row["answer"], row["chunks"])
        judged.append({**row, "judge": j})
        f.write(json.dumps(judged[-1]) + "\n")
        f.flush()
        print(f"[{n}/{len(todo)}] {row['id'][-5:]}  {j['verdict']:9s} supported={j['supported']}", flush=True)

n = len(judged)
verdicts = Counter(r["judge"]["verdict"] for r in judged)
supported = sum(bool(r["judge"]["supported"]) for r in judged)
print(f"\nrun: {config['run_id']}  ({n} questions, generation model {config['generation_model']})")
print("retrieval:", {k: round(v, 2) for k, v in summarize([r["scores"] for r in judged]).items()})
for v in ("correct", "incorrect", "not_found", "error"):
    if verdicts[v]:
        print(f"{v:10s} {verdicts[v]:3d}  ({verdicts[v] / n:.0%})")
print(f"supported (gold answer derivable from the retrieved pages): {supported}/{n} ({supported / n:.0%})")
print("saved to", out)
