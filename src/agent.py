"""V3: a reusable bounded ReAct agent, generalising Exp 20's inline notebook loop so it can be run
against any case set from outside a notebook (Exp 20 pinned RAG results to the prompt before the loop
started; this version gives the agent search_policy_corpus as a callable tool instead, per the V3
pivot -- RAG becomes something the agent decides to invoke and re-invoke, not a fixed pre-fetch).

Design, unchanged from Exp 20 where it already worked:
  - the model sees the claim and the tool catalogue, nothing pre-resolved;
  - one tool call or one record_decision call per turn; observations are fed back;
  - guardrails: step cap, call de-duplication (repeated identical calls served from cache, not counted
    against the cap), read-only tools only, step-cap-reached falls back to ESCALATE rather than guessing.

record_decision is the loop's one terminal action (Change 3 of the V3 pivot: the final answer is itself
a tool call with a validated schema, not a bare JSON blob the loop has to special-case).
"""
from __future__ import annotations
import json, os
from . import llm, tools as T, agent_tools as AT

DECISIONS = ("APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE")


_SYNONYM = {"APPROVED": "APPROVE", "REJECTED": "REJECT", "DENIED": "REJECT", "ESCALATED": "ESCALATE", "REQUEST_INFO": "REQUEST_INFORMATION", "NEED_INFO": "REQUEST_INFORMATION"}


def record_decision(decision: str, policy_evidence: list, missing_fields: list, explanation: str) -> dict:
    decision = _SYNONYM.get(str(decision).upper(), decision)  # tolerate a spelling variant rather than burning a turn on it
    if decision not in DECISIONS:
        return {"ok": False, "found": False, "data": None, "error": f"decision must be one of {DECISIONS}"}
    return {"ok": True, "found": True, "data": {"decision": decision, "policy_evidence": policy_evidence, "missing_fields": missing_fields, "explanation": explanation}, "error": None}


RECORD_SPEC = ({"decision": ("enum", DECISIONS), "policy_evidence": ("list_str_ok_empty", None), "missing_fields": ("list_str_ok_empty", None), "explanation": ("str", None)},
               "Your final answer. Call this, and only this, once you have enough evidence -- do not call further lookup tools afterward.")

SYSTEM = """You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement.
You have no policy text or enterprise records up front: decide what to look up. This claim cannot be decided on enterprise
records alone -- you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility
condition) that actually applies, and use check_rate_ceiling rather than doing that arithmetic yourself. Use the enterprise
tools only for the specific records the claim or an earlier observation points you to (approvals, delegations, travel
requests, exceptions, etc.) -- do not explore records that have no bearing on this claim's expense type. If an excerpt or
record you retrieve names a further clause or identifier (an exception id, a delegation id, a second policy clause), look
that up too before deciding -- do not guess a rule from memory when you could retrieve it.
Guardrails: at most {max_steps} steps. Do not repeat an identical tool call. All tools are read-only. Stop and call
record_decision as soon as you have enough evidence to answer -- do not keep calling tools you do not need. record_decision
is your only way to answer; call it exactly once.
At each turn, return ONLY one JSON object: {{"tool": "<name>", "args": {{...}}}}.
Available tools:
{tools}"""


def _catalogue(specs: dict) -> str:
    return "\n".join(f"- {name}({', '.join(spec)}): {desc}" for name, (spec, desc) in specs.items())


def _check_arg(kind, key, v):
    if kind in ("list_str_ok_empty",):
        return None if isinstance(v, list) and all(isinstance(x, str) for x in v) else f"{key or 'value'} must be a list of strings"
    return T._check(kind, key, v)


def _call(name, args, case_tools, specs):
    if name not in specs:
        return {"ok": False, "found": False, "data": None, "error": f"unknown tool: {name}"}
    spec, _ = specs[name]
    if not isinstance(args, dict):
        return {"ok": False, "found": False, "data": None, "error": "arguments must be an object"}
    req = list(spec)
    missing = [a for a in req if a not in args and not spec[a][0].endswith("?")]
    extra = [a for a in args if a not in spec]
    if missing or extra:
        return {"ok": False, "found": False, "data": None, "error": f"missing {missing} unexpected {extra}"}
    if name == "record_decision" and "decision" in args:
        args["decision"] = _SYNONYM.get(str(args["decision"]).upper(), args["decision"])  # tolerate a spelling variant before validation
    for k, v in list(args.items()):
        kind, key = spec[k]
        if kind == "list_str_ok_empty" and isinstance(v, str):
            args[k] = v = [x.strip() for x in v.split(",") if x.strip()]  # tolerate a comma-joined string instead of a list
        err = _check_arg(kind, key if kind == "enum" else (key or k), v)
        if err:
            return {"ok": False, "found": False, "data": None, "error": err}
    try:
        return case_tools[name](**args)
    except Exception as e:  # noqa
        return {"ok": False, "found": False, "data": None, "error": f"tool error: {type(e).__name__}"}


def default_specs_and_tools(case: dict) -> tuple:
    specs = {"search_policy_corpus": AT.AGENT_TOOL_SPECS["search_policy_corpus"], "check_rate_ceiling": AT.AGENT_TOOL_SPECS["check_rate_ceiling"],
             **{n: (s, d) for n, (fn, s, d) in T.TOOLS.items()}, "record_decision": RECORD_SPEC}
    case_tools = {"search_policy_corpus": AT.make_search_policy_corpus(case), "check_rate_ceiling": AT.check_rate_ceiling, "record_decision": record_decision,
                  **{n: fn for n, (fn, s, d) in T.TOOLS.items()}}
    return specs, case_tools


def run(case: dict, model: str | None = None, max_steps: int = 8, tag: str = "AGENT_V3", system_template: str | None = None,
        specs: dict | None = None, case_tools: dict | None = None) -> dict:
    """Runs the bounded ReAct+agentic-RAG loop on one visible case (dict with 'split' stripped by the
    caller if desired). Returns decision + full trace, cost and guardrail counters.
    system_template/specs/case_tools let a variant (Exp 35A prompt fix, 35C tool-interface fix) swap in
    a different system prompt or tool set while reusing this exact loop, so only one variable changes
    at a time relative to the Exp 34 baseline."""
    model = model or os.environ["PAID_MODEL"]
    if specs is None or case_tools is None:
        d_specs, d_tools = default_specs_and_tools(case)
        specs = specs or d_specs
        case_tools = case_tools or d_tools
    system = (system_template or SYSTEM).format(max_steps=max_steps, tools=_catalogue(specs))
    visible = {k: v for k, v in case.items() if k != "split"}
    messages = [{"role": "system", "content": system}, {"role": "user", "content": f"CLAIM:\n{json.dumps(visible, indent=1, default=str)}"}]
    seen, trace, cost, wrong_tool, tokens_in, tokens_out = {}, [], 0.0, 0, 0, 0
    for step in range(max_steps):
        r = llm.chat(model, messages, temperature=0, max_tokens=400, tag=tag, case_id=case["case_id"])
        cost += r["cost_usd"]; tokens_in += r["input_tokens"]; tokens_out += r["output_tokens"]
        try:
            d = json.loads(r["text"])
        except Exception:
            d = {"tool": "record_decision", "args": {"decision": "ESCALATE", "policy_evidence": [], "missing_fields": [], "explanation": "Could not parse a structured response."}}
        name, args = d.get("tool"), d.get("args") or {}
        if name == "record_decision":
            obs = _call(name, args, case_tools, specs)
            if obs["ok"]:
                return {**obs["data"], "trace": trace, "turns": step + 1, "cost_usd": round(cost, 6), "input_tokens": tokens_in, "output_tokens": tokens_out,
                        "wrong_tool_calls": wrong_tool, "step_cap_hit": False}
            # malformed final answer: tell it why and let it retry within the step budget
            trace.append({"tool": name, "args": args, "observation": obs})
            messages += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": f"OBSERVATION: {json.dumps(obs)}"}]
            continue
        key = (name, tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in args.items())))
        if key in seen:
            obs = seen[key]
        else:
            obs = _call(name, args, case_tools, specs)
            seen[key] = obs
            if not obs.get("ok") or not obs.get("found"):
                wrong_tool += 1
        trace.append({"tool": name, "args": args, "observation": obs})
        messages += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": f"OBSERVATION: {json.dumps(obs, default=str)}"}]
    return {"decision": "ESCALATE", "policy_evidence": [], "missing_fields": [], "explanation": f"Step cap ({max_steps}) reached; escalated instead of guessing.",
            "trace": trace, "turns": max_steps, "cost_usd": round(cost, 6), "input_tokens": tokens_in, "output_tokens": tokens_out, "wrong_tool_calls": wrong_tool, "step_cap_hit": True}


def run_batch(cases: list, model: str | None = None, max_steps: int = 8) -> dict:
    return {c["case_id"]: run(c, model, max_steps) for c in cases}
