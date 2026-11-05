"""Cut each page of a filing into overlapping chunks and save them with labels."""
import json
import sys
from pathlib import Path

CHUNK_SIZE = 1000  # characters per chunk
OVERLAP = 200  # characters shared with the previous chunk

doc_name = sys.argv[1] if len(sys.argv) > 1 else "3M_2018_10K"
pages = json.loads(Path(f"data/processed/{doc_name}.pages.json").read_text(encoding="utf-8"))

chunks = []
for page in pages:
    text = page["text"]
    step = CHUNK_SIZE - OVERLAP
    # start positions: 0, 800, 1600, ... until we run past the end of the page
    for number, start in enumerate(range(0, len(text), step)):
        piece = text[start : start + CHUNK_SIZE]
        if len(piece.strip()) < OVERLAP:  # the tail is already inside the previous chunk
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

out_path = Path(f"data/processed/{doc_name}.chunks.json")
out_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
print(f"{doc_name}: {len(pages)} pages -> {len(chunks)} chunks, saved to {out_path}")
