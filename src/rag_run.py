"""Helpers shared by Exp 7-9: run a retrieval config over cases, log it, and run the downstream LLMs."""
from __future__ import annotations
import json, statistics as st
from . import llm, llm_exp, embed, retrieval, retrieval_eval, evaluate

RAG_SYSTEM = ("You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement, using ONLY the retrieved policy excerpts provided. "
              "Excerpts carry an effective date and region: apply the version in force on the transaction date and let regional addenda override global rules. If the excerpts do not contain what is needed, say so via REQUEST_INFORMATION or ESCALATE rather than guessing.\n" + llm_exp.SCHEMA)
HYBRID_SYSTEM = RAG_SYSTEM + ("\nYou are also given VERIFIED CALCULATIONS computed by deterministic code from the claim and enterprise records (currency conversion, per-person spend, "
                                 "ceilings, dates, thresholds, exact-duplicate and approval-record lookups). Trust them; do not redo the arithmetic. Semantic judgments remain yours: whether a meal is "
                                 "client or employee-only, whether the description is specific enough, whether the bill and description conflict, and which clauses apply.")
KEYS = ("recall", "precision", "rr", "ndcg", "full", "ctx_words", "wrong_year_chunks", "wrong_region_chunks")


def retrieve(R, cases, mode, k, filt, qvecs, exp, name, embed_model):
    gt = evaluate.load_gt()
    rows, ctx = [], {}
    for c, q in zip(cases, qvecs):
        hits = R.rank(mode, retrieval.claim_query(c), q, k, R.allowed(c) if filt else None)
        ctx[c["case_id"]] = R.context(hits)
        m = retrieval_eval.score(c, set(gt[c["case_id"]]["required_policy_ids"]), R.chunks, hits, k)
        rows.append({"case_id": c["case_id"], "split": c["_split"], "scores": [round(s, 4) for _, s in hits], **m})
    agg = {kk: round(st.mean(float(r[kk]) for r in rows), 4) for kk in KEYS}
    rid = f"{exp}-{name}"
    llm.log_event(type="experiment_summary", run_id=rid, experiment=exp, split="DEV+VAL", model=embed_model, config_name=name, mode=mode, k=k, metadata_filter=filt, part="retrieval", chunk_cfg=R.idx["cfg"], **agg)
    for r in rows:
        llm.log_event(type="retrieval", run_id=rid, experiment=exp, config_name=name, mode=mode, k=k, metadata_filter=filt, **r)
    return agg, rows, ctx


def downstream(exp, name, ctx, splits, models, cfg):
    out = {}
    for split in splits:
        for m in models:
            s, recs, _ = llm_exp.run(exp, m, split, RAG_SYSTEM,
                                     lambda c: f"CLAIM:\n{json.dumps(llm_exp.visible(c), indent=1)}\n\nRETRIEVED POLICY EXCERPTS:\n{ctx[c['case_id']]}", config={"temperature": 0, "name": name, **cfg})
            out[(split, m)] = (s, recs)
    return out
