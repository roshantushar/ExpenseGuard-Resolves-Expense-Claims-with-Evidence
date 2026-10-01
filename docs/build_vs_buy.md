# Build-vs-buy

The architectural ownership argument: **rent commodity models and embeddings, own everything
company-specific** — policy mechanics, safety controls, the evaluation harness, and the business-logic
tools, none of which a vendor's general-purpose model can be trusted to get right for a specific company's
policy corpus. Synthetic enterprise fixtures are used deliberately (own, not rent) for reproducibility and
to avoid any real employee/company data risk.

| Layer | Own / rent | Actual technology | Reason |
|---|---|---|---|
| UI / interface | Own | React + Vite frontend (`ui/frontend/`), stdlib-only Python backend (`ui/backend/server.py`) | A demo/explorer over this project's own trace format and case data; no generic off-the-shelf tool exposes a tool-call trace, disposition gate, or evidence trail the way this project needs to show its own decisions. |
| Orchestration | Own | Hand-written bounded ReAct loop (`src/agent.py`), no agent framework | The loop's guardrails (step cap, call dedup, disposition gate, domain guards) are the actual research contribution of this project — renting a framework's agent loop would hide the exact mechanism being tested and measured. |
| LLM | Rent | OpenRouter-hosted `openai/gpt-4o-mini` (paid), `llama3.2:3b` via Ollama (free/local) | Foundation-model quality and cost efficiency at this scale is a commodity capability; building or fine-tuning a model is out of scope and would not change the finding that reasoning, not model choice, was the bottleneck (Exp 35B, 46). |
| Embedding model | Rent | `voyageai/voyage-4-lite` (frozen, Exp 8) | Embedding quality was benchmarked against alternatives (Exp 8) and the best available commodity option was selected; training a custom embedding model is unjustified at this corpus size. |
| Retrieval / index | Own | In-repo chunking + retrieval code (`src/retrieval.py`, `src/retrievers.py`, `src/chunking.py`), no vector database | The corpus (22+ documents) is small enough that a full vector-DB service is unnecessary complexity; the retrieval logic itself (chunking, K, metadata filter) is the tuned artifact this project's RAG-ladder experiments (Exp 5-10) produced and needed direct control over. |
| Policy logic | Own | `src/rules_v2.py`, `src/rules_text.py`, `src/hybrid_facts.py`, `src/workflow_v2.py` | This is the company-specific mechanics (ceilings, thresholds, exceptions, precedence) no vendor product encodes; it is also most of what this project measured and iterated on. Went straight to hand-written code rather than a low-code/no-code rule-builder because the policy logic needed free-text-derived facts (dates, headcounts, exception references buried in prose, not form fields), cross-table joins against the enterprise layer, and unit-testable, git-tracked, diffable logic (`tests/test_no_leakage.py` and friends) — guarantees a drag-and-drop rule tool does not give at this complexity. |
| Enterprise-data layer | Own (synthetic) | `src/tools.py` typed read-only tools over synthetic CSV/table fixtures | A synthetic, reproducible, privacy-safe stand-in for what would be a real ERP/HR/travel-system integration in production; using synthetic fixtures here is a deliberate scope choice (`problem.md` §7's exclusion of real employee data), not a placeholder for something a vendor could supply. |
| Evaluation harness | Own | `src/evaluate.py`, `src/metrics.py`, `src/metrics_ext.py`, the freeze-manifest process | The entire project's credibility rests on this harness (leakage isolation, one-shot held-out discipline, Wilson CIs, standardized FAR/safe-automation metrics) — this cannot be rented without losing control over exactly what "correct" means for this problem. |
| Logging / observability | Own | `results/run_log.jsonl` (shared LLM call log/cache), per-experiment `predictions.jsonl`/`summary.json`, full agent traces (`traces.json`) | Purpose-built for this project's specific auditability requirement (every decision's evidence trail inspectable, ground truth never read at runtime) — a generic observability vendor tool would not understand this project's disposition-gate or domain-guard concepts. |

## The pattern across every row
Every "rent" row is a commodity capability (general language understanding, general embedding quality)
where a vendor's economies of scale genuinely beat building it in-house, and where this project's own
experiments (Exp 8's retriever comparison, Exp 35B/46's model-swap tests) confirm the rented component was
not the bottleneck anyway. Every "own" row is either the actual object of this project's research (the
orchestration, the policy logic, the evaluation harness) or a safety/privacy-relevant boundary (the
synthetic enterprise-data layer) that should not be outsourced regardless of vendor convenience.
