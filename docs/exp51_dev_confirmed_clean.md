# Exp 51 — dev confirmed clean: 44/70, 0.0% FAR

Part of the Exp 47-52 arc. Results: `results/current/dev/exp52_final_confirmed/` (naming: the confirmed dev
number was re-run and saved alongside Exp 52's validation run; see that doc for the file-path note).

| Field | Value |
|---|---|
| **Hypothesis** | With `X2-013` closed by Exp 50's merchant-metadata check, a fresh full run of the 70-claim dev set should confirm 44/70 at 0% FAR, not just the aggregate number from incremental patches. |
| **Exact change from previous version (Exp 50)** | No new code change — this is a confirmation re-run of the Exp 50 design with `X2-013` fixed, served almost entirely from cache (only claims touching the changed code paths produce a different trace). |
| **Evaluation population** | Full 70-claim development set. |
| **Result** | **44/70 (62.9%)**, FAR **0.0%**. One more correct case than the frozen baseline (43/70), at matching safety. |
| **FAR** | 0/52 (0% observed FAR) |
| **What worked / verification method** | Confirmed by a direct diff of every changed prediction against the prior run, not asserted from the aggregate number alone — every case whose prediction changed was individually traced back to the specific fix responsible. |
| **What failed** | Nothing new; this is a confirmation step, not a new design change. |
| **Status** | **Adopted** as the dev-side number for this design. This is a development-set result — see Exp 52 for the validation-split check, and the methodology note in `docs/README.md` on why development performance alone does not establish generalization. |
