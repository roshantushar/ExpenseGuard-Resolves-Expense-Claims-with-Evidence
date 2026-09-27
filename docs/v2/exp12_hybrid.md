# V2 Exp 12 — Hybrid RAG + deterministic rules (development only)

Notebook: `notebooks/v2/exp12_hybrid.ipynb`. Code: `src/hybrid_facts.py` (facts extraction, reusing `src/rules_v2.py` and `src/rules_text.py`). Results: `results/v2/development/exp12_hybrid/`. Plot: `results/v2/plots/exp12_hybrid_ladder.png`. Cost: about $0.23. Development split only.

**Question:** can moving deterministic mechanics (arithmetic, temporal/precedence, evidence validation, duplicate/split) out of the LLM — while it still makes the final decision and writes the explanation — fix the 40/70 dev claims Exp 11 showed wrong under both RAG and the policy oracle?

**Runtime retriever:** Exp 9's M4 (raw query + metadata filter), frozen. The Exp 11 oracle is diagnostic only, never used here.

| Level | Adds | Correct/N | ESCALATE recall |
|---|---|---|---|
| H0 RAG only | — | 22/70 | 0.118 |
| H1 | arithmetic | 21/70 | 0.059 |
| H2 | + temporal/precedence | 23/70 | 0.118 |
| H3 | + evidence validation | **31/70** | **0.647** |
| H4 | + duplicate/split | **33/70** | 0.647 |
| H5 | full hybrid (= H4) | 33/70 | 0.647 |
| Oracle (diagnostic ceiling) | — | 25/70 | 0.059 |

**Findings:** H3 (evidence validation — approval/travel/exception/conference/budget validity, resolved from the real enterprise tables) is the single largest, cleanest cause of the gain, and is exactly what unblocks ESCALATE recall from near-zero to 0.647. Of the 40 RAG+oracle-resistant failures, H3/H4 recover 14 (35%): 10/17 evidence-validation cases, 3/3 arithmetic cases, but **0/19 "semantic/other" cases** — the expected boundary of what facts alone can fix. False approvals settle at 2/52 (3.8%), still under the 10% guardrail.

**The important, humbling comparison:** pure deterministic rules (Exp 2c, no LLM) still beat the best hybrid — **48/70 (69%) vs H5's 33/70 (47%).** Giving the LLM the same facts the rule engine uses, but letting it make the final call, does not reproduce the rule engine's reliability, and sometimes loses it.

**Decision:** the correct architecture is not "facts + LLM decides everything," but a resolver where deterministic code decides directly when the facts are conclusive, and only the genuinely ambiguous residual goes to the LLM — a materially different design than tested here, and the natural next step (a selective router, in the spirit of the eventual Exp 30). Validation untouched.
