# Exp 12B — Deterministic-first residual resolver (architecture probe, development only)

Notebook: `notebooks/exp12b_resolver.ipynb`. Results: `results/current/development/exp12b_resolver/`. Plot: `results/current/plots/exp12b_resolver.png`. Cost: $0.030. Development split only. **Architecture probe, not the final router (that is Exp 30).**

**Question:** can deterministic-first routing (conclusive -> trust the rule engine; unresolved -> escalate or LLM) preserve reliability while using the LLM only for genuine ambiguity? Conclusiveness is defined from runtime-visible state only (the parser's own extraction gaps and the rule engine's own "no rule triggered" fallback), never a label.

| Variant | Correct/N | CDR | False approvals | Human review rate | ESCALATE recall |
|---|---|---|---|---|---|
| R0 rules only (Exp 2c) | 48/70 | 68.6% | 6/52 | 15.7% | 0.647 |
| R1 escalate unresolved | 36/70 | 51.4% | 0/52 | 65.7% | 0.941 |
| **R2 deterministic + LLM residual** | **43/70** | **61.4%** | 0/52 | 20.0% | 0.765 |

**Split:** 34/70 claims resolved conclusively (88.2% accurate); 36/70 routed as residual.

**R1 vs R2 (the key comparison):** on the identical 36-claim residual subset, LLM adjudication scores 13/36 (36.1%) vs blind escalation's 6/36 (16.7%) — **the LLM clearly earns its place over autonomous escalation.** R2 also beats Exp 12's full hybrid (33/70) while calling the LLM on half as many claims (36 vs 70; 34 model calls avoided).

**Honest caveat:** R0 (pure rules, including its own uncertain fallback guesses on all 70) still leads at 48/70. On the same 36-claim residual, the rule engine's raw fallback answer is right 18/36 (50%) — better than both R1 and R2. Neither escalation nor LLM handoff yet beats trusting the rule engine outright, because the conclusiveness signal, while well-calibrated in relative terms (88% vs 50%), still leaves a fallback subset whose naive answer is informative rather than near-chance.

**Decision:** confirmed that LLM beats blind escalation for ambiguity. Not yet a reason to replace the rule engine's own answer. Refine the conclusiveness signal before Exp 30. Resume the original sequence at Exp 13.
