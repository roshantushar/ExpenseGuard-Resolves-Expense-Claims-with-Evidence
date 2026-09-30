import React from "react";
import { COSTS } from "../architectureData.js";

const GUARD_TOOLS = new Set([
  "check_workflow_compliance", "check_approval", "check_meal_compliance", "check_hotel_compliance",
  "check_project_budget", "check_ground_transport_compliance", "check_gift_compliance"
]);
const LOOKUP_TOOLS = new Set([
  "search_policy_corpus", "get_employee_profile", "get_travel_request", "get_exception_record",
  "search_previous_expenses", "get_approval_delegation", "get_manager_approval"
]);

function Stage({ n, title, choice, reached, terminal, children }) {
  return (
    <div className={`pl-stage ${reached ? "reached" : "skipped"} ${terminal ? "terminal" : ""}`}>
      <div className="pl-stage-num">{n}</div>
      <div className="pl-stage-body">
        <div className="pl-stage-title">{title}</div>
        <div className="pl-stage-choice">{choice}</div>
        {children}
      </div>
    </div>
  );
}

function Arrow() {
  return <div className="pl-arrow">↓</div>;
}

/** Full input→output pipeline for one design, on one specific case — which branch actually fired is
 * highlighted from real data (frozen.path, or an empty agent trace for the shared deterministic layer,
 * verified to agree with frozen.path on all 150 exported cases), everything else is dimmed. */
export default function PipelineDiagram({ design, result }) {
  const deterministic = design === "frozen" ? result.path === "deterministic" : !(result.trace || []).length;
  const trace = result.trace || [];
  const guardToolsCalled = [...new Set(trace.filter((s) => GUARD_TOOLS.has(s.tool)).map((s) => s.tool))];
  const lookupToolsCalled = [...new Set(trace.filter((s) => LOOKUP_TOOLS.has(s.tool)).map((s) => s.tool))];
  const gated = trace.some((s) => s.data && typeof s.data === "object" && s.data.policy_disposition);

  return (
    <div className="pipeline">
      <Stage n="in" title="Input" choice="The claim: a bill + free-text note, nothing else structured — identical input for both designs" reached />
      <Arrow />
      <Stage
        n="1"
        title="Deterministic extraction"
        choice="rules_text.py parses the note from free text; rules_v2.py applies policy mechanics — never reads a label (Exp 2, 12). Shared, identical code in both designs."
        reached
      />
      <Arrow />
      <Stage
        n="2"
        title="Conclusive?"
        choice="A runtime-visible signal only — a rule fired AND every needed field was extracted (Exp 12B/30 tuned this gate)"
        reached
      />
      {deterministic ? (
        <>
          <Arrow />
          <Stage n="3" title="Code decides" choice="$0, no LLM call — 100% accurate on the unseen final test (Exp 32)" reached terminal>
            <div className="pl-note">This case resolved here. Nothing below ran.</div>
          </Stage>
        </>
      ) : design === "frozen" ? (
        <>
          <Arrow />
          <Stage
            n="3"
            title="Residual: RAG + resolved facts"
            choice="K=8 chunks · 600/100-token chunking · dense voyage-4-lite embeddings · M4 date/region/doc-type filter (Exp 6–9) + hybrid_facts.py (H1–H4, Exp 12)"
            reached
          />
          <Arrow />
          <Stage n="4" title="Single-shot LLM" choice="gpt-4o-mini, temperature 0 — one call, no tools, no re-asking (frozen at Exp 30)" reached terminal>
            <div className="pl-note">This is the system's one known weak link: 28.6% accurate on its own (Exp 32/33).</div>
          </Stage>
        </>
      ) : (
        <>
          <Arrow />
          <Stage
            n="3"
            title="Bounded ReAct agent"
            choice="Max 8 turns, call de-duplication, read-only tools only (Exp 20/28) — the model chooses what to look up"
            reached
          >
            {lookupToolsCalled.length > 0 && (
              <div className="pl-note">Called this run: {lookupToolsCalled.join(", ")}</div>
            )}
          </Stage>
          <Arrow />
          <Stage
            n="4"
            title="Guarded compliance tools"
            choice="Tools compute the policy disposition in code, not just fetch facts (Exp 40) — each domain-guarded to only the claim types it applies to (Exp 43)"
            reached={guardToolsCalled.length > 0}
          >
            {guardToolsCalled.length > 0 && <div className="pl-note">Called this run: {guardToolsCalled.join(", ")}</div>}
          </Stage>
          <Arrow />
          <Stage
            n="5"
            title="Disposition gate"
            choice="If a tool already computed the correct disposition and the model disagrees anyway, the tool wins (Exp 41)"
            reached={gated}
            terminal
          >
            <div className="pl-note">{gated ? "A tool's computed disposition was trusted over the model's own reasoning on this case." : "No guarded tool returned a disposition here — the model's own reasoning was used."}</div>
          </Stage>
        </>
      )}
      <Arrow />
      <Stage n="out" title="Output" choice="decision + policy_evidence + explanation, fully logged and inspectable" reached terminal />
      {(() => {
        const c = COSTS[design === "frozen" ? "Frozen resolver — dev" : "Guarded agent (candidate)"];
        if (!c) return null;
        return (
          <div className="mini-flow-cost" style={{ marginTop: 10 }}>
            <div className="risk-k">This architecture's business cost per 1,000 claims (base scenario)</div>
            <div className="cost-mini-grid">
              <div><span className="cost-mini-k">AI cost</span><span className="cost-mini-v">${c.ai.toFixed(2)}</span></div>
              <div><span className="cost-mini-k">Human review</span><span className="cost-mini-v">${c.human.toLocaleString()}</span></div>
              <div><span className="cost-mini-k">False approval</span><span className="cost-mini-v">${c.falseApproval.toLocaleString()}</span></div>
              <div className="cost-mini-total"><span className="cost-mini-k">Total</span><span className="cost-mini-v">${c.total.toLocaleString()}</span></div>
            </div>
            <div className="cost-mini-meta">Architecture-level figure (not specific to this one case) · escalation rate {c.escalation} · FAR {c.far} · full model: docs/cost_and_business_impact.md</div>
          </div>
        );
      })()}
    </div>
  );
}
