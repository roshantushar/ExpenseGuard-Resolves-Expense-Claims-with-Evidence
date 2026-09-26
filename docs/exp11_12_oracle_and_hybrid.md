# Experiments 11 and 12 — Policy oracle and RAG + deterministic logic

**Code:** `scripts/exp11_12_oracle_hybrid.py`, `src/rules.py` (`facts()`) · **Outputs:** `results/development/exp11_12/summary.json`, `results/plots/exp11_12_oracle_and_hybrid.png`, predictions under `results/{development,validation}/exp11_oracle/`, `exp12_hybrid/`, `exp12_hybrid_oracle/`
**Exp 10 (query rewriting / reranking) was skipped by agreement:** retrieval already reaches the required clauses often enough, and the LLM step is the limiting factor.
**Retriever:** dense voyage-4-lite, recursive 300/50, K = 3, metadata filter. Both LLMs, development (60) and validation (20).

## What was run
- **Exp 11 — policy oracle:** the evaluator supplies the exact required clauses instead of retrieved ones. Evaluation-only; never a runtime path.
- **Exp 12 — RAG + deterministic logic:** retrieved excerpts plus a "verified calculations" block computed by code from the claim and enterprise records: FX conversion, per-person spend against employee and client ceilings, submission age against the year's window, hotel ceiling by grade and location, exact duplicate lookup, approval threshold crossed and approval-record presence. Semantic judgments (client vs employee meal, description specificity, conflict, applicability) stay with the model.
- **Upper bound:** oracle clauses + code facts.

## Results (correct / n; false approvals among non-approvable)
| Variant | gpt-4o-mini dev | val | llama dev | val | FA dev gpt / llama | gpt input tokens (dev) | gpt cost (dev) |
|---|---|---|---|---|---|---|---|
| RAG, filtered (reference) | 23/60 | 2/20 | 20/60 | 7/20 | 0 / 2 of 39 | 77.0k | $0.0141 |
| Policy oracle (Exp 11) | 23/60 | 9/20 | 20/60 | 6/20 | 0 / 2 | 31.8k | $0.0071 |
| **RAG + code facts (Exp 12)** | **30/60** (Wilson 37.7–62.3%) | **10/20** | 26/60 | 9/20 | 4 / **20** | 89.5k | $0.0160 |
| Oracle + code facts (upper bound) | 30/60 | 10/20 | 26/60 | 7/20 | 2 / 10 | 44.4k | $0.0091 |
| Rules only (Exp 2, for reference) | 47/60 | not run | | | 5 of 39 | none | $0 |

Combined development + validation (n = 80): gpt-4o-mini RAG 25, oracle 32, RAG + facts 40, oracle + facts 40; llama RAG 27, oracle 26, RAG + facts 35, oracle + facts 33.

## Findings
1. **Oracle ≈ RAG, so retrieval is not the main bottleneck.** On development the oracle changes nothing (23 vs 23; 20 vs 20). On validation it helps gpt-4o-mini (9 vs 2), so retrieval costs some accuracy, but even perfect clauses leave gpt-4o-mini under 50%. The oracle uses less than half the tokens because it carries no distractors.
2. **Code-computed facts are the largest single gain**: gpt-4o-mini goes 23 → 30 of 60 (development) and 2 → 10 of 20 (validation); llama 20 → 26 and 7 → 9. Evidence-conflict and self-contained cases improve most. This matches the plan's expectation that arithmetic belongs in code.
3. **Facts made the models less conservative, which costs safety.** gpt-4o-mini false approvals rose from 0 to 4 of 39 (10.3%, just over the 10% guardrail) and llama's from 2 to 20 of 39 (llama approved 36 of 60 claims). Better arithmetic makes the model willing to approve, and it still approves cases that need escalation or missing information.
4. **Still far behind plain rules (47/60).** With oracle clauses and code facts together, gpt-4o-mini stops at 30/60: the remaining errors are judgment, not access to facts. Self-contained cases are 6–7 of 13 for the LLM against 13 of 13 for the rules. Fixed-workflow and split cases stay near zero because they need lookups the prompt does not have.
5. **Cost:** the facts add about 12k input tokens per 60 cases (+16%) and about 10% more cost than plain RAG.

## Caveats
- **Prompt sensitivity:** the reference row reuses Exp 9's filtered retrieval but with the prompt heading "POLICY EXCERPTS" instead of "RETRIEVED POLICY EXCERPTS". That wording change alone moved gpt-4o-mini development from 20 to 23 correct and validation stayed at 2. Differences of about three cases or fewer in this project are within prompt noise.
- Small samples and templated claims (58 distinct texts) make all intervals wide.
- The facts block gives the model information about the claim that is computed by code from claim and enterprise tables only; it uses no ground truth.

## Decision
Deterministic logic is worth keeping in front of the LLM, but as a **decision layer, not just advice**: the rules baseline alone beats every LLM configuration. The productive design is probably rules first, LLM for what rules cannot read (free-text semantics, ambiguous cases), with escalation as the default when the rules abstain. Next: Exp 13 to 15 (missing information, duplicates, split transactions) measure those pieces individually, then the enterprise tools and workflow (Exp 16 to 18).
