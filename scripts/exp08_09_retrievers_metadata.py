"""Experiment 8 (BM25 vs dense vs hybrid) and Experiment 9 (metadata-aware retrieval), recursive 300/50 chunks, K from Exp 7.
Exp 8: modes x embedding models (voyage-4-lite paid, nemotron free), retrieval-only; downstream LLM run for the best mode.
Exp 9: best mode with vs without metadata filter (effective date + region, derived from the claim only); downstream for both.
Usage: python scripts/exp08_09_retrievers_metadata.py"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm_exp, retrieval, embed, retrievers, rag_run
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
CFG, SPLITS = "recursive300_50", ["DEVELOPMENT", "VALIDATION"]
K = json.loads((C.RESULTS / "development" / "exp07_topk" / "summary.json").read_text())["chosen_k"]
EMS = ["voyageai/voyage-4-lite", "nvidia/nemotron-3-embed-1b:free"]
cases = [dict(c, _split=s) for s in SPLITS for c in llm_exp.cases_for(s)]
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
print("K from Exp 7:", K)

# ---------------- Exp 8 ----------------
E8 = "EXP08_RETRIEVER"
r8, ctx8 = {}, {}
for em in EMS:
    R = retrievers.Retriever(em, CFG)
    qv = embed.embed(em, [retrieval.claim_query(c) for c in cases], tag=E8)
    for mode in ("bm25", "dense", "hybrid"):
        agg, rows, ctx = rag_run.retrieve(R, cases, mode, K, False, qv, E8, f"{em.split('/')[-1]}_{mode}", em)
        r8[(em, mode)] = agg; ctx8[(em, mode)] = (ctx, rows)
        print(f"{em.split('/')[-1]:24s} {mode:7s} R {agg['recall']:.3f} P {agg['precision']:.3f} MRR {agg['rr']:.3f} nDCG {agg['ndcg']:.3f} full {agg['full']:.3f} wrong_year {agg['wrong_year_chunks']:.2f} wrong_region {agg['wrong_region_chunks']:.2f}")


def dev_key(k):
    a = r8[k]; return (a["ndcg"] + a["rr"] + a["full"]) / 3


# select on development rows only
import statistics as st
def dev_score(k):
    rows = [r for r in ctx8[k][1] if r["split"] == "DEVELOPMENT"]
    return st.mean((r["ndcg"] + r["rr"] + float(r["full"])) / 3 for r in rows)
best8 = max(r8, key=dev_score)
print("Exp 8 best (development mean of nDCG, MRR, full-coverage):", best8)
d8 = rag_run.downstream(f"{E8}_BEST", f"best_{best8[1]}", ctx8[best8][0], SPLITS, models, {"retriever": best8[0], "mode": best8[1], "chunking": CFG, "k": K})
for (sp, m), (s, _) in d8.items():
    print(f"  Exp8 best {sp[:3]} {m.split('/')[-1]:16s} {s['correct']}/{s['n']} FA {s['false_approvals']}/{s['non_approvable']} ${s['total_cost_usd']:.4f}")

# ---------------- Exp 9 ----------------
E9 = "EXP09_METADATA"
em, mode = best8
R = retrievers.Retriever(em, CFG)
qv = embed.embed(em, [retrieval.claim_query(c) for c in cases], tag=E9)
r9, ctx9 = {}, {}
for filt in (False, True):
    name = "filtered" if filt else "unfiltered"
    agg, rows, ctx = rag_run.retrieve(R, cases, mode, K, filt, qv, E9, name, em)
    r9[name] = agg; ctx9[name] = ctx
    print(f"Exp9 {name:10s} R {agg['recall']:.3f} P {agg['precision']:.3f} MRR {agg['rr']:.3f} nDCG {agg['ndcg']:.3f} full {agg['full']:.3f} wrong_year/case {agg['wrong_year_chunks']:.2f} wrong_region/case {agg['wrong_region_chunks']:.2f}")
d9 = {n: rag_run.downstream(f"{E9}_{n.upper()}", n, ctx9[n], SPLITS, models, {"retriever": em, "mode": mode, "chunking": CFG, "k": K, "metadata_filter": n == "filtered"}) for n in ("unfiltered", "filtered")}
for n in d9:
    for (sp, m), (s, _) in d9[n].items():
        print(f"  Exp9 {n:10s} {sp[:3]} {m.split('/')[-1]:16s} {s['correct']}/{s['n']} FA {s['false_approvals']}/{s['non_approvable']} in_tok {s['input_tokens']} ${s['total_cost_usd']:.4f}")

out = C.RESULTS / "development" / "exp08_09"; out.mkdir(parents=True, exist_ok=True)
(out / "summary.json").write_text(json.dumps({"k": K, "chunking": CFG, "exp8": {f"{a}|{b}": v for (a, b), v in r8.items()}, "exp8_best": list(best8),
    "exp8_best_downstream": {f"{sp}|{m}": s for (sp, m), (s, _) in d8.items()}, "exp9": r9,
    "exp9_downstream": {f"{n}|{sp}|{m}": s for n in d9 for (sp, m), (s, _) in d9[n].items()}}, indent=2, default=str))
fig, ax = plt.subplots(1, 3, figsize=(19, 4.2))
labs = [f"{e.split('/')[-1].replace(':free','*')}\n{m}" for e in EMS for m in ("bm25", "dense", "hybrid")]
for j, (key, lab) in enumerate([("recall", "Recall@K"), ("precision", "Precision@K"), ("rr", "MRR"), ("ndcg", "nDCG@K")]):
    ax[0].bar([i + (j - 1.5) * 0.2 for i in range(6)], [r8[(e, m)][key] for e in EMS for m in ("bm25", "dense", "hybrid")], 0.2, label=lab)
ax[0].set_xticks(range(6)); ax[0].set_xticklabels(labs, fontsize=7); ax[0].legend(fontsize=7); ax[0].set_ylim(0, 1); ax[0].set_title(f"Exp 8: retrieval family (K={K}, dev+val)")
for j, n in enumerate(("unfiltered", "filtered")):
    ax[1].bar([i + (j - 0.5) * 0.35 for i in range(4)], [r9[n][k] for k in ("recall", "rr", "ndcg", "full")], 0.35, label=n)
ax[1].set_xticks(range(4)); ax[1].set_xticklabels(["Recall", "MRR", "nDCG", "all required"]); ax[1].legend(); ax[1].set_ylim(0, 1); ax[1].set_title("Exp 9: metadata filter, retrieval quality")
for j, n in enumerate(("unfiltered", "filtered")):
    ax[2].bar([i + (j - 0.5) * 0.35 for i in range(2)], [r9[n]["wrong_year_chunks"], r9[n]["wrong_region_chunks"]], 0.35, label=n)
ax[2].set_xticks(range(2)); ax[2].set_xticklabels(["wrong-year chunks / case", "wrong-region chunks / case"]); ax[2].legend(); ax[2].set_title("Exp 9: policy-version and region errors")
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp08_09_retrieval_and_metadata.png", dpi=130)
