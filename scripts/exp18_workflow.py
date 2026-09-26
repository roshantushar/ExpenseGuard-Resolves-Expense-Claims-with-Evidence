"""Experiment 18: fixed workflow on all development + validation cases (workflow and agent-candidate families are the gate).
Compares with the rules baseline (Exp 2). Also reports tool-path adherence against the acceptable paths (evaluator side)."""
from __future__ import annotations
import json, sys, time, uuid, statistics as st
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, llm_exp, evaluate, workflow, rules
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EXP = "EXP18_WORKFLOW"
SPLITS = ["DEVELOPMENT", "VALIDATION"]
gt = evaluate.load_gt()
res = {}
for split in SPLITS:
    run_id = f"{EXP}-{split}-{uuid.uuid4().hex[:6]}"
    recs = []
    for c in llm_exp.cases_for(split):
        t0 = time.perf_counter(); d = workflow.run(c); ms = (time.perf_counter() - t0) * 1000
        r = {"case_id": c["case_id"], "predicted_decision": d["decision"], "policy_evidence": d["policy_evidence"], "missing_fields": d["missing_fields"], "reason": d["reason"],
             "manual_review_required": d["manual_review_required"], "tool_calls": d["tool_calls"], "tools_used": [t["tool"] for t in d["trace"]], "latency_ms": round(ms, 3),
             "input_tokens": 0, "output_tokens": 0, "model_cost_usd": 0.0, "error": None}
        recs.append(r)
        llm.log_event(type="case_result", run_id=run_id, experiment=EXP, split=split, model="workflow", **{k: v for k, v in r.items() if k != "case_id"}, case_id=c["case_id"])
        for i, t in enumerate(d["trace"]):
            llm.log_event(type="tool_call", run_id=run_id, experiment=EXP, split=split, case_id=c["case_id"], step=i, **t)
    summary, rows = evaluate.evaluate(recs, gt)
    # tool-path adherence: the tools the workflow used should cover the ground truth's minimum required tools
    ok = tot = 0
    for r in recs:
        need = set(gt[r["case_id"]]["minimum_required_tools"])
        if need:
            tot += 1; ok += need <= set(r["tools_used"])
    summary["required_tools_covered"] = f"{ok}/{tot}"
    summary["avg_tool_calls"] = round(st.mean(r["tool_calls"] for r in recs), 3)
    summary["avg_tool_calls_on_evidence_cases"] = round(st.mean(r["tool_calls"] for r in recs if gt[r["case_id"]]["architecture_group"] != "A_SELF_CONTAINED") or 0, 3)
    for e in rows:
        llm.log_event(type="evaluation", run_id=run_id, experiment=EXP, split=split, model="workflow", **e)
    llm.log_event(type="experiment_summary", run_id=run_id, experiment=EXP, split=split, model="workflow", config={"code": "src/workflow.py"}, **summary)
    out = C.RESULTS / split.lower() / "exp18"; out.mkdir(parents=True, exist_ok=True)
    (out / "predictions.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    (out / "evaluation.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (out / "summary.json").write_text(json.dumps({"run_id": run_id, **summary}, indent=2))
    res[split] = (summary, rows, recs)
    print(split, {k: summary[k] for k in ("n", "correct", "wilson95", "false_approvals", "non_approvable", "human_review_rate", "over_escalation", "missed_escalation", "required_tools_covered", "avg_tool_calls", "median_latency_ms")})
    print("  by family:", summary["by_family"])
# rules baseline for comparison on the same split
base = {sp: json.loads((C.RESULTS / sp.lower() / "exp02" / "summary.json").read_text()) for sp in SPLITS}
for sp in SPLITS: print("rules baseline", sp, base[sp]["correct"], "/", base[sp]["n"], base[sp]["by_family"])
# errors
for sp in SPLITS:
    for e in res[sp][1]:
        if not e["correct"]:
            print("MISS", sp[:3], e["case_id"], e["case_family"], e["expected_decision"], "->", e["predicted_decision"])
fams = ["SELF_CONTAINED_POLICY", "TEMPORAL_POLICY_VERSION", "REGIONAL_PRECEDENCE", "EVIDENCE_CONFLICT", "MISSING_INFORMATION", "DUPLICATE_CHECK", "SPLIT_TRANSACTION", "FIXED_WORKFLOW", "DYNAMIC_AGENT_INVESTIGATION"]
def famacc(summ_by): 
    return [int(summ_by.get(f, "0/0").split("/")[0]) for f in fams], [int(summ_by.get(f, "0/0").split("/")[1]) for f in fams]
fig, ax = plt.subplots(1, 3, figsize=(20, 4.6))
cw = {f: [0, 0] for f in fams}; cb = {f: [0, 0] for f in fams}
for sp in SPLITS:
    for f, v in res[sp][0]["by_family"].items(): a, b = map(int, v.split("/")); cw[f][0] += a; cw[f][1] += b
    for f, v in base[sp]["by_family"].items(): a, b = map(int, v.split("/")); cb[f][0] += a; cb[f][1] += b
x = range(len(fams))
ax[0].bar([i - 0.2 for i in x], [cb[f][0] / max(1, cb[f][1]) for f in fams], 0.4, label="rules (Exp 2)"); ax[0].bar([i + 0.2 for i in x], [cw[f][0] / max(1, cw[f][1]) for f in fams], 0.4, label="fixed workflow (Exp 18)")
ax[0].set_xticks(list(x)); ax[0].set_xticklabels([f.replace("_", "\n") for f in fams], fontsize=5); ax[0].legend(fontsize=7); ax[0].set_ylim(0, 1.05); ax[0].set_title("Accuracy by family, dev + val")
tc = defaultdict(list)
for sp in SPLITS:
    for r in res[sp][2]: tc[gt[r["case_id"]]["case_family"]].append(r["tool_calls"])
ax[1].bar(range(len(fams)), [st.mean(tc[f]) if tc[f] else 0 for f in fams], color="C2"); ax[1].set_xticks(list(x)); ax[1].set_xticklabels([f.replace("_", "\n") for f in fams], fontsize=5); ax[1].set_title("Average tool calls per case")
lat = [r["latency_ms"] for sp in SPLITS for r in res[sp][2]]
ax[2].hist(lat, bins=30, color="C3"); ax[2].set_title(f"Workflow latency per case (ms), median {st.median(lat):.2f}"); ax[2].set_xlabel("ms")
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp18_workflow.png", dpi=130)
