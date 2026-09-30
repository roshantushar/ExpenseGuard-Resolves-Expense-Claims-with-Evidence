# Reproducibility and repository map

## Reproducibility instructions (item 48)

| Step | Command | Cost |
|---|---|---|
| Required Python version | 3.9+ (developed and tested on 3.9.6) | — |
| Install dependencies | `pip install numpy matplotlib pandas` (plots only; the deterministic path and dataset validator need no dependency beyond the standard library) | $0 |
| Environment variables | Copy `.env.example` to `.env`; set `OPENROUTER_API_KEY`, `PAID_MODEL` (`openai/gpt-4o-mini`), `LOCAL_MODEL` (`llama3.2:3b` via Ollama, optional), `MAX_BUDGET_USD` | — |
| Dataset generation (only if rebuilding from scratch) | `python -m dataset_v2.build` — deterministic, seed 6202; reproduces the exact case set. Corpus prose is cached in `dataset_v2/commentary_cache.json` and `semantic_cache.json`, so a rebuild does not redraft already-approved text. | $0 (cached) unless the cache is cleared |
| Zero-cost smoke test | `python -m unittest discover -s tests` (31 tests: leakage, tool, workflow) | $0 |
| Zero-cost dataset audit | `python -m dataset_v2.validate` (50 integrity/leakage checks) | $0 |
| Inspect saved results without rerunning APIs | Read any `results/v2/**/summary.json` or `predictions.jsonl` directly, or `docs/v2/master_comparison.md` / `docs/v2/cost_and_business_impact.md` for the pre-aggregated tables | $0 |
| Run one sample claim (deterministic path, no API call) | `python3 -c "import json; from src import resolver; cases=[json.loads(l) for l in open('ExpenseGuard_V2_DATASET/02_cases/all_cases.jsonl')]; c=next(c for c in cases if c['case_id']=='X2-005'); print(resolver.deterministic(c))"` — returns the decision dict and whether the deterministic layer resolved it conclusively | $0 |
| Run the frozen final test | `python -m scripts.v2.exp32_final_test` — **already run once; do not rerun**, per the project's held-out-runs-once rule | Paid (already spent; do not repeat) |
| Regenerate the cost/business-impact report | `python3 scripts/v2/cost_model.py` — reads saved predictions + ground truth only, writes `docs/v2/cost_and_business_impact.md` | $0 |

Expected output for the smoke test and the dataset audit is "OK" / "N/N checks passed" with no failures;
any failure there means the environment is not correctly set up (e.g. a missing dataset file) rather than
a real project regression, since both are pinned, offline, deterministic checks.

## Making the repo runnable without spending API money (item 49)

- Every experiment's saved predictions, evaluations, and summaries live under `results/v2/`; none of this
  requires an API key to read.
- The deterministic path (`src/resolver.py`'s rule layer, `src/rules_v2.py`, `src/workflow_v2.py`) makes no
  network call and costs nothing to run directly.
- `tests/` and `dataset_v2/validate` are fully offline.
- Any command that calls `src/llm.py` (directly or via `resolver`'s residual step, `agent.run`, or a
  notebook) makes a paid API call unless the exact call was already cached in `results/cache/` from a prior
  run — `scripts.v2.exp32_final_test` and any notebook under `notebooks/v2/` are the commands to be
  cautious with; everything in the table above other than those two rows is either free or already cached.

## Repository map (item 50)

| Directory | Contents |
|---|---|
| `ExpenseGuard_V2_DATASET/` | The dataset: `02_cases/` (visible claims), `04_ground_truth_PRIVATE/` (evaluator-only, never read at runtime), policy corpus and enterprise tables |
| `src/` | Runtime code: deterministic rules (`rules_v2`, `rules_text`), hybrid facts (`hybrid_facts`), typed enterprise tools (`tools`), the fixed workflow (`workflow_v2`), the selective resolver (`resolver`), the bounded agent and guarded tools (`agent`, `agent_tools`, `agent_variants`), retrieval (`retrieval`, `retrievers`, `embed`, `chunking`), and evaluator code (`evaluate`, `metrics`, `metrics_ext`) used only after a run completes |
| `dataset_v2/` | The dataset generator: policy text, case archetypes (`cases_a/b/c.py`), the semantic hardening layer (`semantic.py`), the hidden reference engine (`engine.py`), and the integrity validator (`validate.py`) |
| `scripts/v2/` | One script per experiment that needs a standalone entry point (not every experiment does — many ran as notebooks); includes `cost_model.py` |
| `notebooks/v2/` | The same experiments as notebooks, executed top to bottom, each with its own saved results |
| `tests/` | Unit tests, including `test_no_leakage.py`, which statically enforces that ground truth is only ever joined in the evaluator, never read by runtime code |
| `experiments/` | The freeze manifest (`exp32_freeze_manifest_v2.yaml`) for the one-shot official final test |
| `results/v2/` | Predictions, summaries, plots, and cached embeddings per experiment/split; `results/run_log.jsonl` and `results/cache/` are the single shared LLM call log and cache used across every experiment |
| `docs/v2/` | One write-up per experiment plus this project's cross-cutting analysis docs (master comparison, cost/business impact, Responsible AI risk table, build-vs-buy, synthetic-data provenance, this reproducibility doc), indexed in `docs/v2/README.md` |
| `archive/v1/` | The prior (V1) dataset generation's experiment plan, retained for historical evidence only — not the current dataset, banner-marked as legacy |
| `ui/` | The React + Python demo UI: `ui/frontend/` (Vite/React app), `ui/backend/` (stdlib-only Python server for live-model runs) |
| `problem.md` | Business problem, scope, design principles, and the official-vs-candidate architecture summary |
| `README.md` | Project entry point: headline result, layout, setup, and run instructions |
