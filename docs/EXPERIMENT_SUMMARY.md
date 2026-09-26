# ExpenseGuard — Complete Experiment Summary

Every experiment that was run, what was measured, and what it implies. Numbers are on development + validation unless stated. The frozen final test (40 cases) was run once. Per-experiment write-ups are in `docs/`; the whole project is summarised in `docs/FINAL_REPORT.md`. Every number comes from `results/run_log.jsonl` and the per-experiment result folders.

**Headline:** on the frozen final test the rules + fixed tool workflow (router) scored **38/40 correct (95.0%, 95% Wilson interval 83.5–98.6%)** with 2/35 false approvals, 7.5% human review, 0.07 ms median latency and $0 model cost. The best LLM system (gpt-4o-mini with retrieval and code-computed facts) scored 25/40. No agent was justified. Total spend: $0.26 of the $3.50 cap.

---

## Phase A — Data and baselines

| Exp | What was done | Result | What it implies |
|---|---|---|---|
| 0 | Dataset integrity and leakage audit | 32/32 checks pass | The dataset is usable and no labels leak into runtime data. Only 58 distinct claim texts exist across the 120 cases. |
| 1 | 10-case end-to-end slice with the correct clauses supplied | gpt-4o-mini 3/10, llama3.2:3b 4/10; output schema valid 10/10 | The pipeline works. Even with the right clauses the models fail on per-person arithmetic and on missing information. |
| 2 | Deterministic rules baseline | Dev 47/60 (78.3%), val 16/20, final 31/40 | Rules solve every claim-only case and are blind to enterprise evidence. |

## Phase B — Is policy grounding needed?

| Exp | What was done | Result | What it implies |
|---|---|---|---|
| 3 | LLM with the claim only (no policy) | gpt-4o-mini 16/60 (0 false approvals but it rejected 52 of 60 claims); llama 14/60 (26/39 false approvals) | Grounding is required. gpt-4o-mini looked safe only because it refused almost everything. |
| 4 | Full policy corpus (about 6.8k tokens) in context | gpt-4o-mini 19/60 dev, 3/20 val; llama 20/60, 9/20 | The policy in context barely helps. gpt-4o-mini asked for more information on 17 of 21 clean claims. |

## Phase C — RAG

| Exp | What was done | Result | What it implies |
|---|---|---|---|
| 5 | Naive RAG plus a comparison of 6 embedding models | Best embedding: voyage-4-lite (Recall@3 0.61). gpt-4o-mini 17/60, llama 20/60 | RAG uses about 77% fewer tokens and costs 53% less than full context, but is no more accurate. A free embedding model came close to the paid ones. |
| 6 | Chunking strategies, including recursive chunking | Recursive 300/50 best (MRR 0.535 vs 0.498 fixed). gpt-4o-mini 23/60 dev, 6/20 val | Chunk size matters more than method on this small corpus. One-clause chunks lose context. |
| 7 | Top-K of 1, 3, 5, 8 | K = 3 chosen. Accuracy is flat beyond K = 3 while cost rises | More retrieval buys recall but not better decisions. |
| 8 | BM25 vs dense vs hybrid | Dense best (MRR 0.665); hybrid 0.588; BM25 0.481 | The hybrid did not beat dense retrieval. |
| 9 | Metadata filter (effective date and region) | Recall 0.60 → 0.64; wrong-year and wrong-region chunks fell to 0. gpt-4o-mini fell from 23/60 to 20/60 | The filter fixes retrieval but does not improve LLM decisions. Wrong-year retrieval was rare to begin with. |
| 10 | Skipped by agreement | — | Retrieval was not the limiting factor. |
| 11 | Policy oracle (exact clauses supplied) | Oracle equals RAG on development (23 vs 23); helps gpt-4o-mini on validation (9 vs 2) | Retrieval is not the main bottleneck. Applying the policy is. |

## Phase D and E — Hybrid logic and historical evidence

| Exp | What was done | Result | What it implies |
|---|---|---|---|
| 12 | RAG plus code-computed facts | gpt-4o-mini 30/60 dev, 10/20 val, but false approvals rose from 0 to 4/39; llama 20/39 false approvals | The biggest LLM gain, and it made the models less careful. |
| 13 | Missing-information detection | Rules: 13/13 correct, field precision 1.00, recall 0.81; gpt-4o-mini 5/13; llama 1/13 | Rules ask for exactly the right fields. LLMs mostly do not ask. |
| 14 | Duplicate detection (exact, fuzzy rules, LLM adjudication) | Exact only: 72/80, recall 0.40. Exact + fuzzy rules: 80/80. LLM adjudication: gpt-4o-mini 78/80 (recall 0.60), llama blocked 5/5 legitimate repeats | Deterministic candidate rules win. The 80/80 is not independent: rules were written after seeing labels. |
| 15 | Split-transaction detection | Related purchases 7/7, combined amounts 7/7, detection 3/7, disposition 5/7 | The 4 detection misses are the currency-label inconsistency (below). |

## Phase F to H — Enterprise evidence and the agent gate

| Exp | What was done | Result | What it implies |
|---|---|---|---|
| 16 | Enterprise-evidence oracle on 37 evidence cases | gpt-4o-mini 11 → 16 with exact records; llama 18; rules 20; workflow 30 | Fetching evidence is not the problem. Applying it to policy is. |
| 17 | 8 typed read-only tools plus unit tests | All tests pass; they caught a bug where empty results returned `[]` instead of `null` | The tool layer is reliable and read-only. |
| 18 | Fixed workflow (three versions) | Dev 52/60 → 57/60 → 58/60; val 14/20 → 16/20 → 18/20; **final 38/40** | The workflow is the right architecture. I removed one rule of my own that the policy never stated. |
| 19 | Agent-necessity audit of the 10 agent-candidate cases in dev/val | Branching is a 3-way if/else with a maximum depth of two tools | An agent is not justified (Outcome B). |
| 20–27 | Not run (conditional on Exp 19) | — | The plan runs the agent experiments only if an agent is justified. |

## Phase K and L — Safety, abstention, router, cost

| Exp | What was done | Result | What it implies |
|---|---|---|---|
| 28 | 15 guardrail tests | System 15/15; LLM path 3/4 (both models) | The LLMs resisted the injections but both failed the restaurant-bill vs taxi-description conflict. I wrote these tests myself, so 15/15 is not an independent security result. |
| 29 | Abstention and escalation behaviour | Workflow: 2.5% escalation, abstained on 22 of 29 cases needing review. llama abstained on 1 of 29. Always-escalate control: 8.7% correct | LLMs make confident wrong answers instead of abstaining. |
| 30 | Selective router | 73/80, then 76/80 after the hotel-branch change; identical to the workflow | Tool calls take microseconds, so routing saves nothing measurable here. |
| 31 | Cost-to-serve model | LLM path about $0.00027 per claim; rules and workflow $0 | The LLM path looks cheapest on review cost alone but has 5,000 wrong dispositions per 10,000 claims against 875 for the workflow. Review-time and fixed-cost figures are assumptions. |

## Phase M — Frozen final test (run once, 40 cases)

| System | Correct | Wilson 95% | False approvals | Human review | Challenge set | Excl. flagged cases | Median latency | Cost per case |
|---|---|---|---|---|---|---|---|---|
| **Router (rules + workflow)** | **38/40 (95.0%)** | 83.5–98.6% | 2/35 | 7.5% | 9/10 | 36/36 | 0.07 ms | $0 |
| Rules only | 31/40 (77.5%) | 62.5–87.7% | 4/35 | 17.5% | 7/10 | 30/36 | 0.02 ms | $0 |
| gpt-4o-mini RAG + code facts | 25/40 (62.5%) | 47.0–75.8% | 1/35 | 0% | 5/10 | 24/36 | 1.68 s | $0.00026 |
| llama3.2:3b RAG + code facts | 10/40 (25.0%) | 14.2–40.2% | 17/35 | 0% | 4/10 | 9/36 | 3.11 s | $0 |

| Exp | What was done | Result |
|---|---|---|
| 32 | Frozen final test; freeze manifest hash-verified before the run; the runner refuses a second run | Table above |
| 33 | Failure analysis with one primary category per failure | The router's two failures are both false approvals on currency-threshold cases (EXP-0088 split-transaction miss; EXP-0092 failed to escalate). LLM failures are mostly missing-information and reasoning errors. |

---

## What I infer overall

1. **The right architecture is rules plus a fixed tool workflow.** LLMs never beat the rules at any point, and an agent was not needed.
2. **LLMs fail at applying policy, not finding it.** They stayed weak with the correct clauses (Exp 11) and the correct records (Exp 16), and they almost never abstain when they should.
3. **The safety cost of LLM help is real.** Adding code-computed facts raised accuracy and false approvals together.
4. **Retrieval improvements did not translate into better decisions.** Each retrieval gain moved decision accuracy by no more than noise.
5. **Cheap is not the same as good.** The LLM path looks cheapest on review cost alone; error cost has to sit beside it.

## Dataset findings (nothing was changed)

- 120 cases but only 58 distinct claim texts, so effective sample sizes are smaller than nominal.
- Approval-threshold labels for some non-SGD claims apply the SGD threshold to the raw amount (JPY 54,000 ≈ SGD 491; INR 17,500 ≈ SGD 284; JPY 1,200 ≈ SGD 11). This contradicts the policy text and the dataset's own exchange-rate table. Affected cases were flagged from inputs only, before the final run.
- Over-ceiling hotel claims with neither an exception nor a conference: the policy does not say reject or escalate; the labels say escalate.
- No hard negatives exist for near-duplicate or split detection.
- The `workflow_sufficient = false` flag on the 15 agent candidates is true of a linear checklist but not of a branching workflow.

## Caveats

- **Only the final test is an independent estimate.** The workflow, duplicate and split logic were developed while looking at development and validation labels (disclosed in each doc), and one hotel branch was changed after seeing three of those labels (disclosed in the freeze manifest).
- **Sample and data:** the final test has 40 cases on a synthetic, templated dataset. These numbers estimate performance on this benchmark, not real-world accuracy.
- **No agent was built or run.** The conclusion that an agent is unnecessary rests on the audit and the workflow's results, not on a head-to-head test. The plan's "agent for everything" strategy was not measured.
- **LLM baselines:** two small models, one untuned prompt each. Prompt wording alone moved a development score by 3 cases. Stronger models were not tried.
- **Guardrail tests** were written against my own design. **Cost-to-serve** figures for review time, analyst cost and fixed costs are assumptions, not measurements.
- No claims are made about fraud, intent or real-world savings.
