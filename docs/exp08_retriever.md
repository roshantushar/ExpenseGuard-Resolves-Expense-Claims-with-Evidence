# Exp 8 — BM25 vs dense vs hybrid retrieval (development only)

Notebook: `notebooks/exp08_retriever.ipynb`. Results: `results/current/development/exp08_retriever/`. Plot: `results/current/plots/exp08_retriever.png`. Cost: $0 (reused cached embeddings and an identical-config generation call). Development split only.

**Question:** can BM25 or hybrid (RRF) recover the evidence dense retrieval misses entirely? Frozen: chunking 600/100, K=8, voyage-4-lite for the dense side.

| Retriever | Recall@8 | Full coverage | Wrong-year/case | Wrong-region/case |
|---|---|---|---|---|
| Dense | 0.520 | 27.1% | 0.057 | 0.343 |
| BM25 | 0.295 | 12.9% | 0.000 | 0.357 |
| Hybrid (RRF) | 0.436 | 21.4% | 0.000 | 0.300 |

**Dense-miss diagnostic** (46/70 dev claims missing >=1 required clause from dense's own top-12):

| Retriever | Overall full coverage | Dense-miss recovery (recall>0, of 46) | Multi-clause full coverage | Cross-document full coverage |
|---|---|---|---|---|
| Dense | 27.1% | 35 | 13.2% | 20.0% |
| BM25 | 12.9% | 26 | 11.3% | 7.3% |
| Hybrid | 21.4% | 34 | 13.2% | 14.5% |

**Findings:** dense wins outright and also does best on its own weak subset; hybrid is worse than dense on every metric, dragged down by BM25. Of the 34 dense-miss cases hybrid partially recovers, 21 are via a merchant/category keyword, 8 via a quoted policy/circular ID, 5 via other lexical overlap — shallow matches, not real policy vocabulary in the notes. This rules out "wrong retriever family" and rules out RRF hybrid as a fix.

**Decision:** keep dense (voyage-4-lite); BM25/hybrid not carried forward. The retrieval gap is a query-representation problem, not a retriever-family problem — strong evidence to try Exp 10 (query rewriting) rather than further retriever swaps. Validation untouched.
