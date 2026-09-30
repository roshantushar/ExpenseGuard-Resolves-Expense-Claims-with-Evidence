"""V2 Experiment 1: smallest end-to-end slice. 10 DEVELOPMENT self-contained cases; the harness hands the model the controlling + supporting clauses (oracle, feasibility only).
Usage: python3 scripts/v2/exp01_slice.py [model ...]"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src import config as C, llm_exp, policy
C.load_env()
EXP = "EXP01_SLICE"
SYSTEM = ("You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement. Use only the policy clauses provided; apply the version in force on the transaction date "
          "and the regional rules that override global ones where the clauses say so.\n" + llm_exp.SCHEMA)
gt = {json.loads(l)["case_id"]: json.loads(l) for l in (C.GROUND_TRUTH / "ground_truth.jsonl").read_text().splitlines() if l.strip()}  # evaluator-side pick + oracle clauses
dev = llm_exp.cases_for("DEVELOPMENT")
quota = {"APPROVE": 3, "REJECT": 3, "REQUEST_INFORMATION": 2, "ESCALATE": 2}; ids = []
for c in sorted(dev, key=lambda c: c["case_id"]):
    g = gt[c["case_id"]]
    if g["architecture_group"] == "A_SELF_CONTAINED" and quota[g["expected_decision"]] > 0: quota[g["expected_decision"]] -= 1; ids.append(c["case_id"])
cases = [c for c in dev if c["case_id"] in ids]
print("cases", ids)
oracle = lambda c: "CLAIM:\n" + json.dumps(llm_exp.visible(c), indent=1) + "\n\nRELEVANT POLICY CLAUSES:\n" + policy.render(gt[c["case_id"]]["required_policy_ids"] + gt[c["case_id"]]["supporting_policy_ids"])
res = {}
for m in (sys.argv[1:] or [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]):
    res[m] = llm_exp.run(EXP, m, "DEVELOPMENT", SYSTEM, oracle, cases=cases, config={"temperature": 0, "policy": "oracle clauses", "n": len(cases), "case_ids": ids})
    s = res[m][0]; print(m, {k: s[k] for k in ("correct", "n", "false_approvals", "non_approvable", "schema_valid", "median_latency_ms", "input_tokens", "output_tokens", "total_cost_usd")}, s["confusion"])
llm_exp.plot(EXP, "DEVELOPMENT", res, "V2 Exp 1: smallest slice (oracle clauses, 10 self-contained dev cases)")
