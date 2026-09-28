# ExpenseGuard demo UI

A React app for browsing every one of the 150 claims and seeing exactly how the frozen system and the
best-validated guarded-agent design each processed it — full tool trace, disposition-gate overrides,
and the ground-truth answer side by side. Also supports re-running any claim **live** against either
model, on demand.

## What's precomputed vs. live
By default everything is read from `frontend/public/data/cases.json` — a static export of both designs'
full results and traces for all 150 claims, generated once (see below). This is free and instant.

Toggling **Live model** on a design panel calls a small local backend that runs the *actual* Python
code (`src/resolver.py`, `src/agent.py`, `src/agent_variants.py`) on that one claim, live, with whichever
model you pick. This costs real money against your `MAX_BUDGET_USD`/OpenRouter key and is off by default
— nothing runs live unless you explicitly click "Run live".

## Setup

**Backend** (from the repo root):
```
python -m ui.backend.server
```
Serves on `http://localhost:8787`. Needs your `.env` (`OPENROUTER_API_KEY`, `PAID_MODEL`,
`MAX_BUDGET_USD`) already set up as for the rest of the project.

**Frontend** (in a second terminal):
```
cd ui/frontend
npm install
npm run dev
```
Opens on `http://localhost:5173`. The dev server proxies `/api/*` to the backend on port 8787 (see
`vite.config.js`), so both need to be running for "Live model" to work — the static Overview and
Explorer tabs work fine with only the frontend running.

## Regenerating the precomputed export
If the dataset or either design's code changes, re-run both systems over all 150 claims and rebuild
`frontend/public/data/cases.json`. The export script used to produce the current file is not checked in
as a permanent script (it was a one-off session task); to redo it, adapt the pattern in
`src/resolver.py`'s `resolve_batch`/`resolve_batch_v2`, calling both over `llm_exp.cases_for(split)` for
all three splits, joining with `src/evaluate.py`'s ground truth, and writing one JSON array with each
case's claim, ground truth, and both designs' decision + trace.

## Notes
- The final-test numbers for the guarded agent are a **first-ever, demo-only** run — that design has
  never been officially evaluated against final test and has no freeze manifest. Don't read its
  final-test accuracy as a validated result; see `docs/v2/README.md` for what's actually frozen.
- The backend is for local demo use only: unauthenticated, no rate limiting, spends real money when you
  click "Run live". Don't deploy it publicly as-is.
