"""Ask a question about one filing: retrieve the top 5 chunks, then let a local model answer.

usage: uv run python scripts/ask.py "your question here" [DOC_NAME] [--chunks]

--chunks also prints the text of every chunk the model was given.
"""
import sys

from sec_rag_analyst.generation import ask_ollama, build_prompt
from sec_rag_analyst.retrieval import load_index, search

show_chunks = "--chunks" in sys.argv
args = [a for a in sys.argv[1:] if a != "--chunks"]
question = args[0]
doc_name = args[1] if len(args) > 1 else "3M_2018_10K"

chunks, vectors = load_index(doc_name)
hits = search(question, chunks, vectors, top_k=5)
answer = ask_ollama(build_prompt(question, hits))

if show_chunks:
    for rank, h in enumerate(hits, start=1):
        print(f"\n===== #{rank}  page {h['page_number']}  chunk {h['chunk_number']}  score {h['score']:.3f} =====")
        print(h["text"])

print(f"\nQuestion: {question}\n")
print(f"Answer: {answer}\n")
print("Pages given to the model:", ", ".join(f"{h['page_number']} ({h['score']:.3f})" for h in hits))
