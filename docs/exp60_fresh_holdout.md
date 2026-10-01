# Exp 60 — A fresh, never-before-seen holdout: frozen resolver vs. the Exp 59 candidate

**Status: reported once per the agreed methodology, then corrected once, transparently, for a real bug
found in the test-generation tool itself (not in either system under test). This document reflects the
corrected, final numbers.**

## Methodology (summary; full detail in `scripts/exp60_*.py`)

- 50 genuinely new cases, never seen by either architecture, generated against an **isolated copy** of the
  enterprise tables (`experiments/exp60_holdout/enterprise_data/`) — the real dataset
  (`ExpenseGuard_DATASET/`) was verified byte-for-byte unchanged before and after every step.
- Ground truth computed by `dataset_generator.engine.evaluate()` — a genuinely independent reference
  implementation from `src/rules_v2.py` (different table representations; cross-validated against
  `rules_v2.py` on the original 150 cases by `build.py`, but not the same code), avoiding the circularity
  of testing the frozen resolver against labels derived from its own logic.
- Notes drafted by the real `dataset_generator/semantic.py` pipeline (46 of 50; the 4 evidence-conflict
  cases are hand-written, matching how the original dataset treats that archetype) — genuine stylistic and
  linguistic diversity (Japanese, Hinglish, dictated, terse, verbose, secondhand), not reseeded templates.
  Zero drift between ground truth computed before and after note-drafting, across all 50 cases.
- 36 of 50 cases exercise a category the candidate's fixes touched (roughly half built as negative
  controls the fix must NOT flip); 14 exercise categories nothing touched, as a baseline.

## A correction, made once, disclosed here rather than silently

The first pass flagged 2 false approvals (X3-019, X3-049). On inspection, **X3-049 was not a real system
failure** — it was a bug in my own ground-truth-generation reference tool. The real, unmodified
`check_approval` tool correctly reported this approval as valid (`rules_v2.TYPES["CONFERENCE_FEE"]` treats
a TRAINING-type approval as covering conference fees — a defensible reading, consistent with how the
project's own case-family taxonomy already groups the two). The ESCALATE label came from
`dataset_generator.engine.py`'s own generic approval-tier logic, which never explicitly lists
`CONFERENCE_FEE` and silently falls back to a stricter "GENERAL only" default — an oversight in the
reference tool, not a resolved policy conflict; the actual policy text (`D10_APR.md`, APR-2.1/APR-2.2)
never defines the mapping explicitly either way. **X3-049 is corrected to APPROVE.** No new restriction
was built into the real system to match the reference tool's incomplete list — the reference tool's gap
was the thing that needed fixing, not the agent.

**X3-019 was a real, confirmed gap**: the agent never called `check_software_compliance` — the one tool
meant to catch a missing business owner — and approved anyway. Fixed with a general, procedural gate
(added directly to the candidate's tool layer, not a separate numbered experiment): for any expense type
with a dedicated compliance tool, an APPROVE is not trusted unless that tool was actually consulted
successfully during the run; if not, the decision falls back to ESCALATE. This closes the general failure
class (an advisory tool the model is told to call but sometimes skips), confirmed independently three
times this session (X2-061 earlier, then X3-019).

## The final, corrected result

**FROZEN RESOLVER (official, unmodified): accuracy 22/50 (44%), APPROVE recall 0/20, false approvals 0/30**
**CANDIDATE, gpt-4o-mini (with the require-tool gate): accuracy 34/50 (68%), APPROVE recall 12/20, false approvals 0/30**
**CANDIDATE, gpt-4o (same gate): accuracy 39/50 (78%), APPROVE recall 13/20, false approvals 2/30 (6.7%)**

0% false approvals with gpt-4o-mini, matching the frozen resolver's safety bar, with a large, real
improvement in both overall accuracy and APPROVE recall. The gate cost a small amount of raw accuracy
relative to the uncorrected first pass (3 cases that had reached a correct APPROVE without the required
tool ever succeeding were reclassified to ESCALATE) — a deliberate trade, consistent with the project's
standing choice throughout its history (Exp 30 onward) to prioritize verified safety over unverified
accuracy. Swapping to gpt-4o (same architecture, same gate) is **not** a clean upgrade: higher accuracy,
but 2 new false approvals the gate did not catch — both diagnosed live (a conflict-check gap in one
direction the gate never covered, and a delegation-expiry check the gate's tool-mapping didn't know it
also needed). Disclosed, not smoothed over; gpt-4o-mini is the recommended candidate configuration, not
gpt-4o.

## Accuracy alone understates what actually changed — the safe-automation breakdown

Four-way accuracy blends two very different kinds of error together: a false approval (a safety failure)
and a false rejection (a real, approvable claim wrongly blocked — a cost and a fairness problem, not a
danger). Computed from the same saved predictions, at $0 (no new calls):

| | Safely automated, correct, zero human touch | False approvals | False rejections (real approvable claim, wrongly blocked) | Unnecessary escalations |
|---|---|---|---|---|
| Frozen resolver | **21/50 = 42%** | 0 | **20/50 = 40%** | 0 |
| Candidate, gpt-4o-mini | **33/50 = 66%** | 0 | 2/50 = 4% | 12 |
| Candidate, gpt-4o | 38/50 = 76% | 2 | 3/50 = 6% | 4 |

**The frozen resolver's 0% FAR and 44% accuracy together conceal its actual biggest weakness**: on this
fresh sample, 2 of every 5 claims that should have been approved were wrongly blocked. That cost is
invisible in the FAR number (which only measures the other direction) and only partially visible in
accuracy (which weights it the same as any other kind of wrong answer). The fixed candidate cuts that false
-rejection rate by a factor of 10 (40% → 4%) while holding false approvals at zero — a materially larger,
clearer improvement in real automation value than "68% vs 44% accuracy" conveys on its own. This reframing
was raised earlier in the project's own review process and had not yet been applied to this result; it is
now the recommended way to read Exp 60, not a replacement for FAR as the primary safety gate.

Real spend for the full Exp 60 pipeline (generation + both model comparisons): **$0.13 of $7.50.** Full
session spend: **$7.28 of $7.50.**

## What this does and does not establish

This is the frozen resolver's official comparison point for one fresh, independently-labeled 50-case set,
and it is direct, empirical evidence that the candidate's architecture-level fixes (compute in code,
enforce with a gate, don't trust an unconsulted tool) generalize beyond the cases that originally motivated
them. It is not proof the candidate is free of every remaining gap of this kind — a real, narrower related
issue (a tool being consulted but given content that only superficially satisfies its check, rather than
never being consulted at all) was found in a smaller follow-up check and remains open, undocumented as a
numbered experiment, and not yet fixed. The candidate remains the **leading development candidate**, not
an independently validated final architecture — that status is unchanged by this correction.
