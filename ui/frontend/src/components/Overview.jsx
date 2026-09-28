import React, { useMemo } from "react";
import FlowChart from "./FlowChart.jsx";

function stats(cases, key, split) {
  const rows = split ? cases.filter((c) => c.split === split) : cases;
  const n = rows.length;
  const correct = rows.filter((c) => c[key].correct).length;
  const approvableWrongApprovals = rows.filter((c) => c[key].decision === "APPROVE" && c.ground_truth.expected_decision !== "APPROVE").length;
  const nonApprovable = rows.filter((c) => c.ground_truth.expected_decision !== "APPROVE").length;
  const far = nonApprovable ? (100 * approvableWrongApprovals) / nonApprovable : 0;
  return { n, correct, pct: n ? ((100 * correct) / n).toFixed(1) : "0.0", far: far.toFixed(1) };
}

const StatCard = ({ label, s, tone }) => (
  <div className={`stat-card ${tone || ""}`}>
    <div className="label">{label}</div>
    <div className="value">
      {s.correct}/{s.n}
    </div>
    <div className="label">
      {s.pct}% · FAR {s.far}%
    </div>
  </div>
);

export default function Overview({ cases }) {
  const frozenDev = useMemo(() => stats(cases, "frozen", "DEVELOPMENT"), [cases]);
  const frozenVal = useMemo(() => stats(cases, "frozen", "VALIDATION"), [cases]);
  const frozenFinal = useMemo(() => stats(cases, "frozen", "FINAL_TEST"), [cases]);
  const agentDev = useMemo(() => stats(cases, "agent", "DEVELOPMENT"), [cases]);
  const agentVal = useMemo(() => stats(cases, "agent", "VALIDATION"), [cases]);
  const agentFinal = useMemo(() => stats(cases, "agent", "FINAL_TEST"), [cases]);

  return (
    <div className="overview">
      <h1>The problem</h1>
      <p className="lede">
        An employee expense claim — a bill and a free-text note, nothing else structured — has to be
        decided as <b>APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE</b>, using a 22-document policy
        corpus, 11 enterprise tables, and the note itself, deliberately hardened so decision-critical
        facts (nights, attendee counts, exception references, even the expense category) live only in
        prose — sometimes next to a sentence that states something else entirely.
      </p>

      <h1 style={{ marginTop: 32 }}>How a claim actually gets decided</h1>
      <FlowChart />

      <h1 style={{ marginTop: 32 }}>About this project</h1>
      <div className="about-grid">
        <div className="about-card">
          <h4>What was actually tried</h4>
          <p>
            Over 50 experiments: tuning retrieval, building a deterministic rule engine, a fixed tool
            workflow, three generations of a ReAct agent, and dozens of targeted bug hunts — each one
            changing exactly one variable and measuring the result, never assumed.
          </p>
        </div>
        <div className="about-card">
          <h4>What actually mattered</h4>
          <p>
            Retrieval quality was never the bottleneck — handing the model perfect evidence barely moved
            accuracy. The real fix was moving decisions out of the model's hands into code wherever
            possible, and gating the model so it can't override a tool that already had the right answer.
          </p>
        </div>
        <div className="about-card">
          <h4>What's actually shipped</h4>
          <p>
            The frozen design (left branch of the diagram above): deterministic rules decide whenever
            they can, and a single-shot LLM handles the rest. Tested exactly once against 50 held-out
            claims, hash-manifest-verified: 30/50 correct, 0% false approvals.
          </p>
        </div>
        <div className="about-card">
          <h4>What's better, but not yet frozen</h4>
          <p>
            The guarded agent replaces that single-shot LLM step with a bounded agent whose tools compute
            the decision in code. It beats the frozen design's own accuracy on development and validation
            claims at matching safety — but has never been run against the real final test as an official
            result.
          </p>
        </div>
      </div>

      <h1 style={{ marginTop: 32 }}>Governance &amp; security alignment</h1>
      <p className="lede" style={{ fontSize: 13 }}>
        Framed against recognized frameworks — not a compliance certification, but an honest mapping of
        what was actually built and tested to the risk categories they name.
      </p>
      <div className="about-grid">
        <div className="about-card">
          <h4>OWASP Top 10 for LLM Applications — LLM06: Excessive Agency</h4>
          <p>
            Directly and concretely mitigated: every tool is read-only, bounded by a step cap and call
            deduplication, and — the core mechanism — the disposition gate (Exp 41) structurally prevents
            the model from overriding a tool that already computed the correct answer, with domain guards
            (Exp 43) restricting each tool to only the claim types it actually applies to.
          </p>
        </div>
        <div className="about-card">
          <h4>OWASP Top 10 for LLM Applications — LLM01: Prompt Injection</h4>
          <p>
            Identified and adversarially tested (Exp 28: injection, fake authority, malicious tool-embedded
            text), with a prompt-level defense in place (retrieved and user text is treated as data, never
            instructions). <b>Not fully solved</b>: Exp 28 found retrieval-text injection can still defeat
            that defense, and this remains a documented, disclosed open risk rather than a mitigated one.
          </p>
        </div>
        <div className="about-card">
          <h4>Human oversight (Singapore IMDA / EU AI Act principles)</h4>
          <p>
            ESCALATE is a first-class, deliberately safe outcome, not a failure — any claim the system
            can't resolve with confidence routes to a human reviewer by design. The frozen architecture
            was chosen specifically because it drives false approvals to 0%, at the cost of some raw
            accuracy, over a more "accurate" design that approved bad claims 13.5% of the time.
          </p>
        </div>
        <div className="about-card">
          <h4>Transparency &amp; auditability</h4>
          <p>
            Every decision's full evidence trail — retrieved clauses, resolved facts, every tool call —
            is logged and inspectable; this UI is that transparency mechanism made visible. Ground truth
            is never read by runtime code (enforced by automated leakage tests), so no decision path can
            see the answer it's being graded against.
          </p>
        </div>
      </div>

      <h1 style={{ marginTop: 32 }}>Two designs, live numbers from this export</h1>
      <div className="stat-grid">
        <StatCard label="Frozen · dev" s={frozenDev} />
        <StatCard label="Frozen · validation" s={frozenVal} />
        <StatCard label="Frozen · final test (official)" s={frozenFinal} tone="good" />
        <StatCard label="Guarded agent · dev" s={agentDev} tone="good" />
        <StatCard label="Guarded agent · validation" s={agentVal} tone="good" />
        <StatCard label="Guarded agent · final test (demo only)" s={agentFinal} />
      </div>
      <p className="lede" style={{ fontSize: 13 }}>
        The frozen design is the one actually shipped — tested once, officially, against the real
        held-out final test. The guarded agent is the best-validated candidate to replace its weak
        residual step: it beats the frozen design on development and validation at matching safety, but
        its final-test number here is a first-ever, demo-only look — not an official result, and not yet
        debugged to the same safety standard on that split. Open any case in <b>Case Explorer</b> to see
        exactly how each one arrived at its answer.
      </p>
    </div>
  );
}
