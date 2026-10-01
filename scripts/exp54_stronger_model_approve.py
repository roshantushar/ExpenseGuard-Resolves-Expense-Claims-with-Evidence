"""Exp 54: diagnostic-only. Isolates model capability from prompt wording -- runs the FROZEN, unmodified
SYSTEM_LLM_STEP prompt (src/resolver.py, hash-pinned) against a fixed set of 5 dev-residual APPROVE cases,
swapping only the model (gpt-4o instead of gpt-4o-mini). Answers: is the zero-APPROVE behavior a prompt
problem (Exp 53) or a reasoning-capability problem? Dev split only; does not touch resolver.py itself.
"""
from __future__ import annotations
import json
from src import config as C, resolver as R, llm_exp, retrieval, retrievers, embed, hybrid_facts as HF

# 5 real APPROVE cases from the 36 dev-residual set, chosen to be the HARDEST unsolved ones from Exp 53
# (3x HOTEL_CEILING -- the exact family that produced confident-wrong REJECTs in Exp 53's V3/V3b -- plus
# 2 other families neither variant solved), not the easy ones V3b already got right.
CASE_IDS = ["X2-011", "X2-029", "X2-143", "X2-047", "X2-003"]


def main():
    cases = llm_exp.cases_for("DEVELOPMENT")
    by_id = {c["case_id"]: c for c in cases}
    residual = [by_id[cid] for cid in CASE_IDS]

    RT = retrievers.Retriever(R.EMB, R.CFG)
    qv = embed.embed(R.EMB, [retrieval.claim_query(cc) for cc in residual], tag="EXP54")
    ctx = {cc["case_id"]: RT.context(RT.rank("dense", "unused", q, R.K, R._mask(RT.chunks, cc)))
           for cc, q in zip(residual, qv)}
    facts = {cc["case_id"]: HF.facts_block(HF.extract(cc)[1], R.FACT_LEVELS) for cc in residual}

    def user_fn(cc):
        return f"CLAIM:\n{json.dumps(llm_exp.visible(cc), indent=1)}\n\nDETERMINISTIC FACTS:\n{json.dumps(facts[cc['case_id']], indent=1, default=str)}\n\nRETRIEVED POLICY EXCERPTS:\n{ctx[cc['case_id']]}"

    summary, recs, rows = llm_exp.run("EXP54_STRONGER_MODEL", "openai/gpt-4o", "DEVELOPMENT", R.SYSTEM_LLM_STEP, user_fn, cases=residual, config={"model_only_change": True})
    print(json.dumps({k: summary[k] for k in ("n", "correct", "correct_disposition_rate", "false_approvals", "decision_counts", "total_cost_usd")}, indent=2))
    for r in recs:
        print(r["case_id"], "->", r["predicted_decision"], "|", (r.get("explanation") or "")[:200])


if __name__ == "__main__":
    main()
