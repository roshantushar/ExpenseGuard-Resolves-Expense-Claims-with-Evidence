# Exp 6 — Chunk size and overlap (development only)

Notebook: `notebooks/exp06_chunking.ipynb`. Results: `results/current/development/exp06_chunking/`. Plot: `results/current/plots/exp06_chunking.png`. Cost: about $0.03 (a new embedding build + one generation run). Development split only; validation untouched.

**Hypothesis:** poor chunk boundaries explain part of Exp 5's weak retrieval.

| Config | Chunks | Recall@3 | Full coverage | Avg context words |
|---|---|---|---|---|
| 150/25 | 426 | 0.034 | 0% | 333 |
| 300/50 (Exp 5) | 215 | 0.280 | 15.7% | 673 |
| 600/100 | 111 | 0.322 | 15.7% | 1332 |
| 900/150 | 74 | 0.389 | 17.1% | 1977 |
| clause | 229 | 0.262 | 11.4% | 550 |

**Decision rule (fixed in advance):** best development retrieval, provided it does not materially increase context cost (>=5pp Recall@3 or full-coverage gain, or a clear hard-subset gain); if the mechanical rule's pick is used downstream and shows no accuracy gain despite a large cost increase, prefer the cheaper alternative.

**Findings:** 150/25 is broken (chunks separate a clause from its numbers). Gains plateau in the 300-600 range; full coverage is identical (15.7%) at 300/50 and 600/100. The mechanical rule flagged 900/150, but its downstream check (paid model, dev) scored 20/70 against Exp 5's 21/70 for 300/50 — no gain for 3x the context tokens — so 900/150 is not carried forward, and the other two models were not run. Evidence-fragmentation categorization: "split from context" failures fall from 40 (150/25) to 5 (900/150) as chunks grow, but "none retrieved" (vocabulary mismatch) stays flat at 12-23 regardless of chunk size — chunking is only a partial fix.

**Decision:** carry forward voyage-4-lite / fixed600_100 (best full-coverage and hard-subset recall at moderate cost). Full coverage remains low (16-17%) at every chunk size. Next: Exp 7 (top-K).
