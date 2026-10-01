"""Exp 57: apply the Exp 56 hotel-ceiling fix to the OTHER path -- hybrid_facts.h2_temporal's
applicable_hotel_ceiling_local_currency, used by the single-shot frozen-resolver LLM step (resolve_batch),
not the guarded agent. Same fix (base -> circular -> partner uplift -> long-stay -> fallback tier), same
unmodified resolver.SYSTEM_LLM_STEP prompt, same live gpt-4o-mini, same 18 dev-split HOTEL-family cases as
Exp 56, for a direct, apples-to-apples comparison between the two paths.
"""
from __future__ import annotations
import json
from src import config as C, resolver as R, llm_exp, retrieval, retrievers, embed, hybrid_facts as HF, rules_text as RT
from scripts.hotel_ceiling_v56 import compute_hotel_ceiling

HOTEL_CASES = ["X2-005", "X2-011", "X2-012", "X2-029", "X2-036", "X2-087", "X2-089", "X2-095", "X2-098",
               "X2-104", "X2-111", "X2-121", "X2-128", "X2-132", "X2-139", "X2-142", "X2-143", "X2-148"]


def fixed_ceiling_fact(cc, f):
    """Only overrides the fact when nights is already known (same information the official fact had
    access to) -- this isolates the ceiling-calculation fix from any attendee/date-parsing fix."""
    if not f.get("nights"):
        return None
    from src import tables as T
    grade = T.employee(cc["employee_id"])["grade"]
    r = compute_hotel_ceiling(cc, grade, f["nights"])
    return r["ceiling"] if r.get("ok") else None


def run_variant(fixed: bool, tag: str):
    cases_all = llm_exp.cases_for("DEVELOPMENT")
    by_id = {c["case_id"]: c for c in cases_all}
    cases = [by_id[cid] for cid in HOTEL_CASES]
    det = {c["case_id"]: R.deterministic(c) for c in cases}
    residual = [c for c in cases if not det[c["case_id"]][1]]

    RTr = retrievers.Retriever(R.EMB, R.CFG)
    qv = embed.embed(R.EMB, [retrieval.claim_query(cc) for cc in residual], tag=tag)
    ctx = {cc["case_id"]: RTr.context(RTr.rank("dense", "unused", q, R.K, R._mask(RTr.chunks, cc))) for cc, q in zip(residual, qv)}

    facts = {}
    for cc in residual:
        f, fam = HF.extract(cc)
        base = HF.facts_block(fam, R.FACT_LEVELS)
        if fixed and "applicable_hotel_ceiling_local_currency" in base:
            new_ceil = fixed_ceiling_fact(cc, f)
            if new_ceil is not None:
                base = dict(base, applicable_hotel_ceiling_local_currency=new_ceil)
        facts[cc["case_id"]] = base

    def user_fn(cc):
        return f"CLAIM:\n{json.dumps(llm_exp.visible(cc), indent=1)}\n\nDETERMINISTIC FACTS:\n{json.dumps(facts[cc['case_id']], indent=1, default=str)}\n\nRETRIEVED POLICY EXCERPTS:\n{ctx[cc['case_id']]}"

    summary, recs, rows = llm_exp.run(tag, "openai/gpt-4o-mini", "DEVELOPMENT", R.SYSTEM_LLM_STEP, user_fn, cases=residual, config={"fixed": fixed})

    gt = {json.loads(l)["case_id"]: json.loads(l)["expected_decision"] for l in open(C.ROOT / "ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")}
    out = {}
    for c in cases:
        d, conclusive = det[c["case_id"]]
        out[c["case_id"]] = d["decision"] if conclusive else next(r["predicted_decision"] for r in recs if r["case_id"] == c["case_id"])
    return out, gt


def main():
    before, gt = run_variant(False, "EXP57_BEFORE")
    after, _ = run_variant(True, "EXP57_AFTER")
    for cid in HOTEL_CASES:
        tag = "  <-- CHANGED" if before[cid] != after[cid] else ""
        print(f"{cid:8s} gt={gt[cid]:20s} before={before[cid]:20s} after={after[cid]:20s}{tag}")

    def metrics(d):
        correct = sum(1 for cid in HOTEL_CASES if d[cid] == gt[cid])
        approve_ids = [cid for cid in HOTEL_CASES if gt[cid] == "APPROVE"]
        ah = sum(1 for cid in approve_ids if d[cid] == "APPROVE")
        non_ids = [cid for cid in HOTEL_CASES if gt[cid] != "APPROVE"]
        fa = sum(1 for cid in non_ids if d[cid] == "APPROVE")
        return correct, ah, len(approve_ids), fa, len(non_ids)

    for name, d in [("BEFORE", before), ("AFTER", after)]:
        c, ah, at, fa, nt = metrics(d)
        print(f"\n{name}: accuracy {c}/{len(HOTEL_CASES)}, APPROVE recall {ah}/{at}, false approvals {fa}/{nt}")


if __name__ == "__main__":
    main()
