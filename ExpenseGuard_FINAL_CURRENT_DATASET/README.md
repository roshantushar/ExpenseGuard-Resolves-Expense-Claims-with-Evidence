# ExpenseGuard Final Dataset Package

## Start here
1. Read `DATASET_CARD.md`.
2. Read `06_docs/ExpenseGuard_FINAL_IMPLEMENTATION_AND_EXPERIMENT_PLAN.md`.
3. Run `python 05_generation/validate_dataset.py`.
4. Never expose `04_ground_truth_PRIVATE/` to the model, RAG index, or runtime tools.

## Package layout
- `01_policy_corpus/` - 38-page combined PDF + 12 source documents + metadata
- `02_cases/` - 120 structured bill + employee-description cases and frozen 60/20/40 splits
- `03_enterprise_data/` - read-only tool backends, including previous expenses and fixed FX rates
- `04_ground_truth_PRIVATE/` - expected dispositions, missing fields, duplicate/split truth, tool paths, challenge flags, guardrail cases
- `05_generation/` - validation and regeneration utilities
- `06_docs/` - implementation and experiment plan for the coding agent

Seed: 6201
