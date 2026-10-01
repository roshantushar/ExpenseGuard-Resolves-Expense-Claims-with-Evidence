"""Exp 56: live guarded-agent run with ONLY check_hotel_compliance's ceiling math corrected (Exp 56's
compute_hotel_ceiling, scripts/hotel_ceiling_v56.py). Same system prompt, same every other tool, same
disposition gate -- unchanged, per instruction (the gate correctly enforced the tool's answer; the tool
was wrong, not the gate). Does not edit src/agent.py or src/agent_variants.py (not frozen, but kept
intact per instruction so Exp 40-52's saved results stay reproducible against the original files).

Test set: X2-011, X2-029, X2-139 (the three requested APPROVE cases) plus every other dev-split HOTEL
case, including X2-132 (Tokyo, before CIRC-25-06's 2025-07-01 effective date -- must NOT get the uplift)
and X2-148 (above the ceiling even after any applicable adjustment -- must still REJECT). All 18 dev-split
HOTEL-family cases are run, both with the original tool and the corrected one, so FAR and accuracy are
measured on the same, real, unmodified population.
"""
from __future__ import annotations
import json
from src import agent, agent_variants as V, llm_exp
from scripts.hotel_ceiling_v56 import make_check_hotel_compliance_v56

HOTEL_CASES = ["X2-005", "X2-011", "X2-012", "X2-029", "X2-036", "X2-087", "X2-089", "X2-095", "X2-098",
               "X2-104", "X2-111", "X2-121", "X2-128", "X2-132", "X2-139", "X2-142", "X2-143", "X2-148"]


def run_one(case, fixed: bool, tag: str):
    specs, case_tools = V.specs_and_tools_47(case)
    if fixed:
        case_tools = dict(case_tools, check_hotel_compliance=make_check_hotel_compliance_v56(case))
    raw = agent.run(case, system_template=V.SYSTEM_47, specs=specs, case_tools=case_tools, max_steps=8, tag=tag)
    gated = V.gate_disposition(V.gate_approve(raw))
    return gated


def main():
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    gt = {json.loads(l)["case_id"]: json.loads(l)["expected_decision"] for l in open("ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")}

    rows = []
    for cid in HOTEL_CASES:
        c = cases[cid]
        before = run_one(c, fixed=False, tag="EXP56_BEFORE")
        after = run_one(c, fixed=True, tag="EXP56_AFTER")
        rows.append((cid, gt[cid], before["decision"], after["decision"]))
        print(f"{cid:8s} gt={gt[cid]:20s} before={before['decision']:20s} after={after['decision']:20s}"
              + ("  <-- CHANGED" if before["decision"] != after["decision"] else ""))

    def metrics(col):
        correct = sum(1 for cid, g, b, a in rows if (a if col == "after" else b) == g)
        approve_gt = [r for r in rows if r[1] == "APPROVE"]
        approve_hit = sum(1 for cid, g, b, a in approve_gt if (a if col == "after" else b) == "APPROVE")
        non_approve = [r for r in rows if r[1] != "APPROVE"]
        false_appr = sum(1 for cid, g, b, a in non_approve if (a if col == "after" else b) == "APPROVE")
        return correct, approve_hit, len(approve_gt), false_appr, len(non_approve)

    for col in ("before", "after"):
        c, ah, at, fa, nt = metrics(col)
        print(f"\n{col.upper()}: accuracy {c}/{len(rows)}, APPROVE recall {ah}/{at}, false approvals {fa}/{nt}")


if __name__ == "__main__":
    main()
