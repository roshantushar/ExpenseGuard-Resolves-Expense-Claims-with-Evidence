import React, { useState } from "react";

// Every number here is copied verbatim from docs/v2/cost_and_business_impact.md (scripts/v2/cost_model.py's
// output) — not recomputed in the browser. Changing the scenario only changes which pre-computed row is
// shown; it never recalculates anything client-side.
const SCENARIOS = {
  low: {
    label: "Low — 1,000 claims/mo, $20/hr reviewer",
    rows: [
      { name: "Fixed workflow", total: 6619.05, ai: 0.0, human: 1619.05, falseApproval: 5000.0 },
      { name: "Frozen resolver (official)", total: 2493.8, ai: 0.46, human: 2493.33, falseApproval: 0.0 },
      { name: "Guarded agent (candidate)", total: 3886.99, ai: 1.27, human: 3885.71, falseApproval: 0.0 }
    ]
  },
  base: {
    label: "Base — 10,000 claims/mo, $35/hr reviewer",
    rows: [
      { name: "Fixed workflow", total: 18357.14, ai: 0.0, human: 3357.14, falseApproval: 15000.0 },
      { name: "Frozen resolver (official)", total: 5170.46, ai: 0.46, human: 5170.0, falseApproval: 0.0 },
      { name: "Guarded agent (candidate)", total: 8058.42, ai: 1.27, human: 8057.14, falseApproval: 0.0 }
    ]
  },
  high: {
    label: "High — 100,000 claims/mo, $60/hr reviewer",
    rows: [
      { name: "Fixed workflow", total: 58571.43, ai: 0.0, human: 8571.43, falseApproval: 50000.0 },
      { name: "Frozen resolver (official)", total: 13200.46, ai: 0.46, human: 13200.0, falseApproval: 0.0 },
      { name: "Guarded agent (candidate)", total: 20572.7, ai: 1.27, human: 20571.43, falseApproval: 0.0 }
    ]
  }
};

export default function CostAtScale() {
  const [scenario, setScenario] = useState("base");
  const s = SCENARIOS[scenario];
  const max = Math.max(...s.rows.map((r) => r.total));

  return (
    <div>
      <div className="scenario-toggle">
        {Object.keys(SCENARIOS).map((k) => (
          <button key={k} className={k === scenario ? "active" : ""} onClick={() => setScenario(k)}>
            {k}
          </button>
        ))}
      </div>
      <div className="scenario-label">{s.label} — expected cost per 1,000 claims</div>
      <div className="cost-bars">
        {s.rows.map((r) => (
          <div className="cost-bar-row" key={r.name}>
            <div className="cost-bar-name">{r.name}</div>
            <div className="cost-bar-track">
              <div
                className={`cost-bar-fill ${r.name.startsWith("Frozen") ? "good" : r.name.startsWith("Fixed") ? "bad" : "warn"}`}
                style={{ width: `${(r.total / max) * 100}%` }}
              />
              <span className="cost-bar-value">${r.total.toLocaleString()}</span>
            </div>
            <div className="cost-bar-breakdown">
              AI ${r.ai} · human-review ${r.human.toLocaleString()} · false-approval ${r.falseApproval.toLocaleString()}
            </div>
          </div>
        ))}
      </div>
      <ul className="bullets" style={{ marginTop: 16 }}>
        <li>Fixed workflow's low AI cost is irrelevant — false-approval cost alone dwarfs everything else at every scale</li>
        <li>The frozen resolver stays cheapest to operate at every volume tested, not just cheapest per token</li>
        <li>The guarded agent's higher escalation rate costs more in human review than it saves anywhere else</li>
      </ul>
    </div>
  );
}
