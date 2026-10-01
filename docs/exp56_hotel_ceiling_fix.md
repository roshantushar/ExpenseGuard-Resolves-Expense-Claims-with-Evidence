# Exp 56 — A correct, shared hotel-ceiling calculator for the guarded agent (live, dev-only)

**Status: a real, validated fix — the first one in this investigation (Exp 53-56) that actually moves
APPROVE recall.** `scripts/hotel_ceiling_v56.py` + `scripts/exp56_hotel_ceiling_agent.py`. Does not edit
`src/agent.py`, `src/agent_variants.py`, `src/rules_v2.py`, or `src/hybrid_facts.py` — all of Exp 40-52's
saved results and the code behind them are untouched. This is a new, standalone candidate tool, run
against the live guarded agent (`src/agent.py` + Exp 47's tool set, unmodified), with the disposition gate
kept exactly as-is per instruction: it correctly enforced the tool's answer before; the tool was wrong,
not the gate.

## The fix

`compute_hotel_ceiling()` applies the policy in the documented order and returns both the number and the
clause IDs used:

**base yearly ceiling (TRV-3.x, by tier and grade band) → effective circular (CIRC-25-06 Tokyo +5% from
2025-07-01, CIRC-26-04 India-T1 +6% from 2026-04-01) → eligible partner-hotel conference uplift (+20%
before 2026, +25% from 2026) → long-stay factor (>14 nights from 2025: ×0.9) → exception check.**

For X2-011: ¥34,000 base → ×1.05 (CIRC-25-06, transaction is 2025-08-18, after the 2025-07-01 effective
date) → ¥35,700. ¥34,986/night does not exceed ¥35,700 → compliant.

Used to replace **only** `check_hotel_compliance`'s ceiling lookup, in a fresh agent run — every other
tool, the system prompt, and the disposition gate are identical to the official Exp 47/51/52 configuration.

## One real regression found and fixed before the final run

The first version of `compute_hotel_ceiling` dropped a behavior the original tool had:
`agent_variants.lookup_hotel_ceiling` falls back to the lowest-ceiling tier for the country when a city
isn't in the public TRV-2.2 table (e.g. Chennai isn't listed at all). My first version returned a hard
error for an unlisted city instead. On X2-104 (bill from "Regency **Chennai** Hotel"; the employee's note
describes a stay at "Skyline **Mumbai** Hotel" — a bill/note city mismatch, correctly ignored in favor of
the bill's authoritative city per the tool's own design), that hard error sent the agent around the tool
entirely: it searched the policy corpus itself, read the raw **2026** ceiling table (wrong year for a
2025 transaction) off the retrieved text, and reached APPROVE — a new false approval. Restoring the same
country-level fallback the original tool had fixed it back to the correct ESCALATE with no other change.
This is why the plan's own warning ("a corrected tool response alone does not prove the agent's final
answer will change... test the wider set") mattered in practice, not just in principle.

## Results — all 18 development-split HOTEL-family cases, live, both tool versions run fresh

| Case | Ground truth | Before (original tool) | After (Exp 56 tool) |
|---|---|---|---|
| X2-011 | APPROVE | REJECT | **APPROVE** ✓ |
| X2-029 | APPROVE | REJECT | **APPROVE** ✓ |
| X2-139 | APPROVE | REJECT | **APPROVE** ✓ |
| X2-089, X2-143 | APPROVE | APPROVE | APPROVE (unchanged, already correct) |
| X2-132 (before CIRC-25-06's effective date) | REJECT | REJECT | REJECT (unchanged — correctly no uplift applied) |
| X2-148 (above ceiling even after adjustment) | REJECT | REJECT | REJECT (unchanged) |
| X2-104 (bill/note city mismatch + unlisted city) | ESCALATE | ESCALATE | ESCALATE (unchanged, after the fallback fix above) |
| remaining 11 cases | — | unchanged | unchanged |

**BEFORE: accuracy 13/18, APPROVE recall 2/5, false approvals 0/13**
**AFTER: accuracy 16/18, APPROVE recall 5/5, false approvals 0/13**

All three requested cases fixed. Both requested counterexample types (pre-circular date, above-adjusted-
ceiling) held correctly. Zero new false approvals, zero regressions on the final run. Real spend for this
experiment (both versions, 18 cases, live `gpt-4o-mini` agent turns): **$0.0119**. Cumulative project
spend: **$4.8448 of the $5.00 cap** (~$0.155 remaining).

## What this confirms about the project's own framing

Exp 53-55 already showed the single-shot LLM residual step cannot be trusted to apply even correct facts
reliably. This experiment shows the fix belongs exactly where the project's own established pattern says
it does: **in code, not in the model's hands.** With the ceiling computed correctly in code and the
disposition gate trusting that computation (not the model's own arithmetic), the agent's tool-calling
behavior itself was already correct — it called the right tools in the right order every time; the number
it was handed was wrong. That is an *agent-tool* failure, not a demonstrated retrieval/RAG failure: in
every trace reviewed for this experiment, `search_policy_corpus` was either not needed (`check_hotel_compliance`
alone was sufficient) or was only invoked after a tool error, not as part of normal reasoning.

## What this does not yet establish

This fix is scoped to hotel-ceiling cases specifically. The equivalent gap in `hybrid_facts.py`'s
`applicable_hotel_ceiling_local_currency` (used by the single-shot frozen-resolver path, not the agent)
was identified and separately validated as a pure calculation in Exp 53/55, but was not wired into a live
end-to-end resolver run here — that path's own grounding failures (Exp 55's finding that the model ignores
even correct facts) make it a different, already-documented problem, not one this fix addresses. This
result is also limited to the 18 dev-split HOTEL-family cases; it says nothing yet about the other 7
expense-type families' residual cases, or about validation/final_test (neither was touched, per
instruction).
