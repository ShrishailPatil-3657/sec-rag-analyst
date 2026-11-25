"""Build a fresh hand-grading sheet from a judged dev run, to test the judge on answers it never saw.

usage: uv run python scripts/make_fresh_sheet.py [JUDGED_FILE]
Picks 4 correct, 4 incorrect and 2 not_found answers (by the judge's verdict), at random with a fixed seed,
skipping the 12 items already in hand_grades.csv. The sheet does NOT show the verdicts.
Writes data/processed/fresh_sheet.md (to read) and data/eval/hand_grades_fresh.csv (to fill in).
"""
import csv
import json
import random
import sys
from pathlib import Path

judged_file = sys.argv[1] if len(sys.argv) > 1 else "data/processed/runs/20261117-125715-dev.judged.jsonl"
rows = [json.loads(line) for line in open(judged_file)][1:]
questions = {q["financebench_id"]: q for q in map(json.loads, open("data/financebench/data/financebench_open_source.jsonl"))}
already_graded = {h["id"] for h in csv.DictReader(open("data/eval/hand_grades.csv"))}
rows = [r for r in rows if r["id"] not in already_graded]

QUOTA = {"correct": 4, "incorrect": 4, "not_found": 2}
rng = random.Random(11)
chosen = []
for verdict, n in QUOTA.items():
    pool = [r for r in rows if r["judge"]["verdict"] == verdict]
    chosen += rng.sample(pool, min(n, len(pool)))
rng.shuffle(chosen)  # mix the verdicts so the order gives no hint

sheet = [f"# Fresh hand-grading sheet ({len(chosen)} answers)\n", f"Source run: {judged_file}\n",
         "For each item decide:\n- **correct**: does the model answer match the gold answer? (rounding, units, brackets = negative). "
         "A 'not found' answer is not correct.\n"
         "- **supported**: do the pages the model was given actually contain the answer (or the numbers to compute it)?\n"
         "Write y or n in data/eval/hand_grades_fresh.csv. The judge's verdicts are hidden on purpose.\n"]
for n, r in enumerate(chosen, start=1):
    q = questions[r["id"]]
    sheet.append(f"\n---\n## {n}. {r['id']}  ({r['doc_name']})\n")
    sheet.append(f"**Question:** {q['question']}\n\n**Gold answer:** {q['answer']}\n\n**Model answer:** {r['answer']}\n")
    sheet.append("\n**Pages the model was given:**\n")
    for c in r["chunks"]:
        sheet.append(f"\n[page {c['page_number']}]\n```\n{' '.join(c['text'].split())}\n```\n")

Path("data/processed/fresh_sheet.md").write_text("\n".join(sheet), encoding="utf-8")
out = Path("data/eval/hand_grades_fresh.csv")
if out.exists():
    print(f"{out} already exists, not overwritten (your grades may be in it).")
else:
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "correct", "supported", "note"])
        for r in chosen:
            w.writerow([r["id"], "", "", ""])
print(f"wrote data/processed/fresh_sheet.md with {len(chosen)} items")
