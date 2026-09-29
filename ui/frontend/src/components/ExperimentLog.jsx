import React, { useState } from "react";
import { PHASES } from "../experimentLog.js";

function ExpRow({ e }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="exp-row">
      <div className="exp-summary" onClick={() => setOpen((v) => !v)}>
        <span className="exp-toggle">{open ? "▾" : "▸"}</span>
        <span className="exp-num">Exp {e.n}</span>
        <span className="exp-title">{e.title}</span>
      </div>
      {open && (
        <div className="exp-detail">
          <div>
            <div className="risk-k">Question / hypothesis</div>
            <p>{e.q}</p>
          </div>
          <div>
            <div className="risk-k">What we found</div>
            <p>{e.found}</p>
          </div>
          <div>
            <div className="risk-k">Why we moved to the next experiment</div>
            <p>{e.next}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ExperimentLog() {
  const [openPhase, setOpenPhase] = useState(PHASES[0].name);
  return (
    <div>
      {PHASES.map((phase) => (
        <div key={phase.name} style={{ marginBottom: 18 }}>
          <div className="exp-phase-head" onClick={() => setOpenPhase(openPhase === phase.name ? null : phase.name)}>
            <span className="exp-toggle">{openPhase === phase.name ? "▾" : "▸"}</span>
            <b>{phase.name}</b> <span className="exp-phase-range">{phase.range} — {phase.experiments.length} experiments</span>
          </div>
          {openPhase === phase.name && (
            <div className="exp-list">
              {phase.experiments.map((e) => (
                <ExpRow e={e} key={e.n} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
