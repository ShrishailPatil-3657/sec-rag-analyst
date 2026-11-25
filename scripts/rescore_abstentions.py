"""Apply the current is_not_found rule to a judged run, without calling the LLM again.

usage: uv run python scripts/rescore_abstentions.py RUN.judged.jsonl [...]
The judge's `supported` flag and reasons stay as they were. Only rows whose answer is now an abstention change:
their verdict becomes not_found, and the old verdict is kept in "verdict_before". Safe to run twice.
"""
import json
import sys
from pathlib import Path

from sec_rag_analyst.judge import is_not_found

for name in sys.argv[1:]:
    path = Path(name)
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    changed = []
    for row in lines[1:]:
        if is_not_found(row["answer"]) and row["judge"]["verdict"] != "not_found":
            row["judge"]["verdict_before"] = row["judge"]["verdict"]
            row["judge"]["verdict"] = "not_found"
            changed.append(f"{row['id'][-5:]} ({row['judge']['verdict_before']})")
    lines[0]["abstention_rule"] = "last-two-sentences phrases (judge.py is_not_found)"
    path.write_text("".join(json.dumps(x) + "\n" for x in lines))
    print(f"{path.name}: {len(changed)} rows changed to not_found: {', '.join(changed) or 'none'}")
