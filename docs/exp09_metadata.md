# V2 Exp 9 — Metadata-aware retrieval (development only)

Notebook: `notebooks/v2/exp09_metadata.ipynb`. Results: `results/v2/development/exp09_metadata/`. Plot: `results/v2/plots/exp09_metadata.png`. Cost: $0.098 (two downstream runs; the retrieval ladder was free). Development split only.

**Question:** does restricting dense retrieval to policy-compatible metadata improve coverage, without touching the query? Ablation ladder, each step adding one filter: M0 none, M1 +date, M2 +region, M3 +authoritative document type, M4 +expense-category compatibility. Region = `bill.country`, per FAQ-1.10 and the addenda's own scope clauses ("the addendum of the country where the expense was incurred applies"). M3 excludes FAQ/historical documents per their own text (HIST-3.1: "never override a circular"; GEP26-3.1: FAQ/definitions "never override the clauses above") — not because of knowledge of the private labels.

| Variant | Recall@8 | Full coverage | Wrong-version contam. | Wrong-region contam. | Superseded contam. |
|---|---|---|---|---|---|
| M0 none | 0.520 | 27.1% | 2.9% | 25.7% | 1.4% |
| M1 +date | 0.520 | 27.1% | 0% | 25.7% | 1.4% |
| M2 +region | 0.520 | 27.1% | 0% | 0% | 1.4% |
| M3 +authority | 0.548 | 30.0% | 0% | 0% | 0% |
| M4 +category | 0.563 | 32.9% | 0% | 0% | 0% |

**Findings:** date/region filtering eliminates contamination but adds no coverage on its own (dense embeddings already avoided most wrong-year/region chunks by content). The coverage gain comes from M3/M4. Of 51 M0-incomplete cases, only 12 (2+9+1) had any contamination present — most incompleteness was never a version/region contest.

**Filter-loss check caught a real bug:** the first category map excluded `training` for TRAVEL-category claims, losing TRN-1.1 for 3 hotel-near-conference cases (TRV-5.1 cross-references the conference policy). Fixed; filter-loss is now 0 for every variant.

**Remaining-failure bucket after M4** (47/70 still incomplete): 18 at rank 9-12, 29 at rank >12, 0 never in the ranking, 0 lost to filtering — the gap is entirely about rank now, not missing evidence.

**Downstream (paid model, dev):** M0 18/70, M4 **22/70** (+4, meaningful), 0 false approvals both. Escalation recall moved 0.0 -> 0.118 and REQUEST_INFORMATION recall 0.375 -> 0.500 — the first sign that cleaner retrieval also helps decision quality, though the reasoning gap is far from closed.

**Decision:** keep the full M4 filter. Coverage moved from 27% to 33%, not further; the dominant remaining problem is rank, not missing evidence — sets up Exp 10 (query rewriting: 10A raw, 10B rule-based rewrite, 10C LLM rewrite). Validation untouched.
