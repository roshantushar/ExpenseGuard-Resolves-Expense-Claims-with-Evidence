"""Experiment 2: deterministic rules baseline on the DEVELOPMENT split (no LLM, $0).
Usage: python scripts/exp02_rules.py [DEVELOPMENT|VALIDATION]"""
from __future__ import annotations
import json, sys, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, rules, evaluate
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EXP = "EXP02_RULES"
split = sys.argv[1] if len(sys.argv) > 1 else "DEVELOPMENT"
run_id = f"{EXP}-{split}-{uuid.uuid4().hex[:6]}"
cases = [json.loads(l) for l in (C.CASES / f"{split.lower()}.jsonl").read_text().splitlines() if l.strip()]
recs = []
for c in cases:
    t0 = time.perf_counter()
    d = rules.decide(c)
    ms = (time.perf_counter() - t0) * 1000
    r = {"case_id": c["case_id"], "predicted_decision": d["decision"], "policy_evidence": d["policy_evidence"], "missing_fields": d["missing_fields"],
         "reason": d["reason"], "manual_review_required": d["manual_review_required"], "latency_ms": round(ms, 3), "input_tokens": 0, "output_tokens": 0,
         "model_cost_usd": 0.0, "error": None}
    recs.append(r)
    llm.log_event(type="case_result", run_id=run_id, experiment=EXP, split=split, case_id=c["case_id"], model="rules", **{k: v for k, v in r.items() if k != "case_id"})
gt = evaluate.load_gt()
summary, rows = evaluate.evaluate(recs, gt)
for e in rows:
    llm.log_event(type="evaluation", run_id=run_id, experiment=EXP, split=split, model="rules", **e)
llm.log_event(type="experiment_summary", run_id=run_id, experiment=EXP, split=split, model="rules", config={"rules": "src/rules.py"}, **summary)
out = C.RESULTS / split.lower() / "exp02"; out.mkdir(parents=True, exist_ok=True)
(out / "predictions.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
(out / "evaluation.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
(out / "summary.json").write_text(json.dumps({"run_id": run_id, **summary}, indent=2))
print(json.dumps(summary, indent=1))
# plots: accuracy by family, confusion matrix
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
fams = sorted(summary["by_family"]); v = [int(summary["by_family"][f].split("/")[0]) / int(summary["by_family"][f].split("/")[1]) for f in fams]
ax[0].barh(fams, v); ax[0].set_xlim(0, 1); ax[0].set_title(f"Rules: accuracy by case family ({split.lower()})"); ax[0].tick_params(labelsize=7)
D = ["APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE"]
M = [[sum(1 for x in rows if x["expected_decision"] == e and x["predicted_decision"] == p) for p in D] for e in D]
ax[1].imshow(M, cmap="Blues"); ax[1].set_xticks(range(4)); ax[1].set_yticks(range(4)); ax[1].set_xticklabels([d[:7] for d in D]); ax[1].set_yticklabels([d[:7] for d in D])
for i in range(4):
    for j in range(4): ax[1].text(j, i, M[i][j], ha="center", va="center")
ax[1].set_xlabel("predicted"); ax[1].set_ylabel("expected"); ax[1].set_title("Confusion matrix")
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / f"exp02_rules_{split.lower()}.png", dpi=130)
