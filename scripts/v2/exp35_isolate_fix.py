"""Exp 35: isolating the Exp 34 fix across layers -- prompt (35A), model (35B), tool-interface (35C).
One variable changes at a time relative to the Exp 34 baseline (gpt-4o-mini, 4/13, default prompt and
tools). Same 13 C_AGENT_DYNAMIC development claims as Exp 18/19/20/34.

35B (model swap) is NOT run by this script -- it costs materially more per call and is checked with a
one-case pilot first (see the session transcript) before committing to a full 13-case run, per the
project's standing "print projected cost before a batch" rule.

Usage: python -m scripts.v2.exp35_isolate_fix [35a|35c|both]
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src import config as C, llm, llm_exp, evaluate, agent, agent_variants as V

EXP = "EXP35"


def run_variant(name: str, targets: list, **run_kwargs) -> dict:
    spent_before = llm.spent()
    out = {}
    for i, c in enumerate(targets):
        out[c["case_id"]] = agent.run(c, tag=f"{EXP}_{name.upper()}", **run_kwargs)
        r = out[c["case_id"]]
        print(f"  [{name}][{i + 1}/{len(targets)}] {c['case_id']} -> {r['decision']} ({r['turns']} turns, ${r['cost_usd']:.4f})")
    print(f"  {name} total spend: ${llm.spent() - spent_before:.4f}")
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    gt = evaluate.load_gt()
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    groupC = [gt[cid] for cid in gt if gt[cid]["split"] == "DEVELOPMENT" and gt[cid]["architecture_group"] == "C_AGENT_DYNAMIC"]
    targets = [cases[g["case_id"]] for g in groupC]
    assert len(targets) == 13, f"expected 13 group-C dev claims, found {len(targets)}"
    print(f"{len(targets)} group-C claims | spend so far ${llm.spent():.4f}")

    out_dir = C.RESULTS / "development" / "exp35_isolate_fix"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    if which in ("35a", "both"):
        results["35a_prompt_fix"] = run_variant("35a", targets, system_template=V.SYSTEM_35A)

    if which in ("35c", "both"):
        # per-case tool sets (search_policy_corpus is closured per case already; wrap specs/tools per case)
        agent_out = {}
        spent_before = llm.spent()
        for i, c in enumerate(targets):
            specs, case_tools = V.specs_and_tools_35c(c)
            agent_out[c["case_id"]] = agent.run(c, tag=f"{EXP}_35C", specs=specs, case_tools=case_tools)
            r = agent_out[c["case_id"]]
            print(f"  [35c][{i + 1}/{len(targets)}] {c['case_id']} -> {r['decision']} ({r['turns']} turns, ${r['cost_usd']:.4f})")
        print(f"  35c total spend: ${llm.spent() - spent_before:.4f}")
        results["35c_tool_interface_fix"] = agent_out

    if which in ("35c_v2", "both"):
        agent_out = {}
        spent_before = llm.spent()
        for i, c in enumerate(targets):
            specs, case_tools = V.specs_and_tools_35c_v2(c)
            agent_out[c["case_id"]] = agent.run(c, tag=f"{EXP}_35C_V2", system_template=V.SYSTEM_35C, specs=specs, case_tools=case_tools)
            r = agent_out[c["case_id"]]
            print(f"  [35c_v2][{i + 1}/{len(targets)}] {c['case_id']} -> {r['decision']} ({r['turns']} turns, ${r['cost_usd']:.4f})")
        print(f"  35c_v2 total spend: ${llm.spent() - spent_before:.4f}")
        results["35c_v2_tool_interface_fix_unconfounded"] = agent_out

    for name, out in results.items():
        recs = [{"case_id": cid, "predicted_decision": d["decision"], "policy_evidence": d.get("policy_evidence", []), "missing_fields": d.get("missing_fields", []),
                 "manual_review_required": d["decision"] == "ESCALATE", "latency_ms": 0, "input_tokens": d.get("input_tokens", 0), "output_tokens": d.get("output_tokens", 0),
                 "model_cost_usd": d.get("cost_usd", 0.0), "error": None} for cid, d in out.items()]
        s, rows = evaluate.evaluate(recs, gt)
        (out_dir / f"predictions_{name}.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        (out_dir / f"traces_{name}.json").write_text(json.dumps(out, indent=1, default=str))
        (out_dir / f"summary_{name}.json").write_text(json.dumps(s, indent=1, default=str))
        turns = [d["turns"] for d in out.values()]
        print(f"\n=== {name}: {s['correct']}/{s['n']} ({s['correct_disposition_rate']:.1%}) | FAR {s['false_approval_rate']:.1%} | HRR {s['human_review_rate']:.1%} "
              f"| avg turns {sum(turns) / len(turns):.2f} | step-cap hits {sum(d['step_cap_hit'] for d in out.values())} "
              f"| wrong-tool calls {sum(d['wrong_tool_calls'] for d in out.values())} ===")


if __name__ == "__main__":
    main()
