"""Print the results table for one judged run.

usage: uv run python scripts/report.py data/processed/runs/<run>.judged.jsonl
Shows: retrieval numbers, correct / incorrect / not_found rates, faithfulness, failure types, and a split by question type.
"""
import json
import sys
from collections import Counter, defaultdict

from sec_rag_analyst.metrics import summarize

run_file = sys.argv[1]
lines = [json.loads(line) for line in open(run_file)]
config, rows = lines[0]["config"], lines[1:]
questions = {q["financebench_id"]: q for q in map(json.loads, open("data/financebench/data/financebench_open_source.jsonl"))}

# Each row has: row["scores"]["hit_any"] (bool), row["judge"]["verdict"] ("correct" | "incorrect" | "not_found"),
# row["judge"]["supported"] (bool), and questions[row["id"]]["question_type"].


def failure_type(row):
    """Return one label for this row.

    ok                      correct, and the gold page was retrieved
    ok_without_gold_page    correct, but the gold page was not retrieved (answer came from another page; check by hand)
    retrieval_miss          gold page not retrieved, and the answer was not correct (wrong or not_found)
    abstained               gold page retrieved, but the model said not found
    wrong_despite_retrieval gold page retrieved, but the answer was wrong
    """
    verdict, hit = row["judge"]["verdict"], row["scores"]["hit_any"]
    if verdict == "correct":
        return "ok" if hit else "ok_without_gold_page"
    if not hit:
        return "retrieval_miss"
    if verdict == "not_found":
        return "abstained"
    return "wrong_despite_retrieval"


def rates(group):
    """Return {"correct": share, "incorrect": share, "not_found": share, "supported": share} for a list of rows."""
    verdicts = Counter(r["judge"]["verdict"] for r in group)
    supported = sum(r["judge"]["supported"] for r in group)
    n = len(group)
    return {"correct": verdicts["correct"] / n, "incorrect": verdicts["incorrect"] / n,
            "not_found": verdicts["not_found"] / n, "supported": supported / n}


def print_rates(title, group):
    r = rates(group)
    print(f"{title:28s} n={len(group):3d}  correct {r['correct']:.0%}  incorrect {r['incorrect']:.0%}  "
          f"not_found {r['not_found']:.0%}  supported {r['supported']:.0%}")


print(f"run: {config['run_id']}  ({len(rows)} questions, generation model {config['generation_model']})")
print("retrieval:", summarize([r["scores"] for r in rows]))
print()
print_rates("ALL", rows)

print("\nby question type")
by_type = defaultdict(list)
for r in rows:
    by_type[questions[r["id"]]["question_type"]].append(r)
for t in sorted(by_type):
    print_rates(t, by_type[t])

print("\nfailure types")
counts = Counter(failure_type(r) for r in rows)
for label, n in counts.most_common():
    print(f"  {label:26s} {n:3d}  ({n / len(rows):.0%})")
