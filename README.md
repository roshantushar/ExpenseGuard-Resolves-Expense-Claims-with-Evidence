# ExpenseGuard — Resolves Expense Claims with Evidence

Decides whether an employee expense claim is ready for reimbursement (`APPROVE`, `REJECT`, `REQUEST_INFORMATION` or `ESCALATE`) and experimentally finds the cheapest sufficient architecture: rules, RAG, fixed tool workflow, or an agent.

**Result (frozen final test, 40 cases):** rules + fixed tool workflow (router) 38/40 correct (95.0%, Wilson 83.5–98.6%), 2/35 false approvals, 7.5% human review, $0 model cost. Best LLM system 25/40. No agent was justified. Full write-up: [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md); per-experiment write-ups: [docs/README.md](docs/README.md).

## Layout
- `ExpenseGuard_FINAL_CURRENT_DATASET/` synthetic dataset (120 claims, 12 policy documents, 9 enterprise tables; `04_ground_truth_PRIVATE/` is evaluator-only)
- `src/` runtime code (`rules`, `history`, `tools`, `workflow`, `router`, retrieval and LLM clients) and evaluator code (`evaluate`, `retrieval_eval`, used only after a run)
- `scripts/` one script per experiment (`exp00_...` to `exp33_...`), `tests/` unit tests, `experiments/` freeze manifest
- `results/` predictions, metrics, plots (`results/plots/`), stored embeddings, and the single log `results/run_log.jsonl`
- `docs/` documentation for every experiment

## Setup
Python 3.9+, `numpy`, `matplotlib`, `pandas` (plots only). Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`, `PAID_MODEL` (openai/gpt-4o-mini), `LOCAL_MODEL` (Ollama `llama3.2:3b`, optional) and `MAX_BUDGET_USD`. LLM calls are cached in `results/cache/`; the deterministic system needs no key.

## Run
```
python scripts/exp00_validate.py                      # dataset integrity and leakage audit
python -m unittest discover -s tests                  # 16 tests: tools, leakage, freeze checks
python scripts/exp02_rules.py                         # rules baseline (development)
python scripts/exp18_workflow.py                      # fixed workflow (development + validation)
python scripts/exp30_31_router_cost.py                # router and cost model
python scripts/exp32_final_test.py VALIDATION         # dry run of the final-test pipeline
python scripts/exp32_final_test.py FINAL_TEST --confirm-final-run   # ONCE only; verifies the freeze manifest
python scripts/exp33_failure_analysis.py              # failure categories
```
Do not read `04_ground_truth_PRIVATE/` from runtime code; `tests/test_no_leakage.py` enforces this.
