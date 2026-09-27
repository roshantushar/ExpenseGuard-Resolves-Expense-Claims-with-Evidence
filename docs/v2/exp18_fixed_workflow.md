# V2 Exp 18 — Fixed workflow (V2 port), $0

Notebook: `notebooks/v2/exp18_fixed_workflow.ipynb`. Code: `src/workflow_v2.py` (new), `tests/test_workflow_v2.py` (new), `tests/test_no_leakage.py` (coverage extended). Results: `results/v2/development/exp18_fixed_workflow/`. No LLM calls. Development split only.

**Question:** does a fixed, pre-declared tool sequence (no model) handle enterprise-evidence cases well, including the 13 "agent-candidate" claims? This is the main agent-feasibility gate.

**Acceptance criteria, all met before scoring:** all 31 tests pass; zero direct table access (checked by static analysis of `workflow_v2.py`); a simulated tool failure escalates rather than guesses; a step cap of 1 escalates rather than loops; de-duplication prevents a repeated call and is logged; validation untouched.

**Three-way comparison (isolates orchestration overhead):**

| System | Policy logic | Enterprise access | Correct/N | FAR | Escalate recall |
|---|---|---|---|---|---|
| 2c | same | direct table access | 48/70 (69%) | 11.5% | 0.647 |
| **Exp 18** | same | **typed tools + guardrails** | **45/70 (64%)** | 13.5% | 0.529 |
| R2 (Exp 12B) | mixed | tools/resolved facts + LLM residual | 43/70 (61%) | 0% | 0.765 |

**Group C (13 agent-candidate claims), the key output for Exp 19:** 2c 8/13, **Exp 18 7/13**, R2 7/13. Group B (workflow, 39): 2c 31, Exp 18 28, R2 27.

**Findings:** the orchestration layer adds only a small accuracy cost (3 claims) versus direct table access, tracing to specific policy-porting gaps (gift annual-cap cumulative logic, unreliable in both directions on a counterparty-string match), not to the tool mechanism itself. Median 3 tool calls per claim (max 7); every claim makes at least one call, including self-contained ones, due to an unconditional merchant-risk check — a minor inefficiency worth trimming later. Most importantly: **a purely static tool sequence, with no model-directed branching, solves 7 of 13 "agent-candidate" claims** — direct evidence that many dynamic-looking cases may be workflow-solvable.

**Decision:** credible working baseline; feeds directly into Exp 19's agent-necessity audit.
