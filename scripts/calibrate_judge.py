"""Compare the LLM judge with the owner's hand grades.

usage: uv run python scripts/calibrate_judge.py [RUN_FILE]
Uses the answers in the quick run file that were hand graded. If the run file has no saved chunks
(older runs), the retrieved chunks are recomputed by searching again (the search is deterministic).
"""
import csv
import glob
import json
import os
import sys
import time
from pathlib import Path

from sec_rag_analyst.judge import judge_answer
from sec_rag_analyst.retrieval import load_index, search

run_file = sys.argv[1] if len(sys.argv) > 1 else "data/processed/runs/20261107-203647-quick.jsonl"
rows = {r["id"]: r for r in (json.loads(line) for line in open(run_file)) if "id" in r}
questions = {q["financebench_id"]: q for q in map(json.loads, open("data/financebench/data/financebench_open_source.jsonl"))}
hand = list(csv.DictReader(open("data/eval/hand_grades.csv")))

out = Path("data/processed/judge") / (time.strftime("%Y%m%d-%H%M%S") + "-calibration.jsonl")
out.parent.mkdir(parents=True, exist_ok=True)

agree = {"correct": 0, "supported": 0}
disagreements = []
with out.open("w") as f:
    for h in hand:
        row, q = rows[h["id"]], questions[h["id"]]
        chunks = row.get("chunks")
        if chunks is None:  # older run: search again
            c, v = load_index(row["doc_name"])
            chunks = [{"page_number": x["page_number"], "text": x["text"]} for x in search(q["question"], c, v, top_k=5)]
        j = judge_answer(q["question"], q["answer"], row["answer"], chunks)
        judge_correct = "y" if j["verdict"] == "correct" else "n"
        judge_supported = "y" if j["supported"] else "n"
        agree["correct"] += judge_correct == h["correct"]
        agree["supported"] += judge_supported == h["supported"]
        f.write(json.dumps({"id": h["id"], "hand": [h["correct"], h["supported"]], "judge": j}) + "\n")
        mark = lambda a, b: "ok " if a == b else "DIFF"
        print(f"{h['id'][-5:]}  hand {h['correct']}/{h['supported']}  judge {judge_correct}/{judge_supported} ({j['verdict']})  "
              f"correct:{mark(judge_correct, h['correct'])} supported:{mark(judge_supported, h['supported'])}", flush=True)
        if (judge_correct, judge_supported) != (h["correct"], h["supported"]):
            disagreements.append((h["id"], j["reason"]))

n = len(hand)
print(f"\nagreement on correct:   {agree['correct']}/{n}")
print(f"agreement on supported: {agree['supported']}/{n}")
for i, reason in disagreements:
    print(f"  {i[-5:]}: {reason}")
print("saved to", out)
