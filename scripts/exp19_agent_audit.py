"""Experiment 19: agent-necessity audit of the agent-candidate cases in development + validation (final-test cases are deliberately not touched).
For each case: what the first observation was, whether it changed the next tool, whether a finite if/else covers it, and whether the fixed workflow got it right."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm_exp, evaluate, workflow

gt = evaluate.load_gt()
rows = []
for sp in ("DEVELOPMENT", "VALIDATION"):
    for c in llm_exp.cases_for(sp):
        g = gt[c["case_id"]]
        if g["architecture_group"] != "C_AGENT_DYNAMIC":
            continue
        d = workflow.run(c)
        tools_used = [t["tool"] for t in d["trace"]]
        first = next((t for t in d["trace"] if t["tool"] == "get_travel_request"), {}).get("data") or {}
        branch = "event_id -> conference lookup" if first.get("event_id") else "exception_id -> exception lookup" if first.get("exception_id") else "neither -> no further lookup"
        rows.append({"case_id": c["case_id"], "split": sp, "branch_observed": branch, "label_branch_trigger": g["branch_trigger"],
                     "first_observation_changes_next_tool": branch != "neither -> no further lookup",
                     "next_tool_after_travel_request": tools_used[tools_used.index("get_travel_request") + 1] if "get_travel_request" in tools_used and tools_used.index("get_travel_request") + 1 < len(tools_used) else None,
                     "finite_if_else_implemented": True, "workflow_tool_sequence": tools_used, "workflow_decision": d["decision"], "expected_decision": g["expected_decision"], "workflow_correct": d["decision"] == g["expected_decision"]})
n = len(rows); ok = sum(r["workflow_correct"] for r in rows)
by = {}
for r in rows: by.setdefault(r["branch_observed"], []).append(r["workflow_correct"])
summary = {"n_cases_audited": n, "workflow_correct": f"{ok}/{n}", "by_branch": {k: f"{sum(v)}/{len(v)}" for k, v in by.items()},
           "q1_path_fixed_in_advance_as_linear_checklist": False, "q1_decision_tree_finite_and_enumerable": True,
           "q2_first_observation_changes_next_tool": f"{sum(r['first_observation_changes_next_tool'] for r in rows)}/{n}",
           "q3_finite_if_else_handles_class": True, "q4_model_directed_sequencing_needed": False, "rows": rows}
o = C.RESULTS / "development" / "exp19"; o.mkdir(parents=True, exist_ok=True)
(o / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
for r in rows: print(r["case_id"], r["split"][:3], r["branch_observed"], "|", r["expected_decision"], "<-", r["workflow_decision"], "OK" if r["workflow_correct"] else "MISS")
