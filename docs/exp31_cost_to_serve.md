# V2 Exp 31 — Cost-to-serve ($0)

Notebook: `notebooks/v2/exp31_cost_to_serve.ipynb`. Cost: $0 (arithmetic over Exp 30's measured numbers). Development split only.

**31A, measured:** deterministic path $0/claim, instant. LLM-residual path **$0.000832/claim, 2,077 ms avg**. Blended: **$0.000428/claim**, 51% of claims invoke the LLM. Scaled: $0.43 / $4.28 / $42.81 at 1k / 10k / 100k claims per month — trivial at every scale.

**31B, human review (three labelled assumption scenarios: low $5, medium $15, high $30/review), at HRR = 18.6%:**

| Scenario | 1,000/mo | 10,000/mo | 100,000/mo |
|---|---|---|---|
| Low | $928.93 | $9,289.28 | $92,892.81 |
| Medium | $2,785.93 | $27,859.28 | $278,592.81 |
| High | $5,571.43 | $55,714.28 | $557,142.81 |

Human review costs about **2,100x the AI cost** at every scale — it dominates the cost-to-serve story, not the model.

**31C, incorrect-decision cost, split by consequence (not one flat rate)** — of Exp 30's 27 dev errors:

| Category | Count | Assumed cost/instance | Modelled total |
|---|---|---|---|
| missed_escalate | 4 | $100 | $400 |
| false_rejection | 8 | $30 | $240 |
| unnecessary_request_info | 13 | $8 | $104 |
| missed_request_info | 2 | $40 | $80 |
| false_approval | 0 | $200 | $0 |

**Exp 30 has 0 false approvals**, so the story is not "39% error rate = 39% loss" — the highest-cost category never occurred. `missed_escalate` (bypassing a required human review) is the riskiest realized category.

**Decision:** AI cost is negligible at every scale; human review is the dominant, controllable lever (ties directly to Exp 29's abstention work); error cost is real but concentrated in `missed_escalate` and `false_rejection`, both pointing back to the LLM-residual path (36.1% accuracy, Exp 30) as the priority for improvement. All dollar figures are modelled assumptions, never measured savings. Next: Exp 32, the frozen final test, run once.
