# V2 Exp 30 — Selective architecture router: freezing the final design

Notebook: `notebooks/v2/exp30_selective_router.ipynb`. Code: `src/resolver.py` (new, the frozen pipeline), `src/tools.py` (`validate_approval` fixed for conflicting records, Exp 28). Results: `results/v2/development/exp30_selective_router/`. Cost: $0.030. Development split only.

**Architecture:**
```
claim -> deterministic resolver (rules_text + rules_v2) -> conclusive? -> yes: deterministic decision
                                                                      -> no: M4 RAG + resolved facts (H1-H4) -> LLM
```

**Fix applied first (Exp 28's deterministic bug):** `validate_approval` now detects >1 disagreeing approval records for one expense and returns `CONFLICTING_RECORDS` (mapped to ESCALATE in `workflow_v2`), instead of silently reading only the first. All 31 tests still pass. Exp 28's retrieval-text-injection finding remains an open, documented limitation of the LLM-residual path — not fixed here.

**Three-way comparison:**

| Strategy | Correct/N | False approvals / non-approvable | FAR | Human Review Rate | % invoking the LLM |
|---|---|---|---|---|---|
| H5: LLM for all | 33/70 (47%) | 2/52 | 3.85% | 20.0% | 100% |
| workflow_v2: fixed workflow for all | **45/70 (64%)** | 7/52 | 13.46% | 14.3% | 0% |
| **Exp 30 selective resolver** | 43/70 (61%) | **0/52** | **0.0%** | 18.6% | 51% |

(Population: full 70-claim development split; 52 of the 70 are ground-truth non-`APPROVE`.)

**Path-level accuracy (the extra metric requested):** deterministic path 30/34 (88.2%), LLM-residual path 13/36 (36.1%). The system's reliability comes almost entirely from the deterministic layer; the LLM residual step is the weak link, and improving it (or narrowing the residual via a sharper conclusiveness signal) is the highest-leverage remaining lever.

**Trade-off:** workflow_v2 alone is more accurate; the selective resolver trades 2 points of accuracy for 0 false approvals versus 7 (workflow) and 3 (LLM-for-all).

**Decision: `src/resolver.py` is frozen** as the selective architecture, carried into Exp 31 (cost-to-serve) and Exp 32 (the one-time frozen final test). Validation untouched.
