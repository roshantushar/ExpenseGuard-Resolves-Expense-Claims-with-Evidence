# Exp 61 — "Selective Automation V3": a pre-registered freeze, tested once on a second fresh holdout

**Status: reported exactly once, per the freeze manifest's own process rule — not tuned, not re-run.
This result includes a real false approval, disclosed in full below, not smoothed over.**

## Why this experiment exists

Exp 60 already showed the guarded candidate (Exp 59's tool fixes + Exp 60's require-tool gate)
generalizes to a fresh 50-case holdout. But Exp 60 itself was not pre-registered with Exp 32's level of
rigor — no manifest was committed before the holdout cases were generated. This experiment formalizes
that: `experiments/v3_freeze_manifest.yaml` names and pins the exact architecture under test
("Selective Automation V3" — the same candidate, given a version name for pre-registration purposes, not
new code) **before** a single one of this experiment's 30 holdout cases was generated, and commits to
reporting the result once, win or lose.

## Methodology

- 30 genuinely new cases (`X4-001`…`X4-030`), generated against a **second isolated copy** of the
  enterprise tables (`experiments/v3_holdout/enterprise_data/`) — the real dataset verified byte-for-byte
  unchanged before and after every step.
- Smaller than Exp 60's 50 by deliberate choice, disclosed in the manifest: each case needs individually
  authored enterprise rows and ground-truth cross-validation, and a rushed 50-case set carries real risk
  of the kind of ground-truth bug Exp 60 itself found (X3-049). 30 cases, reviewed carefully, was judged
  the better tradeoff — a real limit on this result's statistical precision, not hidden.
- Ground truth computed by the same independent reference implementation Exp 60 used
  (`dataset_generator.engine.evaluate()`), with the same real note-drafting pipeline for realistic,
  stylistically diverse notes (dictated, local-language, verbose, terse, secondhand).
- Same policy corpus, same enterprise-data schema, same frozen code paths as Exp 60 — only the case
  content and employee/date/amount combinations are new.

## A correction made during case design, before any model was run

The pass-1 ground-truth review (required by the pipeline before any note-drafting call, exactly as Exp 60
required) caught **5 case-design bugs of my own**, before anything was scored: several hotel/meal/mileage
cases that substituted a different employee than the validated template turned out to sit in a different
grade band, which silently changed the applicable ceiling and flipped the intended answer; one evidence-
conflict "no conflict" control accidentally triggered the conflict check through a reworded note. All 5
were caught by cross-checking against Exp 60's already-validated case shapes, fixed before any note was
drafted or any model called, and the final 30 cases all match their designed ground truth exactly. This
is disclosed as part of the process, not hidden — it is exactly the kind of review step this experiment
exists to demonstrate.

Two mileage cases (`X4-011`, `X4-012`) also hit the same note-drafting limitation Exp 60 already
documented (the drafting model sometimes misreads a distance figure into prose, e.g. "65 km" rendered
ambiguously) — the identical failure mode as Exp 60's `X3-013`/`X3-015`, not a new issue, kept in the set
on the same precedent.

## The result

**FROZEN RESOLVER (official, unmodified): accuracy 11/30 (36.7%), APPROVE recall 0/15, false approvals 0/15 (0.0% FAR)**
**V3 CANDIDATE: accuracy 20/30 (66.7%), APPROVE recall 9/15, false approvals 1/15 (6.7% FAR)**

The frozen resolver's lower accuracy here (36.7% vs. 44% on Exp 60, 60% on Exp 32) is a sampling effect,
not a regression: this 30-case set has a higher proportion of APPROVE-truth cases (15/30 = 50%) than
Exp 60 (20/50 = 40%) or Exp 32 (13/50 = 26%), and the frozen resolver has never once produced a correct
APPROVE on its own LLM-residual path across any evaluation this project has run (0/13 final test, 0/20
Exp 60, now 0/15 here) — a sample with more APPROVE-truth cases mechanically lowers its accuracy without
its behavior having changed at all.

## The V3 candidate did not hold 0% FAR this time — disclosed in full, not re-run

Unlike Exp 60 (0/30 false approvals for the same architecture), this run has **one real false approval**:
`X4-020`, a gift claim paid as a "prepaid e-voucher that can be redeemed at various outlets" — a cash
equivalent, which policy prohibits as a gift form. Traced live (diagnosis only; nothing was changed and
no rerun was performed, per the manifest's process rule):

```
check_gift_compliance -> "Within per-gift and annual ceilings, recipient details given, no prohibited form."
```

The require-tool gate worked exactly as designed: `check_gift_compliance` *was* consulted, so the APPROVE
was trusted. The actual gap is narrower and different from anything found before — the tool's own
free-text parsing of the claim's gift form did not recognize "a prepaid e-voucher redeemable at various
outlets" as a cash equivalent, unlike more explicit phrasing (e.g. "cash equivalent" stated directly) the
tool does handle correctly. This is a real, previously-undetected gap in how one compliance tool
interprets free text, not a failure of the gating architecture itself — the same general category of risk
disclosed but not yet fixed after Exp 60 (a tool consulted but given content that only superficially
satisfies its check), now with a second, concrete, numbered instance.

**No fix was applied.** Per the freeze manifest's process rule, this is documented as a finding for a
future experiment, not patched and silently re-run under this same manifest.

## Accuracy alone understates both the gain and the new risk — the safe-automation breakdown

| | Safely automated, correct | False approvals | False rejections (real approvable, wrongly blocked) | Unnecessary escalations |
|---|---|---|---|---|
| Frozen resolver | 10/30 = 33.3% | 0 | 15/30 = 50.0% | 0 |
| V3 candidate | 19/30 = 63.3% | **1** | 2/30 = 6.7% | 5 |

The frozen resolver again shows its real cost on this sample: half of all genuinely approvable claims are
wrongly blocked, invisible in its 0% FAR headline. The V3 candidate still cuts that false-rejection rate
by roughly 7x (50% → 6.7%) and nearly doubles safe automation (33.3% → 63.3%) — but, unlike Exp 60, it
does so at a nonzero false-approval cost here, not zero. Both facts are true and both are reported.

## What this does and does not establish

This is direct evidence that a 0% observed FAR on one 30- or 50-case sample does not mean the true
false-approval rate is zero — exactly the statistical caveat this project has stated but not previously
demonstrated empirically. It does not mean the V3 candidate is worse than previously reported; combined,
the candidate's two fresh-holdout runs are 0 false approvals in 30 non-approvable Exp 60 cases plus 1 in
15 non-approvable Exp 61 cases (1/45 ≈ 2.2% observed combined, with a wide confidence interval at this
sample size). It does mean: **the V3 candidate is not validated as 0% FAR**, and should not be described
that way going forward — it should be described as "0% FAR observed on Exp 60's 50 cases; 6.7% FAR
(1 case) observed on this second, smaller, pre-registered holdout; a real gift-form free-text parsing gap
identified and not yet fixed." The frozen resolver's 0% FAR claim is unaffected (0 false approvals across
all three independent evaluations — Exp 32, Exp 60, Exp 61 — now 82 non-approvable cases total with zero
false approvals).

Spend for this experiment's full pipeline (note generation + frozen/candidate comparison run): **$0.0954**
($0.0157 note-drafting + $0.0797 comparison run). Session total: **$7.38 of $8.00.**
