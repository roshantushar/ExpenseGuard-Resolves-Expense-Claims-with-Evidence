# ExpenseGuard Dataset Card - Final

## Purpose
Synthetic enterprise dataset for evaluating expense-claim readiness for reimbursement: policy compliance, missing information, duplicate/near-duplicate checks, split transactions, approval/exception validation, and selective agentic investigation.

## Size
- 120 model-visible expense cases
- 38-page policy corpus (2024-2026)
- 12 policy source documents
- 9 enterprise lookup tables
- 15 separate guardrail cases
- 10 independently worded/reviewed challenge cases inside the frozen final test

## Architecture distribution
{
  "A_SELF_CONTAINED": 65,
  "B_WORKFLOW": 40,
  "C_AGENT_DYNAMIC": 15
}

## Case-family distribution
{
  "SELF_CONTAINED_POLICY": 24,
  "TEMPORAL_POLICY_VERSION": 7,
  "REGIONAL_PRECEDENCE": 7,
  "EVIDENCE_CONFLICT": 7,
  "MISSING_INFORMATION": 20,
  "DUPLICATE_CHECK": 15,
  "SPLIT_TRANSACTION": 10,
  "FIXED_WORKFLOW": 15,
  "DYNAMIC_AGENT_INVESTIGATION": 15
}

## Outcome distribution
{
  "APPROVE": 31,
  "REJECT": 41,
  "REQUEST_INFORMATION": 37,
  "ESCALATE": 11
}

## Frozen split
{
  "DEVELOPMENT": 60,
  "FINAL_TEST": 40,
  "VALIDATION": 20
}

## Product framing
The task is not fraud detection. It asks: **is this claim ready for reimbursement, and if not, what specifically prevents safe resolution?**

## Data boundaries
- Runtime/model-visible: `02_cases`, `01_policy_corpus`, and approved read-only tools over `03_enterprise_data`.
- Evaluator-only: `04_ground_truth_PRIVATE`.
- Never index or prompt with evaluator-only fields.

## Duplicate and split-transaction design
Duplicate cases include exact duplicates, near duplicates requiring clarification, and legitimate recurring/repeat expenses. Split-transaction cases include related purchases whose combined amount changes approval requirements. Similarity alone is never treated as proof of fraud or intent.

## Agent boundary
Most cases are intentionally solvable by RAG or fixed workflows. Only 15 cases are agent candidates, and all require runtime branching where the first tool observation determines the next evidence source. If a deterministic workflow solves them equally well, the project should conclude that the agent is not justified.

## Limitations
This dataset is synthetic and is designed for controlled architecture/evaluation experiments, not for estimating real-world prevalence, employee behaviour, actual finance processing times, or fraud rates.
