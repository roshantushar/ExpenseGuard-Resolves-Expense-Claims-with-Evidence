# V2 Exp 4B — Long-context baseline

Notebook: `notebooks/v2/exp04b_long_context_baseline.ipynb`. Results: `results/v2/development/exp04b_full/` and `exp04b_lean/`. Plots: `results/v2/plots/exp04b_long_context_summary.png`, `exp04b_confusions.png`, `exp04b_full_development.png`, `exp04b_lean_development.png`. Cost $0.77.

**Hypothesis:** if the corpus fits in context, a model given the claim plus the whole policy could match or beat RAG.

**Configuration:** 70 dev claims, corpus in the system prompt (full 22 documents, about 49-52k tokens; lean = normative clauses only, about 17-19k), no enterprise records, temperature 0. Full on gpt-4o-mini and gemini-2.5-flash-lite; lean also on llama3.2:3b (24k window).

| System | Correct/N (Wilson 95%) | False approvals | Cites nonexistent id | Cost (70 claims) |
|---|---|---|---|---|
| full gpt-4o-mini | 22/70 = 31% (22-43%) | 0/52 | 1/70 | $0.27 |
| full gemini-2.5-flash-lite | 23/70 = 33% (23-45%) | 26/52 | 29/70 | $0.29 |
| lean gpt-4o-mini | 20/70 = 29% (19-40%) | 0/52 | 0/70 | $0.09 |
| lean gemini-2.5-flash-lite | 25/70 = 36% (26-47%) | 12/52 | 23/70 | $0.11 |
| lean llama3.2:3b | 14/70 = 20% (12-31%) | 4/52 | 1/70 | $0 |
| Exp 3 no policy (best) / rules 2b / rules 2c | 37% / 49% / 69% | | | |

**Findings:** all at chance level and no better than with no policy. The policy is not the missing ingredient: 110 of 150 claims depend on enterprise records not in the prompt, and even self-contained claims reach only 7-10 of 18. Models ask for information (REQUEST_INFORMATION for ~90% for gpt-4o-mini) and never escalate. Gemini approves aggressively with the full corpus (50% false approvals) and cites nonexistent ids. Lean vs full is not distinguishable, at a third of the cost. Llama returned invalid JSON for 18 of 70.

**Decision gate:** long context is not an accuracy baseline to beat; RAG must still show gains on tokens/cost/latency, false approvals, version precision or traceability. Accuracy will move with evidence-supplying experiments (12, 16, 18). Next: Exp 5 naive RAG.
