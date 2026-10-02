# Cross-experiment plots

Eight plots built from real, already-saved result files — 78 `summary*.json` files across Exp 0–61
(`results/current/**/summary*.json`), the full per-call ledger (`results/run_log.jsonl`, 21,989 calls), and
the cost model's measured automation metrics (`scripts/cost_model.py`, read-only here — this script never
writes `docs/cost_and_business_impact.md`). No new LLM calls, no new computation beyond aggregation.
Regenerate anytime, $0:

```bash
python3 scripts/export_experiment_analysis_plots.py
```

All PNGs land in `results/current/plots/analysis_*.png`.

| Plot | Type | What it shows | Why it matters |
|---|---|---|---|
| `analysis_cost_per_experiment.png` | Horizontal bar | The 30 most expensive individual experiment runs, colored by split | Cost was concentrated in a handful of runs (model-comparison sweeps, the gpt-4o guarded-agent test) — most of the 78 runs cost fractions of a cent |
| `analysis_cost_vs_accuracy.png` | Bubble scatter (log-x) | Every run's cost against its accuracy, bubble size = claims evaluated | There is no clean "spend more, score more" relationship — some of the cheapest runs score as well as the most expensive ones, which is the real argument for the deterministic-first design |
| `analysis_cost_by_model.png` | Bar | Total logged cost, summed per model, across every run that used it | The explicit paid-vs-free comparison: `gpt-4o-mini` carried most of development ($1.13, 32 runs); `llama3.2:3b` ran 7 full experiments at **$0** |
| `analysis_accuracy_by_model.png` | Grouped bar | The same experiment, run with different models side by side | Shows where the free local model (`llama3.2:3b`) kept pace with paid models and where it fell behind — a per-experiment, not just aggregate, paid/free comparison |
| `analysis_latency_by_model.png` | Box plot | Spread of median per-run latency, grouped by model | `llama3.2:3b` (local inference) is both the slowest and most variable; `gemini-2.5-flash-lite` the fastest and most consistent |
| `analysis_cumulative_spend.png` | Line | Running total of real (uncached) spend across the project's full history, against the budget cap | The actual spend curve, not a single end number — shows spend was gradual except for two step jumps (the Exp 54 stronger-model test and the final cases.json regeneration) |
| `analysis_cost_breakdown_by_architecture.png` | Stacked bar | Expected cost per 1,000 claims, split into AI inference / human review / false approval / false rejection / unnecessary-info-request, per architecture (base scenario) | **The business angle on "which architecture is cheaper" and why** — the frozen resolver's $0 false-approval cost is bought with a large false-rejection cost; the guarded agent cuts total cost ~40% by recovering legitimate approvals, not by cutting corners on safety |
| `analysis_safety_vs_automation.png` | Scatter | Safe automation rate vs. human review rate, per architecture/split | The two numbers a business reviewer actually asks for: how much gets handled safely without a human, and how much still needs one. Counterintuitive real finding: the guarded agent both escalates *more* and safely-automates *more* — it converts marginal "unsafe automate" cases into "escalate" instead of silently absorbing the risk |

**One correction made building these:** `results/run_log.jsonl` logs a nominal `cost_usd` on cache hits too
(what the call would have cost, not what it did cost). The cumulative-spend plot filters those out —
summing all logged cost, cached or not, overstates real spend by roughly 2x ($14.49 vs. the real $7.6).

## Reading these alongside the README

- The headline project numbers (`60%` official accuracy, `$7.38` development spend, the Exp 60/61 candidate
  comparison) come from hand-selected, cited result files — see [`README.md`](../README.md#results) and
  [`docs/cost_and_business_impact.md`](cost_and_business_impact.md).
- These six plots are the broader view across *all* 78 logged runs, not just the frozen headline ones —
  useful for showing the shape of the whole experimental process, not just its endpoint.
