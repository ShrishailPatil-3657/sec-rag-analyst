# Judge rules (draft, collected during hand grading)

Working list for building the LLM judge in Phase B step 5. Each rule says where it came from.
Rules marked "pending" are my suggestions that the owner has not confirmed yet.

## Answer correctness
1. **Numbers:** match within 1% relative, or equal after rounding to the gold answer's precision. Handle units ($1.6 billion = 1,577 million rounded; thousands vs millions) and brackets (negative). The answer may contain LaTeX (item 2); the judge must read it.
2. **Three verdicts, not two:** `correct`, `incorrect`, `not_found`. A "not found" is an abstention, not a wrong answer, and the report shows all three rates. (CONFIRMED by owner; from items 3 and 4)
3. **State the final quantity asked.** Giving only the components (two $4.2B facilities, no $8.4B total) is incorrect. (CONFIRMED by owner; item 5, graded n)
4. **Flag the line item:** "net income" vs "net income attributable" (CLAUDE.md).

## Faithfulness ("supported")
5. Supported = the pages the model was given contain the answer, or the numbers needed to compute it. A wrong answer can still be supported, and a right answer can be unsupported. (items 3, 4, 5)
6. The judge needs the retrieved chunk text. `run_eval.py` does not save it today; either save it in the run file or recompute it by searching again.

5b. **Right answer, wrong reason (item 6):** accuracy and faithfulness are separate scores. A correct answer is not "supported" just because it is correct. Yes/no questions can be right by luck, so the judge must check that the pages given actually show the claim. Item 6 (Amex retention): answer "Yes" matched gold, but the pages given had no retention evidence, so correct = y, supported = n.

5c. **Comparison questions (largest, highest, biggest) (item 7):** an answer is only supported if the pages given include all the candidates. A maximum over an incomplete list is unsupported, and a confident wrong answer is worse than not_found. Item 7 (Amex largest liability): answered long-term debt $42,573M; the balance sheet with customer deposits $110,239M was not retrieved.

## Citations
7. Track citation correctness separately from answer correctness. Item 1: right value, but it cited page 53 while the value is on page 52. The prompt labels chunks with `page_number` (1-based PDF position), not the printed footer number; filings differ (Boeing gap 2, AES gap 3, Adobe 2016 none).

## Failure type (for the report)
8. Label each failed question: retrieval miss (gold page not in top 5), abstain, or wrong/incomplete answer despite good retrieval.

## Generation prompt, not judge (to test separately)
9. Questions like "if not outlined, state 0" conflict with our rule "reply exactly: not found" (item 3, AES). Test: give the model the gold page and see if it answers 0 or still abstains. Not yet run.

## Page conventions to remember when checking
10. `evidence_page_num` is 0-based PDF position. Sheet labels are `page_number` = index + 1. Printed footer numbers differ.

## Calibration bookkeeping
11. All 12 items were graded by the owner (`data/eval/hand_grades.csv`). Claude independently graded items 8 to 12 (`data/eval/hand_grades_claude.csv`) and agreed on all five (correct and supported). Calibration set = the owner's 12 grades; 12 is small (each item is about 8 points of agreement), so say so.
12. Owner CSV fixed: notes are quoted, 12 rows parse cleanly.

## Gold-answer quirks (grade against the gold, but record them)
13. **"Restructuring costs in the income statements, else 0" (items 3 and 10).** AES gold = 0 (no such line on the income statement). PepsiCo gold = $411M, taken from Note 3 even though PepsiCo's income statement also has no restructuring line. A literal reading would give 0 for both. The judge grades against the gold, and the report should list such questions as "gold follows a looser reading than the question wording".

## Judge calibration result (judge frozen 2026-11-11)
Judge: local `qwen3:8b`, temperature 0, prompt in `src/sec_rag_analyst/judge.py`; `not_found` is set by code (`is_not_found`), not by the LLM.
Compared with the owner's 12 hand grades (`scripts/calibrate_judge.py`):
- agreement on `correct`: **12/12**
- agreement on `supported`: **10/12** (first prompt: 8/12)
- remaining disagreements: item 5 (PepsiCo, judge too strict: will not accept two figures that add up to the total) and item 6 (Amex retention, judge too lenient: accepts loosely related evidence).
Caveats: the prompt was changed twice while looking at these same 12 items, so the numbers are optimistic; 12 items is small (one item is about 8 points). The `supported` score is the weaker one and should be reported with this caveat. Later: hand grade about 10 unused answers as a fair check, and try a stronger local model.
