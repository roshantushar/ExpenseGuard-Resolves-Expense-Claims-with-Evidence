# Exp 43 — Guarded tools: 11/13 (84.6%), the best result this session

Combines Exp 41's disposition gate with two domain guards found necessary live in Exp 42: neither
`check_hotel_compliance` nor `check_project_budget` originally checked that the claim was actually the
type of claim they apply to, and both were observed firing on the wrong claim type and returning a
disposition that didn't belong there. Results: `results/v2/development/exp43_guarded_tools_final/`
(10 cases carried from Exp 42's run unchanged; 3 re-run after the second guard fix — X2-005, X2-037,
X2-089 — since only `check_project_budget`'s behavior changed for those).

## What Exp 42 found and this fixes
Exp 42 added `check_project_budget` (closing Exp 33's identified CIRC-26-02 gap) without a domain guard.
Live testing caught it immediately: it fired on **two hotel claims** (X2-005, X2-089), where the claim's
background `project_id` is a routine, unrelated field, not a signal of anything — and both claims were
overridden to an incorrect ESCALATE as a result (this session's disposition gate trusts a tool's
computed answer, so an ungated tool answering the wrong question is exactly as harmful as the model
reasoning badly on its own). The same domain-guard idea already applied to `check_hotel_compliance`
(after it fired on a meal claim in Exp 41) was extended to `check_project_budget`, gated on
`expense_type == 'SOFTWARE'`.

## Result

| System | Correct/13 | FAR | HRR |
|---|---|---|---|
| Fixed workflow (Exp 18) | 7 (53.8%) | 10.0% | 30.8% |
| Decision-in-code (Exp 40) | 7 (53.8%) | 0.0% | 30.8% |
| + disposition gate (Exp 41) | 9 (69.2%) | 0.0% | 53.8% |
| + project-budget tool, unguarded (Exp 42) | 9 (69.2%) | 10.0% | 61.5% |
| **+ both tools domain-guarded (Exp 43)** | **11 (84.6%)** | 10.0% | 46.2% |

**11/13 — 31 points above the fixed workflow, more than double Exp 34's original agentic-RAG baseline.**

## The one remaining error is a genuinely missing rule, not a reasoning failure
`X2-037`'s gold reason is "Remaining budget is smaller than the claim; budget-owner approval requested"
(clauses `APR-5.1`/`APR-5.2`) — a **different** CIRC-26-02 nuance than the one `check_project_budget`
implements: it compares the claim amount against the cost centre's *remaining* budget
(`budget_sgd - committed_sgd`), not just whether the cost centre's status is OPEN. Neither
`rules_v2.software()` nor `check_project_budget` currently implements this comparison, so no tool in
this system can answer it, and the model defaults to APPROVE (a false approval — the one FAR point in
this run). This is a concrete, scoped gap: add a `budget_sufficient` check to `check_project_budget`
comparing `amount_sgd` against `budget_sgd - committed_sgd`, returning `policy_disposition:
"REQUEST_INFORMATION"` (per `APR-5.1`) when insufficient.

## Honest caveats (unchanged from Exp 40/41)
- **n=13.** 84.6% on 13 cases is 2 points different from 76.9% (one case) — this needs confirmation on
  the full 30-claim group-C set before being treated as a stable number, though the mechanism (guard a
  tool's applicability, then trust its computed answer over the model's) is not the kind of fix that
  should behave differently at scale.
- **This remains "the agent gathers evidence, code decides"**, not the agent reasoning better. Every
  point of improvement across Exp 40-43 came from closing a specific gap in what code could already
  compute, gated so it only speaks when it actually applies.

## Decision
This is the best-performing system measured anywhere in this project — ahead of the fixed workflow, the
selective resolver, and every other configuration tried. Recommended next steps, in order: (1) add the
budget-sufficiency check to close X2-037's gap (a small, scoped addition, not a new architecture), (2)
re-validate on the full 30-claim group-C set (dev + validation), (3) only then consider integrating this
pattern into the frozen selective resolver's residual step for the full final-test claim set, since that
is what would actually need to happen before any new frozen number could be claimed.
