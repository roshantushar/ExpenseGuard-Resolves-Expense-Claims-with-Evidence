# Exp 34 — V3 pivot: agentic RAG as the primary architecture

Tests a proposed pivot to make the ReAct agent + agentic RAG the centerpiece architecture, instead of
the frozen selective resolver (Exp 30). `search_policy_corpus` (M4 retriever from Exp 5-10) becomes a
callable tool inside a bounded ReAct loop (`src/agent.py`, `src/agent_tools.py`), rather than fetched
once before the loop starts (Exp 20's design). Code: `src/agent.py`, `src/agent_tools.py`. Results:
`results/v2/development/exp34_agentic_rag/`. Same 13 `C_AGENT_DYNAMIC` development claims as Exp 18/19/20.
Cost: $0.038.

**Compared against:** `rules_v2.py` alone (non-AI baseline) and the fixed workflow (Exp 18), on the
identical 13 claims.

## Result

| System | Correct/13 | FAR | HRR |
|---|---|---|---|
| `rules_v2.py` alone | 6 (46.2%) | 30.0% | 23.1% |
| Fixed workflow (Exp 18) | **7 (53.8%)** | 10.0% | 30.8% |
| **New agent, agentic RAG (this experiment)** | 4 (30.8%) | 10.0% | 38.5% |

**The new agent is worse than the fixed workflow, and worse than Exp 20's earlier agent** (which tied
the workflow at 7/13 using pre-fetched RAG). Avg 7.3 of 8 turns used, 5/13 runs hit the step cap
outright, 15 wrong-tool-calls across 13 cases. Making RAG a callable, re-queryable tool increased
orchestration overhead without buying accuracy.

**The flagship false approval, X2-005 (Chennai):** the agent called `search_policy_corpus`, got a
ceiling number, ran it through a calculator tool instead of doing the math itself — and still used
14,500 (IN-T1's ceiling, for Mumbai/Delhi/Bengaluru) instead of the correct 9,800 (IN-T2, the true
fallback for an unlisted city). The true nightly rate is actually over the correct ceiling, which
should have triggered the exception check (already found empty) → REQUEST_INFORMATION. Instead: a real
false approval, live in the full agentic loop.

## Decision
This does not support the premise that unconstrained agentic RAG would out-perform the selective
resolver here. It reinforces Exp 19/20/28/33: the LLM step, not the orchestration pattern, is the
bottleneck, and more autonomy over retrieval gave it more rope, not more accuracy. This result opened
the diagnostic line of work continued through Exp 35-46 (isolating exactly which layer — prompt, model,
tool interface, retrieval — could fix it, and ultimately finding that only moving the decision into
code, Exp 40-44, did).
