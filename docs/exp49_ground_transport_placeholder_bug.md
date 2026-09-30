# Exp 49 — `check_ground_transport_compliance`: a placeholder-string argument-hallucination bug

Part of the Exp 47-52 arc. Results: `results/current/development/exp49_ground_transport_added/`.

| Field | Value |
|---|---|
| **Hypothesis** | Adding a dedicated, domain-guarded `check_ground_transport_compliance` tool should recover accuracy Exp 48 gave up, without reopening the FAR gap, since ground-transport eligibility derives from structured fields (origin, destination, distance) the agent can pass as arguments. |
| **Exact change from previous version (Exp 48)** | Added `check_ground_transport_compliance` to the guarded tool set. |
| **Evaluation population** | Full 70-claim development set (live-tested before the fix; the bug below was caught mid-run). |
| **Result before fix** | **40/70 (57.1%)**, 4/52 = 7.7% FAR — worse on both axes than Exp 48. |
| **FAR (before fix)** | 4/52 = 7.7% |
| **What failed** | The model passed the literal string `"unknown"` for a missing `origin` field instead of omitting the argument. The tool's `if not origin` guard is defeated by a non-empty string — `"unknown"` is truthy — so the tool proceeded as if `origin` were a real value and returned a wrong disposition. A new, previously-unseen class of argument hallucination distinct from Exp 39's query-quality problem. |
| **Fix** | Added placeholder-string normalization (`_UNSTATED` set) so any of the model's common stand-ins for "not stated" (`"unknown"`, `"n/a"`, `""`, etc.) are treated as missing, not as a real value. |
| **Result after fix** | Folded into Exp 50's run (see that doc for the next confirmed full-dataset number). |
| **Status** | **Bug fixed and adopted**; the tool itself proceeds to Exp 50/51/52. |
