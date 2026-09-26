# Experiments 30 and 31 — Selective router and cost-to-serve

**Code:** `src/router.py`, `scripts/exp30_31_router_cost.py` · **Outputs:** `results/development/exp30_31/summary.json`, `results/plots/exp30_31_router_and_cost.png`. Development + validation, 80 cases.

## Exp 30 — Selective architecture router
`route(claim)`: claim-only categories go to the deterministic rules (no tools); hotel, software and any claim with a prior expense by the same employee and merchant go to the fixed tool workflow. There is no agent branch (Exp 19). The plan's third strategy, "agent for everything", was **not built or run** because the audit did not justify an agent, so it is absent from the table.

| Strategy | Correct (n = 80) | False approvals | Human review | Model cost | Median / P95 latency |
|---|---|---|---|---|---|
| LLM everywhere, gpt-4o-mini RAG + facts | 40 (50.0%) | 4/54 | 1.3% | $0.0213 | 1.79 s / 2.88 s |
| LLM everywhere, llama3.2:3b RAG + facts | 35 (43.8%) | 24/54 | 0% | $0 | 3.58 s / 4.94 s |
| rules everywhere | 63 (78.8%) | 7/54 | 16.3% | $0 | 0.02 ms / 0.11 ms |
| workflow everywhere | **73 (91.3%)** | 4/54 | 2.5% | $0 | 0.07 ms / 0.28 ms |
| **selective router** | **73 (91.3%; Wilson 83.0–95.7%)** | 4/54 | 2.5% | $0 | 0.05 ms / 0.21 ms |

- The router routes 39 claims to rules and 41 to the workflow; 51% of claims use tools, average 1.06 tool calls per claim; **0% invoke an agent** (nothing to invoke).
- **The router matches the workflow exactly.** Tool calls are in-memory lookups worth microseconds, so skipping them on claim-only claims saves nothing measurable; routing is still the right shape for a deployment where tools are real services with latency and cost.
- **The finding is Outcome B:** rules cover claim-only cases, a fixed workflow covers enterprise-evidence cases, and no LLM or agent is needed at this scale. The LLM paths cost 5 orders of magnitude more time and reach 44–50%.
- Development and validation are not clean holdouts for the workflow (see Exp 18); the frozen final test is.

## Exp 31 — Cost-to-serve
**Measured** quantities: model/embedding cost per claim, tokens, latency, Human Review Rate, correct rate, Request-Information rate. **Assumed** quantities (labelled, editable in the script): 10 minutes of analyst review per human-reviewed claim at $40/hour ($6.67 per review), fixed monthly costs of $200 (hosting $100, storage $20, monitoring $50, evaluation runs $30), and that manual review is 100% accurate. None of these is measured; the results are scenario models, not savings.

Measured AI cost per claim: LLM path $0.000268 (gpt-4o-mini generation plus one voyage query embedding of about 100 tokens); rules and workflow $0.

| Strategy | Human review rate | Request-information rate | Wrong dispositions per 10,000 claims | Modelled monthly cost at 1k / 10k / 100k claims |
|---|---|---|---|---|
| manual review only (assumed 100% accurate) | 100% | n/a | 0 (assumed) | $6,667 / $66,667 / $666,667 |
| LLM everywhere (gpt-4o-mini) | 1.3% | 13.8% | **5,000** | $284 / $1,036 / $8,560 |
| rules everywhere | 16.3% | 23.7% | 2,125 | $1,283 / $11,033 / $108,533 |
| workflow / router | 2.5% | 25.0% | **875** | $367 / $1,867 / $16,867 |

**Read this table carefully.** The modelled cost only prices human review and fixed costs, so the LLM path looks cheapest (about $1,036 a month at 10k claims, against $1,867 for the workflow). It is cheap because it resolves claims automatically, but **half of its dispositions are wrong (5,000 per 10,000 claims, against 875)**. The plan's cost model does not price errors (wrong approvals, rework, employee follow-ups), and I have not invented a price for them; a fair comparison must put the wrong-disposition column beside the cost column. Any error cost above roughly $0.20 per wrong claim erases the LLM path's apparent advantage against the workflow at 10k claims a month.
Sensitivity to review time (5/10/20 min) and analyst cost ($30/40/60 per hour) is in `summary.json` (`sensitivity_10k_claims`); the ranking of workflow versus rules is unchanged across it, and the LLM path stays cheapest on this narrow cost definition throughout.

## Decisions
- Final architecture candidate: **rules + fixed tool workflow (router)**, deterministic, $0 model cost, 91% on development + validation.
- Before the frozen final test the open items for you are the label questions raised in Exp 15, 18 and 19 (currency-threshold cases; the "neither exception nor conference" hotel branch). I have not changed any logic or data to fit labels.

## Addendum (post-freeze-decision numbers)
After the hotel-branch change described in `exp32_freeze_and_runbook.md`, the router scores 76/80 (95.0%, Wilson 87.8-98.0%) on development + validation with human review 6.25%, 4/54 false approvals, and about 500 wrong dispositions per 10,000 claims; modelled monthly cost at 10k claims about $4,366 (the extra human review is the reason it rose from about $1,867). These dev/val numbers are no longer independent; the final test is.
