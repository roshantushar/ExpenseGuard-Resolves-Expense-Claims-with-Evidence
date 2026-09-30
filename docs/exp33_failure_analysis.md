# Exp 33 — Failure analysis of the frozen final test

## Hypothesis / question
Given Exp 32's frozen final-test result (30/50 correct, 0 false approvals, APPROVE recall 0.00),
classify each of the 20 errors into a primary failure category — routing/conclusiveness, retrieval/
evidence missing, resolved-fact error, policy reasoning/composition, over-conservative bias, missed
escalation, missing-information confusion, or other — and specifically explain why every one of the
13 APPROVE-expected cases came back wrong.

## Constraints honored
This is diagnostic only. No code, prompt, retriever, routing, or tool logic was changed. No case was
rerun and no frozen number from Exp 32 was altered. Two things were reconstructed **read-only, with
no LLM call**, purely to see what evidence each residual case was actually shown: the RAG context
(same frozen retriever code + already-cached embeddings) and the resolved-fact block (same
`hybrid_facts.py`, deterministic given the claim + enterprise tables). Neither of these reconstructions
can change a decision — they only recover intermediate artifacts that were computed in-memory during
the frozen run and never persisted, other than the model's final `explanation`, which was already
logged verbatim to `results/run_log.jsonl` during the Exp 32 run itself.

## Method
All 20 errors occur on the `llm_residual` path (deterministic path was 22/22 = 100%). Each error was
read manually against its logged explanation, the resolved facts, and the retrieved excerpts, and
assigned one primary category — a judgement classification, disclosed as such (Exp 19 showed a
keyword-based classifier can silently mislabel cases; this analysis avoids that failure mode by
reading each case directly instead of pattern-matching on text).

Full per-case classification: `results/current/final_test/exp33_failure_analysis/failure_classification.csv`.
Notebook: `notebooks/exp33_failure_analysis.ipynb`. Plot:
`results/current/plots/exp33_failure_categories.png`.

## Results

### Primary category counts (n = 20)
| Category | Count |
|---|---|
| Policy reasoning/composition error | 7 |
| Missing-information confusion | 5 |
| Resolved-fact error | 4 |
| Missed escalation | 2 |
| Over-conservative bias | 2 |
| Routing/conclusiveness error | 0 |
| Retrieval/evidence missing | 0 |
| Other | 0 |

Retrieval itself was not the problem on this run: in every residual case inspected, the relevant
policy clause was present somewhere in the top-K excerpts (verified directly for the alcohol-clause
case, X2-114). The gaps are downstream of retrieval — in resolved-fact coverage and in how the LLM
uses the facts and clauses it was given.

### Why every APPROVE case (13/13) failed
All 13 APPROVE-gold cases were on the residual path — none were deterministic, so the hardest class of
decision was entirely delegated to the weakest component.

| Sub-cause | Count (of 13) |
|---|---|
| Demanded evidence not required by policy | 4 |
| Arithmetic/computation error | 3 |
| Ignored a positive resolved fact | 2 |
| Missing evidence that was actually available | 2 |
| Interpreted ambiguity conservatively | 2 |

Representative findings:
- **X2-002 / X2-042** — given a compliant `nightly_rate` fact, the model compared the multi-night
  *total* against the *per-night* ceiling instead, rejecting a compliant hotel claim (X2-042's
  explanation even states a number, 338, below the ceiling it quotes, 390, and rejects anyway).
- **X2-070 / X2-127** — plain numeric/date errors: "25,000 exceeds 45,000" and "30 days is less than
  14 days" are both false on their face.
- **X2-056 / X2-075 / X2-079** — the model asked for a per-person amount on software, telecom, and a
  single-rider taxi claim, none of which need one; `resolver.NEEDED`'s per-category required-field
  list exists for routing but is not used to bound what the LLM may request.
- **X2-025 / X2-062 / X2-137** — a case-family-specific fact (a per-hotel ceiling override, whether a
  COMBINED_SPEND approval type is valid, an active-project-record check for CIRC-26-02) is not
  computed by `hybrid_facts.py`/`tools.py` at all, so the model argued from an incomplete fact block
  and, without evidence either way, defaulted to the negative outcome.

### Dev vs. final residual accuracy
| Path | Correct/N | Accuracy |
|---|---|---|
| Deterministic (final test) | 22/22 | 100% |
| LLM-residual (final test) | 8/28 | 28.6% |
| LLM-residual (dev, Exp 30) | 13/36 | 36.1% |

The deterministic half generalized perfectly to unseen data. Residual-path accuracy was already the
weakest link on dev and degraded further on final test, and APPROVE recall collapsed to exactly zero.

### Prioritization
| Failure source | Count | Fix direction |
|---|---|---|
| Conservative/incorrect LLM policy reasoning (incl. arithmetic, over-conservative bias) | 9 | Better residual prompt/model: forbid re-deriving numbers already given as facts |
| Missing-info confusion | 5 | Bound REQUEST_INFORMATION to each category's `resolver.NEEDED` field list |
| Resolved-fact/evidence gaps | 4 | Add the CIRC-26-02 active-project-record fact; fix `validate_approval`'s COMBINED_SPEND type match |
| Escalation logic | 2 | Same root cause as above; once resolved, route "policy requires a fact that cannot be resolved" straight to ESCALATE by default |
| Routing/conclusiveness | 0 | No evidence of a routing problem — not a priority |

## Decision
No change was made to `src/resolver.py`, `src/tools.py`, `src/hybrid_facts.py`, or any prompt in this
session — the frozen Exp 32 result stands exactly as run. The four fix directions above are documented
as candidates for a future, newly-versioned experiment (not a rerun or a retroactive patch to Exp 32),
should the project continue past this frozen benchmark.
