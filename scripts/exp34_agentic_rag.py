"""Exp 34: V3 pivot -- ReAct Agent + Agentic RAG (search_policy_corpus as a callable tool, multi-hop
enterprise lookups, a deterministic check_rate_ceiling calculator, record_decision as the terminal
tool) vs. the two systems already measured on the same claims: rules_v2.py alone (the project's
declared non-AI baseline) and the fixed workflow (Exp 18/30, one-pass RAG + one-hop tools).

Target set: the 13 C_AGENT_DYNAMIC ("group C") development-split claims (Exp 18/19/20's same set) -- the multi-hop families
(DYNAMIC_HOTEL_DISCOVERY, DYNAMIC_DELEGATION_CHAIN, DYNAMIC_PROJECT_BUDGET_CHAIN,
DYNAMIC_DEEP_HOTEL_CHAIN) -- because that is exactly where a fixed one-pass workflow structurally
cannot chase a discovered id (an exception_id or delegation_id only revealed by an earlier lookup),
and where 4 of the 10 DYNAMIC_HOTEL_DISCOVERY claims are now the V3 RAG-necessity cases (Chennai/Kobe)
that rules_v2.py and workflow_v2.py cannot resolve via table lookup at all.

Usage: python -m scripts.exp34_agentic_rag
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config as C, llm, llm_exp, evaluate, agent, workflow_v2, rules_text as RT, rules_v2 as RV2

EXP = "EXP34_AGENTIC_RAG"


def rules_only(c: dict) -> dict:
    f = RT.parse(c)
    return RV2.decide(dict(c, form=f))


def main():
    t0 = time.time()
    gt = evaluate.load_gt()
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    groupC = [gt[cid] for cid in gt if gt[cid]["split"] == "DEVELOPMENT" and gt[cid]["architecture_group"] == "C_AGENT_DYNAMIC"]
    targets = [cases[g["case_id"]] for g in groupC]
    assert len(targets) == 13, f"expected 13 group-C dev claims, found {len(targets)}"
    print(f"{len(targets)} group-C claims | spend so far ${llm.spent():.4f} of {__import__('os').environ['MAX_BUDGET_USD']}")

    baseline = {c["case_id"]: rules_only(c) for c in targets}
    wf = {c["case_id"]: workflow_v2.decide(c) for c in targets}

    spent_before = llm.spent()
    agent_out = {}
    for i, c in enumerate(targets):
        agent_out[c["case_id"]] = agent.run(c, max_steps=8)
        print(f"  [{i + 1}/{len(targets)}] {c['case_id']} -> {agent_out[c['case_id']]['decision']} "
              f"({agent_out[c['case_id']]['turns']} turns, ${agent_out[c['case_id']]['cost_usd']:.4f}) | spend ${llm.spent():.4f}")
    agent_spend = llm.spent() - spent_before

    recs = {name: [{"case_id": cid, "predicted_decision": d["decision"], "policy_evidence": d.get("policy_evidence", []), "missing_fields": d.get("missing_fields", []),
                    "manual_review_required": d["decision"] == "ESCALATE", "latency_ms": 0, "input_tokens": d.get("input_tokens", 0), "output_tokens": d.get("output_tokens", 0),
                    "model_cost_usd": d.get("cost_usd", 0.0), "error": None}
                   for cid, d in table.items()]
            for name, table in (("rules_only", baseline), ("workflow_v2", wf), ("agent_v3", agent_out))}

    out_dir = C.RESULTS / "development" / "exp34_agentic_rag"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, rr in recs.items():
        s, rows = evaluate.evaluate(rr, gt)
        summary[name] = s
        (out_dir / f"predictions_{name}.jsonl").write_text("\n".join(json.dumps(r) for r in rr) + "\n")
        (out_dir / f"evaluation_{name}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (out_dir / "agent_traces.json").write_text(json.dumps(agent_out, indent=1, default=str))
    (out_dir / "summary.json").write_text(json.dumps({**summary, "agent_spend_usd": round(agent_spend, 6), "wall_clock_s": round(time.time() - t0, 1)}, indent=1, default=str))

    print("\n=== Exp 34 summary (30 group-C dev claims) ===")
    for name in ("rules_only", "workflow_v2", "agent_v3"):
        s = summary[name]
        print(f"{name:12s} correct {s['correct']}/{s['n']} ({s['correct_disposition_rate']:.1%}) | FAR {s['false_approval_rate']:.1%} | HRR {s['human_review_rate']:.1%}")
    print(f"agent turns avg {sum(a['turns'] for a in agent_out.values()) / len(agent_out):.2f} | step-cap hits {sum(a['step_cap_hit'] for a in agent_out.values())} "
          f"| wrong-tool calls {sum(a['wrong_tool_calls'] for a in agent_out.values())} | agent spend ${agent_spend:.4f}")


if __name__ == "__main__":
    main()
