"""Experiment 7: top-K sensitivity (K = 1, 3, 5, 8). Dense retrieval, voyage-4-lite, recursive 300/50, no filters.
Selection rule (declared before running): K with the highest mean development correct count over the two LLMs; ties go to the smaller K."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm_exp, retrieval, embed, retrievers, rag_run
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
EXP = "EXP07_TOPK"
EM, CFG, KS, SPLITS = "voyageai/voyage-4-lite", "recursive300_50", [1, 3, 5, 8], ["DEVELOPMENT", "VALIDATION"]
cases = [dict(c, _split=s) for s in SPLITS for c in llm_exp.cases_for(s)]
R = retrievers.Retriever(EM, CFG)
qv = embed.embed(EM, [retrieval.claim_query(c) for c in cases], tag=EXP)
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
ret, down = {}, {}
for k in KS:
    agg, rows, ctx = rag_run.retrieve(R, cases, "dense", k, False, qv, EXP, f"k{k}", EM)
    ret[k] = agg
    down[k] = rag_run.downstream(f"{EXP}_K{k}", f"k{k}", ctx, SPLITS, models, {"retriever": EM, "chunking": CFG, "k": k})
    print(f"K={k}: R {agg['recall']:.3f} P {agg['precision']:.3f} MRR {agg['rr']:.3f} nDCG {agg['ndcg']:.3f} full {agg['full']:.3f} ctx_words {agg['ctx_words']:.0f}")
    for (sp, m), (s, _) in down[k].items():
        print(f"    {sp[:3]} {m.split('/')[-1]:16s} {s['correct']}/{s['n']}  FA {s['false_approvals']}/{s['non_approvable']}  in_tok {s['input_tokens']}  ${s['total_cost_usd']:.4f}  med {s['median_latency_ms']:.0f}ms")
dev = {k: sum(down[k][("DEVELOPMENT", m)][0]["correct"] for m in models) / 2 for k in KS}
best = max(KS, key=lambda k: (dev[k], -k))
print("dev mean correct by K:", dev, "-> chosen K =", best)
out = C.RESULTS / "development" / "exp07_topk"; out.mkdir(parents=True, exist_ok=True)
(out / "summary.json").write_text(json.dumps({"retrieval": ret, "dev_mean_correct": dev, "chosen_k": best,
    "downstream": {f"k{k}|{sp}|{m}": s for k in KS for (sp, m), (s, _) in down[k].items()}}, indent=2, default=str))
fig, ax = plt.subplots(1, 4, figsize=(20, 4))
for key, lab in [("recall", "Recall@K"), ("precision", "Precision@K"), ("rr", "MRR"), ("ndcg", "nDCG@K"), ("full", "all required in top-K")]:
    ax[0].plot(KS, [ret[k][key] for k in KS], marker="o", label=lab)
ax[0].legend(fontsize=7); ax[0].set_xlabel("K"); ax[0].set_title("Retrieval vs K (dev+val)"); ax[0].set_ylim(0, 1)
for sp, ls in (("DEVELOPMENT", "-"), ("VALIDATION", "--")):
    for m in models:
        n = down[KS[0]][(sp, m)][0]["n"]
        ax[1].plot(KS, [down[k][(sp, m)][0]["correct"] / n for k in KS], ls, marker="o", label=f"{m.split('/')[-1]} {sp[:3]}")
ax[1].legend(fontsize=7); ax[1].set_xlabel("K"); ax[1].set_title("Correct Disposition Rate vs K")
for m in models:
    ax[2].plot(KS, [down[k][("DEVELOPMENT", m)][0]["input_tokens"] / 1000 for k in KS], marker="o", label=m.split("/")[-1])
ax[2].set_title("Input tokens (k, dev 60 cases)"); ax[2].set_xlabel("K"); ax[2].legend(fontsize=7)
ax[3].plot(KS, [down[k][("DEVELOPMENT", models[0])][0]["total_cost_usd"] for k in KS], marker="o", c="C2", label="cost (USD)")
ax3 = ax[3].twinx(); ax3.plot(KS, [down[k][("DEVELOPMENT", models[0])][0]["median_latency_ms"] for k in KS], marker="s", c="C3"); ax3.set_ylabel("median latency ms", color="C3")
ax[3].set_title(f"{models[0].split('/')[-1]}: cost and latency vs K (dev)"); ax[3].set_xlabel("K")
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp07_topk.png", dpi=130)
