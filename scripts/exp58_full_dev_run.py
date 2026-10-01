"""Exp 58 full run: the guarded agent (src/agent.py + src/agent_variants.py's Exp 47 tool set, unmodified)
across the ENTIRE 70-case development split, live, comparing the original tool set against Exp 58's fixed
one (hotel-ceiling fix from Exp 56 + new check_mileage_compliance + new check_software_compliance, all
standalone additions -- src/agent.py and src/agent_variants.py are not edited). Same disposition gate,
same prompt otherwise, same everything else. This is the direct, final comparison against the guarded
agent's own documented dev baseline (44/70 accuracy, 6/18 APPROVE recall, 0/52 false approvals).
"""
from __future__ import annotations
import json
from src import resolver as R, llm_exp, agent_variants as V
from scripts.exp58_full_agent_fix import run_one


def main():
    cases = llm_exp.cases_for("DEVELOPMENT")
    gt = {json.loads(l)["case_id"]: json.loads(l)["expected_decision"] for l in open("ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")}
    det = {c["case_id"]: R.deterministic(c) for c in cases}
    residual = [c for c in cases if not det[c["case_id"]][1]]
    print(f"total dev cases: {len(cases)}, residual (go to agent): {len(residual)}")

    before, after = {}, {}
    for i, c in enumerate(residual, 1):
        before[c["case_id"]] = run_one(c, False, "EXP58_FULL_BEFORE")["decision"]
        after[c["case_id"]] = run_one(c, True, "EXP58_FULL_AFTER")["decision"]
        tag = "  <-- CHANGED" if before[c["case_id"]] != after[c["case_id"]] else ""
        print(f"[{i}/{len(residual)}] {c['case_id']:8s} gt={gt[c['case_id']]:20s} before={before[c['case_id']]:20s} after={after[c['case_id']]:20s}{tag}")

    def full_decision(cid, col):
        d, conclusive = det[cid]
        if conclusive:
            return d["decision"]
        return (after if col == "after" else before)[cid]

    def metrics(col):
        correct = sum(1 for c in cases if full_decision(c["case_id"], col) == gt[c["case_id"]])
        approve_ids = [c["case_id"] for c in cases if gt[c["case_id"]] == "APPROVE"]
        ah = sum(1 for cid in approve_ids if full_decision(cid, col) == "APPROVE")
        non_ids = [c["case_id"] for c in cases if gt[c["case_id"]] != "APPROVE"]
        fa = sum(1 for cid in non_ids if full_decision(cid, col) == "APPROVE")
        return correct, ah, len(approve_ids), fa, len(non_ids)

    for col in ("before", "after"):
        c, ah, at, fa, nt = metrics(col)
        print(f"\n{col.upper()} (full 70-case dev, incl. deterministic path unchanged): accuracy {c}/70, APPROVE recall {ah}/{at}, false approvals {fa}/{nt}")


if __name__ == "__main__":
    main()
