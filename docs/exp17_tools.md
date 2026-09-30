# V2 Exp 17 — Typed enterprise tools + unit tests ($0)

Notebook: `notebooks/v2/exp17_tools.ipynb`. Code: `src/tools.py` (updated), `tests/test_tools.py` (updated), `tests/test_no_leakage.py` (coverage extended). No LLM calls.

**Question:** does the tool layer work reliably, and does it return validated business facts rather than raw rows to interpret (per Exp 16)?

**Two tiers.** Low level (raw rows): the original 8 tools plus 2 new V2 tools, `get_approval_delegation` and `get_cost_centre_budget`. Resolved (new): `validate_approval(expense_id, required_level, required_types, transaction_date, amount_sgd)` — returns `valid: true/false` with an evidence trail (`approval_present`, `delegation_used`, `delegation_valid`, `reason_code`), built from `src/rules_v2.py`'s own APR-2.x/4.x logic.

**Type system:** `call_tool()` now validates a typed spec per argument (string/ID, date, enum, list-of-strings, non-negative amount) instead of assuming every argument is a non-negative string, needed for `validate_approval`'s list and numeric arguments.

**Results:** all 22 tool tests pass, including the full `validate_approval` fixture matrix (valid/expired approval, wrong type, insufficient authority, valid/expired/over-limit delegation, no approval found, malformed date, malformed `required_types`, missing record, and an irrelevant-field invariant). Worked example: a `DELEGATED` approval whose raw row looks fine is correctly flagged `DELEGATION_INVALID` once the delegation record itself is checked — exactly Exp 16's failure pattern (15/52 cases) made concrete.

**Leakage:** `rules_v2`, `rules_text`, `hybrid_facts` added to the leakage test's coverage; all clean.

**Known out-of-scope gap:** `src/workflow.py`/`tests/test_workflow_flags.py` still target V1 case ids (3 failures) — porting them to V2 is Exp 18's task, untouched here.

**Decision:** success criterion met (unit tests pass, deterministic failure behavior, no leakage, resolved facts not raw rows). Next: Exp 18 (fixed workflow), including the V2 port.
