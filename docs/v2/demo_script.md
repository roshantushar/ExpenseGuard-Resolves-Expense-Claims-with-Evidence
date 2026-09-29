# Demo script (items 59-60)

The existing `ui/` demo supports opening any of the 150 claims and inspecting its full trace. Rather than
scrolling through experiment notebooks or the whole case list, use these four verified cases (plus one
failed-architecture example) as the actual walkthrough — each was checked against real saved
predictions/ground truth, not picked arbitrarily.

## The four cases

| # | Category | Case | Family | Ground truth | What it demonstrates |
|---|---|---|---|---|---|
| 1 | Deterministic, easy | **X2-060** | `EQUIPMENT_TIERS` | REJECT | Resolved entirely by `rules_v2`/`rules_text` — $0 cost, no LLM call, no retrieval. Shows the fast, free, 100%-on-unseen-data path that handles most of the "boring" volume. |
| 2 | RAG / evidence | **X2-006** | `DUPLICATE_CHECK` | REJECT | Resolved by the LLM-residual step using retrieved policy clauses and resolved facts (cost $0.0008). Shows why grounding in the actual corpus matters, and what a correctly-cited decision looks like. |
| 3 | Dynamic guarded-tool / agent | **X2-005** | `DYNAMIC_HOTEL_DISCOVERY` | REQUEST_INFORMATION | The case debugged across five prior agent experiments (Exp 35-40) before the guarded-tool design (Exp 43) finally got it right. Shows the disposition gate trusting a tool's computed answer over the model's own reasoning — the project's central mechanism, live. |
| 4 | Human review / escalation | **X2-059** | `SOFTWARE_APPROVAL` | ESCALATE | Correctly routed to a human reviewer by the frozen design. Shows ESCALATE as a deliberate, safe outcome — not a failure — and what a reviewer sees when a claim is handed to them. |

## One failed architecture, shown honestly (item 60)

**X2-026**, `DYNAMIC_DEEP_HOTEL_CHAIN`: gpt-4o-mini (the guarded design's normal model) got this case
correct; swapping in the stronger gpt-4o model (Exp 46) got it wrong — gpt-4o stopped after 3 turns and
concluded early instead of gathering the evidence gpt-4o-mini's run gathered before answering. This is the
concrete case behind Exp 46's headline finding: a bigger, more expensive model (30x the cost) scored worse
overall (15/19 vs. 17/19) despite matching safety (0% FAR either way) — direct, demonstrated evidence that
more model capability alone does not fix a reasoning-architecture problem. Showing this case alongside the
four above demonstrates real engineering judgment: the project didn't just report wins, it kept a
documented loss and explains why it happened.

## Why these five and not a notebook scroll
Each case above is traceable to a specific experiment's saved `predictions.jsonl`, so the walkthrough is
reproducible from files already in the repo, not curated after the fact for narrative effect. Full traces
for all five: `ui/` (open by case ID), or directly via `results/v2/development/exp30_selective_router/`,
`results/v2/development/exp43_guarded_tools_final/`, and `results/v2/development/exp46_guarded_gpt4o/`.
