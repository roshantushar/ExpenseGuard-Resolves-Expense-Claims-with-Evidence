import React, { useState } from "react";

// search_policy_corpus's `excerpts` field is one big string: every retrieved chunk concatenated,
// each preceded by a "[doc_id | region ... | effective ...]" header. Split them back apart so the UI
// can show a clean, collapsed list instead of dumping the whole blob as raw JSON.
function parseChunks(excerpts) {
  if (typeof excerpts !== "string" || !excerpts.trim()) return [];
  return excerpts
    .split(/\n\n(?=\[)/)
    .map((block) => {
      const m = block.match(/^\[(.+?)\]\n([\s\S]*)$/);
      if (!m) return { header: "", text: block };
      return { header: m[1], text: m[2] };
    })
    .filter((c) => c.text.trim());
}

function ChunkList({ excerpts, nChunks }) {
  const [expanded, setExpanded] = useState(false);
  const chunks = parseChunks(excerpts);
  const count = nChunks ?? chunks.length;
  if (!chunks.length) return <span>{count} chunk(s) retrieved</span>;
  return (
    <div>
      <button className="chunk-toggle" onClick={() => setExpanded((v) => !v)}>
        {expanded ? "▾" : "▸"} {count} chunk{count === 1 ? "" : "s"} retrieved — {expanded ? "hide" : "show"}
      </button>
      {expanded && (
        <div className="chunk-list">
          {chunks.map((c, i) => (
            <div className="chunk-card" key={i}>
              <div className="chunk-head">{c.header || `chunk ${i + 1}`}</div>
              <div className="chunk-text">{c.text.length > 260 ? c.text.slice(0, 260) + "…" : c.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function summarizeObs(step) {
  if (step.error) return <span style={{ color: "var(--bad)" }}>error: {step.error}</span>;
  const d = step.data;
  if (d && typeof d === "object" && !Array.isArray(d)) {
    if (typeof d.excerpts === "string") {
      return <ChunkList excerpts={d.excerpts} nChunks={d.n_chunks} />;
    }
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
