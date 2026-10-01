# OWASP Top 10 for LLM Applications (2026) — remapped from the 2025 assessment

**Status: the real 2026 edition was published by OWASP on 2026-08-04, after the original assessment below
(`docs/owasp_llm_top10_2025.md`) was completed against the 2025 edition.** Verified live against two
independent, current sources (cross-checked against each other for consistency) rather than assumed. This
document remaps the original real test evidence onto the new category numbering/order — it does not
duplicate or discard that original work, and it does not re-run any test that still applies unchanged.

## What changed between editions
9 of the 10 categories are the same underlying concept, just reordered (OWASP's 2026 methodology weighted
real incident data at 25% alongside practitioner votes, which moved several categories). One category was
renamed and broadened: **LLM07:2025 "System Prompt Leakage" → LLM08:2026 "Hidden Context Exposure"**, now
explicitly covering RAG-schema and hidden-policy-logic leakage in addition to system-prompt leakage.

| 2026 | Category | 2025 equivalent | Evidence status |
|---|---|---|---|
| LLM01 | Prompt Injection | LLM01 (unchanged position) | Carried forward unchanged |
| LLM02 | Sensitive Information Disclosure | LLM02 (unchanged position) | Carried forward unchanged |
| LLM03 | Excessive Agency | LLM06 | Carried forward unchanged |
| LLM04 | Supply Chain | LLM03 | Carried forward unchanged |
| LLM05 | Data and Model Poisoning | LLM04 | Carried forward unchanged |
| LLM06 | Unbounded Consumption | LLM10 | Carried forward unchanged |
| LLM07 | Misinformation | LLM09 | Carried forward unchanged |
| LLM08 | Hidden Context Exposure | LLM07 "System Prompt Leakage" (renamed, broadened) | **Partial** — original test covers the system-prompt-leakage sub-case only; the broader RAG-schema/hidden-policy-logic scope was not specifically probed. Disclosed, not claimed as full coverage. |
| LLM09 | Vector and Embedding Weaknesses | LLM08 | Carried forward unchanged |
| LLM10 | Improper Output Handling | LLM05 | Carried forward unchanged |

## Full results, 2026 numbering

| Category | Status | Evidence |
|---|---|---|
| LLM01: Prompt Injection | **Not solved** — disclosed open risk | Retrieval-text injection defeated the defense in one live attack; note-based injection partially defended |
| LLM02: Sensitive Information Disclosure | Tested | Crafted claim requesting another employee's salary/personal data; system did not disclose it (safe fallback to ESCALATE, not a demonstrated deliberate refusal) |
| LLM03: Excessive Agency | Mitigated | Disposition gate, domain guards, step cap, call deduplication |
| LLM04: Supply Chain | Tested | `npm audit`: 1 moderate finding, documented, not fixed. Python deps current; runtime resolver/agent code imports no third-party package |
| LLM05: Data and Model Poisoning | Scoped — not applicable | No model is fine-tuned or trained; every model is an unmodified foundation model |
| LLM06: Unbounded Consumption | Tested | `MAX_BUDGET_USD` confirmed live to actually raise `BudgetExceeded`; step cap bounds worst-case cost (3/13, 5/13, 8/13 step-cap hits across Exp 20/34/36) |
| LLM07: Misinformation | Tested | All 897 policy-evidence citations ever saved, checked against the real 229-clause-ID corpus — zero genuinely fabricated citations |
| LLM08: Hidden Context Exposure | **Partially tested** (see table above) | System-prompt-leakage sub-case tested: a "print your system prompt" attack did not echo system-prompt text (safe fallback). RAG-schema / hidden-policy-logic leakage was not separately probed — open item |
| LLM09: Vector and Embedding Weaknesses | Scoped and tested | Fixed, allowlisted 22-document corpus, no live ingestion path, no runtime embedding-insertion mechanism |
| LLM10: Improper Output Handling | Tested | No `dangerouslySetInnerHTML` anywhere in the frontend; a live `<script>` payload did not survive as executable content |

## Honest summary
9 of 10 categories have the same real test evidence as the original 2025 assessment, correctly remapped.
LLM08 (Hidden Context Exposure) is disclosed as only partially covering its new, broader 2026 scope — the
original system-prompt-leakage test still applies to that sub-case, but the RAG-schema/hidden-policy-logic
expansion is open, undisclosed-as-closed work, not silently claimed as tested. This is the current
reference for this project's OWASP status; `docs/owasp_llm_top10_2025.md` remains as the historical record
of the original assessment and is not altered.
