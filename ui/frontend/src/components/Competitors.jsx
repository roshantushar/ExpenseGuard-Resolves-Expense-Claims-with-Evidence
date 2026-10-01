import React from "react";

// Framing matches problem.md §3 exactly: this project does not claim AI-based expense checking is new.
// The narrower question it investigates is whether DYNAMIC cross-system evidence gathering adds
// measurable value — and whether a safety-first, cost-audited architecture-selection process (not just a
// feature list) is the differentiator. Competitor capabilities described here are the well-known, public
// category of features these products are known for — not a claim about their internal architecture,
// which is not public.
const ROWS = [
  {
    capability: "Policy compliance checking",
    them: "Yes — rule/threshold-based",
    us: "Yes — deterministic rules + retrieval-grounded LLM for the residual, routed by conclusiveness"
  },
  {
    capability: "Duplicate / policy-violation detection",
    them: "Yes — established feature across the category",
    us: "Yes, plus explicit split-transaction and near-duplicate handling with negative controls"
  },
  {
    capability: "Dynamic, multi-step evidence gathering (agentic)",
    them: "Not a publicly documented core capability",
    us: "Tested explicitly (Exp 18–60) — not justified by default; adopted only where guarded, then root-caused, fixed, and fresh-holdout tested before being called a candidate"
  },
  {
    capability: "Published, held-out accuracy + false-approval rate",
    them: "Not publicly disclosed",
    us: "30/50 (60%) on a frozen, one-shot 50-claim final test — 0/37 observed false approvals"
  },
  {
    capability: "Architecture chosen by risk-adjusted operating cost, not just accuracy",
    them: "Not publicly documented as a selection method",
    us: "Explicit, and re-verified twice: a cost-model bug was found and fixed; a fresh 50-case holdout later confirmed the fixed candidate matches the shipped design's 0% false-approval rate at double its accuracy — still the shipped design remains official, since it's the only one with a frozen, authorized final-test result"
  },
  {
    capability: "OWASP LLM Top 10 security testing, disclosed",
    them: "Not publicly disclosed",
    us: "All 10 categories tested this project — including an admitted, unsolved prompt-injection risk"
  },
  {
    capability: "Full decision trace + evidence auditability",
    them: "Reviewer-facing UI exists; internal reasoning trace not publicly documented",
    us: "Every tool call, retrieved chunk, and resolved fact is logged and inspectable (this UI)"
  },
  {
    capability: "Ground-truth leakage testing, disclosed",
    them: "Not applicable / not public",
    us: "Explicit before/after leakage test (Exp 2): 70/70 → 48/70 once shortcuts were removed"
  }
];

export default function Competitors() {
  return (
    <div>
      <p className="lede" style={{ fontSize: 13 }}>
        This project does not claim AI-based expense checking is new — SAP Concur / Concur Detect,
        Brex, and Ramp already automate large parts of expense policy compliance. The question this
        project investigates is narrower: <b>does dynamic, multi-step evidence gathering add measurable
        value</b>, and <b>can an architecture be chosen by safety and total operating cost instead of a
        feature checklist</b>. That process, and its evidence, is what's compared below.
      </p>
      <div className="build-table">
        <div className="build-row comp-row comp-head">
          <div>Capability</div>
          <div>Established expense platforms</div>
          <div>ExpenseGuard</div>
        </div>
        {ROWS.map((r) => (
          <div className="build-row comp-row" key={r.capability}>
            <div>{r.capability}</div>
            <div className="comp-them">{r.them}</div>
            <div className="comp-us">{r.us}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
