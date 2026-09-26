# Experiment 19 — Agent-necessity audit

**Code:** `scripts/exp19_agent_audit.py` · **Output:** `results/development/exp19/summary.json` (per-case table)
**Scope:** the 10 agent-candidate cases in development and validation. The 5 in the final test were deliberately not touched.

## The four audit questions
1. **Can the path be decided before execution?** Not as a single linear checklist: the second tool depends on the travel record. But the whole decision tree is finite and enumerable in advance (three branches: `event_id` → conference lookup, `exception_id` → exception lookup, neither → stop).
2. **Does the first tool result change which tool is needed next?** Yes, for 7 of 10 (4 exception branches, 3 conference branches); in the other 3 the first result means no further lookup.
3. **Could a reasonable finite if/else workflow handle the class?** Yes, and it does. Implemented in Exp 18 with two `if` statements on the travel-request record.
4. **Does dynamic sequencing solve a real problem rather than add sophistication?** No. The maximum tool depth is two; there are three branches; there is no case where the workflow needs a tool the designer could not name in advance.

## Result
| Branch seen in the travel record | Workflow correct |
|---|---|
| `exception_id` → exception record | 4/4 |
| `event_id` → conference registration | 3/3 |
| neither | 0/3 |
| **Total** | **7/10** |

All three failures are the same case type: an over-ceiling hotel claim whose travel record shows neither an exception nor a conference. The workflow REJECTs; the labels say ESCALATE. This is a policy-interpretation question, not a sequencing problem, and an agent would face the same ambiguity. A counterfactual check shows that changing that one branch to ESCALATE would fix exactly those three cases and change no other development or validation case (only those 3 of 80 reach it). I did not adopt it, because that would be fitting three labels rather than following a policy clause.

## Conclusion
This is **Outcome B** from the plan: the fixed workflow solves the enterprise-evidence cases, and there is no evidence that model-directed tool sequencing adds anything. Dataset labels mark these 15 cases as `workflow_sufficient = false`; that is true of a linear checklist but not of a branching workflow.

## Consequence for the plan
Experiments 20 to 27 (agent, workflow vs agent, tool-set and description studies, ablations, parallel calls, loop and tool-confusion failures) are conditional on this gate and are **not run by default**. An optional bounded-agent control is possible if you want an empirical comparison; see the summary message.

## Addendum
After this audit, the "neither" branch was changed to ESCALATE for the freeze (see `exp32_freeze_and_runbook.md`). The 7/10 result above is the audit-time number; with the change the workflow gets 10/10 on these dev/val cases, which is not an independent result because the change was prompted by them.
