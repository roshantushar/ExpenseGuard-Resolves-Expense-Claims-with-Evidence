import React, { useState } from "react";

// Condensed from docs/v2/responsible_ai_risk_table.md — same 14 risks, same substance, shortened to
// scannable bullets per cell instead of full sentences. Expand a row for the full mitigation detail.
const RISKS = [
  { risk: "False approval", failure: "A claim that should be rejected/escalated is auto-approved.", mitigation: ["Selective architecture routes the LLM only to non-conclusive cases", "0/37 observed on official final test; 0/52, 0/22 on candidate dev/validation"], residual: "Observed 0% on tested populations — not a guarantee for unseen distributions or higher volume.", human: "ESCALATE is first-class; unresolved claims route to a human, never auto-approved." },
  { risk: "Unsupported rejection", failure: "A legitimate claim is rejected without real policy basis.", mitigation: ["Decisions require policy_evidence", "Exp 33 tracks over-rejection as its own error class"], residual: "Not eliminated — REJECT recall was 0.92; citation correctness wasn't adversarially tested.", human: "Stated evidence is inspectable; REQUEST_INFORMATION exists as a softer alternative." },
  { risk: "Missing evidence", failure: "System decides confidently despite lacking a required fact.", mitigation: ["REQUEST_INFORMATION is first-class, names missing fields", "H1–H4 hybrid-facts extraction (Exp 12)"], residual: "Missing-field precision/recall not comprehensively measured across the full dataset.", human: "Reviewer sees exactly which fields were flagged, supplies them directly." },
  { risk: "Conflicting enterprise records", failure: "Two records disagree and the system silently picks one.", mitigation: ["Exp 28→30: validate_approval detects >1 disagreeing record → CONFLICTING_RECORDS → ESCALATE"], residual: "Fixed only for the one case class found; other tables not exhaustively tested.", human: "Conflicting-record cases route to ESCALATE for human resolution." },
  { risk: "Prompt injection", failure: "Claim/retrieved text contains an instruction to manipulate the decision.", mitigation: ["Adversarially tested (Exp 28)", "Retrieved/user text treated as data, not instructions"], residual: "NOT SOLVED — retrieval-text injection fully succeeded once in testing; disclosed, not hidden.", human: "Full evidence trail logged; auditable after the fact even when not prevented." },
  { risk: "Retrieval poisoning", failure: "Fabricated text planted in the retrieved corpus is treated as authoritative.", mitigation: ["Same Exp 28 test", "Corpus is closed, allowlisted, synthetic — not open/user-editable"], residual: "Same underlying failure as prompt injection — demonstrated to succeed once.", human: "Same as prompt injection: post-hoc auditability + ESCALATE safety net." },
  { risk: "Wrong tool called", failure: "The agent calls a tool that doesn't apply to the situation.", mitigation: ["Read-only tools, typed schemas, call dedup (Exp 20/28)", "Exp 42/43 found & fixed 2 mis-firing tools"], residual: "Fixed only for the specific instances found live; no exhaustive proof for untested shapes.", human: "Every tool call + observation logged in the trace." },
  { risk: "Tool firing outside its domain", failure: "A tool returns a disposition for a claim type it wasn't built for.", mitigation: ["Exp 43 domain guards check expense_type before answering"], residual: "Applied to known-needed tools; an undiscovered mismatch elsewhere can't be ruled out.", human: "Disposition-gate overrides logged distinctly from the model's own reasoning." },
  { risk: "Unreliable input feeding deterministic code", failure: "A deterministic tool computes a confident wrong answer from bad extracted input.", mitigation: ["Placeholder-string normalization (Exp 49)", "Date-based counts computed in code, not trusted from the model (Exp 50)"], residual: "Open-ended bug class — 7 instances found in Exp 47-52 alone by actually running the system.", human: "Every argument's source (model vs. tool) is in the trace." },
  { risk: "Looping / repeated tool calls", failure: "The agent repeats a tool without converging.", mitigation: ["Call dedup + hard step cap (Exp 20/28)", "Step-cap-reached falls back to ESCALATE"], residual: "Step-cap hits still occur (3/13, 5/13, 8/13 across experiments) — fails safe, doesn't prevent looping.", human: "A step-cap ESCALATE is visibly distinct from an ordinary one in the trace." },
  { risk: "Cost explosion", failure: "Unbounded calls drive cost far above expectation.", mitigation: ["MAX_BUDGET_USD hard cap", "Step cap + full call caching"], residual: "Not material at measured pricing/workload — but not stress-tested at production concurrency.", human: "Cost logged per claim/run; scenario projections in the cost model, assumptions labeled." },
  { risk: "Provider failure", failure: "The LLM API is unavailable or errors mid-decision.", mitigation: ["Exp 28 tested malformed/unknown-tool/timeout — all failed closed (4/4)"], residual: "Only synthetic failure injection tested, not a real extended outage.", human: "A failed call routes to ESCALATE." },
  { risk: "Data / privacy", failure: "Real employee or company data is exposed.", mitigation: ["Entire dataset is synthetic — no real data used anywhere (problem.md §7)"], residual: "N/A to this project; a real deployment needs its own data-handling review.", human: "N/A — no real personal data exists here to protect." },
  { risk: "Synthetic-data limitation", failure: "Results may not transfer to real-world claim distributions.", mitigation: ["Hardened 3 rounds to remove trivial shortcuts", "Leakage tests enforce ground-truth isolation"], residual: "A controlled synthetic benchmark — not direct evidence of production performance.", human: "Real-world validation needed before trusting these numbers to transfer." }
];

function Row({ r }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="risk-row">
      <div className="risk-summary" onClick={() => setOpen((v) => !v)}>
        <span className="risk-toggle">{open ? "▾" : "▸"}</span>
        <span className="risk-name">{r.risk}</span>
        <span className="risk-failure">{r.failure}</span>
      </div>
      {open && (
        <div className="risk-detail">
          <div>
            <div className="risk-k">Mitigation</div>
            <ul className="bullets">{r.mitigation.map((m, i) => <li key={i}>{m}</li>)}</ul>
          </div>
          <div>
            <div className="risk-k">Residual risk</div>
            <p>{r.residual}</p>
          </div>
          <div>
            <div className="risk-k">Human control</div>
            <p>{r.human}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RiskTable() {
  return (
    <div className="risk-table">
      {RISKS.map((r) => (
        <Row r={r} key={r.risk} />
      ))}
    </div>
  );
}
