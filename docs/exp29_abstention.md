# V2 Exp 29 — Abstention and escalation behaviour ($0, evaluator-side)

Notebook: `notebooks/v2/exp29_abstention.ipynb` (results live only in this notebook's own executed cell
outputs -- no separate `results/v2/` export exists for this experiment; a prior version of this line
cited `results/v2/development/exp29_abstention/`, which was never written). Cost: $0 (reuses saved
predictions and the run log from Exp 2, 9, 12, 12B, 18). Kept separate from Exp 28's security audit.

**Risk-coverage table (development, 70 claims):**

| System | Auto-resolution | Accuracy on auto-resolved | HRR (escalation rate) | Missed-escalation | Over-escalation | FA among auto-resolved |
|---|---|---|---|---|---|---|
| 2c rules = R0 | 84.3% | 62.7% | 15.7% | 35.3% | 0% | 6/41 |
| H0 RAG+M4 | 95.7% | 29.9% | 4.3% | 88.2% | 1.4% | 0/49 |
| H5 full hybrid | 80.0% | 39.3% | 20.0% | 35.3% | 4.3% | 2/38 |
| workflow_v2 | 85.7% | 60.0% | 14.3% | 47.1% | 1.4% | 7/42 |
| R1 escalate-all-unresolved | 34.3% | 83.3% | 65.7% | 5.9% | 42.9% | 0/23 |
| **R2 LLM-on-residual** | 80.0% | 53.6% | 20.0% | 23.5% | 1.4% | **0/39** |

**Findings:** the RAG/hybrid systems auto-resolve almost everything but are guessing, not abstaining — poor accuracy (30–39%) on what they auto-resolve and severe missed-escalation (35–94%). R1 is the plan's "safe but useless" pattern: missed-escalation drops to 5.9%, but HRR balloons to 65.7%.

**The headline quantification:** of the 36 internally-unresolved claims (Exp 12B), R0's forced answer would be wrong on **18** — a 50% error rate on exactly the claims flagged as uncertain, validating the signal. **R1 captures all 18 genuine errors but at the cost of 18 unnecessary reviews (1:1 ratio).** **R2 fixes 7 of the 18 outright and wastes only 1 unnecessary review** — a far better trade. R2 also has 0 false approvals among its auto-resolved cases, versus 6/41 for R0 and 7/42 for workflow_v2.

**Decision:** abstention earns its cost only in R2's shape (abstain-then-adjudicate), not R1's (abstain-then-defer-blindly). Exp 30 should build the final architecture on R2's pattern: deterministic decision where conclusive, LLM adjudication for the residual, human review reserved for the residual's own genuine escalations.
