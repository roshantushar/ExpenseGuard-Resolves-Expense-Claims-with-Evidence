> **Dataset snapshot note:** the numbers below are exactly as produced by the one-shot run, unedited and
> not rerun, per the manifest's own rule. Afterward, in this same session, the dataset was regenerated
> once more (the Chennai/Kobe RAG-necessity lever, `dataset_generator/world.py`/`cases_c.py`) to make a handful
> of `DYNAMIC_HOTEL_DISCOVERY` cases genuinely retrieval-necessary. That regeneration touches the
> on-disk `ExpenseGuard_DATASET` package, so `experiments/exp32_freeze_manifest_v2.yaml`'s hashes no
> longer match the current dataset files. This result remains the valid, honest record of what that
> frozen system did on the final-test snapshot that existed at the time; it is not reproducible byte-
> for-byte against the dataset as it exists on disk today, and no claim about the *current* dataset
> should cite this manifest as still verifying it. Any new final-test claim needs a fresh freeze cycle.

# Exp 32 — Frozen final test (one-shot, semantic edition)

Freeze manifest: `experiments/exp32_freeze_manifest_v2.yaml` (hashes of code, policy corpus, enterprise
data, ground truth, and the runner script itself; committed before the run). Runner:
`scripts/exp32_final_test.py`. Frozen pipeline: `src/resolver.py` (Exp 30's selective architecture).
Results: `results/current/final_test/exp32_final_test/` (`predictions.jsonl`, `evaluation.jsonl`,
`summary.json`, all locked before evaluation). Cost: $0.0232. Wall clock: 54.7s. Run once, per the
manifest's process rule: no case inspected or rerun mid-run, no post-hoc change to resolver/prompt/
tool logic.

**Question:** how does the frozen selective architecture perform on the 50 held-out final-test claims,
touched for the first and only time here?

## Result

| Metric | Value |
|---|---|
| Correct/N | 30/50 (60.0%), Wilson 95% CI [46.2%, 72.4%] |
| False approvals | 0/37 (0.0% FAR) |
| Human Review Rate | 22.0% |
| Cost | $0.0232 total ($0.00046/claim) |
| % routed to LLM | 28/50 (56%) |

| Class | Support | Recall |
|---|---|---|
| APPROVE | 13 | **0.00** |
| REJECT | 13 | 0.92 |
| REQUEST_INFORMATION | 12 | 0.75 |
| ESCALATE | 12 | 0.75 |

| Path | Correct/N | Accuracy |
|---|---|---|
| Deterministic | 22/22 | **100%** |
| LLM-residual | 8/28 | 28.6% |

Challenge subset (15 independently-worded cases): 10/15 correct (67%).

### Confusion matrix and class-level metrics (item 28)

Computed directly from `predictions.jsonl` against `ground_truth.jsonl` (rows = ground truth, columns =
predicted):

| Truth \ Predicted | APPROVE | REJECT | REQUEST_INFORMATION | ESCALATE |
|---|---|---|---|---|
| **APPROVE** (13) | **0** | 8 | 4 | 1 |
| **REJECT** (13) | 0 | **12** | 1 | 0 |
| **REQUEST_INFORMATION** (12) | 0 | 2 | **9** | 1 |
| **ESCALATE** (12) | 0 | 3 | 0 | **9** |

| Class | Precision | Recall | F1 |
|---|---|---|---|
| APPROVE | 0.000 | **0.000** | 0.000 |
| REJECT | 0.480 | 0.923 | 0.632 |
| REQUEST_INFORMATION | 0.643 | 0.750 | 0.692 |
| ESCALATE | 0.818 | 0.750 | 0.783 |
| **Macro-F1** | — | — | **0.527** |

APPROVE recall is visibly 0.00 — the system never once correctly predicted APPROVE on the final test, and
the confusion matrix shows exactly why: every one of the 13 truly-approvable claims was instead predicted
REJECT (8), REQUEST_INFORMATION (4), or ESCALATE (1). APPROVE's 0% precision-and-recall combination means
its F1 is undefined-in-practice (0.000 here since no true positives exist) — the system is safe (it never
falsely approves) but functionally unable to affirmatively confirm a clean claim, consistent with the
"reading the result" discussion below.

## Reading the result
The deterministic half of the architecture generalized perfectly to unseen data (100%, vs. 88.2% on
dev — no leakage, no overfitting signal). Zero false approvals held, matching the design goal. The
standout, unflattering finding: the LLM-residual path never once correctly predicted APPROVE (0/13),
and its accuracy dropped further than on dev (28.6% vs. 36.1%, Exp 30) — the system is safe but too
conservative when it isn't certain. Full root-cause breakdown of all 20 errors: Exp 33.

## Decision
`src/resolver.py` remains frozen exactly as it stood at manifest time. This is the final, reported
number for the selective architecture; no rerun, no tuning, no retroactive fix, per the manifest's
process rule.
