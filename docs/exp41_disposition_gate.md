# Exp 41 — The disposition gate: beats the fixed workflow, at $0

**Cost: $0.** This is a pure re-scoring of Exp 40's already-collected trace data
(`results/v2/development/exp40_decision_in_code/traces.json`) — no new LLM calls. The gate is applied
*after* the model has already answered, so it changes nothing about how the model behaves; it only
changes whether the model's answer is trusted when a tool already computed the correct one.

## The finding that motivated it
Inspecting Exp 40's three remaining `DYNAMIC_DELEGATION_CHAIN` failures (X2-018, X2-047, X2-145) found
`check_approval()` had already returned the **exactly correct** `policy_disposition` in every case
(REQUEST_INFORMATION, valid/no-issue, and ESCALATE respectively — each matching the expected decision).
The model then ignored it: in at least one case it called `check_hotel_compliance` on what is actually a
meal claim, invented a "nightly rate... ceiling" framing that doesn't apply to meals at all, and
REJECTed based on that instead. This is the exact "ignores a correct resolved fact" pattern Exp 33
first documented, now isolated with a single clean cause per case.

## The fix
`gate_disposition()` generalizes Exp 40's `gate_approve`: scan the trace for any `policy_disposition`
a tool already returned. If exactly one distinct disposition is present and the model's final answer
disagrees with it, **override to the tool's disposition** — code is trusted over the model when they
conflict. If two tools return *different* non-null dispositions (a genuine conflict, e.g. the model
called the wrong domain tool and got a spurious second opinion), the safe answer is ESCALATE rather than
guessing which one is right.

## Result

| System | Correct/13 | FAR | HRR |
|---|---|---|---|
| Fixed workflow (Exp 18) | 7 (53.8%) | 10.0% | 30.8% |
| Decision-in-code (Exp 40) | 7 (53.8%) | 0.0% | 30.8% |
| **+ disposition gate (Exp 41)** | **9 (69.2%)** | **0.0%** | 53.8% |

**This is the first system this entire session to beat the fixed workflow outright**, not just tie it,
while keeping zero false approvals. Two of the three corrected cases (X2-128, X2-145) landed on ESCALATE
via the conflict path and happened to match the gold label exactly; X2-018 also moved to ESCALATE (still
short of the expected REQUEST_INFORMATION) because a spurious second disposition from the mis-called
hotel tool created a genuine conflict the gate correctly treats as unsafe to resolve on its own.

## What's still open
- **The wrong-tool-call problem is not fixed, only contained.** The model still calls
  `check_hotel_compliance` on non-hotel claims; the gate catches the resulting bad decision but produces
  a defensive ESCALATE rather than the precise right answer. A cheap follow-up: reject a
  `check_hotel_compliance` call outright when the claim's own parsed `expense_type` isn't `HOTEL`,
  the same poka-yoke principle applied one level earlier.
- **X2-037 and X2-095 remain wrong** for reasons unrelated to this gate (no `check_approval`/
  `check_hotel_compliance` disposition was ever computed for them — they need the equivalent treatment
  Exp 40 gave hotels and approvals extended to `DYNAMIC_PROJECT_BUDGET_CHAIN`'s CIRC-26-02 check, which
  Exp 33 already identified as a missing resolved-fact family).
- **n=13 still applies.** This should be confirmed on the full 30-claim group-C set before being treated
  as a stable number, though the mechanism (trust code over a model that already has the correct answer
  in its own context) is not the kind of thing that should behave differently on a larger sample.

## Decision
Adopt `gate_disposition` alongside Exp 40's tools. This is now the best-performing LLM-based system
measured in this entire project — ahead of the fixed workflow, the selective resolver's LLM-residual
step, and every other agent variant tried. The next highest-leverage step is extending the same
"resolve it in code, gate the model's answer against it" pattern to `DYNAMIC_PROJECT_BUDGET_CHAIN` and
blocking domain-mismatched tool calls outright, then re-validating on the full 30-claim set before any
claim of a new frozen number.
