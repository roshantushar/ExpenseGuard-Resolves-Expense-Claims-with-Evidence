# Exp 59 — "Fix them all": final results (live, dev-only, candidate not shipped)

**Status: candidate, not shipped.** `scripts/exp59_final_fix.py` + `scripts/exp59_full_dev_run.py`.
Extends Exp 56-58's pattern across every gap in the Exp 58 failure report. Nothing in `src/` is edited.
Development split only — validation and final_test were not touched by this experiment.

## Final result — all 70 development-split cases, live, same day, both variants run fresh

**BEFORE (original, unmodified Exp 47 agent + routing): accuracy 55/70, APPROVE recall 11/18, false approvals 2/52**
**AFTER (Exp 59 fixes): accuracy 67/70, APPROVE recall 18/18, false approvals 1/52**

+12 accuracy, +7 APPROVE recall (18/18 — every real approvable dev case now resolves correctly), false
approvals cut in half. Real spend across all of Exp 56-59's live testing this session:
**$5.19 of the $6.00 cap** (cap raised from $5.00 with explicit authorization).

## What was fixed, and how confident each fix actually is

Two different kinds of fix went into this, and they deserve different confidence levels:

**Code-enforced (a gate checks the outcome regardless of what the model does) — high confidence:**
- Hotel ceiling calculation (base → circular → partner uplift → long-stay), Exp 56, reused here. Fixes
  X2-011, X2-029, X2-139.
- Hotel exception-status gap (`INVALID` status defaulting to the wrong disposition). Fixes X2-012.
- Evidence-consistency check (bill/note category conflict) — initially just an advisory tool, which a live
  run showed the model skip calling on one pass (X2-061 approved outright). **Promoted to an unconditional
  gate** that runs the same check in code regardless of the model's tool-calling behavior. Fixes X2-061,
  and the same fixed word-boundary/decoy-sentence-aware check applied to the deterministic routing path
  fixes X2-028, X2-089, X2-117.
- Gift-recipient government check — found *during* this final validation pass: `check_gift_compliance`
  trusts the model's own `recipient_type` argument with no code check. X2-054 (a gift to "Kanto Regional
  Development Authority," in a Japanese-language note) was correctly REJECTed in one run and wrongly
  APPROVEd in the next, identical code, temperature 0 — the model classified the same recipient as
  `GOVERNMENT` once and `EXTERNAL` the next time. Added a gate that checks the note text directly for
  government/statutory/public-sector keywords, regardless of what the model passes. Verified this holds
  the correct REJECT across repeated runs after the fix.
- Duplicate-detection gap: `workflow_v2.duplicates()` (frozen, used by the agent's `check_workflow_compliance`)
  is missing the `same_kind()` category check that the correct, frozen `rules_v2.duplicates()` has.
  Cross-verified against the correct function before trusting a DUP-1.2 signal. Fixes X2-078.
- Relative-date parsing in the deterministic routing itself (`rules_text.py` cannot compute "21 days
  later" / "28 days after the booking date," silently leaving a wrong departure date that made the
  deterministic path confidently resolve two airfare claims incorrectly before they ever reached the
  agent). Fixed as a routing-level correction, plus a "biz" → BUSINESS cabin synonym. Fixes X2-028, X2-080.
- Two new tools with no prior code-level check at all: `check_mileage_compliance` (odometer-to-distance
  arithmetic moved into code, Exp 58) and `check_airfare_compliance` / `check_training_compliance` (new
  this experiment, mirroring `rules_v2.airfare()`/`training()` exactly). Fixes X2-088, X2-080 (cabin/
  exception side), X2-112.

**Prompt-dependent (no code enforcement, relies on the model following instructions) — lower confidence,
observed to be unstable:**
- Meal attendee counting, moved from a single `external_attendees` number to `attendee_role_counts`
  (explicit per-role counts, classifying subsidiary/intern/secondee staff as internal per D07_MEAL.md).
  This fixed X2-047 and X2-125 reliably across repeated runs. It did **not** reliably fix X2-066: across
  four attempts (three different prompt wordings plus the role-count redesign itself), the model
  miscounted the same 3-person meal as 4, then 5, then 3 attendees in different runs of *identical* code.
  **X2-066 remains an open false approval** -- this is the 1/52 in the final numbers. Unlike the gift and
  evidence-consistency cases, no code-level gate was built for this because the failure is a pure
  attendee-role misclassification with no independent, code-checkable signal to gate against (the gift fix
  works because "government/authority" is a detectable keyword; there is no equivalent for "did the model
  count the right number of people").
- X2-008 (a note that explicitly states "I have not got the total number of people") also remains
  unresolved after two prompt-reinforcement attempts -- the same class of instruction-following limit
  already established in `docs/exp53_approve_calibration.md`.

## Confirmed live: the model is not deterministic at temperature=0

X2-054, X2-061, and X2-066 each produced *different* decisions across separate runs of byte-identical
code, prompts, and `temperature=0` settings. This is not a bug in this experiment's code -- it is a
property of the underlying API. It means: (a) the headline numbers above are a snapshot, not a guaranteed
reproducible result if rerun again right now; (b) the code-enforced gates matter precisely because they
are the only fixes in this set immune to that variance; (c) any future evaluation of this candidate should
average multiple runs per case rather than trust a single pass, which this experiment did not have budget
or time to do exhaustively.

## Remaining disclosed failures (3/70)

| Case | Ground truth | Issue | Status |
|---|---|---|---|
| X2-008 | REQUEST_INFORMATION | Note explicitly states the total attendee count is unknown; model guesses anyway | Unresolved after 2 prompt attempts |
| X2-066 | REJECT | 3-person meal; model inconsistently miscounts attendees across runs | Unresolved after 4 attempts; only remaining false approval |
| X2-147 | ESCALATE | "Approval exists but its type does not cover this expense" | Not investigated this pass -- out of today's scope |

## What this does and does not establish

This is dev-split evidence only. None of Exp 56-59's code has been run against the validation split or
final_test. Some of today's fixes were tuned by iterating directly against these exact dev cases until
they passed (X2-066 four times, X2-125 twice, X2-054 once) -- legitimate dev-set tuning, but it means part
of the accuracy gain is dev-fitted and not yet evidence of generalization. A natural next check, at low
risk, would be a single run against the validation split (none of this code has touched it before) --
disclosed clearly as a secondary, not-pristine check given other architectures have used that split
previously, not a repeat of final_test's frozen-evaluation discipline. The gold-standard option -- a fresh,
newly generated and frozen holdout, matching Exp 32's original rigor -- remains documented future work, not
attempted here.
