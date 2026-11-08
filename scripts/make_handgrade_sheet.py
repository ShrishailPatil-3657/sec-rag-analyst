"""Build a sheet of 12 quick-set answers for hand grading (4 per question type, judge verdicts hidden).

usage: uv run python scripts/make_handgrade_sheet.py [RUN_FILE]
Writes data/processed/handgrade_sheet.md (to read) and data/eval/hand_grades.csv (to fill in).
"""
import csv
import glob
import json
import os
import random
import sys
from pathlib import Path

from sec_rag_analyst.retrieval import load_index, search

run_file = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/processed/runs/*-quick.jsonl"), key=os.path.getmtime)[-1]
rows = [json.loads(line) for line in open(run_file)][1:]
rows = [r for r in rows if r["answer"]]
questions = {q["financebench_id"]: q for q in map(json.loads, open("data/financebench/data/financebench_open_source.jsonl"))}

by_type = {}
for r in rows:
    by_type.setdefault(questions[r["id"]]["question_type"], []).append(r)

rng = random.Random(7)
chosen = []
for t in sorted(by_type):
    chosen += rng.sample(by_type[t], min(4, len(by_type[t])))
rng.shuffle(chosen)  # mix the types so the order gives no hint

sheet = [f"# Hand-grading sheet ({len(chosen)} answers)\n", f"Source run: {run_file}\n",
         "For each item decide:\n- **correct**: does the model answer match the gold answer? (rounding, units, brackets = negative)\n"
         "- **supported**: do the pages the model was given actually contain the answer?\n"
         "Write y or n in data/eval/hand_grades.csv. Do not look at any judge output first.\n"]
for n, r in enumerate(chosen, start=1):
    q = questions[r["id"]]
    chunks, vectors = load_index(r["doc_name"])
    hits = search(q["question"], chunks, vectors, top_k=5)
    sheet.append(f"\n---\n## {n}. {r['id']}  ({r['doc_name']})\n")
    sheet.append(f"**Question:** {q['question']}\n\n**Gold answer:** {q['answer']}\n\n**Model answer:** {r['answer']}\n")
    sheet.append("\n**Pages the model was given:**\n")
    for h in hits:
        sheet.append(f"\n[page {h['page_number']}]\n```\n{' '.join(h['text'].split())}\n```\n")

Path("data/processed/handgrade_sheet.md").write_text("\n".join(sheet), encoding="utf-8")
out = Path("data/eval/hand_grades.csv")
if out.exists():
    print(f"{out} already exists, not overwritten (your grades may be in it).")
else:
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "correct", "supported", "note"])
        for r in chosen:
            w.writerow([r["id"], "", "", ""])
print(f"wrote data/processed/handgrade_sheet.md with {len(chosen)} items")
