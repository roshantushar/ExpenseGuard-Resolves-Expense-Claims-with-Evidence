# Exp 38 — $0 trace audit: when agentic RAG collapses to single-shot RAG

**Cost: $0.** Pure analysis of already-saved trace data from Exp 34
(`results/v2/development/exp34_agentic_rag/agent_traces.json`) — no new LLM calls. Prompted by a direct
methodological gap: Exp 34/35/36/37 all measured end-to-end decision correctness only, and never
independently checked whether the agent's own `search_policy_corpus` calls retrieved the right evidence.
This audit does that, and corrects an overstated earlier claim ("retrieval isn't the bottleneck") that
was based on a single anecdotal check (X2-005), not a systematic one.

## The 13-case recall table

| Case | Case family | # searches | Required clauses | Found in retrieval | Recall | Decision correct |
|---|---|---|---|---|---|---|
| X2-005 | DYNAMIC_HOTEL_DISCOVERY | 1 | 5 | 3 | 0.60 | No |
| X2-018 | DYNAMIC_DELEGATION_CHAIN | 1 | 4 | 0 | **0.00** | No |
| X2-032 | DYNAMIC_DELEGATION_CHAIN | 1 | 4 | 0 | **0.00** | Yes* |
| X2-037 | DYNAMIC_PROJECT_BUDGET_CHAIN | 1 | 5 | 1 | 0.20 | No |
| X2-047 | DYNAMIC_DELEGATION_CHAIN | 1 | 3 | 0 | **0.00** | No |
| X2-055 | DYNAMIC_DELEGATION_CHAIN | 1 | 3 | 0 | **0.00** | No |
| X2-087 | DYNAMIC_HOTEL_DISCOVERY | 1 | 7 | 4 | 0.57 | No |
| X2-089 | DYNAMIC_DEEP_HOTEL_CHAIN | 1 | 7 | 3 | 0.43 | Yes |
| X2-095 | DYNAMIC_DEEP_HOTEL_CHAIN | 1 | 5 | 4 | 0.80 | Yes |
| X2-104 | DYNAMIC_HOTEL_DISCOVERY | 1 | 5 | 3 | 0.60 | Yes |
| X2-128 | DYNAMIC_HOTEL_DISCOVERY | 1 | 5 | 3 | 0.60 | No |
| X2-142 | DYNAMIC_HOTEL_DISCOVERY | 1 | 7 | 4 | 0.57 | No |
| X2-145 | DYNAMIC_DELEGATION_CHAIN | 1 | 4 | 0 | **0.00** | No |

**Mean recall: 33.6%. Zero-recall cases: 4/13 (31%), all `DYNAMIC_DELEGATION_CHAIN`. Cases that ever
issued a second search: 0/13.**

*X2-032 is flagged explicitly: 0.0 recall but a correct decision. The correct ESCALATE was reached
without the retrieved text ever containing a required clause — an **ungrounded lucky pass**, not a
case where retrieval-then-reasoning worked. Counting it as a genuine success overstates the system;
the honest grounded accuracy for Exp 34 is **3/13**, not 4/13.

## Root cause, verified directly (not inferred)

The four zero-recall cases are all `DYNAMIC_DELEGATION_CHAIN`: the claim is a meal expense, but the
actual controlling question is whether the delegated approval is valid (`APR-1.1`, `APR-4.1/.2`, or a
circular like `CIRC-25-07`). In every one of the four cases, the agent searched using the claim's
*surface topic*, not the *actual compliance question*:

```
X2-018, X2-055 -> query "meal reimbursement policy", doc_category="meals"
X2-047, X2-145 -> query "meal expense reimbursement", doc_category="meals"
```

I verified this is a **ranking failure, not a masking failure**: `approval`/`exceptions`/`circular` are
already crosscut categories in the M4 mask (`src/agent_tools.py`'s `CROSSCUT` set) and pass regardless
of `doc_category`. Re-running the exact failing query with the category filter removed entirely still
does not surface `APR-1.1` in the top 8 results — the dense embedding of "meal reimbursement policy"
is simply too far from the approval/delegation chunks. The doc_category argument was never the
bottleneck; the query text was.

**The second, independent finding: the agent never re-queries.** Every one of the 13 cases issued
exactly one `search_policy_corpus` call, despite the system prompt explicitly instructing it to look up
a further clause an observation points to. The "agentic" part of agentic RAG — deciding to search
again — never engaged in this run at all. Functionally, Exp 34's RAG was single-shot RAG with extra
steps.

## Decision
This corrects the record from Exp 33/34/37: retrieval quality **is** a real, measurable contributor to
the agent's poor performance for a third of these cases, driven by weak self-formed queries and a
complete absence of re-querying — not just by downstream reasoning failure as previously claimed. Both
causes are real and independent; see Exp 39 for a targeted fix and whether closing the retrieval gap
alone is sufficient to fix accuracy.
