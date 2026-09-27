# ExpenseGuard V2 — master experiment index

This is the single entry point into everything run on the V2 (semantic, round-3-hardened) dataset:
150 claims (70 dev / 30 validation / 50 final test), 22 policy documents, 11 enterprise tables.
Every experiment below has its own doc (this folder), its own notebook (`notebooks/v2/`), and its own
saved results (`results/v2/<split>/<experiment>/`) — nothing here is hand-typed, every table traces
back to a saved file. No git commit/push has been made on your behalf; the working tree is yours to
review and commit.

## How to read this
- **Dev** = tuned freely. **Validation** = touched once for confirmation, then left alone.
- **Final test** = touched exactly once, ever, under a hash-frozen manifest (Exp 32). Nothing after
  that point changed the frozen numbers.
- Cost figures are real spend from `results/run_log.jsonl`, capped by `MAX_BUDGET_USD=3.50`.

## The story, end to end

| # | Experiment | What it tested | Headline result | Doc |
|---|---|---|---|---|
| 0 | Dataset validation + EDA | Leakage/integrity audit, label/family/split balance | 0 critical errors; corpus hardened to hide facts in free text (semantic round 3) | [exp00](exp00_eda.md) |
| 1 | End-to-end sanity | 10 dev cases, policy given directly | Stale (pre-hardening); superseded by later experiments | [exp01](exp01_smallest_slice.md) |
| 2 | Deterministic rules baseline | `rules.py`/`rules_v2.py`/`rules_text.py` on 70 dev | Regex-only parsing collapses once facts move to free text — this *forced* the hardening | [exp02](exp02_rules_baseline.md) |
| 3 | Generic LLM, no policy | Claim only | Confident but unsupported answers, can't detect missing approvals | [exp03](exp03_generic_llm.md) |
| 4A/4B | Long-context feasibility + baseline | Full corpus in-context vs. RAG | Feasible but expensive ($0.77); did not beat retrieval | [exp04a](exp04a_long_context_feasibility.md) / [exp04b](exp04b_long_context_baseline.md) |
| 5 | Naive RAG | Dense, fixed chunks, top-3 | Beat no-policy, not yet rules | [exp05](exp05_naive_rag.md) |
| 6 | Chunking | 300/50 vs 600/100 vs 900/150 | **600/100 frozen** | [exp06](exp06_chunking.md) |
| 7 | Top-K | K = 1, 3, 5, 8 | **K=8 frozen** | [exp07](exp07_topk.md) |
| 8 | Retriever | BM25 vs dense vs hybrid | Dense frozen; hybrid didn't add enough to justify complexity | [exp08](exp08_retriever.md) |
| 9 | Metadata filtering | M0→M4 ablation (date/region/doc-type/category) | **M4 frozen** — biggest single retrieval-quality lever | [exp09](exp09_metadata.md) |
| 10 | Query rewriting | Rewrite vs. raw query | No benefit found; raw query kept, rewriting **not adopted** | [exp10](exp10_query_rewrite.md) |
| 11 | Policy oracle | Exact clauses supplied vs. best RAG | Split retrieval failure from reasoning failure | [exp11](exp11_oracle.md) |
| 12 | Hybrid rules + RAG | Deterministic mechanics (H1–H4) extracted, LLM decides | Motivated moving arithmetic/temporal/evidence/duplicate logic out of the LLM | [exp12](exp12_hybrid.md) |
| 12B | Deterministic-first router (probe) | Conclusive → trust rules; else → LLM | Proved the routing concept later frozen in Exp 30 | [exp12b](exp12b_resolver.md) |
| 13 | Missing-information detection | REQUEST_INFORMATION accuracy + negative controls | Qualified as a working component | [exp13](exp13_missing_info.md) |
| 14 | Duplicate detection | EXACT/POSSIBLE/LEGITIMATE/NONE classes | 4/4 on classification; no false-fraud wording | [exp14](exp14_duplicate_detection.md) |
| 15 | Split-transaction chain | Retrieval → grouping → combined amount → policy | Full chain confirmed, not just the label | [exp15](exp15_split_transaction.md) |
| 16 | Enterprise-evidence oracle | Raw records vs. pre-resolved facts | Pre-resolved facts help — motivated the typed tool layer | [exp16](exp16_enterprise_oracle.md) |
| 17 | Typed tools + unit tests | 11 read-only tools over enterprise tables | Full pass/fail matrix; `validate_approval` hardened | [exp17](exp17_tools.md) |
| 18 | Fixed workflow | Pre-declared tool sequence, no model | 45/70 (64%) — most accurate single architecture on dev | [exp18](exp18_fixed_workflow.md) |
| 19 | Agent-necessity audit | Do any cases need a model deciding what to look up? | Most "agent-candidate" cases were workflow-solvable | [exp19](exp19_agent_audit.md) |
| 20 | Bounded agent pilot | Real ReAct agent vs. fixed workflow, same cases | Agent didn't beat the workflow → **gate closed, Exp 21–27 not run** | [exp20](exp20_bounded_agent.md) |
| 28 | Guardrail suite (security) | Injection, fake authority, malformed/conflicting input | Found and fixed `validate_approval`'s conflicting-records bug; retrieval-text injection left as a documented open risk | [exp28](exp28_guardrails.md) |
| 29 | Abstention/escalation | Risk-coverage, over/under-escalation | Escalation behaviour quantified per architecture | [exp29](exp29_abstention.md) |
| 30 | **Architecture comparison + freeze** | LLM-for-all vs. fixed workflow vs. selective resolver | **Selective resolver frozen**: 0% FAR, 61% correct, 51% of claims go to the LLM | [exp30](exp30_selective_router.md) |
| 31 | Cost-to-serve | Measured $/claim + review-cost and error-cost sensitivity | $0.00043/claim blended — cost is a non-issue at any scale | [exp31](exp31_cost_to_serve.md) |
| 32 | **Frozen final test (one-shot)** | The 50 held-out claims, touched once | **30/50 (60%), 0 false approvals**, but APPROVE recall 0.00 | [exp32](exp32_final_test.md) |
| 33 | Failure analysis | Root-caused all 20 final-test errors | 9/20 LLM reasoning errors, 5/20 over-asking for info, 4/20 fact-coverage gaps, 0 routing errors | [exp33](exp33_failure_analysis.md) |

*(Exp 21–27 are intentionally absent: Exp 20's measured result closed that gate — see exp20's doc for the decision.)*

## The one-paragraph project story
Rules alone fail once facts are hidden in free text (Exp 2) — this is *why* the dataset was hardened
three times. RAG recovers most of that (Exp 5–10, converging on 600/100 chunking, K=8, dense retrieval,
M4 metadata filtering). But retrieval and even a policy oracle leave real reasoning error (Exp 11), so
deterministic mechanics were pulled out of the LLM into rules + typed tools (Exp 12, 16, 17), and a
fixed workflow using them was the single most accurate architecture (Exp 18, 64% on dev) — but with the
worst false-approval rate (13.5%). A real agent was tested and did not beat the fixed workflow
(Exp 19–20), so agent-specific work stopped there. The chosen design is a **selective resolver**:
deterministic rules handle every case they can resolve conclusively (which turned out to be **100%
accurate on final test**, unseen), and only the residual, harder cases go to an LLM — this drives false
approvals to **exactly zero** at a small accuracy cost and negligible dollar cost (Exp 30, 31). That
design was frozen under a hash-verified manifest and run once on the final 50 claims (Exp 32): 30/50
correct, 0 false approvals, but the LLM step never once correctly approved a genuinely approvable claim
(0/13). Exp 33 traces all 20 errors to the LLM-residual step specifically — mostly reasoning errors and
over-asking for unneeded information, not retrieval or routing failures — and documents concrete,
un-applied fix directions for a future iteration.

## Where to look for what
- **Architecture comparison, final numbers:** Exp 30 (dev) + Exp 32 (frozen final test).
- **Cost:** Exp 31.
- **Security:** Exp 28.
- **Why the agent path was dropped:** Exp 19 + Exp 20.
- **What to fix next, if the project continues:** Exp 33's prioritization table.
- **Freeze manifest (reproducibility guarantee for Exp 32):** `experiments/exp32_freeze_manifest_v2.yaml`.
- **All raw results:** `results/v2/<split>/<experiment>/`; nothing above is hand-typed.
