# V2 Exp 10 — Query rewriting (development only)

Notebook: `notebooks/v2/exp10_query_rewrite.ipynb`. Results: `results/v2/development/exp10_query_rewrite/`. Plot: `results/v2/plots/exp10_query_rewrite.png`. Cost: about $0.062. Development split only.

**Question:** after Exp 9 showed evidence is almost always somewhere in the ranked candidates but often too low, can rewriting the query fix the ranking? Frozen: voyage-4-lite, chunking 600/100, K=8, Exp 9's M4 metadata filter.

| Variant | Recall@8 | Full coverage | Mean required-clause rank | Cases: all gold in top 8 |
|---|---|---|---|---|
| 10A raw | 0.563 | 32.9% | 12.8 | 23 |
| 10B structured (deterministic) | 0.662 | 42.9% | 10.5 | 30 |
| 10C LLM rewrite | 0.560 | 31.4% | 12.9 | 22 |

10C's rewrite passed the "no policy conclusion" check (0/70 rewrites contained conclusion-like wording), but paraphrased into generic terms and lost the specific nouns the raw note carries, so it did not beat raw retrieval.

**Rank migration** (103 still-missing required clauses across the 47 cases incomplete under 10A): 10B promotes 15/21 rank-9-12 clauses and 8/81 rank->12 clauses into the top 8; 10C promotes only 6/21 and 4/81, and regresses some clauses.

**Downstream (paid model, dev): retrieval improved but the decision got worse.** 10A (Exp 9's M4) = 22/70 (31.4%); **10B = 20/70 (28.6%)**, a drop despite a 10-point retrieval gain on every metric. 10C was not run downstream (did not beat 10B on retrieval, per the staged rule).

**Decision:** query rewriting is not adopted; 10A (raw query + M4 filter) remains the carried-forward retriever. Retrieval and downstream accuracy are decoupled here, consistent with every prior experiment in this sequence — the productive next step is Exp 11 (policy oracle), to isolate how much of the remaining error is retrieval vs. reasoning using every claim, not just the small complete-retrieval subsets seen so far.
