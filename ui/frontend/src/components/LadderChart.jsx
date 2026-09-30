import React, { useState } from "react";
import { ARCHITECTURES, COSTS } from "../architectureData.js";

// Every value copied verbatim from docs/master_comparison.md (traced to a summary.json each). Color
// signals safety (FAR), not just accuracy — the whole point of this chart is that the tallest bar
// (rules-only, 68.6%) is the one that got rejected, because it's also the least safe.
const RUNGS = [
  { name: "Rules only", acc: 68.6, far: 11.5, status: "unsafe" },
  { name: "Fixed workflow", acc: 64.3, far: 13.5, status: "unsafe" },
  { name: "Hybrid rules+RAG", acc: 47.1, far: 3.8, status: "unsafe" },
  { name: "Policy oracle (diag.)", acc: 35.7, far: 0.0, status: "diagnostic" },
  { name: "Tuned RAG", acc: 31.4, far: 0.0, status: "safe" },
  { name: "Long context", acc: 31.4, far: 0.0, status: "safe" },
  { name: "Naive RAG", acc: 30.0, far: 0.0, status: "safe" },
  { name: "Frozen resolver — dev", acc: 61.4, far: 0.0, status: "official" },
  { name: "Frozen resolver — final test", acc: 60.0, far: 0.0, status: "official" },
  { name: "Guarded agent (candidate)", acc: 62.9, far: 0.0, status: "candidate" }
];

const COLOR = { unsafe: "var(--bad)", safe: "var(--text-dim)", diagnostic: "var(--warn)", official: "var(--good)", candidate: "var(--accent)" };
const LABEL = { unsafe: "unsafe FAR — rejected", safe: "safe, not chosen", diagnostic: "diagnostic only", official: "OFFICIAL, shipped", candidate: "best candidate, not shipped" };

function MiniFlowchart({ name }) {
  const a = ARCHITECTURES[name];
  const c = COSTS[name];
  if (!a) return null;
  return (
    <div className="mini-flow">
      <div className="mini-flow-exp">{a.exp}</div>
      <div className="mini-flow-steps">
        {a.steps.map((s, i) => (
          <React.Fragment key={i}>
            <div className="mini-flow-step">{s}</div>
            {i < a.steps.length - 1 && <div className="mini-flow-arrow">↓</div>}
          </React.Fragment>
        ))}
      </div>
      <div className="mini-flow-hp">
        <div className="risk-k">Hyperparameters &amp; design choices</div>
        <ul className="bullets">
          {a.hyperparams.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      </div>
      {c && (
        <div className="mini-flow-cost">
          <div className="risk-k">Business cost per 1,000 claims (base scenario: $35/hr reviewer, 6 min/review, $150/false approval)</div>
          <div className="cost-mini-grid">
            <div><span className="cost-mini-k">AI cost</span><span className="cost-mini-v">${c.ai.toFixed(2)}</span></div>
            <div><span className="cost-mini-k">Human review</span><span className="cost-mini-v">${c.human.toLocaleString()}</span></div>
            <div><span className="cost-mini-k">False approval</span><span className="cost-mini-v">${c.falseApproval.toLocaleString()}</span></div>
            <div className="cost-mini-total"><span className="cost-mini-k">Total</span><span className="cost-mini-v">${c.total.toLocaleString()}</span></div>
          </div>
          <div className="cost-mini-meta">Escalation rate {c.escalation} · FAR {c.far}</div>
          {(name === "Long context" || name === "Naive RAG" || name === "Policy oracle (diag.)") && (
            <div className="cost-mini-warn">Low total here comes from near-zero escalation, not from being good — raw accuracy on this rung was 30-36%. Not a real win; see docs/cost_and_business_impact.md.</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function LadderChart() {
  const [open, setOpen] = useState(null);
  const max = Math.max(...RUNGS.map((r) => r.acc));
  return (
    <div>
      <div className="ladder-chart">
        {RUNGS.map((r) => (
          <div key={r.name}>
            <div className="ladder-row clickable" onClick={() => setOpen(open === r.name ? null : r.name)}>
              <div className="ladder-name">
                <span className="ladder-caret">{open === r.name ? "▾" : "▸"}</span> {r.name}
              </div>
              <div className="ladder-track">
                <div className="ladder-fill" style={{ width: `${(r.acc / max) * 100}%`, background: COLOR[r.status] }} />
                <span className="ladder-value">{r.acc}%</span>
              </div>
              <div className={`ladder-status ladder-status-${r.status}`}>{LABEL[r.status]}</div>
            </div>
            {open === r.name && <MiniFlowchart name={r.name} />}
          </div>
        ))}
      </div>
      <p className="lede" style={{ fontSize: 12.5, marginTop: 14 }}>
        <b>The tallest bar (rules only, 68.6%) is not the winner.</b> It was rejected, because it also has
        the highest false-approval rate. Architecture in this project was never chosen by raw accuracy alone.
        Click any row for its pipeline and hyperparameters.
      </p>
    </div>
  );
}
