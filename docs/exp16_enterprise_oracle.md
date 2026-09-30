# V2 Exp 16 — Enterprise-evidence oracle: raw records vs resolved facts

Notebook: `notebooks/v2/exp16_enterprise_oracle.ipynb`. Results: `results/v2/development/exp16_enterprise_oracle/`. Cost: $0.046 (one new run). Development, evidence-dependent subset (52/70 claims needing at least one enterprise lookup).

**Question:** does the LLM need enterprise facts pre-resolved, or can it interpret raw records itself? Isolates raw records vs resolved facts, holding policy evidence (frozen M4 RAG) and the decision-maker (the LLM) fixed.

| Level | Evidence | Correct/52 |
|---|---|---|
| O0 | none (RAG only) | 13 (25.0%) |
| **O1 (new)** | **raw enterprise records** | **12 (23.1%)** |
| O2 | resolved facts (Exp 12's H5) | 23 (44.2%) |
| O3 | deterministic rules (Exp 2c) | 39 (75.0%) |

**O1 scored slightly below O0** — raw records added reasoning burden without reliably conveying validity, exactly the outcome flagged as plausible in advance.

**O1 vs O2 transition:**

| | O2 wrong | O2 correct |
|---|---|---|
| O1 wrong | 25 (48%) | **15 (29%) — record-interpretation failure** |
| O1 correct | 4 (8%) | 8 (15%) |

**29% of evidence-dependent claims are solved only once facts are resolved, not merely supplied** — direct evidence Exp 12's gain was interpretation, not data access. Failure mechanisms (15 key cases, from gold reason text): approval type/conflict (4), expired/invalid approval (2), delegation expired (2), budget misread (1), plus authority-level and date cases — dominated by the model not cross-checking an approval record's type/date/level, exactly what `rules_v2.approval_state()` already does deterministically.

**Methodological note:** the planned "evidence-interpretation accuracy" sub-analysis (LLM's self-reported validity booleans vs the resolver's) could not be scored — the harness only saves fixed schema keys, so the extra `record_interpretation` field was dropped before saving, not a model failure. Not re-run to avoid extra spend; flagged as a gap, not hidden.

**Decision:** confirms and sharpens Exp 12 — Exp 17's tools should return resolved facts and validity flags, not raw rows.
