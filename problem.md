# ExpenseGuard — Problem Definition, Design Decisions, Scope, and Architecture

**Project:** PE6201 Emerging AI Technologies — End-of-Course Project  
**System name:** ExpenseGuard  
**Domain:** Enterprise expense management / finance operations  
**Primary user:** Corporate finance expense reviewer  
**Secondary beneficiary:** Employee submitting an expense claim  

---

# 1. Problem statement

Employees and finance teams lose significant time and money to expense-reimbursement processes that are slow, error-prone, and opaque.

Routine claims, incomplete claims, policy exceptions, duplicate submissions, split transactions, and genuinely ambiguous cases often enter the same manual review queue. Finance reviewers may need to inspect company policy, previous expense history, employee/travel records, approvals, exceptions, and other enterprise data before reaching a decision.

ExpenseGuard is designed to determine whether an expense claim is **ready for reimbursement** and, if not, identify exactly what prevents it from being safely resolved.

The system must return exactly one of:

- `APPROVE`
- `REJECT`
- `REQUEST_INFORMATION`
- `ESCALATE`

The product objective is:

> **Resolve routine claims safely and quickly, request exactly the missing evidence when a claim is incomplete, detect compliance issues such as duplicates or split transactions, and route only genuinely ambiguous or policy-mandated cases to a finance reviewer.**

---

# 2. Why the problem matters

Expense processing consumes both employee and finance-team time.

The project framing uses published industry estimates that manual expense processing can involve substantial per-report administrative cost and rework. The system is therefore not justified merely because AI can be applied; it is justified only if it can:

1. increase correct claim disposition;
2. reduce unnecessary finance review;
3. reduce avoidable back-and-forth;
4. avoid unsafe automatic approvals;
5. preserve explainability and auditability;
6. control cost and latency.

The project will not claim real operational savings unless they are directly measured in a production deployment.

Any modeled financial impact must clearly distinguish:

- **measured system quantities**, such as model cost, latency, token use, and Human Review Rate;
- **assumed business quantities**, such as analyst review minutes or labor cost.

---

# 3. Closest existing products and the gap

Existing enterprise expense platforms already automate important parts of expense compliance.

Examples include:

- SAP Concur / Concur Detect by Oversight
- Brex expense automation and policy-review capabilities
- Ramp expense and policy automation

The project does **not** claim that AI-based expense checking is new.

The narrower problem this project investigates is:

> **Whether dynamic cross-system evidence gathering adds measurable value when the correct next check depends on what a previous lookup reveals.**

The project therefore distinguishes:

- transaction-level policy checking;
- predictable enterprise lookups;
- genuinely dynamic evidence investigation.

This distinction is the basis for comparing RAG, workflow, and agentic execution.

---

# 4. Primary user and persona

## Primary user

A corporate finance expense reviewer.

### Persona

**Maya** is a finance operations analyst reviewing employee expense claims against company policy.

Before deciding a case, she may need to inspect:

- the submitted expense;
- travel records;
- approval records;
- policy exceptions;
- previous claims;
- project information;
- conference registration;
- merchant information.

### What changes if ExpenseGuard works

Maya should no longer spend time manually reviewing routine, fully evidenced claims.

Her attention should be concentrated on cases with:

- missing evidence;
- conflicting evidence;
- policy ambiguity;
- policy-mandated human review;
- unresolved duplicate/split concerns;
- high-risk uncertainty.

Employees are secondary beneficiaries because they receive:

- faster resolution;
- specific requests for missing information;
- evidence-backed reasons for rejection or escalation;
- fewer unexplained back-and-forth cycles.

---

# 5. Product definition

ExpenseGuard asks:

> **Is this expense claim ready for reimbursement?**

If not:

> **What exactly prevents it from being safely resolved?**

The system must be able to distinguish among:

1. clean compliant claim;
2. clear policy violation;
3. missing information;
4. exact duplicate;
5. possible/near duplicate;
6. legitimate repeat expense;
7. split transaction;
8. missing approval;
9. valid exception;
10. wrong policy version;
11. regional policy override;
12. conflicting evidence;
13. policy-mandated human review;
14. dynamic cross-system investigation.

---

# 6. In-scope capabilities

The final project scope includes:

1. policy compliance checking;
2. missing-information detection;
3. exact duplicate detection;
4. near-duplicate candidate detection;
5. legitimate repeat-expense discrimination;
6. split-transaction detection;
7. approval validation;
8. policy-exception validation;
9. temporal policy-version resolution;
10. regional policy precedence;
11. cross-document policy retrieval;
12. evidence-conflict handling;
13. read-only enterprise-data lookup;
14. fixed workflow execution;
15. bounded agentic investigation where justified;
16. abstention and escalation;
17. guardrails;
18. cost and latency analysis;
19. failure analysis;
20. selective routing to the cheapest sufficient architecture.

---

# 7. Explicitly out of scope

The following are not part of the project:

- fraud scoring;
- accusations of employee fraud;
- employee risk scoring;
- intent inference;
- character or honesty inference;
- OCR;
- receipt-image extraction;
- multimodal receipt processing;
- tax adjudication;
- legal adjudication;
- automatic reimbursement;
- payment execution;
- irreversible financial actions;
- disciplinary action;
- unrestricted autonomous agents;
- multi-agent systems;
- real employee or company data;
- email search unless a measured failure later proves it necessary.

Duplicate and split-transaction checks are framed as **claim-level compliance checks**, not fraud detection.

---

# 8. Core design principle

The project does **not** begin by assuming that an agent is required.

The central design principle is:

> **Use the simplest architecture that solves each case reliably.**

The architecture ladder is:

```text
Deterministic rules
→ Generic LLM
→ Full-policy long context
→ RAG
→ Hybrid RAG + deterministic rules
→ Fixed workflow
→ Bounded agent only if genuinely necessary
→ Selective router
```

Every added layer must demonstrate a measurable improvement that justifies:

- higher cost;
- higher latency;
- increased implementation complexity;
- additional failure modes.

---

# 9. Why AI is used

Not every part of the problem needs AI.

## Deterministic code is used for

- arithmetic;
- totals;
- thresholds;
- percentages;
- tips;
- date windows;
- frozen FX conversion;
- exact duplicate matching;
- fixed approval thresholds;
- known policy precedence where explicit;
- schema validation.

## Foundation models are used for

- interpreting free-text employee explanations;
- semantic policy matching;
- resolving language mismatch between claims and policy wording;
- identifying relevant policy categories;
- interpreting ambiguous evidence;
- producing evidence-backed explanations.

## RAG is used when

The correct decision must be grounded in enterprise policy documents not assumed to be known by the model.

## Workflows are used when

The required external evidence path is predictable before execution.

## An agent is used only when

An earlier tool result determines what evidence source should be queried next.

---

# 10. Why long-context is tested before RAG

The policy corpus is intentionally moderate in size.

Therefore, RAG must not be assumed to be necessary.

The project first evaluates:

```text
Claim + full policy corpus → LLM
```

against:

```text
Claim → retrieve policy chunks → LLM
```

RAG is justified only if it demonstrates a meaningful advantage in one or more of:

- accuracy;
- correct policy-version selection;
- correct regional-policy selection;
- lower cost;
- lower latency;
- better scalability;
- better traceability;
- reduced distractor effects.

If long context performs equally well at the current corpus size, that is a valid project finding.

---

# 11. Final dataset design

The current final dataset contains:

- **120 expense claims**
- **65 self-contained / RAG-solvable cases**
- **40 fixed-workflow cases**
- **15 dynamic agent-candidate cases**

Frozen split:

- 60 development
- 20 validation
- 40 final test

The final-test set includes:

- 10 independently worded/reviewed challenge cases.

The dataset is fully synthetic and reproducible.

No real employee or company data is used.

---

# 12. Case families

The dataset covers the following major case families:

## 12.1 Self-contained policy cases

All facts required to decide the claim are present in the claim.

The main challenge is applying the correct policy.

## 12.2 Missing-information cases

The policy makes clear that one or more required facts are absent.

Expected behavior:

```text
REQUEST_INFORMATION
```

with specific missing fields.

## 12.3 Temporal-policy cases

The same type of expense may be treated differently in 2024, 2025, or 2026.

The system must apply the policy effective on the transaction date.

## 12.4 Regional-precedence cases

Global policy may be overridden by a regional addendum.

Regions include:

- Singapore;
- India;
- Japan.

## 12.5 Evidence-conflict cases

The employee explanation and structured transaction evidence do not agree.

The system should not accuse the employee of fraud.

It should request clarification or escalate where appropriate.

## 12.6 Duplicate cases

Cases include:

- exact duplicates;
- near duplicates;
- legitimate repeat expenses;
- non-duplicates.

## 12.7 Split-transaction cases

Related expenses may individually fall below an approval threshold but jointly trigger a different policy requirement.

## 12.8 Fixed-workflow cases

External facts are required, but the lookup sequence is predictable.

## 12.9 Dynamic agent-candidate cases

An earlier tool result determines which evidence source becomes relevant next.

These cases are only **candidates** for agentic execution until a workflow-vs-agent experiment proves that dynamic orchestration is actually useful.

---

# 13. Policy corpus design

The policy corpus is approximately **38 pages** and consists of multiple source documents.

It includes:

- global expense rules;
- travel and hotel policies;
- meal and entertainment rules;
- corporate-card rules;
- approval requirements;
- exception processes;
- conference/training rules;
- duplicate-submission rules;
- split-transaction rules;
- 2024, 2025, and 2026 policy versions;
- Singapore addendum;
- India addendum;
- Japan addendum;
- amendments and circulars;
- definitions;
- worked examples;
- policy-precedence rules.

The corpus is difficult because of **structure**, not unnecessary length.

Difficulty is created through:

- cross-document dependencies;
- effective-date differences;
- regional overrides;
- exceptions;
- similar-looking policies;
- plausible distractors;
- amendments;
- policy precedence;
- historical versions.

---

# 14. Cross-document retrieval design

Some cases require evidence from multiple documents.

Examples:

```text
Travel & Hotel Policy
+
Japan Addendum
+
Approval Matrix
```

or:

```text
Duplicate / Split Policy
+
Previous Expense Record
+
Approval Matrix
```

or:

```text
Conference Policy
+
Travel Record
+
Exception Policy
```

This allows meaningful evaluation of:

- Recall@K;
- MRR;
- nDCG;
- required-evidence coverage;
- metadata filtering;
- reranking;
- hybrid retrieval.

---

# 15. Enterprise data design

Policy documents answer:

> **What is the rule?**

Enterprise tables answer:

> **What is true about this case?**

The dataset includes read-only synthetic enterprise tables such as:

- `employees.csv`
- `travel_requests.csv`
- `manager_approvals.csv`
- `policy_exceptions.csv`
- `previous_expenses.csv`
- `project_registry.csv`
- `conference_registry.csv`
- `merchant_directory.csv`
- `fx_rates.csv`

This separation is essential.

Policy knowledge must not contain employee-specific case facts.

---

# 16. Enterprise tools

Candidate read-only tools are:

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

Tool requirements:

- typed inputs;
- typed outputs;
- compact JSON;
- read-only behavior;
- clear not-found/error states;
- discriminative descriptions;
- no hidden evaluator data;
- no irreversible actions.

---

# 17. Duplicate-bill design

Duplicate checking is included as a compliance capability.

The system distinguishes:

- `EXACT_DUPLICATE`
- `POSSIBLE_DUPLICATE`
- `LEGITIMATE_REPEAT`
- `NONE`

## Exact duplicates

Handled deterministically where possible.

Example indicators:

- same bill number;
- same employee;
- same merchant;
- same amount;
- same date.

## Near duplicates

Candidate generation may use:

- merchant similarity;
- date proximity;
- amount tolerance;
- same employee;
- same project/purpose.

A model may only be used for ambiguous candidate adjudication.

The system must avoid falsely blocking legitimate repeated expenses.

The project will measure:

- duplicate precision;
- duplicate recall;
- duplicate false-positive rate;
- legitimate-repeat false-block rate.

---

# 18. Split-transaction design

Split-transaction detection identifies related claims whose combined value changes the applicable approval requirement.

Example:

```text
Expense A = SGD 290
Expense B = SGD 280
Approval threshold = SGD 500

Combined = SGD 570
```

The system must:

1. identify potentially related transactions;
2. retrieve historical claims;
3. combine amounts deterministically;
4. retrieve the applicable threshold rule;
5. check approval evidence;
6. decide whether the claim can proceed.

The system must also include negative controls so similar but legitimate separate purchases are not wrongly grouped.

---

# 19. Missing-information design

`REQUEST_INFORMATION` is a first-class outcome.

The system should not simply say:

> “More information is required.”

It should identify exact missing fields.

Example:

```json
{
  "decision": "REQUEST_INFORMATION",
  "missing_fields": [
    "external_attendee_names"
  ]
}
```

Ground truth includes:

- required missing fields;
- expected request;
- why the information is required.

Evaluation includes:

- missing-field precision;
- missing-field recall;
- over-request rate.

---

# 20. Policy-version design

Policies vary by effective date.

The system must use:

```text
transaction_date
+
policy effective_from
+
policy effective_to
```

rather than simply retrieving the newest policy.

A wrong-year policy can produce a confident but incorrect approval, so this is treated as a major silent-failure mode.

Metadata-aware retrieval will be evaluated specifically for this problem.

---

# 21. Regional-policy design

Regional policy may override global policy.

Examples include:

- Singapore;
- India;
- Japan.

Policy precedence must be represented explicitly.

A typical precedence hierarchy may include:

```text
Regional / legal restriction
→ approved exception
→ category-specific policy
→ global policy
→ FAQ/example
```

The exact hierarchy must come from the synthetic policy corpus rather than being improvised by the model.

---

# 22. Fixed workflow design

A fixed workflow is used when the evidence path is known in advance.

Example:

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

Another example:

```text
Possible duplicate
↓
Search previous expenses
↓
Compare candidate
↓
Disposition
```

Workflow is preferred over an agent when a reasonable finite process can be defined in advance.

---

# 23. Agent design

An agent is not the default.

A case is only genuinely agentic when:

1. the next action cannot reasonably be fixed in advance;
2. a tool observation changes which evidence source should be checked next;
3. the number/path of steps varies based on runtime evidence;
4. dynamic behavior produces measurable value.

Example:

```text
Check travel record
↓
Observation reveals conference_id
↓
Now conference registration becomes relevant
```

But another similar case may produce:

```text
Check travel record
↓
Observation reveals exception_id
↓
Now exception lookup becomes relevant
```

This is meaningfully different from a fixed checklist.

---

# 24. Agent guardrails

If an agent is used, it must be bounded.

Required controls:

- maximum step cap;
- token/cost budget cap;
- action de-duplication;
- typed tool schemas;
- read-only tools;
- explicit stop condition;
- explicit `REQUEST_INFORMATION`;
- explicit `ESCALATE`;
- no financial write actions;
- no payment execution;
- no unrestricted autonomy.

The agent must log:

- selected tool;
- tool arguments;
- returned observation;
- state summary;
- turns;
- tokens;
- latency;
- cost;
- final disposition.

Hidden chain-of-thought must not be exposed or stored.

---

# 25. Selective architecture

The likely final architecture is selective rather than universal.

```text
Claim
↓
Input validation + deterministic checks
↓
Can hybrid RAG + rules resolve safely?
 ├─ yes → resolve
 └─ no
      ↓
Is the external-evidence path predictable?
 ├─ yes → fixed workflow
 └─ no → bounded agent, only if justified
```

The architecture must be decided from measured results.

Possible valid final findings:

## Outcome A

Rules + RAG solve almost everything.

**Final design:** stop there.

## Outcome B

Workflow solves external-data cases and agent adds no material value.

**Final design:** workflow.

## Outcome C

Agent materially improves a small dynamic subset.

**Final design:** selective routing with agent only for that subset.

## Outcome D

Long context matches RAG.

**Final design:** long context may be preferable at current corpus scale.

---

# 26. Primary output schema

Every system variant should ultimately produce a structured result such as:

```json
{
  "decision": "REQUEST_INFORMATION",
  "policy_evidence": [
    "POL-MEAL-2026-4.2"
  ],
  "enterprise_evidence": [],
  "missing_fields": [
    "external_attendee_names"
  ],
  "reason": "External attendee details are required before the client-meal policy can be applied.",
  "manual_review_required": false
}
```

The schema may evolve during development but must remain structured and evaluable.

---

# 27. Ground-truth design

Private ground truth is physically separated from model-visible inputs.

Example:

```json
{
  "case_id": "EXP-091",
  "expected_decision": "ESCALATE",
  "case_family": "SPLIT_TRANSACTION",
  "required_policy_ids": [
    "APPROVAL-2026-4.3"
  ],
  "required_facts": [],
  "missing_fields": [],
  "manual_touch_required": true,
  "human_review_reason": "POSSIBLE_SPLIT_TRANSACTION",
  "duplicate_status": "NONE",
  "split_transaction_status": "RELATED_SPLIT",
  "related_expense_ids": [
    "EXP-084"
  ],
  "workflow_sufficient": false,
  "agent_required_candidate": true,
  "wrong_behaviour_to_catch": "Approving the current claim without checking the related prior transaction."
}
```

Private ground truth must never be included in:

- prompts;
- RAG index;
- tool descriptions;
- runtime model context;
- model-visible logs.

---

# 28. Leakage controls

Leakage is treated as a first-class evaluation risk.

Checks include:

- no answer labels in model-visible files;
- no expected policy IDs in claims;
- no architecture labels in prompts;
- no answer-bearing metadata;
- no tool descriptions that reveal expected paths;
- no challenge-case hints;
- evaluator-only data loaded after runtime completion.

The dataset validator must check for leakage before experiments begin.

---

# 29. Evaluation design

## Primary metric

### Correct Disposition Rate

```text
correct final disposition / total evaluated claims
```

Report:

- raw count;
- percentage;
- 95% Wilson confidence interval.

---

# 30. Safety/business guardrails

## False Approval Rate

Among cases that should not be approved:

```text
incorrect APPROVE / non-approvable cases
```

This is the key safety metric.

## Human Review Rate

```text
claims requiring actual finance-review intervention / total claims
```

This links the system to operational effort.

## Latency

Report:

- median;
- P95.

## Cost

Report actual:

- model calls;
- input tokens;
- output tokens;
- retrieval calls;
- tool calls;
- model/API cost per case.

---

# 31. Diagnostic metrics

Use only where relevant:

- macro precision;
- macro recall;
- macro F1;
- Recall@K;
- Precision@K;
- MRR;
- nDCG;
- required-evidence coverage;
- correct-policy-version rate;
- missing-field precision;
- missing-field recall;
- duplicate precision;
- duplicate recall;
- legitimate-repeat false-block rate;
- split-transaction precision;
- split-transaction recall;
- wrong-tool rate;
- unnecessary tool-call rate;
- turns;
- step-cap hits;
- unsupported-decision rate.

These metrics explain failures.

They do not replace the headline metric.

---

# 32. Oracle experiments

Two oracle experiments are important.

## Policy oracle

The evaluator provides the exact required policy clauses.

Purpose:

> separate retrieval failure from reasoning failure.

Interpretation:

```text
Oracle >> RAG
→ retrieval bottleneck
```

```text
Oracle ≈ RAG and both fail
→ reasoning/application bottleneck
```

## Enterprise-evidence oracle

The evaluator provides the exact required enterprise facts.

Purpose:

> separate tool/orchestration failure from downstream reasoning failure.

---

# 33. Abstention and escalation

The system must be able to say:

> “I do not have enough evidence to safely resolve this claim.”

Abstention/escalation should be evidence-based.

Possible triggers:

- missing required facts;
- failed tool;
- policy conflict;
- contradictory evidence;
- unresolved version conflict;
- unresolved regional precedence;
- insufficient support for automatic approval.

The project must also ensure that the system does not simply escalate everything.

Therefore, safety must always be evaluated together with Human Review Rate.

---

# 34. Silent failure

The most serious silent failure is:

> **A confident APPROVE decision based on the wrong policy version, missed override, false duplicate conclusion, or misread enterprise evidence.**

Mitigations include:

- version/region metadata;
- evidence-required outputs;
- deterministic calculations;
- policy/evidence tracing;
- False Approval Rate monitoring;
- abstention/escalation;
- tool validation;
- bounded agent behavior;
- no irreversible financial action.

---

# 35. Security and responsible-use design

Prompt injection must be tested in:

- employee description;
- retrieved policy text;
- tool output.

Security testing should be informed by:

- **OWASP Top 10 for LLM Applications (2025)**
- especially **LLM01: Prompt Injection**

Responsible-use design should also align with principles from:

- **Singapore IMDA Model AI Governance Framework**

Key responsible-use principles in this project include:

- human oversight;
- traceable evidence;
- no irreversible autonomous action;
- bounded autonomy;
- transparent limitations;
- no employee-character inference.

---

# 36. Business-impact design

The final project should not overclaim real financial savings.

Measured quantities:

- Correct Disposition Rate;
- False Approval Rate;
- Human Review Rate;
- model/API cost;
- tokens;
- latency;
- auto-resolution rate.

Modeled quantities may include:

```text
Expected human-review cost
=
Human Review Rate × assumed manual-review cost
```

Any manual review time or labor cost must be labeled as an assumption.

The business story is:

> **If ExpenseGuard safely reduces the number of claims requiring finance intervention without increasing false approvals, it reduces avoidable operational review effort.**

---

# 37. Cost-to-serve design

Cost evaluation has three layers.

## Layer 1 — Variable AI/system cost

Measure:

```text
cost per claim
```

from:

- model calls;
- tokens;
- embeddings;
- tool/API usage.

## Layer 2 — Expected human fallback

Model:

```text
Human Review Rate × assumed human-review cost
```

## Layer 3 — Fixed cost

Optionally model:

- hosting;
- storage;
- monitoring;
- evaluation runs.

Illustrative scale may be shown at:

- 1,000 claims/month;
- 10,000;
- 100,000.

These are scenario models, not measured production savings.

---

# 38. Reproduced agent failures

If an agent survives the architecture gate, the project will reproduce at least two failures.

## Failure A — loop / repeated tool calls

Temporarily disable:

- action de-duplication;
- loop protection.

Measure:

- repeated calls;
- turns;
- tokens;
- cost;
- success;
- step-cap hits.

Then restore:

- de-duplication;
- step cap;
- budget cap.

## Failure B — ambiguous tool descriptions

Use vague overlapping tool descriptions.

Measure:

- wrong-tool rate;
- extra turns;
- success;
- cost.

Then restore precise descriptions.

These experiments demonstrate that orchestration and tool design are part of the system.

---

# 39. Final experiment philosophy

The project should be developed one experiment at a time.

The expected progression is:

```text
Dataset validation
→ deterministic baseline
→ generic LLM
→ long context
→ naive RAG
→ optimized RAG
→ policy oracle
→ hybrid RAG + rules
→ missing information
→ duplicate checking
→ split transactions
→ enterprise oracle
→ typed tools
→ fixed workflow
→ agent-necessity audit
→ agent only if justified
→ guardrails
→ selective router
→ cost-to-serve
→ frozen final evaluation
→ failure analysis
```

Every new architecture layer must answer:

> **What measured failure in the simpler architecture does this layer fix?**

---

# 40. Final system success criteria

The project succeeds if it identifies the right architecture boundary.

A strong final result does **not** require the agent to win.

Possible strong conclusions include:

- long context is sufficient at current corpus size;
- RAG provides a better cost/grounding trade-off;
- hybrid RAG + deterministic rules is the best general solution;
- fixed workflows handle nearly all enterprise-data cases;
- an agent is justified only for a small dynamic subset;
- an agent is not justified at all.

The strongest final system is the one that maximizes reliable claim resolution while controlling:

- false approvals;
- unnecessary human review;
- latency;
- cost;
- complexity;
- operational risk.

---

# 41. Definition of done

The project is complete when:

- [ ] dataset validator passes
- [ ] private ground truth is isolated
- [ ] deterministic baseline is measured
- [ ] generic LLM baseline is measured
- [ ] long-context baseline is measured
- [ ] naive and optimized RAG are measured
- [ ] policy oracle is run
- [ ] deterministic/LLM hybrid is evaluated
- [ ] missing-information handling is evaluated
- [ ] duplicate detection is evaluated
- [ ] split-transaction detection is evaluated
- [ ] enterprise-evidence oracle is run
- [ ] typed enterprise tools are tested
- [ ] fixed workflow is evaluated
- [ ] agent necessity is audited
- [ ] agent is built only if justified
- [ ] guardrail suite is run
- [ ] abstention/escalation is measured
- [ ] selective router is evaluated
- [ ] cost/latency are measured
- [ ] architecture is frozen before final test
- [ ] final test is run without tuning
- [ ] raw counts + confidence intervals are reported
- [ ] challenge cases are reported separately
- [ ] failures are categorized
- [ ] assumptions are explicitly labeled
- [ ] no fraud/intent claims are made
- [ ] no irreversible financial action is permitted
- [ ] repository can run from a clean README

---

# 42. Final one-sentence project story

> **ExpenseGuard evaluates whether an expense claim is ready for reimbursement and experimentally determines the cheapest reliable architecture — rules, RAG, workflow, or bounded agentic investigation — needed to resolve it safely with minimal unnecessary finance review.**
