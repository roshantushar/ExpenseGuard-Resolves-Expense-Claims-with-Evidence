# ExpenseGuard — Resolves Expense Claims with Evidence

An employee expense claim (a bill + a free-text note, nothing else structured) has to be decided as
**APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE**, using a 22-document policy corpus, 11 enterprise
tables, and the note itself — deliberately hardened so decision-critical facts (nights, attendee counts,
exception references, even the expense category) live only in prose, sometimes beside a sentence that
states something else. This project experimentally finds the architecture that gets this right, safely.

**Frozen result (one-shot final test, 50 claims):** selective resolver (deterministic rules, code
decides when it can, an LLM only for the residual cases) — **30/50 correct (60%), 0% false approvals.**
The single-shot LLM step it falls back to is the one weak component (28.6% accurate on its own), and
most of this project's later experiments exist to diagnose and fix exactly that.

**Best validated design (not yet frozen):** the same routing, but the residual step is a bounded agent
using tools that compute the policy disposition in code instead of asking the model to judge it —
**44/70 dev (62.9%) and 21/30 validation (70.0%), 0% false approvals on both.** Full diagnostic story,
every experiment, and the flowchart of how this was found: [docs/v2/README.md](docs/v2/README.md).

## Layout
- `ExpenseGuard_V2_DATASET/` the dataset: 150 claims (70 dev / 30 validation / 50 final test), 22 policy
  documents, 11 enterprise tables; `04_ground_truth_PRIVATE/` is evaluator-only, never read at runtime
- `src/` runtime code — deterministic rules (`rules_v2`, `rules_text`), typed enterprise tools (`tools`),
  the fixed workflow (`workflow_v2`), the selective resolver (`resolver`), the bounded agent and its
  guarded tools (`agent`, `agent_tools`, `agent_variants`), retrieval (`retrieval`, `retrievers`,
  `embed`, `chunking`), and evaluator code (`evaluate`, `metrics`, `metrics_ext`) used only after a run
- `dataset_v2/` the dataset generator (policy text, case archetypes, the semantic hardening layer,
  validation)
- `scripts/v2/` one script per experiment; `notebooks/v2/` the same experiments as notebooks
- `tests/` unit tests, including leakage checks (`test_no_leakage.py`) that enforce ground truth is only
  ever joined in the evaluator, never read by runtime code
- `experiments/` the freeze manifest for the frozen final test
- `results/v2/` predictions, metrics, plots, cached embeddings; `results/run_log.jsonl` and
  `results/cache/` are the single shared LLM call log and cache
- `docs/v2/` one write-up per experiment (hypothesis → method → result → decision), indexed in
  [docs/v2/README.md](docs/v2/README.md)

## Setup
Python 3.9+, `numpy`, `matplotlib`, `pandas` (plots only). Copy `.env.example` to `.env` and set
`OPENROUTER_API_KEY`, `PAID_MODEL` (`openai/gpt-4o-mini`), `LOCAL_MODEL` (Ollama `llama3.2:3b`,
optional), and `MAX_BUDGET_USD`. LLM calls and embeddings are cached in `results/cache/`; the
deterministic path needs no key at all.

## Run
```
python -m unittest discover -s tests            # leakage, tool and workflow checks
python -m dataset_v2.validate                    # dataset integrity audit
python -m scripts.v2.exp00_validate              # dataset validation + leakage audit (script form)
python -m scripts.v2.exp32_final_test            # the frozen final test — already run once; do not rerun
```
Most experiments (the RAG ladder, the selective resolver, the agent diagnostics) were run as notebooks
under `notebooks/v2/`, one per experiment, each executed top to bottom with its own saved results under
`results/v2/`. `src/resolver.py` (`resolve_batch`/`resolve_batch_v2`) and `src/agent.py`/
`src/agent_variants.py` are the importable pipelines those notebooks and `exp32_final_test.py` build on.
Never read `04_ground_truth_PRIVATE/` from runtime code — `tests/test_no_leakage.py` enforces this.
