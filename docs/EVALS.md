# Evaluation methodology — one-page index

What gets measured, how, on which data, and which results are not allowed to be rerun. Companion to
[`docs/dataset_card.md`](dataset_card.md) (the data explainer) — this is the evals explainer.

## Metrics

| Metric | Definition | Why it exists |
|---|---|---|
| **Correct Disposition Rate (accuracy)** | correct final decision / total evaluated claims | Headline metric, but never used alone (see below) |
| **False Approval Rate (FAR)** | incorrect APPROVE / non-approvable cases | The safety metric. Held to 0% observed as a hard constraint, not traded off against accuracy |
| **False-rejection rate** | a genuinely approvable claim wrongly rejected / all truly approvable claims | The hidden cost a 0%-FAR headline can mask — see `docs/cost_and_business_impact.md` |
| **Safe Automation Rate** | claims both auto-resolved (no human) AND correct / all claims | "How much of this can run unattended" — includes a correct `REQUEST_INFORMATION` as safe |
| **Human Review Rate** | claims escalated or otherwise requiring a person / all claims | Links the system to real operational effort |
| **Cost / 1,000 claims** | risk-adjusted: AI cost + human-review cost + error cost, three layers priced separately | Why "best accuracy" and "best operating architecture" are not always the same thing |
| **Latency** | median and P95, LLM-residual path only | Deterministic path is ~0s by construction |

Full metric definitions and formulas: `problem.md` §29–31.

## Splits

| Split | n | Role | Touched more than once? |
|---|---|---|---|
| Development | 70 | Iterate, debug, tune | Yes — freely, by design |
| Validation | 30 | Check generalization before freezing a design | Used during the guarded-candidate's development; not independent for that design |
| Final test | 50 | One-shot, frozen-architecture evaluation (Exp 32) | **No — see "Do not rerun" below.** Also disclosed as touched a second time by an unexplained process after the freeze: `docs/second_touch_disclosure.md` |
| Exp 60 holdout | 50 | Fresh, independently-labeled holdout for the guarded candidate | Reported once; a real ground-truth bug was found and corrected transparently (`docs/exp60_fresh_holdout.md`) |
| Exp 61 holdout | 30 | Pre-registered *before generation* — built to break the candidate's fix, not confirm it | Reported once, as pre-registered (`docs/exp61_v3_holdout.md`) |

## Evaluator

`src/evaluate.py` and `src/metrics.py` join private ground truth (`ExpenseGuard_DATASET/04_ground_truth_PRIVATE/`)
against saved predictions **after** a run completes — never imported by runtime code
(`tests/test_no_leakage.py` statically enforces this). Wilson 95% confidence intervals are used for
small-sample rates rather than a bare percentage.

## Freeze manifests — pre-registration before a result exists

| Manifest | Covers | Committed before |
|---|---|---|
| `experiments/exp32_freeze_manifest_v2.yaml` | The official frozen resolver | The Exp 32 final-test run |
| `experiments/v3_freeze_manifest.yaml` | The Exp 61 stress-test holdout | A single Exp 61 case was generated |

A manifest names the exact frozen code (file hashes), the model, and the process rule that no code/data
may change after predictions are produced and viewed — a finding becomes a disclosed note for a future
experiment, never a silent re-run.

## Do not rerun

- **`python -m scripts.exp32_final_test`** — the official final test. Already run once, ever. Rerunning it
  would make "one-shot, held-out" an untrue claim about this project's single most important result. See
  `docs/second_touch_disclosure.md` for what happened the one time this boundary was already crossed.
- **Exp 60 and Exp 61's holdout generation scripts** — already run and reported; rerunning to get a better
  number would turn a pre-registered stress test into a tuned one.

## What's safe to rerun anytime, at $0

```bash
python -m unittest discover -s tests      # leakage, tool, workflow checks
python -m dataset_generator.validate      # dataset integrity audit
```

Both are deterministic, offline, and reproduce the same pass/fail every time.
