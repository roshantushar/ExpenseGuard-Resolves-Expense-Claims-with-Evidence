# Exp 48 — `check_workflow_compliance` redesigned as an allowlist, not a denylist

Part of the Exp 47-52 arc. Results: `results/v2/development/exp48_safe_coverage_dev/`.

| Field | Value |
|---|---|
| **Hypothesis** | Exp 47's regression came from trusting *every* `workflow_v2.decide()` verdict; trusting only the sub-checks that never depend on a free-text-derived field should keep the FAR win without the accuracy loss. |
| **Exact change from previous version (Exp 47)** | Redesigned `check_workflow_compliance` from "trust everything except two known-fixed categories" to "trust nothing except: duplicate detection (bill/date-based), late submission (date-based), restricted merchant (merchant-directory-based), mandatory documentation (bill-field presence)." All four of these checks derive their inputs from structured records or dates, never from a hardened free-text field. |
| **Evaluation population** | Full 70-claim development set. |
| **Result** | **45/70 (64.3%)**, FAR down to 2/52 = 3.9% — the safest full-dataset number reached in this arc so far. |
| **FAR** | 2/52 = 3.9% |
| **What worked** | The allowlist principle itself: only trust a sub-check whose inputs cannot be corrupted by the hardened free-text fields this project deliberately made unreliable. |
| **What failed / traded off** | Accuracy gave up the categories (gift, ground-transport) that happened to work under Exp 47's looser trust but rested on the same fragile free-text logic — a deliberate trade of some correct answers for removing an unsafe trust path. |
| **Status** | **Adopted as the design principle**, carried forward through Exp 49-52. Accuracy shortfall addressed by adding dedicated, domain-guarded tools for the categories given up here (Exp 49, 50). |
