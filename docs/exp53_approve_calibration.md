# Exp 53 — Can the residual LLM step ever be made to APPROVE? (diagnostic, dev-only)

**Status: diagnostic, not shipped.** Does not touch or modify the frozen `src/resolver.py` /
`src/llm_exp.py` (hash-pinned in `experiments/exp32_freeze_manifest_v2.yaml`). Runs a standalone
script, `scripts/exp53_approve_calibration.py`, against the same 36 development-split residual
cases the frozen pipeline already routes to the LLM, reusing its unmodified retrieval/facts code.
Development split only — validation and final_test were not touched.

## The finding that motivated this

Across every official result ever produced by this project's shipped architecture — development
(70 cases), validation (30 cases), and the frozen final test (50 cases) — **the system has
predicted APPROVE exactly zero times**, on any split, ever. 39 of the 150 cases in the dataset are
genuinely APPROVE in ground truth (18 dev / 8 validation / 13 final test); none were ever caught.
This was not previously documented as its own finding — it fell out of the deterministic-path vs.
residual-path breakdown discussed in `docs/second_touch_disclosure.md` and `README.md`'s error
analysis, but the "zero APPROVE, full stop" framing hadn't been stated explicitly before.

Root cause, confirmed structurally: `src/rules_v2.py`'s deterministic rules never themselves
output APPROVE — by design they only fire conclusively on a violation, a missing required fact,
or an escalation trigger. Every claim that is actually clean falls through to the LLM-residual
step. Of the 36 development-split residual cases, 17 (nearly half) are genuinely APPROVE. The
official residual-step prompt (`resolver.SYSTEM_LLM_STEP`) caught 0 of them, while still
achieving 0% false approvals on the ones it got wrong (it never approved anything, so it structurally
cannot false-approve).

## What was tried

Two standalone prompt variants, same retrieval/facts/model (`gpt-4o-mini`, same K=8 dense
retrieval, same H1-H4 hybrid facts) as the frozen step — only the system prompt text differs.

| Variant | Change from the frozen prompt | n | Correct | False approvals | APPROVE predicted | Correct APPROVE (of 17 true) |
|---|---|---|---|---|---|---|
| Official (frozen, for reference) | — | 36 | 13/36 (36.1%) | 0 | 0 | 0/17 |
| V3 | Drops the "reached you because rules couldn't resolve it" framing; states APPROVE is expected/normal when facts support it | 36 | 11/36 (30.6%) | 0 | 1 | 1/17 |
| V3b | V3, plus an explicit instruction to double-check the exact numeric comparison before concluding REJECT, and to treat any mentioned exception/tolerance/approval path as not-a-clear-violation | 36 | 13/36 (36.1%) | **1 (5.3% FAR)** | 5 | 4/17 |

Real API calls throughout (`gpt-4o-mini`), $0.0603 total for both variants combined. Cumulative
project spend: **$4.7094 of the $5.00 cap** (`MAX_BUDGET_USD`).

## What this shows

- **It is not primarily a prompt-caution problem.** Simply telling the model "APPROVE is normal,
  don't over-hedge" (V3) barely moved APPROVE recall (0→1) and made overall accuracy *worse*
  (13→11): removing the hedging language made the model more willing to confidently assert a
  violation it hadn't actually verified — e.g. case X2-011, a hotel bill 986 JPY over the Tokyo
  ceiling, rejected without checking for a stated tolerance or FX nuance in the retrieved excerpts.
- **Adding an explicit "verify the arithmetic, don't guess REJECT" instruction (V3b) genuinely
  helped** — it recovered 4 of the 17 real APPROVE cases (equipment, software, gift, and training
  claims, all simple single-threshold checks) while holding overall accuracy at the official
  baseline (13/36 either way).
- **But V3b broke the one invariant this whole project is built around: it produced 1 false
  approval (5.3% FAR).** Case X2-061 (`EVIDENCE_CONFLICT` archetype): the bill is from a
  ride-hailing vendor ("RideNow India"), but the employee's note (in Hindi/Hinglish) describes a
  two-night hotel stay — the bill and the description describe two different expenses. V3b's
  arithmetic-check instruction correctly confirmed the amount was under the ceiling and stopped
  there, missing the vendor/description mismatch entirely — a semantic evidence conflict, not a
  numeric one. The instruction that fixed the numeric failures did nothing for this different
  failure mode.

## Conclusion

APPROVE recall and 0% FAR are in real, measured tension for this residual step, not just an
assumed one — this experiment is the first time that tradeoff has been quantified with actual
runs rather than argued from principle. A prompt fix that recovers real APPROVE cases without
reintroducing false approvals would need to separately verify (a) the numeric/threshold claim and
(b) that the bill and the note describe the same transaction, as two independent checks — plausibly
by adding an explicit `evidence_matches_description` fact to `src/hybrid_facts.py` (H1-H4 already
does exactly this kind of work for arithmetic and duplicates) rather than asking the LLM to catch
both at once in one pass. That is a real, scoped next step, not a vague "needs more work" — but it
is new code against a frozen module's dependency, so it was not attempted here; this experiment's
job was to diagnose the problem honestly, not to ship a fix under time pressure days before
submission.

**This result directly supports, rather than undermines, the project's existing headline
decision:** the frozen design's conservatism (0% FAR, but 0/39 real approvals ever caught) was a
deliberate, measured tradeoff (`docs/README.md`, Act 3 of the experiment story) — this experiment
is the first direct evidence of *why* that tradeoff is real: the cheapest available fix for the
APPROVE blind spot measurably reintroduces the exact risk the frozen design was chosen to avoid.
