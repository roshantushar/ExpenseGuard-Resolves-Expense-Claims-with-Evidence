import React, { useState } from "react";
import TraceStep from "./TraceStep.jsx";
import PipelineDiagram from "./PipelineDiagram.jsx";

const MODELS = ["openai/gpt-4o-mini", "openai/gpt-4o"];

export default function DesignPanel({ title, subtitle, caseObj, designKey, backendDesign, precomputedNote }) {
  const [live, setLive] = useState(false);
  const [model, setModel] = useState(MODELS[0]);
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [liveResult, setLiveResult] = useState(null);
  const [error, setError] = useState(null);

  const precomputed = caseObj[designKey];
  const shown = live && liveResult ? liveResult : precomputed;
  const decision = shown?.decision;
  const correct = live && liveResult ? decision === caseObj.ground_truth.expected_decision : precomputed?.correct;

  // Derived from what the architecture actually did on this case -- never a fabricated score. "High" only
  // when either no LLM was involved (deterministic path) or a code-level gate (Exp 40/41) enforced the
  // disposition over the model's own answer; everything else is ungated LLM judgment, labeled "Lower".
  const gated = (shown?.explanation || "").includes("gate:");
  const confidence = !shown ? null
    : shown.path === "deterministic" ? { label: "High", detail: "Resolved by deterministic code — no LLM involved." }
    : gated ? { label: "High", detail: "A code-level gate enforced this disposition over the model's own answer." }
    : { label: "Lower", detail: "LLM judgment on this case — not enforced by a code-level gate." };

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
          {!live && precomputedNote && (
            <div style={{ fontSize: 11, color: "var(--warn, #d8a93b)", marginTop: 3, fontStyle: "italic" }}>{precomputedNote}</div>
          )}
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

          {confidence && (
            <div className="review-card" style={{ marginTop: 14, padding: 12, border: "1px solid var(--border, #333)", borderRadius: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <b>{decision === "ESCALATE" || decision === "REQUEST_INFORMATION" ? "Human review required" : "Automated disposition"}</b>
                <span className={`decision-pill ${confidence.label === "High" ? "APPROVE" : "REQUEST_INFORMATION"}`} title={confidence.detail}>
                  Confidence: {confidence.label}
                </span>
              </div>
              {(shown.policy_evidence || []).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-dim)", fontWeight: 700 }}>Why — policy evidence</div>
                  <ul className="bullets">{shown.policy_evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
                </div>
              )}
              {(shown.missing_fields || []).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-dim)", fontWeight: 700 }}>Missing / requested information</div>
                  <ul className="bullets">{shown.missing_fields.map((f, i) => <li key={i}>{f}</li>)}</ul>
                </div>
              )}
              {(decision === "ESCALATE" || decision === "REQUEST_INFORMATION") && (
                <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                  {["Approve", "Reject", "Request Info"].map((a) => (
                    <button key={a} className="chunk-toggle" disabled title="Illustrative only — this demo is read-only, no reviewer action is recorded">{a}</button>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div style={{ color: "var(--text-dim)", fontSize: 12.5 }}>No result for this design on this case.</div>
      )}
    </div>
  );
}
