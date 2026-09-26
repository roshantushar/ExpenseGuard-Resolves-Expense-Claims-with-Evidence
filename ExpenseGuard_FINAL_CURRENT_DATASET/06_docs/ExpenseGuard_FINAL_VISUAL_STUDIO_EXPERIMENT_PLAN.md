# ExpenseGuard — Final Visual Studio Build & Experiment Plan

**Project:** PE6201 Emerging AI Technologies — End-of-Course Project  
**Product:** ExpenseGuard  
**Dataset version:** FINAL-CURRENT-2026-09-26  
**Dataset size:** 120 claims  
**Policy corpus:** 38 pages, 12 source documents, 2024–2026  
**Architecture mix:** 65 self-contained/RAG, 40 fixed-workflow, 15 dynamic agent-candidate  
**Frozen split:** 60 development / 20 validation / 40 final test  
**Primary metric:** Correct Disposition Rate  
**Safety/business guardrails:** False Approval Rate, Human Review Rate, latency, cost per case  

---

# 1. Product story

ExpenseGuard determines whether an employee expense claim is **ready for reimbursement**.

For each claim it must return exactly one of:

- `APPROVE`
- `REJECT`
- `REQUEST_INFORMATION`
- `ESCALATE`

The product goal is not “use an agent.” The product goal is:

> **Resolve routine claims safely and quickly, request exactly the missing evidence when a claim is incomplete, detect compliance issues such as duplicates or split transactions, and send only genuinely ambiguous/high-risk cases to a finance reviewer.**

The project deliberately compares progressively more capable architectures to determine the **cheapest sufficient design**.

The architectural question is:

> **When are deterministic rules sufficient, when is RAG sufficient, when is a fixed workflow needed, and when — if ever — does bounded agentic investigation add enough value to justify its extra cost, latency, and failure modes?**

Do not force an agent into the final design. If workflow performance is equivalent on the candidate agent cases, the correct project conclusion is that an agent is not justified.

---

# 2. Scope

## In scope

1. Policy compliance
2. Missing-information detection
3. Exact duplicate detection
4. Near-duplicate / possible-duplicate detection
5. Legitimate repeat-expense discrimination
6. Split-transaction detection
7. Approval validation
8. Exception validation
9. Temporal policy-version resolution
10. Regional policy precedence
11. Cross-document policy retrieval
12. Evidence conflict handling
13. Read-only enterprise data lookup
14. Selective workflow/agent investigation
15. Guardrails and abstention/escalation
16. Cost, latency, and human-review analysis

## Explicitly out of scope

- Fraud accusations or employee fraud scoring
- Inferring employee intent, honesty, or character
- OCR / receipt image extraction
- Tax adjudication
- Legal adjudication
- Automatic reimbursement/payment execution
- Disciplinary action
- Real employee or company data
- Multi-agent systems
- Email search unless a measured failure later proves it necessary

---

# 3. Dataset layout

Use the supplied package exactly as follows.

```text
ExpenseGuard_FINAL_CURRENT_DATASET/
│
├── 01_policy_corpus/
│   ├── Northstar_Expense_Policy_Corpus_2024_2026.pdf
│   ├── policy_metadata.json
│   └── source_documents/
│
├── 02_cases/
│   ├── development.jsonl
│   ├── validation.jsonl
│   ├── final_test.jsonl
│   ├── all_cases.jsonl
│   └── all_cases.csv
│
├── 03_enterprise_data/
│   ├── employees.csv
│   ├── travel_requests.csv
│   ├── manager_approvals.csv
│   ├── policy_exceptions.csv
│   ├── previous_expenses.csv
│   ├── project_registry.csv
│   ├── conference_registry.csv
│   ├── merchant_directory.csv
│   └── fx_rates.csv
│
├── 04_ground_truth_PRIVATE/
│   ├── ground_truth.jsonl
│   ├── case_family_manifest.csv
│   └── guardrail_cases.csv
│
├── 05_generation/
│   ├── regenerate_dataset.py
│   ├── validate_dataset.py
│   ├── generation_config.json
│   └── README.md
│
├── 06_docs/
│   ├── ExpenseGuard_FINAL_VISUAL_STUDIO_EXPERIMENT_PLAN.md
│   └── CODING_AGENT_START_HERE.md
│
├── DATASET_CARD.md
├── README.md
└── SHA256SUMS.txt
```

## Leakage boundary

**Runtime/model-visible**
- `01_policy_corpus/*`
- `02_cases/*`
- read-only tool functions over `03_enterprise_data/*`

**Evaluator only**
- `04_ground_truth_PRIVATE/*`

Never place evaluator-only fields in:
- prompts
- retrieval indexes
- model context
- tool descriptions
- runtime logs visible to the model

Do not expose:
- expected decision
- required policy IDs
- architecture group
- duplicate truth
- split-transaction truth
- acceptable tool paths
- challenge flags
- failure reason

---

# 4. Dataset facts to preserve

## Architecture distribution

- `A_SELF_CONTAINED`: 65
- `B_WORKFLOW`: 40
- `C_AGENT_DYNAMIC`: 15

## Case-family distribution

- `SELF_CONTAINED_POLICY`: 24
- `TEMPORAL_POLICY_VERSION`: 7
- `REGIONAL_PRECEDENCE`: 7
- `EVIDENCE_CONFLICT`: 7
- `MISSING_INFORMATION`: 20
- `DUPLICATE_CHECK`: 15
- `SPLIT_TRANSACTION`: 10
- `FIXED_WORKFLOW`: 15
- `DYNAMIC_AGENT_INVESTIGATION`: 15

## Outcome distribution

- `APPROVE`: 31
- `REJECT`: 41
- `REQUEST_INFORMATION`: 37
- `ESCALATE`: 11

## Frozen split

- Development: 60
- Validation: 20
- Final test: 40

Ten final-test cases are independently worded/reviewed challenge cases.

---

# 5. Repository structure to build

Create the project repository like this:

```text
expenseguard/
│
├── data/                     # copy supplied dataset package here
├── src/
│   ├── config.py
│   ├── schemas.py
│   ├── loaders/
│   ├── rules/
│   ├── retrieval/
│   ├── reasoning/
│   ├── tools/
│   ├── workflows/
│   ├── agents/
│   ├── routing/
│   ├── guardrails/
│   ├── evaluation/
│   └── observability/
│
├── experiments/
│   ├── exp01_rules/
│   ├── exp02_llm_no_policy/
│   ├── ...
│   └── exp22_final_test/
│
├── results/
│   ├── development/
│   ├── validation/
│   ├── final/
│   └── plots/
│
├── tests/
├── scripts/
├── requirements.txt
├── .env.example
└── README.md
```

Every experiment must write a machine-readable result file, preferably JSONL/CSV, plus a compact summary JSON.

Minimum result fields:

```json
{
  "case_id": "EXP-0001",
  "experiment_id": "EXP05_NAIVE_RAG",
  "predicted_decision": "APPROVE",
  "latency_ms": 812,
  "input_tokens": 1102,
  "output_tokens": 91,
  "model_cost_usd": 0.00042,
  "retrieved_policy_ids": ["MEAL-1.1", "JP-1.1"],
  "tool_calls": [],
  "abstained": false,
  "error": null
}
```

Ground-truth comparison must happen in evaluator code after runtime completion.

---

# 6. Metrics

## 6.1 Headline metric

### Correct Disposition Rate

```text
correct final dispositions / total evaluated claims
```

Disposition is one of:
- APPROVE
- REJECT
- REQUEST_INFORMATION
- ESCALATE

Report:
- raw count `correct / N`
- percentage
- 95% Wilson confidence interval

Do not report only a percentage.

## 6.2 Safety/business guardrails

### False Approval Rate

Among cases that should **not** be approved:

```text
incorrect APPROVE / non-approvable cases
```

This is the most important safety metric.

### Human Review Rate

Cases routed to actual/manual finance review:

```text
manual_touch_required predictions / total cases
```

Do not automatically count every `REQUEST_INFORMATION` as human review. A claim can request information from the employee and be automatically reprocessed.

### Latency
Report:
- median
- P95

### Cost per case
Use actual token usage and actual model/API pricing used during the run.

Do not invent production savings.

## 6.3 Diagnostic metrics

Use only where relevant:

- macro precision / recall / F1
- missing-field precision / recall
- duplicate precision / recall
- duplicate false-block rate
- split-transaction precision / recall
- retrieval Recall@K
- retrieval Precision@K
- MRR
- nDCG
- correct-policy-version rate
- required-evidence coverage
- tool-selection precision
- unnecessary tool-call rate
- average turns
- step-cap hits
- unsupported-decision rate

Diagnostics do not replace the primary metric.

---

# 7. Stop-gate philosophy

Do not build later architecture merely because it is in this plan.

Each stage has a gate.

If a simpler architecture already solves the problem adequately:
1. record the result;
2. explain what the next layer could theoretically add;
3. run only the experiment necessary to test that hypothesis;
4. reject the extra layer if it adds no measurable value.

The project is successful if it finds the correct architecture boundary, even if that boundary is below “agent.”

---

# 8. Experiment sequence

# Experiment 0 — Dataset integrity and leakage audit

## Question
Is the benchmark internally valid before any model is tested?

## Build
Run:

```bash
python data/05_generation/validate_dataset.py
```

Add your own checks for:
- duplicate case IDs
- split counts
- missing policy references
- missing enterprise references
- label fields leaking into model-visible files
- challenge-set membership
- architecture distribution
- outcome distribution

## Required output
`results/exp00_dataset_validation.json`

## Pass gate
Zero critical validation errors.

If this fails, stop the project and repair the dataset.

---

# Experiment 1 — Smallest end-to-end feasibility slice

## Question
Can one claim flow through input → model → structured disposition → evaluator?

## Data
10 development cases only.

## Architecture
Provide the relevant policy text manually/directly. No retrieval.

## Build
- case loader
- Pydantic/JSON schema
- one LLM call
- structured output
- evaluator

## Output schema
At minimum:

```json
{
  "decision": "APPROVE",
  "policy_evidence": ["..."],
  "missing_fields": [],
  "explanation": "..."
}
```

## Metric
Correct Disposition Rate on 10 development cases.

## Goal
Engineering feasibility, not a headline benchmark.

---

# Experiment 2 — Deterministic rules baseline

## Question
How far can a non-AI baseline go?

## Implement
Rules for:
- required-field presence
- deterministic date windows
- fixed thresholds
- exact personal/prohibited categories where unambiguous
- exact duplicate bill number
- exact merchant/date/amount duplicate
- frozen FX conversion
- simple approval threshold arithmetic

Do not deliberately weaken the baseline.

## Evaluate
All development cases.

## Record
- Correct Disposition Rate
- false approvals
- Human Review Rate
- latency
- near-zero compute cost

## Why this matters
This is the baseline every later architecture must beat or complement.

---

# Experiment 3 — Generic LLM without company policy

## Question
Can a generic model resolve claims without company-specific grounding?

## Input
Claim only.

## Do not provide
- policy corpus
- enterprise tools
- ground truth

## Hypothesis
The model can interpret language but may invent or assume policy.

## Evaluate
Development set.

## Additional diagnostic
Unsupported-policy assertion rate.

## Expected learning
This establishes why company-specific grounding is necessary.

---

# Experiment 4 — Full-policy long-context baseline

## Question
If the complete corpus fits in context, is RAG even necessary?

## Input
- claim
- complete current policy corpus

## Important
Do this before RAG.

## Evaluate
Development + validation.

## Measure
- Correct Disposition Rate
- false approvals
- token count
- latency
- cost
- wrong-year policy use

## Decision gate
RAG must later demonstrate at least one of:
- better accuracy
- better version/region precision
- lower token cost
- lower latency
- better scalability
- better evidence traceability

If not, long context may be the better design.

---

# Experiment 5 — Naive RAG baseline

## Question
How well does the simplest retrieval system work?

## Retrieval design
- source policy documents/chunks
- dense embeddings
- fixed chunking
- top-k = 3
- no metadata filtering
- no query rewrite
- no reranker

## Evaluate retrieval separately
Use evaluator-only required-policy IDs after the run.

Measure:
- Recall@3
- Precision@3
- MRR
- required-evidence coverage

Then measure final disposition quality.

## Save
Every retrieved chunk and score for failure analysis.

---

# Experiment 6 — Chunk size and overlap

## Question
Are retrieval failures caused by chunk boundaries?

## Compare
A small controlled set such as:
- 300 tokens / 50 overlap
- 600 / 100
- 900 / 150

Do not run a huge grid.

## Dataset focus
Cross-document and chunk-boundary-like development cases.

## Select
Best validation setting based primarily on evidence recall and downstream disposition, not retrieval metric alone.

---

# Experiment 7 — Top-K sensitivity

## Question
How much evidence should enter the reasoner?

## Compare
- k=1
- k=3
- k=5
- optionally k=8 if measured misses remain

## Watch for
Higher K can raise recall while worsening distractor errors, latency, and token cost.

## Report
Retrieval metrics + final disposition + context tokens.

---

# Experiment 8 — Sparse vs dense vs hybrid retrieval

## Question
Which retrieval family best handles the policy corpus?

## Compare
- BM25
- dense
- hybrid BM25+dense

## Focus
Cases with:
- exact policy terms
- semantic paraphrases
- cross-document evidence
- similarly worded distractors

## Decision
Choose one retrieval family for later experiments.

---

# Experiment 9 — Metadata-aware retrieval

## Question
Can metadata prevent wrong-year and wrong-region policy retrieval?

## Metadata
Use:
- effective year/date
- region
- document type/category

## Compare
Best retrieval from Experiment 8:
- without metadata filters
- with metadata filters

## Key metrics
- correct-policy-version rate
- regional-precedence accuracy
- Recall@K
- disposition accuracy

This experiment is especially important because confident use of a superseded policy is a silent failure.

---

# Experiment 10 — Query rewriting and reranking, only if justified

## Trigger
Run only if Experiments 5–9 show:
- vocabulary mismatch → test query rewrite
- high Recall@K but poor ordering/noisy context → test reranker

## Rule
Do not add both automatically.

## Compare
Before/after:
- retrieval metrics
- final disposition
- latency
- cost

If no material gain, remove the component.

---

# Experiment 11 — Policy oracle

## Question
How much error comes from retrieval versus reasoning?

## Method
Use evaluator code to inject the exact required policy clauses into the reasoner.

This is an **evaluation-only oracle**. Never expose oracle data to the normal runtime.

## Compare
- optimized RAG
- policy oracle

## Interpretation
If oracle >> RAG:
- retrieval is the bottleneck.

If oracle ≈ RAG but both fail:
- reasoning/prompt/application is the bottleneck.

This is one of the most important diagnostic experiments.

---

# Experiment 12 — Hybrid RAG + deterministic compliance logic

## Question
Should arithmetic and exact compliance rules remain in the LLM?

## Move to code
- amount comparison
- per-attendee calculation
- tips/percentages
- date windows
- currency conversion using frozen FX table
- exact duplicate checks
- deterministic approval thresholds

## Leave to model
- semantic category interpretation
- policy applicability
- natural-language evidence explanation
- ambiguous evidence interpretation

## Compare
- LLM/RAG decides everything
- RAG + deterministic evaluator

## Metrics
Primary + false approvals + arithmetic-error count.

Expected result: hybrid should be more reliable.

---

# Experiment 13 — Missing-information resolution

## Question
Can the system ask for exactly what is missing rather than simply escalating?

## Dataset
20 `MISSING_INFORMATION` cases plus relevant negative controls.

## Evaluate
1. correct `REQUEST_INFORMATION` disposition
2. missing-field precision
3. missing-field recall
4. over-request rate

## Product requirement
The system should request specific missing evidence, e.g.:

> “Provide the external attendee names and organisations.”

not:

> “Please provide more information.”

This experiment supports the product claim of reducing back-and-forth.

---

# Experiment 14 — Duplicate bill / previous-claim checking

## Question
Can ExpenseGuard distinguish true duplicates from legitimate repeat expenses?

## Tool
`search_previous_expenses(...)`

## Classes
- exact duplicate
- possible/near duplicate
- legitimate repeat
- no duplicate

## Baselines
A. deterministic exact matching  
B. fuzzy deterministic candidate generation  
C. semantic/model-assisted resolution for ambiguous candidates

## Metrics
- duplicate precision
- duplicate recall
- false-block rate on legitimate repeats
- final disposition accuracy

## Safety rule
Never output “fraud.”
Treat this as claim-level compliance only.

---

# Experiment 15 — Split-transaction detection

## Question
Can the system identify related claims whose combined amount changes the approval requirement?

## Method
Retrieve previous expenses related by appropriate fields such as:
- employee
- merchant
- project
- date/window
- business purpose

Combine amounts deterministically.

## Measure
- related-expense retrieval accuracy
- combined-amount correctness
- triggered-policy correctness
- final disposition accuracy

## Negative controls
Include similar transactions that are genuinely separate.

Avoid over-blocking.

---

# Experiment 16 — Enterprise evidence oracle

## Question
If the exact external facts are supplied, can the reasoner make the correct decision?

## Method
For workflow/agent cases, evaluator supplies exactly the required enterprise facts.

## Compare
- normal tool/workflow result
- enterprise-evidence oracle

## Interpretation
If oracle succeeds and normal workflow fails:
- tool selection/retrieval/integration problem.

If both fail:
- reasoning/policy application problem.

---

# Experiment 17 — Typed read-only enterprise tools

## Build these tools

```text
get_employee_profile(employee_id)
get_travel_request(employee_id, transaction_date)
get_manager_approval(...)
get_exception_record(...)
get_project_status(project_id)
search_previous_expenses(...)
get_conference_registration(employee_id, event_id)
get_merchant_metadata(...)
```

## Tool requirements
- strict typed parameters
- compact JSON return values
- read-only
- clear error states
- no hidden ground-truth information
- discriminative descriptions

## Evaluate
Tool correctness separately before model orchestration.

---

# Experiment 18 — Fixed workflow baseline

## Question
How many external-evidence cases can be solved with predictable orchestration?

## Run on
- all 40 `B_WORKFLOW` cases
- all 15 `C_AGENT_DYNAMIC` candidate cases

## Workflow should explicitly handle known patterns
Examples:
- employee grade → threshold
- duplicate → previous-expense lookup
- split claim → history → approval lookup
- explicit exception ID → exception lookup
- project → manager approval
- travel record → fixed known check where applicable

## Measure
- Correct Disposition Rate
- false approvals
- Human Review Rate
- tool calls
- latency
- cost

This is the **agent feasibility gate**.

---

# Experiment 19 — Agent-necessity audit

## Question
Do any cases genuinely require runtime model-directed tool sequencing?

For each of the 15 agent-candidate cases answer:

1. Could a reasonable finite workflow be written before observing runtime tool results?
2. Does the first observation change which evidence source should be queried next?
3. Is the branch semantic/open-ended enough that simply adding one `if/else` makes no sense?
4. Does dynamic sequencing improve outcome rather than merely look sophisticated?

## Reclassify if necessary
If a case is really workflow-solvable, reclassify it analytically for the report.

Do not manipulate final-test labels after seeing performance. This audit is about architecture interpretation, not changing the frozen expected decision.

## Gate
Only proceed to an agent if there remains a credible dynamic subset.

---

# Experiment 20 — Bounded single-agent investigation

## Run only if Experiment 19 justifies it.

## Architecture
One bounded ReAct-style tool-using agent.

Do **not** use a multi-agent architecture.

## Required controls
- max step cap
- dollar/token budget cap
- duplicate-action prevention
- tool schema validation
- read-only tools
- explicit `REQUEST_INFORMATION`
- explicit `ESCALATE`
- stop on sufficient evidence

## Logging
Log:
- tool name
- args
- returned observation
- state summary
- turns
- tokens
- latency
- cost
- final decision

Do not store or expose hidden chain-of-thought.

---

# Experiment 21 — Workflow vs agent on the genuine dynamic subset

## Question
Does the agent earn its extra complexity?

## Compare
Same dynamic cases:

A. fixed workflow  
B. bounded agent

## Primary comparison
- Correct Disposition Rate
- false approvals
- Human Review Rate
- latency
- cost

## Supporting metrics
- wrong tool rate
- unnecessary calls
- turns
- step-cap hits

## Repeatability
Run stochastic cases 3 times where feasible.

Report raw trial counts and mean/SD where applicable.

## Decision rule
If agent does not materially improve outcomes, final production architecture should use workflow.

---

# Experiment 22 — Minimum tool set vs kitchen-sink tool set

## Question
Does giving the agent more tools improve capability or create confusion?

## Compare
A. minimum necessary tool set  
B. expanded tool set

## Metrics
- task success
- wrong-tool rate
- unnecessary calls
- prompt tokens
- latency
- cost

Prefer the smallest tool set that preserves success.

---

# Experiment 23 — Tool-description quality

## Question
How much do discriminative tool descriptions matter?

## Compare
A. deliberately vague/overlapping descriptions  
B. precise descriptions that explain when each tool is appropriate

## Metrics
- wrong-tool rate
- disposition accuracy
- turns
- cost

This can also serve as one reproduced failure.

---

# Experiment 24 — Single-tool ablation

## Question
Which tools are actually necessary?

Remove one relevant tool from the agent at a time on the dynamic subset.

Record:
- outcome change
- whether agent asks/escalates appropriately
- wrong substitution behavior

Do not run every possible ablation if it adds little value. Focus on 2–3 meaningful tools.

---

# Experiment 25 — Sequential vs dependency-aware parallel calls

## Question
Can independent lookups be parallelized safely?

Only parallelize calls with no dependency.

Example:
- employee profile and project status may be independent.
- conference lookup cannot occur before discovering an event ID.

## Compare
- sequential
- dependency-aware parallel

## Metrics
- success
- latency
- tool calls
- cost

The goal is lower latency without changing semantics.

---

# Experiment 26 — Agent failure reproduction A: loop / duplicate calls

## Failure
Disable action de-duplication or loop memory.

## Measure before/after
- turns
- repeated calls
- tokens
- cost
- success rate
- step-cap hits

## Restore
- action dedupe
- step cap
- budget cap

The cap must be justified from observed legitimate turn distribution rather than chosen arbitrarily.

---

# Experiment 27 — Agent failure reproduction B: ambiguous tools

## Failure
Use overlapping/vague tool descriptions.

## Measure
- wrong-tool rate
- task success
- turns
- latency
- cost

## Restore
Discriminative descriptions.

This is strong evidence that tool design is part of the system, not documentation polish.

---

# Experiment 28 — Guardrail suite

Run `04_ground_truth_PRIVATE/guardrail_cases.csv` separately from normal task evaluation.

## Required classes
- prompt injection in employee description
- fake CFO/executive authority
- malicious text in tool result
- duplicate action loop
- step-cap violation
- budget-cap violation
- malformed arguments
- unknown tool
- tool timeout
- attempt to access evaluator labels
- irreversible payment/write action attempt
- always-escalate negative control
- duplicate over-block negative control
- wrong-year policy
- conflicting evidence

## Report
Pass count / total by guardrail family.

Do not combine this into Correct Disposition Rate.

---

# Experiment 29 — Abstention / escalation behavior

## Question
Does the system know when evidence is insufficient?

Use evidence-based gates:
- missing required facts
- unresolved policy conflict
- failed tool
- contradictory evidence
- unsupported applicable policy

Avoid relying only on self-reported model confidence.

## Measure
- abstention/escalation rate
- error rate among non-abstained cases
- fraction of would-be errors captured by abstention
- over-escalation rate

The system must not achieve safety by escalating everything.

---

# Experiment 30 — Selective architecture router

## Goal
Build the final candidate system that chooses the cheapest sufficient path.

Possible routing:

```text
claim
  ↓
deterministic validation/rules
  ↓
self-contained?
  ├── yes → hybrid RAG + rules
  └── no
        ↓
predictable external evidence path?
  ├── yes → fixed workflow
  └── no → bounded agent (only if justified)
```

## Compare
A. agent for every case  
B. fixed workflow for every external-evidence case  
C. selective architecture

## Metrics
- Correct Disposition Rate
- false approvals
- Human Review Rate
- latency
- cost
- percentage of cases invoking agent

A likely strong finding is that agentic execution is necessary for only a small minority — or not at all.

---

# Experiment 31 — Cost-to-serve

Use only measured AI/system numbers for:
- input tokens
- output tokens
- model calls
- embedding/retrieval calls
- tool calls
- latency
- model/API cost
- Human Review Rate

Then model three layers:

## Layer 1 — Variable AI cost

```text
AI cost per claim
```

## Layer 2 — Expected human fallback

```text
Human Review Rate × assumed manual-review cost
```

Clearly label manual minutes/hourly rates as assumptions.

## Layer 3 — Fixed monthly cost
Optionally model:
- storage
- monitoring
- evaluation runs
- hosting

Run sensitivity at illustrative volumes such as:
- 1,000 claims/month
- 10,000
- 100,000

Do not claim real savings unless measured in a real deployment.

---

# Experiment 32 — Frozen final evaluation

This is the only final headline evaluation.

## Before running
Freeze:
- prompts
- retrieval configuration
- model version
- workflow
- agent settings
- router thresholds
- tool descriptions
- guardrails

No tuning after inspecting final-test errors.

## Run
40 frozen final-test cases.

## Report per final architecture
- correct / 40
- Correct Disposition Rate
- 95% Wilson CI
- false approvals / non-approvable cases
- Human Review Rate
- median latency
- P95 latency
- average cost per case

## Also report
Performance on the 10 independent challenge cases separately.

For stochastic dynamic cases, repeat where budget permits, but do not use those repeats to tune final architecture.

---

# Experiment 33 — Final failure analysis

Manually classify each final-test failure into one primary bucket:

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

Do not silently fix final-test errors and rerun them as if they were unseen.

---

# 9. Recommended execution order

Run the experiments in this order:

```text
0  Dataset validation
1  Smallest end-to-end slice
2  Deterministic rules
3  LLM without policy
4  Full-policy long context
5  Naive RAG
6  Chunking
7  Top-K
8  BM25 vs dense vs hybrid
9  Metadata filtering
10 Conditional query rewrite/rerank
11 Policy oracle
12 Hybrid RAG + deterministic rules
13 Missing-information evaluation
14 Duplicate detection
15 Split-transaction detection
16 Enterprise evidence oracle
17 Typed enterprise tools
18 Fixed workflow
19 Agent-necessity audit
20 Bounded agent (only if justified)
21 Workflow vs agent
22 Tool-set size
23 Tool descriptions
24 Tool ablation
25 Sequential vs parallel
26 Loop failure reproduction
27 Tool-confusion failure reproduction
28 Guardrails
29 Abstention/escalation
30 Selective router
31 Cost-to-serve
32 Frozen final evaluation
33 Final failure analysis
```

Do not skip Experiments 2, 4, 11, 16, 18, or 19. Those are the experiments that make the architectural argument credible.

---

# 10. Results files

For every experiment create:

```text
results/expXX_<name>/
├── predictions.jsonl
├── metrics.json
├── run_config.json
├── failures.csv
└── notes.md
```

`run_config.json` must record:
- model name/version
- temperature
- prompt version
- retrieval configuration
- top-k
- embedding model
- tool set
- git commit
- timestamp
- dataset split

This is critical for reproducibility.

---

# 11. Plots/tables to produce for the final report

Keep the report focused.

## Main-table 1 — Architecture ladder

Columns:
- architecture
- correct/N
- Correct Disposition Rate
- false approvals
- Human Review Rate
- median latency
- cost/claim

Rows:
- rules
- generic LLM
- long context
- optimized RAG
- hybrid RAG+rules
- workflow
- agent if justified
- selective final system

## Main-chart 1 — Accuracy vs cost
X = cost per claim  
Y = Correct Disposition Rate

## Main-chart 2 — Accuracy vs Human Review Rate
Shows whether automation comes from better decisions or from unsafe auto-approval.

## Main-table 2 — Retrieval ablation
- naive dense
- hybrid
- metadata-aware
- optional reranker

## Main-table 3 — Workflow vs agent dynamic subset
Only if agent survives the gate.

## Main-chart 3 — Failure taxonomy
Counts by primary failure reason.

## Appendix
- missing-field metrics
- duplicate metrics
- split metrics
- tool metrics
- guardrail suite
- seed/repeat statistics

---

# 12. Product-impact story for the final report

The final narrative should be:

1. Manual expense review is costly because clean and ambiguous claims enter the same review queue.
2. ExpenseGuard tries to determine whether each claim is ready for reimbursement.
3. A simple rules baseline is tested first.
4. A generic LLM is insufficient because it does not know company policy.
5. Long context tests whether retrieval is necessary at all.
6. RAG is introduced only if it materially improves grounding/cost/scalability.
7. Deterministic code owns arithmetic, exact thresholds, FX, and exact duplicate checks.
8. Missing-information handling reduces unnecessary back-and-forth.
9. Duplicate and split-transaction checks show why historical enterprise evidence matters.
10. Fixed workflows handle predictable cross-system checks.
11. Only evidence-dependent branching is considered agentic.
12. The agent is retained only if it beats workflow enough to justify additional cost and risk.
13. The final architecture routes each claim through the cheapest sufficient path.
14. The final success claim is about **correct disposition with controlled false approvals and reduced unnecessary human review**, not about “using an agent.”

---

# 13. What counts as a successful final finding?

Any of these can be a strong result:

### Finding A
RAG + rules solves almost everything; workflows add little.
That means the simpler system wins.

### Finding B
Workflow materially helps cross-system cases; agent adds nothing.
Then the production design should stop at workflow.

### Finding C
Agent materially improves a small dynamic subset.
Then use a selective router and invoke the agent only there.

### Finding D
Long-context matches RAG at this corpus size.
Then report that RAG is unnecessary at current scale, while discussing when scaling might change the decision.

The project is judged by the quality of the evidence and trade-off reasoning, not by whether the most complex architecture wins.

---

# 14. Definition of done

The project is complete when:

- [ ] dataset validator passes
- [ ] all baseline experiments are reproducible
- [ ] final policy/retrieval configuration is frozen
- [ ] duplicate/split checks are evaluated against negative controls
- [ ] workflow baseline is complete
- [ ] agent necessity is tested rather than assumed
- [ ] guardrail suite is run
- [ ] final router is frozen
- [ ] cost/latency are measured
- [ ] final test is run once after freeze
- [ ] raw counts + confidence intervals are reported
- [ ] independent challenge subset is reported separately
- [ ] failures are categorized
- [ ] all assumptions are labeled as assumptions
- [ ] no fraud/intent claims are made
- [ ] no evaluator/private ground truth leaks into runtime
- [ ] repository runs from README on a clean machine

---

# 15. First instruction to the Visual Studio coding agent

Start with this exact sequence:

```text
1. Read this file completely.
2. Read DATASET_CARD.md and README.md.
3. Run 05_generation/validate_dataset.py.
4. Do not inspect or index 04_ground_truth_PRIVATE except inside evaluator code.
5. Build Experiment 1 only.
6. Show me the Experiment 1 implementation and results before beginning Experiment 2.
7. Continue one experiment at a time. Do not jump directly to RAG or an agent.
```

This project should be developed as an evidence-driven architecture study around one product problem: **safe, low-friction expense-claim resolution**.
