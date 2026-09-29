import React from "react";

// Every value copied verbatim from docs/v2/master_comparison.md (traced to a summary.json each). Color
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

export default function LadderChart() {
  const max = Math.max(...RUNGS.map((r) => r.acc));
  return (
    <div>
      <div className="ladder-chart">
        {RUNGS.map((r) => (
          <div className="ladder-row" key={r.name}>
            <div className="ladder-name">{r.name}</div>
            <div className="ladder-track">
              <div className="ladder-fill" style={{ width: `${(r.acc / max) * 100}%`, background: COLOR[r.status] }} />
              <span className="ladder-value">{r.acc}%</span>
            </div>
            <div className={`ladder-status ladder-status-${r.status}`}>{LABEL[r.status]}</div>
          </div>
        ))}
      </div>
      <p className="lede" style={{ fontSize: 12.5, marginTop: 14 }}>
        <b>The tallest bar (rules only, 68.6%) is not the winner.</b> It was rejected, because it also has
        the highest false-approval rate. Architecture in this project was never chosen by raw accuracy alone.
      </p>
    </div>
  );
}
