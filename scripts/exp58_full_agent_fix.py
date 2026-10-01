"""Exp 58: "fix this for everything." Extends Exp 56's pattern (compute the disposition in code, let the
gate enforce it) to the remaining gaps Exp 53 found -- mileage and the software business-owner check --
neither of which has ANY dedicated tool in the current guarded agent at all (agent_variants.py's own
comment on check_workflow_compliance says so explicitly: "It does NOT check telecom, training, mileage,
car rental or equipment category rules"). check_meal_compliance and check_gift_compliance already apply
their circulars correctly (verified by inspection) -- no fix needed there, only live verification that the
agent, which reads the raw note itself rather than a regex, doesn't have the same attendee/owner-extraction
gaps rules_text.py had.

Does not edit src/agent.py or src/agent_variants.py. Two new standalone tools, reusing rules_v2's exact
mileage/software math (frozen, unchanged), added alongside the existing (unmodified) Exp 47 tool set plus
Exp 56's hotel-ceiling fix, for one combined "Exp 58 full fix" agent configuration.
"""
from __future__ import annotations
import json
from src import agent, agent_variants as V, llm_exp, rules_text as RT, rules_v2 as RV
from scripts.hotel_ceiling_v56 import make_check_hotel_compliance_v56


def make_check_mileage_compliance(case: dict):
    f = RT.parse(case)

    def check_mileage_compliance(distance_km=None, odometer_start=None, odometer_end=None) -> dict:
        if f.get("expense_type") != "MILEAGE":
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a mileage expense; check_mileage_compliance does not apply here"}
        if odometer_start is not None and odometer_end is not None:
            try:
                distance_km = float(odometer_end) - float(odometer_start)
            except (TypeError, ValueError):
                return {"ok": False, "found": False, "data": None, "error": "odometer_start/odometer_end must be numbers"}
        if not distance_km or distance_km <= 0:
            return {"ok": False, "found": False, "data": None, "error": "distance_km not stated; pass distance_km directly, or odometer_start and odometer_end (code computes the difference)"}
        rate = RV.MILEAGE[RV.region(case)][RV.Y(case)]
        calculated = round(rate * distance_km, 2)
        billed = case["bill"]["total"]
        if billed > calculated + 0.005:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["GRD-4.1"], "rate_per_km": rate,
                                                          "distance_km": distance_km, "calculated_amount": calculated,
                                                          "reason": f"Claim {billed:.2f} exceeds calculated reimbursement {calculated:.2f} ({distance_km:g} km x {rate}/km)."}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": None, "rate_per_km": rate, "distance_km": distance_km, "calculated_amount": calculated,
                                                      "reason": "Claim amount matches or is below the calculated mileage reimbursement."}, "error": None}

    return check_mileage_compliance


def make_check_software_compliance(case: dict):
    f = RT.parse(case)

    def check_software_compliance(business_owner_name=None) -> dict:
        if f.get("expense_type") != "SOFTWARE":
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a software expense; check_software_compliance does not apply here"}
        if not business_owner_name or not str(business_owner_name).strip():
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["SWE-1.1"], "missing_fields": ["business_owner"],
                                                          "reason": "Named business owner required."}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "A named business owner was provided; no issue on this check "
                                                      "(call check_project_budget separately if this subscription is charged to a project)."}, "error": None}

    return check_software_compliance


MILEAGE_SPEC = ({"distance_km": ("amount?", None), "odometer_start": ("amount?", None), "odometer_end": ("amount?", None)},
                 "For a MILEAGE claim: pass distance_km directly if the note states it, OR pass odometer_start and odometer_end "
                 "(the tool computes the distance and the reimbursement in code -- never do this arithmetic yourself). Returns "
                 "policy_disposition directly.")
SOFTWARE_SPEC = ({"business_owner_name": ("str?", None)},
                  "For a SOFTWARE subscription claim: pass the named business owner exactly as stated or implied in the note "
                  "(e.g. 'managed by X', 'owned by X', 'X is responsible for this subscription') -- any phrasing that names a "
                  "specific person counts. Returns REQUEST_INFORMATION if no name is given.")

EXTRA_PROMPT = (" For a mileage claim, call check_mileage_compliance instead of computing the distance or reimbursement yourself "
                 "-- give it the odometer readings if that is what the note states, not a value you subtracted. For a software "
                 "subscription, call check_software_compliance with the named business owner you read from the note.")


def build_fixed_tools(case: dict):
    specs, case_tools = V.specs_and_tools_47(case)
    specs = {**specs, "check_mileage_compliance": MILEAGE_SPEC, "check_software_compliance": SOFTWARE_SPEC}
    case_tools = {**case_tools, "check_hotel_compliance": make_check_hotel_compliance_v56(case),
                  "check_mileage_compliance": make_check_mileage_compliance(case), "check_software_compliance": make_check_software_compliance(case)}
    system = V.SYSTEM_47 + EXTRA_PROMPT
    return specs, case_tools, system


def run_one(case, fixed: bool, tag: str):
    if fixed:
        specs, case_tools, system = build_fixed_tools(case)
    else:
        specs, case_tools = V.specs_and_tools_47(case)
        system = V.SYSTEM_47
    raw = agent.run(case, system_template=system, specs=specs, case_tools=case_tools, max_steps=8, tag=tag)
    return V.gate_disposition(V.gate_approve(raw))


if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else "X2-088"
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    c = cases[cid]
    r = run_one(c, True, "EXP58_SINGLE")
    print(cid, "->", r["decision"], "|", r.get("explanation"))
    for i, step in enumerate(r["trace"], 1):
        print(f"turn {i}: {step['tool']} {step['args']} -> {json.dumps(step['observation'])[:200]}")
