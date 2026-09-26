"""Experiment 32: the frozen final test. Refuses to run on FINAL_TEST unless (1) --confirm-final-run is given, (2) every frozen file still matches the
hash recorded in experiments/exp32_freeze_manifest.yaml, and (3) no earlier final run exists (results/final/RAN). Any other split is a dry run written to results/<split>/exp32_dryrun.
Usage: python scripts/exp32_final_test.py [SPLIT] [--confirm-final-run]"""
from __future__ import annotations
import hashlib, json, os, re, sys, time, uuid, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config as C, llm, llm_exp, evaluate, router, rules, flags, retrieval, embed, retrievers, rag_run, metrics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
args = [a for a in sys.argv[1:] if not a.startswith("--")]
split = (args[0] if args else "VALIDATION").upper()
final = split == "FINAL_TEST"
MANIFEST = ROOT / "experiments" / "exp32_freeze_manifest.yaml"
EXP = "EXP32_FINAL_TEST" if final else "EXP32_DRYRUN"
out = C.RESULTS / ("final" if final else split.lower()) / ("exp32" if final else "exp32_dryrun")

# ---- freeze integrity ----
frozen = dict(re.findall(r"^\s+((?:src|scripts)/\S+):\s+([0-9a-f]{64})\s*$", MANIFEST.read_text(), re.M))
bad = [f for f, h in frozen.items() if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != h]
if bad:
    sys.exit(f"FREEZE VIOLATION: files changed since the manifest was written: {bad}")
if final:
    if "--confirm-final-run" not in sys.argv:
        sys.exit("Refusing to run on FINAL_TEST without --confirm-final-run")
    if (C.RESULTS / "final" / "RAN").exists():
        sys.exit("A final run already exists (results/final/RAN). The final test is run once.")
    (C.RESULTS / "final").mkdir(parents=True, exist_ok=True)
    (C.RESULTS / "final" / "RAN").write_text(time.strftime("%Y-%m-%dT%H:%M:%S") + "\n")
out.mkdir(parents=True, exist_ok=True)

gt = evaluate.load_gt()
cases = llm_exp.cases_for(split)
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
proj = len(cases) * 2 * 2200 / 1e6 * 0.15
print(f"{EXP}: {len(cases)} cases from {split}; projected paid cost about ${proj:.3f}; spent so far ${llm.spent():.4f} of ${os.environ['MAX_BUDGET_USD']}; freeze verified ({len(frozen)} files)")

R = retrievers.Retriever("voyageai/voyage-4-lite", "recursive300_50")
qv = embed.embed("voyageai/voyage-4-lite", [retrieval.claim_query(c) for c in cases], tag=EXP)
sysrec = {}


def record(name, fn):
    recs = []
    for c in cases:
        t0 = time.perf_counter(); d = fn(c); ms = (time.perf_counter() - t0) * 1000
        recs.append({"case_id": c["case_id"], "predicted_decision": d["decision"], "policy_evidence": d["policy_evidence"], "missing_fields": d["missing_fields"], "reason": d["reason"],
                     "manual_review_required": d["manual_review_required"], "tool_calls": d.get("tool_calls", 0), "route": d.get("route"), "latency_ms": ms, "input_tokens": 0, "output_tokens": 0,
                     "model_cost_usd": 0.0, "error": None})
    return recs


sysrec["router (frozen system)"] = record("router", router.route)
sysrec["rules only"] = record("rules", lambda c: rules.decide(c))
# LLM baselines with frozen prompts: filtered dense retrieval + code facts
_, _, ctx = rag_run.retrieve(R, [dict(c, _split=split) for c in cases], "dense", 3, True, qv, EXP, "retrieval_for_baseline", "voyageai/voyage-4-lite")
facts = {c["case_id"]: rules.facts(c) for c in cases}
for m in models:
    s, recs, _ = llm_exp.run(EXP, m, split, rag_run.HYBRID_SYSTEM, lambda c: f"CLAIM:\n{json.dumps(llm_exp.visible(c), indent=1)}\n\nPOLICY EXCERPTS:\n{ctx[c['case_id']]}\n\nVERIFIED CALCULATIONS:\n{facts[c['case_id']]}",
                             cases=cases, config={"temperature": 0, "frozen": True})
    sysrec[f"{m.split('/')[-1]} RAG + code facts"] = recs

# ---- evaluation (ground truth joined after all predictions exist) ----
flagged = {c["case_id"] for c in cases if flags.currency_ambiguous(c)}
challenge = {c["case_id"] for c in cases if gt[c["case_id"]]["independent_challenge"]}
report = {"split": split, "n": len(cases), "currency_flagged_case_ids": sorted(flagged), "challenge_case_ids": sorted(challenge), "systems": {}}
for name, recs in sysrec.items():
    def sub(ids): return [r for r in recs if r["case_id"] in ids]
    full, rows = evaluate.evaluate(recs, gt)
    entry = {"all": full}
    if challenge: entry["challenge_set"] = evaluate.evaluate(sub(challenge), gt)[0]
    if flagged:
        entry["currency_flagged"] = evaluate.evaluate(sub(flagged), gt)[0]
        entry["excluding_currency_flagged"] = evaluate.evaluate([r for r in recs if r["case_id"] not in flagged], gt)[0]
    report["systems"][name] = entry
    rid = f"{EXP}-{name.replace(' ', '_')}-{uuid.uuid4().hex[:6]}"
    for r in recs: llm.log_event(type="case_result", run_id=rid, experiment=EXP, split=split, model=name, **{k: v for k, v in r.items() if k != "case_id"}, case_id=r["case_id"])
    for e in rows: llm.log_event(type="evaluation", run_id=rid, experiment=EXP, split=split, model=name, **e)
    llm.log_event(type="experiment_summary", run_id=rid, experiment=EXP, split=split, model=name, config={"manifest": str(MANIFEST.name)}, **full)
    (out / f"predictions_{name.replace(' ', '_').replace('(', '').replace(')', '')}.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    (out / f"evaluation_{name.replace(' ', '_').replace('(', '').replace(')', '')}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"{name:32s} correct {full['correct']}/{full['n']} ({full['correct_disposition_rate']:.3f}, Wilson {full['wilson95']}) FA {full['false_approvals']}/{full['non_approvable']} HRR {full['human_review_rate']:.3f} "
          f"median {full['median_latency_ms']:.2f}ms p95 {full['p95_latency_ms']:.2f}ms cost/case ${full['total_cost_usd'] / full['n']:.6f}")
    if challenge: print(f"    challenge set: {entry['challenge_set']['correct']}/{entry['challenge_set']['n']}")
    if flagged: print(f"    currency-flagged: {entry['currency_flagged']['correct']}/{entry['currency_flagged']['n']}; excluding them: {entry['excluding_currency_flagged']['correct']}/{entry['excluding_currency_flagged']['n']}")
(out / "report.json").write_text(json.dumps(report, indent=2, default=str))
names = list(sysrec)
fig, ax = plt.subplots(1, 4, figsize=(20, 4.4))
v = [report["systems"][n]["all"] for n in names]
ax[0].bar(range(len(names)), [x["correct_disposition_rate"] for x in v], yerr=[[x["correct_disposition_rate"] - x["wilson95"][0] for x in v], [x["wilson95"][1] - x["correct_disposition_rate"] for x in v]], capsize=4)
ax[0].set_ylim(0, 1); ax[0].set_title(f"{EXP}: Correct Disposition Rate (95% Wilson)")
ax[1].bar(range(len(names)), [x["false_approval_rate"] or 0 for x in v], color="C3"); ax[1].axhline(0.10, ls="--", c="k", lw=0.8); ax[1].set_title("False Approval Rate")
ax[2].bar(range(len(names)), [x["median_latency_ms"] for x in v], color="C1"); ax[2].set_yscale("log"); ax[2].set_title("Median latency (ms, log)")
ax[3].bar(range(len(names)), [x["total_cost_usd"] / x["n"] * 1e6 for x in v], color="C2"); ax[3].set_title("Cost per case (USD x 1e-6)")
for a in ax: a.set_xticks(range(len(names))); a.set_xticklabels([n.replace(" (", "\n(").replace(" RAG", "\nRAG") for n in names], fontsize=6)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / f"exp32_{'final' if final else 'dryrun_' + split.lower()}.png", dpi=130)
