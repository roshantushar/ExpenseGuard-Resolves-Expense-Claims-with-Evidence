"""Experiment 5: naive RAG baseline + embedding-model comparison.
Retrieval: dense embeddings, fixed chunks (300 tokens / 50 overlap), top-3, raw claim-derived query, no metadata filter, no reranker, no rewriting.
Part A compares embedding models on retrieval metrics only (dev+val). Part B runs the downstream LLMs with the best model's top-3 chunks.
All chunk configs are embedded and stored under results/embeddings/ for reuse in Exp 6-9."""
from __future__ import annotations
import json, os, sys, statistics as st
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, llm_exp, retrieval, embed, evaluate, metrics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
EXP = "EXP05_NAIVE_RAG"
K = 3
NAIVE = "fixed300_50"
STORE_CFGS = ["fixed300_50", "fixed150_25", "fixed600_100", "clause"]
EMB_MODELS = ["openai/text-embedding-3-small", "baai/bge-base-en-v1.5", "google/gemini-embedding-2", "voyageai/voyage-4-lite",
              "nvidia/nemotron-3-embed-1b:free", "liquid/lfm-2.5-embedding-350m:free"]
SPLITS = ["DEVELOPMENT", "VALIDATION"]
gt = evaluate.load_gt()
cases = [dict(c, _split=s) for s in SPLITS for c in llm_exp.cases_for(s)]
queries = [retrieval.claim_query(c) for c in cases]


def retrieval_metrics(idx, qvecs, k):
    rows = []
    for c, q in zip(cases, qvecs):
        req = set(gt[c["case_id"]]["required_policy_ids"])
        hits = retrieval.search(idx, q, k)
        ch = [idx["chunks"][i] for i, _ in hits]
        cov = set().union(*[set(x["clause_ids"]) for x in ch]) if ch else set()
        rel = [bool(req & set(x["clause_ids"])) for x in ch]
        rows.append({"case_id": c["case_id"], "split": c["_split"], "required": sorted(req), "retrieved": [x["chunk_id"] for x in ch], "scores": [round(s, 4) for _, s in hits],
                     "recall": len(req & cov) / len(req) if req else None, "precision": sum(rel) / len(rel) if rel else 0.0,
                     "rr": next((1 / (r + 1) for r, x in enumerate(rel) if x), 0.0), "full_coverage": bool(req <= cov) if req else None})
    return rows


def agg(rows):
    r = [x for x in rows if x["recall"] is not None]
    return {"n": len(r), "recall_at_k": round(st.mean(x["recall"] for x in r), 4), "precision_at_k": round(st.mean(x["precision"] for x in r), 4),
            "mrr": round(st.mean(x["rr"] for x in r), 4), "full_coverage_rate": round(st.mean(x["full_coverage"] for x in r), 4)}


# ---- Part A: embedding-model comparison (retrieval only) ----
results, failures = {}, {}
for m in EMB_MODELS:
    try:
        qv = embed.embed(m, queries, tag=EXP)
    except Exception as e:  # noqa
        failures[f"{m}|queries"] = repr(e)[:200]; print("FAILED queries", m, failures[f"{m}|queries"]); continue
    for cfg in STORE_CFGS:
        try:
            idx = retrieval.build_or_load(m, cfg)
        except Exception as e:  # noqa
            failures[f"{m}|{cfg}"] = repr(e)[:200]; print("FAILED index", m, cfg, failures[f"{m}|{cfg}"]); continue
        rows = retrieval_metrics(idx, qv, K)
        results[(m, cfg)] = rows
        s = agg(rows)
        rid = f"{EXP}-A-{m.split('/')[-1]}-{cfg}"
        llm.log_event(type="experiment_summary", run_id=rid, experiment=EXP, split="DEV+VAL", model=m, chunk_cfg=cfg, k=K, part="A_retrieval", **s)
        for x in rows:
            llm.log_event(type="retrieval", run_id=rid, experiment=EXP, model=m, chunk_cfg=cfg, k=K, **x)

table = {f"{m}|{cfg}": agg(rows) for (m, cfg), rows in results.items()}
print(f"{'embedding model':40s} {'chunking':13s}  R@3   P@3   MRR   full-cov")
for (m, cfg), rows in results.items():
    a = agg(rows); print(f"{m:40s} {cfg:13s} {a['recall_at_k']:.3f} {a['precision_at_k']:.3f} {a['mrr']:.3f} {a['full_coverage_rate']:.3f}")

# embedding cost/tokens per model from the log
cost, toks = defaultdict(float), defaultdict(int)
for l in open(C.SHARED / "run_log.jsonl"):
    r = json.loads(l)
    if r.get("kind") == "embedding" and not r.get("cached"):
        cost[r["model"]] += r["cost_usd"]; toks[r["model"]] += r["input_tokens"]

best_model = max((m for m in EMB_MODELS if (m, NAIVE) in results), key=lambda m: (agg([x for x in results[(m, NAIVE)] if x["split"] == "DEVELOPMENT"])["recall_at_k"], -cost[m]))
print("best embedding model by development Recall@3 (naive chunking):", best_model)

# ---- Part B: downstream generation with naive RAG ----
idx = retrieval.build_or_load(best_model, NAIVE)
qv = embed.embed(best_model, queries, tag=EXP)
ctx = {c["case_id"]: "\n\n".join(f"[{idx['chunks'][i]['doc_id']} | region {idx['chunks'][i]['region']} | effective {idx['chunks'][i]['effective_from']} to {idx['chunks'][i]['effective_to']}]\n{idx['chunks'][i]['text']}"
                               for i, _ in retrieval.search(idx, q, K)) for c, q in zip(cases, qv)}
SYSTEM = ("You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement, using ONLY the retrieved policy excerpts provided. "
          "Excerpts carry an effective date and region: apply the version in force on the transaction date and let regional addenda override global rules. If the excerpts do not contain what is needed, say so via REQUEST_INFORMATION or ESCALATE rather than guessing.\n" + llm_exp.SCHEMA)
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
ds = {}
for split in SPLITS:
    res = {}
    for m in models:
        res[m] = llm_exp.run(EXP, m, split, SYSTEM, lambda c: f"CLAIM:\n{json.dumps(llm_exp.visible(c), indent=1)}\n\nRETRIEVED POLICY EXCERPTS:\n{ctx[c['case_id']]}",
                             config={"temperature": 0, "retriever": best_model, "chunking": NAIVE, "k": K, "filters": "none"})
        s = res[m][0]
        print(split, m, {k: s[k] for k in ("correct", "n", "false_approvals", "non_approvable", "human_review_rate", "schema_valid", "decision_counts", "median_latency_ms", "total_tokens", "total_cost_usd")})
    llm_exp.plot(EXP, split, res, f"Exp 5: naive RAG, {best_model}, {NAIVE}, top-{K} ({split.lower()})")
    ds[split] = {m: res[m][0] for m in models}

# ---- outputs ----
out = C.RESULTS / "development" / "exp05_naive_rag"; out.mkdir(parents=True, exist_ok=True)
(out / "embedding_comparison.json").write_text(json.dumps({"k": K, "table": table, "failures": failures, "embedding_cost_usd": cost, "embedding_input_tokens": toks, "best_model": best_model,
                                                          "downstream": ds}, indent=2, default=dict))
(out / "retrieval_rows.jsonl").write_text("\n".join(json.dumps({"embed_model": m, "chunk_cfg": cfg, **x}) for (m, cfg), rows in results.items() for x in rows) + "\n")
ms = [m for m in EMB_MODELS if (m, NAIVE) in results]
fig, ax = plt.subplots(1, 3, figsize=(18, 4.2))
w = 0.25
for j, (key, lab) in enumerate([("recall_at_k", "Recall@3"), ("precision_at_k", "Precision@3"), ("mrr", "MRR")]):
    ax[0].bar([i + (j - 1) * w for i in range(len(ms))], [agg(results[(m, NAIVE)])[key] for m in ms], w, label=lab)
ax[0].set_xticks(range(len(ms))); ax[0].set_xticklabels([m.split("/")[-1].replace(":free", "*") for m in ms], rotation=25, fontsize=7); ax[0].legend(); ax[0].set_ylim(0, 1)
ax[0].set_title(f"Retrieval by embedding model ({NAIVE}, k=3, dev+val; * = free)")
cfgs = STORE_CFGS
for j, cfg in enumerate(cfgs):
    ax[1].bar([i + (j - 1.5) * 0.2 for i in range(len(ms))], [agg(results[(m, cfg)])["recall_at_k"] if (m, cfg) in results else 0 for m in ms], 0.2, label=cfg)
ax[1].set_xticks(range(len(ms))); ax[1].set_xticklabels([m.split("/")[-1].replace(":free", "*") for m in ms], rotation=25, fontsize=7); ax[1].legend(fontsize=7); ax[1].set_ylim(0, 1)
ax[1].set_title("Recall@3 by chunking config")
ax[2].bar([m.split("/")[-1].replace(":free", "*") for m in ms], [cost[m] * 1e4 for m in ms], color="C2"); ax[2].set_title("Embedding cost (USD x 1e-4), all stored indexes + queries")
ax[2].tick_params(axis="x", rotation=25, labelsize=7)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp05_embedding_comparison.png", dpi=130)
