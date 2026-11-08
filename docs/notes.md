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

## Eval harness (Phase B)

A **harness** is the scaffolding around the thing under test. It feeds each question to the RAG system, collects the outputs, scores them against the gold answers, and logs the result with the settings used. The RAG system is what is tested; the harness is the machinery that tests it the same way every time.

In my own words:

## Dev set, held-out set, and why

- No model is trained here. We tune **settings** (chunk size, k, prompt). If we pick settings by looking at one question set's score, that score becomes optimistic (overfitting).
- So the 150 questions are split once, with a fixed seed: **dev** (100, used while experimenting), **held-out** (50, looked at only at the end of a phase), and a **quick** subset (30 of the dev questions, for fast checks). The split is saved in `data/eval/split.json` and never regenerated.
- The split is **stratified**: each `question_type` is split separately so both parts get a mix. The ids are **sorted before the shuffle**, so the same seed gives the same split whatever order the file has.
- Small sets are noisy. On 50 questions one question is 2 points, and a gain under about 15 points could be luck. On 100 questions, about 10.

In my own words:

## Retrieval metrics

- **hit rate (any):** at least one gold page is in the top 5. **full recall (all):** every gold page is. **mean fraction:** gold pages found divided by gold pages.
- **Reciprocal rank (rr):** 1 divided by the rank of the first correct chunk (1, 0.5, 0.33 ...; 0 if absent). **MRR** is the average of rr over all questions. It rewards putting the right page near the top, which hit rate cannot see.
- Compare `page_index` (0-based) to `evidence_page_num`. Gold pages are a set because some questions list a page twice.

In my own words:

## LLM judge and calibration (planned)

- The **judge** is a second LLM call that grades the first: it sees the question, gold answer and model answer (and the retrieved chunks, for faithfulness).
- **Calibration** does not train it. I grade about 12 answers by hand, the judge grades the same ones, and we measure agreement. Low agreement means fixing the judge prompt before trusting its numbers.

In my own words:

## Failure notes: first retrieval baseline

- Baseline (known filing, top 5, dev set of 100): hit rate 0.57, full recall 0.46, MRR 0.40. By type: metrics-generated 0.76, novel-generated 0.56, domain-relevant 0.39.
- In the 11 misses on the quick set, the gold page was usually a financial statement table, and the question used a concept ("working capital", "quick ratio") that the table never states in those words. Hypothesis, not yet tested; Phase C is where it gets tested.
- Multi-page questions: hit rate (any) 0.70 but full recall only 0.15.
