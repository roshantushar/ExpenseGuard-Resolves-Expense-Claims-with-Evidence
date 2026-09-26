# Experiment 6 — Chunking strategies (including recursive chunking)

**Code:** `scripts/exp06_chunking.py`, `src/chunking.py` · **Outputs:** `results/development/exp06_chunking/chunking_comparison.json`, `results/plots/exp06_chunking_comparison.png`, `results/{development,validation}/exp06_chunking/`
**Setup:** dense retrieval, top-3, raw claim query, no filters, 80 cases (development + validation). Retrieval metrics averaged over five embedding models (text-embedding-3-small, gemini-embedding-2, voyage-4-lite, nemotron free, bge); embeddings for every config are stored in `results/embeddings/`.

## Recursive chunking (implemented without dependencies)
Split on the coarsest separator present, in order: clause heading (`## `), paragraph, line, sentence, word. Recurse until every piece is at most the size limit, then greedily merge neighbouring pieces up to the limit with overlap. Chunks therefore respect clause boundaries where possible, unlike fixed windows, which cut mid-clause. Sizes tested: 100/15, 200/30, 300/50 tokens (about 0.75 words per token). Recursive chunks average 46, 108 and 164 words (83, 35 and 23 chunks).

## Retrieval results (mean over embedding models)
| Chunking | Recall@3 | Precision@3 | MRR | All required clauses in top-3 | Words in context |
|---|---|---|---|---|---|
| fixed 150/25 | 0.451 | 0.337 | 0.473 | 27.7% | 330 |
| fixed 300/50 (Exp 5 naive) | 0.539 | 0.342 | 0.498 | 40.0% | 615 |
| whole document (fixed 600/100) | 0.671 | 0.383 | 0.571 | 55.3% | 929 |
| clause (one per clause, with header) | 0.423 | 0.288 | 0.476 | 28.0% | 154 |
| recursive 100/15 | 0.399 | 0.269 | 0.425 | 25.5% | 140 |
| recursive 200/30 | 0.426 | 0.295 | 0.472 | 28.2% | 357 |
| **recursive 300/50** | 0.550 | 0.341 | **0.535** | 41.5% | 557 |

- **Recursive 300/50 is the best recursive setting and slightly beats the fixed window of the same size** on MRR (0.535 vs 0.498; with voyage, 0.665 vs 0.646) and on all-clauses coverage (41.5% vs 40.0%), using 9% less context. The gains are small and within noise at 80 cases.
- **Smaller chunks are worse.** One-clause chunks lose the surrounding document context (region, year, related clauses), so the right document is harder to find and the top-3 covers fewer required clauses. Recursive 100/15 is the worst config.
- **Whole-document chunks score highest** on recall and coverage, but that is partly mechanical: a whole document contains 6 to 7 clauses, so it covers more required clauses for the same top-3, and it puts about 929 words in the prompt. It says little about retrieval quality per se.
- **Chunk size matters more than chunk method** here, because the corpus is small.

## Downstream check (voyage-4-lite, recursive 300/50, top-3)
| Split | Model | Correct | Wilson 95% | False approvals | Cost |
|---|---|---|---|---|---|
| Dev (60) | gpt-4o-mini | 23 (38.3%) | 27.1–51.0% | 1/39 | $0.0144 |
| Dev (60) | llama3.2:3b | 19 (31.7%) | 21.3–44.2% | 0/39 | $0 |
| Val (20) | gpt-4o-mini | 6 (30.0%) | 14.5–51.9% | 0/15 | $0.0048 |
| Val (20) | llama3.2:3b | 6 (30.0%) | 14.5–51.9% | 1/15 | $0 |

Against Exp 5 (fixed 300/50): gpt-4o-mini 17 → 23 of 60 on development and 3 → 6 of 20 on validation; llama 20 → 19 and 8 → 6. The gpt-4o-mini improvement is the largest step so far for an LLM configuration, but the confidence intervals overlap heavily and the LLM's behaviour changed only partly through retrieval, so treat it as a lead, not a result. The rules baseline (78% on development) remains far ahead.

## Notes
- The best recursive config was chosen by development MRR among recursive configs only; the comparison with fixed chunking was not used for selection.
- The chosen chunking for later experiments is recursive 300/50, pending Exp 7 to 9.
- Failures: bge cannot embed the whole-document chunks (512-token limit), so its whole-document row is missing and that config averages four models.
