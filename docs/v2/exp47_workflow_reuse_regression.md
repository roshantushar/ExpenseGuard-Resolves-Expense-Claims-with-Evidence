# Exp 47 — Reusing `workflow_v2.decide()` as a catch-all tool: a regression, caught immediately

Part of the Exp 47-52 arc that closes Exp 45's full-dataset FAR gap. Results:
`results/v2/development/exp47_full_coverage_dev/`.

| Field | Value |
|---|---|
| **Hypothesis** | `workflow_v2.decide()` already implements every claim-family's policy mechanics correctly (it is the Exp 18 fixed workflow); reusing it as a blanket "catch everything else" tool inside the guarded-agent's disposition gate should extend Exp 44's safety win to the full dataset for free. |
| **Exact change from previous version (Exp 44/45)** | Added `check_workflow_compliance`, a thin wrapper that calls `workflow_v2.decide()` and returns its verdict as a trusted disposition for the disposition gate, for every claim family without its own dedicated guarded tool. |
| **Evaluation population** | Full 70-claim development set. |
| **Result** | **46/70 (65.7%)**, down from Exp 45's 51/70. FAR improved to 3/52 = 5.8%. |
| **FAR** | 3/52 = 5.8% (better than Exp 45's 6/52 = 11.5%, but the accuracy regression is the finding) |
| **HRR** | 25.7% (up from Exp 45's 21.4%) |
| **What worked** | FAR did improve versus Exp 45 — trusting *some* code-computed disposition is still safer than trusting the model alone. |
| **What failed** | `workflow_v2.decide()` internally parses the same hardened free-text fields (attendee counts, gift recipients, alcohol amounts) that every other fix in this arc exists to route *around*. Its own verdicts could be just as wrong as a false approval, and the disposition gate trusted them unconditionally — overriding 9 cases the model had already gotten right on its own, confirmed across meal, delegation, gift, mileage and approval-tier families. |
| **Status** | **Rejected.** The "trust everything except two known-fixed categories" (denylist) design was abandoned in favor of Exp 48's allowlist. |
