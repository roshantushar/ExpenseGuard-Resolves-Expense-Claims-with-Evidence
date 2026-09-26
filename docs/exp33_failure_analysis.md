# Experiment 33 — Final failure analysis

**Code:** `scripts/exp33_failure_analysis.py` · **Outputs:** `results/final/exp33/failures.json`, `results/plots/exp33_final_failures.png`
One primary category per incorrect prediction, from the plan's taxonomy. Categories for the primary system were assigned by rule and checked by hand; for the three baselines the same rule was applied and is heuristic (arithmetic and retrieval errors inside the LLM baselines are not separately diagnosed).

## Primary system (router): 2 failures out of 40
| Case | Family | Expected → predicted | Category | Note |
|---|---|---|---|---|
| EXP-0088 | split transaction | REQUEST_INFORMATION → APPROVE | SPLIT_TRANSACTION_MISS | Related purchase found and combined correctly (JPY 54,000), but the combined amount is SGD 491 at the frozen rate, below the SGD 500 threshold, so no approval was demanded. Currency-flagged in advance. |
| EXP-0092 | fixed workflow (challenge) | ESCALATE → APPROVE | FAILED_TO_ESCALATE | JPY 1,200 software subscription (SGD 11) treated as below the approval threshold; the label applies the SGD 1,000 rule to the raw number. Currency-flagged in advance. |
Both are false approvals and both trace to the same root cause: SGD-equivalent thresholds versus labels that apply thresholds to the raw amount. In the system's own terms these are confident decisions near a threshold expressed in a different currency, which is exactly the situation the enterprise practice discussed earlier would send to a human. A near-threshold review band was **not** part of the frozen system and was not tried.

## Baselines
| Category | router | rules only | gpt-4o-mini + facts | llama3.2:3b + facts |
|---|---|---|---|---|
| SPLIT_TRANSACTION_MISS | 1 | 2 | 3 | 2 |
| FAILED_TO_ESCALATE | 1 | 1 | 3 | 3 |
| MISSING_FIELD_ERROR | 0 | 1 | 5 | 11 |
| OVER_ESCALATION | 0 | 5 | 0 | 0 |
| DUPLICATE_FALSE_NEGATIVE | 0 | 0 | 1 | 2 |
| REASONING_ERROR | 0 | 0 | 3 | 8 |
| POLICY_PRECEDENCE_ERROR | 0 | 0 | 0 | 2 |
| WRONG_POLICY_VERSION | 0 | 0 | 0 | 2 |
| **Total** | **2** | **9** | **15** | **30** |

- **Rules only** failed mostly by over-escalating hotel claims it cannot verify (5 of 9): exactly the gap the tool workflow closes.
- **gpt-4o-mini** failed mainly by not asking for missing information (5), missing splits (3) and failing to escalate (3), and by reasoning errors (3); it made a single false approval.
- **llama3.2:3b** failed across the board: 11 missing-field errors, 8 reasoning errors, wrong-version and precedence errors, and 17 false approvals.
- Not observed for any system: retrieval-specific categories, tool errors, loops, prompt injection or system errors (categories that need an agent or that the baselines do not expose). The plan's example wording applies: instead of "95% correct", the primary system's failures were two threshold-currency false approvals.
