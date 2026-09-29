# ExpenseGuard V2 — Resolves Expense Claims with Evidence

An employee expense claim (a bill + a free-text note, nothing else structured) has to be decided as
**APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE**, using **150 claims** (70 development / 30
validation / 50 final test), **22+ policy documents**, and **11 enterprise tables** — the note itself
deliberately hardened so decision-critical facts (nights, attendee counts, exception references, even the
expense category) live only in prose, sometimes beside a sentence that states something else. This
project experimentally finds the architecture that gets this right, safely.

**Official architecture: Exp 30, the selective resolver** — deterministic rules decide whenever they can
(the deterministic path); an LLM handles only the residual cases it can't. **Official final evaluation:
Exp 32**, the one-shot, hash-manifest-verified run against the 50-claim held-out final test:

| Metric | Value |
|---|---|
| Correct/N | **30/50 = 60%** |
| Observed false approvals | **0/37 non-approvable cases (0% observed FAR)** |
| Deterministic path | **22/22 (100%)** |
| LLM residual path | **8/28 (28.6%)** |

The LLM-residual step is the one weak component this architecture relies on, and most of this project's
later experiments (Exp 34 onward) exist to diagnose and fix exactly that.

**Headline finding: the best-performing AI architecture was not the best operating architecture.**
ExpenseGuard found that safe automation must be judged jointly on accuracy, false approvals, escalation
burden, and total cost-to-serve — not on accuracy or FAR alone. A post-final guarded-agent candidate
(Exp 34-52) replaces the residual LLM step with a bounded agent whose tools compute the policy disposition
in code, and on the splits it has been evaluated on — 44/70 dev, 0/52 falsely approved; 21/30 validation,
0/22 falsely approved (0% observed FAR on both) — it beats the frozen architecture's own development
accuracy (43/70) by one point at matching FAR. **But it escalates 1.5-1.8x more often** (34% vs. 19-22%),
and a risk-adjusted cost model ([docs/v2/cost_and_business_impact.md](docs/v2/cost_and_business_impact.md))
finds its total expected operating cost is *higher* than the frozen design's at every scale tested (low,
base, and high claim-volume scenarios), because the added human-review load outweighs its accuracy and
AI-cost advantages. It is also a **development-and-validation-selected candidate**, not an independently
validated architecture — its design was changed in direct response to what the validation run revealed
(see the methodology note in [docs/v2/README.md](docs/v2/README.md)). **It has never been run against the
final test and carries no freeze manifest.** Given the cost finding, a new frozen holdout for this
candidate is not currently justified — see the held-out-set decision in the cost doc — so Exp 30/32 remains
the sole official result and the frozen selective resolver remains the preferred operating architecture.

Full diagnostic story, every experiment, and the flowchart of how this was found:
[docs/v2/README.md](docs/v2/README.md). Business problem and scope: [problem.md](problem.md).

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
