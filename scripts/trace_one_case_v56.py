"""Same as trace_one_case_live.py but using the Exp 56 corrected check_hotel_compliance tool."""
from __future__ import annotations
import json, sys
from src import agent, agent_variants as V, llm_exp
from scripts.hotel_ceiling_v56 import make_check_hotel_compliance_v56

CASE_ID = sys.argv[1] if len(sys.argv) > 1 else "X2-104"


def main():
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    case = cases[CASE_ID]
    print("CLAIM:", json.dumps({k: v for k, v in case.items() if k != "split"}, indent=1))
    specs, case_tools = V.specs_and_tools_47(case)
    case_tools = dict(case_tools, check_hotel_compliance=make_check_hotel_compliance_v56(case))
    raw = agent.run(case, system_template=V.SYSTEM_47, specs=specs, case_tools=case_tools, max_steps=8, tag="TRACE_V56")
    gated = V.gate_disposition(V.gate_approve(raw))

    for i, step in enumerate(raw["trace"], 1):
        print(f"\n--- Turn {i} ---")
        print("tool:", step["tool"], "args:", json.dumps(step["args"]))
        print("returned:", json.dumps(step["observation"], indent=1, default=str))

    print(f"\nRAW decision: {raw['decision']} | {raw.get('explanation')}")
    print(f"GATED decision: {gated['decision']} | {gated.get('explanation')}")


if __name__ == "__main__":
    main()
