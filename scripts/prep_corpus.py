"""Prepare every filing that a question set uses.

usage: uv run python scripts/prep_corpus.py quick     (or dev, or held_out)
"""
import json
import sys
import time
from pathlib import Path

from sec_rag_analyst.prep import prepare
from sec_rag_analyst.retrieval import load_index

split_name = sys.argv[1]
split = json.loads(Path("data/eval/split.json").read_text())
rows = map(json.loads, Path("data/financebench/data/financebench_open_source.jsonl").read_text().splitlines())
doc_of = {q["financebench_id"]: q["doc_name"] for q in rows}

docs = sorted({doc_of[i] for i in split[split_name]})
for n, doc in enumerate(docs, start=1):
    start = time.time()
    prepare(doc)  # pages and chunks
    load_index(doc)  # embeddings: computed once, then reused
    print(f"[{n}/{len(docs)}] {doc}  {time.time() - start:.0f}s", flush=True)
