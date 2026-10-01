# Exp 54 — Does a stronger reasoning model fix the APPROVE blind spot? (diagnostic, dev-only)

**Status: diagnostic, not shipped.** `scripts/exp54_stronger_model_approve.py`. Uses the FROZEN,
unmodified `resolver.SYSTEM_LLM_STEP` prompt from `src/resolver.py` — no prompt changes at all,
unlike Exp 53. The only variable changed is the model: `openai/gpt-4o` in place of
`openai/gpt-4o-mini`. This isolates whether the zero-APPROVE behavior (`docs/exp53_approve_calibration.md`)
is a prompt problem or a raw reasoning-capability problem.

## Cases

The 5 hardest of the 17 real dev-residual APPROVE cases — the ones neither Exp 53 variant solved:
3x `HOTEL_CEILING` (X2-011, X2-029, X2-143 — the family responsible for Exp 53's confident-wrong
REJECTs) plus `DYNAMIC_DELEGATION_CHAIN` (X2-047) and `FX_THRESHOLD` (X2-003).

## Result

| Case | Official (gpt-4o-mini, frozen prompt) | gpt-4o (same frozen prompt) |
|---|---|---|
| X2-011 | REJECT (wrong) | REJECT (wrong) |
| X2-029 | REJECT (wrong) | REQUEST_INFORMATION (wrong) |
| X2-143 | REJECT (wrong) | **APPROVE (correct)** |
| X2-047 | REQUEST_INFORMATION (wrong) | REQUEST_INFORMATION (wrong) |
| X2-003 | REQUEST_INFORMATION (wrong) | REQUEST_INFORMATION (wrong) |

1/5 recovered, 0 false approvals, $0.0702 for 5 calls (`gpt-4o` is ~16x gpt-4o-mini's per-token
price). Cumulative project spend: **$4.7797 of the $5.00 cap.**

A genuinely interesting sub-finding on X2-011: gpt-4o's own explanation states *"the nightly rate
of 34,986 JPY exceeds the adjusted ceiling of 35,700 JPY for Tokyo in 2025, which includes a 5%
uplift."* It correctly found and computed the 5% regional uplift that gpt-4o-mini never found at
all in Exp 53 — but 34,986 does not exceed 35,700, and the correct decision given its own numbers
is APPROVE. The model computed the right policy nuance and still stated the wrong conclusion from
it. That is a decision/rationale-consistency failure, not a missing-capability one — a different
bug than "didn't know about the uplift."

## Conclusion

A stronger model helps a little (1/5, zero new risk) without any prompt engineering, which is
consistent with Exp 53's finding that this is substantially a reasoning problem rather than a
pure prompt-caution problem — but it does not solve it, and it is not free: at gpt-4o's price,
running the full 36-case residual set would cost roughly $0.50, and this project's total budget
across all 54 experiments is $5.00. Combining Exp 53's arithmetic-double-check instruction with
Exp 54's stronger model was not attempted — remaining budget (~$0.22) was intentionally left
unspent rather than run a combined test without asking first, since it would leave very little
margin for anything else if it needed a retry.
