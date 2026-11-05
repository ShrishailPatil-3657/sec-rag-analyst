"""Print the top 5 chunks for a question (no LLM involved).

usage: uv run python scripts/search_chunks.py "your question here" [DOC_NAME]
"""
import sys

from sec_rag_analyst.retrieval import load_index, search

question = sys.argv[1]
doc_name = sys.argv[2] if len(sys.argv) > 2 else "3M_2018_10K"

chunks, vectors = load_index(doc_name)
print(f"\nQuestion: {question}\n")
for rank, hit in enumerate(search(question, chunks, vectors, top_k=5), start=1):
    preview = hit["text"][:150].replace("\n", " ")
    print(f"{rank}. score={hit['score']:.3f}  page={hit['page_number']}  {hit['chunk_id']}\n   {preview}\n")
