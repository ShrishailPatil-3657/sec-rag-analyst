# SEC RAG Analyst

A system that answers questions about SEC filings and cites the page, plus a test bench that measures each RAG technique on the same benchmark (FinanceBench, 150 questions).

## Results table

Filled in one row at a time, one change per row. Numbers are on the 50 held-out questions (run once, never tuned on). Dev numbers (100 questions) are in the Phase B notes. Accuracy and faithfulness come from a local LLM judge (qwen3:8b) that agreed with my hand grades on 10 of 10 unseen answers. That sample is small, and one known judge miss remains (see Phase B).

| Technique | Config | Hit@5 | Accuracy | Faithfulness | What failed |
| --- | --- | --- | --- | --- | --- |
| Baseline | fixed 1,000-char chunks, bge-small dense top-5, qwen3:8b | 0.56 | 30% (34% wrong, 36% not found) | 34% | Gold page missed on 38% of questions. Right page but wrong or incomplete answer on 18%: numbers for ratios sit in a different chunk, wrong column or units. |

## Phase notes

One section per phase: what I built, what the result was, what failed, what I learned. Concept explanations live in [docs/notes.md](docs/notes.md).

### Phase A: Baseline (days 1-3)

**What I built**

1. PDF to pages (pypdf), keeping `page_index` (0-based) and `page_number` (1-based).
2. Pages to chunks: about 1,000 characters with 200 overlap, labelled with page and chunk number.
3. Chunks to vectors with a local embedding model (BGE-small), saved to disk. The index is a plain array in memory.
4. A question is turned into a vector with the same model. The vectors are normalized, so `vectors @ question_vector` is cosine similarity, and the top 5 chunks are kept.
5. The 5 chunks go into a prompt (answer only from the text, cite pages, otherwise say "not found") and a local model (Ollama, qwen3:8b) writes the answer.
6. `scripts/ask.py` runs all of this from the terminal for one filing.

**What I tested**

Hand checks on the benchmark questions for two filings: `3M_2018_10K` (2 questions) and `AMD_2022_10K` (7 questions). I compared the retrieved pages with the gold evidence using `page_index`, and read each answer against the gold answer. I also wrote 2 extra questions of my own about an AMD share-repurchase table. They are not benchmark questions, and I wrote them after reading the table, so they are easier than the real ones.

**Results (hand graded, 9 benchmark questions, not a rate)**

| Filing | Question | Gold page in top 5 | Model answer | Verdict |
| --- | --- | --- | --- | --- |
| 3M | 03029 capex FY2018 ($1,577M) | no (best gold chunk ranked 273 of 816) | $8,738M, wrong column | confidently wrong |
| 3M | 04672 net PP&E FY2018 ($8.70B) | no (best gold chunk ranked 111) | $0.222B, wrong row | confidently wrong |
| AMD | 00222 quick ratio | no (ranked 140 and 401) | `not found` | abstained, which was the right call |
| AMD | 00995 major products | yes, rank 4 | correct list | correct |
| AMD | 01198 what drove revenue | yes by page, but the answer chunk ranked 6th | only the Xilinx acquisition | partial |
| AMD | 00917 what drove operating margin | yes, rank 4 | correct reason plus unsupported extra text | mostly correct |
| AMD | 01279 largest cash flow source | yes, rank 5 | operating activities | correct |
| AMD | 00563 fastest-growing segment | no | Data Center, 64% (from page 43, not the gold page 48) | correct, other page |
| AMD | 00757 customer concentration | no, but the gold chunk sits next to a retrieved page | "yes", without the 16% figure | partial |

- Gold page in the top 5: 3M 0 of 2, AMD 4 of 7.
- Answers: 3 correct, 1 mostly correct, 2 partial, 1 abstained, 2 confidently wrong.
- My own 2 table questions (AMD share repurchases, page 41): both correct.

**What failed and why**

Retrieval:
- **Chunks full of numbers embed weakly.** The 3M gold chunks ranked 111th and 273rd, while prose chunks about "capital spending" ranked in the top 5.
- **The question and the filing use different words.** "capital expenditure" versus "Purchases of property, plant and equipment". "PPNE" never appears in the filing.
- **Exhibit-list pages (103 to 106 in AMD) crowded the top 5.** They took 9 of 35 slots across the 7 AMD questions, because their boilerplate matches short, general questions.
- **Scores are bunched together** (top 5 often within 0.01 to 0.02), so the ranking among them is close to arbitrary. In AMD question 3 the answer chunk lost by 0.001.
- **A page-level hit is not a chunk-level hit.** In AMD question 3 the right page was retrieved but not the chunk with the answer.

Chunking and parsing:
- **Tables are cut between chunks.** The 3M capex table was split, so the next chunk held a bare "8,738" with no labels.
- **Table layout depends on the PDF.** pypdf wrote the 3M table one value per line, so row and column were lost. In the AMD repurchase table each row stayed on one line, and the questions worked.

Generation:
- **The model sometimes answers when it should say "not found".** On 3M it picked a number from a fragment with no labels. On AMD question 1 it abstained correctly, so the behaviour is inconsistent.
- **It adds text that is not in the excerpts** (AMD question 4) and writes "likely" when unsure (AMD question 3).
- **It put pages after "not found"**, although the prompt says to reply exactly "not found".
- **Small citation slip.** In AMD question 2 a phrase from page 60 was cited as page 4.

**What worked**
- Prose questions (products, drivers, cash flow) were mostly found and answered well.
- Tables worked when the row stayed intact and the question used the table's own words (the AMD repurchase table, 2 of 2).
- The model abstained when the context was clearly off-topic.

**What I learned**
- Dense (embedding) search matches meaning, not exact words. It handles synonyms and misses exact line items and acronyms.
- "Tables fail" is too broad. They fail when the text is flattened, when the question uses different words from the row labels, or when a row is cut between chunks.
- A wrong answer can come from retrieval or from generation. `--chunks` shows which one.
- Raising `top_k` would not have fixed the 3M questions, because the gold chunks ranked far below 5.
- The benchmark's `evidence_page_num` is the 0-based PDF page, not the printed number. For AMD, printed page = `page_number` - 3. Citations shown to a user should probably include both.

**Open decisions for Phase B**
- Score hit rate by page or by chunk, or both?
- If the answer is right but comes from a page other than the gold page (AMD question 6), is that a hit?
- Count `not found (page ...)` as an abstention.
- Decide how to grade long-form answers (drivers, explanations), where wording differs from the gold answer.

In my own words (fill in):

- What the pipeline does, from PDF to answer:
  1. extract_pages.py reads each page of the PDF and saves its text with a page_index (0-based) and a page_number (1-based).
  2. chunk_pages.py cuts each page into chunks of 1,000 characters with 200 characters of overlap, so a sentence cut at the edge still appears whole in the next chunk. Every chunk keeps its page_index and page_number so the answer can cite a page.
  3. When I ask a question, ask.py calls load_index() in retrieval.py. If the chunk vectors are not saved yet, it turns every chunk into a vector with the BGE model and saves them to a file on disk. Otherwise it reuses the saved file. For now the vectors sit in memory as a plain array. Later I will move them to Postgres with pgvector.
  4. The question is turned into a vector with the same model. All vectors are normalized, so a dot product between the question vector and every chunk vector gives the cosine similarity. I keep the 5 chunks with the highest scores.
  5. generation.py builds a prompt: the rules (answer only from the text, cite pages, say "not found" if the answer is missing), then the 5 chunks labelled with their pages, then the question. A local Ollama model (qwen3:8b) writes the answer, and ask.py prints it with the pages it was given.
- Why a table is hard for this pipeline, and when it is not:
  A table is hard when its labels get separated from its numbers. This happens when the table is cut between two chunks, or when the PDF text comes out with one value per line, so I can no longer tell which row and column a number belongs to. A chunk that is mostly numbers also scores lower in the search than a chunk of normal sentences, so the right chunk can rank far below the top 5. It also fails when my question uses different words from the row label, for example "capital expenditure" versus "Purchases of property, plant and equipment". A table works well when each row stays together on one line with its label, and the question uses the same words as the table, like the dates in the AMD share repurchase table.
- Why the model answered instead of saying "not found":
  In the 3M questions, the chunks it received looked like they contained the answer. In one, a bare number sat right under the words "capital spending", so the model took it as the answer. The "not found" rule is only an instruction in the prompt. Nothing checks the answer against the text afterwards, and the model cannot know that the right number was in a chunk it never received. When the retrieved text is clearly unrelated, as in the AMD quick ratio question, the model did say "not found". It guesses when the text is close to the topic but not the answer.

### Phase B: Eval harness (days 4-5)

**What I built**

1. A fixed split of the 150 questions with a set seed: 100 dev (for debugging and error analysis), 50 held-out (run once for the headline numbers), plus a 30-question quick set.
2. Retrieval metrics per question: hit rate (any gold page in the top 5), full recall (all gold pages), mean fraction of gold pages found, and MRR (how high the first gold page ranks). All compare `page_index`.
3. A batch runner (`scripts/run_eval.py`) that runs a split end to end, logs the config (models, chunking, git commit) and saves the retrieved chunks with each answer. It can resume after an interruption.
4. An LLM judge (`src/sec_rag_analyst/judge.py`, local qwen3:8b, temperature 0). It gives each answer a verdict (`correct`, `incorrect`, `not_found`) and a `supported` flag (do the retrieved pages contain what is needed to derive the gold answer, which is the faithfulness score). `not_found` is decided by code, not by the model.
5. `scripts/report.py`: rates by question type and a failure-type breakdown for any judged run.

**How I checked the judge**

- On my first 12 hand grades it agreed on `correct` 12/12 and on `supported` 10/12. The prompt was changed twice while looking at those same items, so that is optimistic.
- On 10 dev answers it had never seen (4 judged correct, 4 incorrect, 2 not found, verdicts hidden while I graded), it agreed on `correct` 10/10 and `supported` 10/10. One item I first graded "partially supported" (a table cut off at the last line, 90% there) and then counted as supported.
- Ten items is a small sample. Read this as "no disagreements found", not "100% accurate".

**Results**

| Run | Questions | Hit rate | Full recall | MRR | Correct | Incorrect | Not found | Supported |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | 100 | 0.57 | 0.46 | 0.40 | 31% | 32% | 37% | 33% |
| held-out | 50 | 0.56 | 0.52 | 0.42 | 30% | 34% | 36% | 34% |

The held-out numbers match the dev numbers, so the dev set was not flattering the baseline (with 50 questions, one question is 2 points).

By question type (accuracy, dev / held-out): domain-relevant 30% / 18%, metrics-generated 24% / 35%, novel-generated 38% / 38%. Metrics-generated questions have the most wrong answers on dev (42% incorrect). Domain-relevant questions have the most abstentions (45% on dev) and the lowest retrieval hit rate (0.39 on dev).

Failure types (dev / held-out): gold page missed 39 / 19, correct 27 / 12, right page but wrong answer 20 / 9, right page but the model abstained 10 / 7, correct without the gold page 4 / 3.

When the gold page was retrieved, the answer was correct 47% of the time on dev (27 of 57 questions). When it was missed, it was correct 9% of the time (4 of 43), and 27 of those 43 were abstentions, which is the behaviour I want.

**What failed and why**

- **Retrieval is the biggest problem.** The gold page was missed for about 4 questions in 10. Reasons seen: acronyms that the filing never uses ("PPNE" for property, plant and equipment, net), and numbers-heavy statement pages that embed weakly.
- **A page hit is not a chunk hit.** Roughly 13 of the 20 dev questions with the right page and a wrong answer were ratio questions where the page was retrieved but the chunk holding a needed number (COGS, capex, dividends) was not.
- **Wrong column or units.** Block FY2020: the model read $2,131,050 thousand as millions.
- **Incomplete answers.** PepsiCo: gave $4.2B per facility instead of the $8.4B total.
- **Ranking.** In several hand-graded items the answer chunk was in the top 5 but ranked last.
- **The model abstains in its own words**, not the exact phrase "not found" (see judge limits).

**Judge fixes (start of Phase C)**

- **Abstentions in other words (fixed).** `not_found` used to be detected by the exact phrase, so answers like "Therefore, it is not possible to determine..." were judged on content. On dev, 1 was marked `correct` (Amcor gross margin) and 4 `incorrect`; on held-out, 2 `incorrect`. `is_not_found` now also checks the last two sentences for conclusion phrases ("the answer is not found", "not possible to determine", "cannot be calculated"). It looks only at the end, so an answer that mentions a missing detail and then gives a number is not an abstention (tested on real answers). The saved verdicts were recomputed with `scripts/rescore_abstentions.py`, without calling the LLM again, so the judge prompt stayed frozen and the 10/10 unseen check still applies. The numbers above are the corrected ones. Before the fix: dev 32 / 36 / 32, held-out 30 / 38 / 32.
- **Not changed, on purpose.** Editing the judge prompt would invalidate the unseen check and need a full re-judge. One miss is known: Coca-Cola 0.0146 against a gold of 0.01, which should be correct after rounding to the gold's precision. It costs at most 1 point. Netflix (5,466,312 against a gold of $5,466M in millions) I first thought was too strict. The question asks for millions and the answer gave the thousands figure with no conversion, so `incorrect` is right.
- **Soft abstentions stay as they are.** One held-out answer (3M quick ratio) says the quick ratio "is not explicitly mentioned" and then talks about liquidity. It is judged on content, as `incorrect`.
- 4 dev and 3 held-out answers were correct without the gold page (`ok_without_gold_page`). From the judge's reasons on the dev ones, they seem to come from another page with the same figures (not yet checked by hand). Stricter accuracy (correct and gold page retrieved) is 27% on dev.

**What I learned**

- Hit rate, accuracy and faithfulness measure different things, and a result needs all three. Retrieval hit is 0.57 but accuracy is 32%, and faithfulness is only 33%.
- A held-out set is only honest if it is run once. I did not change anything after seeing it.
- A judge is a model too and needs its own check against human grades.
- Page numbers come in four forms (see `docs/notes.md`). Only `page_index` is used for comparison.

**Next:** Phase C (retrieval upgrades), one change at a time, starting with metadata filtering. The judge fixes are done, so the baseline above is the comparison point. The reranker (cross-encoder) targets the "answer chunk ranked last" cases.

In my own words (fill in):

- What the three scores (hit rate, accuracy, faithfulness) each tell me, and why I need all three:
- Why the held-out set is run only once:
- What I trust and do not trust about the judge, and why:
- What the failure types say about where to improve first:

### Phase C: Retrieval upgrades (days 6-12)

*Not started.*

### Phase D: Agent (days 13-19)

*Not started.*

### Phase E: Polish (days 20-28)

*Not started.*
