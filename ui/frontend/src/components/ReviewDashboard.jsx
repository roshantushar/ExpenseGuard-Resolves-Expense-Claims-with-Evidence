import React, { useEffect, useMemo, useState } from "react";

// Maya's persona dashboard: "here's today's queue, here's what actually needs you." Uses the frozen
// (official, shipped) design's decision for every one of the 150 cases as a stand-in for "today's claims" --
// this is a demo/story surface, not a live production queue, but every number on it is a real saved result,
// not invented.

const FLAG_PRIORITY = { ESCALATE: 0, REQUEST_INFORMATION: 1, REJECT: 2, APPROVE: 3 };
const STORAGE_KEY = "expenseguard_reviewer_actions_v1";

function flagsFor(c) {
  const d = c.frozen;
  const flags = [];
  if (d.decision === "ESCALATE") flags.push({ label: "Needs your review", tone: "bad" });
  if (d.decision === "REQUEST_INFORMATION") {
    flags.push({ label: `Missing: ${(d.missing_fields || []).join(", ") || "info"}`, tone: "warn" });
  }
  if (d.path === "llm_residual") flags.push({ label: "LLM-reasoned", tone: "neutral" });
  else flags.push({ label: "Instant · $0", tone: "neutral" });
  return flags;
}

function loadActions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveActions(actions) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(actions));
  } catch {
    /* private window / storage blocked — review actions just won't persist across reloads */
  }
}

export default function ReviewDashboard({ cases }) {
  const [filter, setFilter] = useState("ALL");
  const [openId, setOpenId] = useState(null);
  const [actions, setActions] = useState(() => loadActions());

  useEffect(() => {
    saveActions(actions);
  }, [actions]);

  function setStatus(caseId, status) {
    setActions((prev) => {
      const current = prev[caseId] || {};
      const next = { ...current, status: current.status === status ? null : status };
      return { ...prev, [caseId]: next };
    });
  }

  function setComment(caseId, comment) {
    setActions((prev) => ({ ...prev, [caseId]: { ...(prev[caseId] || {}), comment } }));
  }

  const todays = useMemo(
    () => [...cases].sort((a, b) => FLAG_PRIORITY[a.frozen.decision] - FLAG_PRIORITY[b.frozen.decision] || a.case_id.localeCompare(b.case_id)),
    [cases]
  );

  const counts = useMemo(() => {
    const c = { total: todays.length, escalate: 0, info: 0, reject: 0, approve: 0, deterministic: 0 };
    for (const t of todays) {
      if (t.frozen.decision === "ESCALATE") c.escalate++;
      else if (t.frozen.decision === "REQUEST_INFORMATION") c.info++;
      else if (t.frozen.decision === "REJECT") c.reject++;
      else if (t.frozen.decision === "APPROVE") c.approve++;
      if (t.frozen.path === "deterministic") c.deterministic++;
    }
    return c;
  }, [todays]);

  const needsMaya = counts.escalate;
  const autoResolved = counts.total - needsMaya;

  const filtered = filter === "ALL" ? todays : todays.filter((c) => c.frozen.decision === filter);

  return (
    <div className="overview">
      <div className="overview-inner">
        <h1>Maya's queue — today</h1>
        <p className="lede">
          Every one of today's {counts.total} claims, triaged by the shipped architecture's own decision —
          sorted so whatever actually needs a human floats to the top. This is a story surface built from
          real saved results, not a live production queue.
        </p>

        <div className="stat-grid" style={{ marginTop: 18 }}>
          <div className="stat-card">
            <div className="label">Claims today</div>
            <div className="value">{counts.total}</div>
          </div>
          <div className="stat-card good">
            <div className="label">Auto-resolved, no review needed</div>
            <div className="value">{autoResolved} <span style={{ fontSize: 14, fontWeight: 400 }}>({((100 * autoResolved) / counts.total).toFixed(0)}%)</span></div>
          </div>
          <div className="stat-card bad">
            <div className="label">Needs Maya's review</div>
            <div className="value">{needsMaya} <span style={{ fontSize: 14, fontWeight: 400 }}>({((100 * needsMaya) / counts.total).toFixed(0)}%)</span></div>
          </div>
          <div className="stat-card warn">
            <div className="label">Sent back for missing info</div>
            <div className="value">{counts.info}</div>
          </div>
          <div className="stat-card">
            <div className="label">Resolved instantly, $0 (no LLM call)</div>
            <div className="value">{counts.deterministic}</div>
          </div>
        </div>

        <div className="dash-filters">
          {[
            ["ALL", "All"],
            ["ESCALATE", "Needs review"],
            ["REQUEST_INFORMATION", "Missing info"],
            ["REJECT", "Rejected"],
            ["APPROVE", "Approved"],
          ].map(([k, label]) => (
            <button key={k} className={`dash-filter-btn ${filter === k ? "active" : ""}`} onClick={() => setFilter(k)}>
              {label}
            </button>
          ))}
        </div>

        <div className="dash-queue">
          {filtered.map((c) => {
            const flags = flagsFor(c);
            const open = openId === c.case_id;
            const d = c.frozen;
            const action = actions[c.case_id] || {};
            return (
              <div key={c.case_id} className={`dash-row ${c.frozen.decision === "ESCALATE" ? "priority" : ""}`}>
                <div className="dash-row-head" onClick={() => setOpenId(open ? null : c.case_id)}>
                  <span className={`decision-pill ${c.frozen.decision}`}>{c.frozen.decision}</span>
                  <div className="dash-row-main">
                    <div className="dash-row-title">
                      <span className="mono-cell">{c.case_id}</span> — {c.claim.bill.merchant}, {c.claim.bill.total} {c.claim.bill.currency}
                    </div>
                    <div className="dash-row-flags">
                      {flags.map((f, i) => (
                        <span key={i} className={`flag-chip ${f.tone}`}>{f.label}</span>
                      ))}
                      {action.status && (
                        <span className={`flag-chip ${action.status === "ACCEPTED" ? "good" : "bad"}`}>
                          You {action.status === "ACCEPTED" ? "accepted" : "rejected"} this
                        </span>
                      )}
                      {action.comment && <span className="flag-chip neutral">Comment added</span>}
                    </div>
                  </div>
                  <span className="dash-row-toggle">{open ? "▾" : "▸"}</span>
                </div>
                {open && (
                  <div className="dash-row-detail">
                    <div className="claim-note">"{c.claim.employee_description}"</div>

                    <div className="why-block">
                      <div className="why-title">Why the system reached this conclusion</div>
                      <dl className="why-grid">
                        <dt>Decision</dt>
                        <dd>{d.decision}</dd>
                        <dt>Resolution path</dt>
                        <dd>
                          {d.path === "deterministic"
                            ? "Deterministic code rule — no LLM call, $0, instant"
                            : "LLM-residual reasoning — retrieved policy evidence + enterprise facts"}
                        </dd>
                        <dt>Policy clauses cited</dt>
                        <dd>
                          {d.policy_evidence?.length ? (
                            d.policy_evidence.map((p) => (
                              <span key={p} className="mono-cell" style={{ marginRight: 6 }}>{p}</span>
                            ))
                          ) : (
                            <span style={{ color: "var(--text-dim)" }}>None cited for this decision</span>
                          )}
                        </dd>
                        <dt>Missing fields</dt>
                        <dd>
                          {d.missing_fields?.length ? d.missing_fields.join(", ") : <span style={{ color: "var(--text-dim)" }}>None</span>}
                        </dd>
                        <dt>Full explanation</dt>
                        <dd>{d.explanation || <span style={{ color: "var(--text-dim)" }}>No free-text explanation recorded — deterministic rules decide by clause, not narration.</span>}</dd>
                        <dt>Claim details</dt>
                        <dd>
                          {c.claim.bill.merchant_category || "—"} · submitted {c.claim.submission_date || "—"} ·
                          transaction {c.claim.transaction_date || "—"} · employee {c.claim.employee_id || "—"} ·
                          project {c.claim.project_id || "—"}
                        </dd>
                      </dl>
                    </div>

                    <div className="review-actions">
                      <div className="why-title">Your review</div>
                      <div className="review-buttons">
                        <button
                          className={`review-btn accept ${action.status === "ACCEPTED" ? "active" : ""}`}
                          onClick={() => setStatus(c.case_id, "ACCEPTED")}
                        >
                          ✓ Accept system's decision
                        </button>
                        <button
                          className={`review-btn reject ${action.status === "REJECTED" ? "active" : ""}`}
                          onClick={() => setStatus(c.case_id, "REJECTED")}
                        >
                          ✗ Reject / override
                        </button>
                      </div>
                      <textarea
                        className="review-comment"
                        placeholder="Add a comment (reason for override, note for the employee, anything worth recording)…"
                        value={action.comment || ""}
                        onChange={(e) => setComment(c.case_id, e.target.value)}
                      />
                      <div className="review-note">Saved to this browser only — not sent anywhere, not a write to any enterprise system.</div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          {filtered.length === 0 && <div style={{ padding: 20, color: "var(--text-dim)" }}>Nothing in this filter.</div>}
        </div>
      </div>
    </div>
  );
}
