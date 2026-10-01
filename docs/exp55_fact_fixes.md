# Exp 55 — Five targeted fact fixes, tested one at a time, live (diagnostic, dev-only)

**Status: diagnostic, not shipped. All five kept 0 false approvals; none recovered a single APPROVE.**
`scripts/exp55_fact_fixes.py`. Frozen `resolver.SYSTEM_LLM_STEP` prompt, unchanged throughout — only the
`DETERMINISTIC FACTS` block handed to it was corrected, one behavior at a time, per the requested
methodology. Live `gpt-4o-mini` calls, development split only; cases whose facts didn't change for a given
variant hit the existing cache at $0. Real new spend across all five variants: **$0.0088**. Cumulative
project spend: **$4.7888 of the $5.00 cap.**

## Root causes confirmed and patched (standalone, `src/` frozen files untouched)

1. **Hotel/meal ceiling circulars never reached the LLM's facts.** `rules_v2.hotel()`/`meal()` — the
   functions that actually detect violations — already apply the real circular adjustments (CIRC-25-06
   Tokyo +5%, CIRC-26-04 India-T1 +6%, CIRC-25-11 India meal ceiling → 2100). `hybrid_facts.h2_temporal()`'s
   `applicable_hotel_ceiling_local_currency` / `applicable_meal_ceiling_per_person` facts use the static
   base table only — the enforcement logic and the fact shown to the LLM had silently drifted apart.
2. **Attendee-counting regex has no pattern for "myself, N colleagues, and M external guests"** (X2-047's
   exact phrasing) — falls through to `unknown_from_claim_text`.
3. **Business-owner regex has no pattern for "managed by NAME"** (X2-078) — same failure mode.
4. **Distance/odometer parsing requires an explicit "km" unit and cannot compute a distance from two
   odometer readings at all** (X2-088) — and a separate, deeper gap: `rules_text.py`'s number-word parser
   (`num()`) has no "thousand" support, so it could not have parsed "twenty-three thousand three hundred
   ten" even if the odometer pattern existed. Built a supplementary word-number parser for this fix only.

## Results — all five variants, same 4 metrics each

| Variant | (a) 5 diagnostic cases → APPROVE | (b) APPROVE recall /18 | (c) false approvals /52 | (d) accuracy /70 |
|---|---|---|---|---|
| Baseline (official, re-verified live) | 0/5 | 0/18 | 0 | 43/70 |
| hotel_circular | 0/5 | 0/18 | 0 | 43/70 |
| meal_circular | 0/5 | 0/18 | 0 | 43/70 |
| attendee_count | 0/5 | 0/18 | 0 | 43/70 |
| business_owner | 0/5 | 0/18 | 0 | 43/70 |
| mileage_odometer | 0/5 | 0/18 | 0 | 43/70 |

**Every single variant held 0% FAR — and none moved a single case to APPROVE.** Per the requested rule
("keep a change only if the wider development results support it"), none of these five fixes is kept.

## Why they didn't work — this is the actual finding

In every one of the five cases, after the fix, the *correct number was sitting directly in the
DETERMINISTIC FACTS block* the model was given — and the model still got the decision wrong, in one of
two specific ways:

- **It ignored the corrected fact and cited a different, wrong number from elsewhere** (X2-011: given
  ceiling 35,700, cited "30,000" — a different grade band read off the raw retrieved policy table;
  X2-125: given ceiling 2,100, cited "2,000" — the un-amended base value; X2-047: given per-person SGD
  100 across 18 correctly-counted attendees, classified the claim as an *employee* meal and applied the
  ~SGD 50 employee ceiling instead of the SGD 120 client ceiling it should have used for a claim with 9
  external guests).
- **It recomputed the exact right number itself and then stated a self-contradictory conclusion from
  it** (X2-088: its own explanation states *"the claim amount of 28.8 SGD exceeds the calculated
  reimbursement... which totals 28.8 SGD"* — 28.8 does not exceed 28.8, REJECT anyway. This is the same
  exact failure pattern `docs/exp54_stronger_model_approve.md` found independently with `gpt-4o` on
  X2-011: right arithmetic, wrong stated conclusion from its own numbers).

This is a stronger and more specific result than Exp 53/54's "reasoning failure" framing: **the residual
LLM step does not reliably ground its final decision in the DETERMINISTIC FACTS it is given, even when
those facts are complete, correct, and the prompt explicitly instructs it to treat them as authoritative
and not recompute or contradict them.** Fixing the fact-computation bugs (real, now documented and
patched here) is necessary but demonstrably not sufficient.

## What this implies for next steps

The safest path to recovering real APPROVE cases is not a better fact or a better prompt for the LLM
step — it's **making the comparison in code**, the same move this project's entire history has made
for every other category of error (`docs/README.md`'s Act 2/5: arithmetic, duplicates, dispositions all
moved out of the model's hands once code could do them instead). `rules_v2.decide()` already reaches a
correct, circular-aware "no rule triggered → APPROVE" conclusion for the hotel/meal cases in this
experiment (`docs/exp53_approve_calibration.md`'s finding) — `resolver.deterministic()` just discards it
as "not conclusive." A safe fix would combine: (a) trusting that fallback specifically for expense types
where every applicable per-category check has actually run to completion with no unresolved field, and
(b) closing the 8 real rule gaps found earlier (`docs/post_freeze_findings.md`'s alcohol-default bug,
consumer-service category-matching, exception-ID validation) that currently make blind trust of the
fallback unsafe. That is real, scoped engineering work against a frozen module's dependents — not
attempted here, and not something to rush before submission.
