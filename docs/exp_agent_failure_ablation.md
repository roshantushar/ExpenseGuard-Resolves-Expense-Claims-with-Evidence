# Reproduced agent failures (problem.md §38)

An agent survived the necessity gate (Exp 20, and later Exp 34-52), so `problem.md` §38 requires
reproducing at least two failure modes by temporarily removing a guardrail and measuring what happens. This
was not done during the original experiment sequence — found missing by an independent audit — and is run
here rather than left descoped, since the free local model made it possible at $0 cost despite the
project's paid budget being nearly exhausted ($0.35 of $5.00 remaining at the time).

Script: `scripts/v2/exp_agent_failure_ablation.py`. Model: `llama3.2:3b` (Ollama, free). Cases: X2-005,
X2-037, X2-145 — three `C_AGENT_DYNAMIC` development claims already used elsewhere in this project's docs
(demo script, Exp 28's base claim), so results are easy to cross-check. Neither ablation edits
`src/agent.py`; each is a standalone copy of its loop, so there is nothing to "restore" in shipped code.
Total cost: **$0.00** (all three conditions, all three cases).

## Failure A — de-duplication and step cap removed

A copy of the agent loop with the `seen`-call cache removed (every tool call executes fresh, even an exact
repeat) and the normal 8-step cap replaced by a 20-step ceiling (a genuinely uncapped loop cannot be run
safely against a live model; this bounds the worst case while still removing the cap as the thing that
would otherwise stop a loop early).

| Case | Baseline (guarded) | No dedup / high ceiling | What happened |
|---|---|---|---|
| X2-005 | REJECT, 7 turns | REJECT, 7 turns, 6 calls, **2 repeated** | Minor drift, still resolved correctly |
| X2-037 | ESCALATE, 8 turns (step-cap hit even *with* guardrails) | **No decision reached. Hit the 20-step ceiling with 20 calls, 19 of them exact repeats of an earlier call.** | **A real, reproduced loop** |
| X2-145 | REJECT, 6 turns | REJECT, 6 turns, 5 calls, 1 repeated | Minor drift, still resolved correctly |

**X2-037 is the reproduced failure this section exists to demonstrate.** Without de-duplication, the model
got stuck re-issuing the same tool call 19 times in a row and never produced a final decision at all —
not a near-miss, a genuine unresolved loop. Note this case *already* hits the normal step cap even with
guardrails intact (8/8 turns, correctly falling back to ESCALATE) — it was already the hardest of the
three cases, and removing dedup turned a guarded, safe step-cap fallback into an unguarded, unresolved
loop. The other two cases show the guardrail matters less when the model isn't already struggling — dedup
and the step cap are a safety net for the hard cases, not a constraint that changes behavior on the easy
ones.

## Failure B — vague, overlapping tool descriptions

The real loop (dedup and step cap both intact — isolates tool-description quality as the one variable),
every tool's description replaced with a short, generic, overlapping sentence (e.g. `search_policy_corpus`
and every enterprise tool both described only as "Looks something up." / "Gets some info.").

| Case | Baseline (real descriptions) | Vague descriptions | What happened |
|---|---|---|---|
| X2-005 | REJECT, 7 turns | REJECT, 5 turns, 1/4 wrong-tool calls | Slightly worse tool selection, same final answer |
| X2-037 | ESCALATE, 8 turns | ESCALATE, 8 turns, 3/8 wrong-tool calls | More wrong-tool calls, same final answer, still step-cap-limited |
| X2-145 | REJECT, 6 turns | **ESCALATE**, 8 turns, 0/4 wrong-tool calls, step-cap hit | **Final decision changed** |

X2-145 is the more interesting reproduced failure here: with vague descriptions, the model didn't
necessarily pick a "wrong" tool by the narrow found/not-found heuristic, but took a different, longer path
through the tool catalogue, hit the step cap, and landed on a different final decision (ESCALATE instead of
the correct REJECT) — degraded tool descriptions changed the *outcome*, not just the call count, even on a
case that resolved cleanly with real descriptions.

## What this demonstrates

Both required failure modes are now reproduced with real numbers, not asserted: removing de-duplication can
turn an already-hard case's safe step-cap fallback into a genuine unresolved loop (X2-037), and vague tool
descriptions can flip a correct decision to an incorrect one even without a clean "wrong tool" signal
(X2-145). This is direct evidence — not a design argument — for why `src/agent.py`'s guardrails
(call deduplication, the step cap, precise tool descriptions) are load-bearing rather than defensive
boilerplate.

## What this does not show
Three cases is enough to reproduce the failure mode `problem.md` §38 asks for, not enough to quantify its
rate across the full case population. This is a targeted reproduction, not a new benchmark — no existing
result changes because of it, and the normal, guarded loop (`src/agent.py`, unmodified) is what every other
experiment in this project actually used.

Raw output: `results/v2/development/exp_agent_failure_ablation/results.json`.
