"""Experiments 30 (selective router) and 31 (cost-to-serve). Dev + val (80 cases). Measured quantities come from saved runs; business quantities are assumptions
and are labelled as such."""
from __future__ import annotations
import json, sys, time, uuid, statistics as st
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, llm_exp, evaluate, router
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

gt = evaluate.load_gt()
SPL = ["DEVELOPMENT", "VALIDATION"]
# ---------------- Exp 30 ----------------
recs, routes = [], {}
run_id = f"EXP30_ROUTER-{uuid.uuid4().hex[:6]}"
for sp in SPL:
    for c in llm_exp.cases_for(sp):
        t0 = time.perf_counter(); d = router.route(c); ms = (time.perf_counter() - t0) * 1000
        r = {"case_id": c["case_id"], "predicted_decision": d["decision"], "missing_fields": d["missing_fields"], "manual_review_required": d["manual_review_required"],
             "latency_ms": ms, "input_tokens": 0, "output_tokens": 0, "model_cost_usd": 0.0, "tool_calls": d["tool_calls"], "route": d["route"], "error": None}
        recs.append(r); routes[c["case_id"]] = d["route"]
        llm.log_event(type="case_result", run_id=run_id, experiment="EXP30_ROUTER", split=sp, model="router", case_id=c["case_id"], **{k: v for k, v in r.items() if k != "case_id"})
summ, rows = evaluate.evaluate(recs, gt)
for e in rows: llm.log_event(type="evaluation", run_id=run_id, experiment="EXP30_ROUTER", split="DEV+VAL", model="router", **e)
share = {k: sum(v == k for v in routes.values()) for k in ("rules", "workflow")}
summ.update(route_counts=share, agent_invocations=0, avg_tool_calls=round(st.mean(r["tool_calls"] for r in recs), 3), share_using_tools=round(sum(r["tool_calls"] > 0 for r in recs) / len(recs), 3))
llm.log_event(type="experiment_summary", run_id=run_id, experiment="EXP30_ROUTER", split="DEV+VAL", model="router", config={"code": "src/router.py"}, **summ)
print("ROUTER", {k: summ[k] for k in ("n", "correct", "wilson95", "false_approvals", "non_approvable", "human_review_rate", "route_counts", "share_using_tools", "avg_tool_calls", "median_latency_ms")})


def agg(pred_fn):
    ids = [c for sp in SPL for c in (r["case_id"] for r in map(json.loads, Path(pred_fn(sp)).read_text().splitlines()))]
    return ids


def load(fn):
    return [json.loads(l) for sp in ("development", "validation") for l in Path(fn(sp)).read_text().splitlines() if l.strip()]


def stats_from(recs_, cost_key=None):
    s, _ = evaluate.evaluate([{**r, "latency_ms": r.get("latency_ms", 0), "input_tokens": r.get("input_tokens", 0), "output_tokens": r.get("output_tokens", 0), "model_cost_usd": r.get("model_cost_usd", 0.0)} for r in recs_], gt)
    return s


strategies = {
    "LLM everywhere: gpt-4o-mini RAG + facts (Exp 12)": load(lambda sp: C.RESULTS / sp / "exp12_hybrid" / "predictions_openai_gpt-4o-mini.jsonl"),
    "LLM everywhere: llama3.2:3b RAG + facts (Exp 12)": load(lambda sp: C.RESULTS / sp / "exp12_hybrid" / "predictions_llama3.2_3b.jsonl"),
    "rules everywhere (Exp 2)": load(lambda sp: C.RESULTS / sp / "exp02" / "predictions.jsonl"),
    "workflow everywhere (Exp 18)": load(lambda sp: C.RESULTS / sp / "exp18" / "predictions.jsonl"),
    "selective router (Exp 30)": recs,
}
res = {k: stats_from(v) for k, v in strategies.items()}
res["selective router (Exp 30)"]["route_counts"] = share
for k, s in res.items():
    print(f"{k:52s} {s['correct']}/{s['n']} FA {s['false_approvals']}/{s['non_approvable']} HRR {s['human_review_rate']:.3f} cost ${s['total_cost_usd']:.4f} med {s['median_latency_ms']:.2f}ms p95 {s['p95_latency_ms']:.2f}ms")

# ---------------- Exp 31 ----------------
# measured per-claim AI cost. LLM path = generation call (measured) + one query embedding (measured from the log).
emb = [json.loads(l) for l in open(C.SHARED / "run_log.jsonl") if '"kind": "embedding"' in l]
q = [r for r in emb if r["model"] == "voyageai/voyage-4-lite" and r["experiment"] == "EXP07_TOPK" and not r["cached"]]
emb_tokens_per_query = sum(r["input_tokens"] for r in q) / 80 if q else 90
emb_cost_per_query = (sum(r["cost_usd"] for r in q) / 80) if q else 2e-6
llm_row = res["LLM everywhere: gpt-4o-mini RAG + facts (Exp 12)"]
ai_cost = {"manual review only": 0.0, "LLM everywhere: gpt-4o-mini RAG + facts (Exp 12)": llm_row["total_cost_usd"] / llm_row["n"] + emb_cost_per_query,
           "rules everywhere (Exp 2)": 0.0, "workflow everywhere (Exp 18)": 0.0, "selective router (Exp 30)": 0.0}
hrr = {"manual review only": 1.0, **{k: res[k]["human_review_rate"] for k in ai_cost if k in res}}
acc = {"manual review only": 1.0, **{k: res[k]["correct_disposition_rate"] for k in ai_cost if k in res}}
ri_rate = {k: sum(r["predicted_decision"] == "REQUEST_INFORMATION" for r in v) / len(v) for k, v in strategies.items()}
ri_rate["manual review only"] = 0.0
# ASSUMPTIONS (not measured): edit here
ASSUME = {"manual_review_minutes": 10, "analyst_cost_per_hour_usd": 40, "fixed_monthly_usd": {"hosting": 100, "storage": 20, "monitoring": 50, "evaluation_runs": 30},
          "note": "All values in this dict are illustrative assumptions, not measurements."}
review_cost = ASSUME["manual_review_minutes"] / 60 * ASSUME["analyst_cost_per_hour_usd"]
fixed = sum(ASSUME["fixed_monthly_usd"].values())
scales = [1000, 10000, 100000]
table = {}
for k in ai_cost:
    table[k] = {"measured_ai_cost_per_claim_usd": round(ai_cost[k], 7), "measured_human_review_rate": round(hrr[k], 4), "measured_correct_rate": round(acc[k], 3),
                "measured_request_information_rate": round(ri_rate[k], 3),
                "wrong_dispositions_per_10000_claims (measured rate, not monetised)": round((1 - acc[k]) * 10000),
                "assumed_review_cost_per_claim_usd": round(hrr[k] * review_cost, 4),
                "monthly_cost_usd": {str(n): round(n * (ai_cost[k] + hrr[k] * review_cost) + (0 if k == "manual review only" else fixed), 2) for n in scales},
                "ai_cost_per_correct_disposition_usd": round(ai_cost[k] / acc[k], 7) if acc[k] else None}
    print(f"{k:52s} AI ${ai_cost[k]:.6f}/claim  HRR {hrr[k]:.3f}  RI {ri_rate[k]:.3f}  correct {acc[k]:.3f}  wrong/10k {round((1 - acc[k]) * 10000)}  monthly {table[k]['monthly_cost_usd']}")
sens = {}
for mins in (5, 10, 20):
    for rate in (30, 40, 60):
        rc = mins / 60 * rate
        sens[f"{mins}min@${rate}/h"] = {k: round(10000 * (ai_cost[k] + hrr[k] * rc) + (0 if k == "manual review only" else fixed), 0) for k in ai_cost}
out = C.RESULTS / "development" / "exp30_31"; out.mkdir(parents=True, exist_ok=True)
(out / "summary.json").write_text(json.dumps({"router": summ, "strategies": {k: {kk: v[kk] for kk in ("n", "correct", "wilson95", "false_approvals", "non_approvable", "human_review_rate", "total_cost_usd", "median_latency_ms", "p95_latency_ms", "total_tokens")} for k, v in res.items()},
                                             "cost_to_serve": {"assumptions": ASSUME, "embedding_tokens_per_query": emb_tokens_per_query, "table": table, "sensitivity_10k_claims": sens}}, indent=2, default=str))
fig, ax = plt.subplots(1, 3, figsize=(20, 4.8))
ks = list(res); lab = [k.replace(": ", ":\n").replace(" (", "\n(") for k in ks]
ax[0].bar(range(len(ks)), [res[k]["correct_disposition_rate"] for k in ks], color="C0"); ax[0].set_title("Exp 30: Correct Disposition Rate by strategy"); ax[0].set_ylim(0, 1)
ax[0].set_xticks(range(len(ks))); ax[0].set_xticklabels(lab, fontsize=5)
for k, x in zip(ks, range(len(ks))): ax[0].text(x, res[k]["correct_disposition_rate"] + 0.01, f"FA {res[k]['false_approvals']}/{res[k]['non_approvable']}", ha="center", fontsize=6)
tk = list(table)
for n, col in zip(scales, ("C0", "C1", "C2")):
    ax[1].plot(range(len(tk)), [table[k]["monthly_cost_usd"][str(n)] for k in tk], marker="o", label=f"{n:,} claims/month", c=col)
ax[1].set_yscale("log"); ax[1].set_xticks(range(len(tk))); ax[1].set_xticklabels([k.replace(": ", ":\n").replace(" (", "\n(") for k in tk], fontsize=5); ax[1].legend(fontsize=7)
ax[1].set_title("Exp 31: modelled monthly cost (USD, log scale; review cost and fixed costs are ASSUMPTIONS)")
ax[2].bar(range(len(tk)), [table[k]["measured_ai_cost_per_claim_usd"] * 1e6 for k in tk], color="C2"); ax[2].set_title("Measured AI cost per claim (USD x 1e-6)")
ax[2].set_xticks(range(len(tk))); ax[2].set_xticklabels([k.replace(": ", ":\n").replace(" (", "\n(") for k in tk], fontsize=5)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp30_31_router_and_cost.png", dpi=130)
