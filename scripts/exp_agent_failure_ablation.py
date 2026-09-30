"""problem.md Sec38 -- reproduced agent failures. Required once an agent survives the necessity gate
(it did: Exp 20, later Exp 34-52). Two ablations, each temporarily removing one guardrail from a COPY of
src/agent.py's loop (src/agent.py itself is never edited -- nothing to "restore" in the shipped code):

  Failure A: no call de-duplication, no step cap (run to a high step ceiling instead) -- does the agent
             loop or repeat calls without the safety net that normally masks this?
  Failure B: vague, overlapping tool descriptions -- does the agent pick the wrong tool more often?

Runs on 3 C_AGENT_DYNAMIC dev cases (X2-005, X2-037, X2-145 -- already used elsewhere in this project's
docs, so results are easy to cross-check) with the free local model (LOCAL_MODEL=llama3.2:3b via Ollama),
$0 cost, matching the project's own convention for budget-constrained live tests (see
scripts/v2/exp_owasp_llm_top10.py). Real paid budget was $0.35 of $5.00 remaining at the time this was
written -- too little to safely run this live against the paid model without risking hitting the hard cap
mid-experiment, so the free model is not a workaround here, it is the correct choice for this ablation.

ponytail: one script, one JSON + one markdown output, no test framework -- a one-shot diagnostic, not a
permanent fixture.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src import config as C, llm, llm_exp, agent as A, agent_tools as AT, tools as T

C.load_env()
MODEL = os.environ["LOCAL_MODEL"]
CASES = ["X2-005", "X2-037", "X2-145"]
MAX_STEPS_NORMAL = 8
MAX_STEPS_ABLATION_A = 20  # high ceiling instead of the normal step cap, so a real loop isn't masked by it


def _cases():
    all_cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    return [all_cases[cid] for cid in CASES]


def run_normal(case, max_steps=MAX_STEPS_NORMAL, tag="ABLATION_BASELINE"):
    """The real, guarded loop (src/agent.py, unmodified) -- the control every ablation is compared against."""
    return A.run(case, model=MODEL, max_steps=max_steps, tag=tag)


def run_no_guardrails(case, max_steps=MAX_STEPS_ABLATION_A, tag="ABLATION_A_NO_DEDUP"):
    """Copy of src/agent.py's loop with the `seen` de-dup cache removed (every call re-executes, even an
    identical repeat) and a much higher step ceiling standing in for "no step cap" (a genuinely uncapped
    loop cannot be safely run against a live model -- this bounds worst case while still removing the
    normal cap as the thing that would otherwise stop a loop early)."""
    specs, case_tools = A.default_specs_and_tools(case)
    system = A.SYSTEM.format(max_steps=max_steps, tools=A._catalogue(specs))
    visible = {k: v for k, v in case.items() if k != "split"}
    messages = [{"role": "system", "content": system}, {"role": "user", "content": f"CLAIM:\n{json.dumps(visible, indent=1, default=str)}"}]
    trace, cost, tokens_in, tokens_out, total_calls, repeated_calls = [], 0.0, 0, 0, 0, 0
    for step in range(max_steps):
        r = llm.chat(MODEL, messages, temperature=0, max_tokens=400, tag=tag, case_id=case["case_id"])
        cost += r["cost_usd"]; tokens_in += r["input_tokens"]; tokens_out += r["output_tokens"]
        try:
            d = json.loads(r["text"])
        except Exception:
            d = {"tool": "record_decision", "args": {"decision": "ESCALATE", "policy_evidence": [], "missing_fields": [], "explanation": "unparseable"}}
        name, args = d.get("tool"), d.get("args") or {}
        if name == "record_decision":
            obs = A._call(name, args, case_tools, specs)
            if obs["ok"]:
                return {**obs["data"], "trace": trace, "turns": step + 1, "cost_usd": round(cost, 6),
                        "input_tokens": tokens_in, "output_tokens": tokens_out, "total_calls": total_calls,
                        "repeated_calls": repeated_calls, "step_cap_hit": False}
            trace.append({"tool": name, "args": args, "observation": obs})
            messages += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": f"OBSERVATION: {json.dumps(obs)}"}]
            continue
        # NO seen-cache check here -- deliberately: every call executes fresh, an exact repeat is not detected
        total_calls += 1
        key = (name, tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in args.items())))
        if any(t.get("_key") == key for t in trace):
            repeated_calls += 1
        obs = A._call(name, args, case_tools, specs)
        trace.append({"tool": name, "args": args, "observation": obs, "_key": key})
        messages += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": f"OBSERVATION: {json.dumps(obs, default=str)}"}]
    return {"decision": None, "explanation": f"ceiling ({max_steps}) reached without a final answer", "trace": trace,
            "turns": max_steps, "cost_usd": round(cost, 6), "input_tokens": tokens_in, "output_tokens": tokens_out,
            "total_calls": total_calls, "repeated_calls": repeated_calls, "step_cap_hit": True}


VAGUE_DESCRIPTIONS = {
    "search_policy_corpus": "Looks something up.",
    "check_rate_ceiling": "Checks a number.",
    "get_employee_profile": "Gets some info.",
    "get_travel_request": "Gets some info.",
    "get_manager_approval": "Gets some info.",
    "get_exception_record": "Gets some info.",
    "get_project_status": "Gets some info.",
    "search_previous_expenses": "Gets some info.",
    "get_conference_registration": "Gets some info.",
    "get_merchant_metadata": "Gets some info.",
    "get_approval_delegation": "Gets some info.",
    "get_cost_centre_budget": "Gets some info.",
    "get_fx_rate": "Gets some info.",
    "validate_approval": "Checks something about an approval.",
}


def run_vague_tools(case, max_steps=MAX_STEPS_NORMAL, tag="ABLATION_B_VAGUE_TOOLS"):
    """Real loop (dedup + step cap both intact, unlike ablation A), but every tool's description degraded
    to a short, generic, overlapping sentence -- isolates tool-description quality as the one variable."""
    specs, case_tools = A.default_specs_and_tools(case)
    vague_specs = {name: (spec, VAGUE_DESCRIPTIONS.get(name, "Does something.")) for name, (spec, desc) in specs.items()}
    return A.run(case, model=MODEL, max_steps=max_steps, tag=tag, specs=vague_specs, case_tools=case_tools)


def _wrong_tool_rate(result, case):
    """Heuristic: a tool call is 'wrong' if it returned found=False/ok=False (the same signal src/agent.py
    itself uses for its own wrong_tool_calls counter), or if it queried a domain unrelated to this claim's
    expense type (best-effort, not exhaustive)."""
    trace = result.get("trace") or []
    if not trace:
        return 0, 0
    wrong = sum(1 for t in trace if not t["observation"].get("ok") or not t["observation"].get("found"))
    return wrong, len(trace)


def main():
    results = {"failure_a_no_guardrails": {}, "failure_b_vague_tools": {}, "baseline": {}}
    for case in _cases():
        cid = case["case_id"]
        print(f"--- {cid} ---")
        base = run_normal(case)
        results["baseline"][cid] = {"decision": base.get("decision"), "turns": base.get("turns"),
                                     "cost_usd": base.get("cost_usd"), "step_cap_hit": base.get("step_cap_hit")}
        print("  baseline (guarded):", results["baseline"][cid])

        a = run_no_guardrails(case)
        results["failure_a_no_guardrails"][cid] = {"decision": a.get("decision"), "turns": a["turns"],
                                                     "total_calls": a["total_calls"], "repeated_calls": a["repeated_calls"],
                                                     "cost_usd": a["cost_usd"], "step_ceiling_hit": a["step_cap_hit"]}
        print("  Failure A (no dedup, high ceiling):", results["failure_a_no_guardrails"][cid])

        b = run_vague_tools(case)
        wrong, total = _wrong_tool_rate(b, case)
        results["failure_b_vague_tools"][cid] = {"decision": b.get("decision"), "turns": b.get("turns"),
                                                   "wrong_tool_calls": wrong, "total_tool_calls": total,
                                                   "cost_usd": b.get("cost_usd"), "step_cap_hit": b.get("step_cap_hit")}
        print("  Failure B (vague tool descriptions):", results["failure_b_vague_tools"][cid])

    out = ROOT / "results/v2/development/exp_agent_failure_ablation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2))
    print(f"\nwrote {out / 'results.json'}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
