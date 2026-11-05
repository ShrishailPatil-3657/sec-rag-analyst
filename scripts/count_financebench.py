"""Count what is in FinanceBench: companies, filing types, question types, and PDFs."""
import json
from collections import Counter
from pathlib import Path

root = Path("data/financebench")
questions = [json.loads(l) for l in open(root / "data/financebench_open_source.jsonl")]
docs = [json.loads(l) for l in open(root / "data/financebench_document_information.jsonl")]
pdfs = {p.stem for p in (root / "pdfs").glob("*.pdf")}

print(f"questions: {len(questions)}   documents (metadata): {len(docs)}   PDFs on disk: {len(pdfs)}")

print("\nQuestions per company:")
for company, n in Counter(q["company"] for q in questions).most_common():
    print(f"  {n:3d}  {company}")

print("\nQuestion type (how the question was made):")
for k, n in Counter(q["question_type"] for q in questions).items():
    print(f"  {n:3d}  {k}")

print("\nReasoning needed (first label only):")
for k, n in Counter((q["question_reasoning"] or "none").split(" OR ")[0] for q in questions).most_common():
    print(f"  {n:3d}  {k}")

print("\nFiling types in the document list:")
for k, n in Counter(d["doc_type"] for d in docs).most_common():
    print(f"  {n:3d}  {k}")

print("\nFilings the questions point at:")
q_docs = Counter(q["doc_name"] for q in questions)
print(f"  {len(q_docs)} distinct documents; most-asked: {q_docs.most_common(3)}")

print("\nPDFs with no metadata row:", sorted(pdfs - {d["doc_name"] for d in docs}))
print("Questions whose PDF is missing:", sorted(set(q_docs) - pdfs) or "none")
