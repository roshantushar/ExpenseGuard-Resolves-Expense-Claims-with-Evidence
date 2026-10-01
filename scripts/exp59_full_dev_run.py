"""Exp 59 full run: fixed deterministic routing (deterministic_fixed) + fixed agent tools (build_tools_v59)
across the entire 70-case development split, live, compared against the unmodified Exp 47 configuration
(the same "before" used throughout this investigation). src/*.py is not edited anywhere.
"""
from __future__ import annotations
import json
from src import llm_exp
from scripts.exp58_full_agent_fix import run_one as run_one_before
from scripts.exp59_final_fix import deterministic_fixed, run_one_v59


def main():
    cases = llm_exp.cases_for("DEVELOPMENT")
    gt = {json.loads(l)["case_id"]: json.loads(l)["expected_decision"] for l in open("ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")}

    det_before = {}
    det_after = {}
    from src import resolver as R
    for c in cases:
        det_before[c["case_id"]] = R.deterministic(c)
        det_after[c["case_id"]] = deterministic_fixed(c)

    residual_after = [c for c in cases if not det_after[c["case_id"]][1]]
    print(f"total dev cases: {len(cases)}, residual under FIXED routing: {len(residual_after)}")

    before, after = {}, {}
    for i, c in enumerate(cases, 1):
        cid = c["case_id"]
        # BEFORE: exactly the original, unmodified Exp 47 pipeline (deterministic routing + agent).
        d, conclusive = det_before[cid]
        before[cid] = d["decision"] if conclusive else run_one_before(c, False, "EXP59_FULL_BEFORE")["decision"]
        # AFTER: fixed routing + fixed tools.
        d2, conclusive2 = det_after[cid]
        after[cid] = d2["decision"] if conclusive2 else run_one_v59(c, "EXP59_FULL_AFTER")["decision"]
        tag = "  <-- CHANGED" if before[cid] != after[cid] else ""
        print(f"[{i}/{len(cases)}] {cid:8s} gt={gt[cid]:20s} before={before[cid]:20s} after={after[cid]:20s}{tag}")

    def metrics(d):
        correct = sum(1 for c in cases if d[c["case_id"]] == gt[c["case_id"]])
        approve_ids = [c["case_id"] for c in cases if gt[c["case_id"]] == "APPROVE"]
        ah = sum(1 for cid in approve_ids if d[cid] == "APPROVE")
        non_ids = [c["case_id"] for c in cases if gt[c["case_id"]] != "APPROVE"]
        fa = sum(1 for cid in non_ids if d[cid] == "APPROVE")
        return correct, ah, len(approve_ids), fa, len(non_ids)

    for name, d in [("BEFORE", before), ("AFTER", after)]:
        c, ah, at, fa, nt = metrics(d)
        print(f"\n{name}: accuracy {c}/70, APPROVE recall {ah}/{at}, false approvals {fa}/{nt}")


if __name__ == "__main__":
    main()
