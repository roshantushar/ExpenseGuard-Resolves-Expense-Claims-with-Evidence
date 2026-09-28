import React from "react";

const Box = ({ tone = "default", title, lines = [], className = "" }) => (
  <div className={`fc-box fc-${tone} ${className}`}>
    <div className="fc-box-title">{title}</div>
    {lines.map((l, i) => (
      <div className="fc-box-line" key={i}>
        {l}
      </div>
    ))}
  </div>
);

const Arrow = ({ label }) => (
  <div className="fc-arrow-col">
    <div className="fc-arrow-line" />
    <div className="fc-arrow-head" />
    {label && <div className="fc-arrow-label">{label}</div>}
  </div>
);

export default function FlowChart() {
  return (
    <div className="flowchart">
      <Box title="Employee expense claim" lines={["bill + free-text note — nothing else structured"]} />
      <Arrow />
      <Box
        tone="neutral"
        title="Deterministic resolver"
        lines={["rules_text.py parses the note", "rules_v2.py applies policy mechanics", "visible-only — never reads a label"]}
      />
      <Arrow label="conclusive? (a rule fired AND every needed field was extracted)" />

      <div className="fc-branch">
        <div className="fc-branch-col">
          <div className="fc-branch-tag fc-tag-yes">YES</div>
          <Arrow />
          <Box tone="good" title="Code decides" lines={["no LLM call · $0", "100% accurate on unseen final-test data"]} />
        </div>
        <div className="fc-branch-col">
          <div className="fc-branch-tag fc-tag-no">NO</div>
          <Arrow />
          <Box tone="neutral" title="Residual step" lines={["the hard cases — this is what most experiments in this project are about"]} />
          <Arrow />
          <div className="fc-branch">
            <div className="fc-branch-col">
              <Box
                tone="warn"
                title="Frozen design"
                lines={["M4 RAG + resolved facts", "→ single-shot LLM", "28.6% accurate on its own"]}
              />
            </div>
            <div className="fc-branch-col">
              <Box
                tone="good"
                title="Best validated design"
                lines={[
                  "bounded ReAct agent",
                  "guarded tools compute the disposition in CODE",
                  "a gate blocks the model from overriding a tool's correct answer",
                  "58–89% accurate depending on claim family"
                ]}
              />
            </div>
          </div>
        </div>
      </div>

      <Arrow />
      <Box tone="final" title="APPROVE · REJECT · REQUEST_INFORMATION · ESCALATE" />
    </div>
  );
}
