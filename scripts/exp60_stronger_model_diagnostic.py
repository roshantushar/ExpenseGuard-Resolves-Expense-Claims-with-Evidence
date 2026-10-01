"""Diagnostic only, NOT a rerun of Exp 60. Tests whether X3-019 and X3-049 (the two false approvals from
the Exp 60 holdout) are specific to gpt-4o-mini or would also fool a stronger model -- same architecture,
same isolated tables, same cases, only the model changes (openai/gpt-4o instead of gpt-4o-mini). This does
NOT alter the reported 36/50 Exp 60 result (docs/exp60_fresh_holdout.md); it is a separate, clearly labeled
follow-up question, same pattern as Exp 54's stronger-model diagnostic.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "exp60_holdout"
sys.path.insert(0, str(ROOT))

from src import config as C
C.ENTERPRISE = HOLDOUT / "enterprise_data"

from src import agent, agent_variants as V
from scripts.exp59_final_fix import build_tools_v59, gate_evidence_consistency, gate_gift_recipient

CASES = ["X3-019", "X3-049"]


def run_with_model(case, model, tag):
    specs, case_tools, system = build_tools_v59(case)
    raw = agent.run(case, model=model, system_template=system, specs=specs, case_tools=case_tools, max_steps=8, tag=tag)
    result = V.gate_disposition(V.gate_approve(raw))
    result = gate_evidence_consistency(case, result)
    result = gate_gift_recipient(case, result)
    return result


def main():
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in (HOLDOUT / "cases.jsonl").read_text().splitlines()}
    gt = {r["case_id"]: r for r in (json.loads(l) for l in (HOLDOUT / "ground_truth_private.jsonl").read_text().splitlines())}

    for cid in CASES:
        c = cases[cid]
        print(f"\n===== {cid} (gt={gt[cid]['expected_decision']}) =====")
        r = run_with_model(c, "openai/gpt-4o", "EXP60_DIAGNOSTIC_GPT4O")
        print("gpt-4o decision:", r["decision"], "|", r.get("explanation"))
        for i, step in enumerate(r["trace"], 1):
            print(f"  turn {i}:", step["tool"], step["args"])
            print("    ->", json.dumps(step["observation"])[:200])


if __name__ == "__main__":
    main()
