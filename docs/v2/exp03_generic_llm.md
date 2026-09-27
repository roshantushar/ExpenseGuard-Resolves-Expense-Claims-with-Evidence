# V2 Exp 3 — Generic LLM without company policy

Notebook: `notebooks/v2/exp03_generic_llm.ipynb`. Results: `results/v2/development/exp03_no_policy/` and `exp03b_no_policy_dated/`. Plots: `results/v2/plots/exp03_no_policy_development.png`, `exp03_no_policy_detail.png`, `exp03b_no_policy_dated_development.png`.

**Hypothesis:** with no policy and no records, a generic LLM gives confident but unsupported answers, collapses onto default decisions, and cannot detect missing approvals.

**Configuration:** 70 development claims of the semantic V2; claim only (bill, dates, project, note); temperature 0; models `openai/gpt-4o-mini`, `google/gemini-2.5-flash-lite` (OpenRouter) and `llama3.2:3b` (Ollama). 3b adds one sentence, "today is the submission date".

| Model | Correct/N (Wilson 95%) | False approvals | Decision mix | Cost (70 claims) |
|---|---|---|---|---|
| gpt-4o-mini | 26/70 = 37.1% (27-49%) | 0/52 | REJECT 39, RI 31 | $0.0066 |
| gemini-2.5-flash-lite | 20/70 = 28.6% (19-40%) | 0/52 | RI 62, ESC 5, REJ 3 | $0.0054 |
| llama3.2:3b | 22/70 = 31.4% (22-43%) | 11/52 | REJECT 55, APPROVE 15 | $0 |
| rules 2a / 2b / 2c (Exp 2) | 31% / 49% / 69% | 39 / 15 / 6 of 52 | | $0 |

**Findings:** all three sit at chance level (majority class 26.7%), below the improved rules. Zero clause ids are cited, but 19/70 (paid models) and 57/70 (llama) explanations assert rules or limits. Missed escalation is 88-100%. Low false-approval counts for the paid models come from never approving. gpt-4o-mini rejects many claims as "dated in the future"; telling it today's date (3b) did not help (57 "future" explanations, 20/70). Caveats: 70 claims, wide intervals, one prompt.

**Decision:** grounding is required; the no-policy rung is the floor. Next: Exp 4A/4B (long-context feasibility and baseline).
