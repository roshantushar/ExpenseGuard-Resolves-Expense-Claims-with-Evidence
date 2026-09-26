"""Experiment 11 (policy oracle) and Experiment 12 (RAG + deterministic compliance logic). Development + validation, both LLMs.
Retriever (from Exp 7-9): dense voyage-4-lite, recursive 300/50, K=3, metadata filter.
Exp 11: evaluator supplies the exact required clauses (evaluation-only, never a runtime path).
Exp 12: retrieved excerpts + code-computed facts (src/rules.facts); plus an upper-bound variant with oracle clauses + facts."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm_exp, retrieval, embed, retrievers, rag_run, policy, evaluate, rules
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
EM, CFG, K, SPLITS = "voyageai/voyage-4-lite", "recursive300_50", 3, ["DEVELOPMENT", "VALIDATION"]
cases = [dict(c, _split=s) for s in SPLITS for c in llm_exp.cases_for(s)]
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
gt = evaluate.load_gt()
R = retrievers.Retriever(EM, CFG)
qv = embed.embed(EM, [retrieval.claim_query(c) for c in cases], tag="EXP11_12")
_, _, rag_ctx = rag_run.retrieve(R, cases, "dense", K, True, qv, "EXP11_12", "retrieval_for_reference", EM)   # same context as Exp 9 'filtered'
oracle_ctx = {c["case_id"]: policy.render(gt[c["case_id"]]["required_policy_ids"]) for c in cases}       # evaluator-supplied
facts = {c["case_id"]: rules.facts(c) for c in cases}
HYBRID_SYSTEM = rag_run.HYBRID_SYSTEM


def go(exp, name, ctx, system, with_facts):
    out = {}
    for split in SPLITS:
        for m in models:
            def user(c):
                u = f"CLAIM:\n{json.dumps(llm_exp.visible(c), indent=1)}\n\nPOLICY EXCERPTS:\n{ctx[c['case_id']]}"
                return u + (f"\n\nVERIFIED CALCULATIONS:\n{facts[c['case_id']]}" if with_facts else "")
            s, recs, rows = llm_exp.run(exp, m, split, system, user, config={"temperature": 0, "name": name, "retriever": EM, "chunking": CFG, "k": K, "facts": with_facts})
            out[(split, m)] = s
    return out


variants = {
    "RAG (Exp 9 filtered)": ("EXP09_METADATA_FILTERED", rag_ctx, rag_run.RAG_SYSTEM, False),
    "Policy oracle (Exp 11)": ("EXP11_ORACLE", oracle_ctx, rag_run.RAG_SYSTEM, False),
    "RAG + code facts (Exp 12)": ("EXP12_HYBRID", rag_ctx, HYBRID_SYSTEM, True),
    "Oracle + code facts (upper bound)": ("EXP12_HYBRID_ORACLE", oracle_ctx, HYBRID_SYSTEM, True),
}
res = {}
for name, (exp, ctx, sysm, wf) in variants.items():
    res[name] = go(exp, name, ctx, sysm, wf)
    for (sp, m), s in res[name].items():
        print(f"{name:34s} {sp[:3]} {m.split('/')[-1]:16s} {s['correct']}/{s['n']} FA {s['false_approvals']}/{s['non_approvable']} HRR {s['human_review_rate']:.3f} in_tok {s['input_tokens']} out_tok {s['output_tokens']} ${s['total_cost_usd']:.4f} med {s['median_latency_ms']:.0f}ms p95 {s['p95_latency_ms']}ms  {s['decision_counts']}")
out = C.RESULTS / "development" / "exp11_12"; out.mkdir(parents=True, exist_ok=True)
(out / "summary.json").write_text(json.dumps({n: {f"{sp}|{m}": s for (sp, m), s in r.items()} for n, r in res.items()}, indent=2, default=str))
# plot: correct rate and false approvals by variant/model on development; cost
fig, ax = plt.subplots(1, 4, figsize=(21, 4.3))
names = list(variants)
for j, m in enumerate(models):
    for k, sp in enumerate(SPLITS):
        ax[0].bar([i + (j * 2 + k - 1.5) * 0.2 for i in range(len(names))], [res[n][(sp, m)]["correct_disposition_rate"] for n in names], 0.2, label=f"{m.split('/')[-1]} {sp[:3]}")
ax[0].axhline(47 / 60, ls="--", c="k", lw=0.8); ax[0].text(-0.4, 47 / 60 + 0.01, "rules only (dev) 0.78", fontsize=7)
ax[0].set_xticks(range(len(names))); ax[0].set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=6); ax[0].set_ylim(0, 1); ax[0].legend(fontsize=6); ax[0].set_title("Correct Disposition Rate")
for j, m in enumerate(models):
    ax[1].bar([i + (j - 0.5) * 0.35 for i in range(len(names))], [res[n][("DEVELOPMENT", m)]["false_approval_rate"] for n in names], 0.35, label=m.split("/")[-1])
ax[1].axhline(0.10, ls="--", c="k", lw=0.8); ax[1].set_xticks(range(len(names))); ax[1].set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=6); ax[1].legend(fontsize=7); ax[1].set_title("False Approval Rate (dev)")
for j, m in enumerate(models):
    ax[2].bar([i + (j - 0.5) * 0.35 for i in range(len(names))], [res[n][("DEVELOPMENT", m)]["input_tokens"] / 1000 for n in names], 0.35, label=m.split("/")[-1])
ax[2].set_xticks(range(len(names))); ax[2].set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=6); ax[2].set_title("Input tokens (k, dev)"); ax[2].legend(fontsize=7)
ax[3].bar([n.replace(" (", "\n(") for n in names], [res[n][("DEVELOPMENT", models[0])]["total_cost_usd"] for n in names], color="C2"); ax[3].tick_params(axis="x", labelsize=6)
ax[3].set_title(f"{models[0].split('/')[-1]} cost (USD, dev)")
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp11_12_oracle_and_hybrid.png", dpi=130)
