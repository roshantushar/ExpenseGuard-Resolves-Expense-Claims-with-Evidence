# Experiment 3 — Generic LLM without company policy

**Question:** Can a generic model make reliable expense decisions with no policy grounding?
**Code:** `scripts/exp03_no_policy.py`, `src/llm_exp.py` · **Outputs:** `results/development/exp03_no_policy/`, `results/plots/exp03_no_policy_development.png`
**Config:** claim only (no policy, no tools, no ground truth), temperature 0, JSON output, 60 development cases. Models: gpt-4o-mini (OpenRouter), llama3.2:3b (local).

## Results (development, n = 60)
| Model | Correct | Wilson 95% | False approvals | Predictions | Explanations asserting a rule/limit* | Cost | Median latency | Tokens in/out |
|---|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 16/60 = 26.7% | 17.1–39.0% | 0/39 | 52 REJECT, 7 REQUEST_INFO, 1 ESCALATE | 31.7% | $0.0048 | 1.5 s | 20.7k / 2.8k |
| llama3.2:3b | 14/60 = 23.3% | 14.4–35.4% | 26/39 (67%) | 36 APPROVE, 24 REJECT | 43.3% | $0 | 1.2 s | 21.6k / 3.4k |

*Heuristic keyword match on the explanation (policy, limit, ceiling, threshold, exceed, allowed, permitted, standard). Neither model cited clause IDs, so the ID-based "unsupported policy" rate is 0% and uninformative.

## Findings
- **Grounding is needed.** Both models are close to chance-level usefulness. gpt-4o-mini's 0 false approvals is misleading: it never approved anything (52/60 rejected), so it got 0 of the 21 approvable claims right. It is safe only because it refuses everything.
- **Llama approves freely:** 36/60 approvals and 26 false approvals.
- **Unsupported assertions:** explanations invent rules ("alcohol is typically not reimbursable under standard company policies"). gpt-4o-mini still got temporal (3/3) and regional (5/5) cases right, probably by rejecting them for other reasons.
- Missing-information, evidence-conflict, split and workflow families are near 0 for both models.

## Note on the log
Exp 3 was run twice. The second run added the text-assertion metric and was served from cache (no new spend). The first run's rows remain in `run_log.jsonl` under an earlier `run_id`; use the later one.

## Decision
Policy grounding is required. Proceed to Exp 4.
