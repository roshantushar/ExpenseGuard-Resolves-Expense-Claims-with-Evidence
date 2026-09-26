# Experiment 7 — Top-K sensitivity

**Code:** `scripts/exp07_topk.py`, `src/retrievers.py`, `src/retrieval_eval.py`, `src/rag_run.py` · **Outputs:** `results/development/exp07_topk/summary.json`, `results/plots/exp07_topk.png`, per-K LLM predictions in `results/{development,validation}/exp07_topk_k*/`
**Setup:** dense retrieval, voyage-4-lite, recursive 300/50 chunks, no filters, K in {1, 3, 5, 8}; retrieval metrics on 80 cases (development + validation), downstream on both LLMs.
**Selection rule (declared before running):** K with the highest mean development correct count across the two LLMs; ties go to the smaller K.

## Retrieval
| K | Recall@K | Precision@K | MRR | nDCG@K | All required in top-K | Words in context |
|---|---|---|---|---|---|---|
| 1 | 0.248 | 0.525 | 0.525 | 0.525 | 3.7% | 190 |
| 3 | 0.598 | 0.383 | 0.665 | 0.576 | 41.2% | 567 |
| 5 | 0.688 | 0.258 | 0.681 | 0.614 | 46.3% | 908 |
| 8 | 0.756 | 0.172 | 0.687 | 0.636 | 55.0% | 1412 |

Higher K buys recall and coverage but dilutes precision and roughly doubles the prompt from K=3 to K=8.

## Downstream (correct / n, false approvals)
| K | gpt-4o-mini dev | gpt-4o-mini val | llama dev | llama val | gpt-4o-mini input tokens (dev) | gpt-4o-mini cost (dev) | llama median latency |
|---|---|---|---|---|---|---|---|
| 1 | 9/60 | 2/20 | 12/60 | 6/20 | 42.5k | $0.0087 | 1.9 s |
| 3 | **23/60** | 6/20 | 19/60 | 6/20 | 79.6k | $0.0144 | 2.2 s |
| 5 | 22/60 | 6/20 | 20/60 | 7/20 | 112.6k | $0.0194 | 2.9 s |
| 8 | 22/60 | 6/20 | 20/60 | 7/20 | 163.8k | $0.0228 | 3.8 s |

False approvals stay between 0 and 2 of 39 (development) at every K.

## Findings and decision
- K=1 is clearly too few (9/60 for gpt-4o-mini). Beyond K=3, accuracy is flat within one case while cost, tokens and latency keep rising (K=8 costs 58% more than K=3 for the same accuracy).
- Rule result: development means are 10.5, 21.0, 21.0, 21.0, so **K = 3** is chosen (tie broken toward smaller K).
- Retrieval improves with K but downstream accuracy does not, which again points to policy application, not evidence access, as the limit.
