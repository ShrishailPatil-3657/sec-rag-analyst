# SEC RAG Analyst

A system that answers questions about SEC filings and cites the page, plus a test bench that measures each RAG technique on the same benchmark (FinanceBench, 150 questions).

## Results table

Filled in one row at a time, one change per row. Nothing is measured yet. The Phase A hand checks below are a small sample and are not a baseline number.

| Technique | Config | Hit@5 | Accuracy | Faithfulness | What failed |
| --- | --- | --- | --- | --- | --- |
| Baseline | fixed chunks, dense top-5, local 8B | | | | |

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

**Next:** Phase B (eval harness). Fixed 20-question baseline, then a script for all 150 questions.

### Phase B: Eval harness (days 4-5)

*Not started.*

### Phase C: Retrieval upgrades (days 6-12)

*Not started.*

### Phase D: Agent (days 13-19)

*Not started.*

### Phase E: Polish (days 20-28)

*Not started.*
