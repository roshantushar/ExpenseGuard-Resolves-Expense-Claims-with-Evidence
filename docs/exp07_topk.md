# V2 Exp 7 — Top-K retrieval sensitivity (development only)

Notebook: `notebooks/v2/exp07_topk.ipynb`. Results: `results/v2/development/exp07_topk/`. Plot: `results/v2/plots/exp07_topk.png`. Cost: about $0.125 (two downstream runs; retrieval sweep reused the frozen Exp 6 index). Development split only.

**Hypothesis:** higher K trades recall for distractors and cost; find where it plateaus.

| K | Recall@K | Full coverage | Context words |
|---|---|---|---|
| 1 | 0.170 | 10% | 444 |
| 3 | 0.322 | 16% | 1332 |
| 5 | 0.445 | 20% | 2212 |
| 8 | 0.520 | 27% | 3501 |
| 10 | 0.554 | 30% | 4355 |
| 12 | 0.597 | 34% | 5173 |

**Missing-clause-rank diagnostic** (59/70 dev cases incomplete at K=3): first missing gold clause ranks 4-5 for 25 cases, 6-8 for 8, 9-12 for 7 — all fixable by K=12. But **19 of 59 (27% of all dev claims) never appear in the top 12 at all** — a retriever/query problem, not a top-K problem.

**Implementation note:** a first version of the K-selection rule anchored on the sweep's own maximum (K=12), which is circular when the curve has not plateaued; caught and re-run as an explicit K=8 vs K=12 comparison before writing conclusions.

**Downstream check:** paid model, dev: K=8 = 18/70 (26%), K=12 = 20/70 (29%), false approvals 0/52 both. A 2-case difference is a screening signal only (not >=4), so K=12 was not adopted on this evidence, and Gemini/llama were not run.

**Decision:** K=8 is the operational choice (most of the recall gain at meaningfully lower cost than K=12). About a quarter of dev claims need a different retriever or query representation, which Exp 8 (BM25/dense/hybrid) and, if needed, Exp 10 (query rewriting) must address. Validation untouched.
