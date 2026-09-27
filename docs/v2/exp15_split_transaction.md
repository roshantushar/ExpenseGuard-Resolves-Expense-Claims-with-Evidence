# V2 Exp 15 — Split-transaction workflow decomposition (short confirmatory experiment, $0)

Notebook: `notebooks/v2/exp15_split_transaction.ipynb`. Cost: $0. Development split only.

**Question:** Exp 14 confirmed split *classification* (4/4). Exp 15 asks whether the complete chain — related-record retrieval, grouping, combined-amount calculation, policy consequence — works, not just the label.

| Part | Raw count |
|---|---|
| 15A related-record retrieval | 4/4 |
| 15B split grouping (0/66 false groupings on negatives) | 4/4 |
| 15C combined-amount calculation (exact to the cent, FX-normalized) | 4/4 |
| 15D policy consequence (correct final disposition) | 4/4 |

**Finding:** Exp 14 established split classification; Exp 15 decomposed the complete split workflow and confirmed that retrieval, grouping, amount calculation, and policy consequence were all correct on the four development positives, with no false split grouping among negatives. Two of the four cases (India, Japan) combine to below SGD 500 in raw terms but correctly trigger the region-specific local-currency threshold, confirming the right threshold is used, not just correct arithmetic.

**Caution:** 4 positive cases is tiny; this is a raw-count finding, not a reliability percentage.

**Decision:** no change needed. Next: Exp 16 (enterprise-evidence oracle), reframed to isolate raw records vs. resolved facts vs. deterministic outcome.
