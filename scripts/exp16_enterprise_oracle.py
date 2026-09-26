"""Experiment 16: enterprise-evidence oracle. On the evidence-dependent cases (fixed-workflow, dynamic, split, duplicate families; dev + val),
the evaluator supplies the exact enterprise records the case needs (from the ground truth's required tools, run through the real tools), and the LLM
(RAG + code facts, as in Exp 12) decides. Compared with the same LLM without records (Exp 12) and with the fixed workflow (Exp 18)."""
from __future__ import annotations
import json, os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, llm_exp, retrieval, embed, retrievers, rag_run, evaluate, rules, tools
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
EXP = "EXP16_ENTERPRISE_ORACLE"
EM, CFG, K, SPLITS = "voyageai/voyage-4-lite", "recursive300_50", 3, ["DEVELOPMENT", "VALIDATION"]
FAMS = {"FIXED_WORKFLOW", "DYNAMIC_AGENT_INVESTIGATION", "SPLIT_TRANSACTION", "DUPLICATE_CHECK"}
gt = evaluate.load_gt()
all_cases = [dict(c, _split=s) for s in SPLITS for c in llm_exp.cases_for(s)]
cases = [c for c in all_cases if gt[c["case_id"]]["case_family"] in FAMS]
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]


def oracle_records(c):
    need = gt[c["case_id"]]["minimum_required_tools"]          # evaluator-side knowledge of which records matter
    obs, tr = [], None
    args = {"get_employee_profile": {"employee_id": c["employee_id"]}, "get_travel_request": {"employee_id": c["employee_id"], "date": c["transaction_date"]},
            "get_manager_approval": {"expense_id": c["case_id"]}, "get_project_status": {"project_id": c["project_id"]},
            "search_previous_expenses": {"employee_id": c["employee_id"], "merchant": c["bill"]["merchant"]}, "get_merchant_metadata": {"merchant_name": c["bill"]["merchant"]}}
    order = [t for t in ("get_employee_profile", "get_travel_request", "get_manager_approval", "get_project_status", "search_previous_expenses", "get_merchant_metadata") if t in need]
    for t in order:
        r = tools.call_tool(t, args[t]); obs.append((t, args[t], r))
        if t == "get_travel_request" and r["found"]: tr = r["data"]
    exc = (re.search(r"EXC-[A-Z]+-\d{3}", c["employee_description"]) or [None])[0] or (tr and tr["exception_id"])
    if "get_exception_record" in need and exc:
        obs.append(("get_exception_record", {"exception_id": exc}, tools.call_tool("get_exception_record", {"exception_id": exc})))
    if "get_conference_registration" in need and tr and tr["event_id"]:
        obs.append(("get_conference_registration", {"event_id": tr["event_id"]}, tools.call_tool("get_conference_registration", {"event_id": tr["event_id"]})))
    return "\n".join(f"- {t}({json.dumps(a)}) -> " + (json.dumps(r["data"]) if r["found"] else "NOT FOUND") for t, a, r in obs) or "- (no enterprise records required)"


R = retrievers.Retriever(EM, CFG)
qv = embed.embed(EM, [retrieval.claim_query(c) for c in cases], tag=EXP)
_, _, rag_ctx = rag_run.retrieve(R, cases, "dense", K, True, qv, EXP, "retrieval_for_reference", EM)
facts = {c["case_id"]: rules.facts(c) for c in cases}
ent = {c["case_id"]: oracle_records(c) for c in cases}
SYSTEM = rag_run.RAG_SYSTEM + ("\nYou are also given VERIFIED CALCULATIONS computed by code, and ENTERPRISE RECORDS returned by read-only lookups. Both are authoritative facts about this claim; do not redo the arithmetic. "
                               "Semantic judgments and which policy clauses apply remain yours.")
out = {}
for split in SPLITS:
    sub = [c for c in cases if c["_split"] == split]
    for m in models:
        s, recs, rows = llm_exp.run(EXP, m, split, SYSTEM, lambda c: f"CLAIM:\n{json.dumps(llm_exp.visible(c), indent=1)}\n\nPOLICY EXCERPTS:\n{rag_ctx[c['case_id']]}\n\nVERIFIED CALCULATIONS:\n{facts[c['case_id']]}\n\nENTERPRISE RECORDS:\n{ent[c['case_id']]}",
                                    cases=sub, config={"temperature": 0, "oracle": "enterprise records", "retriever": EM, "chunking": CFG, "k": K})
        out[(split, m)] = s
        print(split[:3], m.split("/")[-1], f"{s['correct']}/{s['n']} FA {s['false_approvals']}/{s['non_approvable']} in_tok {s['input_tokens']} ${s['total_cost_usd']:.4f} {s['decision_counts']}")


def score_from(path_fn, tag=None):
    ok = n = fa = na = 0
    for split in SPLITS:
        ids = {c["case_id"] for c in cases if c["_split"] == split}
        for l in Path(path_fn(split)).read_text().splitlines():
            r = json.loads(l)
            if r["case_id"] in ids:
                g = gt[r["case_id"]]; n += 1; ok += r["predicted_decision"] == g["expected_decision"]
                if g["expected_decision"] != "APPROVE": na += 1; fa += r["predicted_decision"] == "APPROVE"
    return ok, n, fa, na


cmp = {}
for m in models:
    tag = m.replace("/", "_").replace(":", "_")
    cmp[f"{m.split('/')[-1]}: no enterprise records (Exp 12)"] = score_from(lambda sp: C.RESULTS / sp.lower() / "exp12_hybrid" / f"predictions_{tag}.jsonl")
    cmp[f"{m.split('/')[-1]}: oracle records (Exp 16)"] = score_from(lambda sp: C.RESULTS / sp.lower() / EXP.lower() / f"predictions_{tag}.jsonl")
cmp["rules only (Exp 2)"] = score_from(lambda sp: C.RESULTS / sp.lower() / "exp02" / "predictions.jsonl")
cmp["fixed workflow (Exp 18)"] = score_from(lambda sp: C.RESULTS / sp.lower() / "exp18" / "predictions.jsonl")
for k, (ok, n, fa, na) in cmp.items(): print(f"{k:50s} {ok}/{n}  false approvals {fa}/{na}")
o = C.RESULTS / "development" / "exp16"; o.mkdir(parents=True, exist_ok=True)
(o / "summary.json").write_text(json.dumps({"n_cases": len(cases), "comparison": {k: {"correct": v[0], "n": v[1], "false_approvals": v[2], "non_approvable": v[3]} for k, v in cmp.items()},
                                            "llm_runs": {f"{sp}|{m}": s for (sp, m), s in out.items()}}, indent=2, default=str))
fig, ax = plt.subplots(1, 2, figsize=(15, 4.6))
ks = list(cmp)
ax[0].barh([k for k in ks], [cmp[k][0] / cmp[k][1] for k in ks], color=["C0", "C1", "C0", "C1", "C7", "C2"]); ax[0].set_xlim(0, 1); ax[0].set_title(f"Evidence-dependent cases (n={len(cases)}): correct rate"); ax[0].tick_params(labelsize=7)
ax[1].barh([k for k in ks], [cmp[k][2] / max(1, cmp[k][3]) for k in ks], color="C3"); ax[1].axvline(0.10, ls="--", c="k", lw=0.8); ax[1].set_xlim(0, 1); ax[1].set_title("False approval rate"); ax[1].tick_params(labelsize=7)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp16_enterprise_oracle.png", dpi=130)
