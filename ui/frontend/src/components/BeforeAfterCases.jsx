import React, { useState } from "react";
import { CASES } from "../beforeAfterCases.js";

export default function BeforeAfterCases() {
  const [active, setActive] = useState(0);
  const c = CASES[active];
  return (
    <div>
      <div className="ba-tabs">
        {CASES.map((cc, i) => (
          <button key={cc.decision} className={`ba-tab decision-pill ${cc.decision} ${i === active ? "ba-tab-active" : ""}`} onClick={() => setActive(i)}>
            {cc.decision}
          </button>
        ))}
      </div>

      <div className="ba-claim">
        <div>
          <span className="rec-id">{c.caseId}</span> · {c.merchant} · {c.amount}
        </div>
        <div className="claim-note" style={{ marginTop: 8 }}>"{c.note}"</div>
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-dim)" }}>
          Ground truth: <span className={`decision-pill ${c.decision}`} style={{ fontSize: 11, padding: "2px 8px" }}>{c.decision}</span> — {c.reason} ({c.clauses.join(", ")})
        </div>
      </div>

      <div className="ba-grid">
        <div className="ba-col ba-before">
          <div className="ba-col-head">Before — manual review</div>
          <ul className="bullets">
            {c.before.map((b, i) => <li key={i}>{b}</li>)}
          </ul>
        </div>
        <div className="ba-arrow-mid">→</div>
        <div className="ba-col ba-after">
          <div className="ba-col-head">After — ExpenseGuard</div>
          <ul className="bullets">
            {c.after.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </div>
      </div>

      {c.outcome === "guarded-correct-frozen-wrong" && (
        <div className="callout-card bad" style={{ marginTop: 12 }}>
          Shown honestly, not curated away: this is the one decision type the official, shipped design
          still gets wrong on its own. The guarded-agent candidate fixes this specific case, which is
          exactly why it remains the most promising (but not yet officially adopted) direction — see the
          cost analysis for why it hasn't replaced the frozen design regardless.
        </div>
      )}
    </div>
  );
}
