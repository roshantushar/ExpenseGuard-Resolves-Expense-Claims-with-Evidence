> **Stale:** this run used the earlier (easy) V2 with structured form fields. It has not been re-run on the semantic edition.

# V2 Exp 1 — End-to-end sanity

Notebook: `notebooks/v2/exp01_sanity.ipynb`. Results: `results/v2/development/exp01_slice/` (earlier run kept in `exp01_slice_previous_run/`). Plot: `results/v2/plots/exp01_slice_development.png`.

**Hypothesis:** a claim plus its correct policy clauses can be turned into a schema-valid decision by a model, end to end.

**Configuration:** 9 development group-A claims (quota 3/3/2/2 could not be filled: only 1 ESCALATE exists), oracle clauses supplied, temperature 0, fresh cache (live calls). Models: `openai/gpt-4o-mini` (OpenRouter) and `llama3.2:3b` (Ollama).

| Model | Correct/N | CDR (Wilson 95%) | Schema valid | False approvals | Median latency | Tokens in/out | Cost |
|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 5/9 | 55.6% (27-81%) | 9/9 | 0/6 | 1.9 s | 8206 / 662 | $0.0016 |
| llama3.2:3b | 4/9 | 44.4% (19-73%) | 9/9 | 0/6 | 2.4 s | 8401 / 740 | $0 |

**Findings:** pipeline works (18/18 valid, no errors). Both models over-reject even with correct clauses (mileage arithmetic slip, FX-threshold case, submission-window case not escalated). Decisions matched the earlier run 9/9 (llama) and 8/9 (gpt-4o-mini).

**Decision:** feasibility confirmed; n is too small for performance claims. Next: Exp 2 deterministic baseline.
