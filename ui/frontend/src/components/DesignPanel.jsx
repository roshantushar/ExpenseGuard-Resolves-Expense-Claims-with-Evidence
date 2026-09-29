import React, { useState } from "react";
import TraceStep from "./TraceStep.jsx";
import PipelineDiagram from "./PipelineDiagram.jsx";

const MODELS = ["openai/gpt-4o-mini", "openai/gpt-4o"];

export default function DesignPanel({ title, subtitle, caseObj, designKey, backendDesign }) {
  const [live, setLive] = useState(false);
  const [model, setModel] = useState(MODELS[0]);
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [liveResult, setLiveResult] = useState(null);
  const [error, setError] = useState(null);

  const precomputed = caseObj[designKey];
  const shown = live && liveResult ? liveResult : precomputed;
  const decision = shown?.decision;
  const correct = live && liveResult ? decision === caseObj.ground_truth.expected_decision : precomputed?.correct;

  async function runLive() {
    setStatus("running");
    setError(null);
    try {
      const r = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseObj.case_id, design: backendDesign, model })
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      setLiveResult(data);
      setStatus("done");
    } catch (e) {
      setError(String(e.message || e));
      setStatus("error");
    }
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h3>{title}</h3>
          <div style={{ fontSize: 11.5, color: "var(--text-dim)" }}>{subtitle}</div>
        </div>
        {decision && <span className={`decision-pill ${decision}`}>{decision}</span>}
      </div>

      {shown && <PipelineDiagram design={designKey} result={shown} />}

      <div className="live-panel">
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />
          Live model
        </label>
        {live && (
          <>
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              {MODELS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
            <button onClick={runLive} disabled={status === "running"}>
              {status === "running" ? "Running…" : "Run live"}
            </button>
            {status === "done" && <span className="status">✓ fresh result (${(liveResult.cost_usd ?? 0).toFixed(4)})</span>}
            {status === "error" && <span className="err">✗ {error}</span>}
            {status === "idle" && <span className="status">calls the real backend — requires `python -m ui.backend.server` running</span>}
          </>
        )}
      </div>

      {shown ? (
        <>
          {correct !== undefined && <span className={`correctness ${correct ? "ok" : "wrong"}`}>{correct ? "✓ matches ground truth" : "✗ does not match ground truth"}</span>}
          {shown.turns !== undefined && shown.turns !== null && (
            <div style={{ fontSize: 11.5, color: "var(--text-dim)", marginTop: 8 }}>{shown.turns} agent turn(s)</div>
          )}
          <div style={{ marginTop: 16 }}>
            {(shown.trace || []).length > 0 && <div className="trace-label">Live execution trace for this run</div>}
            {(shown.trace || []).length === 0 ? (
              <div style={{ fontSize: 12.5, color: "var(--text-dim)" }}>
                {shown.path === "deterministic" ? "Resolved deterministically — no LLM call, no tools." : "No tool trace for this path."}
              </div>
            ) : (
              (shown.trace || []).map((step, i) => <TraceStep key={i} step={step} i={i} />)
            )}
          </div>
          {shown.explanation && <div className="explanation">{shown.explanation}</div>}
        </>
      ) : (
        <div style={{ color: "var(--text-dim)", fontSize: 12.5 }}>No result for this design on this case.</div>
      )}
    </div>
  );
}
