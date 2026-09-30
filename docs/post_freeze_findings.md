# Post-freeze findings — bugs found in frozen code, not fixed retroactively

External review found three bugs inside modules the Exp 32 freeze manifest
(`experiments/exp32_freeze_manifest_v2.yaml`) pins by hash: `src/rules_text.py`, `src/llm_exp.py`, and the
`resolver.py` → `llm_exp.run` call chain. Per the manifest's own process rule ("no code... may change after
the final-test predictions are produced and viewed... documented as a finding for a *future* experiment,
not applied retroactively to this run's numbers" — the same rule already exercised once, in the correction
note at the top of `docs/exp44_full_confirmation.md`), none of the three are patched here. This doc is
that documentation.

## 1. Silent field defaults can defeat the deterministic-vs-LLM routing check

`src/rules_text.py`'s note parser defaults three fields when the free-text note doesn't state them, instead
of leaving them `None`:
- `alcohol_amount` / `tip_amount` → `0.0` for MEAL claims (lines ~79-81)
- `cabin` → `"ECONOMY"` for AIRFARE claims (line ~89)

`src/resolver.py:deterministic()` decides whether a claim is safe to resolve without an LLM by checking
`f.get(k) is None` for each field the claim's expense type needs (the `NEEDED` dict — `cabin` is required
for AIRFARE). Because the parser never actually leaves these fields `None`, that check can't tell "the note
said economy" apart from "the note said nothing and the parser assumed economy" — a claim can be routed
down the deterministic (no-LLM) path and decided as if a fact were confirmed when it was only guessed.

**Why not fixed now:** both files are frozen (hashes in the manifest). A fix changes what routes to the
LLM vs. the deterministic path, which would change Exp 32's already-reported numbers if applied
retroactively — exactly what the manifest's process rule forbids.

**Fix for a future experiment:** have the parser return `None` (or a separate `stated: bool` flag per
field) when a value is inferred rather than found in text, and have `deterministic()`'s conclusiveness
check honor that distinction. Re-run the affected experiments fresh under a new manifest, not by editing
history.

## 2. `unsupported_policy_assertion_rate` doesn't measure what its name says

`src/llm_exp.py:60` (frozen, hash `d6739c69ac6d0327` in the manifest):
```python
unsupported_policy_assertion_rate=round(sum(r["cited_any_policy"] for r in recs) / n, 4)
```
This is the fraction of responses that cited *any* policy clause at all — not the fraction that cited one
*without support* (a hallucinated or unjustified citation). Every `summary.json` written by any experiment
that used the shared `llm_exp.run` runner carries this field under a name that overstates what it checked.
(Separately, `LLM09` in `docs/owasp_llm_top10_2025.md` does the real "is this citation genuinely
fabricated" check correctly, by extracting the ID token and comparing against the valid-clause set — that
check is sound; only this field's *name*, inside the frozen runner, is wrong.)

**Why not fixed now:** `src/llm_exp.py` is frozen; it's also the module `src/resolver.py` calls for the
LLM-residual step of the already-run Exp 32.

**Fix for a future experiment:** rename the field (e.g. `cited_any_policy_rate`) and, if an "unsupported
citation" rate is wanted, compute it the way `LLM09`'s audit already does (ID-token extraction against the
corpus's valid clause-id set), inside a new, non-frozen module version.

## 3. "Predictions written before any evaluation" is true only at the outer-script level

`scripts/exp32_final_test.py` writes `predictions.jsonl` (line ~33) before calling
`evaluate.load_gt()`/`evaluate.evaluate()` (line ~35-36) — that ordering is real. But the one call it makes
into the pipeline, `resolver.resolve_batch()` (`src/resolver.py:57-85`), internally calls
`llm_exp.run` for the LLM-residual claims, and `llm_exp.run` itself calls `evaluate.load_gt()` and
`evaluate.evaluate(recs, gt)` (`src/llm_exp.py:56-57`) *before* returning — i.e. before Exp 32's own
`predictions.jsonl` is written. Ground truth is loaded and joined against the residual-path predictions one
level down, earlier than the outer script's own "locked before evaluation" framing implies. This does not
mean labels reach the model prompt (no evidence of that; `tests/test_no_leakage.py` would also catch an
import of the evaluator from a genuinely runtime-only module, and `llm_exp` is the one documented,
intentional exception since it scores immediately after generating, not before) — it means the *process*
claim ("no case is inspected... before the batch is complete and saved") is looser than stated once you
follow the actual call chain, not that the final-test result itself is compromised.

**Why not fixed now:** changing this ordering means changing `src/llm_exp.py` and/or `src/resolver.py`,
both frozen for Exp 32.

**Fix for a future experiment:** have `resolve_batch`/`llm_exp.run` return raw predictions without scoring,
and move all evaluation to the outer script, so "predictions locked, then evaluated" is true at every level
of the call chain, not just the outermost one.
