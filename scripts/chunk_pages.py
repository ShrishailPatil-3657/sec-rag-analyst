"""Cut each page of a filing into overlapping chunks and save them with labels.

usage: uv run python scripts/chunk_pages.py [DOC_NAME]
The logic lives in src/sec_rag_analyst/prep.py; this script is a thin wrapper around it.
"""
import json
import sys

from sec_rag_analyst.prep import PROCESSED_DIR, make_chunks

doc_name = sys.argv[1] if len(sys.argv) > 1 else "3M_2018_10K"
pages = json.loads((PROCESSED_DIR / f"{doc_name}.pages.json").read_text(encoding="utf-8"))
chunks = make_chunks(doc_name, pages)
out_path = PROCESSED_DIR / f"{doc_name}.chunks.json"
out_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
print(f"{doc_name}: {len(pages)} pages -> {len(chunks)} chunks, saved to {out_path}")
