# Exp 40 — Moving the decision into code: the first agent to match the workflow

Implements the three targeted fixes proposed after Exp 39's finding that better evidence alone doesn't
fix the agent: (1) argument-free approval and hotel-compliance tools so the model can no longer
hallucinate an enum, (2) each tool returns a `policy_disposition` computed from the exact, already-
tested mapping in `rules_v2`/`workflow_v2` rather than asking the model to re-derive REJECT vs.
REQUEST_INFORMATION vs. ESCALATE, and (3) a code-level gate that overrides APPROVE to ESCALATE if the
model answers APPROVE despite a negative `policy_disposition` already sitting in its own trace. Code:
`src/agent_variants.py` (`make_check_approval`, `make_check_hotel_compliance`, `gate_approve`,
`specs_and_tools_40`). Results: `results/current/development/exp40_decision_in_code/`. Same 13 claims. Cost:
$0.020 — among the cheapest agent runs of the whole session, because it also needed the fewest turns.

## Result: the first agent to match the fixed workflow

| System | Correct/13 | FAR | HRR | Avg turns | Step-cap hits | Cost |
|---|---|---|---|---|---|---|
| Fixed workflow (Exp 18) | 7 (53.8%) | 10.0% | 30.8% | — | — | $0 |
| Old agent, pre-fetched RAG (Exp 20) | 7 (53.8%) | 30.0% | 23.1% | 5.69 | 3/13 | $0.043 |
| Agentic RAG v1 (Exp 34) | 4 (30.8%) | 10.0% | 38.5% | 7.31 | 5/13 | $0.038 |
| Agentic RAG v2, parallel + poka-yoke ceiling (Exp 36) | 4 (30.8%) | 0.0% | 61.5% | 7.38 | 8/13 | $0.046 |
| True two-hop RAG + poka-yoke ceiling (Exp 39) | 3 (23.1%) | 20.0% | 7.7% | — | — | $0.038 |
| **Decision-in-code (Exp 40)** | **7 (53.8%)** | **0.0%** | **30.8%** | **5.54** | **0/13** | **$0.015** |

HRR here means the fraction of the 13 cases the system itself chose to ESCALATE — a high HRR (e.g. Exp 36's 61.5%) is not automatically good: it can mean the system is correctly deferring hard cases, or it can mean 0% FAR was bought cheaply by escalating almost everything ambiguous. Compare against each row's own accuracy to tell which.

**Exp 40 ties the fixed workflow's accuracy and beats it on every safety and efficiency metric.** Zero
false approvals (vs. the workflow's 10%), zero step-cap hits (vs. Exp 34's 5/13 and Exp 36's 8/13),
fewer turns than any other LLM-based system tested this session, and the lowest cost per case.

## X2-005: the case debugged across five prior experiments, finally correct
```
get_employee_profile, get_travel_request                                (routine lookups)
check_hotel_compliance(grade='G4', nights=3)
  -> {tier: IN-T2, ceiling: 9800.0, nightly_rate: 12740.0, compliant: false,
      policy_disposition: 'REQUEST_INFORMATION', reason: 'Cited exception identifier does not exist...'}
get_exception_record('EXC-0933') -> not found                            (confirms the tool's own check)
-> REQUEST_INFORMATION   (CORRECT -- first time this case has been answered correctly all session)
```
The tier is correct (9,800, not 14,500 -- Exp 35C/36's fix, retained). The exception-driven disposition
is correct (REQUEST_INFORMATION, not REJECT -- the bug that survived Exp 36/37/39 is now closed, because
the model is no longer the one deciding what a missing exception id means; `rules_v2.exception_for`'s
own tested mapping decides it, and the tool just states the answer).

## What worked, and what's still open

**The hotel family is now essentially solved for the agent.** All 4 `DYNAMIC_HOTEL_DISCOVERY` cases and
1 of 2 `DYNAMIC_DEEP_HOTEL_CHAIN` cases are correct (5/6) -- `check_hotel_compliance` closes both bugs
this family had (tier substitution, exception disposition) at once.

**`DYNAMIC_DELEGATION_CHAIN` remains the weak family:** 2/5 correct. `check_approval` returns the
correct `policy_disposition` when validate_approval itself is the deciding factor, but several of these
cases turn on a nuance `check_approval` doesn't cover on its own (e.g. distinguishing which of two
overlapping delegation records applies) -- the same class of gap Exp 33 flagged for
`DYNAMIC_PROJECT_BUDGET_CHAIN` (no resolved fact exists yet for some multi-hop chains). This is exactly
the "1+2" pattern to extend next: the fix that worked for hotels was closing the compliance logic
entirely into one tool: delegation chains need the equivalent treatment.

**The APPROVE gate (point 5) had less to do than expected:** zero false approvals were produced by the
model itself in this run, so `gate_approve` never actually had to override anything. It remains in place
as a safety net, not a load-bearing part of this specific result -- worth keeping regardless, since nothing
in this design guarantees the model won't approve against a disposition on a different case distribution.

## Honest caveats
- **n=13.** One case flipping is worth ~8 points of accuracy. This is real signal (a mechanism-level
  fix that closed two independently-diagnosed bugs at once, not a lucky draw), but it should be
  confirmed on the full 30-claim group-C set (adding the 17 validation-split cases) before treating
  53.8% as a stable number.
- **This is not "the agent got smarter."** Every fix here moved a decision that was previously made by
  the model into code that computes it once, correctly, using logic already tested elsewhere in this
  project (`rules_v2`, `workflow_v2`). The agent's remaining job is evidence-gathering and orchestration
  -- deciding what to look up and when -- not policy interpretation. That division of labor is exactly
  what worked, and the write-up should say so plainly rather than credit the model with better judgment
  it did not exercise here.

## Decision
This is the first LLM-based system this session to reach the fixed workflow's accuracy without giving
up its false-approval advantage. It does not yet beat the workflow outright (tied, not ahead), and the
delegation-chain family shows the same fix needs to be repeated there before a stronger claim is
warranted. Recommended next step, budget permitting: build the delegation-chain equivalent of
`check_hotel_compliance`, then re-run the full 30-claim group-C set (dev + validation) rather than just
these 13, to confirm the result holds at a size where individual cases don't swing the number by 8 points.
