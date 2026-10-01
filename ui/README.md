# ExpenseGuard demo UI

A React app for browsing every one of the 150 claims and seeing exactly how the frozen system and the
best-validated guarded-agent design each processed it — full tool trace, disposition-gate overrides,
and the ground-truth answer side by side. Also supports re-running any claim **live** against either
model, on demand.

## What's precomputed vs. live
By default everything is read from `frontend/public/data/cases.json` — a static export of both designs'
full results and traces for all 150 claims, generated once (see below). This is free and instant.

Toggling **Live model** on a design panel calls a small local backend that runs the *actual* Python
code on that one claim, live, with whichever model you pick: `src/resolver.py` for the frozen design, and
the real Exp 59–61 guarded candidate (`scripts/exp60_require_tool_gate.run_candidate`, built on
`src/agent.py`) for the agent design — not an earlier, superseded tool set. This costs real money against
your `MAX_BUDGET_USD`/OpenRouter key and is off by default — nothing runs live unless you explicitly click
"Run live".

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
- This static export's own final-test column for the guarded agent is a **first-ever, demo-only** run
  against the *original* 50-case final-test split — that specific run has no freeze manifest and its
  provenance couldn't be re-established from committed scripts/logging (`docs/second_touch_disclosure.md`).
  Don't read it as a validated result. The guarded candidate's real, pre-registered evaluations are two
  separate fresh holdouts the frozen design has also been run against: `docs/exp60_fresh_holdout.md` and
  `docs/exp61_v3_holdout.md`. See `docs/README.md` for what's officially frozen.
- The backend is for local demo use only: unauthenticated (CORS restricted to `localhost`/`127.0.0.1`,
  but still no auth or rate limiting), and spends real money when you click "Run live". Run it locally and
  stop it after the demo — don't deploy it publicly as-is.
- `npm audit` in `ui/frontend/` reports 2 findings (1 moderate, 1 high) in `esbuild`/`vite`'s **dev-server
  only** path, not in the production build — `npm audit --omit=dev` (and the built `dist/`) report 0.
  Disclosed, not silently patched: the fix requires a breaking major-version Vite upgrade, out of scope for
  this project without being asked.
