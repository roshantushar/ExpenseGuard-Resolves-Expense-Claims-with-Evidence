# Experiment 4 — Full-policy long-context baseline

**Question:** If the whole policy corpus fits in context, is RAG necessary?
**Code:** `scripts/exp04_long_context.py` · **Outputs:** `results/{development,validation}/exp04_long_context/`, `results/plots/exp04_long_context_{development,validation}.png`
**Config:** claim + all 12 policy source documents verbatim (about 6.8k tokens; the corpus is smaller than I first estimated at 15–20k), temperature 0, one prompt version, no tuning. Same policy prefix for every case. Llama run with a 16k context window.

## Results
| Split | Model | Correct | Wilson 95% | False approvals | Human review | Schema-valid | Wrong-version cases | Cost | Median / P95 latency |
|---|---|---|---|---|---|---|---|---|---|
| Dev (60) | gpt-4o-mini | 19 (31.7%) | 21.3–44.2% | 1/39 | 1.7% | 60 | 2 | $0.0315 | 1.95 s / 2.55 s |
| Dev (60) | llama3.2:3b | 20 (33.3%) | 22.7–45.9% | 13/39 (33%) | 0% | 55 | 9 | $0 | 3.4 s / 14.0 s |
| Val (20) | gpt-4o-mini | 3 (15.0%) | 5.2–36.0% | 0/15 | 0% | 20 | 1 | $0.0101 | 1.97 s / 2.34 s |
| Val (20) | llama3.2:3b | 9 (45.0%) | 25.8–65.8% | 3/15 | 0% | 19 | 2 | $0 | 3.0 s / 11.9 s |

Tokens: about 354k input per 60 cases (about 5.9k per case) for both models. Rules baseline for comparison: 47/60 on development at $0 and 0.02 ms.

## Findings
- **Long context does not rescue the LLM.** gpt-4o-mini goes from 26.7% (no policy) to 31.7% with the full corpus; the difference is inside the confidence intervals. Rules score 78%.
- **Failure mode is over-asking.** gpt-4o-mini predicted REQUEST_INFORMATION 34 times out of 60, including 17 of 21 approvable claims. It is safe (1 false approval) but sends most clean claims back to the employee.
- **Small model cannot use a long policy.** Llama produced 5 schema-invalid outputs on development, 9 wrong-version citations, 33% false approvals and P95 latency of 14 s.
- **Not a context problem.** In Exp 1, gpt-4o-mini given only the correct clauses also got 3/10. The bottleneck looks like applying the policy (per-person arithmetic, thresholds, deciding what counts as missing), not finding it. This supports a hybrid where code does the arithmetic (Exp 12).
- **Wrong-version rate is low for gpt-4o-mini** (2/60 development), so year confusion is not its main failure here.

## Caveats
- One prompt, no iteration. A prompt that tells the model not to ask for information unless a clause requires it could move these numbers; I did not tune, so as not to overfit development.
- Small samples, and the dataset is templated (58 distinct claim texts), so intervals are wide.
- The corpus is small (about 6.8k tokens). Conclusions about scaling to larger corpora are out of scope.

## Decision gate
RAG must later show a gain over this baseline in accuracy, false approvals, cost, latency, traceability or version precision. Long context is cheap at this size (about $0.0005 per case), so the case for RAG rests on precision and traceability, not cost. Next: Exp 5 (naive RAG), which needs an embedding model.
