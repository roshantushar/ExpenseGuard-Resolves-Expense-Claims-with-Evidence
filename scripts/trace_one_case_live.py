"""Diagnostic-only, not an experiment: run the real guarded agent (src/agent.py + src/agent_variants.py's
Exp 47 tool set -- the same code resolve_batch_v2 calls) on ONE real case, live, and print every turn in
full: the model's raw tool call, the tool's raw return value, and the final gated decision. No frozen file
is modified. Dev split case only.
"""
from __future__ import annotations
import json
from src import agent, agent_variants as V, llm_exp

CASE_ID = __import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "X2-011"


def main():
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    case = cases[CASE_ID]
    print("CLAIM:", json.dumps({k: v for k, v in case.items() if k != "split"}, indent=1))
    specs, case_tools = V.specs_and_tools_47(case)
    raw = agent.run(case, system_template=V.SYSTEM_47, specs=specs, case_tools=case_tools, max_steps=8, tag="TRACE_LIVE")
    gated1 = V.gate_approve(raw)
    gated2 = V.gate_disposition(gated1)

    print(f"\n{'='*70}\nTURN-BY-TURN TRACE ({raw['turns']} turns, ${raw['cost_usd']:.4f})\n{'='*70}")
    for i, step in enumerate(raw["trace"], 1):
        print(f"\n--- Turn {i} ---")
        print("Model called tool:", step["tool"])
        print("With args:", json.dumps(step["args"], indent=1))
        print("Tool returned:", json.dumps(step["observation"], indent=1, default=str))

    print(f"\n{'='*70}\nRAW MODEL FINAL DECISION (before any gate): {raw['decision']}")
    print("Raw explanation:", raw.get("explanation"))
    print(f"\nAFTER gate_approve: {gated1['decision']}")
    print(f"AFTER gate_disposition (what resolve_batch_v2 actually ships): {gated2['decision']}")
    print("Final explanation:", gated2.get("explanation"))


if __name__ == "__main__":
    main()
