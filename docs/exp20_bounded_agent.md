# Exp 20 — Bounded single agent pilot (development, group-C claims)

Notebook: `notebooks/exp20_bounded_agent.ipynb`. Results: `results/current/development/exp20_bounded_agent/` (predictions, full traces, summary). Cost: $0.0432. Run regardless of Exp 19's audit conclusion, as agreed.

**Question:** does a real, model-directed ReAct agent beat, tie, or lose to Exp 18's fixed workflow on the same 13 group-C claims?

**Result: exact tie, 7/13 each — but on different cases.**

| | Correct | False approvals (of 10 non-approvable) | Avg turns | Step-cap hits | Wrong-tool calls |
|---|---|---|---|---|---|
| Workflow (Exp 18) | 7/13 | 1/10 | — | — | — |
| Agent (Exp 20) | 7/13 | 3/10 | 5.69 | 3/13 | 20 total |

**The standout finding: complementary, not equal, errors.** The two methods' correct sets overlap on only 3 claims (X2-089, X2-095, X2-142). Together they solve **11 of 13 (85%)** — each gets right several cases the other misses. Only X2-037 and X2-104 (the two hardest chains) are missed by both. This is direct evidence for a selective architecture rather than committing to one method for every dynamic case.

**Safety:** the agent's false-approval rate (30%) is well above the workflow's (10%) and above the 10% guardrail — independent model-directed reasoning here is more prone to premature APPROVE.

**Orchestration cost:** average 5.69 of 6 turns used, 3/13 runs hit the step cap (all safely fell back to ESCALATE), and 20 wrong-tool-calls across 13 cases (~1.5/case) from guessed identifiers or premature calls.

**Decision:** combining Exp 19's audit (no case structurally requires agentic reasoning) with this measured tie-with-worse-safety-and-cost result, **a bounded agent is not justified as a wholesale replacement for the fixed workflow.** Exp 21-27 (ablations contingent on the agent adding value) are not warranted as a general change. The complementary-error finding is carried into Exp 30: a selective router trying the workflow first, falling back to the agent only on its known-weak families, could recover several of the 6 cases unique to one method without paying the agent's cost everywhere. Next: Exp 28 (guardrails).
