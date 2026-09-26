# Experiment 32 — Freeze decisions and runbook (the final test has NOT been run)

**Files:** `experiments/exp32_freeze_manifest.yaml`, `scripts/exp32_final_test.py`, `scripts/make_freeze_manifest.py`, `src/flags.py`, `tests/test_workflow_flags.py`

## Decisions made before the run
1. **Hotel over the ceiling, approved trip, neither an exception nor a conference on record → ESCALATE** (was REJECT). Basis: GEP26-4.1 (missing evidence must result in a request for information or escalation, not a guess) and the general principle that a violation an exception could still cure should not be auto-rejected. **Disclosure:** the change was prompted by three development/validation labels (EXP-0111, 0114, 0120), so those splits are no longer independent for this branch. An expired or invalid exception still REJECTs; a non-registered conference still REJECTs.
2. **Currency-threshold cases: no logic change.** Thresholds stay SGD-equivalent (APR-1.1, CIRC-26-02) using the frozen FX table. Affected claims are flagged from inputs only (`src/flags.py`): a non-SGD software claim whose raw amount exceeds SGD 1,000 while its SGD equivalent does not, or a non-SGD split candidate whose combined raw amount exceeds 500 while its combined SGD equivalent does not. Results are reported for all cases, for the flagged subset, and excluding it.
3. **No invented rules.** The project-status hotel rule was removed in Exp 18 v2.

## Post-change development and validation results (no longer independent; for reference)
| | Development | Validation | Combined |
|---|---|---|---|
| Fixed workflow / router | 58/60 (Wilson 88.6–99.1%) | 18/20 (69.9–97.2%) | 76/80 (95.0%) |
| Remaining misses | EXP-0098, EXP-0104 | EXP-0082, EXP-0085 | all four are currency-flagged |
Unit tests: 16 pass (`python -m unittest discover -s tests`).

## Dry run
`python scripts/exp32_final_test.py VALIDATION` runs the whole pipeline on validation as a dry run (`results/validation/exp32_dryrun/`, `results/plots/exp32_dryrun_validation.png`): router 18/20, rules 16/20, gpt-4o-mini RAG + facts 10/20, llama 9/20, all four currency-flagged cases correctly picked out. Cost $0 (cached).

## Guards in the runner
On `FINAL_TEST` it (1) refuses without `--confirm-final-run`, (2) refuses if any of the 18 frozen source files differs from its SHA-256 in the manifest, (3) refuses if `results/final/RAN` exists. It writes that marker before predicting. Verified: running it on `FINAL_TEST` without the flag exits immediately, before any final case is read.

## What the final run does and reports
Runs the router (primary), rules only, gpt-4o-mini RAG + code facts and llama3.2:3b RAG + code facts once, on the 40 final-test cases. Reports Correct Disposition Rate with the raw count and 95% Wilson interval, false approvals among non-approvable cases, Human Review Rate, median and P95 latency, cost per case, the 10 challenge cases separately, and the currency-flagged subset separately (with the result excluding it). Projected paid spend is under $0.02. Exp 33 (failure categories) is a separate analysis of the primary system's errors.

## Steps
1. Review the manifest and commit the code, tests, docs and `experiments/exp32_freeze_manifest.yaml`.
2. Any further edit to a frozen file requires regenerating the manifest (`python scripts/make_freeze_manifest.py`) and committing it again before the run.
3. Give the go-ahead; the run is then `python scripts/exp32_final_test.py FINAL_TEST --confirm-final-run`.
