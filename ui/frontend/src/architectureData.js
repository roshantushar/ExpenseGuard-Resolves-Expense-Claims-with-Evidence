// Business cost per 1,000 claims, base scenario ($35/hr reviewer, 6 min/review, $150/false approval) —
// computed directly from each rung's real predictions + ground truth, same methodology as
// scripts/v2/cost_model.py (verified: Fixed workflow/Frozen/Guarded rows match that script's output
// exactly). See docs/v2/cost_and_business_impact.md's "Full architecture-ladder cost" section.
export const COSTS = {
  "Rules only": { escalation: "15.7%", far: "6/41", ai: 0.0, human: 3692.86, falseApproval: 12857.14, total: 16550.0 },
  "Fixed workflow": { escalation: "14.3%", far: "7/42", ai: 0.0, human: 3357.14, falseApproval: 15000.0, total: 18357.14 },
  "Hybrid rules+RAG": { escalation: "20.0%", far: "2/38", ai: 0.83, human: 4700.0, falseApproval: 4285.71, total: 8986.55 },
  "Policy oracle (diag.)": { escalation: "2.9%", far: "0/50", ai: 0.29, human: 671.43, falseApproval: 0.0, total: 671.72 },
  "Tuned RAG": { escalation: "4.3%", far: "0/49", ai: 0.76, human: 1007.14, falseApproval: 0.0, total: 1007.9 },
  "Long context": { escalation: "0.0%", far: "0/52", ai: 3.87, human: 0.0, falseApproval: 0.0, total: 3.87 },
  "Naive RAG": { escalation: "1.4%", far: "0/52", ai: 0.25, human: 335.71, falseApproval: 0.0, total: 335.97 },
  "Frozen resolver — dev": { escalation: "18.6%", far: "0/39", ai: 0.43, human: 4364.29, falseApproval: 0.0, total: 4364.71 },
  "Frozen resolver — final test": { escalation: "22.0%", far: "0/27", ai: 0.46, human: 5170.0, falseApproval: 0.0, total: 5170.46 },
  "Guarded agent (candidate)": { escalation: "34.3%", far: "0/35", ai: 1.27, human: 8057.14, falseApproval: 0.0, total: 8058.42 }
};

// Per-architecture pipeline + hyperparameters, one entry per rung shown in LadderChart. Every value
// traced to a specific experiment doc under docs/v2/ — nothing here is a guess.
export const ARCHITECTURES = {
  "Rules only": {
    exp: "Exp 2c",
    steps: ["Input: claim (bill + free-text note)", "Regex/keyword extraction (rules_text.py)", "Deterministic rule engine (rules_v2.py)", "Decision"],
    hyperparams: ["No model, no retrieval — $0, instant", "Regex patterns hand-authored per claim family", "No hyperparameters to tune"]
  },
  "Fixed workflow": {
    exp: "Exp 18",
    steps: ["Input: claim", "Pre-declared typed-tool sequence (per claim type)", "workflow_v2.decide()", "Decision"],
    hyperparams: ["No model call — $0", "Step cap: 1 (sequence is fixed, no loop possible)", "Call de-duplication", "8 typed read-only tools"]
  },
  "Hybrid rules+RAG": {
    exp: "Exp 12",
    steps: ["Input: claim", "hybrid_facts.py — H1–H4 computed facts (arithmetic, temporal, evidence, duplicate/split)", "RAG retrieval", "Single LLM call", "Decision"],
    hyperparams: ["Chunking: 600 tokens / 100 overlap (frozen, Exp 6)", "Top-K: 8 (frozen, Exp 7)", "Retriever: dense, voyage-4-lite (frozen, Exp 8)", "Model: gpt-4o-mini, temperature 0"]
  },
  "Policy oracle (diag.)": {
    exp: "Exp 11",
    steps: ["Input: claim", "Evaluator supplies the exact correct clauses directly (retrieval bypassed)", "Single LLM call", "Decision"],
    hyperparams: ["Model: gpt-4o-mini, temperature 0", "Diagnostic only — needs ground truth to run, not deployable", "Purpose: separate retrieval failure from reasoning failure"]
  },
  "Tuned RAG": {
    exp: "Exp 9",
    steps: ["Input: claim", "Chunk the policy corpus", "Embed query", "Retrieve top-K", "M4 metadata filter (date/region/doc-type)", "Single LLM call", "Decision"],
    hyperparams: ["Chunking: 600 / 100 (Exp 6)", "Top-K: 8 (Exp 7)", "Retriever: dense, voyage-4-lite (Exp 8)", "Metadata filter: M4 — date + region + document-type compatibility (Exp 9)", "Model: gpt-4o-mini, temperature 0"]
  },
  "Long context": {
    exp: "Exp 4B",
    steps: ["Input: claim", "Entire 22-document policy corpus stuffed into context (no retrieval)", "Single LLM call", "Decision"],
    hyperparams: ["Model: gpt-4o-mini, temperature 0", "No chunking, no top-K — the whole corpus every call", "~40x the cost of tuned RAG per claim"]
  },
  "Naive RAG": {
    exp: "Exp 5",
    steps: ["Input: claim", "Chunk the policy corpus", "Embed the raw claim as the query", "Retrieve top-3", "Single LLM call", "Decision"],
    hyperparams: ["Chunking: 300 / 50 (pre-tuning default)", "Top-K: 3 (pre-tuning default)", "Retriever: dense, best of 4 embedding models compared — voyage-4-lite", "Query: raw claim text, no rewriting", "Model: gpt-4o-mini, temperature 0"]
  },
  "Frozen resolver — dev": {
    exp: "Exp 30",
    steps: ["Input: claim", "Deterministic rules (shared layer)", "Conclusive? → yes: code decides ($0)", "→ no: RAG (tuned config) + hybrid facts", "Single LLM call", "Decision"],
    hyperparams: ["Deterministic path: 0 hyperparameters, $0", "Residual: chunking 600/100, K=8, dense voyage-4-lite, M4 filter", "Model: gpt-4o-mini, temperature 0", "Routing gate: runtime-visible conclusiveness signal only (Exp 12B/30)"]
  },
  "Frozen resolver — final test": {
    exp: "Exp 32",
    steps: ["Same pipeline as dev, run once", "Hash-manifest-verified before the run", "Decision"],
    hyperparams: ["Identical config to Exp 30 — frozen before this run, never tuned afterward", "50-claim held-out set — Exp 32 itself ran exactly once, but a later, undisclosed re-run of the pipeline against this split was found by audit (docs/v2/second_touch_disclosure.md); Exp 32's own saved result was not affected"]
  },
  "Guarded agent (candidate)": {
    exp: "Exp 52",
    steps: ["Input: claim", "Deterministic rules (shared layer)", "Conclusive? → yes: code decides ($0)", "→ no: bounded ReAct agent", "Guarded compliance tools compute disposition in code", "Disposition gate (tool overrides model on disagreement)", "Decision"],
    hyperparams: ["Deterministic path: identical to the frozen design (shared code)", "Agent: max 8 turns, call de-duplication, read-only tools only", "Model: gpt-4o-mini, temperature 0", "7 domain-guarded tools (Exp 40–52), each scoped to specific claim types"]
  }
};
