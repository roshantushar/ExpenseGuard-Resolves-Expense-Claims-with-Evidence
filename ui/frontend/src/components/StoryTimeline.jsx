import React from "react";

const ACTS = [
  {
    title: "Act 1 — Meet the data, and watch every easy answer fail",
    tags: ["Exp 0", "Exp 2–4", "Exp 5–10", "Exp 11"],
    body: `It starts with 150 expense claims — a bill and a free-text note, nothing structured. Exp 0
audited the dataset for leakage and consistency, and confirmed it had been hardened three separate
times so no fact could be lifted from a form field. Exp 2 proved why that mattered: plain deterministic
rules, which scored perfectly on an earlier, easier version of the data, collapsed once facts moved into
free text. Exp 3 tried a generic LLM with no policy — confident, but wrong in ways that couldn't be
trusted. Exp 4 tried stuffing the whole policy corpus into context — feasible, but expensive and no
better than retrieval. Exp 5–10 was a patient tuning ladder for RAG: chunk size, top-K, retriever choice,
metadata filters, query rewriting (which improved retrieval but made the final answers worse). By Exp 9,
retrieval was about as good as it would get — 56% of the right clauses in the top 8 results. Then Exp 11
handed the model the exact correct clauses directly, no searching required. Accuracy barely moved: 57%
of the errors were reasoning failures, not retrieval failures. The bottleneck was never finding the
right rule — it was applying it.`
  },
  {
    title: "Act 2 — Build the pieces, and learn what a model actually needs",
    tags: ["Exp 12", "Exp 13–17", "Exp 18–20"],
    body: `Exp 12 pulled arithmetic, date logic, and duplicate detection out of the LLM's hands and
computed them in code. Exp 13–17 qualified each remaining piece — missing-information detection,
duplicate/split handling, enterprise-fact resolution, typed read-only tools — one at a time. Exp 18
assembled a fixed, pre-declared workflow with no model in the loop at all, and it was the most accurate
single system so far (64% on development). Exp 19 asked whether any claim genuinely needs a model
deciding what to look up next, and Exp 20 tested a real bounded agent to find out — it only tied the
fixed workflow, while being three times less safe. The agent gate closed there.`
  },
  {
    title: "Act 3 — Choose safety over accuracy, and freeze it",
    tags: ["Exp 28–29", "Exp 30", "Exp 31–33"],
    body: `Exp 28 attacked the system on purpose (prompt injection, fake authority, conflicting records)
and found one real bug, fixed, plus one disclosed, accepted risk. Exp 29 measured how well the system
knew when to abstain. Exp 30 ran the decisive comparison: LLM-for-everything, the fixed workflow, or a
selective design where deterministic rules decide whenever they can. The workflow was more accurate
(64%) but approved bad claims 13.5% of the time; the selective design gave up a few points for zero false
approvals — and that's what got frozen. Exp 31 confirmed the cost was negligible. Exp 32 was the moment
of truth: the frozen system, run exactly once against 50 unseen claims — 30/50 correct, 0% false
approvals. Exp 33 found the LLM half of the system kept contradicting facts it had already been given.`
  },
  {
    title: "Act 4 — Try to build a better agent, and watch it fail in five different ways",
    tags: ["Exp 34", "Exp 35–36", "Exp 37–39"],
    body: `Exp 34 tested a real agent, RAG as something searchable and re-searchable — worse than the
fixed workflow, and it repeated the "ignores a given fact" failure on a Chennai hotel claim, using the
wrong ceiling. Exp 35 isolated prompt, model, and tool-interface layers at once: a stricter prompt
tripled false approvals; a 16x more expensive model got the same accuracy with worse safety; a better
tool interface helped only when the model chose to use it. Exp 36 batched tool calls in parallel — no
overall improvement. Exp 37 handed the agent the exact correct policy text directly — false approvals
nearly quadrupled, ruling out evidence quality for good. Exp 38, a free trace audit, found the agent's
own search queries were genuinely weak and it never searched twice. Exp 39 fixed that specific problem
and accuracy still fell. Nothing about more information, more autonomy, or more horsepower was working.`
  },
  {
    title: "Act 5 — Stop asking the model to decide",
    tags: ["Exp 40–41", "Exp 42–44", "Exp 46"],
    body: `Three specific bugs, traced to their root, pointed the same direction: bad tool arguments,
REJECT/REQUEST_INFORMATION confusion, and overriding a tool that already had the right answer. Exp 40's
fix: build tools that compute the decision in code, not just fetch facts. That tied the fixed workflow.
Exp 41 added a gate — if a tool already had the correct disposition and the model disagreed anyway,
trust the tool. That beat the fixed workflow outright. Exp 42–43 found and fixed the same design flaw
twice (a tool firing on a claim type it was never meant to answer). Exp 44 confirmed it on validation
data never touched before — 17 of 19 correct, zero false approvals. Exp 46 tried a stronger model again,
now with guards in place — still no improvement, though the guards kept false approvals at zero
regardless of model.`
  },
  {
    title: "Act 6 — Close the gap for the whole dataset",
    tags: ["Exp 45", "Exp 47–50", "Exp 51–52"],
    body: `Exp 45 applied the working design to every claim, not just the family it was built for —
accuracy jumped, but false approvals reappeared everywhere a category had no dedicated tool. Exp 47
tried a shortcut (reusing existing, tested code as a catch-all) and made things worse — that code shared
the same fragile note-reading problem it was meant to route around. Exp 48 redesigned the fallback to
trust only checks that never depend on reading free text. Exp 49 caught the model passing the word
"unknown" as if it were a real answer. Exp 50 found the model miscounting hotel nights from a date range,
and closed the last false approval by cross-checking a merchant's true category against enterprise data.
Exp 51 confirmed it on development: 44/70, zero false approvals — one better than the frozen system's own
number. Exp 52 ran it against validation for the first time, immediately caught one more real bug, fixed
it, and reached the final confirmed result: 44/70 development and 21/30 validation, 0% false approvals
on both.`
  }
];

export default function StoryTimeline() {
  return (
    <div className="story">
      <h1 style={{ marginBottom: 4 }}>The story, from data to decision</h1>
      <p style={{ color: "var(--text-dim)", marginBottom: 28, fontSize: 14 }}>
        Every number here traces back to a saved result file and a written doc under <code>docs/v2/</code>.
      </p>
      {ACTS.map((act) => (
        <div className="act" key={act.title}>
          <h2>{act.title}</h2>
          <div style={{ marginBottom: 8 }}>
            {act.tags.map((t) => (
              <span className="tag" key={t}>
                {t}
              </span>
            ))}
          </div>
          <p>{act.body}</p>
        </div>
      ))}
    </div>
  );
}
