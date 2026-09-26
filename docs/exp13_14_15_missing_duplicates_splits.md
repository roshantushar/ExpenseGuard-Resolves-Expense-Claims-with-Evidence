# Experiments 13, 14 and 15 — Missing information, duplicate detection, split transactions

**Code:** `scripts/exp13_14_15_history.py`, `src/history.py` · **Outputs:** `results/development/exp13_14_15/summary.json`, `exp15_rows.jsonl`, `results/plots/exp13_14_15_history.png`
**Data:** development + validation (80 cases). Only 13 missing-information, 10 duplicate-family and 7 split cases are in these splits, so every number below has a very small denominator.

## Important caveat: these rules were written after I saw the labels
For Exp 14 and 15 I inspected the ground-truth fields and reasons for the duplicate and split families (development and validation) before writing the logic: the 3-day gap for possible duplicates, the "monthly/recurring" rule for legitimate repeats, the treatment of an approval of another purpose as conflicting evidence. Scores of 80/80 and 7/7 on those steps are therefore **not an unbiased estimate**. The frozen final test (Exp 32) is the real check. The Exp 13 rules come from Exp 2, which were written from policy text and claims only, but the field-name matching (below) uses the dataset's vocabulary.

## Exp 13 — Missing-information detection (13 cases + 58 negative controls)
Requested field names are matched to the dataset vocabulary (origin, destination, attendee_count, external_attendee_names, business_amount, specific_business_purpose, ...) by keywords on the evaluator side; free-form names like `itemised_business_amount` map to `business_amount`.
| System | Correct REQUEST_INFORMATION | Field precision | Field recall | Exact field set | Unnecessary requests on other cases |
|---|---|---|---|---|---|
| Rules (Exp 2) | **13/13** | **1.00** | **0.81** | 9/13 | 0/58 |
| RAG + code facts, gpt-4o-mini | 5/13 | 1.00 | 0.24 | 1/13 | 0/58 |
| RAG + code facts, llama3.2:3b | 1/13 | 0.33 | 0.05 | 0/13 | 0/58 |

Rules ask for the right thing and never over-ask. The rules miss fields only where the policy wants several (for example both attendee names and count). The LLMs mostly do not ask at all (they reject or approve instead), which is the dominant failure, not vague requests.

## Exp 14 — Duplicate detection (80 cases: 10 duplicate-family, 5 legitimate repeats, 70 with no duplicate)
Class = EXACT_DUPLICATE, POSSIBLE_DUPLICATE, LEGITIMATE_REPEAT or NONE. "Positive" means exact or possible.
| Approach | Class accuracy | Duplicate precision | Duplicate recall | False positives on NONE | Legitimate repeats wrongly blocked | Duplicate-family disposition | Cost |
|---|---|---|---|---|---|---|---|
| A. exact match only | 72/80 | 1.00 | 0.40 | 0/70 | 0/5 | 7/10 | $0 |
| B. exact + fuzzy rules (same employee/merchant/currency, amount within 2%, date window) | 80/80 | 1.00 | 1.00 | 0/70 | 0/5 | 10/10 | $0 |
| C. B's candidates, gpt-4o-mini adjudicates | 78/80 | 1.00 | 0.60 | 0/70 | 0/5 | 8/10 | $0.0006 |
| C. B's candidates, llama3.2:3b adjudicates | 72/80 | 0.50 | 1.00 | 0/70 | **5/5** | 2/10 | $0 |

- Exact matching alone finds only 40% of duplicates: it catches the two identical bills and none of the three near-duplicates. Adding candidate generation fixes that.
- **Model adjudication did not beat the deterministic rules.** gpt-4o-mini missed two near-duplicates (called them repeats); llama flagged every legitimate monthly repeat as a duplicate (5/5 false blocks), which is exactly the failure the plan warns about.
- Similarity is never treated as fraud; the output is a claim-level class.
- The corpus gives no hard negatives: candidate generation finds no candidates outside the 25 duplicate and split cases (0/70 false positives is easy).

## Exp 15 — Split-transaction detection (7 split cases + 73 controls)
Pipeline: search previous expenses (same employee, merchant, project, currency, within 3 days, not a near-duplicate), combine amounts deterministically, convert to SGD with the frozen FX table, test the SGD 500 rule (APR-1.1), look up approval evidence.
| Metric | Result |
|---|---|
| Related-transaction retrieval | 7/7 correct |
| False links on non-split cases | 0/73 |
| Combined amount | 7/7 correct |
| Split precision / recall | 1.00 / **3/7** |
| Triggered policy correct | 3/7 |
| Disposition on split cases | 5/7 |

### Dataset inconsistency found (no change made)
Four of the seven split cases are labelled as exceeding the SGD 500 approval threshold when combined, but under the dataset's own frozen FX table they do not:
| Case | Combined | In SGD | Label says |
|---|---|---|---|
| EXP-0082, EXP-0085 | JPY 54,000 | 491.4 | threshold exceeded (APR-1.1) |
| EXP-0086, EXP-0089 | INR 17,500 | 283.5 | threshold exceeded (APR-1.1) |
The three SGD cases (SGD 570) are consistent. The pipeline is therefore penalised on those four cases by the labels, not by an error in the arithmetic: the two INR cases still get the right disposition (ESCALATE) through the approval-conflict rule, but the two JPY cases get the wrong one. I recommend reviewing the intended thresholds (or FX) for non-SGD split cases before the final test; I have not changed the dataset.

## Decisions
- Use deterministic candidate generation for duplicates and splits in the final system; keep the LLM out of duplicate adjudication unless a case is genuinely ambiguous, and never with the 3B local model.
- Missing-information detection belongs in rules. The LLM prompts need explicit "ask for exactly the missing field" handling if kept.
- Next: Exp 16 (enterprise-evidence oracle), Exp 17 (typed read-only tools with unit tests), Exp 18 (fixed workflow, the main agent-feasibility gate).
