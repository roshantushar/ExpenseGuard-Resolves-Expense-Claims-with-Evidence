# Experiment 5 — Naive RAG baseline and embedding-model comparison

**Code:** `scripts/exp05_naive_rag.py`, `src/chunking.py`, `src/embed.py`, `src/retrieval.py` · **Outputs:** `results/development/exp05_naive_rag/` (comparison JSON, per-case retrieval rows), `results/{development,validation}/exp05_naive_rag/` (LLM predictions), `results/plots/exp05_*.png`
**Stored embeddings (reusable):** `results/embeddings/<model>/<chunking>/{vectors.npy, chunks.jsonl}`, 6.3 MB. Later experiments load these instead of re-embedding.

## Chunking strategy
- **Naive baseline (Exp 5):** fixed-size chunks of 300 tokens with 50 overlap, split per document, never across documents. Tokens are approximated as words / 0.75 (no tokenizer dependency). This gives 23 chunks of about 180 words.
- **Also stored for Exp 6:** fixed 150/25 (42 chunks), fixed 600/100 (12 chunks), and a structure-aware "clause" strategy (one chunk per policy clause, 79 chunks, each prefixed with document id, region and effective dates).
- **The corpus is small:** documents average about 315 words, so a 600-token chunk is a whole document and 600/900 are identical. The plan's 300/600/900 sweep is therefore degenerate above 300; Exp 6 will use 150 / 300 / whole-document / clause instead.
- Every chunk carries metadata (document id, region, effective_from/to, category) for Exp 9 filtering, and the list of clause IDs it covers (a clause counts as covered if at least half of its text is in the chunk). Clause IDs are used only by the evaluator for metrics and are never shown to a model.
- **Query:** raw claim-derived text (category, country, date, line items, description). No rewriting, no filter, no reranker.

## Part A — embedding models (retrieval only, top-3, development + validation, 80 cases)
Fixed 300/50 chunking:
| Embedding model | Recall@3 | Precision@3 | MRR | All required clauses in top-3 | Total embedding cost |
|---|---|---|---|---|---|
| voyageai/voyage-4-lite | **0.610** | 0.379 | **0.646** | 43.8% | $0.0006 |
| baai/bge-base-en-v1.5 | 0.550 | 0.346 | 0.467 | 43.8% | $0.0001 |
| nvidia/nemotron-3-embed-1b (free) | 0.537 | 0.350 | 0.529 | 40.0% | $0 |
| google/gemini-embedding-2 | 0.506 | 0.312 | 0.435 | 33.8% | $0.0060 |
| openai/text-embedding-3-small | 0.490 | 0.325 | 0.412 | 38.8% | $0.0005 |
| liquid/lfm-2.5-embedding-350m (free) | failed at 300 and 600 (HTTP 400, likely input-length limit); 150 and clause worked | | | | $0 |

- **Best model:** voyage-4-lite is best and cheap; it was chosen automatically by development Recall@3 (ties broken by cost) for Part B and is stored for later experiments. The free nemotron model is close behind, and the most expensive model (gemini, 10x the cost) was not better.
- **Failures:** bge cannot embed 600-token chunks (512-token limit); the liquid model failed on larger chunks. Both are recorded, not hidden.
- **Recall is not comparable across chunk sizes.** Bigger chunks cover more clauses, so 600/100 (whole documents) shows the highest Recall@3 (0.62–0.71) while Precision@3 stays around 0.38–0.40. Judge chunking on precision and downstream accuracy (Exp 6).
- **Naive retrieval is weak.** Even the best model finds all required clauses in only 44% of cases.
- Retrieval scores here are on 80 cases with 58 distinct claim texts; differences of a few points between models are within noise.

## Part B — downstream generation (voyage-4-lite, 300/50, top-3)
| Split | Model | Correct | Wilson 95% | False approvals | Cost | Tokens in/out | Median / P95 latency |
|---|---|---|---|---|---|---|---|
| Dev (60) | gpt-4o-mini | 17 (28.3%) | 18.5–40.8% | 0/39 | $0.0149 | 82.5k / 4.2k | 1.6 s / 2.7 s |
| Dev (60) | llama3.2:3b | 20 (33.3%) | 22.7–45.9% | 4/39 | $0 | 84.6k / 4.8k | 2.6 s / 3.7 s |
| Val (20) | gpt-4o-mini | 3 (15.0%) | 5.2–36.0% | 0/15 | $0.0048 | 27.0k / 1.3k | 1.7 s / 2.1 s |
| Val (20) | llama3.2:3b | 8 (40.0%) | 21.9–61.3% | 1/15 | $0 | 27.7k / 1.7k | 3.0 s / 4.5 s |

## Comparison with Exp 4 (full policy in context)
Accuracy is essentially unchanged (gpt-4o-mini 19 → 17 of 60 on development, 3 → 3 of 20 on validation; llama 20 → 20 and 9 → 8). Naive RAG uses about 77% fewer input tokens (82.5k vs 354k) and costs 53% less ($0.0149 vs $0.0315) for gpt-4o-mini. Llama's tail latency improves (P95 3.7 s vs 14 s) and its false approvals drop (4/39 vs 13/39). So RAG is cheaper and faster but not more accurate; gpt-4o-mini still over-rejects and over-asks, matching the earlier finding that policy application, not access to the policy, is the bottleneck.

## Log note
The first run of this script crashed at the final plot after the LLM runs had finished; a fixed re-run produced identical results from cache (no extra spend). The log therefore holds two copies of the Exp 5 rows with different `run_id`s; use the later one.

## Next
Exp 6 (chunking), Exp 7 (top-K), Exp 8 (BM25 vs dense vs hybrid), and Exp 9 (metadata filters) all read the stored embeddings.
