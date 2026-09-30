// The full experiment story, one "act" per phase, as scannable bullet points (not prose paragraphs).
// Rendered as a scroll-revealed timeline on the Overview tab. Every number traces back to a saved
// result file and a doc under docs/.
export const ACTS = [
  {
    title: "Act 1 — Meet the data, and watch every easy answer fail",
    tags: ["Exp 0", "Exp 2–4", "Exp 5–10", "Exp 11"],
    points: [
      "150 expense claims — a bill and a free-text note, nothing structured",
      "Exp 0: dataset audited for leakage; hardened 3 separate times so no fact could be lifted from a form field",
      "Exp 2: plain deterministic rules collapsed once facts moved into free text",
      "Exp 3: generic LLM with no policy — confident, but unsupported",
      "Exp 4: whole policy corpus in context — feasible, but 40x the cost of RAG, no accuracy gain",
      "Exp 5–10: tuning ladder for RAG (chunk size, top-K, retriever, metadata filters, query rewrite)",
      "Exp 9: retrieval plateaued at 56% of the right clauses in the top 8 results",
      "Exp 11: handed the model the exact correct clauses directly — accuracy barely moved",
      "⟶ 57% of errors were reasoning failures, not retrieval failures. The bottleneck was never finding the rule — it was applying it."
    ]
  },
  {
    title: "Act 2 — Build the pieces, and learn what a model actually needs",
    tags: ["Exp 12", "Exp 13–17", "Exp 18–20"],
    points: [
      "Exp 12: pulled arithmetic, date logic, and duplicate detection out of the LLM's hands into code",
      "Exp 13–17: qualified each remaining piece one at a time (missing-info, duplicates/splits, enterprise facts, typed tools)",
      "Exp 18: a fixed, pre-declared workflow with no model in the loop — most accurate system so far (64% dev)",
      "Exp 19: audited whether any claim genuinely needs a model deciding what to look up next",
      "Exp 20: a real bounded agent only tied the fixed workflow, at 3x the false-approval rate",
      "⟶ The agent gate closed here — no evidence yet that dynamic tool choice earns its cost."
    ]
  },
  {
    title: "Act 3 — Choose safety over accuracy, and freeze it",
    tags: ["Exp 28–29", "Exp 30", "Exp 31–33"],
    points: [
      "Exp 28: attacked the system on purpose (prompt injection, fake authority, conflicting records) — found 1 real bug (fixed) + 1 disclosed, accepted risk",
      "Exp 29: measured how well the system knew when to abstain",
      "Exp 30: LLM-for-everything vs. fixed workflow vs. selective (rules decide when they can) — workflow was more accurate (64%) but approved bad claims 13.5% of the time",
      "⟶ Selective design frozen: gave up a few points of accuracy for 0 false approvals",
      "Exp 31: confirmed cost was negligible ($0.0004/claim)",
      "Exp 32: the frozen system, run exactly once against 50 unseen claims — 30/50 correct, 0/37 false approvals",
      "Exp 33: found the LLM half of the system kept contradicting facts it had already been given"
    ]
  },
  {
    title: "Act 4 — Try to build a better agent, and watch it fail in five different ways",
    tags: ["Exp 34", "Exp 35–36", "Exp 37–39"],
    points: [
      "Exp 34: a real searchable agent — worse than the fixed workflow (4/13), used the wrong hotel ceiling",
      "Exp 35: stricter prompt tripled false approvals; a 16x pricier model matched accuracy but worsened safety; a better tool interface only helped if the model chose to use it",
      "Exp 36: parallel tool calls — no overall improvement",
      "Exp 37: handed the agent the exact correct policy text directly — false approvals nearly quadrupled",
      "Exp 38: free trace audit found the agent's own search queries were genuinely weak, never re-searched",
      "Exp 39: fixed that specific problem — accuracy still fell",
      "⟶ Nothing about more information, more autonomy, or more horsepower was working."
    ]
  },
  {
    title: "Act 5 — Stop asking the model to decide",
    tags: ["Exp 40–41", "Exp 42–44", "Exp 46"],
    points: [
      "Root cause traced to 3 bugs: bad tool arguments, REJECT/REQUEST_INFO confusion, overriding a tool that already had the right answer",
      "Exp 40: tools that compute the decision in code, not just fetch facts — tied the fixed workflow",
      "Exp 41: disposition gate — if a tool already had the correct answer and the model disagreed, trust the tool — beat the workflow outright",
      "Exp 42–43: found and fixed the same design flaw twice (a tool firing on a claim type it was never meant to answer)",
      "Exp 44: confirmed on validation data never touched before — 17/19 correct, 0 false approvals",
      "Exp 46: a stronger model with guards in place — still no improvement, but guards held FAR at 0% regardless of model"
    ]
  },
  {
    title: "Act 6 — Close the gap for the whole dataset",
    tags: ["Exp 45", "Exp 47–50", "Exp 51–52"],
    points: [
      "Exp 45: applied the design to every claim — accuracy jumped, but false approvals reappeared wherever a category had no dedicated tool",
      "Exp 47: reused existing tested code as a catch-all — made it worse (same fragile note-reading problem)",
      "Exp 48: redesigned the fallback to trust only checks that never depend on reading free text",
      "Exp 49: caught the model passing the word \"unknown\" as if it were a real answer",
      "Exp 50: found the model miscounting hotel nights from a date range; closed the last false approval",
      "Exp 51: confirmed on development — 44/70, 0 false approvals (one better than the frozen system)",
      "Exp 52: validation run immediately caught one more real bug, fixed it — 44/70 dev + 21/30 validation, 0% FAR on both"
    ]
  },
  {
    title: "Act 7 — The twist, and a second twist: cost accounting had a bug",
    tags: ["Cost model", "Responsible AI", "OWASP Top 10"],
    points: [
      "The guarded agent looked like the clear winner: higher accuracy, same 0% false approvals",
      "Risk-adjusted cost model: it escalates to a human 1.5–1.8x more often than the frozen design",
      "First cost model: human-review cost dominates every scenario — total operating cost looked higher at every scale — but that model omitted false-rejection and unnecessary-info-request costs",
      "Corrected: once those costs are priced in, the guarded candidate is cheaper at every scale — the frozen design's much higher false-rejection rate (36.8% dev / 50.0% final test) was never priced before",
      "⟶ The frozen resolver still ships officially — the guarded candidate has never been run against the held-out final test, so independent generalization remains unproven, not because it's the cheaper design",
      "Separately: completed a full OWASP Top 10 for LLM Applications (2025) pass — all 10 categories",
      "Zero fabricated policy citations found across every decision ever made; budget/step caps confirmed to actually trip",
      "Prompt injection left exactly where Exp 28 found it — a disclosed, unsolved risk, not a silently-claimed win",
      "⟶ Final lesson: pick the architecture on safe automation, total cost, AND how well-tested the evidence is — not on accuracy or a single cost model run alone."
    ]
  }
];
