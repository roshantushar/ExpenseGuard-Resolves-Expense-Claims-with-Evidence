import React from "react";

// Real numbers from docs/exp33_failure_analysis.md / results/current/final_test/exp33_failure_analysis/
// failure_classification.csv — a manual read of all 20 errors on the frozen final test, not a keyword
// classifier (Exp 19 showed those can silently mislabel cases).
const CATEGORIES = [
  { name: "Policy reasoning / composition error", count: 7 },
  { name: "Missing-information confusion", count: 5 },
  { name: "Resolved-fact error", count: 4 },
  { name: "Missed escalation", count: 2 },
  { name: "Over-conservative bias", count: 2 },
  { name: "Retrieval / evidence missing", count: 0 },
  { name: "Routing / conclusiveness error", count: 0 }
];

const APPROVE_SUBCAUSES = [
  { name: "Demanded evidence not required by policy", count: 4 },
  { name: "Arithmetic / computation error", count: 3 },
  { name: "Ignored a positive resolved fact", count: 2 },
  { name: "Missing evidence that was actually available", count: 2 },
  { name: "Interpreted ambiguity conservatively", count: 2 }
];

function Bars({ data, total }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="err-bars">
      {data.map((d) => (
        <div className="err-bar-row" key={d.name}>
          <div className="err-bar-name">{d.name}</div>
          <div className="err-bar-track">
            <div className="err-bar-fill" style={{ width: `${(d.count / max) * 100}%` }} />
            <span className="err-bar-value">
              {d.count}/{total}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ErrorAnalysis() {
  return (
    <div>
      <p className="lede" style={{ fontSize: 13 }}>
        All 20 errors on the frozen final test occurred on the LLM-residual path — the deterministic path
        was 22/22 (100%). <b>Zero were caused by retrieval</b>: the relevant clause was present in the
        retrieved evidence in every case checked.
      </p>
      <h3 className="sub-h">Where all 20 errors came from</h3>
      <Bars data={CATEGORIES} total={20} />

      <h3 className="sub-h" style={{ marginTop: 24 }}>Why every one of the 13 APPROVE-truth cases failed</h3>
      <p className="lede" style={{ fontSize: 12.5 }}>
        Every genuinely approvable claim on the final test went through the residual path — the hardest
        class of decision, delegated entirely to the weakest component.
      </p>
      <Bars data={APPROVE_SUBCAUSES} total={13} />

      <ul className="bullets" style={{ marginTop: 16 }}>
        <li>A real example: <code>X2-070</code> — 25,000 JPY does not exceed a 45,000 JPY threshold; the model asserted the opposite and rejected for a nonexistent approval requirement</li>
        <li>A real example: <code>X2-002</code> — nightly rate was compliant (303.33 &lt; 350 ceiling), but the model compared the 3-night total against the per-night ceiling and rejected anyway</li>
        <li>Full per-case breakdown, including every explanation quoted verbatim: <code>docs/exp33_failure_analysis.md</code></li>
      </ul>

      <h3 className="sub-h" style={{ marginTop: 26 }}>The clearest silent failure this project actually found</h3>
      <div className="callout-card bad">
        <ul className="bullets">
          <li><code>X2-013</code> ("personal spend") was a false approval that survived Exp 45 through Exp 49 — unnoticed inside the aggregate accuracy number</li>
          <li>The agent confidently approved it because <code>workflow_v2.decide()</code> only saw the hardened, visible merchant category ("OTHER"), never the true category sitting in an enterprise tool it already had access to</li>
          <li>Nothing about the decision looked wrong in isolation: schema-valid, confident, evidence cited</li>
          <li><b>It was found only because ground truth existed to check against (Exp 50). In a real deployment, with no ground truth, this exact failure would have paid out silently.</b></li>
        </ul>
      </div>

      <h3 className="sub-h" style={{ marginTop: 22 }}>Is accuracy alone even a meaningful bar? The majority-class baseline</h3>
      <div className="callout-card">
        <ul className="bullets">
          <li>Always predicting the single most common outcome, computed from real ground truth — not assumed</li>
          <li>Development: REJECT-always → 27.1% accuracy, 0% FAR</li>
          <li>Final test: REJECT-always → 26.0% accuracy, 0% FAR</li>
          <li>Validation: APPROVE-always → 26.7% accuracy — similar raw accuracy, but <b>100% FAR</b></li>
          <li>⟶ Accuracy alone can't tell these two baselines apart. The official 60% final-test result and the FAR metric together are what actually mean something.</li>
        </ul>
      </div>
    </div>
  );
}
