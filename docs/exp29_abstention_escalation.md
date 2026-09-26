# Experiment 29 — Abstention and escalation behaviour

**Code:** `scripts/exp29_abstention.py` (computed from saved predictions on development + validation, 80 cases; no new model calls) · **Output:** `results/development/exp29/summary.json`, `results/plots/exp29_abstention.png`
**Definitions:** escalated = ESCALATE; abstained = ESCALATE or REQUEST_INFORMATION; auto-resolved = APPROVE or REJECT. "Cases needing review" = cases whose correct answer is ESCALATE or REQUEST_INFORMATION (29 of 80). Always paired with the human-review load.

| System | Escalation rate | Abstention rate | Error rate among auto-resolved | Abstained on cases needing review | Unnecessary escalations | Correct rate |
|---|---|---|---|---|---|---|
| rules (Exp 2) | 16.3% | 40.0% | 7/48 | 22/29 | 10/13 | 78.7% |
| **fixed workflow (Exp 18)** | **2.5%** | 27.5% | 7/58 | **22/29** | **0/2** | **91.2%** |
| gpt-4o-mini, RAG + facts (Exp 12) | 1.3% | 15.0% | 40/68 | 12/29 | 0/1 | 50.0% |
| llama3.2:3b, RAG + facts (Exp 12) | 0% | 1.3% | 45/79 | 1/29 | 0/0 | 43.8% |
| gpt-4o-mini, full policy (Exp 4) | 1.3% | 61.3% | 18/31 | 14/29 | 1/1 | 27.5% |
| always escalate (control) | 100% | 100% | n/a | 29/29 | 73/80 | 8.7% |

## Findings
- **The always-escalate control is safe and useless** (8.7% correct, 100% human review), as the plan warned; every real system is judged against it.
- **The workflow abstains where it should**: 22 of the 29 cases that need employee input or Finance review, with only 2.5% escalations and no unnecessary ones. Its remaining errors are all confident decisions on the three hotel cases and four currency-threshold cases discussed in Exp 18/19; none of its 7 errors was an abstention.
- **LLMs almost never abstain when they should**: llama abstained on 1 of 29 (it approved or rejected nearly everything); gpt-4o-mini with facts on 12 of 29. Their errors are mostly confident (40 of 68 and 45 of 79 auto-resolved answers wrong), which is the dangerous pattern.
- **gpt-4o-mini with the full policy abstains a lot (61%) but mostly for the wrong reasons**: 40 of its 58 errors were unnecessary requests for information rather than escalations, which pushes work back to employees.
- **Escalation recall is low everywhere** (workflow 2 of 7, rules 3 of 7). The seven cases labelled ESCALATE are dominated by the ambiguous cases (hotels with neither exception nor conference, the currency-threshold software and split cases), where the deterministic logic follows the policy text and the labels ask for human review.
