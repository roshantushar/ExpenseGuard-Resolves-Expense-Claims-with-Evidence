import React, { useMemo, useState } from "react";
import DesignPanel from "./DesignPanel.jsx";

export default function Explorer({ cases }) {
  const [query, setQuery] = useState("");
  const [split, setSplit] = useState("ALL");
  const [family, setFamily] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);

  const families = useMemo(() => ["ALL", ...Array.from(new Set(cases.map((c) => c.case_family))).sort()], [cases]);

  const filtered = useMemo(() => {
    return cases.filter((c) => {
      if (split !== "ALL" && c.split !== split) return false;
      if (family !== "ALL" && c.case_family !== family) return false;
      if (query && !c.case_id.toLowerCase().includes(query.toLowerCase()) && !c.claim.bill.merchant.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [cases, query, split, family]);

  const selected = cases.find((c) => c.case_id === selectedId);

  return (
    <div className="explorer">
      <div className="sidebar">
        <div className="search">
          <input placeholder="Search case id or merchant…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="filters">
          <select value={split} onChange={(e) => setSplit(e.target.value)}>
            <option value="ALL">All splits</option>
            <option value="DEVELOPMENT">Development</option>
            <option value="VALIDATION">Validation</option>
            <option value="FINAL_TEST">Final test</option>
          </select>
          <select value={family} onChange={(e) => setFamily(e.target.value)}>
            {families.map((f) => (
              <option key={f} value={f}>
                {f === "ALL" ? "All families" : f}
              </option>
            ))}
          </select>
        </div>
        <div className="case-list">
          {filtered.map((c) => (
            <div key={c.case_id} className={`case-row ${c.case_id === selectedId ? "selected" : ""}`} onClick={() => setSelectedId(c.case_id)}>
              <div className="id">{c.case_id}</div>
              <div className="fam">{c.case_family}</div>
              <div className="badges">
                <span className={`badge split-${c.split}`}>{c.split === "FINAL_TEST" ? "final" : c.split.toLowerCase()}</span>
                <span className={`badge ${c.frozen.correct ? "ok" : "wrong"}`}>frozen {c.frozen.correct ? "✓" : "✗"}</span>
                <span className={`badge ${c.agent.correct ? "ok" : "wrong"}`}>agent {c.agent.correct ? "✓" : "✗"}</span>
              </div>
            </div>
          ))}
          {filtered.length === 0 && <div style={{ padding: 16, color: "var(--text-dim)", fontSize: 13 }}>No cases match.</div>}
        </div>
      </div>

      <div className="detail">
        {!selected && <div className="empty">Pick a claim from the list to see how each design processed it.</div>}
        {selected && (
          <>
            <div className="claim-card">
              <h3>The claim (exactly what the system sees)</h3>
              <div className="claim-fields">
                <div>
                  <div className="k">Case ID</div>
                  {selected.case_id}
                </div>
                <div>
                  <div className="k">Merchant</div>
                  {selected.claim.bill.merchant}
                </div>
                <div>
                  <div className="k">Amount</div>
                  {selected.claim.bill.total} {selected.claim.bill.currency}
                </div>
                <div>
                  <div className="k">Country / City</div>
                  {selected.claim.bill.country} / {selected.claim.bill.city}
                </div>
                <div>
                  <div className="k">Transaction date</div>
                  {selected.claim.transaction_date}
                </div>
                <div>
                  <div className="k">Merchant category</div>
                  {selected.claim.bill.merchant_category}
                </div>
              </div>
              <div className="claim-note">"{selected.claim.employee_description}"</div>
            </div>

            <div className="panels">
              <DesignPanel title="Frozen design" subtitle="deterministic → single-shot LLM (official, shipped)" caseObj={selected} designKey="frozen" backendDesign="frozen" />
              <DesignPanel title="Guarded agent" subtitle="deterministic → bounded agent with code-computed dispositions (best validated)" caseObj={selected} designKey="agent" backendDesign="agent" />
            </div>

            <div className="gt-card">
              <h3 style={{ margin: "0 0 8px", fontSize: 13.5, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.5 }}>Ground truth (private, evaluator-only)</h3>
              <span className={`decision-pill ${selected.ground_truth.expected_decision}`}>{selected.ground_truth.expected_decision}</span>
              <p style={{ fontSize: 13, marginTop: 10, color: "#d6dae3" }}>{selected.ground_truth.reason}</p>
              <div style={{ fontSize: 11.5, color: "var(--text-dim)" }}>Controlling clauses: {selected.ground_truth.required_policy_ids.join(", ")}</div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
