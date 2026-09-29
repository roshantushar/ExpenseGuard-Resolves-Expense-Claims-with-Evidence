import React from "react";

const LAYERS = [
  { layer: "UI / interface", choice: "Own", tech: "React + Vite frontend, stdlib-only Python backend", reason: "Needs to expose this project's own trace format and disposition gate — no off-the-shelf tool understands those concepts." },
  { layer: "Orchestration", choice: "Own", tech: "Hand-written bounded ReAct loop (src/agent.py)", reason: "The guardrails (step cap, dedup, disposition gate, domain guards) ARE the research contribution — a framework would hide the mechanism being measured." },
  { layer: "LLM", choice: "Rent", tech: "openai/gpt-4o-mini (paid) · llama3.2:3b via Ollama (free)", reason: "Commodity capability; benchmarked, not the bottleneck (Exp 35B, 46 both show a bigger model doesn't fix reasoning failures)." },
  { layer: "Embedding model", choice: "Rent", tech: "voyageai/voyage-4-lite (frozen, Exp 8)", reason: "Benchmarked against alternatives; training a custom embedder is unjustified at this corpus size." },
  { layer: "Retrieval / index", choice: "Own", tech: "In-repo chunking + retrieval, no vector DB", reason: "22-document corpus is small enough that a full vector-DB service is unnecessary; the tuned config itself (K, chunking, filter) is the artifact." },
  { layer: "Policy logic", choice: "Own", tech: "rules_v2.py, rules_text.py, hybrid_facts.py, workflow_v2.py", reason: "Company-specific mechanics no vendor product encodes; this is most of what the project measured." },
  { layer: "Enterprise-data layer", choice: "Own (synthetic)", tech: "Typed read-only tools over synthetic fixtures", reason: "A reproducible, privacy-safe stand-in for a real ERP/HR/travel integration; explicit scope choice, not a placeholder." },
  { layer: "Evaluation harness", choice: "Own", tech: "evaluate.py, metrics.py, freeze-manifest process", reason: "The project's credibility rests on this — leakage isolation, one-shot held-out discipline, standardized FAR/safe-automation metrics." },
  { layer: "Observability", choice: "Own", tech: "run_log.jsonl, per-experiment summary.json, full agent traces", reason: "Purpose-built for this project's disposition-gate and domain-guard auditability requirement." },
];

const CONFIG = [
  { k: "Retrieval — chunking", v: "600 tokens / 100 overlap (Exp 6)" },
  { k: "Retrieval — top-K", v: "K = 8 (Exp 7)" },
  { k: "Retrieval — retriever", v: "Dense, voyageai/voyage-4-lite (Exp 8)" },
  { k: "Retrieval — metadata filter", v: "M4: date + region + document-type compatibility (Exp 9)" },
  { k: "Frozen residual model", v: "openai/gpt-4o-mini, temperature 0" },
  { k: "Agent step cap", v: "8 turns, hard budget cap (MAX_BUDGET_USD), call de-duplication" },
  { k: "Dataset", v: "150 claims — 70 dev / 30 validation / 50 final test, seed 6202" },
];

const COST = [
  { arch: "Deterministic rules only", cost: "$0 / claim" },
  { arch: "Official frozen selective resolver (Exp 30/32)", cost: "~$0.0004–0.0005 / claim" },
  { arch: "Guarded-agent candidate (Exp 52)", cost: "~$0.0009–0.0013 / claim" },
];

export default function BuildDetails() {
  return (
    <div className="overview">
      <div className="overview-inner">
      <h1>Build vs. buy</h1>
      <p className="lede">
        Rent commodity capability (models, embeddings) where a vendor's economies of scale genuinely win and
        this project's own experiments confirm it isn't the bottleneck; own everything company-specific —
        policy logic, safety controls, the evaluation harness, and business-logic tools. Full detail:{" "}
        <code>docs/v2/build_vs_buy.md</code>.
      </p>
      <div className="build-table">
        <div className="build-row build-head">
          <div>Layer</div>
          <div>Own / Rent</div>
          <div>Technology</div>
          <div>Reason</div>
        </div>
        {LAYERS.map((l) => (
          <div className="build-row" key={l.layer}>
            <div>{l.layer}</div>
            <div>
              <span className={`chip ${l.choice.startsWith("Own") ? "chip-own" : "chip-rent"}`}>{l.choice}</span>
            </div>
            <div className="mono-cell">{l.tech}</div>
            <div>{l.reason}</div>
          </div>
        ))}
      </div>

      <h1 style={{ marginTop: 36 }}>Frozen configuration</h1>
      <p className="lede">The exact, tuned parameters the official architecture runs on — every value earned by a dedicated experiment, not guessed.</p>
      <div className="kv-grid">
        {CONFIG.map((c) => (
          <div className="kv-card" key={c.k}>
            <div className="kv-k">{c.k}</div>
            <div className="kv-v">{c.v}</div>
          </div>
        ))}
      </div>

      <h1 style={{ marginTop: 36 }}>Measured cost per claim</h1>
      <div className="kv-grid">
        {COST.map((c) => (
          <div className="kv-card" key={c.arch}>
            <div className="kv-k">{c.arch}</div>
            <div className="kv-v">{c.cost}</div>
          </div>
        ))}
      </div>
      <p className="lede" style={{ fontSize: 13 }}>
        Token cost alone doesn't decide the architecture here — a full risk-adjusted cost model including
        human-review and false-approval cost is in <code>docs/v2/cost_and_business_impact.md</code>, and it
        reverses the "cheaper per token" ranking once escalation volume is included.
      </p>

      <h1 style={{ marginTop: 36 }}>Run it yourself</h1>
      <ul className="bullets">
        <li>Requires Python 3.9+; <code>pip install numpy matplotlib pandas</code> (plots only — the deterministic path needs nothing beyond stdlib)</li>
        <li>Copy <code>.env.example</code> to <code>.env</code>, set <code>OPENROUTER_API_KEY</code>, <code>PAID_MODEL</code>, <code>MAX_BUDGET_USD</code></li>
        <li>Everything below runs offline, at $0, except the one explicitly marked PAID</li>
      </ul>
      <div className="flow" style={{ fontSize: 12.5 }}>
{`python -m unittest discover -s tests            # $0 — 31 tests: leakage, tool, workflow
python -m dataset_v2.validate                    # $0 — 50/50 dataset integrity checks
python -m scripts.v2.exp32_final_test            # PAID — the frozen final test, already run once, do not rerun
python3 scripts/v2/cost_model.py                 # $0 — regenerates the cost/business-impact report`}
      </div>
      <p className="lede" style={{ fontSize: 13 }}>
        Full reproducibility guide and repo map: <code>docs/v2/reproducibility_and_repo_map.md</code>.
      </p>

      <h1 style={{ marginTop: 36 }}>Dataset: generation and honest limitations</h1>
      <ul className="bullets">
        <li>150 claims generated deterministically — seed 6202, <code>dataset_v2/build.py</code> — fully reproducible from scratch</li>
        <li>Free-text notes and policy prose drafted by <code>openai/gpt-4o-mini</code>, then independently re-extracted and re-verified against the hidden reference engine (blind to the hidden facts)</li>
        <li>Hardened across 3 rounds, each verified to actually remove a shortcut (Exp 2: regex-baseline accuracy fell 70/70 → 48/70 as shortcuts were removed)</li>
        <li>Ground truth physically isolated; never read by runtime code (<code>tests/test_no_leakage.py</code>)</li>
      </ul>
      <div className="callout-card">
        <div className="risk-k" style={{ marginBottom: 6 }}>What this dataset cannot prove</div>
        <ul className="bullets">
          <li>This is a controlled synthetic benchmark — results are not direct evidence of production-world performance</li>
          <li>Generated cases may inherit generator-model (gpt-4o-mini) phrasing biases and blind spots</li>
          <li>Real employee behavior and real policy ambiguity are likely more complex than the archetypes modeled here</li>
          <li>A real deployment would need a fresh, real-world validation pass before trusting these numbers to transfer</li>
        </ul>
      </div>

      <h1 style={{ marginTop: 36 }}>Intended use — and explicit non-use</h1>
      <div className="persona-grid">
        <div className="persona-card primary">
          <div className="persona-role">Intended use</div>
          <ul className="bullets">
            <li>Decision support and selective automation for a finance expense reviewer</li>
            <li>Auto-resolves what it can resolve safely; routes the rest to a human with a specific reason and the evidence already assembled</li>
          </ul>
        </div>
        <div className="persona-card">
          <div className="persona-role">Explicit non-use</div>
          <ul className="bullets">
            <li>Not an autonomous financial authority — no reimbursement is paid or executed without a human</li>
            <li>Not a fraud-accusation or employee-risk-scoring system</li>
            <li>Not a production deployment as shipped — a research/evaluation system needing a real-world validation pass first</li>
          </ul>
        </div>
      </div>
      </div>
    </div>
  );
}
