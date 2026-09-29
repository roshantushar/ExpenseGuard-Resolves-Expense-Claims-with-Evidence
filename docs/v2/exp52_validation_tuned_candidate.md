# Exp 52 — validation run finds a seventh bug; development-and-validation-selected candidate confirmed

Part of the Exp 47-52 arc. Results: `results/v2/validation/exp51_resolver_v2/` (first validation pass, bug
found mid-run), `results/v2/validation/exp52_final_confirmed/` and `results/v2/dev/exp52_final_confirmed/`
(both splits, re-run after the fix).

| Field | Value |
|---|---|
| **Hypothesis** | The design confirmed on dev in Exp 51 should hold at comparable accuracy and 0% FAR on the 30-claim validation split, the first time this exact design touches that split. |
| **Exact change from previous version (Exp 51)** | A bug was found *during* this run, not before it: `check_hotel_compliance` never verified an approved travel request existed at all (`TRV-1.1`, the same prerequisite `rules_v2.hotel()` and `workflow_v2.hotel()` already check before anything else) — a compliant ceiling with no approved trip silently returned "no issue" on `X2-115`. Fixed, verified against all 4 previously-correct hotel cases individually (none broke), then both splits were re-run in full. |
| **Evaluation population** | 30-claim validation split (first and only look at this split for this design), plus a re-run of the 70-claim development split with the same fix applied. |
| **Result** | Development 44/70 (62.9%), 0/52 falsely approved. **Validation 21/30 (70.0%), 0/22 falsely approved.** Combined 65/100 (65.0%), 0/74 falsely approved. |
| **FAR** | 0/52 dev, 0/22 validation (0% observed FAR on both) |
| **What worked** | The validation run did exactly what a validation run is for: it surfaced a real, previously-unfound bug through fresh data, not through code review. |
| **What failed / caveat** | This design was changed *because of* what this validation run revealed (the TRV-1.1 fix), which means the 21/30 validation number was produced by a design that has now seen and reacted to validation-split behavior. It is **not** an untouched, independent generalization estimate — see the methodology note in `docs/v2/README.md`. The correct label for this design going forward is a **development-and-validation-selected candidate**, not a "fully validated" architecture. |
| **Status** | **Candidate**, not adopted as an official frozen result. Beats the frozen Exp 30/32 design's own development accuracy (44/70 vs. 43/70) at matching observed safety (0% FAR on both splits it has seen), but has never touched the final-test split and has no freeze manifest. Promoting it to official status requires a fresh, untouched holdout per the project's held-out-runs-once rule — not a re-run of the original 50-claim final test, which is no longer unseen for architectures shaped by Exp 33's error analysis (see the methodology note). |
