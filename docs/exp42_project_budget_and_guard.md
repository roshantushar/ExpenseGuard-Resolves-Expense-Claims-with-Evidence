# Exp 42 — check_project_budget, and catching an unguarded tool live

Adds `check_project_budget` (closing the `DYNAMIC_PROJECT_BUDGET_CHAIN` gap Exp 33 identified: no
resolved-fact family existed for CIRC-26-02's active-project-record check) alongside Exp 41's
disposition gate and Exp 40's existing tools. Code: `src/agent_variants.py` (`make_check_project_budget`,
`specs_and_tools_42`). Results: `results/v2/development/exp42_project_budget_and_guard/`. Same 13
development claims. Cost: $0.027 (plus $0.001 for a 3-case confirmation re-run after the fix below).

## Result: same accuracy, worse safety — a new tool without a domain guard

| System | Correct/13 | FAR | HRR |
|---|---|---|---|
| + disposition gate (Exp 41) | 9 (69.2%) | 0.0% | 53.8% |
| **+ project-budget tool, unguarded (this experiment)** | 9 (69.2%) | **10.0%** | 61.5% |

Accuracy held, but a live regression appeared immediately: `check_project_budget` had no domain guard
(unlike `check_hotel_compliance`, already guarded after an earlier incident) and fired on **two hotel
claims** (X2-005, X2-089), where the claim's background `project_id` is a routine, unrelated field. Both
were incorrectly overridden by the disposition gate to ESCALATE, and a third case (X2-037) became a new
false approval for an unrelated reason (the tool's project-active/cost-centre-open check didn't cover
the actual rule this claim needed — a remaining-budget comparison, `APR-5.1`).

## The fix, verified live
Added the same domain guard already proven for `check_hotel_compliance`: `check_project_budget` now
refuses to run unless `expense_type == 'SOFTWARE'`. Re-running the two affected hotel claims confirmed
both recovered to their correct answers (X2-005: REQUEST_INFORMATION; X2-089: APPROVE) — see Exp 43 for
the combined, corrected result.

## Decision
This is exactly the same lesson as the model calling `check_hotel_compliance` on a meal claim earlier:
**a composite tool that computes a disposition is only safe if it also knows when it doesn't apply.**
Every new guarded tool needs this check from the start, not added reactively after an incident. Carried
forward into Exp 43/44's final design.
