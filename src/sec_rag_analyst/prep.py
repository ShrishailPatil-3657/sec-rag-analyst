"""Turn a FinanceBench PDF into pages and chunks on disk. Skips work that is already done."""
import json
from pathlib import Path

from pypdf import PdfReader

PDF_DIR = Path("data/financebench/pdfs")
PROCESSED_DIR = Path("data/processed")
CHUNK_SIZE = 1000  # characters per chunk
OVERLAP = 200  # characters shared with the previous chunk


def extract_pages(doc_name: str) -> list[dict]:
    reader = PdfReader(PDF_DIR / f"{doc_name}.pdf")
    return [
        {
            "doc_name": doc_name,
            "page_index": index,  # 0-based, same as FinanceBench evidence_page_num
            "page_number": index + 1,  # 1-based, same as the PDF viewer
            "text": page.extract_text() or "",
        }
        for index, page in enumerate(reader.pages)
    ]


def make_chunks(doc_name: str, pages: list[dict]) -> list[dict]:
    chunks = []
    step = CHUNK_SIZE - OVERLAP
    for page in pages:
        text = page["text"]
        for number, start in enumerate(range(0, len(text), step)):
            piece = text[start : start + CHUNK_SIZE]
            if len(piece.strip()) < OVERLAP:  # tail already inside the previous chunk
                continue
            chunks.append(
                {
                    "chunk_id": f"{doc_name}_p{page['page_index']}_c{number}",
                    "doc_name": doc_name,
                    "page_index": page["page_index"],
                    "page_number": page["page_number"],
                    "chunk_number": number,
                    "text": piece,
                }
            )
    return chunks


def prepare(doc_name: str) -> None:
    """Write <doc>.pages.json and <doc>.chunks.json unless the chunks file already exists."""
    chunks_path = PROCESSED_DIR / f"{doc_name}.chunks.json"
    if chunks_path.exists():
        return
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pages = extract_pages(doc_name)
    (PROCESSED_DIR / f"{doc_name}.pages.json").write_text(json.dumps(pages, indent=2), encoding="utf-8")
    chunks_path.write_text(json.dumps(make_chunks(doc_name, pages), indent=2), encoding="utf-8")
