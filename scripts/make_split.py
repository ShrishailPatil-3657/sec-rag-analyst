"""Write data/eval/split.json once. Do not re-run it after experiments start: the split must stay fixed."""
import json
import sys
from pathlib import Path

from sec_rag_analyst.split import make_split

DATA = Path("data/financebench/data/financebench_open_source.jsonl")
OUT = Path("data/eval/split.json")

if OUT.exists():
    sys.exit(f"{OUT} already exists. The split is fixed; delete it by hand only if you really mean to.")

questions = [json.loads(line) for line in DATA.read_text().splitlines()]
split = make_split(questions)
OUT.write_text(json.dumps(split, indent=2))
print({name: len(ids) for name, ids in split.items()}, "->", OUT)
