"""Print text from chosen pages of a FinanceBench PDF.

usage: uv run python scripts/peek_pdf.py DOC_NAME PAGE_NUMBER [PAGE_NUMBER ...] [--chars N]
Page numbers start at 1, like a PDF viewer.
"""
import sys
from pathlib import Path

from pypdf import PdfReader

args = sys.argv[1:]
chars = 1500
if "--chars" in args:
    i = args.index("--chars")
    chars = int(args[i + 1])
    del args[i : i + 2]

doc_name, page_numbers = args[0], [int(a) for a in args[1:]]
reader = PdfReader(Path("data/financebench/pdfs") / f"{doc_name}.pdf")
print(f"{doc_name}: {len(reader.pages)} pages")
for n in page_numbers:
    print(f"\n===== page {n} =====")
    print((reader.pages[n - 1].extract_text() or "")[:chars])
