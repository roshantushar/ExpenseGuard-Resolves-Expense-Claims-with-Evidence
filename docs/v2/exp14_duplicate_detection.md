# V2 Exp 14 — Duplicate expense detection (component qualification, $0)

Notebook: `notebooks/v2/exp14_duplicate_detection.ipynb`. Results: `results/v2/development/exp14_duplicate_detection/`. Cost: $0.0002 (3 fixture calls). Development split only.

**Question:** can the system separate EXACT_DUPLICATE, POSSIBLE_DUPLICATE, LEGITIMATE_REPEAT and SPLIT_TRANSACTION, without falsely blocking a legitimate repeat?

| Component | Dev result |
|---|---|
| 14A candidate retrieval | 7/7 gold-positive cases retrieved; 7/70 total dev claims produce any candidate |
| 14B exact/fuzzy deterministic adjudication | Perfect: 2/2 exact, 4/4 split, precision/recall 1.0 both; **false-block rate 0/64 (0.0%)** |
| 14C LLM-assisted adjudication | **Not evaluable on development: 0 gold POSSIBLE_DUPLICATE cases exist in dev.** Implementation smoke-tested on 3 synthetic, non-scored fixtures: valid labels, structured output, no fraud wording, no crashes. |

**Dataset-size finding, stated plainly:** development is sufficient to fully qualify 14A/14B (on small counts: n=2, n=4, n=1) but has nothing to measure 14C against. The whole dataset has only 3 POSSIBLE_DUPLICATE cases total (1 validation, 2 final test); any future 14C score must be reported as a raw count, never a percentage.

**Informal, non-scored note:** one fixture meant to be an obvious LEGITIMATE_REPEAT was labelled POSSIBLE_DUPLICATE by the model — not counted in any metric, but worth watching later.

**Decision:** 14A/14B carried forward as-is (already in use since Exp 2). 14C's real evaluation is deferred to a split that actually contains the class. Next: Exp 15 (split-transaction detection).
