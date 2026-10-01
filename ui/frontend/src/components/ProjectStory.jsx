import React, { useEffect, useMemo, useState } from "react";
import LadderChart from "./LadderChart.jsx";
import RiskTable from "./RiskTable.jsx";
import { ALL_EXPERIMENTS } from "../experimentLog.js";

const NAV = [
  { id: "s1", label: "Overview" },
  { id: "s2", label: "Problem" },
  { id: "s3", label: "Persona" },
  { id: "s4", label: "User Flow" },
  { id: "s5", label: "Why Hybrid" },
  { id: "s6", label: "Architecture" },
  { id: "s7", label: "Dataset" },
  { id: "s8", label: "Experiments" },
  { id: "s9", label: "Official Result" },
  { id: "s10", label: "Why 60%" },
  { id: "s11", label: "Failure Analysis" },
  { id: "s12", label: "What Didn't Fix It" },
  { id: "s13", label: "Guarded Agent" },
  { id: "s14", label: "Cost" },
  { id: "s15", label: "Build vs Buy" },
  { id: "s16", label: "Safety" },
  { id: "s17", label: "Decision Matrix" },
  { id: "s18", label: "Demo" },
  { id: "s19", label: "Limitations" },
  { id: "s20", label: "Conclusion" },
  { id: "s21", label: "Documents" },
];

const MV = "See experiment evidence"; // shown whenever a value could not be loaded from a canonical source

function Metric({ value, suffix = "" }) {
  return <span>{value === undefined || value === null ? MV : `${value}${suffix}`}</span>;
}

function Section({ id, title, children }) {
  return (
    <section id={id} className="ps-section">
      <h1>{title}</h1>
      {children}
    </section>
  );
}

const DOCS = [
  ["Root README", "README.md"], ["Problem Statement", "problem.md"],
  ["Final Report (1,200 words)", "docs/FINAL_REPORT.md"], ["Experiment Index", "docs/README.md"],
  ["Exp 30 — Architecture Freeze", "docs/exp30_selective_router.md"], ["Exp 32 — Final Test", "docs/exp32_final_test.md"],
  ["Exp 33 — Failure Analysis", "docs/exp33_failure_analysis.md"], ["Cost & Business Impact", "docs/cost_and_business_impact.md"],
  ["Build vs Buy", "docs/build_vs_buy.md"], ["Responsible AI Risk Table", "docs/responsible_ai_risk_table.md"],
  ["OWASP 2026 Evaluation", "docs/owasp_llm_top10_2026.md"], ["Synthetic Data Provenance", "docs/synthetic_data_provenance.md"],
  ["Reproducibility Guide", "docs/reproducibility_and_repo_map.md"], ["Demo Script", "docs/demo_script.md"],
  ["Gate Override Audit", "docs/gate_override_audit.md"], ["CHANGELOG_FINAL", "CHANGELOG_FINAL.md"],
  ["Exp 53 — Approve Calibration", "docs/exp53_approve_calibration.md"], ["Exp 54 — Stronger Model", "docs/exp54_stronger_model_approve.md"],
  ["Exp 55 — Fact Fixes", "docs/exp55_fact_fixes.md"], ["Exp 56 — Hotel Ceiling Fix", "docs/exp56_hotel_ceiling_fix.md"],
  ["Exp 57 — Hybrid Facts, No Gate", "docs/exp57_hybrid_facts_hotel.md"], ["Exp 58 — Full Agent Fix", "docs/exp58_full_agent_fix.md"],
  ["Exp 59 — Final Fix", "docs/exp59_final_fix.md"], ["Exp 60 — Fresh Holdout", "docs/exp60_fresh_holdout.md"],
  ["Exp 61 — Pre-Registered V3 Holdout", "docs/exp61_v3_holdout.md"],
];

const EXP_PHASES_7 = [
  { name: "Phase 1 — Baselines", range: "Exp 0–4", ns: ["0", "1", "2", "3", "4A/4B"],
    findings: ["Dataset validated, 0 critical errors", "Simple deterministic rules became brittle after hardening", "Generic LLM produced unsupported decisions", "Long context did not justify its cost"] },
  { name: "Phase 2 — Retrieval", range: "Exp 5–11", ns: ["5", "6", "7", "8", "9", "10", "11"],
    findings: ["Chunking, top-K, dense/BM25/hybrid, and metadata filtering all tuned in turn", "Query rewriting improved retrieval metrics but hurt final answers", "Policy oracle: perfect evidence barely moved accuracy"],
    highlight: "Better retrieval did not automatically improve downstream decisions." },
  { name: "Phase 3 — Hybrid / Tools", range: "Exp 12–17", ns: ["12 / 12B", "13", "14", "15", "16", "17"],
    findings: ["Deterministic-first routing motivated and probed", "Missing-info, duplicate/split checks qualified", "Enterprise-fact resolution and typed tools qualified"],
    highlight: "Arithmetic and checkable policy mechanics moved out of the LLM." },
  { name: "Phase 4 — Workflow vs Agent", range: "Exp 18–20 (21–27 not run)", ns: ["18", "19", "20"],
    findings: [], highlight: "Agentic autonomy did not justify its additional risk.", skipNotice: true },
  { name: "Phase 5 — Guardrails / Freeze / Final", range: "Exp 28–33", ns: ["28", "29", "30", "31", "32", "33"], findings: [] },
  { name: "Phase 6 — Post-Final Agent Research", range: "Exp 34–39", ns: ["34", "35", "36", "37", "38", "39"],
    findings: [], highlight: "More prompting, a larger model and better retrieval did not solve the decision problem." },
  { name: "Phase 7 — Guarded Agent", range: "Exp 40–52", ns: ["40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52"],
    findings: [], highlight: "Reliable deterministic authority helped only when tool inputs and applicability boundaries were also reliable." },
  { name: "Phase 8 — Root-cause the APPROVE blind spot, fix it, fresh-holdout test it", range: "Exp 53–60", ns: ["53", "54", "55", "56", "57", "58", "59", "60"],
    findings: [], highlight: "A fact handed to the model changes nothing unless something in the architecture enforces its use — the disposition gate, not the fact itself, is what made every later fix work." },
  { name: "Phase 9 — Pre-register the candidate, test it a second, independent time", range: "Exp 61", ns: ["61"],
    findings: [], highlight: "A 0% observed false-approval rate on one holdout is not the same claim as 0% true risk — the second, pre-registered holdout found the candidate's first real false approval." },
];

function ExperimentPhase({ phase }) {
  const [open, setOpen] = useState(false);
  const entries = phase.ns.map((n) => ALL_EXPERIMENTS.find((e) => e.n === n)).filter(Boolean);
  return (
    <div className="exp-phase-head" style={{ cursor: "pointer", marginBottom: 8 }} onClick={() => setOpen((v) => !v)}>
      <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
        <span className="exp-toggle">{open ? "▾" : "▸"}</span>
        <b>{phase.name}</b> <span className="exp-phase-range">{phase.range}</span>
      </div>
      {open && (
        <div style={{ marginTop: 10, cursor: "default" }} onClick={(e) => e.stopPropagation()}>
          {phase.skipNotice && (
            <div className="callout-card bad" style={{ marginBottom: 10 }}>
              <b>Exp 21–27: NOT RUN — agent gate closed.</b> Exp 20 failed the pre-defined agent-value/safety
              gate, so the additional agent-optimization experiments planned as Exp 21–27 were deliberately
              skipped, not forgotten.
            </div>
          )}
          {phase.findings.length > 0 && (
            <ul className="bullets" style={{ marginBottom: 8 }}>{phase.findings.map((f, i) => <li key={i}>{f}</li>)}</ul>
          )}
          {phase.highlight && <div className="callout-card" style={{ marginBottom: 10, fontStyle: "italic" }}>"{phase.highlight}"</div>}
          <div className="exp-list">
            {entries.map((e) => (
              <div className="exp-row" key={e.n}>
                <div className="exp-summary" style={{ cursor: "default" }}>
                  <span className="exp-num">Exp {e.n}</span>
                  <span className="exp-title">{e.title}</span>
                </div>
                <div className="exp-detail" style={{ paddingLeft: 14 }}>
                  <div><div className="risk-k">Question</div><p>{e.q}</p></div>
                  <div><div className="risk-k">Found</div><p>{e.found}</p></div>
                  <div><div className="risk-k">Why → next</div><p>{e.next}</p></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AllExperimentsTable() {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 14 }}>
      <button className="chunk-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? "▾ Hide" : "▸ View"} all {ALL_EXPERIMENTS.length} experiments
      </button>
      {open && (
        <div className="build-table" style={{ marginTop: 10, maxHeight: 480, overflowY: "auto" }}>
          <div className="build-row" style={{ gridTemplateColumns: "70px 1fr 1fr 1fr" }}>
            <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Exp</div>
            <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Hypothesis</div>
            <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Main finding</div>
            <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Why → next</div>
          </div>
          {ALL_EXPERIMENTS.map((e) => (
            <div className="build-row" style={{ gridTemplateColumns: "70px 1fr 1fr 1fr", fontSize: 11.5 }} key={e.n}>
              <div className="mono-cell">{e.n}</div>
              <div>{e.q}</div>
              <div>{e.found}</div>
              <div>{e.next}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const DEMO_CASES = [
  { id: "X2-060", label: "Deterministic, easy", note: "$0, no LLM call" },
  { id: "X2-006", label: "RAG / evidence case", note: "retrieval-grounded LLM call" },
  { id: "X2-005", label: "Guarded-tool agent", note: "debugged across 5 prior experiments" },
  { id: "X2-059", label: "Human review / escalation", note: "correctly routed, not a failure" },
];

export default function ProjectStory() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    fetch("/data/project_story.json")
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch((e) => setLoadError(String(e)));
  }, []);

  const d = data || {};
  const arch = useMemo(() => d.architecture_comparison || {}, [d]);

  if (loadError) {
    return <div className="overview"><div className="overview-inner"><p className="err">Could not load /data/project_story.json ({loadError}). Run <code>python3 scripts/export_project_story.py</code> to generate it.</p></div></div>;
  }

  return (
    <div className="overview project-story">
      <div className="ps-nav">
        <div className="ps-nav-inner">
          {NAV.map((n) => (
            <a key={n.id} href={`#${n.id}`} className="ps-nav-link">{n.label}</a>
          ))}
        </div>
      </div>
      <div className="overview-inner ps-body">
        <Section id="s1" title="The Full Story, In Depth">
          <p className="lede" style={{ fontSize: 16 }}>Evidence-Grounded Enterprise Expense Compliance</p>
          <p className="lede" style={{ fontStyle: "italic" }}>
            "How far should an enterprise expense-compliance system climb from deterministic rules to RAG,
            workflows and agents before the additional accuracy no longer justifies the cost, complexity
            and operational risk?"
          </p>
          <div className="badge-strip">
            <div className="badge-stat"><div className="badge-n">Selective Resolver</div><div className="badge-l">Official system · Exp 30 / Exp 32</div></div>
            <div className="badge-stat"><div className="badge-n"><Metric value={d.exp32_official?.correct} suffix={`/${d.exp32_official?.n ?? ""}`} /></div><div className="badge-l"><Metric value={d.exp32_official?.accuracy_pct} suffix="% · " />0 observed false approvals</div></div>
            <div className="badge-stat"><div className="badge-n">Frozen &amp; retained</div><div className="badge-l">Final architecture decision</div></div>
          </div>
          <div className="callout-card" style={{ marginTop: 20, fontSize: 16, fontWeight: 700, textAlign: "center" }}>
            "The best-performing AI architecture was not the best operating architecture."
          </div>
          <p className="lede" style={{ textAlign: "center", marginTop: 8 }}>
            Enterprise AI should be optimized for safe automation and total operating cost, not benchmark accuracy alone.
          </p>
        </Section>

        <Section id="s2" title="The Problem">
          <p className="lede">Corporate finance reviewers must decide whether employee expense claims comply with company policy.</p>
          <p className="lede" style={{ fontSize: 13 }}>A claim may require checking:</p>
          <ul className="bullets">
            <li>Employee free-text explanation</li><li>Applicable expense policy</li><li>Policy version / effective date</li>
            <li>Approval records</li><li>Delegation records</li><li>Travel requests</li><li>Hotel ceilings</li>
            <li>Project budgets</li><li>Previous claims</li><li>Exceptions</li><li>Missing/conflicting evidence</li>
          </ul>
          <div className="stat-grid">
            {["APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE"].map((x) => (
              <div className="stat-card" key={x}><span className={`decision-pill ${x}`}>{x}</span></div>
            ))}
          </div>
          <p className="lede" style={{ fontStyle: "italic", marginTop: 12 }}>
            "The goal is not maximum autonomous decision-making. The goal is maximum safe automation at
            acceptable total operating cost."
          </p>
          <div className="risk-k" style={{ marginTop: 16 }}>What success looks like</div>
          <p className="lede" style={{ fontSize: 13 }}>
            A false approval (paying a claim that should have been rejected) is far costlier than an
            unnecessary human review, so the primary success metric is <strong>False Approval Rate (FAR)</strong> —
            target as close to 0% as possible — with accuracy and Human Review Rate as secondary metrics
            that must not be sacrificed to get there.
          </p>
          <div className="stat-grid" style={{ marginTop: 8 }}>
            <div className="stat-card good"><div className="value"><Metric value={d.exp32_official?.far_pct} suffix="%" /></div><div className="label">FAR — frozen final test (target metric)</div></div>
            <div className="stat-card"><div className="value"><Metric value={d.exp32_official?.accuracy_pct} suffix="%" /></div><div className="label">Accuracy — frozen final test</div></div>
            <div className="stat-card"><div className="value"><Metric value={d.exp32_official?.human_review_rate_pct} suffix="%" /></div><div className="label">Human Review Rate — frozen final test</div></div>
          </div>
          <p className="lede" style={{ fontSize: 13, marginTop: 8 }}>
            Every rung of the architecture ladder (§6) was kept or discarded by whether it moved FAR toward
            0% without an unacceptable rise in Human Review Rate: the deterministic layer resolves the cases
            it can prove, the LLM/RAG layer only handles the residual it cannot, and the disposition gate in
            code overrides a model decision whenever a tool result and the model disagree — which is why the
            frozen system reaches 0% observed FAR on the 50-case final test rather than only a high raw
            accuracy score.
          </p>
          <div className="risk-k" style={{ marginTop: 16 }}>Other metrics tracked across every experiment</div>
          <ul className="bullets">
            <li><strong>Correct Decision Rate (CDR)</strong> — accuracy with a Wilson confidence interval, since n is small</li>
            <li><strong>APPROVE recall</strong> — of claims that should be approved, how many actually were (a low-automation system can hit 0% FAR by escalating everything, so this catches that failure mode)</li>
            <li><strong>Safe Automation Rate</strong> — share of cases resolved automatically without a false approval</li>
            <li><strong>Escalation Rate</strong> — share of cases the system declines to decide on its own</li>
            <li><strong>Human Review Rate (HRR)</strong> — share of decisions routed to a person, tracked alongside FAR so gains in one are not hidden by losses in the other</li>
            <li><strong>Retrieval quality</strong> — Recall@K, Precision@K, MRR, and Full Evidence Coverage for the RAG layer</li>
            <li><strong>Cost</strong> — dollars/claim from measured token usage, and risk-adjusted cost per 1,000 claims (§14) once reviewer time and the cost of a wrong decision are modelled in</li>
            <li><strong>Latency</strong> — median and P95 per claim</li>
            <li><strong>Guardrail pass rate</strong> — adversarial/OWASP test pass rate, tracked separately from CDR so safety is never traded for accuracy</li>
          </ul>
        </Section>

        <Section id="s3" title="Primary Persona">
          <div className="persona-grid">
            <div className="persona-card primary">
              <div className="persona-name">Maya — Finance Expense Reviewer</div>
              <p style={{ fontSize: 13 }}>Maya is a finance operations analyst reviewing employee expense claims. She must determine whether each claim is compliant by combining employee explanations, policy evidence and enterprise records.</p>
              <div className="risk-k" style={{ marginTop: 10 }}>Her current tasks</div>
              <ul className="bullets">
                <li>Read claim</li><li>Identify applicable policy</li><li>Find policy clause</li><li>Check required evidence</li>
                <li>Query enterprise systems</li><li>Resolve conflicts</li><li>Apply calculations/limits</li>
                <li>Approve, reject, request information, or escalate</li><li>Record the reason</li>
              </ul>
            </div>
            <div className="persona-card">
              <div className="risk-k">Pain points</div>
              <ul className="bullets">
                <li>Fragmented evidence</li><li>Manual policy lookup</li><li>Policy-version ambiguity</li>
                <li>Repetitive calculations</li><li>Inconsistent decisions</li><li>Costly false approvals</li>
                <li>Unnecessary human review</li>
              </ul>
            </div>
          </div>
        </Section>

        <Section id="s4" title="User Flow">
          <UserFlow />
        </Section>

        <Section id="s5" title="Why AI / Why Hybrid">
          <div className="about-grid">
            <div className="about-card"><h4>Deterministic Logic</h4><ul className="bullets"><li>Arithmetic</li><li>Policy ceilings</li><li>Dates</li><li>Explicit approval requirements</li><li>Deterministic policy mechanics</li></ul></div>
            <div className="about-card"><h4>RAG</h4><ul className="bullets"><li>Organization-specific policy documents</li><li>Policy versions</li><li>Evidence grounding</li></ul></div>
            <div className="about-card"><h4>LLM</h4><ul className="bullets"><li>Natural-language understanding</li><li>Ambiguous employee explanations</li><li>Evidence synthesis</li></ul></div>
            <div className="about-card"><h4>Agent / Tools</h4><ul className="bullets"><li>Dynamic multi-step evidence gathering</li><li>Choosing which enterprise source to inspect</li><li>Re-querying after discovering new information</li></ul></div>
          </div>
          <p className="lede" style={{ fontStyle: "italic", marginTop: 12 }}>"ExpenseGuard therefore tests a hybrid architecture rather than forcing every decision through an LLM."</p>
        </Section>

        <Section id="s6" title="Architecture Ladder">
          <LadderChart />
          <p className="lede" style={{ fontStyle: "italic", marginTop: 12 }}>"Complexity was added only when the previous rung exposed a measurable limitation."</p>
        </Section>

        <Section id="s7" title="Dataset &amp; Evaluation Contract">
          <div className="stat-grid">
            <div className="stat-card"><div className="value"><Metric value={d.dataset?.total} /></div><div className="label">Total claims</div></div>
            <div className="stat-card"><div className="value"><Metric value={d.dataset?.development} /></div><div className="label">Development</div></div>
            <div className="stat-card"><div className="value"><Metric value={d.dataset?.validation} /></div><div className="label">Validation</div></div>
            <div className="stat-card"><div className="value"><Metric value={d.dataset?.final_test} /></div><div className="label">Frozen final test</div></div>
            <div className="stat-card"><div className="value">22+</div><div className="label">Policy documents</div></div>
            <div className="stat-card"><div className="value">11</div><div className="label">Enterprise tables</div></div>
          </div>
          <p className="lede" style={{ fontSize: 13, marginTop: 12 }}>Hardened three times. "Decision-critical facts were deliberately moved from convenient structured fields into natural-language claim text."</p>
          <div className="pl-note" style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 12, marginTop: 8 }}>
            <span className="pl-stage" style={{ opacity: 1, display: "inline-block" }}>Easy structured case</span> → hardening → <span className="pl-stage" style={{ opacity: 1, display: "inline-block" }}>Free-text evidence, harder realistic case</span>
          </div>
          <ul className="bullets" style={{ marginTop: 12 }}>
            <li>Accuracy, FAR, APPROVE recall</li><li>Safe Automation Rate, Escalation Rate, Human Review Rate</li>
            <li>Recall@K, Full Evidence Coverage</li><li>Cost / claim, Risk-adjusted cost / 1,000 claims</li>
          </ul>
          <div className="callout-card" style={{ marginTop: 10, fontWeight: 700 }}>Exp 32 final set frozen before evaluation</div>
        </Section>

        <Section id="s8" title="Experiment Journey">
          {EXP_PHASES_7.map((p) => <ExperimentPhase phase={p} key={p.name} />)}
          <AllExperimentsTable />
        </Section>

        <Section id="s9" title="Official Architecture — Exp 30 / Exp 32">
          <OfficialArchDiagram />
          <div className="stat-grid" style={{ marginTop: 16 }}>
            <div className="stat-card good"><div className="value"><Metric value={arch.selective_resolver?.correct} suffix={`/${arch.selective_resolver?.n ?? ""}`} /></div><div className="label">Development — <Metric value={arch.selective_resolver?.accuracy_pct} suffix="%" />, 0 observed FAR</div></div>
            <div className="stat-card good"><div className="value"><Metric value={d.exp32_official?.correct} suffix={`/${d.exp32_official?.n ?? ""}`} /></div><div className="label">Final test — <Metric value={d.exp32_official?.accuracy_pct} suffix="%" />, <Metric value={d.exp32_official?.false_approvals} />/<Metric value={d.exp32_official?.non_approvable} /> observed false approvals</div></div>
            <div className="stat-card"><div className="value"><Metric value={d.exp32_path_performance?.deterministic?.correct} suffix={`/${d.exp32_path_performance?.deterministic?.n ?? ""}`} /></div><div className="label">Deterministic path</div></div>
            <div className="stat-card"><div className="value"><Metric value={d.exp32_path_performance?.llm_residual?.correct} suffix={`/${d.exp32_path_performance?.llm_residual?.n ?? ""}`} /></div><div className="label">LLM residual path</div></div>
            <div className="stat-card bad"><div className="value"><Metric value={d.exp32_path_performance?.approve_recall?.correct} suffix={`/${d.exp32_path_performance?.approve_recall?.n ?? ""}`} /></div><div className="label">APPROVE recall</div></div>
          </div>
          <p className="lede" style={{ fontWeight: 700, marginTop: 10 }}>"This remains the only independent final-test result."</p>
        </Section>

        <Section id="s10" title="Why Select a 60% System?">
          <div className="stat-grid">
            <div className="stat-card bad"><div className="value">~47%</div><div className="label">LLM-only · 3.9% FAR</div></div>
            <div className="stat-card bad"><div className="value"><Metric value={arch.fixed_workflow?.accuracy_pct} suffix="%" /></div><div className="label">Fixed workflow · <Metric value={arch.fixed_workflow?.far_pct} suffix="% FAR" /></div></div>
            <div className="stat-card good"><div className="value"><Metric value={arch.selective_resolver?.accuracy_pct} suffix="%" /></div><div className="label">Selective resolver · 0 observed FAR</div></div>
          </div>
          <p className="lede" style={{ marginTop: 12 }}>"The architecture was not selected because 60% accuracy is high. It was selected because the competing higher-accuracy workflow produced materially more false approvals."</p>
          <div className="callout-card" style={{ fontWeight: 700 }}>Architecture objective: Minimise business risk subject to useful automation.</div>
        </Section>

        <Section id="s11" title="Final Failure Analysis">
          <FailureChart categories={d.exp33_failures?.categories} total={d.exp33_failures?.total_errors} />
          <p className="lede" style={{ marginTop: 10 }}>All final-test errors occurred on the residual path.</p>
          <p className="lede" style={{ fontWeight: 700 }}>"The deterministic branch generalized; the LLM residual became the main weakness."</p>
        </Section>

        <Section id="s12" title="What Did Not Fix the Agent?">
          <div className="err-bars">
            {["Stronger prompt", "Larger GPT-4o", "Parallel tools", "Perfect policy evidence", "Improved retrieval / re-query"].map((x) => (
              <div key={x} style={{ display: "flex", justifyContent: "space-between", padding: "8px 14px", background: "#1c1414", border: "1px solid #6a2a2a", borderRadius: 8 }}>
                <span>{x}</span><span style={{ color: "var(--bad)", fontWeight: 700 }}>✗</span>
              </div>
            ))}
            {["Decision-in-code tools", "Disposition gate", "Domain guards"].map((x) => (
              <div key={x} style={{ display: "flex", justifyContent: "space-between", padding: "8px 14px", background: "#12241d", border: "1px solid #245a44", borderRadius: 8 }}>
                <span>{x}</span><span style={{ color: "var(--good)", fontWeight: 700 }}>✓</span>
              </div>
            ))}
          </div>
          <p className="lede" style={{ fontWeight: 700, marginTop: 10 }}>"The breakthrough was not a larger model. It was changing who had decision authority."</p>
        </Section>

        <Section id="s13" title="Guarded Agent">
          <GuardedArchDiagram />
          <div className="callout-card" style={{ marginTop: 10 }}>
            <b>Leading development candidate — validated on a fresh holdout (Exp 60), not yet an independently
            pre-registered final test.</b> Its early design (through Exp 52) was development/validation-selected;
            Exp 53–59 then root-caused and fixed why it had never once produced a correct APPROVE, and Exp 60
            tested the fix on 50 cases neither architecture had ever seen.
          </div>
          <div className="stat-grid" style={{ marginTop: 12 }}>
            <div className="stat-card good"><div className="value"><Metric value={d.guarded_candidate?.development?.correct} suffix={`/${d.guarded_candidate?.development?.n ?? ""}`} /></div><div className="label">Dev (Exp 52) — <Metric value={d.guarded_candidate?.development?.accuracy_pct} suffix="%" />, <Metric value={d.guarded_candidate?.development?.human_review_rate_pct} suffix="% HRR" /></div></div>
            <div className="stat-card good"><div className="value"><Metric value={d.guarded_candidate?.validation?.correct} suffix={`/${d.guarded_candidate?.validation?.n ?? ""}`} /></div><div className="label">Validation (Exp 52) — <Metric value={d.guarded_candidate?.validation?.accuracy_pct} suffix="%" />, <Metric value={d.guarded_candidate?.validation?.human_review_rate_pct} suffix="% HRR" /></div></div>
          </div>
          <h3 className="sub-h" style={{ marginTop: 24 }}>Exp 60 — fresh, never-before-seen 50-case holdout</h3>
          <FreshHoldoutTable
            holdout={d.exp60_holdout}
            rows={[
              { key: "frozen", name: "Frozen resolver (official)" },
              { key: "candidate_mini", name: "Fixed candidate, gpt-4o-mini" },
              { key: "candidate_gpt4o", name: "Fixed candidate, gpt-4o" },
            ]}
            summaryTop="The fixed candidate (gpt-4o-mini) matched the frozen design's 0% observed false-approval rate at roughly double its accuracy on this sample. Swapping to gpt-4o is not a clean upgrade — higher accuracy, but 2 new false approvals the gate did not catch."
            summaryBottom="The frozen resolver's 0% FAR and 44% accuracy conceal its biggest real weakness on this fresh data: 2 of every 5 claims that should have been approved were wrongly blocked. The fixed candidate cuts that false-rejection rate 10x (40% → 4%)."
          />

          <h3 className="sub-h" style={{ marginTop: 28 }}>Exp 61 — a second, pre-registered holdout: the "0% FAR" claim did not hold</h3>
          <p className="lede" style={{ fontSize: 13 }}>
            Exp 60 was honest but not formally pre-registered. Exp 61 named and froze the exact candidate
            architecture ("Selective Automation V3") in a manifest committed before a single one of 30 new
            holdout cases was generated — closer to Exp 32's own rigor than Exp 60's.
          </p>
          <FreshHoldoutTable
            holdout={d.exp61_holdout}
            rows={[
              { key: "frozen", name: "Frozen resolver (official)" },
              { key: "candidate", name: "V3 candidate (gpt-4o-mini)" },
            ]}
            summaryTop="This time the candidate did NOT hold 0% false approvals: X4-020, a gift paid as a 'prepaid e-voucher redeemable at various outlets,' was wrongly approved. Traced live — the require-tool gate worked correctly (the tool was consulted), but check_gift_compliance's free-text parsing did not recognize that phrasing as a cash-equivalent gift form. No fix was applied, per the manifest's own process rule: documented as a finding for a future experiment, not patched and silently re-run."
            summaryBottom="Combined across Exp 60 and Exp 61, the candidate has 1 false approval in 45 non-approvable cases (~2.2% observed, not 0%) — a materially more honest statement of its risk. The frozen resolver's own 0% FAR claim is unaffected: 0 false approvals across Exp 32, Exp 60, and Exp 61 combined (82 non-approvable cases)."
          />
          <div className="callout-card" style={{ marginTop: 10 }}>
            <b>Why Exp 61 is pre-registered but the candidate still isn't "formally validated":</b> Exp 61 is a
            pre-registered <i>stress-test</i> holdout, built to try to break the fix, not to serve as the
            project's replacement final-test protocol. Promotion to official status would require a separately
            frozen evaluation specifically designed for that decision, at Exp 32's scale — not a re-use of a
            stress test, however rigorous.
          </div>
        </Section>

        <Section id="s14" title="Higher Accuracy ≠ Better Operating Architecture">
          <CostTwist scenarios={d.cost_scenarios} />
        </Section>

        <Section id="s15" title="Build vs. Buy">
          <p className="lede" style={{ fontStyle: "italic" }}>Rent commodity intelligence. Own domain-specific control.</p>
          <BuildVsBuyTable />
        </Section>

        <Section id="s16" title="Responsible AI / Security">
          <RiskTable />
          <h3 className="sub-h" style={{ marginTop: 24 }}>OWASP Top 10 for LLM Applications (2026)</h3>
          <OwaspTable />
        </Section>

        <Section id="s17" title="Build vs. Operate Decision">
          <DecisionMatrix arch={arch} d={d} />
        </Section>

        <Section id="s18" title="Presentation Demo Cases">
          <div className="build-table">
            {DEMO_CASES.map((c) => (
              <div className="build-row" style={{ gridTemplateColumns: "120px 1fr 1fr 120px" }} key={c.id}>
                <div className="mono-cell">{c.id}</div><div>{c.label}</div><div style={{ color: "var(--text-dim)" }}>{c.note}</div>
                <div><button className="chunk-toggle" onClick={() => navigator.clipboard?.writeText(c.id)}>Copy ID</button></div>
              </div>
            ))}
          </div>
          <h3 className="sub-h" style={{ marginTop: 20 }}>Failed Architecture Example</h3>
          <div className="callout-card bad">
            <b>X2-026</b> — gpt-4o-mini got this correct; swapping in gpt-4o (Exp 46) regressed it. A larger
            model stopping after fewer turns, missing evidence gpt-4o-mini gathered — direct evidence a
            bigger model does not fix a reasoning-architecture problem.
          </div>
        </Section>

        <Section id="s19" title="Limitations">
          <ul className="bullets">
            <li>Synthetic benchmark — not production financial data</li>
            <li>Same-model blind spot: every claim note, in every split including both fresh holdouts, was drafted by the same model (gpt-4o-mini) the system also uses to decide them — this benchmark cannot rule out that some measured accuracy reflects the model parsing its own writing style rather than reasoning that would transfer to real, human-written claims</li>
            <li>Official blind evidence is Exp 32 only — that result cannot be re-earned and still governs the shipped architecture</li>
            <li>Validation influenced both the Exp 52 candidate design and, later, the Exp 53–59 fixes built to close its APPROVE blind spot</li>
            <li>Exp 60 is a real, independently-labeled fresh holdout, but not a formally pre-registered freeze-and-final-test in the same sense as Exp 32</li>
            <li>A narrower, related gap was found in a smaller follow-up check after Exp 60 (a tool consulted but given content that only superficially satisfies its check, not never consulted at all) — disclosed, not yet fixed</li>
            <li>Prompt/retrieval injection remains a residual risk</li>
            <li>Residual LLM path remains weak</li>
            <li>The live demo's "agent" endpoint now runs the actual Exp 59–61 candidate; it's still an unauthenticated local-only dev server with no rate limiting, meant to be run locally and stopped after a demo, not deployed as-is</li>
            <li>Real deployment requires shadow evaluation, access controls, privacy controls and monitoring</li>
          </ul>
          <p className="lede" style={{ marginTop: 10 }}>"A formal, pre-registered freeze-and-larger-holdout would be required before the guarded candidate could be called a validated replacement for the official architecture."</p>
          <p className="lede">"The frozen resolver still ships officially — not because it is cheaper (a sensitivity check found that advantage does not survive diagnostic final-run safety numbers), but because it is the only design with an authorized, frozen final-test result."</p>
        </Section>

        <Section id="s20" title="Final Takeaways">
          <div className="about-grid">
            <div className="about-card"><h4>1. Grounding ≠ Reasoning</h4><p>Better retrieval did not automatically improve decisions.</p></div>
            <div className="about-card"><h4>2. Autonomy ≠ Value</h4><p>The initial agent added failure modes without sufficient benefit.</p></div>
            <div className="about-card"><h4>3. Deterministic ≠ Automatically Safe</h4><p>Code is only reliable with trustworthy inputs and validated applicability boundaries.</p></div>
            <div className="about-card"><h4>4. Accuracy ≠ Business Value</h4><p>The more accurate guarded candidate had higher human-review cost and a lower total operating cost at dev/validation rates — but that cost edge isn't robust, so the cheaper-looking design still didn't ship.</p></div>
          </div>
          <div className="callout-card" style={{ marginTop: 16, fontWeight: 700, textAlign: "center" }}>"Reliability came from assigning authority to the component best suited to each decision."</div>
          <p className="lede" style={{ textAlign: "center", marginTop: 8 }}>"Enterprise AI should be only as sophisticated as necessary to maximise safe automation at the lowest total operating cost."</p>
        </Section>

        <Section id="s21" title="Project Documents">
          <div className="build-table">
            {DOCS.map(([label, path]) => (
              <div className="build-row" style={{ gridTemplateColumns: "1fr 200px" }} key={path}>
                <div>{label}</div>
                <div><a className="chunk-toggle" style={{ display: "inline-block", textDecoration: "none" }} href={`http://localhost:8787/docs/${path}`} target="_blank" rel="noreferrer">Open (requires backend running)</a></div>
              </div>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}

function UserFlow() {
  const [openStage, setOpenStage] = useState(null);
  const stages = [
    { id: "submit", label: "Employee submits expense claim", info: "A bill + free-text note, nothing else structured." },
    { id: "receive", label: "ExpenseGuard receives claim + free-text note", info: "Same input schema for every architecture tested." },
    { id: "extract", label: "Extract decision-relevant facts", info: "rules_text.py parses the note; never reads a label." },
    { id: "policy", label: "Determine applicable policy", info: "Date/region/document-type compatibility (M4 filter, Exp 9)." },
    { id: "evidence", label: "Determine required enterprise evidence", info: "Approvals, delegations, travel requests, budgets, prior claims." },
    { id: "gate", label: "Can deterministic logic safely resolve it?", info: "A runtime-visible conclusiveness signal only — never a label." },
    { id: "yes", label: "YES → Apply validated policy mechanics in code", info: "$0, instant, 100% accurate on unseen final-test data." },
    { id: "no", label: "NO → Retrieve policy evidence + resolve enterprise facts", info: "K=8, 600/100 chunking, dense embeddings, M4 filter + hybrid facts." },
    { id: "reason", label: "Decision reasoning", info: "Single-shot LLM (frozen) or bounded agent with guarded tools (candidate)." },
    { id: "decide", label: "APPROVE / REJECT / REQUEST INFO / ESCALATE", info: "One of four outcomes, always." },
    { id: "human", label: "Human reviewer if needed", info: "ESCALATE is a first-class, deliberately safe outcome." },
  ];
  return (
    <div className="timeline" style={{ maxWidth: 700 }}>
      {stages.map((s, i) => (
        <div key={s.id} className="pl-stage reached" style={{ cursor: "pointer", marginBottom: 8 }} onClick={() => setOpenStage(openStage === s.id ? null : s.id)}>
          <div className="pl-stage-num">{i + 1}</div>
          <div className="pl-stage-body">
            <div className="pl-stage-title">{s.label}</div>
            {openStage === s.id && <div className="pl-stage-choice">{s.info}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

function OfficialArchDiagram() {
  return (
    <div className="pipeline">
      {["Claim", "Deterministic Resolver", "Conclusive?"].map((t) => (
        <React.Fragment key={t}><div className="pl-stage reached"><div className="pl-stage-body"><div className="pl-stage-title">{t}</div></div></div><div className="pl-arrow">↓</div></React.Fragment>
      ))}
      <div style={{ display: "flex", gap: 14 }}>
        <div className="pl-stage reached terminal" style={{ flex: 1 }}><div className="pl-stage-body"><div className="pl-stage-title">YES → Deterministic Decision</div></div></div>
        <div className="pl-stage reached terminal" style={{ flex: 1 }}><div className="pl-stage-body"><div className="pl-stage-title">NO → M4-Filtered Dense RAG → Enterprise Fact Resolution → Single-Shot LLM</div></div></div>
      </div>
      <div className="pl-arrow">↓</div>
      <div className="pl-stage reached terminal"><div className="pl-stage-body"><div className="pl-stage-title">Final Outcome / Escalation</div></div></div>
    </div>
  );
}

function GuardedArchDiagram() {
  const steps = ["Claim", "Agent Orchestration", "Retrieve / Inspect Evidence", "Domain-Specific Compliance Tool", "Applicability Guard", "Tool-Computed Disposition", "Disposition Gate", "LLM may explain/orchestrate but cannot override a qualified deterministic disposition", "Final Decision / Human Escalation"];
  return (
    <div className="pipeline">
      {steps.map((t, i) => (
        <React.Fragment key={t}>
          <div className="pl-stage reached" style={{ borderColor: "var(--warn)" }}><div className="pl-stage-body"><div className="pl-stage-title">{t}</div></div></div>
          {i < steps.length - 1 && <div className="pl-arrow">↓</div>}
        </React.Fragment>
      ))}
    </div>
  );
}

function FailureChart({ categories, total }) {
  if (!categories) return <p className="lede">{MV}</p>;
  const labelMap = { policy_reasoning_composition: "Policy reasoning / composition error", missing_information_confusion: "Missing-information confusion", resolved_fact_error: "Resolved-fact error", missed_escalation: "Missed escalation", over_conservative_bias: "Over-conservative bias" };
  const entries = Object.entries(categories).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, v]) => v));
  return (
    <div className="err-bars">
      {entries.map(([k, v]) => (
        <div className="err-bar-row" key={k}>
          <div className="err-bar-name">{labelMap[k] || k}</div>
          <div className="err-bar-track"><div className="err-bar-fill" style={{ width: `${(v / max) * 100}%` }} /><span className="err-bar-value">{v}/{total}</span></div>
        </div>
      ))}
    </div>
  );
}

function FreshHoldoutTable({ holdout, rows, summaryTop, summaryBottom }) {
  if (!holdout) return <p className="lede">{MV}</p>;
  return (
    <div>
      <div className="stat-grid">
        {rows.map((r) => (
          <div className={`stat-card ${holdout[r.key].false_approvals === 0 ? "good" : "bad"}`} key={r.key}>
            <div className="value"><Metric value={holdout[r.key].correct} suffix={`/${holdout[r.key].n}`} /></div>
            <div className="label">{r.name} — <Metric value={holdout[r.key].accuracy_pct} suffix="%" />, <Metric value={holdout[r.key].false_approvals} /> false approvals (<Metric value={holdout[r.key].far_pct} suffix="%" /> FAR), APPROVE recall <Metric value={holdout[r.key].approve_recall.correct} suffix={`/${holdout[r.key].approve_recall.n}`} /></div>
          </div>
        ))}
      </div>
      {summaryTop && <p className="lede" style={{ fontWeight: 700, marginTop: 10 }}>{summaryTop}</p>}
      <h4 style={{ marginTop: 18 }}>Accuracy alone understates what changed — the safe-automation breakdown</h4>
      <div className="build-table" style={{ marginTop: 8 }}>
        <div className="build-row" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr" }}>
          {["", "Safely automated, correct", "False approvals", "False rejections (real approvable, wrongly blocked)", "Unnecessary escalations"].map((h) => (
            <div key={h} style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>{h}</div>
          ))}
        </div>
        {rows.map((r) => {
          const h = holdout[r.key];
          return (
            <div className="build-row" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr" }} key={r.key}>
              <div>{r.name}</div>
              <div style={{ fontWeight: 700 }}>{h.safely_automated}/{h.n} = {h.safely_automated_pct}%</div>
              <div style={{ color: h.false_approvals > 0 ? "var(--bad)" : "inherit", fontWeight: h.false_approvals > 0 ? 700 : 400 }}>{h.false_approvals}</div>
              <div style={{ color: h.false_rejections_pct >= 20 ? "var(--bad)" : "inherit", fontWeight: h.false_rejections_pct >= 20 ? 700 : 400 }}>{h.false_rejections}/{h.n} = {h.false_rejections_pct}%</div>
              <div>{h.unnecessary_escalations}</div>
            </div>
          );
        })}
      </div>
      {summaryBottom && <p className="lede" style={{ marginTop: 10 }}>{summaryBottom}</p>}
    </div>
  );
}

function CostTwist({ scenarios }) {
  const [scenario, setScenario] = useState("base");
  if (!scenarios) return <p className="lede">{MV}</p>;
  const s = scenarios[scenario];
  const max = Math.max(s.fixed_workflow, s.frozen_final_test, s.guarded_dev);
  const rows = [
    { name: "Fixed workflow", v: s.fixed_workflow, cls: "bad" },
    { name: "Frozen resolver (official)", v: s.frozen_final_test, cls: "good" },
    { name: "Guarded candidate", v: s.guarded_dev, cls: "warn" },
  ];
  return (
    <div>
      <div className="scenario-toggle">{Object.keys(scenarios).map((k) => <button key={k} className={k === scenario ? "active" : ""} onClick={() => setScenario(k)}>{k}</button>)}</div>
      <div className="scenario-label">{s.label} — total expected cost / 1,000 claims (scripts/cost_model.py)</div>
      <div className="cost-bars">
        {rows.map((r) => (
          <div className="cost-bar-row" key={r.name}>
            <div className="cost-bar-name">{r.name}</div>
            <div className="cost-bar-track"><div className={`cost-bar-fill ${r.cls}`} style={{ width: `${(r.v / max) * 100}%` }} /><span className="cost-bar-value">${r.v.toLocaleString()}</span></div>
          </div>
        ))}
      </div>
      <div className="stat-grid" style={{ marginTop: 14 }}>
        <div className="stat-card"><div className="value">18.6–22%</div><div className="label">Frozen escalation rate</div></div>
        <div className="stat-card warn"><div className="value">~34%</div><div className="label">Guarded candidate escalation rate</div></div>
      </div>
      <p className="lede" style={{ marginTop: 10 }}>"The guarded candidate improved predictive quality, but escalated approximately 1.5–1.8× more claims."</p>
      <div className="callout-card" style={{ fontWeight: 700, marginTop: 8 }}>
        Guarded candidate cheaper in every scenario shown — at its dev/validation rates (bars above, computed
        live from <code>scripts/cost_model.py</code>). That advantage does <u>not</u> survive its diagnostic
        final-run safety numbers — see <code>docs/cost_and_business_impact.md</code>'s sensitivity analysis.
        This is why the frozen resolver still ships: not because it's cheaper, but because it's the only
        design with an authorized, frozen final-test result to check the cost model against.
      </div>
      <div className="callout-card bad" style={{ marginTop: 8, fontWeight: 700, textAlign: "center" }}>"Human-review cost dominated inference cost."</div>
      <div className="callout-card" style={{ marginTop: 8, fontWeight: 700, textAlign: "center" }}>"The best-performing AI architecture was not the best operating architecture."</div>
    </div>
  );
}

const BVB_ROWS = [
  ["Interface / Serving", "Own", "React + Vite frontend, stdlib-only Python backend"],
  ["Orchestration", "Own", "Hand-written bounded ReAct loop (src/agent.py)"],
  ["Foundation Model", "Rent", "openai/gpt-4o-mini (paid) · llama3.2:3b (free)"],
  ["Embeddings", "Rent", "voyageai/voyage-4-lite (frozen, Exp 8)"],
  ["Retrieval", "Own", "In-repo chunking + retrieval, no vector DB"],
  ["Policy Logic", "Own", "rules_v2.py, rules_text.py, hybrid_facts.py, workflow_v2.py"],
  ["Enterprise Tools", "Own (synthetic)", "Typed read-only tools over synthetic fixtures"],
  ["Evaluation Harness", "Own", "evaluate.py, metrics.py, freeze-manifest process"],
  ["Observability", "Own", "run_log.jsonl, per-experiment summary.json, full agent traces"],
  ["Dataset", "Own (synthetic)", "150 claims, seed 6202, deterministic generator"],
  ["Infrastructure", "Rent", "OpenRouter API, Ollama local runtime"],
];
function BuildVsBuyTable() {
  return (
    <div className="build-table">
      <div className="build-row" style={{ gridTemplateColumns: "180px 100px 1fr" }}>
        <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Layer</div>
        <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Own / Rent</div>
        <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Technology</div>
      </div>
      {BVB_ROWS.map(([layer, choice, tech]) => (
        <div className="build-row" style={{ gridTemplateColumns: "180px 100px 1fr" }} key={layer}>
          <div>{layer}</div><div><span className={`chip ${choice.startsWith("Own") ? "chip-own" : "chip-rent"}`}>{choice}</span></div><div className="mono-cell">{tech}</div>
        </div>
      ))}
    </div>
  );
}

const OWASP_ROWS = [
  ["LLM01", "Prompt Injection", "Tested", "Residual risk — retrieval-text injection succeeded once, disclosed unsolved"],
  ["LLM02", "Sensitive Information Disclosure", "Tested", "No cross-employee data disclosed"],
  ["LLM03", "Excessive Agency", "Tested — mitigated", "Disposition gate, domain guards, step caps, call dedup"],
  ["LLM04", "Supply Chain", "Tested", "Dependency inventory clean; npm audit: 1 moderate finding, documented"],
  ["LLM05", "Data / Model Poisoning", "Not applicable (training) / Partially applicable (retrieval corpus)", "No fine-tuning occurs; retrieval-corpus integrity scored under LLM01/09 instead"],
  ["LLM06", "Unbounded Consumption", "Tested", "Budget cap verified to actually trip; step cap bounds worst case"],
  ["LLM07", "Misinformation", "Tested", "0 fabricated citations found across 897 checked"],
  ["LLM08", "Hidden Context Exposure", "Partially tested", "Renamed/broadened from \"System Prompt Leakage\" — that sub-case tested (not echoed, via a parse-failure fallback, not a proven deliberate refusal); the newly added RAG-schema/hidden-policy-logic scope not separately probed"],
  ["LLM09", "Vector / Embedding Weaknesses", "Tested / scoped", "Closed, allowlisted, precomputed corpus — no live ingestion path"],
  ["LLM10", "Improper Output Handling", "Tested", "No unsafe HTML sink; React escapes by default"],
];
function OwaspTable() {
  return (
    <div className="build-table">
      <div className="build-row" style={{ gridTemplateColumns: "70px 220px 200px 1fr" }}>
        <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>#</div>
        <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Category</div>
        <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Status</div>
        <div style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>Residual risk / note</div>
      </div>
      {OWASP_ROWS.map(([id, name, status, note]) => (
        <div className="build-row" style={{ gridTemplateColumns: "70px 220px 200px 1fr" }} key={id}>
          <div className="mono-cell">{id}</div><div>{name}</div><div style={{ color: (id === "LLM01" || id === "LLM08") ? "var(--bad)" : "var(--good)" }}>{status}</div><div>{note}</div>
        </div>
      ))}
    </div>
  );
}

function DecisionMatrix({ arch, d }) {
  const rows = [
    { name: "Rules", acc: "68.6%", far: "11.5%", esc: "15.7%", cost: "$0", complexity: "Low", status: "Rejected" },
    { name: "RAG (tuned)", acc: "31.4%", far: "0.0%", esc: "4.3%", cost: "Low", complexity: "Low-Med", status: "Intermediate" },
    { name: "Fixed Workflow", acc: arch.fixed_workflow ? `${arch.fixed_workflow.accuracy_pct}%` : MV, far: arch.fixed_workflow ? `${arch.fixed_workflow.far_pct}%` : MV, esc: "14.3%", cost: "$0", complexity: "Medium", status: "Rejected" },
    { name: "Bounded Agent", acc: "53.8%", far: "30.0%", esc: "23.1%", cost: "Med", complexity: "High", status: "Rejected" },
    { name: "Frozen Selective Resolver", acc: arch.selective_resolver ? `${arch.selective_resolver.accuracy_pct}%` : MV, far: "0.0%", esc: "18.6–22%", cost: "Lowest", complexity: "Medium", status: "Official — Preferred Operating Architecture" },
    { name: "Guarded Agent (fixed, Exp 53–61)", acc: d.exp60_holdout ? `${d.exp60_holdout.candidate_mini.accuracy_pct}%` : MV, far: (d.exp60_holdout && d.exp61_holdout) ? `~${Math.round(1000 * (d.exp60_holdout.candidate_mini.false_approvals + d.exp61_holdout.candidate.false_approvals) / (d.exp60_holdout.n - d.exp60_holdout.candidate_mini.approve_recall.n + d.exp61_holdout.n - d.exp61_holdout.candidate.approve_recall.n)) / 10}% combined` : MV, esc: "~34%", cost: "Higher", complexity: "Highest", status: "Leading development candidate — not promoted to official" },
  ];
  return (
    <div className="build-table">
      <div className="build-row" style={{ gridTemplateColumns: "180px 80px 80px 90px 90px 90px 1fr" }}>
        {["Architecture", "Accuracy", "FAR", "Escalation", "Cost", "Complexity", "Decision"].map((h) => <div key={h} style={{ fontWeight: 700, fontSize: 11, color: "var(--text-dim)" }}>{h}</div>)}
      </div>
      {rows.map((r) => (
        <div className="build-row" style={{ gridTemplateColumns: "180px 80px 80px 90px 90px 90px 1fr" }} key={r.name}>
          <div style={{ fontWeight: r.status.startsWith("Official") ? 700 : 400 }}>{r.name}</div>
          <div>{r.acc}</div><div>{r.far}</div><div>{r.esc}</div><div>{r.cost}</div><div>{r.complexity}</div>
          <div style={{ color: r.status.startsWith("Official") ? "var(--good)" : r.status.includes("Rejected") ? "var(--bad)" : "var(--text-dim)", fontWeight: 700 }}>{r.status}</div>
        </div>
      ))}
    </div>
  );
}
