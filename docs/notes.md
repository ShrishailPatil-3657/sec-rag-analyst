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
- **Faithfulness ("supported"):** do the pages the model was given actually contain what is needed to derive the gold answer (or the numbers to compute it)? Measures whether the answer rests on the document and not on a guess. It is separate from accuracy: a correct answer can be unsupported (a lucky guess, or a yes/no right by chance), and a wrong answer can be supported (the pages had it, the model misread it).
- Baseline on the held-out set: hit 0.56, accuracy 30%, faithfulness 34%. All three are needed. Hit rate says retrieval found the page, accuracy says the answer matched, faithfulness says the answer came from the text.
- **Page hit is not chunk hit.** Hit rate counts a question as a hit if any chunk from the gold *page* was retrieved. The chunk holding the number can still be missing, which is why many ratio questions fail even with a hit.

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

## LLM judge and calibration

- The **judge** is a second LLM call that grades the first. It sees the question, the gold answer, the model answer and the retrieved chunks. It returns a verdict (`correct`, `incorrect`, `not_found`) and a `supported` flag. Here it is the local qwen3:8b at temperature 0 (so the same input gives the same output). `not_found` is decided by code, not by the model, because abstaining is a fact about the answer text.
- Why a judge at all: grading 150 answers by hand for every experiment is too slow, and exact string matching fails on rounding, units and wording.
- **Calibration** does not train it. I grade some answers by hand, the judge grades the same ones, and we count agreement. Low agreement means the judge's numbers cannot be trusted.
- **Tuned vs unseen:** I changed the judge prompt twice while looking at my first 12 hand grades, so its 12/12 and 10/12 agreement there is optimistic. The fair test is answers it was never tuned on. I graded 10 fresh dev answers with the verdicts hidden (4 judged correct, 4 incorrect, 2 not found) and it agreed on 10/10 for both scores. Ten is a small sample, so the honest claim is "no disagreements found".
- **Freeze the judge** before the final measurement. If I keep editing it after seeing results, the numbers stop being comparable. Known judge errors are written down and fixed once, then the baseline is re-judged so every row in the results table uses the same judge.
- Known judge errors so far: abstentions in other words than "not found" were judged by content (fixed in code: the last two sentences are now checked, and the saved verdicts were recomputed without re-running the LLM), and one rounding miss remains (0.0146 against a gold of 0.01). I left the prompt alone because editing it would invalidate the check on unseen answers.

In my own words:

## Failure types

`scripts/report.py` gives each question one label, using the verdict and whether the gold page was retrieved:

- **ok:** correct, and the gold page was retrieved.
- **ok_without_gold_page:** correct, but the gold page was not retrieved. The answer came from another page (often the same figure appears twice), or it was a judge error. Check by hand before trusting it.
- **retrieval_miss:** gold page not retrieved, and the answer was wrong or not found. When the answer is "not found" this is the system behaving well; the retrieval is what failed.
- **abstained:** the gold page was retrieved, but the model said not found. The model could not use what it had.
- **wrong_despite_retrieval:** the gold page was retrieved, and the answer is still wrong. Causes seen: the chunk with the needed number was not retrieved, wrong column or units, an incomplete answer.

The labels point at what to fix: retrieval misses go to Phase C (filtering, hybrid search, reranking), wrong-despite-retrieval goes to chunking and prompting.

In my own words:

## Four kinds of page number

All of them describe a page of a PDF, but they are not the same number.

| Name | Where | Starts at |
| --- | --- | --- |
| `evidence_page_num` | FinanceBench gold evidence | 0 (position in the PDF file) |
| `page_index` | our pages and chunks | 0 (same position, same meaning) |
| `page_number` | our pages and chunks, and the labels the model sees | 1 (`page_index` + 1) |
| printed page number | the footer on the page | whatever the filing prints |

- Positions count every page of the file from the cover, including unnumbered front pages. The printed number is lower (Boeing by 2, AES by 3, Pfizer 2021 by 6 on one chunk checked, Adobe 2016 not at all).
- Compare `page_index` with `evidence_page_num` only. To find a cited page in a PDF viewer, jump to that position in the page counter, not the footer number.

In my own words:

## Cross-encoder reranker

- Today's search is a **bi-encoder**: the question and each chunk are turned into vectors separately, and search compares the vectors. Chunk vectors are computed once, so it is fast, but the model never reads the question and a chunk together.
- A **cross-encoder** reads the question and one chunk together and outputs a single relevance score. It is more accurate and much slower, because nothing can be precomputed.
- A **reranker** uses both: the fast search pulls a wider list of candidates (say the top 30), the cross-encoder rescores those, and the top 5 of the new order go to the LLM.
- What it can fix: the answer chunk is retrieved but ranked low (seen in a hand-graded item where the answer chunk was ranked 5th of 5). What it cannot fix: a page that never made the candidate list, which needs wider candidates, metadata filtering or hybrid search.
- Phase C will measure it as one change on its own, against this baseline.

In my own words:

## Failure notes: first retrieval baseline

- Baseline (known filing, top 5, dev set of 100): hit rate 0.57, full recall 0.46, MRR 0.40. By type: metrics-generated 0.76, novel-generated 0.56, domain-relevant 0.39.
- In the 11 misses on the quick set, the gold page was usually a financial statement table, and the question used a concept ("working capital", "quick ratio") that the table never states in those words. Hypothesis, not yet tested; Phase C is where it gets tested.
- Multi-page questions: hit rate (any) 0.70 but full recall only 0.15.
