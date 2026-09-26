# ExpenseGuard V2 Dataset Package

Start with `DATASET_CARD.md`. Layout: `01_policy_corpus/` (22 documents as markdown plus one PDF), `02_cases/` (150 claims and frozen splits), `03_enterprise_data/` (11 read-only tables), `04_ground_truth_PRIVATE/` (evaluator only), `05_generation/`, `06_docs/` (validation and retrieval-difficulty reports).
Rebuild: `python -m dataset_v2.build` (deterministic, seed 6202; corpus prose is frozen in `dataset_v2/commentary_cache.json`), then `python -m dataset_v2.validate` and `python -m dataset_v2.measure_retrieval`.
Never expose `04_ground_truth_PRIVATE/` to a model, an index or a runtime tool.
