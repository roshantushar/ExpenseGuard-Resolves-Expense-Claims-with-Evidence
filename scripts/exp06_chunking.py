"""Experiment 6: chunking strategies, including recursive chunking. Retrieval-only comparison across embedding models
(top-3, dev+val, raw claim query, no filters), then a downstream LLM check for the best recursive config vs the Exp 5 naive config."""
from __future__ import annotations
import json, os, sys, statistics as st
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, llm_exp, retrieval, embed, evaluate
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
EXP = "EXP06_CHUNKING"
K = 3
CFGS = ["fixed150_25", "fixed300_50", "fixed600_100", "clause", "recursive100_15", "recursive200_30", "recursive300_50"]
MODELS = ["openai/text-embedding-3-small", "google/gemini-embedding-2", "voyageai/voyage-4-lite", "nvidia/nemotron-3-embed-1b:free", "baai/bge-base-en-v1.5"]
SPLITS = ["DEVELOPMENT", "VALIDATION"]
gt = evaluate.load_gt()
cases = [dict(c, _split=s) for s in SPLITS for c in llm_exp.cases_for(s)]
queries = [retrieval.claim_query(c) for c in cases]


def metrics_for(idx, qvecs):
    rows = []
    for c, q in zip(cases, qvecs):
        req = set(gt[c["case_id"]]["required_policy_ids"])
        ch = [idx["chunks"][i] for i, _ in retrieval.search(idx, q, K)]
        cov = set().union(*[set(x["clause_ids"]) for x in ch])
        rel = [bool(req & set(x["clause_ids"])) for x in ch]
        rows.append({"split": c["_split"], "recall": len(req & cov) / len(req), "precision": sum(rel) / K, "rr": next((1 / (r + 1) for r, x in enumerate(rel) if x), 0.0),
                     "full": req <= cov, "ctx_words": sum(len(x["text"].split()) for x in ch), "case_id": c["case_id"], "retrieved": [x["chunk_id"] for x in ch]})
    return rows


def agg(rows):
    return {k: round(st.mean(r[k] for r in rows), 4) for k in ("recall", "precision", "rr", "full", "ctx_words")}


res, fail = {}, {}
for m in MODELS:
    qv = embed.embed(m, queries, tag=EXP)
    for cfg in CFGS:
        try:
            idx = retrieval.build_or_load(m, cfg)
        except Exception as e:  # noqa
            fail[f"{m}|{cfg}"] = repr(e)[:120]; continue
        rows = metrics_for(idx, qv)
        res[(m, cfg)] = rows
        a = agg(rows)
        llm.log_event(type="experiment_summary", run_id=f"{EXP}-A-{m.split('/')[-1]}-{cfg}", experiment=EXP, split="DEV+VAL", model=m, chunk_cfg=cfg, k=K, part="A_retrieval",
                      n_chunks=len(idx["chunks"]), **a)
        for x in rows:
            llm.log_event(type="retrieval", run_id=f"{EXP}-A-{m.split('/')[-1]}-{cfg}", experiment=EXP, model=m, chunk_cfg=cfg, k=K, **x)

print("Mean over embedding models (top-3, dev+val):")
print(f"{'chunking':18s} n_models  Recall  Precision  MRR   all-required  ctx_words")
avg = {}
for cfg in CFGS:
    rs = [agg(res[(m, cfg)]) for m in MODELS if (m, cfg) in res]
    avg[cfg] = {k: round(st.mean(r[k] for r in rs), 3) for k in rs[0]}
    print(f"{cfg:18s} {len(rs):3d}      {avg[cfg]['recall']:.3f}  {avg[cfg]['precision']:.3f}     {avg[cfg]['rr']:.3f} {avg[cfg]['full']:.3f}        {avg[cfg]['ctx_words']:.0f}")
print("voyage-4-lite:")
for cfg in CFGS:
    a = agg(res[("voyageai/voyage-4-lite", cfg)]); print(f"  {cfg:18s} R {a['recall']:.3f} P {a['precision']:.3f} MRR {a['rr']:.3f} full {a['full']:.3f} ctx {a['ctx_words']:.0f}")

# ---- downstream: best recursive config (development MRR on voyage) vs naive fixed300_50 ----
BEST_M = "voyageai/voyage-4-lite"
rec = [c for c in CFGS if c.startswith("recursive")]
best = max(rec, key=lambda c: agg([r for r in res[(BEST_M, c)] if r["split"] == "DEVELOPMENT"])["rr"])
print("best recursive config by development MRR:", best)
idx = retrieval.build_or_load(BEST_M, best)
qv = embed.embed(BEST_M, queries, tag=EXP)
ctx = {c["case_id"]: "\n\n".join(f"[{idx['chunks'][i]['doc_id']} | region {idx['chunks'][i]['region']} | effective {idx['chunks'][i]['effective_from']} to {idx['chunks'][i]['effective_to']}]\n{idx['chunks'][i]['text']}"
                               for i, _ in retrieval.search(idx, q, K)) for c, q in zip(cases, qv)}
SYSTEM = ("You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement, using ONLY the retrieved policy excerpts provided. "
          "Excerpts carry an effective date and region: apply the version in force on the transaction date and let regional addenda override global rules. If the excerpts do not contain what is needed, say so via REQUEST_INFORMATION or ESCALATE rather than guessing.\n" + llm_exp.SCHEMA)
down = {}
for split in SPLITS:
    r = {}
    for m in [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]:
        r[m] = llm_exp.run(EXP, m, split, SYSTEM, lambda c: f"CLAIM:\n{json.dumps(llm_exp.visible(c), indent=1)}\n\nRETRIEVED POLICY EXCERPTS:\n{ctx[c['case_id']]}",
                           config={"temperature": 0, "retriever": BEST_M, "chunking": best, "k": K, "filters": "none"})
        s = r[m][0]; down[f"{split}|{m}"] = s
        print(split, m, {k: s[k] for k in ("correct", "n", "false_approvals", "non_approvable", "schema_valid", "total_tokens", "total_cost_usd", "median_latency_ms")})
    llm_exp.plot(EXP, split, r, f"Exp 6: recursive chunking {best}, top-{K} ({split.lower()})")

out = C.RESULTS / "development" / "exp06_chunking"; out.mkdir(parents=True, exist_ok=True)
(out / "chunking_comparison.json").write_text(json.dumps({"k": K, "mean_over_models": avg, "per_model": {f"{m}|{c}": agg(rows) for (m, c), rows in res.items()}, "failures": fail, "best_recursive": best, "downstream": down}, indent=2))
fig, ax = plt.subplots(1, 3, figsize=(18, 4.3))
x = range(len(CFGS)); w = 0.27
for j, (k, lab) in enumerate([("recall", "Recall@3"), ("precision", "Precision@3"), ("rr", "MRR")]):
    ax[0].bar([i + (j - 1) * w for i in x], [avg[c][k] for c in CFGS], w, label=lab)
ax[0].set_xticks(list(x)); ax[0].set_xticklabels(CFGS, rotation=30, fontsize=7); ax[0].legend(); ax[0].set_ylim(0, 1); ax[0].set_title("Retrieval by chunking (mean of embedding models)")
ax[1].bar(CFGS, [avg[c]["ctx_words"] for c in CFGS], color="C2"); ax[1].set_title("Words in retrieved top-3 context (prompt size)"); ax[1].tick_params(axis="x", rotation=30, labelsize=7)
for m in MODELS:
    ax[2].plot(CFGS, [agg(res[(m, c)])["rr"] if (m, c) in res else float("nan") for c in CFGS], marker="o", label=m.split("/")[-1].replace(":free", "*"))
ax[2].set_title("MRR by chunking, per embedding model"); ax[2].legend(fontsize=7); ax[2].tick_params(axis="x", rotation=30, labelsize=7)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp06_chunking_comparison.png", dpi=130)
