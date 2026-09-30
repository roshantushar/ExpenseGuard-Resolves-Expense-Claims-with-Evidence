# Exp 35 — Isolating the fix across layers: prompt vs. model vs. tool interface

Code: `src/agent_variants.py` (35A prompt, 35C tool interface), `scripts/v2/exp35_isolate_fix.py`.
Results: `results/v2/development/exp35_isolate_fix/`. Same 13 `C_AGENT_DYNAMIC` development claims as
Exp 18/19/20/34, so every row below is directly comparable. One variable changes per row relative to
the Exp 34 baseline (gpt-4o-mini, default prompt, default tools: 4/13).

**Question:** Exp 33/34 both found the same failure — the model ignores TRV-2.2's stated closed-world
fallback rule ("a city not listed takes the lowest tier for its country") and substitutes a more
familiar tier instead (Chennai should use IN-T2's 9,800 ceiling; the model kept using IN-T1's 14,500).
Which layer actually fixes it: a stricter prompt, a stronger model, or a safer tool interface?

## The 6-row comparison

| System | Correct/13 | FAR | HRR | Avg turns | Step-cap hits | Cost (13 cases) |
|---|---|---|---|---|---|---|
| Fixed workflow (Exp 18) | **7 (53.8%)** | 10.0% | 30.8% | — (no LLM) | — | $0 |
| Old agent, pre-fetched RAG (Exp 20) | 7 (53.8%) | 30.0% | 23.1% | 5.69 | 3/13 | $0.043 |
| New agent, agentic RAG (Exp 34 baseline) | 4 (30.8%) | 10.0% | 38.5% | 7.31 | 5/13 | $0.038 |
| **35A — prompt fix** | 4 (30.8%) | **30.0%** | 7.7% | 6.69 | 0/13 | $0.040 |
| **35B — stronger model (gpt-4o)** | 4 (30.8%) | **50.0%** | 7.7% | 6.77 | 1/13 | $0.720 |
| **35C — tool-interface fix (unconfounded)** | 3 (23.1%) | 10.0% | 30.8% | 7.23 | 4/13 | $0.028 |

*(`rules_v2.py` alone, the non-AI baseline: 6/13, FAR 30% — included for reference in Exp 34's own doc.)*

## What each layer actually did

**35A (prompt):** added an explicit "list every city in the table, verify membership before using a
row" instruction plus a tighter stopping rule. It worked exactly as intended *mechanically* — step-cap
hits dropped from 5/13 to 0/13 and average turns fell — but **accuracy did not move (still 4/13) and
false approvals tripled (10%→30%)**. Telling the model to stop earlier made it commit to a wrong
answer with *less* verification, not more; the underlying substitution error was never actually fixed,
it just got expressed with more confidence and fewer safety-net step-cap escalations.

**35B (model): the most striking and counter-intuitive result.** gpt-4o costs ~19x gpt-4o-mini per
case ($0.055/case average vs. mini's ~$0.003) and ties mini's accuracy exactly (4/13) — but its false
approval rate is **50%**, five times mini's own baseline and the worst number of any system tested this
entire session. It approved 7 of 13 claims, five of them wrongly (X2-037, X2-087, X2-104, X2-142,
X2-145 — mostly ESCALATE-expected cases it approved outright). A stronger model was not more careful
here; it was more *confidently* wrong, more willing to conclude APPROVE from partial evidence. This is
the opposite of what "use a stronger model" is usually assumed to buy you, and cost 17x more to get it.

**35C (tool interface): the only layer that measurably fixed the targeted bug, though not the case
overall.** The first attempt (offering `lookup_hotel_ceiling` alongside the old `check_rate_ceiling`)
found only 3/13 cases even called the new tool — **zero of them the Chennai/Kobe cases it was built
for** — because the model defaulted to the familiar tool when both were available (a textbook
tool-confusion result). Removing the competing tool entirely raised adoption to 11/13, and a further
bug found live (the tool required grade as a bare int, but `get_employee_profile` returns `"G4"`; the
model kept passing the string and the calls failed) was fixed mid-experiment. With both problems
resolved, **`lookup_hotel_ceiling` returned the exactly correct ceiling for X2-005 (9,800, not
14,500) and the model's own explanation cited that correct number** — the original tier-substitution
bug is gone for this case. But X2-005 was still marked wrong overall: with the correct ceiling in hand,
the model treated "nightly rate exceeds ceiling, and the cited exception doesn't exist" as a flat
REJECT rather than REQUEST_INFORMATION (asking for a valid exception reference) — a second, independent
reasoning gap the tool fix was never meant to touch. Overall group accuracy (3/13) also did not improve,
because the other delegation/project-chain cases in this set have their own, unrelated failure modes
untouched by a hotel-ceiling-specific fix.

## Reading this against the PE6201 reliability framing
Exp 34's own numbers (workflow 7/13 with 0 LLM turns; the new agent 4/13 at 7.3/8 average turns; 5/13
step-cap hits) are consistent with treating each additional agent turn as another chance for the
model's per-step reliability to compound against it — more autonomy without fixing the underlying
per-step reliability made things worse, not better, exactly as the earlier finding predicted. Exp 35
adds the harder result: **none of the three most natural per-step fixes (a stricter prompt, a stronger
model, a safer tool interface) raised overall accuracy above the workflow's 7/13 on this set.** The
tool-interface layer is the only one that demonstrably fixed the specific bug it targeted when actually
used — but "when actually used" is doing real work in that sentence: an ACI fix only helps if the model
chooses the safer tool over an available unsafe one, and even then it only closes the one failure mode
it was built for.

## Decision
No system tested in Exp 34/35 beats the plain fixed workflow (7/13, $0, no LLM calls, more accurate and
safer than every LLM-based variant except the tool-interface fix's FAR, which only ties it). The
practical takeaway for this dataset is unchanged from Exp 30: prefer the deterministic path wherever it
resolves conclusively, and treat every additional degree of agent autonomy as a cost that needs to earn
its keep, not something to add by default. If this line of work continues, the two highest-leverage
next steps are (a) removing unsafe/overlapping tools rather than merely adding safer ones alongside
them, and (b) separately targeting the exception-vs-rejection disposition gap 35C's own result
surfaced, since it is now the single remaining, independently confirmed defect on the flagship case.
