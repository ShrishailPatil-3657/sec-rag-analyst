"""Compare the owner's fresh hand grades with the judge's saved verdicts (no LLM calls).

usage: uv run python scripts/compare_fresh.py [JUDGED_FILE]
Reads data/eval/hand_grades_fresh.csv and the judged dev run. Judge verdicts incorrect and not_found both count as "n" for correct.
A hand grade other than y or n (e.g. "partially") is shown but left out of the agreement counts.
"""
import csv
import json
import sys

judged_file = sys.argv[1] if len(sys.argv) > 1 else "data/processed/runs/20261117-125715-dev.judged.jsonl"
judged = {r["id"]: r for r in (json.loads(line) for line in open(judged_file)) if "id" in r}
hand = list(csv.DictReader(open("data/eval/hand_grades_fresh.csv")))

counts = {"correct": [0, 0], "supported": [0, 0]}  # [agree, compared]
for h in hand:
    j = judged[h["id"]]["judge"]
    jc = "y" if j["verdict"] == "correct" else "n"
    js = "y" if j["supported"] else "n"
    marks = []
    for name, mine, theirs in (("correct", h["correct"], jc), ("supported", h["supported"], js)):
        if mine in ("y", "n"):
            counts[name][1] += 1
            counts[name][0] += mine == theirs
            marks.append(f"{name}:{'ok ' if mine == theirs else 'DIFF'}")
        else:
            marks.append(f"{name}:{mine!r} (not counted)")
    print(f"{h['id'][-5:]}  hand {h['correct']}/{h['supported']}  judge {jc}/{js} ({j['verdict']})  " + "  ".join(marks))
    if jc != h["correct"] or js != h["supported"]:
        print(f"        judge reason: {j['reason']}")

print()
for name, (a, n) in counts.items():
    print(f"agreement on {name}: {a}/{n}")
