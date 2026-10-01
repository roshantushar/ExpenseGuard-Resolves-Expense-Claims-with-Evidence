# Full experiment table — description, rationale, inference, and next step

Every experiment this project ran, in one table: **what it was**, **why it was run**, **what it actually
showed**, and **why that led to the next one**. Source of truth for the short "Headline result" version:
[`docs/README.md`](README.md#full-experiment-index); per-experiment detail: `docs/expNN_*.md`,
`results/current/`. Numbers 21–27 are a deliberate gap (no record kept of why — stated plainly rather than
implied to be data loss; see `docs/README.md`).

## Part 1 — building the frozen architecture (Exp 0–33)

| # | Description | Why it was carried out | What was inferred | Why it led to the next step |
|---|---|---|---|---|
| 0 | Dataset validation + exploratory data analysis on the generated 150-claim set | A dataset no one has checked for leakage or structural bias isn't safe to build on | 0 critical errors; hardened 3 rounds total so decision-critical facts live only in free text, never a structured field | Cleared the dataset as a safe foundation before any architecture work began |
| 1 | Smallest possible end-to-end slice: one claim, exact policy clauses handed directly, one LLM call, one decision | The project's own rule: prove the smallest version works before adding any layer | 18/18 schema-valid outputs, 0 errors — feasibility confirmed; accuracy (55.6%/44.4%) was explicitly not the bar being tested | Cleared to add retrieval, rules, and eventually an agent, one layer at a time |
| 2 | Deterministic rules alone, no model, no retrieval | Test whether the cheapest possible approach already solves the problem | Early rule baselines failed outright; after hardening, regex-only extraction degraded substantially (69%→roughly halved) once facts moved into free text | Proved rules alone can't read prose — motivated adding retrieval and an LLM for the residual |
| 3 | Generic LLM, no policy context at all | Isolate how much a model can do with zero grounding | Confident, but entirely unsupported answers | Proved grounding (policy evidence) is necessary, not optional |
| 4A/4B | Long-context feasibility and baseline: whole policy corpus in the prompt, no retrieval | Test whether retrieval is even necessary at this corpus size | Feasible, but ~$0.77/run — 40x a tuned RAG pipeline, no accuracy gain | Retrieval (RAG) justified on cost grounds at this corpus size |
| 5–10 | RAG tuning ladder: chunking, top-K, retriever, metadata filtering | A naive RAG config is rarely a fair test of retrieval's ceiling | Froze at 600/100-token chunking, K=8, dense embeddings, a metadata filter — Recall@8 plateaued at 0.56 | Set up the critical oracle test: is 0.56 recall the bottleneck, or is something else? |
| 11 | Policy oracle: hand the model the exact correct clauses directly, bypass retrieval | Separate a retrieval failure from a reasoning failure | Accuracy moved only from 22 to 25/70 with *perfect* evidence — retrieval was not the dominant bottleneck | Redirected the rest of the project from retrieval tuning toward hybrid rules and reasoning-focused fixes |
| 12, 12B | Hybrid deterministic rules + RAG; an early router probe | Test whether combining code and retrieval beats either alone | Motivated pulling arithmetic/date logic into code; the routing concept itself held up | Began the shift toward a selective (code-first) architecture |
| 13–17 | Qualify each remaining component individually: missing-info detection, duplicate detection, enterprise-fact resolution, typed tools | Each piece needed its own evidence before being assembled into a pipeline | Each component qualified on its own terms (precision/recall measured, not assumed) | Cleared every component needed to build a real fixed workflow |
| 18–20 | Fixed, pre-declared tool workflow vs. a real bounded ReAct agent | The central design question: does dynamic tool choice earn its cost over a fixed plan? | Workflow hit 64.3% dev accuracy (highest raw accuracy tested) but 13.5% FAR — unsafe; the agent only tied the workflow (7/13) at 3x the FAR | **Agent gate closed** — autonomy didn't earn its cost yet; motivated a selective, code-first design instead |
| 28 | Adversarial guardrail suite: prompt injection, fake authority, conflicting records, malformed/timeout failures | A system isn't safe just because it hasn't been attacked yet | Found and fixed one real bug; retrieval-text injection defeated the defense once — logged as an open, disclosed risk, not silently patched away | Confirmed the architecture needed an explicit, honest risk table, not a clean-bill-of-health claim |
| 29 | Abstention/escalation behavior audit | Quantify how well the system knows when *not* to decide | Measured real risk-coverage tradeoffs for `ESCALATE` | Informed the freeze decision's safety threshold |
| **30** | **Architecture freeze**: deterministic rules decide whenever they can, an LLM handles only the residual | Combine every finding above into one committed design before testing it blind | **0/52 falsely approved (0% observed FAR) at 61% dev accuracy** — traded a few points of raw accuracy for eliminating false approvals | `src/resolver.py` frozen at this point — no further tuning after this, by the project's own rule |
| 31 | Cost-to-serve measurement on the frozen design | Confirm cost wasn't secretly the real constraint before going further | $0.00043/claim measured — inference cost was not a material architecture-selection constraint at this pricing/workload | Freed the project to choose architecture on accuracy/safety grounds, not cost, at this stage |
| **32** | **The official, one-shot final test** against the 50-claim held-out split, verified against a pre-committed hash manifest | The project's single most important evidentiary claim — run once, ever, per the freeze discipline | **30/50 (60%), 0/37 falsely approved (0% observed FAR)**; deterministic path 22/22, LLM-residual path only 8/28 | Named the LLM-residual path as the one weak, unresolved component — the target for everything that follows |
| 33 | Failure analysis on all 20 final-test errors | Understand *why* the residual path failed before trying to fix it blind | 9 reasoning failures, 5 over-asking, 4 fact gaps, 2 escalation-logic errors, **0 retrieval failures** | Confirmed (again) that reasoning, not evidence access, was the real target — set up the guarded-agent research line |

## Part 2 — the agentic-RAG diagnostic line (Exp 34–39): ruling things out

| # | Description | Why it was carried out | What was inferred | Why it led to the next step |
|---|---|---|---|---|
| 34 | A real, full agentic-RAG rebuild from scratch | Test whether a proper agent (not Exp 20's early version) does better | Worse than the fixed workflow: 4/13, and a tier-substitution false approval | Needed to isolate *which* variable was actually responsible before trying more fixes at once |
| 35 | Isolated prompt / model / tool-interface changes, one at a time | Avoid changing multiple variables and not knowing which one mattered | None fixed it alone | Ruled out quick fixes — the problem was structural, not cosmetic |
| 36 | Parallel tool-call turns + a second-generation poka-yoke (mistake-proofing) fix | Try a different failure-prevention mechanism | Fixed its one specific target case, but step-cap hits got *worse* overall | Confirmed fixes needed to be general, not case-specific patches |
| 37 | Perfect policy oracle, repeated on the agent (same test as Exp 11, different architecture) | Check whether the agent's failure was also a retrieval problem | Same accuracy, but FAR *quadrupled* with perfect evidence | Proved perfect retrieval was insufficient to fix the agent — reasoning, again, was the real issue |
| 38 | Free ($0) audit of the agent's own self-issued search queries | The agent chooses its own queries — were they actually any good? | 33.6% recall, and the agent never once re-queried after a weak result | Found a real, separate, secondary problem: the agent's own retrieval behavior was genuinely weak |
| 39 | Fixed that specific retrieval-query weakness | Test whether fixing it closes the overall accuracy gap | Recall improved to 45.4% — but final accuracy still *fell* | Proved retrieval and reasoning are two separate failure modes — fixing one doesn't fix the other |

## Part 3 — the fix, and closing the gap (Exp 40–52)

| # | Description | Why it was carried out | What was inferred | Why it led to the next step |
|---|---|---|---|---|
| **40** | Tools that *compute* the decision in code, instead of the model judging it from fetched facts | If reasoning is the problem, stop asking the model to reason about the parts code can resolve | Tied the fixed workflow: 7/13, 0% FAR | Proved code-computed tools were viable — the next question was whether they could *beat* the workflow |
| **41** | A disposition gate: if a tool already computed the right answer and the model disagreed, trust the tool | Stronger than just offering the tool — actually enforce its answer | Beat the workflow outright: 9/13, 0% FAR | Established the gate as the core mechanism, not just a nice-to-have |
| 42 | Added a project-budget tool to the guarded set | Extend coverage to more claim categories | Caught a tool firing confidently on a claim type it was never built for, live | Exposed a general failure class: tools need to check their own applicability |
| **43** | Domain guards added: every tool checks the claim type before answering | Directly close the exact gap Exp 42 found | 11/13 (84.6%) | Validated the domain-guard pattern as a structural fix, not a one-off patch |
| **44** | Confirmed result on the full `C_AGENT_DYNAMIC` subset | Check the fix generalizes within its original test slice | 17/19 (89.5%), 0% FAR — best result yet, but only on this slice | Set up the real test: does this hold on the *full* dataset, not just the curated subset? |
| 45 | Extended the same design to the full dataset | The subset result means nothing if it doesn't generalize | *Rejected* — accuracy rose, but FAR broke to 11.5%, concentrated entirely in categories with no guarded tool | Proved the gate only protects what it's built for — motivated closing coverage gaps category by category |
| 46 | Swapped in a stronger model, guards unchanged | Test whether model size, not architecture, was the real lever | *Rejected* — worse accuracy, 30x the cost; FAR held at 0% regardless of model | Proved the guards, not model size, were what controlled safety — an important, reusable finding |
| 47 | Reused an existing, already-tested tool as a catch-all for uncovered categories | Avoid building a new tool from scratch for every gap | *Rejected, a regression* — 46/70, down from 51/70; the reused tool shared the same free-text fragility it was meant to route around | Proved a "reuse what's tested" shortcut doesn't work if the tool's own weakness travels with it |
| 48 | Redesigned the fallback to trust only checks independent of free-text parsing | Directly fix what Exp 47 exposed | 45/70, FAR 3.9% | Recovered safety, but accuracy was still below the frozen baseline's own dev number |
| 49 | Added a ground-transport (mileage) tool | Extend coverage further | Found and fixed a live bug: the model passing the placeholder string "unknown" as if it were a real answer | Reinforced that live bugs, not theoretical gaps, were the actual source of most failures |
| 50 | Added a gift-compliance tool, a hotel-date-counting fix, and a merchant-metadata cross-check | Close the remaining known coverage gaps | 43/70, FAR 1.9% — ties the frozen baseline's own dev accuracy | Close enough to warrant a clean, full confirmation run |
| 51 | Clean development-split confirmation run | Verify the design holds without any further changes | **44/70 (62.9%), 0/52 falsely approved (0% observed FAR)** — one point above the frozen design's own dev accuracy | Cleared to test on validation — a split the design hadn't been tuned against as directly |
| **52** | Validation run | Check generalization beyond the development split | **21/30 (70.0%), 0/22 falsely approved (0% observed FAR)** — but a 7th live bug was found and fixed during this run | Flagged as a development-and-validation-selected candidate, not an independently validated one — set up the root-cause work in Part 4 |

## Part 4 — root-causing the candidate's missed APPROVE cases, fixing it, fresh-holdout validation (Exp 53–60)

| # | Description | Why it was carried out | What was inferred | Why it led to the next step |
|---|---|---|---|---|
| 53 | Tried prompt-only fixes to recover missed APPROVE cases | Cheapest possible fix to try first | Recovered some cases, but introduced a new false approval | *Rejected* — proved the fix needed to be structural, not prompt-level |
| 54 | Swapped in a stronger model, same prompt, as a diagnostic | Rule out "the model just isn't smart enough" | Modest, unreliable gain alone | Confirmed this was substantially a reasoning problem, not a capability-ceiling problem |
| 55 | Handed the frozen (non-agent) resolver the exact correct facts directly | Test whether the problem was *access* to facts at all | 0 of 5 fixes changed the outcome | Proved the resolver ignores even correct facts unless something *forces* their use — the key insight that led to the gate-based fix |
| **56** | Wired a hotel-ceiling fix into the guarded agent's tool, enforced by the disposition gate | Apply Exp 55's insight: enforcement, not just information | **First validated win**: 13/18 → 16/18 on the hotel subset, 0 new false approvals | Proved the gate pattern was the actual mechanism that mattered |
| 57 | Same exact fix, applied to the single-shot resolver, no gate | Isolate whether the fix or the gate was doing the work | 0 change | Direct proof: the *gate*, not the fix content, is what matters |
| 58 | Extended the pattern to mileage and software tools, full 70-case dev run | Scale the validated pattern to more categories | 55/70 → 67/70, 18/18 APPROVE recall (dev-fitted; some cases tuned directly against) | Motivated consolidating every remaining category fix into one pass |
| 59 | Consolidated every fix: hotel, meal, mileage, software, airfare, training, evidence-consistency, gift-recipient | One clean, final version of the candidate before testing it fresh | Same 67/70 dev result; 3 real failures remain, disclosed rather than hidden | Cleared to test on data this exact design had never seen |
| **60** | **Fresh, independently-labeled 50-case holdout**, never seen by either architecture | The only way to trust a result is to test it on data it couldn't have been tuned against | **Candidate: 34/50 (68%), 0/30 false approvals** — matched the frozen design's safety bar at roughly double its accuracy (22/50) and recovered real APPROVE recall (0/20 → 12/20). A stronger model (gpt-4o) hit 78% but introduced 2 false approvals (6.7%) | Strong evidence the fix generalizes — but not formally pre-registered, which is exactly what Exp 61 was built to address |

A correction made transparently during Exp 60: the first pass flagged 2 false approvals; one turned out to
be a bug in the test-generation reference tool itself, not a real system failure — corrected and documented
rather than silently dropped. Full detail: [`docs/exp53_approve_calibration.md`](exp53_approve_calibration.md)
through [`docs/exp60_fresh_holdout.md`](exp60_fresh_holdout.md).

## Part 5 — a pre-registered second holdout, "Selective Automation V3" (Exp 61)

| # | Description | Why it was carried out | What was inferred | What it means going forward |
|---|---|---|---|---|
| **61** | A second, independent 30-case holdout, with the exact candidate architecture named and frozen in a committed manifest **before** a single case was generated | Exp 60 was honest but not formally pre-registered — this closes that gap, at rigor closer to Exp 32's own | **Frozen resolver: 11/30 (36.7%), 0/15 false approvals** (same never-correctly-approves pattern). **Candidate: 20/30 (66.7%), 9/15 APPROVE recall, but 1/15 false approvals (6.7% FAR)** — the candidate's first observed false approval on fresh data, a gift-form text-parsing gap, diagnosed live and disclosed, not patched and silently rerun | Combined across Exp 60 + 61, the candidate's real observed FAR is ~2.2% (1/45), not 0% — this is the actual reason it isn't promoted to official status: not a lack of accuracy, a lack of a frozen, authorized final test at Exp 32's own scale |

Full detail: [`docs/exp61_v3_holdout.md`](exp61_v3_holdout.md). Standardized master comparison table (every
architecture, every column, every number traced to a `summary.json` file):
[`docs/master_comparison.md`](master_comparison.md).
