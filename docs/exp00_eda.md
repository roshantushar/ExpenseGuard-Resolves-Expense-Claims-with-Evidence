# Exp 0 — Dataset validation + EDA (semantic edition)

> Re-run after the semantic rebuild: visible forms are empty, facts live in LLM-drafted notes (mean ~50 words, 7 styles (incl. dictated, some local-language), computed facts, distractors, self-corrections, coarse bill categories; all 150 pass validation, 4 accepted by manual review or fallback). Validator 50/50. Corpus now 229 clauses, ~39.5k words, 71-page PDF.

Notebook: `notebooks/exp00_dataset_validation_eda.ipynb`. Outputs: `results/current/exp00/eda_summary.json`, `results/current/plots/exp00_eda.png`. No LLM calls, cost $0.

**Hypothesis:** the dataset is internally consistent, leak-free and balanced enough to benchmark on.

**Result:** pass. Validator 50/50; independent checks pass (unique IDs, cases and ground truth align, all required policy IDs exist in the corpus, no private fields in model-visible cases, challenge cases only in final test).

| Item | Value |
|---|---|
| Claims | 150 (70 dev / 30 validation / 50 final test) |
| Outcome classes | APPROVE 39, REJECT 40, ESCALATE 36, REQUEST_INFORMATION 35 |
| Majority-class baseline | 26.7% |
| Non-approvable (False Approval Rate denominator) | 111 |
| Case families | 31 |
| Architecture groups | A self-contained 40, B workflow 80, C agent-dynamic 30 |
| Cross-document / temporal amendment / manual touch / challenge | 116 / 28 / 36 / 15 |
| Policy corpus | 22 documents, about 39.5k words |
| Enterprise tables | 11 (previous_expenses is the largest, 2,483 rows) |
| Currencies | SGD 98, JPY 30, INR 22 |

**Note:** the repo contains no video data; "video dataset" was interpreted as this dataset.

**Decision:** gate passed; proceed to Exp 1 and 2. Long-context (Exp 4A) looks feasible at about 50k tokens.
