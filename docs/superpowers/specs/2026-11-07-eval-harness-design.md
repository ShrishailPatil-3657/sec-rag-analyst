# Phase B: Eval harness design

## Intent
Give every change to the RAG system a comparable number. The harness runs a fixed set of FinanceBench questions through the pipeline, scores retrieval and answers automatically, and logs each run with its settings. The owner is learning: each piece is explained in plain language, and the owner writes the core scoring logic (see "Who writes what").

## Goals
- Retrieval scores that need no LLM: hit rate (any), full recall (all), average fraction, MRR.
- Answer scores: accuracy and faithfulness, from an LLM judge that is checked against hand grading.
- One command runs a question set and writes a result file that records the config.
- A report that lists failures per question, not only averages.
- Notes in `docs/notes.md` for each new concept.

## Non-goals
- No new retrieval techniques (Phase C). No agent (Phase D). No hosted model (final run only).
- No whole-corpus search yet. The baseline searches inside the known filing.

## Anti-goals
- Tuning on the held-out set. A score that cannot be reproduced. A judge nobody checked.

## Decisions made with the owner
- **Split of the 150 questions:** about 100 dev, 50 held-out. Random with a fixed seed, balanced across the three `question_type` groups. Saved to `data/eval/split.json` and never regenerated.
- **Quick-debug subset:** 20 to 35 questions taken from the dev set, saved to the same file.
- **Held-out use:** not looked at while experimenting. Run only at the end of a phase; reported in the README.
- **Baseline scope:** search inside the filing named by `doc_name`. Routing across filings is Phase C.
- **Multi-page evidence (35 questions):** per question, record the fraction of evidence pages found in the top k. Report hit rate (any), full recall (all) and the average fraction. Headline hit rate is "any".
- **Comparing runs:** one change at a time; look at which questions flipped, not only totals. Noise is large (about 15 points on 50 questions, 10 on 100), so say so in the README.

## Components
1. **Split script** (`scripts/make_split.py`) writes `data/eval/split.json`.
2. **Corpus prep:** extract pages, chunk and embed the filings the questions use (84 filings; 2 are done).
3. **Retrieval metrics** (`src/sec_rag_analyst/metrics.py`): compare retrieved `page_index` values with `evidence_page_num` (0-based).
4. **Runner** (`scripts/run_eval.py`): for each question, retrieve top 5, generate an answer, save question, retrieved pages, answer and config to `data/processed/runs/<run_id>.jsonl`.
5. **Judge** (`src/sec_rag_analyst/judge.py`): an LLM decides whether the answer matches the gold answer within rounding tolerance, and whether the answer is supported by the retrieved text.
6. **Judge calibration:** the owner hand-grades 10 to 15 dev answers; we report agreement with the judge and fix the judge prompt if it is low.
7. **Report** (`scripts/report.py`): metrics table plus the list of failed questions with their type.

## Constraints
- `page_index` (0-based) for all comparisons. Gold answers are rounded: use tolerance and note "net income" vs "attributable".
- Local models only (Ollama `qwen3:8b`, temperature 0). Run with `uv run`. Never print or commit keys.
- Every run file records: chunk size and overlap, embedding model, k, generation model, prompt version, split name and git commit.

## Who writes what
The owner writes the core logic (metrics, matching rules, judge prompt). Claude explains each concept first, scaffolds files and tests, and reviews.

## Left to the builder (my calls, owner can change)
- Judge model: the same local `qwen3:8b` for now. A different local model is possible if agreement is poor.
- Numeric tolerance: 1% relative or rounding to the gold answer's precision.
- Run file format: JSON Lines.

## Order of work
1. Split file. 2. Retrieval metrics on the two filings that exist (tests first). 3. Prepare the other filings. 4. Runner on the quick-debug subset. 5. Judge and hand calibration. 6. Full dev run and report. 7. Held-out run once, for the baseline row.

## Open questions
None blocking. Corpus prep time for 82 filings is unknown until measured.
