"""Turn one FinanceBench PDF into a JSON file with one record per page.

usage: uv run python scripts/extract_pages.py [DOC_NAME]
The logic lives in src/sec_rag_analyst/prep.py; this script is a thin wrapper around it.
"""
import json
import sys

from sec_rag_analyst.prep import PROCESSED_DIR, extract_pages

doc_name = sys.argv[1] if len(sys.argv) > 1 else "3M_2018_10K"
pages = extract_pages(doc_name)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
out_path = PROCESSED_DIR / f"{doc_name}.pages.json"
out_path.write_text(json.dumps(pages, indent=2), encoding="utf-8")
print(f"{doc_name}: wrote {len(pages)} pages to {out_path}")
