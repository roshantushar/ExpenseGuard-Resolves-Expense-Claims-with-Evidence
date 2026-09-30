# Exp 0 — Dataset integrity and leakage audit

**Question:** Is the dataset internally consistent, correctly split and free of label leakage before any system touches it?

**Setup:** `python3 scripts/exp00_validate.py` runs `dataset_generator.validate` on the packaged files only (no generator internals). No model calls, cost $0.

**Result:** 45/45 checks passed. 150 cases (40 self-contained / 80 workflow / 30 dynamic), split 70/30/50, outcomes balanced per split, 15 challenge cases all in the final test, 116 cross-document cases, 28 decided by mid-year circulars. The reference engine re-derives every label from the packaged CSVs; no ground-truth keys or label strings appear in cases, policy or tables; no employee is shared across splits.

**Plot:** `results/current/plots/exp00_dataset_distributions.png` (cost/latency/tokens not applicable: no model calls).

**Decision:** Dataset accepted as the benchmark. Frozen final-test rules apply again: final-test cases are run once, after a freeze.
