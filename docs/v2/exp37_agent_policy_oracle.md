# Exp 37 — Policy oracle for the agent: does perfect policy retrieval fix it?

Mirrors Exp 11 (the single-shot resolver's policy oracle) but for the agent architecture: isolates
whether the agent's failures trace to retrieval quality, or survive even with perfect evidence. Code:
`src/agent_variants.py` (`make_oracle_policy_tool`, `SYSTEM_ORACLE`). Results:
`results/v2/development/exp37_agent_policy_oracle/`. Same 13 `C_AGENT_DYNAMIC` development claims as
Exp 18/19/20/34/35/36. Cost: $0.029.

**Design:** `search_policy_corpus` is replaced by `get_correct_policy_excerpts()`, a tool that returns
`policy.render(required_policy_ids + supporting_policy_ids)` straight from the **private ground truth**
— the exact, complete, minimal set of controlling clauses, with no retrieval noise, no distractor
chunks, nothing to search for. This is an evaluator-only diagnostic exactly like Exp 11/16: it could
never exist in a real system, since it requires already knowing the answer's controlling clauses.
Everything else (enterprise tools, `check_rate_ceiling`, the loop, the model) is identical to Exp 34's
baseline — retrieval quality is the only variable changed.

## Result: no improvement. It got worse.

| System | Correct/13 | FAR | HRR |
|---|---|---|---|
| Agentic RAG v1 (Exp 34, real retrieval) | 4 (30.8%) | 10.0% | 38.5% |
| **Agent + perfect policy oracle (Exp 37)** | 4 (30.8%) | **40.0%** | 30.8% |

Accuracy is **exactly unchanged** (4/13). False approvals nearly quadrupled, from 10% to **40%** — the
second-worst safety number recorded this entire session (only gpt-4o, Exp 35B, was worse, at 50%).

## The proof, on the flagship case
X2-005's oracle text includes, verbatim, TRV-2.2's full location-tier table **and** its fallback
sentence ("a city not listed takes the lowest tier for its country"), among only 8 short clauses with
zero distractors:

```
get_correct_policy_excerpts() -> [TRV-3.3, TRV-2.1, TRV-6.1, EXC-1.2, EXC-2.1, TRV-1.1, TRV-2.2, EXC-2.2]
                                   (TRV-2.2's table and fallback sentence are right there, verbatim)
check_rate_ceiling(amount=38220, nights=3, ceiling=14500)   <- still IN-T1, still wrong (should be 9,800)
-> APPROVE   (WRONG -- false approval; expected REQUEST_INFORMATION)
```

This is the cleanest possible test of the hypothesis that retrieval quality is the bottleneck, and it
fails decisively: with the correct clause handed directly, with nothing to find and nothing to filter
out, the model still picked the wrong tier from the table it was just given.

**And it isn't only X2-005.** Of the 4 false approvals in this run, **3 are the same
`DYNAMIC_HOTEL_DISCOVERY` family** (X2-005, X2-104, X2-128) making the identical tier-substitution
error on different claims, even with each one's own correct clauses handed directly. This is a
consistent, repeatable defect in how the model reads and applies this specific kind of table, not a
one-off mistake on one case.

## Answer to the question this experiment was built to answer
**No — giving the agent the correct policy does not make it work well.** This decisively rules out
retrieval/evidence-quality as the explanation for Exp 34's poor performance. Combined with Exp 35/36
(prompt fix, stronger model, tool-interface fix, parallel turns — none of which raised accuracy above
4/13 either), the picture is now complete: **every layer that could plausibly be blamed — retrieval,
prompt wording, model strength, tool interface, turn budget — has been tested in isolation, and none of
them is the fix.** The defect is in the model's own reading comprehension and judgment when applying a
closed-world fallback rule, and it survives being handed the answer's own controlling clauses directly.

## Decision
This closes out the diagnostic line of work from Exp 33 onward. No further "give it better X" variant
is likely to help without a fundamentally different mechanism (e.g. code-level verification of table
membership rather than asking the model to read it correctly, which is what the deterministic path
already does by construction). The selective resolver (Exp 30) remains the frozen, final architecture:
it wins not because its LLM step is good, but because it is designed to expose that step to as few
decisions as possible.
