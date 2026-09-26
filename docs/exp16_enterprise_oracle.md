# Experiment 16 — Enterprise-evidence oracle

**Code:** `scripts/exp16_enterprise_oracle.py` · **Outputs:** `results/development/exp16/summary.json`, `results/plots/exp16_enterprise_oracle.png`
**Cases:** the 37 evidence-dependent development + validation cases (fixed workflow, dynamic agent-candidate, split, duplicate families).
**Oracle:** the evaluator picks the records each case needs (from the ground truth's required tools), runs them through the real tools, and supplies the results to the LLM together with RAG excerpts and code-computed facts. Evaluation-only.

## Results (correct / 37; false approvals among 19 non-approvable)
| System | Correct | False approvals |
|---|---|---|
| gpt-4o-mini, no enterprise records (Exp 12) | 11 | 2/19 |
| **gpt-4o-mini + oracle records** | **16** | **0/19** |
| llama3.2:3b, no enterprise records (Exp 12) | 18 | 7/19 |
| llama3.2:3b + oracle records | 18 | 5/19 |
| rules only (Exp 2) | 20 | 7/19 |
| **fixed workflow (Exp 18)** | **30** | 4/19 |

## Interpretation
Supplying the exact records helps gpt-4o-mini (11 → 16) and lowers its false approvals, but even with every required fact in front of it the LLM is right on under half the cases, while a fixed if/else workflow using the same records reaches 30 of 37. **Tool retrieval is not the bottleneck; applying the evidence to the policy is.** Llama does not improve at all (18 → 18). Cost was $0.011 for both models. Sample size is small (37), so differences of a few cases are noise; the 14-case gap to the workflow is not.
