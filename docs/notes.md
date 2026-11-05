# Learning notes

Plain-language explanations of how this project works. Add to it as new ideas come up. The "In my own words" lines are for you: rewrite each idea without looking, because being able to explain it is what interviews test.

## Day 1 exploration (fill in)

- Companies that appear most:
- Kinds of questions I saw:
- Hardest question to answer by hand, and why:
- One thing that confused me:

## RAG (Retrieval-Augmented Generation)

An LLM answers from memory, which can be wrong or invented (hallucination). RAG makes it an open-book exam: first **retrieve** the relevant pages, then let the LLM **generate** an answer using only those pages, and cite them.

In my own words:

## The pipeline

```
Prepare once:   PDF -> pages -> chunks (+ labels) -> embeddings -> index
Each question:  question -> embedding -> top-k closest chunks -> prompt -> LLM -> answer + pages
```

- **Parsing:** turn the PDF into plain text, keeping each page's number.
- **Chunk:** a small piece of text (about 1,000 characters). Search works better on small pieces, and an LLM can only read so much at once.
- **Chunk overlap:** neighbouring chunks share about 200 characters so a sentence isn't cut in half.
- **Metadata:** labels on each chunk (company, year, form type, page). Later we use them to search only "3M, FY2018".
- **Embedding:** a list of numbers that captures a text's meaning. Similar meaning gives similar numbers.
- **Similarity / top-k:** a score for how close two embeddings are. Top-5 means the five best-scoring chunks.

In my own words:

## In-memory index vs. vector database

An **index** is where chunks and embeddings are stored so they can be searched. **In-memory** means a plain Python list/array in RAM:

```python
scores = embeddings @ question_embedding   # compare the question to every chunk
top5 = scores.argsort()[-5:]               # keep the 5 best
```

Fine for a few filings: search takes milliseconds. It doesn't scale to hundreds of filings and can't pre-filter. A **vector database** (Postgres + pgvector, in Phase E) stores the same embeddings but filters by metadata and searches fast. We start in memory so retrieval is visible, not hidden by a database.

In my own words:

## Hit rate vs. accuracy

- **Hit rate (recall@k):** was the evidence page among the top k retrieved chunks? Measures *retrieval*.
- **Accuracy:** did the final answer match the gold answer (allowing for rounding)? Measures *retrieval plus generation*.
- If hit is yes and accuracy is no, the problem is reading or arithmetic. If hit is no, fix retrieval first.

In my own words:

## Baseline and ablation

- **Baseline:** the simplest working version, measured first.
- **Ablation:** change one thing at a time and record its effect. This shows which technique actually helped, and it is the core of the results table.
- Keep the 20 baseline questions fixed. Don't tune on them.

In my own words:

## Failure notes

Write one sentence each time something goes wrong, for example "Table row cut across two chunks, so the value was separated from its label."

- The tables being cut in between chunks, the row and col lables getting seperated from the values are part of the reasons causing the model to answer incorrectly, this also depends on how the pdf is being read - tables fail when the text is flattened, for 3M this happend and for AMD the table lables were retained so it answered correctly.
- Using same wording as in the filing leads to more accurate chunks being fetched and correct answers.
