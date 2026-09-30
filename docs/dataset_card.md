# ExpenseGuard V2 Dataset Card (semantic edition)

## What changed in the semantic edition
The first V2 exposed every decision-critical fact in a structured claim `form` (cabin, attendee counts, gift type, alcohol amount...), so a rule engine reading those fields reached 100%. In this edition the visible `form` is empty and the bill has one generic line item: **every fact a decision depends on is stated only in a free-text note**, drafted by gpt-4o-mini from hidden facts. Notes vary in style (indirect, terse, verbose with distractor numbers, assistant-written, local-language terms, formal challenge memos), express some facts indirectly (check-in/check-out dates instead of nights, a list of who attended instead of a headcount, cabin by its features) and rely on policy definitions (contractors are external, subsidiary staff and interns on payroll are employees, e-vouchers are cash equivalents, state-owned bodies are government-affiliated: clauses MEAL-1.4, GIFT-1.5, GIFT-1.6 and FAQ entries). The hidden exact facts stay in `04_ground_truth_PRIVATE` (`hidden_form`, `hidden_description`) and still drive every label through the reference engine. Each note was validated by a blind LLM extraction against the hidden facts, by a re-run of the reference engine on the visible text, and by leak/length checks; the notes are **not human-reviewed** (one note was accepted by hand, see `semantic.manual_review`).

## Purpose
A harder synthetic benchmark for expense-claim readiness (APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE) built to stress **retrieval**: a dense, versioned, cross-referenced policy corpus; claims phrased in everyday language; and rules whose numbers live in different documents, years, regions and circulars. The task is not fraud detection.

## Size
- 150 unique claims (every employee description and bill number is unique; one employee per claim, so no employee spans splits)
- 22 policy documents, 229 clauses, 39,470 words, 71-page PDF
- 11 enterprise tables; 2,483 historical expenses (including hard-negative rows for duplicate and split detection)
- 15 separate guardrail cases (carried over from V1, `04_ground_truth_PRIVATE/guardrail_cases.csv`)

## Architecture groups
| Group | Cases | Meaning |
|---|---|---|
| A_SELF_CONTAINED | 40 | Decidable from the claim, the policy corpus and the FX table; no enterprise lookup is needed |
| B_WORKFLOW | 80 | Fixed evidence path once the claim type is known; 47 need two or more lookups, the rest need one |
| C_AGENT_DYNAMIC | 30 | The next record to read depends on what the previous lookup returned; chains are 2 to 5 lookups deep (lookups needed: {2: 9, 3: 12, 4: 4, 5: 5}) with recorded branch triggers |

Cross-document cases (evidence in two or more documents): 116. Cases decided by a mid-year circular amendment: 28.

## Outcomes
All: {'REJECT': 40, 'APPROVE': 39, 'REQUEST_INFORMATION': 35, 'ESCALATE': 36}. Development: {'APPROVE': 18, 'REQUEST_INFORMATION': 16, 'REJECT': 19, 'ESCALATE': 17}. Validation: {'APPROVE': 8, 'ESCALATE': 7, 'REJECT': 8, 'REQUEST_INFORMATION': 7}. Final test: {'REJECT': 13, 'APPROVE': 13, 'REQUEST_INFORMATION': 12, 'ESCALATE': 12}.

## Frozen split
70 development / 30 validation / 50 final test, stratified by outcome and then by group. Final test by group: {'A': 14, 'B': 25, 'C': 11}.
**Challenge set:** 15 final-test cases (outcomes {'ESCALATE': 4, 'APPROVE': 4, 'REJECT': 4, 'REQUEST_INFORMATION': 3}) whose free-text description was rewritten with a separately authored template (different structure and vocabulary, same structured facts). "Independent" here means independently authored templates; **the wording was not reviewed by a human.**

## Corpus design (why retrieval is hard)
- **Near-identical clauses across years, regions and grade bands**: three global policy versions, three regional addenda and yearly ceiling tables that differ only in numbers and dates.
- **Two-hop numbers**: employee meal, client meal, gift, telecom and mileage limits live only in the regional addenda; the global meals policy points to them and states default figures that never apply to Singapore, India or Japan.
- **Mid-year circulars** amend values held in other documents without naming the category in their headings; the controlling value depends on the transaction date.
- **Stale distractors**: a historical-schedules document, an expired 2023 schedule, withdrawn drafts, and worked examples that quote the value current when they were written.
- **Vocabulary gap**: policy text uses formal terms (ground transportation, accommodation, hospitality); claims say cab, put up, hosted.
- **Filler with a purpose**: each clause carries two paragraphs of qualitative interpretive guidance (written once by gpt-4o-mini and frozen in `dataset_v2/commentary_cache.json`; validated to contain no numbers, currency codes or new requirements) so relevant text is diluted by realistic prose.
- Document list: D01 Global Expense Policy 2024, D02 Global Expense Policy 2025, D03 Global Expense Policy 2026, D04 Travel and Accommodation Policy, D05 Air and Rail Travel Standards, D06 Ground Transportation Policy, D07 Meals and Entertainment Policy, D08 Client Gifts and Hospitality Policy, D09 Corporate Card and Personal Spend Policy, D10 Approval Authority, Delegation and Budget Control Policy, D11 Exceptions and Waivers Procedure, D12 Training, Certification and Conferences Policy, D13 Software, Subscriptions and Equipment Policy, D14 Telecommunications Policy, D15 Duplicate, Split and Recurring Expense Controls, D16 Currency and FX Handling Policy, D17 Singapore Expense Addendum, D18 India Expense Addendum, D19 Japan Expense Addendum, D20 Finance Circulars 2024 to 2026, D21 Historical Limits and Superseded Schedules, D22 Definitions, Frequently Asked Questions and Worked Examples.

## Ground truth
Every label comes from `dataset_v2/engine.py`, a reference policy engine that reads the same structured schedules (`dataset_v2/world.py`) the policy text is rendered from, so the text and the labels cannot disagree. Thresholds in SGD equivalent use the monthly FX table exactly as the FX policy states, avoiding the raw-amount inconsistencies found in V1. Per case the ground truth records the decision, controlling clause ids (`required_policy_ids`), context clauses (`supporting_policy_ids`), the documents involved, missing fields, the tool path the engine walked, the minimum required tools, branch triggers and the human-review reason for escalations.

## Retrieval difficulty (same retrievers, chunking and query builder on both datasets; recall / all-required-clauses-retrieved)
| Retriever | V1 (23 chunks) | V2 (218 chunks) |
|---|---|---|
| dense, K=3 | 0.57 / 0.39 | 0.29 / 0.13 |
| dense, K=10 | 0.77 / 0.62 | 0.46 / 0.20 |
| BM25, K=3 | 0.43 / 0.26 | 0.14 / 0.09 |
| hybrid (RRF), K=3 | 0.56 / 0.39 | 0.26 / 0.13 |
| dense + metadata filter, K=3 | 0.64 / 0.44 | 0.29 / 0.13 |
voyage-4-lite embeddings, recursive 300/50 chunks. V2 cases need 3.16 controlling clauses on average (V1: 2.12). Part of the difficulty is corpus size and more required clauses, which is intended.

## Enterprise tables (rows)
approval_delegations 37, conference_registry 15, cost_centre_budgets 83, employees 300, fx_rates 108, manager_approvals 123, merchant_directory 182, policy_exceptions 46, previous_expenses 2483, project_registry 60, travel_requests 114.

## Validation
`python -m dataset_v2.validate` runs 50 checks (50 pass): split, group and outcome balance, clause existence, schedule values present in the corpus, PDF page count, referential integrity, uniqueness, leakage (labels absent from cases, corpus and tables; challenge cases unmarked), and **reproduction of every label by the reference engine from the packaged files**. Report: `06_docs/validation_report.json`.

## Data boundaries
Runtime and model-visible: `02_cases`, `01_policy_corpus`, approved read-only tools over `03_enterprise_data`. Evaluator-only: `04_ground_truth_PRIVATE`.

## Known limitations
- Synthetic; not for estimating real prevalence, behaviour, processing times or fraud.
- The reference engine defines the policy semantics where the prose could be read two ways; a human policy review of the engine would strengthen the labels.
- 47 of the 80 workflow cases need two or more lookups; the other 33 need exactly one, so "multi-tool" holds for 47/80.
- The runtime tool layer in `src/` still targets V1 (eight tools). V2 adds two lookups (`get_approval_delegation`, `get_cost_centre_budget`) and new columns, and needs a port before systems can be run on it.
- Claim notes and policy commentary are LLM-written; the notes were validated automatically only. The retrieval-difficulty table below was measured on the previous V2 corpus (three clauses and three FAQ entries were added afterwards), so treat it as approximate.
- Interpretive guidance was LLM-written (qualitative only). The V1 metadata-aware wrong-year metric is near zero here because temporal difficulty sits in circular-versus-base values, not in whole-year documents.
- No baseline system results exist yet on V2 apart from the retrieval measurements above.
