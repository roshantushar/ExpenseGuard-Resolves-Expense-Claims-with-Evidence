# Exp 58 — "Fix this for everything": full 70-case dev run, guarded agent (live)

**Status: real improvement confirmed, plus one important reproducibility caveat that must be disclosed
alongside it.** `scripts/exp58_full_agent_fix.py` + `scripts/exp58_full_dev_run.py`. Extends Exp 56's
pattern (compute the disposition in code, let the existing disposition gate enforce it) to every gap
Exp 53 found: hotel ceiling (Exp 56, reused unmodified), plus two brand-new tools —
`check_mileage_compliance` (odometer/distance arithmetic moved into code, same `rules_v2.mileage()` math)
and `check_software_compliance` (the SWE-1.1 named-business-owner check, currently absent from the agent's
tool set entirely). `check_meal_compliance` and `check_gift_compliance` were inspected and already apply
their circulars correctly — no fix needed there. `src/agent.py` and `src/agent_variants.py` are untouched;
everything is additive, in new files. Budget cap raised from $5.00 to $6.00 with explicit authorization.

## Result — all 70 development-split cases, live, same day, same code, both variants

**BEFORE (original, unmodified Exp 47 tool set): accuracy 55/70, APPROVE recall 11/18, false approvals 2/52**
**AFTER (Exp 58 tools): accuracy 59/70, APPROVE recall 15/18, false approvals 2/52**

Four cases changed, all correctly, all the intended targets: **X2-011, X2-029, X2-139 (hotel ceiling)**
and **X2-088 (mileage)** all flipped from wrong to correct APPROVE. **Zero new false approvals** — the
2/52 FAR is identical in both columns (see caveat below: it is not new, and not something this fix
touches). X2-047 (meal) and X2-125 (meal) were already correct in both variants, confirming
`check_meal_compliance`'s existing circular logic needed no fix. X2-078 (software) did not reach the new
`check_software_compliance` tool in either variant — `check_workflow_compliance` flagged a possible
duplicate of a prior month's bill from the same vendor first, in both the before and after run; for a
monthly-billed software subscription that recurs every month this is very plausibly a false-positive
duplicate check, not a software-owner problem, but it is a different, pre-existing gap, not something this
experiment's tools address.

## Important caveat: this "before" does not match the previously documented official baseline

The guarded agent's documented dev result (Exp 51/52, `docs/README.md`, quoted throughout this
investigation) is **44/70 accuracy, 6/18 APPROVE recall, 0/52 false approvals**. This experiment's own
fresh re-run of the *identical, unmodified* Exp 47 configuration today produced **55/70, 11/18, 2/52** —
a different result, on the same code, with `temperature=0`. Two false approvals appear in *both* the
before and after columns here that are not present in the originally saved official result at all:

- **X2-061** (ground truth REQUEST_INFORMATION): the bill is from "RideNow India" (a ride-hailing vendor);
  the note (in Hindi) describes a two-night **hotel** stay near a conference venue. Bill and note describe
  two different transactions — the same bill/note evidence-conflict pattern independently found on X2-104
  in Exp 56. The agent approved it in both runs.
- **X2-066** (ground truth REJECT): an employee meal in Tokyo involving a subsidiary employee and a
  payroll intern as two of the three attendees — a probable eligibility nuance this investigation did not
  characterize further.

Neither case involves hotel, mileage, or software — they are unrelated to anything Exp 56-58 touched, and
they are identical in both columns of this run, so they are not a regression introduced by this
experiment. But their presence means **the previously documented 44/70 / 0 FAR guarded-agent baseline did
not reproduce when re-run live today under nominally identical conditions.** The most likely explanation
is that `openai/gpt-4o-mini` is a model alias, not a pinned snapshot — OpenRouter/OpenAI can and do update
what it points to over time, and the original Exp 51/52 runs and this one are weeks apart. This is a real,
disclosable reproducibility risk for any LLM-based evaluation that is not itself new to this project (the
freeze manifest's hash-pinning already protects the code side of this; it cannot protect against the
model provider changing what a model name resolves to). It was not investigated further here — doing so
would require re-running Exp 51/52's exact original configuration again today and comparing, which was
judged out of scope for this fix-focused pass.

## Conclusion

Within a single, controlled, same-day comparison, the Exp 58 fixes are a clean, real win: +4 accuracy,
+4 APPROVE recall, zero new false approvals, on live data, against the unmodified tool set run under the
exact same conditions on the same day. That comparison is valid on its own terms. What it is **not** is a
clean "44/70 → 59/70" headline — the reference point itself moved for reasons outside this experiment's
control, and that has to be reported alongside the improvement, not instead of it.
