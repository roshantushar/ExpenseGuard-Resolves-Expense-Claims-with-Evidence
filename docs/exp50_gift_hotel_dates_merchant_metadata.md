# Exp 50 — gift tool, hotel date-arithmetic fix, and a merchant-metadata cross-check

Part of the Exp 47-52 arc. Results: `results/current/development/exp50_gift_and_hotel_dates/`.

| Field | Value |
|---|---|
| **Hypothesis** | Three independent, scoped fixes should close most of the remaining dev gap: (1) a dedicated gift-compliance tool recovers the category Exp 48 gave up; (2) computing hotel nights from dates in code instead of trusting the model's count closes a specific arithmetic error class; (3) cross-checking the enterprise `get_merchant_metadata` tool (not free text) against the workflow's coarsened category closes the one remaining dev false approval. |
| **Exact change from previous version (Exp 49)** | (1) Added `check_gift_compliance` (model supplies recipient/gift-form fields, code applies the ceiling). (2) `check_hotel_compliance` now takes `check_in_date`/`check_out_date` and computes the night count by date subtraction in code, instead of accepting a model-supplied night count. (3) Added a merchant-metadata cross-check for `X2-013` ("personal spend"), since `workflow_v2.decide()` only sees the hardened, coarsened visible category ("OTHER") while `get_merchant_metadata` (an enterprise tool the agent already had access to) holds the true category. |
| **Evaluation population** | Full 70-claim development set. |
| **Result** | **43/70 (61.4%)**, 1/52 = 1.9% FAR — effectively tied with the frozen baseline's dev accuracy (43/70, Exp 30), with the safety gap nearly closed to a single false approval. |
| **FAR** | 1/52 = 1.9% (down to one false approval, `X2-013`) |
| **What worked** | The hotel date fix caught the same class of arithmetic bug `check_hotel_compliance` already existed to prevent (ceiling division), one step earlier in the pipeline — confirming date/quantity arithmetic belongs in code, not in the model's head, everywhere it appears. The merchant-metadata cross-check is not a hardening bypass: it uses a tool the agent was always entitled to call, not the free text the hardening specifically degraded. |
| **What failed / open** | `X2-013` was still wrong at the point this run's number was recorded; the merchant-metadata check that closes it was confirmed moments after, carried into Exp 51's number. |
| **Status** | **Adopted.** All three fixes carried forward into Exp 51. |
