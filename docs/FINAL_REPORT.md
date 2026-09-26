# ExpenseGuard — Final report

## Question and answer
**Question:** when are rules sufficient, when is RAG sufficient, when is a fixed workflow required, and when does agentic investigation justify its cost, latency and risk?
**Answer on this benchmark:** claim-only cases are solved by deterministic rules; enterprise-evidence cases by a fixed tool workflow with if/else branching; LLMs (RAG, long context, hybrid) did not beat the rules at any point and were not needed; an agent was not justified. On the frozen final test the rules + workflow router scored **38/40 (95.0%, Wilson 83.5–98.6%)** with 2/35 false approvals, 7.5% human review, 0.07 ms median latency and $0 model cost. Best LLM system: gpt-4o-mini with retrieval and code-computed facts, 25/40 (62.5%). This is **Outcome B** of the plan (workflow solves the enterprise cases; agent adds nothing).

## The ladder, measured (development + validation unless noted)
| Step | Result | Verdict |
|---|---|---|
| Exp 2 rules | dev 47/60, val 16/20; final 31/40 | strong on claim-only cases; blind to enterprise evidence |
| Exp 3 LLM without policy | 16/60 (gpt-4o-mini), 14/60 (llama) | grounding needed |
| Exp 4 full policy in context (about 6.8k tokens) | 19/60 dev, 3/20 val | little gain; policy application, not access, is the limit |
| Exp 5–9 RAG (recursive 300/50 chunks, voyage-4-lite, K = 3, metadata filter) | best retrieval Recall@3 0.64, MRR 0.70 | RAG is cheaper (about 77% fewer tokens than full context) but not more accurate |
| Exp 11 policy oracle | oracle about equal to RAG on development | retrieval is not the main bottleneck |
| Exp 12 RAG + code-computed facts | 30/60 dev, 10/20 val (gpt-4o-mini) | best LLM configuration; raised false approvals |
| Exp 13–15 missing info, duplicates, splits | rules ask for the right fields (13/13); fuzzy rules beat LLM adjudication; splits found 7/7 | deterministic code beats models |
| Exp 16 enterprise oracle | LLM with exact records 16/37; workflow 30/37 | orchestration is not the bottleneck; applying evidence is |
| Exp 18 fixed workflow | dev 58/60, val 18/20 (after disclosed fixes); final 38/40 | the architecture |
| Exp 19 agent audit | branching is a 3-way if/else, depth 2 | agent not justified; Exp 20–27 not run |
| Exp 28 guardrails | system 15/15; LLM path 3/4 | see caveats |
| Exp 29 abstention | workflow abstains on 22/29 cases needing review, 2.5% escalation | LLMs almost never abstain |
| Exp 30–31 router and cost | router = workflow; LLM path cheapest on a review-cost-only model but 5,000 wrong dispositions per 10,000 claims | error cost must sit beside review cost |
| Exp 32–33 final test and failures | 38/40; two currency-threshold false approvals | see docs |

## Findings worth keeping
1. The simplest layer that can solve a class of cases should solve it: rules for arithmetic, dates, FX, exact duplicates and required fields; tools for records; a model only where free text truly needs reading. In this run no such case appeared that rules could not read.
2. LLMs were unreliable at applying policy even with the right clauses and the right facts in the prompt (oracle experiments), and almost never abstained when they should have.
3. Providing code-computed facts was the largest LLM improvement, and it made false approvals worse, so any LLM component needs a deterministic safety layer.
4. Validation of the tools caught a real bug (empty results returned `[]` instead of `null`); process discipline mattered more than model choice.

## Dataset findings (no data was changed)
- 120 cases but only 58 distinct claim texts (up to 8 repeats), so effective sample sizes are smaller than nominal and intervals are wide.
- Approval-threshold labels for some non-SGD claims apply the SGD threshold to the raw amount (JPY 54,000 ≈ SGD 491; INR 17,500 ≈ SGD 284; JPY 1,200 ≈ SGD 11), contradicting the policy text and the frozen FX table. Six dev/val/final cases are affected and were flagged from inputs before the final run.
- Over-ceiling hotel claims with neither exception nor conference: the policy does not say REJECT or ESCALATE; labels say ESCALATE.
- The dataset contains no hard negatives for near-duplicate or split detection: candidate generation finds nothing outside the designed cases.
- The "workflow_sufficient = false" flag for the 15 agent candidates is true of a linear checklist but not of a branching workflow.

## Honest limitations
- **Held-out integrity:** the final test was run once after the freeze. But the workflow, duplicate and split logic were developed while looking at development and validation labels (disclosed per experiment), and one hotel branch was changed after seeing three dev/val labels (disclosed in the manifest). Development and validation results are therefore not independent estimates; only the final result is, and it has n = 40 and a synthetic templated dataset.
- **No agent was built or run.** The conclusion that an agent is unnecessary rests on the audit and on the workflow's results, not on a head-to-head experiment (Exp 20–27 were skipped by the plan's gate). The plan's third router strategy, "agent for everything", was not measured.
- **Guardrail suite** was written by me against my own design (one test each); it is not an independent red-team.
- **Cost-to-serve:** review time, analyst cost, fixed monthly costs and 100% manual accuracy are assumptions, not measurements; nothing is a measured saving.
- **Small models and one prompt:** the LLM baselines used gpt-4o-mini and a 3B local model with a single prompt, not tuned; prompt wording alone moved a development score by 3 cases. Stronger models were not tried, so "LLMs did not help" applies to these models and prompts.
- No claims are made about fraud, intent or real-world savings.

## Reproducing
See the root `README.md`. Every number is in `results/run_log.jsonl` (LLM calls with tokens in/out, cost and latency; per-case results; evaluation rows; tool calls; experiment summaries) and in the per-experiment folders; nothing was typed by hand.
