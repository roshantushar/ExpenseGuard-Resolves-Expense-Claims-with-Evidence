"""Part of Exp 60's correction pass (see docs/exp60_fresh_holdout.md): a general, procedural gate closing
the "advisory tool silently skipped" failure class (X2-061 earlier this session, then X3-019 on the Exp 60
holdout). For any expense type with a dedicated compliance tool, an APPROVE is not trusted unless that tool
was actually consulted successfully; otherwise the decision falls back to ESCALATE -- a safe, valid
outcome, not a guess. Asserts no new substantive policy judgment, only that verification happened.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import agent, agent_variants as V, rules_text as RT
from scripts.exp59_final_fix import build_tools_v59, gate_evidence_consistency, gate_gift_recipient

REQUIRED_TOOL = {
    "HOTEL": "check_hotel_compliance", "MEAL_CLIENT": "check_meal_compliance", "MEAL_EMPLOYEE": "check_meal_compliance",
    "GIFT": "check_gift_compliance", "AIRFARE": "check_airfare_compliance", "TRAINING": "check_training_compliance",
    "SOFTWARE": "check_software_compliance", "MILEAGE": "check_mileage_compliance",
}


def gate_require_category_tool(case: dict, result: dict) -> dict:
    f = RT.parse(case)
    tool = REQUIRED_TOOL.get(f.get("expense_type"))
    if not tool or result.get("decision") != "APPROVE":
        return result
    consulted_cleanly = any(
        step["tool"] == tool and (step.get("observation") or {}).get("ok")
        and not (step["observation"].get("data") or {}).get("policy_disposition")
        for step in result.get("trace", [])
    )
    if not consulted_cleanly:
        return {**result, "decision": "ESCALATE", "explanation": result.get("explanation", "") +
                f" [gate: overridden from APPROVE -- {tool} was never consulted (or returned an issue) for this claim; "
                f"an APPROVE is not trusted without it.]"}
    return result


def run_candidate(case, model: str | None = None, tag: str = "EXP60_CANDIDATE"):
    specs, case_tools, system = build_tools_v59(case)
    raw = agent.run(case, model=model, system_template=system, specs=specs, case_tools=case_tools, max_steps=8, tag=tag)
    result = V.gate_disposition(V.gate_approve(raw))
    result = gate_evidence_consistency(case, result)
    result = gate_gift_recipient(case, result)
    result = gate_require_category_tool(case, result)
    return result
