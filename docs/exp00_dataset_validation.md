# Experiment 0 — Dataset integrity and leakage audit

**Question:** Is the benchmark trustworthy before any model or retrieval experiment runs?
**Script:** `scripts/exp00_validate.py` · **Output:** `results/exp00_dataset_validation.json`, `results/plots/exp00_dataset_distributions.png`
**Cost / LLM calls:** none.

## Result
32 / 32 checks passed (0 critical errors). Stop gate cleared.

## What is checked
- IDs unique; cases and ground truth cover the same 120 IDs; split 60/20/40; split files agree with `all_cases`; architecture 65/40/15; 10 challenge cases, all in FINAL_TEST.
- Every required/triggered policy ID exists in the corpus; every policy doc has an effective date.
- Every enterprise reference resolves (employees, projects, travel events, exceptions, approvals); an FX rate exists for every case year/month/currency.
- Duplicate and split links resolve; split `combined_amount` equals current claim + related expenses; agent candidates have a branch trigger and are not workflow-sufficient; missing-info cases list missing fields.
- Leakage: no ground-truth keys, label strings or ground-truth reason text in cases, policy docs, metadata or enterprise tables. Case IDs appear in `manager_approvals` / `policy_exceptions` / `previous_expenses` only as join keys.
- The packaged `validate_dataset.py` passes.

## Observations that shape later experiments
- Final test is dominated by non-approvable cases (5 APPROVE / 16 REJECT / 15 REQUEST_INFORMATION / 4 ESCALATE), so False Approval Rate has a small denominator and the Correct Disposition Rate needs its Wilson interval.
- Only 20 validation cases, so validation numbers will be noisy.

## Limitations
Split combined-amount check only covers same-currency related expenses. Leakage checks are string-based, not semantic.
