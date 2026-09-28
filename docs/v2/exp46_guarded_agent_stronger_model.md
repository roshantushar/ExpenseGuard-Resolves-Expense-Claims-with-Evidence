# Exp 46 — the guarded agent with a stronger model: still no, but the guards hold

Re-tests Exp 35B's question (does a stronger model help?) with the guarded-agent design instead of
the unguarded Exp 34 baseline. Same 19 `C_AGENT_DYNAMIC` dev+validation claims as Exp 44. Model:
`openai/gpt-4o` in place of `gpt-4o-mini`, identical tools/prompt/gate otherwise. Results:
`results/v2/development/exp46_guarded_gpt4o/`. Cost: $0.628 (vs. gpt-4o-mini's $0.021 for the same 19
cases — 30x).

## Result

| Model | Correct/19 | FAR | Avg turns | Cost |
|---|---|---|---|---|
| gpt-4o-mini (Exp 44) | **17 (89.5%)** | 0% | ~6 | $0.021 |
| gpt-4o (this experiment) | 15 (79.0%) | **0%** | 3.89 | $0.628 |

**The stronger model did worse, at 30x the cost — but false approvals stayed at 0% either way.** That
second point is the real finding: Exp 35B showed the *unguarded* agent's FAR jumping to 50% with gpt-4o
(more confident, more wrong); here, with the guards in place, model strength has no effect on the safety
property at all. The guards make FAR a property of the system design, not of which model happens to be
running it.

## Why gpt-4o still got 2 cases wrong that gpt-4o-mini got right
- **X2-026** (`DYNAMIC_DEEP_HOTEL_CHAIN`, expected ESCALATE): gpt-4o stopped after 3 turns — called
  `check_hotel_compliance` (correctly found the ceiling exceeded, no exception), and answered REJECT
  without ever calling `check_approval`. This family specifically layers an approval/delegation check on
  top of the hotel decision; gpt-4o-mini's slower, more turn-hungry exploration happened to catch both
  signals, gpt-4o's faster convergence caught only the first.
- **X2-055** (`MEAL_CLIENT`, expected APPROVE): a meal-ceiling case — a category with **no guarded
  tool**. gpt-4o retrieved the right clause and tried to do the per-attendee ceiling math itself,
  landing on REQUEST_INFORMATION. This is the same raw-reasoning-over-retrieved-text failure mode every
  model has shown all session; it is not fixed by a bigger model, only by a guarded tool.

## Decision
Do not switch to gpt-4o. gpt-4o-mini with the guarded design remains the best system found this session:
cheaper, more accurate, and equally safe. This closes the "would a stronger model fix it" question a
second time (Exp 35B, then this), now under the improved design: the answer is consistently no, because
the bottleneck was never raw model capability — it is the presence or absence of a guard for the specific
decision in question.
