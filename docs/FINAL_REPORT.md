# ExpenseGuard — final report

*Decision-flow structure, first person (individual work), ~1,200 words. Only pivotal experiments are named
here — everything else is in `docs/`, indexed at `docs/README.md`.*

## A. Problem and business value
I built ExpenseGuard to decide, for a single expense claim (a bill + a free-text note, nothing else
structured), whether it is safe to APPROVE, REJECT, REQUEST_INFORMATION, or ESCALATE — against a 22+
document policy corpus and 11 enterprise tables. I only consider this justified if it increases correct
disposition, reduces unnecessary finance review, avoids unsafe automatic approvals, and keeps cost/latency
controlled (`problem.md`) — not merely because AI can be applied. I deliberately did not begin by assuming
an agent, or even an LLM, was required.

## B. Dataset and evaluation contract
I generated 150 synthetic claims (70 development / 30 validation / 50 final test), deterministically (seed
6202, `dataset_generator/`) and hardened them across three rounds so decision-critical facts live only in free
text, never a structured field. I physically isolated ground truth (`04_ground_truth_PRIVATE/`) and
enforce with `tests/test_no_leakage.py` that runtime code never reads it. I ran the held-out final test
once, ever, against a manifest I committed before that run — full provenance in
`docs/synthetic_data_provenance.md`.

## C. Rules / LLM / RAG baselines
I found that deterministic rules alone (Exp 2) collapsed once I moved facts out of structured fields —
early failures motivated the hardening, and after hardening, regex-only extraction degraded substantially
(69%→halved across three rounds), with unsafe FAR throughout. I tested a generic LLM with no policy (Exp 3)
and long-context-with-full-corpus (Exp 4B); both plateaued around 31-37% dev accuracy, and long context
cost 40x tuned RAG for no accuracy gain — this is why I justified using RAG at all at this corpus size.

## D. Retrieval optimization and oracle diagnosis
I tuned the RAG ladder (chunking, top-K, retriever, metadata filtering — Exp 9/10) and froze it at K=8,
600/100-token chunking, dense embeddings (voyage-4-lite), and a metadata filter for date/region/document-
type compatibility. Then in Exp 11 I ran a policy oracle — handing the model the exact required clauses —
and accuracy moved only from 22 to 25/70. **I concluded retrieval was not the dominant downstream
bottleneck; oracle policy evidence produced only a modest accuracy gain.** That single finding redirected
the rest of my effort from retrieval tuning toward hybrid rules and, later, architecture.

## E. Workflow vs. agent-necessity gate
Exp 18's fixed, pre-declared tool workflow reached the highest raw dev accuracy I tested (64.3%) — but at
13.5% FAR, unsafe. Exp 19/20 then tested whether dynamic, model-directed tool choice adds real value on the
13 hardest "agent-candidate" claims: a bounded ReAct agent tied the workflow (7/13) with *complementary*,
not merely equal, errors — evidence for a selective architecture, but also that the agent alone was not yet
safe (30% FAR).

## F. Official selective architecture
I combined these findings in Exp 30: deterministic rules decide whenever a case is conclusive; an LLM
handles only the residual. This reached 0% FAR at 61.4% dev accuracy — I traded 2-3 points of raw accuracy
for eliminating false approvals versus both the fixed workflow (13.5% FAR) and an LLM-for-all baseline
(3.85% FAR). I froze `src/resolver.py` at this point.

## G. One-shot final test
I ran this frozen system once, verified against a committed hash manifest at the time it ran, against the
50-claim held-out final test (Exp 32) — *note: the dataset was regenerated once more afterward, so that
manifest's hashes no longer match the files on disk today; this result is the honest record of that one
run, not something the current dataset can still verify byte-for-byte (`docs/exp32_final_test.md`)*:
**30/50 (60%), 0/37 false approvals observed.** The deterministic path generalized perfectly (22/22, vs.
88.2% on dev — no overfitting signal); the LLM-residual path never once correctly predicted APPROVE (0/13
recall) and scored only 28.6% overall, confirming it as the one weak component I'd need to address.

## H. Failure analysis
I categorized all 20 final-test errors (Exp 33): entirely on the LLM-residual path, dominated by reasoning
failures rather than missing evidence or retrieval misses. This closed, for me, the question of whether
retrieval was ever the problem, and pointed squarely at reasoning as the remaining lever.

## I. Guarded-agent post-final research
My first full agentic-RAG rebuild (Exp 34) scored *worse* than the fixed workflow (4/13) — every attempt to
fix it by loosening constraints (stricter prompts, a stronger model, parallel tool calls) either did
nothing or made safety worse (FAR up to 50%, Exp 35B). Repeating the perfect-policy-oracle test on the
agent (Exp 37) found the same result as Exp 11: **perfect policy evidence was insufficient to resolve the
agent's decision failures, showing retrieval quality alone did not explain the problem.** Auditing the
agent's own search behavior (Exp 38-39) found its self-issued queries genuinely weak (33.6% recall) — a
real secondary retrieval problem — but fixing that alone still didn't improve final accuracy: **retrieval
and reasoning were separate failure modes.**

The fix that worked, which I built in Exp 40/41: stop asking the model to decide, give it a tool that
computes the answer in code, and gate the model so it cannot override a tool that already had the right
answer. I then added domain guards (Exp 43/44) to close cases where an ungated tool answered a question it
was never built for, reaching 17/19 (89.5%) at 0% FAR on the `C_AGENT_DYNAMIC` subset. When I extended this
to the full dataset, safety broke first (Exp 45: 11.5% FAR, every false approval in a category with no
guarded tool); I then found and fixed seven real bugs — by running the system and reading its output, not
by reasoning about the code in the abstract — to close that gap (Exp 47-52), reaching **44/70 dev and 21/30
validation, 0% observed FAR on both authorized splits, one point above the frozen design's own dev
accuracy.** *(Later disclosure: an audit found a real but unauthorized, partial run against 30 of the 50
final-test claims, scoring materially worse — 50% accuracy, 17.6% FAR — than any of the authorized numbers
above; see `docs/second_touch_disclosure.md`.)*

## J. Cost/business trade-off
This is the most important thing I found late in the project — in two parts. First, when I built a
risk-adjusted cost model (`docs/cost_and_business_impact.md`), I found the guarded candidate escalates
1.5-1.8x more often than the frozen design (34% vs. 19-22%), and human-review cost dominates every scenario
I tested — so I originally concluded its **total expected operating cost is higher than the frozen
design's at low, base, and high claim-volume scenarios**, despite its accuracy/FAR advantage, and on that
basis did not create a new held-out set for the candidate.

**Correction, found on later review:** that cost model omitted false-rejection and unnecessary-
information-request costs from the total, even though both were already defined as assumptions in the code
— an oversight, not a deliberate scoping choice. With both included, priced the same way as the
false-approval cost already in the model, the guarded candidate is cheaper than the frozen design at every
scenario scale **under development/validation rates**, because the frozen design's deterministic rules
false-reject far more often (36.8% dev / 50.0% final test vs. the candidate's 17.2% dev / 21.4% validation)
— an error mode the original model never priced.

**Second correction, found on later independent audit:** the guarded-agent candidate itself has real
execution data against 30 of the 50 final-test claims (`docs/second_touch_disclosure.md`), scoring 50%
accuracy and 17.6% FAR — materially worse than every authorized number for this design. A no-cost
sensitivity analysis (`docs/cost_and_business_impact.md`, existing data only) re-priced the cost model
using this diagnostic run's rates: **the candidate's cost advantage does not survive.** Once false
approvals are priced at meaningful business cost, degraded unseen-data safety erases the modeled
advantage.

**Resolution:** the frozen selective resolver remains the official architecture — not because it is
necessarily the cheapest in theory, but because it is the only architecture with a properly frozen,
documented evaluation contract and an official result to check against. The guarded-agent candidate is
retained as a promising but unvalidated candidate: its development/validation results and the corrected
cost model suggest it could be economically better, but the diagnostic final-run evidence is sufficient to
prevent promotion, even though it cannot itself establish the candidate's true generalization performance
(the final-test set is no longer independent, and this diagnostic run's origin could not be established
from committed scripts/logging). No new held-out set was created for the candidate — that is future work,
not a decision I am making implicitly by omission.

## K. Responsible AI and limitations
Full risk table: `docs/responsible_ai_risk_table.md`. I directly mitigated Excessive Agency (OWASP
LLM06) with read-only tools, step caps, and the disposition gate. I did **not** solve Prompt Injection
(LLM01) — Exp 28 found retrieval-text injection can still defeat my current defense, disclosed as an open
risk. I completed a full OWASP Top 10 (2025) pass (`docs/owasp_llm_top10_2025.md`); this is a controlled
synthetic benchmark, and results are not direct evidence of production performance
(`docs/synthetic_data_provenance.md`).

## L. Final conclusion
I found that reliability comes from assigning decision authority to the component best suited to each
task: deterministic, validated, domain-scoped tools for policy mechanics; retrieval and LLMs for evidence
access and interpretation; agentic autonomy only when bounded by reliable tools, applicability guards, and
human fallback. On this benchmark, I did not find unconstrained agentic decision-making justified — but I
also found determinism alone insufficient, since a deterministic tool with bad inputs (Exp 47) can
propagate errors just as confidently as a model can. **My conclusion is that enterprise AI architecture
should be selected on safe automation and total operating cost, not benchmark accuracy alone.**
