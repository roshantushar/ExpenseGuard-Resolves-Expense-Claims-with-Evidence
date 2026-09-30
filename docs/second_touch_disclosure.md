# Disclosure — the held-out data was touched more than once after the freeze

An independent audit of this repository found **two separate, undisclosed touches** of the held-out
final-test split (and one of validation) after the Sep 27 freeze. Both are documented here in full rather
than left as unexplained files on disk. Neither changed Exp 32's own official saved result.

## Touch 1 — the frozen resolver's LLM-residual step, re-run against final_test and validation

- `results/current/final_test/resolver/summary_openai_gpt-4o-mini.json` — n=30, 27/30 calls served from cache
  (3 genuinely new calls), dated after the freeze.
- `results/current/validation/resolver/summary_openai_gpt-4o-mini.json` — n=15, 1/15 cached (14 new calls).
- Proof this is a distinct run, not a duplicate view of Exp 32's own data: case `X2-021` is recorded as
  `path: "deterministic"` (no LLM call) in Exp 32's official predictions, but appears in this file as a
  fresh LLM call with different cited clauses.
- The dataset was regenerated after Exp 32 ran (already disclosed in `docs/exp32_final_test.md`), and
  this run's content is consistent with having executed against the regenerated files. **Origin could not
  be established from committed scripts/logging.**

## Touch 2 — the guarded-agent candidate itself, run against 60% of final_test

This is the more consequential of the two. `src/resolver.py`'s `resolve_batch_v2` (the guarded-agent
candidate pipeline, tagged `RESOLVER_V2` in the shared call log) was run against final-test claims:

- `results/run_log.jsonl` shows 3,308 real LLM calls under `experiment: "RESOLVER_V2"` (Sep 29,
  03:29–17:31) and a further batch of 103 calls under `RESOLVER_V2_REGEN`, all at 18:07:10 — one minute
  before `ui/frontend/public/data/cases.json`'s file timestamp (18:08).
- That export file carries a genuine (non-empty, real tool-call trace) guarded-agent prediction for
  **30 of the 50 final-test cases** — e.g. `X2-001`: a real 2-turn run calling `check_workflow_compliance`
  and returning its actual data, not a placeholder.
- **Measured result on those 30 cases: 15/30 correct (50%), and 3 false approvals out of 17 non-approvable
  cases (17.6% observed FAR).** This is materially worse than the 0% observed FAR reported for the
  candidate on every other split in every other document in this project.
- This was not disclosed anywhere. `docs/exp45_resolver_v2_full_dev.md`, `docs/gate_override_audit.md`,
  and `docs/exp47_52_full_coverage.md` all reference `resolve_batch_v2`/`RESOLVER_V2`, but each one scopes
  its stated analysis to development and validation only. `gate_override_audit.md` explicitly notes the
  export spans "81 exported non-deterministic cases across all three splits" while analyzing only 100 of
  them (development + validation) — the final-test portion of that same export was never discussed.
- The UI previously displayed this as a "Guarded agent · final test (demo only)" stat card. That card has
  been **removed from the live demo** as of this disclosure — showing a partial, uncontextualized 30/50
  result without this explanation next to it was actively misleading, not merely incomplete. The underlying
  data file (`cases.json`) has not been altered and remains available for inspection.

## What this means for every "never run against final test" / "0% FAR on every split" claim

Those statements, repeated in `README.md`, `docs/README.md`, `docs/FINAL_REPORT.md`, `problem.md`,
and `CHANGELOG_FINAL.md`, are **not accurate**. A substantial, real run against 60% of the held-out set
already exists, and its result is worse than every headlined number for this candidate. This does not
retroactively make that run an authorized, frozen, one-shot evaluation — it has no freeze manifest, covers
only 30 of 50 cases, and its origin could not be established from committed scripts/logging — so it
should not be cited as "the candidate's official final-test result" either. It should be read as exactly
what it is: unauthorized, partial, real evidence that the candidate's true held-out performance may be
worse than its development/validation numbers suggest, discovered after the fact rather than designed as
a test.

## What is not known
**Origin could not be established from committed scripts/logging.** No committed script or notebook calls
`resolve_batch_v2` (or `resolver.resolve_batch`) against the full final-test case set; the run_log entries
establish that it happened and roughly when, not who ran it, why, or whether its output influenced any
documented conclusion before this disclosure. No doc cites these specific numbers, which is some evidence
nothing was knowingly built on them — but the absence of a citation is not proof no one looked. This is
stated as a fact, not speculated about further.

## Status
Documented, not corrected retroactively, consistent with this project's standing practice for issues found
after the fact. **Any claim that the guarded-agent candidate has "never been tested against final test" or
maintains "0% FAR on every split measured" must be qualified with a link to this disclosure.** The official,
frozen, one-shot result for this project remains Exp 32's 30/50 (60%), 0/37 observed false approvals for the
**frozen resolver** — this disclosure concerns the candidate architecture only, and does not change Exp 32's
own result.
