"""Turn one FinanceBench PDF into a JSON file with one record per page."""
import json
import sys
from pathlib import Path

from pypdf import PdfReader

doc_name = sys.argv[1] if len(sys.argv) > 1 else "3M_2018_10K"
pdf_path = Path("data/financebench/pdfs") / f"{doc_name}.pdf"
out_path = Path("data/processed") / f"{doc_name}.pages.json"
out_path.parent.mkdir(parents=True, exist_ok=True)

reader = PdfReader(pdf_path)
pages = []
for index, page in enumerate(reader.pages):
    pages.append(
        {
            "doc_name": doc_name,
            "page_index": index,  # starts at 0, same as FinanceBench "evidence_page_num"
            "page_number": index + 1,  # starts at 1, same as the PDF viewer
            "text": page.extract_text() or "",
        }
    )

out_path.write_text(json.dumps(pages, indent=2), encoding="utf-8")
print(f"{doc_name}: wrote {len(pages)} pages to {out_path}")
