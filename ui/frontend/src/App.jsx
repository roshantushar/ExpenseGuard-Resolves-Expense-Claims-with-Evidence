import React, { useEffect, useState } from "react";
import Overview from "./components/Overview.jsx";
import Explorer from "./components/Explorer.jsx";
import StoryTimeline from "./components/StoryTimeline.jsx";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "explorer", label: "Case Explorer" },
  { id: "story", label: "Experiment Story" }
];

export default function App() {
  const [tab, setTab] = useState("overview");
  const [cases, setCases] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    fetch("/data/cases.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setCases)
      .catch((e) => setLoadError(String(e)));
  }, []);

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          Expense<span>Guard</span> — Architecture Demo
        </div>
        <div className="tabs">
          {TABS.map((t) => (
            <div key={t.id} className={`tab ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>
              {t.label}
            </div>
          ))}
        </div>
      </div>
      <div className="main">
        {loadError && (
          <div className="detail">
            <p className="err">
              Could not load /data/cases.json ({loadError}). Make sure ui/frontend/public/data/cases.json
              exists (see ui/README.md for how to regenerate it).
            </p>
          </div>
        )}
        {!loadError && !cases && <div className="detail">Loading {cases ? "" : "cases…"}</div>}
        {!loadError && cases && tab === "overview" && <Overview cases={cases} />}
        {!loadError && cases && tab === "explorer" && <Explorer cases={cases} />}
        {!loadError && cases && tab === "story" && <StoryTimeline />}
      </div>
    </div>
  );
}
