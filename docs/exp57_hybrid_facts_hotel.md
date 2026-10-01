# Exp 57 — The same ceiling fix, applied to the single-shot resolver path (live, dev-only)

**Status: negative result, exactly as Exp 55 predicted.** `scripts/exp57_hybrid_facts_hotel.py`. Applies
Exp 56's `compute_hotel_ceiling()` fix to `hybrid_facts.h2_temporal`'s
`applicable_hotel_ceiling_local_currency` fact (used by the single-shot frozen-resolver LLM step,
`resolve_batch` / `resolver.SYSTEM_LLM_STEP`) instead of the guarded agent's tool. Same unmodified prompt,
same live `gpt-4o-mini`, same 18 dev-split HOTEL-family cases as Exp 56, for a direct comparison.

## Result

**BEFORE: accuracy 10/18, APPROVE recall 0/5, false approvals 0/13**
**AFTER: accuracy 10/18, APPROVE recall 0/5, false approvals 0/13**

**Zero cases changed.** Even X2-143 — where the *correct* ceiling (SGD 350, no circular adjustment even
needed) and the *correct* nightly rate (SGD 332.5) were both already sitting in the facts block before
this fix — still came back REJECT, identically, before and after. Real new spend: **$0.0017**. Cumulative
project spend: **$4.8465 of the $5.00 cap** (~$0.154 remaining).

## Why this is not a bug in the fix — it's the Exp 55 finding, confirmed a second time

This is not a failed experiment; it is the same result Exp 55 already found, now reproduced on a fresh
case set: **the single-shot LLM-residual step does not reliably ground its final decision in the
DETERMINISTIC FACTS it is given, even when the fact is exactly correct.** Compare directly with Exp 56:

| | Exp 56 (guarded agent, `check_hotel_compliance` tool) | Exp 57 (single-shot resolver, `hybrid_facts` block) |
|---|---|---|
| Mechanism | Tool computes `policy_disposition` in code; disposition gate overrides the model if it disagrees | Model is shown a fact and told to treat it as authoritative; nothing enforces that it does |
| Ceiling fix alone | **Fixed 3/3 target cases, 0 regressions** | **Fixed 0/3 target cases** |

The difference is not the quality of either fix — both compute the identical, verified-correct ceiling
(Exp 56's `compute_hotel_ceiling`, reused unmodified here). The difference is **structural**: Exp 56's
architecture has a code-level gate that enforces the correct computation regardless of what the model
says; Exp 57's architecture only *hands* the model a fact and hopes it's used. This is the clearest
evidence yet in this investigation for the project's own recurring lesson — moving a decision into code
only pays off when something *enforces* that the code's answer is used, not merely when the code's answer
is correct and available.

## Conclusion for the project story

The APPROVE-recall fix demonstrated in Exp 56 is real, but it is specific to the guarded-agent
architecture's disposition-gate design — it is not portable to the single-shot resolver by copying the
same fact over, and Exp 57 is direct, live proof of that rather than an assumption carried over from
Exp 55's different case set. This closes out the hotel-ceiling line of investigation for both
architectures with a clean, consistent answer: **fix the computation in code, and make sure something
enforces it** — half of that was already true for the frozen resolver's facts; only the guarded agent's
gate supplies the other half.
