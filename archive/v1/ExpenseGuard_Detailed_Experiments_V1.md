> **LEGACY V1 — superseded by ExpenseGuard V2. Retained only for historical experiment evidence.**
> This plan describes the original 120-claim (60 development / 20 validation / 40 final test) V1 dataset
> and experiment sequence. The current project uses the 150-claim V2 dataset (70/30/50) described in
> [`problem.md`](../../problem.md) and [`docs/v2/README.md`](../../docs/v2/README.md); V1's own final
> result (Exp 30/32 for that dataset generation) is a chronological predecessor to V2's Exp 30/32, not the
> current official result. Do not cite numbers from this file as current performance.

# ExpenseGuard — Detailed Experiment Plan (V1)

**Project:** PE6201 Emerging AI Technologies — End-of-Course Project  
**System:** ExpenseGuard  
**Purpose:** Evidence-driven evaluation of rules, LLMs, RAG, workflows, and agents for enterprise expense-claim resolution.

---

## Project goal

ExpenseGuard determines whether an employee expense claim is **ready for reimbursement**.

For each claim, the system must return exactly one of:

- `APPROVE`
- `REJECT`
- `REQUEST_INFORMATION`
- `ESCALATE`

The project does **not** assume that the most complex architecture is the best one. The aim is to determine the **cheapest sufficient architecture** for each class of expense case.

The architecture ladder is:

```text
Deterministic rules
→ Generic LLM
→ Full-policy long context
→ Naive RAG
→ Optimized RAG
→ Hybrid RAG + deterministic rules
→ Fixed enterprise workflow
→ Bounded agent only if genuinely required
→ Selective router
```

The key research question is:

> **When are rules sufficient, when is RAG sufficient, when is a fixed workflow required, and when — if ever — does agentic investigation justify its additional cost, latency, and risk?**

---

# Phase A — Validate the data and simple baselines

## Experiment 0 — Dataset integrity and leakage audit

### Question
Is the benchmark trustworthy before any model or retrieval experiment is run?

### Steps
1. Validate that all 120 cases have unique IDs.
2. Verify the split:
   - 60 development
   - 20 validation
   - 40 final test
3. Verify the architecture groups:
   - 65 self-contained / RAG-solvable
   - 40 fixed-workflow
   - 15 agent-candidate
4. Verify that every policy ID referenced by private ground truth exists in the policy corpus.
5. Verify that every enterprise-data reference points to a valid record.
6. Verify all duplicate-expense links.
7. Verify all split-transaction relationships.
8. Verify that the 10 challenge cases remain isolated in final test.
9. Check that private ground-truth fields are absent from:
   - model-visible cases
   - policy documents
   - enterprise tool outputs
   - retrieval metadata
10. Run the packaged dataset validator.

### Output
`results/exp00_dataset_validation.json`

### Pass condition
Zero critical dataset-integrity or leakage errors.

### Stop gate
If this experiment fails, stop and repair the dataset before continuing.

---

## Experiment 1 — Smallest end-to-end feasibility slice

### Question
Can one claim travel through the complete system and produce a valid structured output?

### Dataset
Use only 10 development cases.

### Architecture
No retrieval, no workflow, no agent.

Provide the relevant policy text directly to the model.

### Steps
1. Load structured bill details.
2. Load employee free-text description.
3. Provide the relevant policy section manually.
4. Call one foundation model.
5. Require structured output.
6. Compare with frozen ground truth.

### Required output schema

```json
{
  "decision": "APPROVE",
  "policy_evidence": ["POLICY-ID"],
  "missing_fields": [],
  "explanation": "..."
}
```

### Measure
- Correct Disposition Rate
- schema-valid output rate
- latency
- failures

### Goal
Engineering feasibility, not headline performance.

---

## Experiment 2 — Deterministic rules baseline

### Question
How much of expense compliance can ordinary deterministic code solve?

### Implement deterministic checks for
- required fields
- fixed date windows
- numeric thresholds
- percentages and tips
- frozen FX conversion
- exact duplicate bill number
- exact merchant + amount + date duplicate
- fixed approval thresholds
- simple prohibited categories
- deterministic totals and comparisons

### Example

```text
Claim amount = SGD 620
Approval threshold = SGD 500
Manager approval absent

→ REQUEST_INFORMATION or ESCALATE
```

### Dataset
All development cases.

### Measure
- correct / N
- Correct Disposition Rate
- False Approval Rate
- Human Review Rate
- latency
- cost

### Why this matters
This is the true non-AI baseline. Later systems must beat or complement it.

---

# Phase B — Establish why grounding is needed

## Experiment 3 — Generic LLM without company policy

### Question
Can a generic foundation model make reliable expense decisions without company-specific policy grounding?

### Input
- claim only

### Do not provide
- company policy
- enterprise tools
- private ground truth

### Hypothesis
The model may produce convincing but unsupported policy assumptions.

### Measure
- Correct Disposition Rate
- False Approval Rate
- unsupported-policy assertion rate
- cost
- latency

### Expected learning
This experiment demonstrates whether policy grounding is required.

---

## Experiment 4 — Full-policy long-context baseline

### Question
If the complete policy corpus fits into context, is RAG necessary at all?

### Input
- claim
- complete relevant policy corpus

### Important
Run this before any optimized RAG work.

### Dataset
Development + validation.

### Measure
- Correct Disposition Rate
- False Approval Rate
- wrong-policy-version errors
- input tokens
- output tokens
- latency
- cost

### Decision gate
RAG must later demonstrate at least one of:
- higher accuracy
- lower false-approval rate
- better policy-version precision
- lower token cost
- lower latency
- better scalability
- stronger evidence traceability

If it does not, long context may be the better design.

---

# Phase C — Build and understand RAG

## Experiment 5 — Naive RAG baseline

### Question
How well does the simplest possible retrieval system perform?

### Retrieval design
- dense embeddings
- fixed chunking
- top-k = 3
- raw claim-derived query
- no metadata filtering
- no reranker
- no query rewriting

### Pipeline

```text
Claim
↓
Embedding query
↓
Retrieve top 3 chunks
↓
LLM
↓
Disposition
```

### Retrieval metrics
- Recall@3
- Precision@3
- MRR
- required-policy coverage

### Downstream metrics
- Correct Disposition Rate
- False Approval Rate
- latency
- cost

### Logging
Save all retrieved chunks and retrieval scores for failure analysis.

---

## Experiment 6 — Chunk size and overlap

### Question
Are retrieval failures caused by poor chunk boundaries?

### Compare
A small controlled set such as:

```text
300 tokens / 50 overlap
600 tokens / 100 overlap
900 tokens / 150 overlap
```

### Focus cases
- cross-document evidence
- exception clauses
- appendix references
- policy text split across paragraphs

### Measure
- Recall@K
- Precision@K
- MRR
- downstream Correct Disposition Rate
- prompt tokens
- cost

### Decision
Select one chunking configuration for future experiments.

Do not run a huge hyperparameter grid.

---

## Experiment 7 — Top-K retrieval sensitivity

### Question
How many retrieved chunks should enter the reasoner?

### Compare
- K = 1
- K = 3
- K = 5
- optionally K = 8 only if evidence is still being missed

### Trade-off

```text
Higher K
→ potentially higher recall
→ more distractors
→ more prompt tokens
→ more cost
```

### Measure
- Recall@K
- Precision@K
- Correct Disposition Rate
- false approvals
- context tokens
- latency
- cost

---

## Experiment 8 — BM25 vs dense vs hybrid retrieval

### Question
Which retrieval family works best for the policy corpus?

### Compare
- BM25
- dense embeddings
- hybrid BM25 + dense

### Focus cases
- exact policy terminology
- semantic paraphrases
- similarly worded distractors
- cross-document cases

### Measure
- Recall@K
- Precision@K
- MRR
- nDCG
- required-evidence coverage
- Correct Disposition Rate

### Decision
Select the best retrieval family for later experiments.

---

## Experiment 9 — Metadata-aware retrieval

### Question
Can metadata prevent wrong-year and wrong-region policy retrieval?

### Metadata
Use:
- effective date/year
- region
- policy category
- document type

### Compare
Best retriever:
1. without metadata filters
2. with metadata filters

### Example

```text
Transaction date = August 2025
Country = Japan

Avoid retrieving:
- 2026 policy
- Singapore addendum
```

### Measure
- correct-policy-version rate
- regional-precedence accuracy
- Recall@K
- MRR
- Correct Disposition Rate
- false approvals

### Why this matters
Confident use of a superseded policy is a major silent failure.

---

## Experiment 10 — Query rewriting / reranking

### Run only if earlier experiments justify it

Do not add these automatically.

### Case A — Vocabulary mismatch
If relevant policy language is semantically different from employee wording, test query rewriting.

Example:

```text
Employee:
"customer dinner after workshop"

Rewritten:
"client entertainment meal attendee policy"
```

### Case B — Correct evidence ranks too low
If Recall@K is high but ordering is poor, test reranking.

### Compare
Before vs after:
- Recall@K
- MRR
- nDCG
- Correct Disposition Rate
- latency
- cost

### Decision
If gain is negligible, remove the component.

---

## Experiment 11 — Policy oracle

### Question
How much failure comes from retrieval versus reasoning?

### Method
Evaluator code supplies the exact required policy clauses.

This is evaluation-only and must never appear in normal runtime.

### Compare
- optimized RAG
- policy oracle

### Interpretation

If:

```text
Oracle >> RAG
```

then retrieval is the bottleneck.

If:

```text
Oracle ≈ RAG but both fail
```

then reasoning or policy application is the bottleneck.

### Importance
This is one of the strongest failure-decomposition experiments in the project.

---

# Phase D — Build the hybrid compliance engine

## Experiment 12 — RAG + deterministic compliance logic

### Question
Should arithmetic and exact policy checks remain inside the LLM?

### Move into deterministic code
- amount comparisons
- per-attendee calculations
- percentages and tips
- date windows
- FX conversion
- exact duplicate checks
- fixed approval thresholds

### Leave to the model
- semantic category interpretation
- policy applicability
- ambiguous evidence interpretation
- explanation

### Compare
1. LLM/RAG decides everything
2. RAG + deterministic evaluator

### Measure
- Correct Disposition Rate
- False Approval Rate
- arithmetic-error count
- latency
- cost

### Expected finding
Hybrid should be more reliable and easier to audit.

---

## Experiment 13 — Missing-information detection

### Question
Can the system ask for exactly what is missing rather than generically escalating?

### Dataset
20 missing-information cases plus negative controls.

### Example

Policy requires:
- external attendee names
- business purpose
- project ID

Case contains:
- business purpose
- project ID

Correct result:

```text
REQUEST_INFORMATION

Missing:
external_attendee_names
```

### Measure
- correct `REQUEST_INFORMATION` disposition
- missing-field precision
- missing-field recall
- unnecessary-field request rate

### Product requirement
Avoid vague output such as:

> “Please provide more information.”

Prefer:

> “Provide the names and organisations of the external attendees.”

---

# Phase E — Historical-expense intelligence

## Experiment 14 — Duplicate expense detection

### Question
Can ExpenseGuard identify duplicate claims without falsely blocking legitimate repeat expenses?

### Tool
`search_previous_expenses(...)`

### Classes
- `EXACT_DUPLICATE`
- `POSSIBLE_DUPLICATE`
- `LEGITIMATE_REPEAT`
- `NONE`

### Compare three approaches

#### A. Exact deterministic match
Examples:
- same bill number
- same employee + merchant + date + amount

#### B. Fuzzy deterministic candidate generation
Possible features:
- merchant similarity
- date window
- amount tolerance
- same employee/project

#### C. Model-assisted adjudication
Use only for ambiguous candidates.

### Measure
- duplicate precision
- duplicate recall
- duplicate false-positive rate
- false blocking of legitimate repeats
- Correct Disposition Rate

### Safety
Never label the employee as committing fraud.

This is claim-level compliance checking only.

---

## Experiment 15 — Split-transaction detection

### Question
Can the system identify related transactions whose combined amount changes an approval requirement?

### Example

```text
Current claim = SGD 290
Previous related claim = SGD 280
Approval threshold = SGD 500

Combined = SGD 570
```

### Steps
1. Search previous expenses.
2. Identify related transactions.
3. Combine amounts deterministically.
4. Retrieve the relevant approval policy.
5. Check approval evidence.
6. Produce disposition.

### Measure
- related-transaction retrieval accuracy
- split-transaction precision
- split-transaction recall
- combined-amount correctness
- triggered-policy correctness
- Correct Disposition Rate

### Negative controls
Include similar transactions that are genuinely separate.

---

# Phase F — Introduce enterprise evidence

## Experiment 16 — Enterprise-evidence oracle

### Question
If the exact required external facts are supplied, can the reasoning system solve the case?

### Example oracle facts

```text
employee_grade = G5
travel_approved = true
conference_registered = true
official_hotel = true
```

### Compare
- normal system
- enterprise-evidence oracle

### Interpretation

If oracle succeeds but normal tool execution fails:

> tool retrieval/orchestration is the bottleneck.

If oracle also fails:

> policy reasoning/application is the bottleneck.

---

## Experiment 17 — Build typed enterprise tools

### Build these read-only tools

```text
get_employee_profile()
get_travel_request()
get_manager_approval()
get_exception_record()
get_project_status()
search_previous_expenses()
get_conference_registration()
get_merchant_metadata()
```

### Tool requirements
- strict typed parameters
- compact JSON return values
- read-only
- clear empty/not-found states
- discriminative descriptions
- no private ground-truth leakage

### Before LLM orchestration
Unit test:
- valid arguments
- invalid identifiers
- missing records
- malformed arguments
- timeouts
- empty results
- response schema

The tool layer should be reliable before workflow or agent experiments.

---

# Phase G — Test whether workflow is sufficient

## Experiment 18 — Fixed workflow baseline

### Question
How many external-evidence cases can a predictable workflow solve?

### Example flow

```text
Hotel claim
↓
Retrieve hotel policy
↓
Get employee grade
↓
Get travel approval
↓
Evaluate threshold
↓
Disposition
```

Duplicate example:

```text
Possible duplicate
↓
Search previous expenses
↓
Exact/fuzzy comparison
↓
Disposition
```

### Run on
- all 40 workflow cases
- all 15 agent-candidate cases

### Measure
- Correct Disposition Rate
- False Approval Rate
- Human Review Rate
- tool calls
- latency
- cost

### Importance
This is the main agent-feasibility gate.

---

## Experiment 19 — Agent-necessity audit

### Question
Do any cases genuinely require runtime model-directed tool sequencing?

For each of the 15 agent-candidate cases ask:

1. Can the path be decided before execution?
2. Does the first tool result change which tool is needed next?
3. Could a reasonable finite `if/else` workflow handle the class of case?
4. Does dynamic sequencing solve a real problem rather than add sophistication?

### Example of genuine dynamic behavior

```text
check travel request
↓
Result contains conference_id
↓
Now conference lookup becomes relevant
```

Versus:

```text
check travel request
↓
Result contains exception_id
↓
Now exception-record lookup becomes relevant
```

### Decision
Only cases surviving this audit should be treated as genuinely agentic.

If workflow handles them cleanly, the correct conclusion is:

> An agent is not required.

---

# Phase H — Agent experiments

## Experiment 20 — Bounded single agent

### Run only if Experiment 19 justifies it

### Architecture
One bounded ReAct-style agent.

Do not use a multi-agent design.

### Agent loop

```text
Case
↓
Determine evidence needed
↓
Tool call
↓
Observation
↓
Decide next action
↓
...
↓
Final disposition
```

### Required guardrails
- max-step cap
- token/cost budget
- action de-duplication
- typed tool schemas
- read-only tools
- explicit `REQUEST_INFORMATION`
- explicit `ESCALATE`
- stop when evidence is sufficient

### Log
- tool name
- tool arguments
- observation
- state summary
- turns
- tokens
- latency
- cost
- final decision

Do not expose hidden chain-of-thought.

---

## Experiment 21 — Workflow vs agent

### Question
Does the agent justify its extra complexity?

### Dataset
Same genuine dynamic cases for both systems.

### Compare

| Metric | Workflow | Agent |
|---|---:|---:|
| Correct/N |  |  |
| Correct Disposition Rate |  |  |
| False approvals |  |  |
| Human Review Rate |  |  |
| Average tool calls |  |  |
| Latency |  |  |
| Cost |  |  |

### Repetition
Run stochastic cases around 3 times where practical.

Report:
- raw trial count
- mean
- standard deviation

### Decision
If agent performance is not materially better, do not use the agent in the final architecture.

---

# Phase I — Tool-design experiments

## Experiment 22 — Minimum tool set vs kitchen-sink tool set

### Question
Does exposing more tools improve the agent or create confusion?

### Compare

#### Minimal tool set
Only tools required for the case family.

#### Expanded tool set
Expose many enterprise tools simultaneously.

### Measure
- task success
- wrong-tool rate
- unnecessary tool calls
- prompt tokens
- latency
- cost

### Expected insight
A smaller tool set may be more reliable.

---

## Experiment 23 — Tool-description quality

### Question
How much do tool descriptions affect agent reliability?

### Weak version

```text
Tool A: gets records
Tool B: checks records
```

### Strong version

```text
get_exception_record:
Retrieve an already-approved policy exception by exception_id.
Do not use this tool for ordinary manager approvals.
```

### Measure
- wrong-tool rate
- success rate
- turns
- latency
- cost

This can serve as one reproduced agent failure.

---

## Experiment 24 — Single-tool ablation

### Question
Which tools are actually necessary?

Remove one relevant tool at a time.

Example:

```text
Remove get_conference_registration()
```

Observe whether the agent:
- requests information
- escalates correctly
- hallucinates
- substitutes another tool incorrectly

### Scope
Run only 2–3 meaningful ablations.

Do not exhaustively remove every tool.

---

## Experiment 25 — Sequential vs dependency-aware parallel calls

### Question
Can independent lookups run in parallel without changing semantics?

### Parallel-safe example

```text
get_employee_profile()
+
get_project_status()
```

### Not parallel-safe

```text
get_conference_registration(event_id)
```

when `event_id` must first be discovered from a travel record.

### Compare
- sequential execution
- dependency-aware parallel execution

### Measure
- success
- latency
- tool calls
- cost

---

# Phase J — Reproduce agent failures

## Experiment 26 — Agent loop / duplicate-call failure

### Failure setup
Temporarily disable action de-duplication or loop memory.

### Observe

```text
get_travel_request()
get_travel_request()
get_travel_request()
```

### Measure before/after
- turns
- repeated calls
- tokens
- cost
- success
- step-cap hits

### Restore
- action de-duplication
- step cap
- budget cap

### Important
Choose the step cap from observed legitimate turn distribution, not arbitrarily.

---

## Experiment 27 — Tool-confusion failure

### Failure setup
Use vague, overlapping tool descriptions.

Example:

```text
get_approval()
get_exception()
get_authorization()
```

### Measure
- wrong-tool rate
- task success
- turns
- latency
- cost

### Restore
Discriminative tool descriptions.

Show before/after results.

---

# Phase K — Safety and responsible deployment

## Experiment 28 — Guardrail suite

### Keep separate from normal task evaluation

Test:
- prompt injection in employee description
- fake CFO/executive authority
- malicious text in tool result
- attempt to access private labels
- unknown tool
- malformed arguments
- duplicate-action loop
- budget-cap violation
- step-cap violation
- tool timeout
- attempted payment/write action
- wrong-year policy
- conflicting evidence
- always-escalate negative control
- aggressive duplicate blocking

### Report
Pass count / total by guardrail category.

Do not combine guardrail score with Correct Disposition Rate.

---

## Experiment 29 — Abstention and escalation behavior

### Question
Does the system know when it lacks enough evidence?

### Trigger abstention/escalation for
- missing required facts
- unresolved policy conflict
- failed tool
- contradictory evidence
- unsupported policy
- unresolved version/region conflict

### Measure
- abstention/escalation rate
- error rate among auto-resolved cases
- percentage of would-be errors captured by abstention
- unnecessary escalation rate

### Important
A system that escalates 100% of claims is safe but useless.

Always pair this metric with Human Review Rate.

---

# Phase L — Final architecture

## Experiment 30 — Selective architecture router

### Goal
Route each claim through the cheapest sufficient path.

### Candidate architecture

```text
Claim
↓
Deterministic validation/rules
↓
Can hybrid RAG + rules solve it?
 ├─ yes → resolve
 └─ no
      ↓
Is the external-evidence path predictable?
 ├─ yes → fixed workflow
 └─ no → bounded agent
```

### Compare three strategies
1. Agent for everything
2. Workflow for all external-evidence cases
3. Selective architecture

### Measure
- Correct Disposition Rate
- False Approval Rate
- Human Review Rate
- latency
- cost
- percentage of cases invoking agent

### Likely useful finding
Agentic execution may be required for only a small minority of cases — or none.

---

## Experiment 31 — Cost-to-serve

### Measure actual system quantities
- input tokens
- output tokens
- model calls
- embedding calls
- tool calls
- latency
- model/API cost
- Human Review Rate

### Layer 1 — Variable AI/system cost

```text
AI cost per claim
```

### Layer 2 — Expected human fallback

```text
Human Review Rate × assumed manual-review cost
```

Manual review time and hourly cost must be clearly labeled as assumptions.

### Layer 3 — Fixed monthly costs
Optionally model:
- hosting
- storage
- monitoring
- evaluation runs

### Illustrative scales
- 1,000 claims/month
- 10,000 claims/month
- 100,000 claims/month

### Important
Do not call modelled business savings “measured savings.”

---

# Phase M — Freeze and evaluate

## Experiment 32 — Frozen final test

### Before running
Freeze:
- prompts
- model version
- temperature
- retrieval configuration
- chunk size
- top-k
- metadata filters
- tool descriptions
- workflow logic
- agent settings
- router
- guardrails

No tuning after inspecting final-test errors.

### Dataset
40 frozen final-test cases.

### Report
- Correct: X / 40
- Correct Disposition Rate
- 95% Wilson confidence interval
- False approvals: X / N non-approvable cases
- Human Review Rate
- median latency
- P95 latency
- average cost per case

### Challenge set
Report the 10 independently worded/reviewed challenge cases separately.

### Stochastic runs
Repeat dynamic/stochastic cases where budget permits, but do not tune based on these repeats.

---

## Experiment 33 — Final failure analysis

### For each final-test failure assign one primary category

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

### Output
Create a final failure-count table and plot.

### Reporting example

Instead of only:

> “Accuracy was 90%.”

Report:

> “Four failures remained: two wrong-policy-version retrieval errors, one duplicate false positive, and one evidence-conflict reasoning error.”

This gives the final project a much stronger evaluation story.

---

# Complete execution order

Run experiments in this exact sequence:

```text
0  Dataset validation
1  Smallest end-to-end slice
2  Deterministic rules baseline
3  Generic LLM without policy
4  Full-policy long context
5  Naive RAG
6  Chunk-size experiment
7  Top-K experiment
8  BM25 vs dense vs hybrid
9  Metadata-aware retrieval
10 Query rewrite / reranker only if justified
11 Policy oracle
12 Hybrid RAG + deterministic rules
13 Missing-information evaluation
14 Duplicate detection
15 Split-transaction detection
16 Enterprise-evidence oracle
17 Enterprise tools
18 Fixed workflow
19 Agent-necessity audit
20 Bounded agent only if justified
21 Workflow vs agent
22 Minimum vs expanded tool set
23 Tool-description experiment
24 Tool ablation
25 Sequential vs parallel
26 Loop-failure reproduction
27 Tool-confusion failure reproduction
28 Guardrails
29 Abstention / escalation
30 Selective architecture router
31 Cost-to-serve
32 Frozen final test
33 Final failure analysis
```

---

# Full project flow

```text
DATASET
  │
  ├─ Exp 0  Validate data
  │
  ├─ Exp 1  End-to-end feasibility
  │
  ├─ Exp 2  Rules baseline
  │
  ├─ Exp 3  Generic LLM
  │
  ├─ Exp 4  Long context
  │
  ├─ Exp 5  Naive RAG
  │
  ├─ Exp 6  Chunking
  │
  ├─ Exp 7  Top-K
  │
  ├─ Exp 8  BM25/dense/hybrid
  │
  ├─ Exp 9  Metadata filtering
  │
  ├─ Exp 10 Rewrite/rerank if needed
  │
  ├─ Exp 11 Policy oracle
  │
  ├─ Exp 12 Hybrid RAG + rules
  │
  ├─ Exp 13 Missing information
  │
  ├─ Exp 14 Duplicate detection
  │
  ├─ Exp 15 Split transactions
  │
  ├─ Exp 16 Enterprise oracle
  │
  ├─ Exp 17 Build tools
  │
  ├─ Exp 18 Fixed workflow
  │
  ├─ Exp 19 Do we need an agent?
  │
  ├──── NO ───────────────→ keep workflow
  │
  └──── YES
       │
       ├─ Exp 20 Agent
       ├─ Exp 21 Workflow vs agent
       ├─ Exp 22 Tool set
       ├─ Exp 23 Tool descriptions
       ├─ Exp 24 Tool ablation
       ├─ Exp 25 Parallel calls
       ├─ Exp 26 Loop failure
       └─ Exp 27 Tool confusion
              │
              ↓
       Exp 28 Guardrails
              ↓
       Exp 29 Abstention
              ↓
       Exp 30 Selective router
              ↓
       Exp 31 Cost-to-serve
              ↓
       Exp 32 FINAL TEST
              ↓
       Exp 33 Failure analysis
```

---

# Core metrics

## Primary metric

### Correct Disposition Rate

```text
correct final dispositions / total evaluated claims
```

Report:
- raw count
- percentage
- 95% Wilson confidence interval

---

## Safety/business guardrails

### False Approval Rate

```text
incorrect APPROVE / non-approvable cases
```

### Human Review Rate

```text
claims requiring actual finance-review intervention / total claims
```

### Latency
Report:
- median
- P95

### Cost
Report actual:
- model tokens
- model calls
- retrieval calls
- tool calls
- API/model cost per case

---

# Diagnostic metrics

Use only where relevant:

- macro precision
- macro recall
- macro F1
- Recall@K
- Precision@K
- MRR
- nDCG
- correct-policy-version rate
- required-evidence coverage
- missing-field precision
- missing-field recall
- duplicate precision
- duplicate recall
- duplicate false-block rate
- split-transaction precision
- split-transaction recall
- wrong-tool rate
- unnecessary tool-call rate
- average turns
- step-cap hits
- unsupported-decision rate

These support diagnosis. They do not replace the primary metric.

---

# Final architecture decision rule

The project should not be judged by whether an agent exists.

Possible valid conclusions include:

## Outcome A
Rules + RAG solve almost everything.

**Conclusion:** stop there.

## Outcome B
Fixed workflow solves enterprise-evidence cases and agent adds no material gain.

**Conclusion:** workflow is the right architecture.

## Outcome C
Agent materially improves only a small dynamic subset.

**Conclusion:** use selective routing and invoke the agent only there.

## Outcome D
Long context matches RAG at this corpus size.

**Conclusion:** RAG is not justified at the current policy scale.

Any of these is a strong project result if supported by measured evidence.

---

# Final development instruction

Implement the project one experiment at a time.

For each experiment:

1. State the hypothesis.
2. Freeze the configuration.
3. Run only the required split.
4. Save machine-readable predictions.
5. Save metrics.
6. Record latency and cost.
7. Record failures.
8. Decide whether the next architectural layer is justified.
9. Do not begin the next experiment until the current result is understood.

The project should tell one consistent story:

> **ExpenseGuard safely resolves as many expense claims as possible using the cheapest reliable architecture, while controlling false approvals, unnecessary finance review, latency, and cost.**
