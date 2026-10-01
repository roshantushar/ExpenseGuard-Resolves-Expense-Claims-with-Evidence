import React, { useMemo } from "react";
import FlowChart from "./FlowChart.jsx";
import BeforeAfterCases from "./BeforeAfterCases.jsx";
import Competitors from "./Competitors.jsx";
import ErrorAnalysis from "./ErrorAnalysis.jsx";
import CostAtScale from "./CostAtScale.jsx";
import LadderChart from "./LadderChart.jsx";
import RiskTable from "./RiskTable.jsx";
import useReveal from "../hooks/useReveal.js";
import { ACTS } from "../storyData.js";

function stats(cases, key, split) {
  const rows = split ? cases.filter((c) => c.split === split) : cases;
  const n = rows.length;
  const correct = rows.filter((c) => c[key].correct).length;
  const approvableWrongApprovals = rows.filter((c) => c[key].decision === "APPROVE" && c.ground_truth.expected_decision !== "APPROVE").length;
  const nonApprovable = rows.filter((c) => c.ground_truth.expected_decision !== "APPROVE").length;
  const far = nonApprovable ? (100 * approvableWrongApprovals) / nonApprovable : 0;
  return { n, correct, pct: n ? ((100 * correct) / n).toFixed(1) : "0.0", far: far.toFixed(1), farCount: approvableWrongApprovals, farDenom: nonApprovable };
}

const StatCard = ({ label, s, tone }) => (
  <div className={`stat-card ${tone || ""}`}>
    <div className="label">{label}</div>
    <div className="value">
      {s.correct}/{s.n}
    </div>
    <div className="label">
      {s.pct}% · FAR {s.farCount}/{s.farDenom} = {s.far}%
    </div>
  </div>
);

const STORY_STRIP = [
  { k: "THE DATA", body: "150 claims — a bill + free-text note, nothing structured. 22 policies, 11 enterprise systems." },
  { k: "🔍 FOUND", body: "The frozen baseline: 30/50, 0/37 false approvals — but its LLM step never once correctly approved a real approvable claim." },
  { k: "🛠️ FIXED", body: "Rebuilt that step so tools compute the answer in code, gated so the model can't override a fact it was already given." },
  { k: "🔬 TESTED HARDER", body: "A second holdout, pre-registered before a single case existed — built to break the fix, not confirm it." },
  { k: "✅ WHAT SHIPS", body: "The fix wins every accuracy test it's taken. The baseline ships anyway: 0 false approvals across all 82 cases it's ever faced." }
];

const BADGES = [
  { n: "55", l: "experiments run (numbered 0-61, Exp 21-27 skipped)" },
  { n: "150", l: "claims, 22+ policies, 11 tables" },
  { n: "7", l: "real live-found bugs, fixed in the guarded-agent build (Exp 40-52)" },
  { n: "0", l: "observed false approvals (official frozen resolver)" },
  { n: "10/10", l: "OWASP LLM categories tested" },
  { n: "$7.38", l: "total API spend, all of it" }
];

function ActCard({ act, index }) {
  const [ref, visible] = useReveal();
  return (
    <div ref={ref} className={`act-row ${visible ? "in" : ""}`}>
      <div className="act-dot-col">
        <div className="act-dot">{index + 1}</div>
        {index < ACTS.length - 1 && <div className="act-line" />}
      </div>
      <div className="act-card">
        <h3>{act.title}</h3>
        <div style={{ marginBottom: 10 }}>
          {act.tags.map((t) => (
            <span className="tag" key={t}>
              {t}
            </span>
          ))}
        </div>
        <ul className="bullets">
          {act.points.map((p, i) => (
            <li key={i} className={p.startsWith("⟶") ? "punchline" : ""}>
              {p.replace(/^⟶\s*/, "")}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function Overview({ cases }) {
  const frozenDev = useMemo(() => stats(cases, "frozen", "DEVELOPMENT"), [cases]);
  const frozenVal = useMemo(() => stats(cases, "frozen", "VALIDATION"), [cases]);
  const frozenFinal = useMemo(() => stats(cases, "frozen", "FINAL_TEST"), [cases]);
  const agentDev = useMemo(() => stats(cases, "agent", "DEVELOPMENT"), [cases]);
  const agentVal = useMemo(() => stats(cases, "agent", "VALIDATION"), [cases]);

  return (
    <div className="overview">
      <div className="overview-inner">
      <h1>The problem, in one sentence</h1>
      <p className="lede">
        Given an expense claim — a bill and a free-text note, nothing else structured — decide whether it's
        safe to <b>APPROVE</b>, <b>REJECT</b>, <b>REQUEST_INFORMATION</b>, or <b>ESCALATE</b> it to a human —
        and never confidently approve a claim that should not have been approved.
      </p>
      <div className="badge-strip">
        {BADGES.map((b) => (
          <div className="badge-stat" key={b.l}>
            <div className="badge-n">{b.n}</div>
            <div className="badge-l">{b.l}</div>
          </div>
        ))}
      </div>

      <h1 style={{ marginTop: 36 }}>The story, in one line each</h1>
      <div className="story-strip">
        {STORY_STRIP.map((s, i) => (
          <React.Fragment key={s.k}>
            <div className="story-step">
              <div className="story-step-k">{s.k}</div>
              <div className="story-step-body">{s.body}</div>
            </div>
            {i < STORY_STRIP.length - 1 && <div className="story-arrow">→</div>}
          </React.Fragment>
        ))}
      </div>

      <h1 style={{ marginTop: 36 }}>Who this is for</h1>
      <div className="persona-grid">
        <div className="persona-card primary">
          <div className="persona-role">Primary user</div>
          <div className="persona-name">Maya — Corporate Finance Expense Reviewer</div>
          <ul className="bullets">
            <li>Today: manually inspects policy, travel records, approvals, exceptions, prior claims, merchant data — for every claim</li>
            <li>With ExpenseGuard: only sees claims that genuinely need her — missing evidence, conflicting evidence, ambiguity, or a policy-mandated review</li>
            <li>Evidence is already assembled by the time it reaches her</li>
          </ul>
        </div>
        <div className="persona-card">
          <div className="persona-role">Secondary beneficiary</div>
          <div className="persona-name">The employee submitting the claim</div>
          <ul className="bullets">
            <li>Faster resolution on routine claims</li>
            <li>A specific request when something's missing, not a vague "more info needed"</li>
            <li>An evidence-backed reason whenever a claim is rejected or escalated</li>
          </ul>
        </div>
      </div>
      <p className="lede" style={{ fontSize: 12.5 }}>
        External industry estimate (GBTA Foundation, not a measured result): manual processing costs ~$58 /
        20 min per report; 19% contain errors, costing a further $52 / 18 min to correct. See{" "}
        <code>problem.md</code> §2.
      </p>

      <h1 style={{ marginTop: 36 }}>Four real decisions, before and after</h1>
      <p className="lede" style={{ fontSize: 13 }}>
        One real case per outcome, step by step — how it would be handled manually vs. with ExpenseGuard.
        Every case is real, verified against the actual saved results, not staged for effect.
      </p>
      <BeforeAfterCases />

      <h1 style={{ marginTop: 36 }}>How a claim actually gets decided</h1>
      <FlowChart />

      <h1 style={{ marginTop: 36 }}>Climbing the complexity ladder — only when justified</h1>
      <p className="lede" style={{ fontSize: 13 }}>
        Every rung below was measured, not assumed. Higher accuracy alone was never enough to win.
      </p>
      <LadderChart />

      <h1 style={{ marginTop: 36 }}>Who else does this, and what's different here</h1>
      <Competitors />

      <h1 style={{ marginTop: 36 }}>About this project</h1>
      <div className="about-grid">
        <div className="about-card">
          <h4>What was actually tried</h4>
          <ul className="bullets">
            <li>Retrieval tuning ladder (chunking, top-K, retriever, metadata filter)</li>
            <li>A deterministic rule engine, hardened and re-tested 3 times</li>
            <li>A fixed, pre-declared tool workflow</li>
            <li>Three generations of a ReAct agent</li>
            <li>Dozens of targeted live bug hunts — one variable changed at a time, always measured</li>
          </ul>
        </div>
        <div className="about-card">
          <h4>What actually mattered</h4>
          <ul className="bullets">
            <li>Retrieval was never the bottleneck — perfect evidence barely moved accuracy</li>
            <li>The real fix: move decisions out of the model's hands into code</li>
            <li>Gate the model so it can't override a tool that already had the right answer</li>
          </ul>
        </div>
        <div className="about-card">
          <h4>What's actually shipped</h4>
          <ul className="bullets">
            <li>Deterministic rules decide whenever they can</li>
            <li>A single-shot LLM handles the rest</li>
            <li>Tested once, frozen: 30/50 correct, 0 observed false approvals — the only architecture with an independent held-out result</li>
          </ul>
        </div>
        <div className="about-card">
          <h4>The twist — and a correction</h4>
          <ul className="bullets">
            <li>A guarded agent scored higher on accuracy at matching safety on dev/validation</li>
            <li>It escalates more often — a first cost model found this made it more expensive; that model had a bug, fixed</li>
            <li>But a diagnostic run on (no-longer-independent) final-test data showed real degradation, including false approvals — not promoted</li>
          </ul>
        </div>
        <div className="about-card">
          <h4>What happened next — root-cause, fix, fresh test</h4>
          <ul className="bullets">
            <li>Found why: the model doesn't reliably ground its answer in facts unless a tool computes the disposition <b>and</b> something enforces the tool was actually used</li>
            <li>Fixed live: a missing policy circular, an unenforced conflict check, a skippable tool call</li>
            <li>Tested once on a fresh, never-seen 50-case holdout: <b>0% false approvals, matching the frozen resolver</b>, at roughly double its accuracy and APPROVE recall</li>
            <li>A stronger model (gpt-4o) traded that safety margin for accuracy — disclosed, not smoothed over</li>
          </ul>
        </div>
      </div>

      <h1 style={{ marginTop: 36 }}>Where the frozen system got it wrong — error analysis</h1>
      <ErrorAnalysis />

      <h1 style={{ marginTop: 36 }}>What each architecture actually costs, at scale</h1>
      <CostAtScale />

      <h1 style={{ marginTop: 36 }}>Governance &amp; security alignment</h1>
      <p className="lede" style={{ fontSize: 13 }}>
        Framed against recognized frameworks — an honest mapping of what was tested, not a compliance
        certification. All 10 OWASP Top 10 for LLM Applications (2026) categories have real test evidence.
      </p>
      <div className="about-grid">
        <div className="about-card">
          <h4>LLM06: Excessive Agency — mitigated</h4>
          <ul className="bullets">
            <li>Every tool is read-only, bounded by a step cap and call deduplication</li>
            <li>Disposition gate structurally prevents overriding a tool with the correct answer</li>
            <li>Domain guards restrict each tool to only the claim types it applies to</li>
          </ul>
        </div>
        <div className="about-card">
          <h4>LLM01: Prompt Injection — not fully solved</h4>
          <ul className="bullets">
            <li>Adversarially tested (Exp 28): injection, fake authority, malicious tool-embedded text</li>
            <li>Retrieved/user text is treated as data, never instructions</li>
            <li><b>Retrieval-text injection can still defeat that defense</b> — disclosed, not hidden</li>
          </ul>
        </div>
        <div className="about-card">
          <h4>Human oversight (IMDA / EU AI Act principles)</h4>
          <ul className="bullets">
            <li>ESCALATE is a first-class, deliberately safe outcome, not a failure</li>
            <li>Frozen architecture chosen specifically to drive false approvals to 0%</li>
            <li>Traded some raw accuracy for that — a "more accurate" design approved bad claims 13.5% of the time</li>
          </ul>
        </div>
        <div className="about-card">
          <h4>Transparency &amp; auditability</h4>
          <ul className="bullets">
            <li>Every retrieved clause, resolved fact, and tool call is logged and inspectable</li>
            <li>This UI is that transparency mechanism made visible</li>
            <li>Ground truth is never read by runtime code — enforced by automated leakage tests</li>
          </ul>
        </div>
      </div>

      <h1 style={{ marginTop: 36 }}>Full risk table — risk → mitigation → residual risk → human control</h1>
      <p className="lede" style={{ fontSize: 13 }}>
        14 risk categories. Click a row to expand. A disclaimer is not a mitigation — every row states what
        was actually built, including where the residual risk is real and unsolved.
      </p>
      <RiskTable />

      <h1 style={{ marginTop: 36 }}>Two designs, live numbers from this export</h1>
      <p className="lede" style={{ fontSize: 13 }}>
        <b>The target, stated explicitly:</b> 0 observed false approvals on the evaluation population, at
        the best accuracy achievable without violating that constraint — never "maximize accuracy" alone.
      </p>
      <div className="stat-grid">
        <StatCard label="Frozen · dev" s={frozenDev} />
        <StatCard label="Frozen · validation" s={frozenVal} />
        <StatCard label="Frozen · final test (official)" s={frozenFinal} tone="good" />
        <StatCard label="Guarded agent · dev" s={agentDev} tone="good" />
        <StatCard label="Guarded agent · validation" s={agentVal} tone="good" />
      </div>
      <p className="lede" style={{ fontSize: 13 }}>
        The frozen design is the one actually shipped — tested once, officially, against the real
        held-out final test. The fixed guarded-agent candidate was separately tested once against a fresh,
        independently-labeled 50-case holdout neither design had seen: <b>0% false approvals, 68% accuracy</b>
        — real evidence its fixes generalize, not yet an independently validated replacement (full result in{" "}
        <code>docs/exp60_fresh_holdout.md</code>). Open any case in <b>Case Explorer</b> to see exactly how
        each one arrived at its answer.
      </p>

      <h1 style={{ marginTop: 36 }}>Why "0% false approvals, 44% accuracy" hides the real story</h1>
      <p className="lede" style={{ fontSize: 13 }}>
        Four-way accuracy blends a false approval (a safety failure) with a false rejection (a real
        approvable claim wrongly blocked — a cost, not a danger) into one number. Broken apart, on the same
        Exp 60 fresh holdout, at $0 — recomputed from saved predictions, no new calls:
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border, #333)" }}>
              <th style={{ padding: "8px 10px" }}></th>
              <th style={{ padding: "8px 10px" }}>Safely automated & correct, no human</th>
              <th style={{ padding: "8px 10px" }}>False approvals</th>
              <th style={{ padding: "8px 10px" }}>False rejections</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: "1px solid var(--border, #222)" }}>
              <td style={{ padding: "8px 10px" }}>Frozen resolver (official)</td>
              <td style={{ padding: "8px 10px" }}>21/50 = 42%</td>
              <td style={{ padding: "8px 10px" }}>0</td>
              <td style={{ padding: "8px 10px", fontWeight: 600 }}>20/50 = 40%</td>
            </tr>
            <tr style={{ borderBottom: "1px solid var(--border, #222)" }}>
              <td style={{ padding: "8px 10px" }}>Candidate, gpt-4o-mini + gate</td>
              <td style={{ padding: "8px 10px", fontWeight: 600 }}>33/50 = 66%</td>
              <td style={{ padding: "8px 10px" }}>0</td>
              <td style={{ padding: "8px 10px" }}>2/50 = 4%</td>
            </tr>
            <tr>
              <td style={{ padding: "8px 10px" }}>Candidate, gpt-4o + gate</td>
              <td style={{ padding: "8px 10px" }}>38/50 = 76%</td>
              <td style={{ padding: "8px 10px" }}>2</td>
              <td style={{ padding: "8px 10px" }}>3/50 = 6%</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="lede" style={{ fontSize: 13 }}>
        The frozen resolver's 0% FAR conceals its actual biggest weakness: on this fresh sample, <b>2 of
        every 5 claims that should have been approved were wrongly blocked.</b> The fixed candidate cuts
        that false-rejection rate by 10x while holding false approvals at zero — a larger, clearer
        improvement in real automation value than "68% vs 44% accuracy" conveys alone.
      </p>

      <h1 style={{ marginTop: 44 }}>The full story, from data to decision</h1>
      <p className="lede" style={{ fontSize: 13, marginBottom: 24 }}>
        Every number below traces back to a saved result file and a written doc under <code>docs/</code>.
        Scroll down.
      </p>
      <div className="timeline">
        {ACTS.map((act, i) => (
          <ActCard act={act} index={i} key={act.title} />
        ))}
      </div>
      </div>
    </div>
  );
}
