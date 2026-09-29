> **Superseded:** the "not adopted" verdict below was the right call at the time, but the missing
> category-specific guards this doc calls for were built immediately after (Exp 47-52). The corrected
> design reaches 44/70 (62.9%) dev **and** 21/30 (70.0%) validation, both at 0% FAR — see
> `exp47_52_full_coverage.md` and the updated `README.md`. Kept as-is below: the diagnosis (false
> approvals concentrated exactly in unguarded categories) is what motivated and shaped the fix.

# Exp 45 — resolver_v2 on the full 70-claim dev set: the coverage/safety trade-off

Tests whether the guarded-agent design validated on the `C_AGENT_DYNAMIC` family (Exp 40-44, 17/19,
0% FAR) holds up when applied to **every** dev claim, not just the 30 dynamic-chain ones. Code:
`src/resolver.py`'s `resolve_batch_v2` (new function; `resolve_batch`, the frozen Exp 30 path, is
untouched). Results: `results/v2/development/exp45_resolver_v2_full_dev/`. Cost: $0.067, 70 claims.

**Design:** identical deterministic routing to the frozen resolver (`deterministic()`, unchanged); only
the residual (non-conclusive) step changes, from the single-shot RAG+facts prompt to the bounded ReAct
agent with guarded tools (`check_hotel_compliance`, `check_approval`, `check_project_budget`) plus the
disposition gate.

## Result

| Path | Correct/N | Accuracy |
|---|---|---|
| Deterministic (unchanged) | 30/34 | 88.2% |
| LLM-residual v2 (guarded agent) | 21/36 | **58.3%** (vs. Exp 30's original 13/36 = 36.1%) |
| **Overall** | **51/70 (72.9%)** | vs. Exp 30's 43/70 (61.4%) |
| **FAR** | **6/52 = 11.5%** | vs. Exp 30's **0/52 = 0.0%** |

Residual-path accuracy nearly doubled system-wide, not just on the 19 cases it was tuned against — real
evidence the guarded-tool pattern generalizes. But false approvals rose to 11.5%, and every single one
of the 6 false approvals is in a category with **no guarded tool**: `DUPLICATE_CHECK`, `PERSONAL_SPEND`,
`GIFT_RULES`, `EMPLOYEE_MEAL_TEMPORAL` (x2), `GROUND_TRANSPORT`. Zero false approvals occurred in any
category a guarded tool actually covers (hotel, approval, software-project-budget).

## A tested, rejected stopgap
A blunt patch — refuse any agent-issued APPROVE outside the guarded categories (hotel, software) and
downgrade it to ESCALATE — was tested retroactively (free, no new LLM calls) against this run's own
saved trace: it brought FAR down to 1/52 = 1.9%, but accuracy fell back to 43/70 (61.4%), matching the old
baseline almost exactly. It works by blocking legitimate approvals along with the bad ones, so it isn't
a real improvement, just a wash. **Not adopted.**

## Decision
**Not frozen.** The frozen system remains Exp 30/32 (43/70 dev, 30/50 final test, 0/37 falsely approved) — this
project's standing priority has been 0% false approvals over raw accuracy since Exp 30 was chosen over
the more-accurate fixed workflow for exactly that reason, and this result would reverse that trade-off
without equivalent justification. The real fix is building the missing category-specific guards (meal
ceiling, gift rules, personal-spend/duplicate detection, ground transport) the same proven way
`check_hotel_compliance` was built, not a blanket restriction. Scoped as future work, not done this
session.
