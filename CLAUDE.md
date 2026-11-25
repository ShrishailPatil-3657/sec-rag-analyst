# SEC RAG Analyst

A RAG system that answers questions about SEC filings (10-K, 10-Q, 8-K, earnings) with page-level citations, and a research testbed that measures each RAG technique against the same benchmark.

The owner is learning while building. Explain new concepts in plain language, one step at a time, and say what each step is for. Keep finance jargon to what the task needs.

## Goals

1. **Working analyst.** Given a question, find the right filing page, read it, answer, and cite the page. Prefer "not found" to a guess.
2. **Honest measurement.** Every technique gets a number on a fixed question set. The README results table (baseline to final) is the main deliverable.
3. **Algorithm comparison.** Change one thing at a time (ablation) and record the effect on hit rate, accuracy and faithfulness.
4. **Boston add-on corpus.** After the FinanceBench work is stable, add Boston-area filings as a demo corpus (see "Boston add-on").

Not goals: stock picking, judging companies, a polished UI.

## Data

- Benchmark: `data/financebench/` (a separate git repo cloned inside this one).
  - `data/financebench_open_source.jsonl`: 150 questions. Fields: `financebench_id, company, doc_name, question_type, question_reasoning, domain_question_num, question, answer, justification, dataset_subset_label, evidence`. Split evenly: 50 `metrics-generated`, 50 `domain-relevant`, 50 `novel-generated`.
  - `data/financebench_document_information.jsonl`: 361 documents (`doc_name, company, gics_sector, doc_type, doc_period, doc_link`). Types: 10k, 10q, 8k, earnings, annual report.
  - `pdfs/`: 368 PDFs. Eight have no metadata row: `ADOBE_2022Q2_10Q`, `AMCOR_2022_8K_*` (two), `BLOCK_2022_8K_dated-2022-01-28`, `BOSTONPROPERTIES_2015_10K`, `FOOTLOCKER_2022_10Q`, `ULTABEAUTY_2023Q1_EARNINGS`, `ULTABEAUTY_2023Q2_EARNINGS`.
  - `results/`: published baseline outputs (GPT-4, Claude-2, Llama2) to compare against.
- About 40 companies. Some have filings but no questions (Apple, Oracle, eBay, Intel, PG&E, Salesforce). Do not choose evaluation filings from those.
- `doc_name` is the key that links a question to its PDF (for example `3M_2018_10K`).
- Generated files go in `data/processed/` (pages, chunks, embeddings). Never edit `data/financebench/`.

## Conventions that cause bugs

- `evidence_page_num` in FinanceBench is **0-based**. Store `page_index` (0-based) and `page_number` (1-based) on every page and chunk, and compare using `page_index`.
- The PDF page and the printed page number can differ in other filings. Check each new file.
- Filing amounts are in millions of USD. Brackets mean negative. The first year column is usually the newest. Confirm the column.
- Gold answers are rounded. Judge correctness with tolerance, and flag whether an item was "net income" or "net income attributable".
- Metadata (company, fiscal year, form type) must be on every chunk. Wrong-year retrieval is the biggest expected error source.

## Pipeline

```
PDF -> pages (pypdf) -> chunks + metadata -> embeddings -> index
question -> retrieve top-k -> prompt (answer only from text, cite pages, else "not found") -> LLM -> answer + pages
```

The baseline uses an **in-memory index**: chunks and embeddings live in a Python list/array, and search scores the question against every chunk. No database until Phase E (pgvector). Later phases replace pieces one at a time.

## Roadmap

The owner can spend 2 to 3+ hours a day, so the original 8-week guide ("SEC RAG Project Week 1 Guide and Cheat Sheets.md") is compressed to about 4 weeks. The eval harness is built early so every later experiment is cheap to score. Only phase A follows the guide directly. The rest is a proposal that the owner approved in outline; confirm details before starting each phase.

| Phase | Days | Build | Measure |
| --- | --- | --- | --- |
| A. Baseline | 1-3 | Exploration, PDF to pages, chunks (about 1,000 chars, 200 overlap), local embeddings (BGE or e5 via sentence-transformers), top-5 retrieval, local LLM answer via Ollama (about 8B model) | Questions answered end to end with page numbers |
| B. Eval harness | 4-5 | Fixed 20-question baseline, then a script that runs all 150 questions | Hit rate (recall@k), MRR, accuracy, faithfulness, LLM judge calibrated against hand grading. Do not tune on the 20 baseline questions. |
| C. Retrieval upgrades | 6-12 | Judge fixes first (done). Then, searching inside the known filing: BM25 + hybrid search (RRF), cross-encoder reranker, table-aware chunking and chunk-size sweep. Last step: switch to corpus-wide search (no `doc_name` given) and add metadata filtering (company, year, form type) and document routing | Gain per component. Corpus-wide numbers will drop, so report them as a new row, not as a change to the in-filing rows |
| D. Agent | 13-19 | LangGraph loop: query rewriting, decomposition, search tool, table lookup, calculator tool, abstain | Gain on multi-step and ratio questions |
| E. Polish | 20-28 | Citation check, final run with a hosted model (Claude), Postgres with pgvector, Boston add-on, Streamlit or CLI demo, README and short write-up | Final results table, faithfulness, wrong-answer rate |

Every row of the README table is: technique, config, hit rate, accuracy, and a short note on what failed.

## Resume lens

This is the owner's flagship project for co-op applications (first-semester MS AI student, Northeastern). That shapes priorities:

1. **Measured results** on a fixed benchmark, reported honestly. These become the resume bullets.
2. **Ablations**: one change at a time.
3. **Error analysis**: write up what still fails and why.
4. **Understanding**: the owner must be able to explain every component in an interview. Explain new concepts as we go, and keep `docs/notes.md` updated with them.
5. **Clean repo and demo**: tests, README results table, citations visible in a demo.

Do not add techniques (GraphRAG, fine-tuning) unless an observed failure justifies them.

## Research-backed experiments

Candidates for the comparison. Treat the claims as hypotheses to test here, not as facts. Most were read from search snippets, not full papers.

- **Structure-aware chunking** by filing element instead of fixed size: [Financial Report Chunking for Effective RAG](https://arxiv.org/pdf/2402.05131).
- **Document routing**: pick the right filing first, then retrieve chunks inside it. Targets cross-company and cross-year confusion: [Hybrid Document-Routed Retrieval for Financial RAG](https://arxiv.org/html/2603.26815).
- **Hybrid retrieval** (BM25 + dense with Reciprocal Rank Fusion) plus a **cross-encoder reranker**: compare with [Optimizing Retrieval Strategies for Financial QA](https://arxiv.org/abs/2503.15191).
- **HyDE** (embed a hypothetical answer instead of the question). Reference experiment on this benchmark: [financial-rag-lab](https://github.com/ikram4748/financial-rag-lab).
- **Agentic RAG** with corrective loops and tool use: [SoK: Agentic RAG](https://arxiv.org/pdf/2603.07379), [Rethinking Agentic RAG](https://arxiv.org/pdf/2605.27123).
- **Reranking for agents**: [Training Documents Reranker with Search Rubrics](https://arxiv.org/pdf/2608.03527).
- Original benchmark paper: FinanceBench, arXiv 2311.11944.

Before adding any technique, read the paper itself. Record in the README what was reproduced and what was not.

## Boston add-on

FinanceBench has no Boston-headquartered company with questions. Closest in the data: Boston Properties (one 2015 10-K, no questions) and CVS Health (Woonsocket, RI; 4 questions).

Plan, in Phase E at the earliest:
- Use `edgartools` (already a dependency) to download recent filings of Boston-area companies. Verify each company's headquarters before adding it.
- Write 20 to 30 gold questions with page evidence by hand. Keep them in `data/boston/`, separate from FinanceBench.
- Use FinanceBench for scored comparisons. Use the Boston set as a demo and as a check that the findings carry over to new filings.

## Working rules

- Python 3.14, managed with `uv`. Run everything with `uv run`, never bare `python`.
- Layout: library code in `src/`, one-off scripts in `scripts/`, tests in `tests/`. Lint with `ruff`, test with `pytest`.
- Keep the baseline simple. Add one technique per change so each result is attributable.
- Never print or commit `.env` or API keys. Hosted-model keys are only for the final run.
- Local models while building. Hosted model only for the final benchmark run.
- Keep `docs/notes.md` current: when a new concept or decision comes up, add a short plain-language explanation, and leave the "In my own words" prompts for the owner to fill in.
- Commit at the end of each work session with a descriptive message.
- If something fails, report the exact output. Wrong answers are data for the failure notes.
