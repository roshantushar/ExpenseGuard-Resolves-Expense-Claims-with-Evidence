# V2 Exp 13 — Missing-information detection (component qualification, $0)

Notebook: `notebooks/v2/exp13_missing_info.ipynb`. Results: `results/v2/development/exp13_missing_info/`. Plot: `results/v2/plots/exp13_missing_info.png`. Cost: $0 (reused predictions from Exp 2, 9, 12, 12B). Development split only.

**Question:** can any system ask for exactly what is missing? 16 positive REQUEST_INFORMATION cases, 54 negative controls, already present in the dev split.

| System | RI recall | RI precision | Field precision | Field recall | Exact field-set match |
|---|---|---|---|---|---|
| 2c rules | 1.000 | 0.552 | 0.625 | 0.625 | 10/16 |
| H0 RAG+M4 | 0.500 | 0.286 | 0.000 | 0.000 | 0/8 |
| H5 hybrid | 0.438 | 0.467 | 0.000 | 0.000 | 0/7 |
| **R2 resolver** | **0.875** | **0.560** | **0.571** | **0.571** | **8/14** |

**Findings:** 2c catches every RI case but over-triggers on 13/54 negatives (precision 0.55). The RAG systems score **0.0 field precision/recall** — inspecting raw predictions shows this is a real conceptual/vocabulary drift, not just formatting: e.g. `travel_request_record` predicted for gold `exception_reference`; `per_person_amount` (a derived quantity) predicted for gold `attendee_count` (the actionable fact). R2 wins because 14/16 of its predictions inherit the rule engine's own vocabulary. No system produced a vague, fieldless request (0/16 all four). Field-level: only 2c/R2 ever name a specific field correctly, across every bucket down to n=1.

**Resolver diagnostic:** of Exp 12B's 36 residual claims, 6 are gold RI; only 1/6 has a single note-parser gap matching the gold field — most residual RI cases need enterprise-evidence facts, not better note parsing, consistent with Exp 12's finding.

**Decision:** deterministic path is recall-trustworthy but needs a precision fix; LLM path cannot yet be trusted to name the specific fact. Recommendation for Exp 30: prefer the deterministic field name when available; treat an LLM-only field name as a lower-confidence hint. Next: Exp 14 (duplicate detection).
