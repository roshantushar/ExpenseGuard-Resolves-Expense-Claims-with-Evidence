# ExpenseGuard - Final Design, Build Order, and Experiment Plan

## 1. Product problem
ExpenseGuard determines whether a corporate expense claim is ready for reimbursement. It should approve clean claims, reject clearly non-reimbursable claims, request exactly the missing information when the evidence is incomplete, and escalate only genuinely ambiguous/high-risk cases.

This project is **not** fraud detection and does not infer employee intent.

## 2. Core research question
**When does an enterprise expense-compliance case require rules, RAG, a fixed workflow, or bounded agentic investigation, and what measurable improvement does each additional layer provide relative to false-approval risk, human review, latency, and cost?**

## 3. Data model
Every model-visible case already contains structured bill details and employee free text. There is no OCR or multimodal extraction.

Main outcomes:
- `APPROVE`
- `REJECT`
- `REQUEST_INFORMATION`
- `ESCALATE`

Primary metric:
- **Correct Disposition Rate**

Guardrails:
- False Approval Rate
- Human Review Rate
- latency
- cost per case

Feature-level diagnostics:
- missing-field precision/recall
- duplicate precision/recall
- split-transaction detection precision/recall
- retrieval Recall@K / Precision@K / MRR / nDCG
- unsupported decision rate
- tool-selection metrics

## 4. Non-negotiable privacy/leakage boundaries
Runtime/model-visible:
- `02_cases/*`
- `01_policy_corpus/*`
- approved read-only functions over `03_enterprise_data/*`

Evaluator-only:
- `04_ground_truth_PRIVATE/*`

Never put expected decision, required policy IDs, architecture labels, acceptable tool paths, duplicate truth, split truth, or challenge flags into prompts or retrieval indexes.

## 5. Build order - do not start with the agent

### Phase 0 - Validate the dataset
Run:
```bash
python 05_generation/validate_dataset.py
```
Stop if validation fails.

### Phase 1 - Smallest feasibility slice
Use 10 DEVELOPMENT cases only.
Build:
1. loader;
2. schema validation;
3. one foundation-model call with relevant policy supplied directly;
4. structured output;
5. exact evaluator.

Success gate: end-to-end cases execute and evaluator produces reproducible results.

### Phase 2 - Non-AI rules baseline
Implement a respectable deterministic baseline for:
- required fields;
- obvious prohibited personal categories;
- exact duplicate bill number;
- deterministic amount/date checks where applicable.

Do not deliberately cripple it. Sometimes rules winning is a valid result.

### Phase 3 - LLM without company policy
Claim only -> model -> disposition.
Purpose: demonstrate whether a generic model invents/assumes company policy.

### Phase 4 - Full-policy long-context baseline
Give the complete policy corpus to the model.
This must happen before RAG because the corpus is only ~38 pages. If long context is already accurate and economically acceptable, RAG must justify itself rather than being assumed necessary.

### Phase 5 - Naive RAG
Start with:
- source documents as retrieval units;
- dense retrieval;
- fixed chunking;
- top-k = 3;
- no reranker.

Measure retrieval separately from decision quality.

### Phase 6 - RAG experiments
Only change levers tied to observed failure modes:
1. chunk size / overlap;
2. top-k;
3. BM25 vs dense vs hybrid;
4. metadata filters for year, region, category;
5. query rewriting only if vocabulary mismatch is measured;
6. reranking only if high recall but poor ranking/noisy context is measured.

Do not run a giant combinatorial grid.

### Phase 7 - Policy oracle
Inject exactly the correct policy clauses from evaluator ground truth into the reasoner.
Purpose: upper bound and failure isolation.

Compare:
- RAG result;
- oracle-policy result.

If oracle is much better -> retrieval problem.
If oracle remains poor -> reasoning/prompt problem.

### Phase 8 - Hybrid deterministic + LLM architecture
Move arithmetic and exact rules into code:
- per-attendee arithmetic;
- date windows;
- amount comparisons;
- percentage tips;
- fixed FX conversion using `fx_rates.csv`;
- exact duplicate check.

LLM handles semantic interpretation, policy applicability, evidence explanation.

Compare with LLM-decides-everything.

### Phase 9 - Duplicate / previous-claim feature
Implement `search_previous_expenses`.

Evaluate three classes separately:
1. exact duplicate;
2. possible/near duplicate;
3. legitimate recurring/repeat expense.

Diagnostics:
- duplicate precision;
- duplicate recall;
- false-block rate on legitimate repeats.

Never label a person fraudulent. This is claim-level compliance only.

### Phase 10 - Split-transaction feature
Search historical related expenses and combine relevant same-merchant/project/date spend before applying approval thresholds.

Evaluate:
- related-expense retrieval;
- combined amount correctness;
- approval decision correctness.

### Phase 11 - Read-only enterprise tool layer
Implement typed functions:
- `get_employee_profile(employee_id)`
- `get_travel_request(employee_id, transaction_date)`
- `get_manager_approval(...)`
- `get_exception_record(...)`
- `get_project_status(project_id)`
- `search_previous_expenses(employee_id, merchant, transaction_date, amount=None, bill_number=None)`
- `get_conference_registration(employee_id, event_id)`

Return compact JSON. Tool descriptions must clearly distinguish neighbouring tools.

### Phase 12 - Fixed workflow
Run all workflow cases and agent-candidate cases through a deterministic workflow.

Expected workflow strengths:
- duplicate checking;
- split transaction + approval lookup;
- employee grade + travel lookup;
- project + manager approval;
- explicit exception ID lookup.

This phase is the agent feasibility gate.

### Phase 13 - Decide whether an agent is actually needed
For the 15 candidate dynamic cases, inspect whether a finite predetermined workflow solves them cleanly.

Agent is justified only if:
1. first tool result changes which tool should be called next;
2. adding a simple deterministic branch does not remove the need for runtime model-directed sequencing;
3. agent materially improves task success or review burden;
4. false approvals do not worsen unacceptably.

If the workflow performs equally well, **stop and conclude the agent is not justified**.

### Phase 14 - Bounded single-agent investigation
If Phase 13 justifies it, build one bounded ReAct-style agent.

Guards:
- step cap;
- budget cap;
- duplicate-action prevention;
- tool schema validation;
- read-only tools only;
- explicit `REQUEST_INFORMATION` and `ESCALATE` exits.

Log tool names, arguments, observations, turns, tokens, latency and cost. Do not log hidden chain-of-thought.

### Phase 15 - Agent experiments
Required only if agent survives the feasibility gate:
1. workflow vs agent on dynamic subset;
2. minimum tool set vs expanded set;
3. vague vs discriminative tool descriptions;
4. single-tool ablation;
5. sequential vs dependency-aware parallel calls where independent;
6. model battery across at least 3 distinct model families/price tiers if budget permits.

Run dynamic/negative stochastic cases 3 times where possible. Report raw trial counts, not only percentages.

### Phase 16 - Two reproduced failures
Failure A: working agent minus loop/duplicate-action protection.
Report before/after:
- turns;
- tokens;
- cost;
- pass rate;
- step-cap hits.

Failure B: working agent with ambiguous overlapping tool descriptions.
Report before/after:
- wrong-tool rate;
- task success;
- latency/cost if changed.

### Phase 17 - Guardrail suite
Run `04_ground_truth_PRIVATE/guardrail_cases.csv` separately from normal evals.
At least cover:
- prompt injection;
- fake authority;
- malicious tool output;
- loop;
- step/budget caps;
- malformed/unknown tools;
- tool timeout;
- evaluator-label access attempt;
- irreversible financial action attempt;
- always-escalate negative control;
- duplicate over-block negative control;
- wrong-year policy;
- conflicting evidence.

### Phase 18 - Selective final architecture
Compare:
A. agent for every case;
B. selective routing:
   - simple/self-contained -> hybrid RAG;
   - predictable external checks -> workflow;
   - genuinely dynamic evidence path -> agent.

A good final finding may be that most claims do not need an agent.

### Phase 19 - Cost-to-serve
Use measured values for:
- model input/output tokens;
- retrieval calls;
- tool calls;
- latency;
- AI cost;
- automated-success/review rate.

Then model:
1. variable AI cost;
2. expected human fallback = human-review rate x assumed review cost;
3. fixed monthly infra/eval/monitoring.

Label human-review minutes/hourly rates as assumptions and run sensitivity ranges.

## 6. Evaluation design

### Final test discipline
- Tune only on DEVELOPMENT and VALIDATION.
- Freeze architecture before FINAL_TEST.
- 10 final-test cases are independently worded/reviewed challenge cases.

### Headline reporting
For each major architecture report:
- correct / N;
- Correct Disposition Rate;
- 95% Wilson confidence interval;
- false approvals / non-approvable N;
- Human Review Rate;
- median/P95 latency;
- average cost per case.

### Diagnostic appendix
- per-class precision/recall/F1;
- retrieval metrics;
- missing-field accuracy;
- duplicate/split metrics;
- tool-selection metrics;
- turns/tokens;
- failure taxonomy.

## 7. Failure taxonomy
Use one primary reason per failure:
- `RETRIEVAL_MISS`
- `RETRIEVAL_DISTRACTOR`
- `WRONG_POLICY_VERSION`
- `POLICY_PRECEDENCE_ERROR`
- `REASONING_ERROR`
- `ARITHMETIC_ERROR`
- `MISSING_FIELD_ERROR`
- `DUPLICATE_FALSE_POSITIVE`
- `DUPLICATE_FALSE_NEGATIVE`
- `SPLIT_TRANSACTION_MISS`
- `WRONG_TOOL`
- `TOOL_ARGUMENT_ERROR`
- `TOOL_RESULT_MISREAD`
- `LOOP`
- `PREMATURE_STOP`
- `FAILED_TO_ESCALATE`
- `OVER_ESCALATION`
- `PROMPT_INJECTION`
- `SYSTEM_ERROR`

## 8. Recommended report story
1. Expense claims are costly when routine cases require manual handling and rework.
2. Start with deterministic checks.
3. Generic LLM understands language but lacks company policy.
4. Full context establishes whether retrieval is even necessary.
5. RAG is introduced only if it improves grounding/cost/scalability.
6. Oracle isolates retrieval from reasoning.
7. Deterministic code takes over arithmetic and exact checks.
8. Duplicate and split checks show why enterprise history matters.
9. Fixed workflows handle predictable cross-system evidence.
10. Only dynamic cases are candidates for an agent.
11. Agent is retained only if measured value exceeds its cost/risk.
12. Final architecture uses the cheapest sufficient path per case.

## 9. Definition of success
A strong project is **not** one where the agent wins. A strong project is one where the experiments reveal the correct architecture boundary and the system reduces unsafe decisions and unnecessary human review without hiding cost or uncertainty.
