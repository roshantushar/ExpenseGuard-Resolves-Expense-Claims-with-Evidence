# Exp 11 — Policy oracle (development only)

Notebook: `notebooks/exp11_oracle.ipynb`. Results: `results/current/development/exp11_oracle/`. Plot: `results/current/plots/exp11_oracle.png`. Cost: $0.021 (10A/10B reused at $0). Development split only. Evaluator-only (reads private ground truth); never a runtime component.

**Question:** how much of the remaining error disappears when the model is given exactly the required + supporting policy clauses (`src/policy.render`, no explanation/label/decision hint)?

| System | Correct/N | CDR (95% CI) | Missed-escalation rate | Macro-F1 |
|---|---|---|---|---|
| 10A RAG (raw + M4 filter) | 22/70 | 31.4% (22-43%) | 88.2% | 0.326 |
| 10B RAG (structured rewrite) | 20/70 | 28.6% (19-40%) | 94.1% | 0.276 |
| **Oracle** | **25/70** | **35.7% (26-47%)** | 94.1% | 0.284 |

**The headline: this is the "even perfect retrieval does not solve it" outcome (22 -> 25, not 22 -> 45).** The bottleneck is policy application, not retrieval.

**Case-level split (RAG=10A):**

| | Oracle wrong | Oracle correct |
|---|---|---|
| RAG wrong | 40 (57.1%) — reasoning failure | 8 (11.4%) — retrieval failure |
| RAG correct | 5 (7.1%) — instability | 17 (24.3%) — solved |

**Exp 10 follow-up:** of 10 cases where 10B improved gold-clause coverage over 10A, 9 kept the wrong decision; of those, the oracle solves only 1 and also fails 8 — confirming 10B's retrieval gain didn't help because the model couldn't have used the evidence correctly anyway.

**By complexity (oracle):** 1 clause 10/17 (59%), 2 clauses 5/9 (56%), **3+ clauses 10/44 (23%)** — accuracy roughly halves once 3+ clauses must be composed. Temporal (2/12) and exception (2/11) cases are hardest even under the oracle; regional cases (5/21) are close to average.

**Escalation:** oracle ESCALATE recall stays at 0.059 (worse than 10A's 0.118) — perfect evidence does not fix escalation recognition. REQUEST_INFORMATION recall does rise (0.50 -> 0.69), the clearest genuine oracle benefit.

**Decision:** motivates Exp 12 (hybrid RAG + deterministic rules) — move arithmetic and multi-clause composition into code (per `src/rules_v2.py`'s existing split), leave semantic judgment to the LLM. Validation untouched.
