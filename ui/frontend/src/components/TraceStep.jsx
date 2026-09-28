import React from "react";

function summarizeObs(step) {
  if (step.error) return <span style={{ color: "var(--bad)" }}>error: {step.error}</span>;
  const d = step.data;
  if (d && typeof d === "object" && !Array.isArray(d)) {
    if (d.policy_disposition) {
      return (
        <span>
          <span className="disposition">policy_disposition: {d.policy_disposition}</span>
          {d.reason ? ` — ${d.reason}` : ""}
        </span>
      );
    }
    const entries = Object.entries(d).slice(0, 4);
    return entries.map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(", ");
  }
  if (Array.isArray(d)) return `${d.length} record(s) returned`;
  return step.found === false ? "not found" : "ok";
}

export default function TraceStep({ step, i }) {
  return (
    <div className="trace-step">
      <div className="tool">
        {i + 1}. {step.tool}
      </div>
      {step.args && Object.keys(step.args).length > 0 && <div className="args">{JSON.stringify(step.args)}</div>}
      <div className="obs">{summarizeObs(step)}</div>
    </div>
  );
}
