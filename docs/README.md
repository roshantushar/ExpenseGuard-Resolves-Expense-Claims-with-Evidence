# Project documentation

One file per experiment: hypothesis, frozen config, results, plots, failures, decision.

| Exp | Doc | Status |
|---|---|---|
| 0 | [exp00_dataset_validation.md](exp00_dataset_validation.md) | done |
| 1 | [exp01_smallest_slice.md](exp01_smallest_slice.md) | done |
| 2 | [exp02_rules_baseline.md](exp02_rules_baseline.md) | done (development) |
| 3 | [exp03_generic_llm_no_policy.md](exp03_generic_llm_no_policy.md) | done (development) |
| 4 | [exp04_full_policy_long_context.md](exp04_full_policy_long_context.md) | done (development + validation) |
| 5 | [exp05_naive_rag_and_embeddings.md](exp05_naive_rag_and_embeddings.md) | done (development + validation) |
| 6 | [exp06_chunking_recursive.md](exp06_chunking_recursive.md) | done (development + validation) |
| 7 | [exp07_topk.md](exp07_topk.md) | done (development + validation) |
| 8, 9 | [exp08_09_retrievers_and_metadata.md](exp08_09_retrievers_and_metadata.md) | done (development + validation) |
| 10 | skipped by agreement (see exp11_12 doc) | skipped |
| 11, 12 | [exp11_12_oracle_and_hybrid.md](exp11_12_oracle_and_hybrid.md) | done (development + validation) |
| 13, 14, 15 | [exp13_14_15_missing_duplicates_splits.md](exp13_14_15_missing_duplicates_splits.md) | done (development + validation) |
| 16 | [exp16_enterprise_oracle.md](exp16_enterprise_oracle.md) | done (development + validation) |
| 17 | [exp17_typed_tools.md](exp17_typed_tools.md) | done (10 unit tests pass) |
| 18 | [exp18_fixed_workflow.md](exp18_fixed_workflow.md) | done (development + validation) |
| 19 | [exp19_agent_necessity_audit.md](exp19_agent_necessity_audit.md) | done: agent not justified |
| 20-27 | not run (conditional on Exp 19) | skipped by the plan's gate |
| 28 | [exp28_guardrails.md](exp28_guardrails.md) | done: 15/15 system, LLM 3/4 |
| 29 | [exp29_abstention_escalation.md](exp29_abstention_escalation.md) | done |
| 30, 31 | [exp30_31_router_and_cost.md](exp30_31_router_and_cost.md) | done |
| 32 | [exp32_freeze_and_runbook.md](exp32_freeze_and_runbook.md) | frozen, NOT yet run |
| 33 | pending (needs the final run) | pending |

Model plan: OpenRouter paid model (GPT-mini class) for initial experiments, compared against a free/local model (Ollama `llama3.2:3b`). Every experiment reports cost, latency and tokens with plots in `results/plots/`.

## Run log
`results/run_log.jsonl` is the single log. Row types: `llm_call` (tokens in/out, cost, latency, cached), `case_result` (prediction per case), `evaluation` (ground-truth join, written after the run), `experiment_summary`. Rows from Exp 2 onward carry `run_id` and `split`.
