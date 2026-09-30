# Exp 5 — Naive RAG baseline

Notebook: `notebooks/exp05_naive_rag.ipynb`. Results: `results/current/development/exp05_naive_rag/`, `results/current/validation/exp05_naive_rag/`. Plots: `results/current/plots/exp05_embedding_comparison.png`, `exp05_naive_rag_development.png`, `exp05_naive_rag_validation.png`. Cost about $0.045 (all three models tested, both splits, summed from each run's `total_cost_usd`).

**Hypothesis:** retrieval will beat no-policy but not yet the rules or the whole corpus.

**Part A (retrieval only, dev+validation, fixed300_50):**

| Embedding model | Recall@3 | Precision@3 | MRR | Full coverage |
|---|---|---|---|---|
| voyage-4-lite (best) | 0.272 | 0.217 | 0.422 | 15% |
| nemotron-3-embed-1b (free) | 0.161 | 0.153 | 0.303 | 6% |
| gemini-embedding-2 | 0.146 | 0.120 | 0.253 | 6% |
| text-embedding-3-small | 0.120 | 0.107 | 0.223 | 5% |

`bge-base-en-v1.5` and `liquid/lfm-2.5-embedding-350m:free` returned HTTP 400 on OpenRouter for most chunk configs (endpoint issue), so incomplete.

**Part B (generation, top-3 voyage-4-lite/fixed300_50 chunks, 70 dev claims):**

| Model | Correct/N (95% CI) | False approvals | Decisions |
|---|---|---|---|
| gpt-4o-mini | 21/70 = 30% (21-42%) | 0/52 | REJECT 59 |
| gemini-2.5-flash-lite | 22/70 = 31% (22-43%) | 7/52 | REQUEST_INFORMATION 54 |
| llama3.2:3b | 20/70 = 29% (19-40%) | 1/52 | REJECT 68 |

For comparison: Exp 3 (no policy) best 37%; Exp 4B-lean (whole corpus) gemini 36%; rules 2b 49%, 2c 69%.

**Findings:** naive RAG is not yet useful. Recall is weak because the query (coarse bill category + raw note text) shares little vocabulary with the formal policy (approval, duplicate, circular numbers). Models collapse onto REJECT more than in earlier experiments. Missed escalation is 100% across the board. Validation gives the same picture (8/30 for all three).

## Retrieval-vs-reasoning decomposition
Only 11/70 dev claims (16%) have complete top-3 retrieval. On that subset, accuracy is 18% (gpt-4o-mini), 18% (gemini), 45% (llama) — no better than on the 59 incomplete-retrieval claims (32%/34%/25%). **The bottleneck is not retrieval alone**: even with every required clause supplied, the models are wrong 55-82% of the time. Small subset (n=11), so not conclusive; Exp 11's policy oracle will test this on every claim.

## Where recall is low
Self-contained claims retrieve best (recall 0.42, full coverage 39%); workflow (0.26/10%) and dynamic (0.17/0%) are worse. Multi-clause claims do much worse than single-clause (0.22 vs 0.47 recall). Cross-document (0.23 vs 0.46) and REQUEST_INFORMATION claims (0.15, 0% full coverage) are hardest. Temporal/circular claims are not notably harder (0.27 vs 0.28) — the difficulty is multi-clause/cross-document structure.

## Per-class recall
ESCALATE recall is 0.0 for all three models. gpt-4o-mini/llama collapse onto REJECT (recall 0.89-1.0, other classes near 0); gemini collapses onto REQUEST_INFORMATION (0.875).

## Failure sample (10 cases)
6 "enterprise fact unavailable to RAG" (needs an approval/travel/exception/delegation record), 3 "evidence retrieved but reasoning failed" (recall 1.0, still wrong), 1 "multi-clause miss".

**Decision:** naive RAG is not competitive; part retrieval gap, part reasoning gap (to be split precisely by Exp 11). Exp 5 is frozen. **From Exp 6 onward: tune chunk size/top-K/retriever choices on development only; validation is used once to confirm the final configuration, not for repeated comparisons.** For Exp 8, hybrid/BM25 are not assumed to help most — these notes avoid policy vocabulary by design, so pure BM25 could underperform dense retrieval; query rewriting (Exp 10) is a more likely fix for the real vocabulary gap if Exp 8/9 fall short. Next: Exp 6 (chunk size/overlap, development only).
