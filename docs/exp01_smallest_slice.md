# Experiment 1 — Smallest end-to-end feasibility slice

**Question:** Can one claim travel through the whole system and produce a valid structured output?
**Script:** `scripts/exp01_slice.py` · **Outputs:** `results/development/exp01/` (predictions per model, `summary.json`), `results/plots/exp01_slice.png`

## Configuration (frozen)
- 10 DEVELOPMENT cases from the self-contained group, picked deterministically (first by case id per decision quota 3 APPROVE / 3 REJECT / 3 REQUEST_INFORMATION / 1 ESCALATE, filled to 10). The ESCALATE and some REQUEST_INFORMATION cases are not in the self-contained group, so the actual mix is 3 APPROVE / 4 REJECT / 3 REQUEST_INFORMATION.
- No retrieval, workflow or agent. The harness passes the required policy clauses straight to the model (evaluator-supplied, so this is an oracle input used only for feasibility, not a runtime design).
- Temperature 0, JSON output, schema `{decision, policy_evidence, missing_fields, explanation}`.
- Models: `openai/gpt-4o-mini` (OpenRouter) and `llama3.2:3b` (local Ollama, free).

## Results (n = 10)
| Model | Correct | Wilson 95% | Schema-valid | False approvals | Median / P95 latency | Tokens in / out | Cost |
|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 3/10 | 10.8–60.3% | 10/10 | 0/7 | 1.96 s / 2.73 s | 4748 / 709 | $0.0011 |
| llama3.2:3b | 4/10 | 16.8–68.7% | 10/10 | 2/7 | 1.67 s / 2.94 s | 4929 / 690 | $0 |

The 3 vs 4 gap is not meaningful at n = 10. Total OpenRouter spend so far: about $0.0011 of the $3.50 cap.

## Conclusion on feasibility
The pipeline works end to end: both models returned schema-valid output for 10/10 cases with no errors. This experiment says nothing about headline performance.

## Failure patterns seen (gpt-4o-mini, even with the correct clauses supplied)
- **Per-person arithmetic:** three cases (JPY 8,800 for two employees against a per-person ceiling) were rejected because the model compared the total to the per-person limit. This is what Exp 2 and Exp 12 (deterministic arithmetic) are meant to address.
- **Evidence conflict:** bill says restaurant, description says taxi. Expected `REQUEST_INFORMATION`; the model chose `REJECT` in both cases.
- **Missing information:** the model rejected instead of asking for `origin` / `destination`.
- **Llama 3.2 3B** made 2 false approvals out of 7 non-approvable cases, versus 0 for gpt-4o-mini.

## Dataset observation (no change made)
Only 58 distinct claim texts exist across the 120 cases (max 8 repeats of the same claim). Templated cases mean the effective sample size is smaller than 120, and repeated templates in development and final test are worth remembering when reading confidence intervals.

## Decision
Feasibility gate passed. Next: Exp 2 (deterministic rules baseline, no LLM), then Exp 3 and Exp 4.
