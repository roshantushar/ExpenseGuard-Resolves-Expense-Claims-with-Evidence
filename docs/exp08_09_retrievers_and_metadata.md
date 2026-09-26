# Experiments 8 and 9 — Retrieval family and metadata-aware retrieval

**Code:** `scripts/exp08_09_retrievers_metadata.py`, `src/retrievers.py` · **Outputs:** `results/development/exp08_09/summary.json`, `results/plots/exp08_09_retrieval_and_metadata.png`
**Setup:** recursive 300/50 chunks, K = 3 (from Exp 7), 80 cases (development + validation) for retrieval; best configs run through both LLMs.

## Exp 8 — BM25 vs dense vs hybrid
BM25 is implemented directly (k1 = 1.5, b = 0.75). Hybrid is reciprocal rank fusion (constant 60) of BM25 and dense. Dense embeddings: voyage-4-lite (paid) and nemotron (free).
| Retriever | Recall@3 | Precision@3 | MRR | nDCG@3 | All required in top-3 |
|---|---|---|---|---|---|
| BM25 | 0.465 | 0.304 | 0.481 | 0.410 | 28.7% |
| dense, voyage-4-lite | **0.598** | **0.383** | **0.665** | **0.576** | 41.2% |
| hybrid, voyage-4-lite | 0.581 | 0.371 | 0.588 | 0.519 | 41.2% |
| dense, nemotron (free) | 0.579 | 0.367 | 0.546 | 0.514 | 42.5% |
| hybrid, nemotron (free) | 0.531 | 0.342 | 0.517 | 0.471 | 40.0% |

- **Dense beats BM25** by about 0.13 recall and 0.18 MRR; hybrid did not beat the best dense retriever. The policy text and employee wording differ enough that keywords alone miss (BM25 is worst), but the corpus is small, so fusing in a weaker BM25 ranking adds noise.
- **Free nemotron is close to paid voyage** on recall and coverage, lower on MRR.
- Best by the development mean of nDCG, MRR and coverage: **dense, voyage-4-lite**. Downstream results are identical to the Exp 6/7 K=3 run (same context): gpt-4o-mini 23/60 development and 6/20 validation; llama 19/60 and 6/20.

## Exp 9 — Metadata filtering
The filter uses only the claim and chunk metadata: keep chunks whose document is in force on the transaction date and whose region is GLOBAL or the claim's own country. Best retriever with vs without the filter:
| | Recall@3 | Precision@3 | MRR | nDCG@3 | All required | Wrong-year chunks / case | Wrong-region chunks / case |
|---|---|---|---|---|---|---|---|
| unfiltered | 0.598 | 0.383 | 0.665 | 0.576 | 41.2% | 0.15 | 0.39 |
| filtered | **0.642** | **0.400** | **0.700** | **0.613** | **45.0%** | **0.00** | **0.00** |

The filter removes all wrong-year and wrong-region retrievals (a wrong-region chunk appeared in about 39% of unfiltered slots) and improves every retrieval metric.

Downstream, however, it did not help:
| | Development | Validation |
|---|---|---|
| gpt-4o-mini unfiltered → filtered | 23/60 → 20/60 (FA 1 → 0 of 39) | 6/20 → 2/20 |
| llama3.2:3b unfiltered → filtered | 19/60 → 19/60 (FA 0 → 3 of 39) | 6/20 → 7/20 |

- The differences are within noise (n = 60 and 20; several cases share the same claim text), but there is no evidence that better retrieval produced better decisions.
- Wrong-year retrieval was rare to begin with (0.15 chunks per case), so the silent wrong-version failure the plan worries about is small at this scale and for these models.
- Retrieval is no longer the limiting factor for the LLM: it is applying the retrieved rule (arithmetic, what counts as missing, when to escalate).

## Decisions
- **Retriever for later experiments:** dense voyage-4-lite, recursive 300/50, K = 3, **with** the metadata filter (retrieval is strictly better and the filter is cheap, deterministic and removes a known silent-failure mode). Downstream accuracy is a caveat, not a reason to drop it.
- Exp 10 (query rewriting or reranking) is not justified: recall, not ordering, is the retrieval weakness only for 55% of cases, and the LLM step dominates. I recommend skipping it unless you want it run for completeness.
- Next: Exp 11 (policy oracle) to separate retrieval from reasoning failures directly, and Exp 12 (hybrid RAG + deterministic rules).
