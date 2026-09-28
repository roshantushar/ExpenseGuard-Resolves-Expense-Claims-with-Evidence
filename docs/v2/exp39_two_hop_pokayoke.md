# Exp 39 — True two-hop agentic RAG + poka-yoke

Tests whether fixing Exp 38's diagnosed retrieval gap actually raises accuracy, or only fixes retrieval
itself while the downstream reasoning failures (Exp 33/36/37) remain. Code: `src/agent_variants.py`
(`make_search_policy_corpus_v2`, `_wrap_hint`, `specs_and_tools_39`). Results:
`results/v2/development/exp39_two_hop_pokayoke/`. Same 13 claims. Cost: $0.038.

**Two fixes, both applied together (this is a combined test, not a third isolated variable):**

1. **Guaranteed governance retrieval, not a category unlock.** Exp 38 showed the doc_category filter
   was never actually the blocker (approval/exceptions/circular already bypass it as crosscut
   categories) — the real problem is that a governance-relevant chunk simply never ranks for a
   surface-topic query. So `search_policy_corpus` now always runs a **second, fixed-query retrieval
   pass** ("manager approval delegation authority validity exception policy") restricted to the
   governance categories, and merges those chunks into every call's result — the agent gets governance
   content whether or not it thinks to ask for it by name.
2. **A tool-observation nudge for the genuine second hop.** `validate_approval` (when invalid or
   delegated) and `get_travel_request` (when it names an exception) now return one extra field,
   `unverified_policy_domain`, and the system prompt requires a second `search_policy_corpus` call
   whenever that field appears — a concrete trigger, not just a standing instruction to "look things up."
3. Exp 36's poka-yoke (`check_hotel_ceiling`, no model-supplied city) is retained unchanged, so the
   tier-substitution fix stays in place while these two retrieval fixes are added.

## Result

| Metric | Exp 34 (baseline) | Exp 39 |
|---|---|---|
| Correct/13 | 4 (30.8%; 3 grounded, per Exp 38) | 3 (23.1%) |
| FAR | 10.0% | 20.0% |
| Mean recall of required clauses | 33.6% | **45.4%** |
| Zero-recall cases | 4/13 | **1/13** |
| Cases issuing 2+ searches | 0/13 | **7/13** |

**The retrieval fix worked exactly as designed.** Mean recall rose from 33.6% to 45.4%, zero-recall
cases dropped from 4 to 1, and 7 of 13 cases now genuinely re-query after an `unverified_policy_domain`
hint (up from 0 ever re-querying in Exp 34) — for example X2-018 (one of Exp 38's zero-recall cases)
now issues a second search after `validate_approval` comes back invalid, specifically targeting
"delegation policy."

**Accuracy did not improve. It went down, and false approvals roughly doubled.** With better-grounded
evidence, the model still reaches the wrong disposition on most cases — for the same reasons already
documented (Exp 33/36/37): argument hallucination (X2-018 still passes `required_types=['meal']`,
lowercase, not a real approval type), and REJECT-vs-REQUEST_INFORMATION disposition confusion on a
missing exception (X2-005, again). Better retrieval gave the model more correct material to reason
over and it still reasoned its way to the wrong answer at a similar or higher rate.

## Decision
Retrieval quality and reasoning quality are confirmed as two separate, independently real problems.
Fixing the first (this experiment) measurably improved retrieval on its own terms but did not transfer
into better decisions — consistent with Exp 37's finding that even perfect policy evidence doesn't fix
the agent. Between Exp 37 (perfect evidence, non-agentic tool set) and Exp 39 (much-improved but
imperfect evidence, full agentic tool set with two hops), neither closes the gap to the fixed workflow's
7/13. The conclusion carried into every prior experiment doc stands: the bottleneck is the model's
downstream judgment and tool-argument formation, not what evidence it has in front of it, and the
selective resolver (Exp 30) remains the right architecture because it minimizes exposure to that
judgment rather than trying to perfect it.
