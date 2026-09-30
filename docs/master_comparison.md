# Master architecture comparison

Every row is pulled directly from a `results/current/**/summary*.json` file — no hand-typed numbers. Populations
differ across rows (see the **Population** column); never compare two rows' raw fractions without checking
this column first (per the project's rule against comparing unlike denominators, item 14).

Column definitions: **FAR** = false `APPROVE` decisions ÷ ground-truth non-`APPROVE` cases in that row's
population, shown as a count. **HRR** = Human Review Rate (fraction routed to ESCALATE / manual review).
**Status**: `official` (Exp 30/32, the one architecture ever run once against the real final test),
`candidate` (development-and-validation-selected, not final-tested), `rejected` (tried, abandoned for a
measured reason).

| # | Architecture | Population | N | Correct/N | Accuracy | False approvals / non-approvable | FAR | HRR | Model | Cost (total) | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2a | Rules only, as-is (pre-hardening logic) | Dev | 70 | 22/70 | 31.4% | 39/52 | 75.0% | 2.9% | none | $0 | rejected |
| 2c | Rules only, regex-hardened | Dev | 70 | 48/70 | 68.6% | 6/52 | 11.5% | 15.7% | none | $0 | rejected (leads on raw accuracy, but unsafe FAR) |
| 3 | Generic LLM, no policy | Dev | 70 | 26/70 | 37.1% | 0/52 | 0.0% | 0.0% | gpt-4o-mini | $0.0066 | rejected (no grounding, escalates nothing) |
| 4B | Long-context (full corpus + claim) | Dev | 70 | 22/70 | 31.4% | 0/52 | 0.0% | 0.0% | gpt-4o-mini | $0.271 | rejected (no accuracy gain, 40x the cost of RAG) |
| 5 | Naive RAG | Dev | 70 | 21/70 | 30.0% | 0/52 | 0.0% | 1.4% | gpt-4o-mini | $0.018 | rejected (superseded by tuned RAG) |
| 9 | Tuned RAG (M4 metadata filter) | Dev | 70 | 22/70 | 31.4% | 0/52 | 0.0% | 4.3% | gpt-4o-mini | $0.053 | rejected as a standalone system (feeds into Exp 12) |
| 11 | Policy oracle (perfect retrieval, diagnostic) | Dev | 70 | 25/70 | 35.7% | 0/52 | 0.0% | 2.9% | gpt-4o-mini | $0.021 | diagnostic only |
| 12 | Hybrid rules + RAG | Dev | 70 | 33/70 | 47.1% | 2/52 | 3.8% | 20.0% | gpt-4o-mini | $0.058 | rejected (superseded by Exp 30's router) |
| 18 | Fixed workflow (typed tools) | Dev | 70 | 45/70 | 64.3% | 7/52 | 13.5% | 14.3% | none | $0 | rejected (unsafe FAR) |
| 20 | Bounded ReAct agent (pre-fetched RAG) | `C_AGENT_DYNAMIC` dev subset | 13 | 7/13 | 53.8% | 3/10 | 30.0% | 23.1% | gpt-4o-mini | $0.043 | rejected (unsafe FAR) |
| **30** | **Selective resolver (rules → conclusive? → code : LLM)** | **Dev** | **70** | **43/70** | **61.4%** | **0/52** | **0.0%** | **18.6%** | gpt-4o-mini | $0.030 | **official** |
| **32** | **Selective resolver — official final test (one-shot)** | **Final test** | **50** | **30/50** | **60.0%** | **0/37** | **0.0%** | **22.0%** | gpt-4o-mini | $0.023 | **official** |
| 34 | Full agentic-RAG rebuild | `C_AGENT_DYNAMIC` dev subset | 13 | 4/13 | 30.8% | 1/10 | 10.0% | 38.5% | gpt-4o-mini | $0.038 | rejected |
| 40 | Decision-in-code (first guarded tool) | `C_AGENT_DYNAMIC` dev subset | 13 | 7/13 | 53.8% | 0/10 | 0.0% | 30.8% | gpt-4o-mini | $0.015 | rejected (superseded, step toward 41/43) |
| 41 | + disposition gate | `C_AGENT_DYNAMIC` dev subset | 13 | 9/13 | 69.2% | 0/10 | 0.0% | 53.8% | gpt-4o-mini | $0 (cached) | rejected (superseded by 43) |
| 43 | + domain guards (corrected) | `C_AGENT_DYNAMIC` dev subset | 13 | 11/13 | 84.6% | 1/10 | 10.0% | 46.2% | gpt-4o-mini | $0.027 | rejected (superseded by 44) |
| **44** | **Best result on its own slice, unconfirmed beyond it** | `C_AGENT_DYNAMIC` dev+val | 19 | 17/19 | 89.5% | 0/15 | 0.0% | 47.4% | gpt-4o-mini | $0.021 | rejected as a generalizing claim — broke on Exp 45 |
| 45 | Guarded design extended to full dataset | Dev | 70 | 51/70 | 72.9% | 6/52 | 11.5% | 21.4% | gpt-4o-mini | $0.086 | rejected (unsafe FAR) |
| 46 | + stronger model (gpt-4o) | `C_AGENT_DYNAMIC` dev+val | 19 | 15/19 | 78.9% | 0/15 | 0.0% | 42.1% | gpt-4o | $0.694 | rejected (worse accuracy, 30x cost) |
| 47 | Workflow-reuse denylist, full dataset | Dev | 70 | 46/70 | 65.7% | 3/52 | 5.8% | 25.7% | gpt-4o-mini | $0.056 | rejected (regression) |
| 48 | Allowlist redesign, full dataset | Dev | 70 | 45/70 | 64.3% | 2/52 | 3.8% | 28.6% | gpt-4o-mini | $0.064 | rejected (accuracy trade-off, superseded) |
| 49 | + ground-transport tool (pre-fix) | Dev | 70 | 40/70 | 57.1% | 4/52 | 7.7% | 38.6% | gpt-4o-mini | $0.078 | rejected (bug, fixed same experiment) |
| 50 | + gift tool + hotel-date fix + merchant check | Dev | 70 | 43/70 | 61.4% | 1/52 | 1.9% | 34.3% | gpt-4o-mini | $0.091 | rejected (superseded by 51, one bug open) |
| 51 | Dev confirmed clean | Dev | 70 | 44/70 | 62.9% | 0/52 | 0.0% | 34.3% | gpt-4o-mini | $0.089 | candidate |
| **52** | **Validation run + 7th bug fix (current candidate)** | Dev | 70 | 44/70 | 62.9% | 0/52 | 0.0% | 34.3% | gpt-4o-mini | $0.089 | **candidate** |
| **52** | **Validation run + 7th bug fix (current candidate)** | Validation | 30 | 21/30 | 70.0% | 0/22 | 0.0% | 33.3% | gpt-4o-mini | $0.021 | **candidate** |

## Majority-class / trivial baseline (reporting only — no architecture decision rests on this)
Always predicting the single most common ground-truth outcome for that split, computed directly from
`ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl` (evaluator-only reference, used here
only to report a baseline, never fed to any runtime code):

| Population | N | Most common class | Count | Accuracy if always predicted | FAR if always predicted |
|---|---|---|---|---|---|
| Development | 70 | REJECT | 19 | 27.1% | 0% (REJECT is never a false approval) |
| Validation | 30 | APPROVE | 8 | 26.7% | 100% (every one of the 22 non-approve cases would be a false approval) |
| Final test | 50 | REJECT | 13 | 26.0% | 0% (REJECT is never a false approval) |

This is reporting only. It shows that raw accuracy alone is a weak signal here — a trivial REJECT-always
baseline reaches 26-27% accuracy with 0% FAR, so the frozen architecture's 60% final-test accuracy and the
candidate's 62.9-70% dev/validation accuracy are meaningfully above a baseline that costs nothing, not
merely above zero. It also shows why FAR must be tracked separately from accuracy: an APPROVE-majority
baseline on validation would score similarly on raw accuracy to a REJECT-majority baseline on dev, while
being catastrophically unsafe (100% FAR) — accuracy alone cannot distinguish these two outcomes. No
architecture decision in this project rests on this baseline.

## What each complexity rung bought us (item 52)

The whole project story, compressed to one table. "Final decision" reflects the state as of the cost
analysis in `docs/cost_and_business_impact.md`, not just each rung's own accuracy/FAR result in
isolation.

| Rung | Why introduced | Problem it solved | New failure it introduced | Accuracy impact | Safety impact | Cost/latency impact | Final decision |
|---|---|---|---|---|---|---|---|
| Rules only (Exp 2) | Cheapest possible baseline; test whether policy mechanics are simple enough for regex/field-matching | Handles simple, self-contained cases at $0 | Collapses once decision-critical facts move to free text (the dataset's own hardening); approves almost everything once its category checks stop firing | Halves across three hardening rounds (65→54→48/70) | Unsafe on its own — high FAR (11.5-75%) | $0, instant | Rejected as a standalone system; kept as the fast-path layer inside every later architecture |
| Generic LLM, no policy (Exp 3) | Test whether the model already "knows" the policy without retrieval | Nothing — establishes the floor | Confident, unsupported answers not grounded in the actual corpus | 37.1% dev | 0% FAR here, but only because it rarely commits to APPROVE | Cheap ($0.0066/70 claims), fast | Rejected — no grounding |
| Long context (Exp 4B) | Test whether the corpus is small enough that RAG is unnecessary | Nothing new solved vs. Exp 3 | Same ungrounded-reasoning failures, at far higher cost | 31.4% dev, no better than Exp 3 | 0% FAR | 40x the cost of tuned RAG ($0.271 vs. $0.053/70 claims) | Rejected — RAG is justified |
| RAG ladder (Exp 5-10) | Ground the model in the actual policy corpus instead of its own assumptions | Retrieval grounding, correct-version/region selection via metadata filtering | None new; retrieval quality itself plateaus quickly | Marginal (~30-32% dev across variants) — retrieval tuning alone never moved this much | Stayed at or near 0% FAR throughout | Cheap, ~$0.02-0.08/70 claims | Adopted (K=8, 600/100 chunking, dense, M4 metadata) as the frozen retrieval config, but retrieval was never the accuracy bottleneck |
| Policy oracle (Exp 11) | Diagnose whether retrieval or reasoning is the real limiter | Confirms perfect evidence barely helps (22→25/70) | None — a diagnostic, not a shipped component | +3 points over tuned RAG at best | 0% FAR | Diagnostic only | Not deployed; redirected effort from retrieval tuning toward hybrid rules and, later, the agent line |
| Hybrid rules + RAG (Exp 12) | Pull arithmetic/date/threshold mechanics out of the LLM's hands into code | Removes a class of arithmetic error from the residual step | Introduces routing complexity (conclusive vs. not) | 47.1% dev | FAR rose to 3.8% here (pre-conclusiveness-tuning) | Moderate | Superseded by Exp 30's tuned router, but the core idea (compute in code, ask the model only what's left) became the project's central mechanism |
| Fixed workflow (Exp 18) | Test whether a pre-declared tool sequence beats ad hoc RAG for enterprise-evidence cases | Handles predictable multi-table lookups at $0, no model call | Highest FAR of any adopted-scale system (13.5%) — accurate but unsafe | 64.3% dev — the single highest raw dev accuracy of any architecture tested | Unsafe (7/52 false approvals) | $0, instant | Rejected for safety despite leading on raw accuracy — the clearest evidence in this project that accuracy alone cannot drive architecture selection |
| Bounded agent, first attempt (Exp 20) | Test whether dynamic tool-choice adds value over a fixed sequence, on the 13 hardest agent-candidate cases | Ties the workflow (7/13) with genuinely complementary errors — evidence for a selective architecture | High FAR (30%), wrong-tool calls, step-cap hits | Tied with workflow on this subset | Unsafe | Higher latency/cost than deterministic paths, but still cents/claim | Rejected as-is; motivates gating the agent's autonomy rather than abandoning it |
| **Selective resolver (Exp 30, frozen)** | Combine the safe deterministic layer with an LLM only where code can't resolve conclusively | Reaches 0% FAR while keeping most of the deterministic layer's accuracy | The residual LLM step remains weak (36.1% dev, 28.6% final test) — the system's one known weak link | 61.4% dev, 60.0% final test | **0% FAR, dev and final test** | Cheapest safe option: ~$0.0005/claim | **Adopted — this is the official, shipped architecture** |
| Agentic-RAG rebuild (Exp 34-39) | Attempt to fix the residual step's weakness by giving the model tools and letting it search dynamically | Nothing — every variant (stricter prompt, stronger model, perfect RAG, better retrieval, parallel calls) either did nothing or made things worse | FAR as high as 50% (Exp 35B); step-cap hits up to 8/13 (Exp 36) | Flat or worse (30.8% best case, same as the original bounded agent) | Repeatedly worse | 16-30x cost with no accuracy gain (Exp 35B) | Rejected at every variant — the clearest evidence that more autonomy alone does not fix a reasoning bottleneck |
| Decision-in-code + disposition gate (Exp 40-44) | Stop asking the model to judge; give it a tool that computes the disposition, and trust the tool over the model when they disagree | Ties then beats the workflow safely: 7→9→11/13, then 17/19 at 0% FAR | A tool trusted blindly is exactly as dangerous as a model reasoning badly if it fires outside its domain (found and fixed, Exp 42/43) | 53.8%→89.5% on the `C_AGENT_DYNAMIC` subset | 0% FAR throughout this line | Cheapest agent variant yet (as low as $0.015/13 claims) | The mechanism (not yet the final result) is adopted; extended to the full dataset next |
| Full-dataset extension + fixes (Exp 45-52) | Extend the decision-in-code pattern from the 30-claim dynamic subset to the entire dataset | Reaches 44/70 dev and 21/30 validation at 0% FAR — the guarded agent's best-**authorized**-split form | Seven real bugs found by actually running the system: reused fragile free-text logic (Exp 47), placeholder-string hallucination (Exp 49), date-arithmetic miscounts (Exp 50), a missing prerequisite check caught by validation itself (Exp 52). **A later audit also found real, unauthorized execution data for this design against 60% of final-test, scoring 17.6% FAR** (`docs/second_touch_disclosure.md`). | 62.9% dev, 70.0% validation — 1 point above the frozen design on dev; 50% on the 30/50 unauthorized final-test cases an audit found | 0% FAR on authorized splits; 17.6% FAR on the unauthorized final-test diagnostic | Slightly higher AI cost than the frozen design under dev/validation rates, and **substantially higher escalation rate** (34% vs. 19-22%) | **Candidate, not adopted** — cheaper under dev/validation rates (see cost analysis below), but that advantage does not survive its diagnostic final-run safety numbers |
| Cost/business-impact analysis (this pass) | Test whether the candidate's accuracy/FAR advantage translates into an operational win, and whether it holds if unseen-data safety degrades | Under development/validation rates, the corrected cost model finds the candidate cheaper at every scenario scale (an earlier version of the model had a bug that found the opposite). A no-cost sensitivity analysis using the diagnostic final-run rates instead reverses this again: the candidate becomes more expensive than the frozen design. | N/A — an analysis, not an architecture | N/A | N/A | Base scenario: frozen $19,170/1,000 vs. candidate $12,916/1,000 (dev rates) but $20,393/1,000 (diagnostic final-run rates) | **The frozen selective resolver remains the official architecture; the guarded candidate is retained as a promising, unvalidated candidate; no new held-out set created** |
