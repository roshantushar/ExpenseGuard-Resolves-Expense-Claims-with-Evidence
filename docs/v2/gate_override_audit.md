# Disposition-gate override audit — is the guarded agent genuinely agentic?

External review raised a sharp, fair question: the disposition gate (Exp 41) lets a tool's computed answer
override the model's own decision. If that override rarely or never actually fires, the design is
deterministic logic with an LLM front end, not a genuine agentic win — precisely the "workflow mislabeled
as agent" failure mode to guard against. This audit answers it with a real, computed number, not an
estimate.

## Why this needed a fresh computation, not a lookup
The static UI export (`ui/frontend/public/data/cases.json`) never captured the agent's `explanation`
field for any non-deterministic case — a real gap in the export script, found while investigating this
question (every one of 81 exported non-deterministic cases across all three splits had `explanation: null`).
The gate's override marker text lives only in that field
(`src/agent_variants.py:gate_disposition`/`gate_approve`), so the export could not answer this question at
all. The correct fix was to re-derive the answer directly from the pipeline itself, not to guess from
incomplete exported data.

## Method
For every `DEVELOPMENT`+`VALIDATION` claim (100 total) that the deterministic layer did **not** resolve
conclusively (51 cases — verified by calling `resolver.deterministic()` directly, not assumed), re-ran
`agent.run()` with the exact same model, system prompt (`V.SYSTEM_47`), tools (`V.specs_and_tools_47`),
and step cap as the shipped `resolve_batch_v2` pipeline, captured the **pre-gate** decision, then applied
`V.gate_disposition(V.gate_approve(...))` and captured the **post-gate** decision. Every call replayed from
the existing on-disk cache — **verified $0 marginal cost** (`llm.spent()` identical before and after,
`$4.6490` both times).

## Result

| | Count |
|---|---|
| Residual (non-conclusive) dev+validation claims | 51 |
| Gate actually changed the decision | **2 (3.9%)** |
| Gate mechanism used in both cases | `gate_approve` (Exp 40) — model wanted to APPROVE, a tool signal said otherwise |
| `gate_disposition`'s full-override or conflicting-disposition paths (Exp 41) | 0 |

The two cases where it fired:

| Case | Pre-gate (model's own answer) | Post-gate (shipped decision) | Ground truth | Gate's call correct? |
|---|---|---|---|---|
| `X2-005` | APPROVE | REQUEST_INFORMATION | REQUEST_INFORMATION | **Yes — exact match** |
| `X2-034` | APPROVE | ESCALATE | ESCALATE | **Yes — exact match** |

## Reading this honestly
**The override is rare — 3.9%, not "most of the work."** The reviewer's underlying concern is legitimate:
the bulk of the guarded design's accuracy and safety comes from the tools computing a disposition the model
*agrees with* on its own (through dynamic tool orchestration — a genuinely different tool sequence is
called depending on claim content, verified per-case in this project's UI), not from the gate overruling
the model. That part of the system is closer to workflow-plus-verification than to autonomous agentic
judgment, and this project's docs should not imply otherwise.

**But the override is not zero, and both times it fired, it was the entire reason the design's FAR stayed
at 0% instead of rising to 2/51 ≈ 3.9%.** Both overridden cases were a model-attempted APPROVE that would
have been a false approval; both post-gate decisions exactly match ground truth. Removing the gate would
not have improved accuracy elsewhere (nothing else changes) — it would have specifically reopened these
two false approvals. The gate is a narrow, rarely-triggered, but load-bearing safety backstop, not the
primary source of the design's accuracy.

## Correct framing going forward
Replace any language implying the guarded agent's safety comes from sophisticated agentic self-correction
with: **the guarded agent's tool orchestration is genuinely dynamic (different tools called per case,
depending on claim content), but its 0% observed FAR rests on a narrow, deterministic gate that overrides
the model in a small minority of cases (3.9% here) — and both known instances of that override were
correct, necessary interventions, not false positives.** This is a real, verified, agentic *and*
deterministic hybrid — not one masquerading as the other — and it should be described as exactly that:
dynamic orchestration for evidence-gathering and disposition computation, with a deterministic backstop for
the narrow set of cases where the model's own final answer would have been unsafe.
