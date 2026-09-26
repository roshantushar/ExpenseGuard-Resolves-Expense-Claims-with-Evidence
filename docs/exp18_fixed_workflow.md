# Experiment 18 — Fixed workflow baseline (the agent-feasibility gate)

**Code:** `src/workflow.py`, `scripts/exp18_workflow.py`, `src/history.py`, `src/tools.py` · **Outputs:** `results/{development,validation}/exp18/`, `results/plots/exp18_workflow.png`. Tool calls are logged one row each (`type: tool_call`) in `run_log.jsonl`.
**Cost:** $0, no LLM. Median latency 0.05 ms per case.

## Design (no model, fixed order, branching only by if/else on tool observations)
1. Claim-level rules (Exp 2).
2. `search_previous_expenses` for every claim → exact duplicate → REJECT; near-duplicate → REQUEST_INFORMATION; related same-day purchases → combined amount (FX to SGD) → APR-1.1 → approval lookup (approval for combined spend → APPROVE; approval of another purpose → ESCALATE as conflicting evidence; none → REQUEST_INFORMATION).
3. Hotel: employee grade → travel request → (if the claim cites an exception) exception record → base ceiling → exception record from the travel request, or conference registration for the partner-hotel ceiling.
4. Software: FX-converted amount → manager approval → project status when above SGD 1000.

## Results
| Split | Correct | Wilson 95% | False approvals | Human review | Avg tool calls | Required tools covered |
|---|---|---|---|---|---|---|
| Development | **57/60 (95.0%)** | 86.3–98.3% | 2/39 | 3.3% | 1.53 | 19/27 |
| Validation | **16/20 (80.0%)** | 58.4–91.9% | 2/15 | 0% | 1.60 | 8/10 |
| Combined | **73/80 (91.3%)** | | 4/54 (7.4%) | | | |
| Rules only, combined | 63/80 (78.8%) | | | | | |

By family (development, workflow vs rules): fixed-workflow 6/8 vs 3/8, dynamic 6/7 vs 1/7, split 5/5 vs 3/5, all claim-only families unchanged at 100%. Validation: workflow 2/2 and 1/3 on the fixed and dynamic families.

## Version history (be careful reading the validation number)
- **v1 (first pass):** development 52/60, validation 14/20. In v1 I had added a rule that escalated hotel claims on closed projects or projects not allowing travel. **The policy corpus says nothing about that**; I invented it, and it was wrong on all three affected cases.
- **v2 (current):** removed the invented project rule; check a cited exception before requiring a travel request (dev misses); route duplicate and split logic through the search tool. Development 57/60, validation 16/20.
- The changes were motivated by **development** errors, but I also saw the validation errors of v1, so validation is no longer a clean estimate. Final test is the clean check.

## Remaining errors (7 of 80)
- **Currency-threshold labels (4 cases):** EXP-0098 and EXP-0104 are software subscriptions of JPY 1,200 that the labels treat as exceeding the SGD 1,000 rule (JPY 1,200 is about SGD 11 at the frozen rate); EXP-0082 and EXP-0085 are the JPY split cases from Exp 15. Same inconsistency as Exp 15: thresholds appear to be applied to the raw number, not the FX-converted amount. I followed the policy text and did not change the dataset.
- **Hotel over ceiling with neither exception nor conference (3 cases: EXP-0120, EXP-0111, EXP-0114):** the workflow REJECTs; the labels say ESCALATE in all three. The policy does not say which is correct, so I have not added a rule to fit three labels.

## Agent-necessity signal (feeds Exp 19)
The 15 agent-candidate cases in these splits are 7/10 correct with a fixed if/else workflow (6/7 dev, 1/3 val); the branch "travel record has event_id → conference lookup, has exception_id → exception lookup" is a plain conditional on the first observation. All three failures are the policy-ambiguity pattern above, not a sequencing problem. Nothing so far requires model-directed tool selection.

## Addendum (v3, before the final-test freeze)
The over-ceiling hotel branch with neither an exception nor a conference now ESCALATEs (GEP26-4.1); see `exp32_freeze_and_runbook.md` for the reasoning and the disclosure that this was prompted by three dev/val labels. Development 58/60, validation 18/20, combined 76/80. The four remaining misses are the currency-threshold cases, which are flagged rather than fitted. v1 and v2 results above are historical.
