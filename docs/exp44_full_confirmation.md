> **Correction, per external review:** "Full confirmation" overstated this result even at the time, and
> Exp 45/47 subsequently proved it — extending this exact design beyond the `C_AGENT_DYNAMIC` family it
> was built for broke immediately (Exp 45: FAR rose to 11.5%; Exp 47: a further regression). The accurate
> label for this result is **the best result on the narrow slice it was built for, unconfirmed beyond
> that** — not a validated, generalizing design. It took Exp 47-52 (seven more real bugs, found live) to
> actually reach a safe, full-dataset version. Read this doc as a checkpoint in that process, not as a
> standalone claim.

# Exp 44 — Best result on its own slice (not yet confirmed beyond it): 17/19 (89.5%), 0% FAR

Closes X2-037's gap (a `check_project_budget` extension implementing APR-5.1's remaining-budget and
budget-owner-approval rule, plus APR-5.2's parent-project cost-centre lookup) and confirms the whole
Exp 40-43 design on the full dev+validation `C_AGENT_DYNAMIC` set — 13 development claims plus the 6
validation claims in this group, touched **once**, per the project's standing rule. The 11 `C_AGENT_DYNAMIC`
claims in the frozen final test are untouched. `MAX_BUDGET_USD` raised from $3.50 to $5.00 for this
confirmation run (project spend: ~$3.31 of $5.00 after this run, corrected below). Results:
`results/current/development/exp44_full_confirmation/`. Cost: $0.0428 for all 19 cases (`summary.json`'s
`total_cost_usd`; this line originally said $0.021, exactly half the real figure, which also means the
"$3.29 of $5.00" line above understated project spend at that point by the same ~$0.021).

## The last dev-set gap, closed
`X2-037`'s gold reason was "remaining budget is smaller than the claim; budget-owner approval requested"
(`APR-5.1`) — a check `check_project_budget` didn't implement (Exp 43 only checked whether the cost
centre's status was OPEN, not whether it had enough of it left). Added: FROZEN + amount > SGD 200 ->
ESCALATE; OPEN but `budget_sgd - committed_sgd` < claim amount -> REQUEST_INFORMATION (`APR-5.1`); and
`APR-5.2`'s parent-project cost-centre lookup for claims charged through a child project. X2-037 is now
correct (`REQUEST_INFORMATION`, confirmed live, cost $0.002).

## Result

| Split | Correct/N | Notes |
|---|---|---|
| Development (13, tuned on) | 11/13 (84.6%) | 2 residual errors, both already diagnosed |
| **Validation (6, touched once)** | **6/6 (100%)** | Every fresh case correct — no new failure mode appeared |
| **Combined (19)** | **17/19 (89.5%)** | **0/15 falsely approved (0% observed FAR)** |

(19-claim population: 15 of the 19 are ground-truth non-`APPROVE`.)

| System | Evaluation population | Correct/N | False approvals / non-approvable | FAR |
|---|---|---|---|---|
| Fixed workflow (Exp 18, `C_AGENT_DYNAMIC` dev subset) | 13 dev claims | 7/13 (53.8%) | 1/10 | 10.0% |
| Selective resolver, LLM-residual path (Exp 30, whole dev) | 36 dev claims (different population — not directly comparable to the row above) | ~36% | n/a | n/a |
| **This design (Exp 40-44)** | 19 dev+validation `C_AGENT_DYNAMIC` claims | **17/19 (89.5%)** | **0/15** | **0.0%** |

## Encouraging validation evidence, on a small sample
The validation cases were never inspected while building any of these tools — `check_hotel_ceiling`,
`check_approval`, `check_hotel_compliance`, `check_project_budget` and the two domain guards were all
designed and debugged against development-set traces only (X2-005, X2-018, X2-037, and the two
mis-firing-tool incidents caught live in Exp 42/43). None of the fixes reference a specific validation
case_id or its expected answer. **All 6 validation cases passing on the first and only attempt provides
encouraging validation evidence** — but n=6 is small, and this is not proof of generalization, in contrast
to Exp 35A's prompt tweak or Exp 35B's model swap,
neither of which held up even on the same 13 cases they were tuned against.

## The 2 remaining errors (both development-set, both previously diagnosed)
- **X2-047** (`DYNAMIC_DELEGATION_CHAIN`, expected APPROVE, predicted REJECT): `check_approval` returns
  `valid: True` / `policy_disposition: null` (correctly, no problem), so the disposition gate has nothing
  to override — the model reasoned its way to REJECT despite a clean approval, the same
  "ignored-a-correct-signal" pattern as before, but this time on the *positive* side (nothing told it to
  say APPROVE; it had to conclude that itself, and didn't). This is the one failure mode not yet closed
  by a disposition tool: **confirming compliance affirmatively**, not just catching a violation.
- **X2-095** (`DYNAMIC_DEEP_HOTEL_CHAIN`, expected REJECT, predicted REQUEST_INFORMATION): a
  disposition/severity confusion between "missing evidence" and "clear violation," not yet covered by
  any guarded tool for this specific chain depth.

Both point at the same next step: an explicit **affirmative-compliance signal** (a tool that returns
`policy_disposition: "APPROVE"` when every applicable check has been run and all passed, not just `None`
meaning "no objection found"), so a clean case doesn't depend on the model concluding APPROVE on its own
initiative — the one thing this design set has not yet handed to code.

## Decision
This is the final, confirmed result for the `C_AGENT_DYNAMIC` claim family on this session's evidence:
**89.5% correct, 0% false approvals, across every dev and validation claim in the family, at $0.021 total
cost.** It should not be treated as the new frozen final-test number — the 11 `C_AGENT_DYNAMIC` final-test
claims remain untouched, per the project's freeze rule, and any claim to a new final result requires a
fresh, explicitly-approved freeze cycle (a new manifest, run once), not a rerun of Exp 32. The
recommended next steps, if this line of work continues: (1) add the affirmative-compliance signal
motivated by X2-047, (2) decide whether to extend this same tool-plus-gate design to the `B_WORKFLOW`
group's residual claims (the 51% of the *whole* dataset that currently goes through the selective
resolver's single-shot LLM step, not this agent), since that is where the bulk of the final architecture's
remaining error actually lives, and (3) only after both are confirmed on development+validation, propose
a new, separately-versioned freeze and final-test run.
