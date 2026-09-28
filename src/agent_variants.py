"""Exp 35: three single-variable variants on the Exp 34 agent baseline (src/agent.py), isolating
prompt vs. model vs. tool-interface as the fix for the Chennai/Kobe tier-substitution failure (Exp 33,
34: the model ignores a stated closed-world fallback rule and substitutes a more familiar tier).

35A -- prompt layer: same model, same tools, a stricter system prompt (explicit closed-world check +
       a tighter stopping rule against Exp 34's 7.3/8 average-turns finding).
35B -- model layer: Exp 34's exact prompt and tools, only the model changes (src/agent.run's own
       `model` argument already covers this; no new code needed here).
35C -- tool-interface (ACI / poka-yoke) layer: Exp 34's exact prompt, gpt-4o-mini, but
       check_rate_ceiling is replaced by lookup_hotel_ceiling(city, country, year, grade_band), which
       parses the SAME public D04 policy document server-side (regex over the same markdown tables a
       human or the model would read) and returns the resolved ceiling plus whether the city was
       literally listed -- so a hallucinated tier can no longer be silently passed into the calculator.
       This is a reading-comprehension aid over the public corpus text, not private ground truth: the
       tier tables and the "lowest tier for its country" sentence are the same text search_policy_corpus
       already retrieves, only parsed structurally instead of left for the model to read from prose.
"""
from __future__ import annotations
import re
from pathlib import Path
from . import agent as A, agent_tools as AT, tools as T, rules_text as RT, rules_v2 as RV

DOC = Path(__file__).resolve().parents[1] / "ExpenseGuard_V2_DATASET" / "01_policy_corpus" / "source_documents" / "D04_TRV.md"

# ---------------------------------------------------------------- 35A: prompt layer
SYSTEM_35A = """You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement.
You have no policy text or enterprise records up front: decide what to look up. This claim cannot be decided on enterprise
records alone -- you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility
condition) that actually applies, and use check_rate_ceiling rather than doing that arithmetic yourself. Use the enterprise
tools only for the specific records the claim or an earlier observation points you to -- do not explore records that have
no bearing on this claim's expense type.

CLOSED-WORLD TABLE CHECK: whenever a retrieved excerpt gives you a lookup table (for example a city-to-tier table), you must
verify membership explicitly before using a row from it. List, to yourself, every city literally printed in that table. If
the claim's own city is not one of the cities you just listed, you may NOT use any tier from that table directly -- the
claim's city is unlisted. Find and apply the table's own stated fallback rule for an unlisted entry (for example "a city
not listed takes the lowest tier for its country") instead of picking the tier of a similar-sounding or nearby listed city.

If an excerpt or record you retrieve names a further clause or identifier (an exception id, a delegation id, a second
policy clause), look that up too before deciding -- do not guess a rule from memory when you could retrieve it.
Guardrails: at most {max_steps} steps, but stop well before that -- most claims need 3-5 tool calls, not {max_steps}. Do not
repeat an identical tool call, and do not re-query a fact you already have. All tools are read-only. The moment your last
observation gives you everything needed for a decision, call record_decision on your very next turn -- do not verify a
conclusion you already reached with an extra lookup. record_decision is your only way to answer; call it exactly once.
At each turn, return ONLY one JSON object: {{"tool": "<name>", "args": {{...}}}}.
Available tools:
{tools}"""


# ---------------------------------------------------------------- 35C: tool-interface (ACI) layer
def _parse_location_tiers() -> dict:
    """Parses TRV-2.2's own city-to-tier table straight out of the public document text."""
    text = DOC.read_text()
    sec = re.search(r"## TRV-2\.2.*?\n(.*?)\n##", text, re.S).group(1)
    return {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r"\|\s*([A-Za-z][\w .]*?)\s*\|\s*([A-Z]{2}-[A-Z0-9]+)\s*\|", sec)}


def _parse_ceiling_table(clause_id: str) -> dict:
    """Parses one year's TRV-3.x nightly-ceiling table (tier -> {band: ceiling}) from the same document."""
    text = DOC.read_text()
    m = re.search(rf"## {re.escape(clause_id)}.*?\n(.*?)\n##", text, re.S)
    sec = m.group(1)
    header = re.search(r"\|\s*Location tier\s*\|\s*Currency\s*\|(.+?)\|\s*\n", sec)
    bands = [b.strip() for b in header.group(1).split("|") if b.strip()]
    out = {}
    for row in re.finditer(r"\|\s*([A-Z]{2}-[A-Z0-9]+)\s*\|\s*([A-Z]{3})\s*\|(.+?)\|\s*\n", sec):
        tier, vals = row.group(1), [float(v.strip().replace(",", "")) for v in row.group(3).split("|") if v.strip()]
        out[tier] = dict(zip(bands, vals))
    return out


_CLAUSE_BY_YEAR = {2024: "TRV-3.1", 2025: "TRV-3.2", 2026: "TRV-3.3"}
_BAND_BY_GRADE = lambda g: "G1-G3" if g <= 3 else "G4-G5" if g <= 5 else "G6-G7" if g <= 7 else "G8+"


def lookup_hotel_ceiling(city: str, country: str, year: int, grade) -> dict:
    """Structural replacement for letting the model pass an arbitrary `ceiling` float it read off a
    table itself. Parses TRV-2.2 (city->tier) and TRV-3.x (tier->ceiling by band) directly from the
    public policy document, resolves the tier (direct match, or the lowest-ceiling tier for the
    country if the city is unlisted -- both facts already present in the same public text), and
    returns the ceiling plus whether a fallback was used. A hallucinated tier can no longer reach the
    calculator: the tool computes the tier, the model only supplies city/country/year/grade."""
    if int(year) not in _CLAUSE_BY_YEAR:
        return {"ok": False, "found": False, "data": None, "error": "year must be 2024, 2025 or 2026"}
    tiers = _parse_location_tiers()
    ceilings = _parse_ceiling_table(_CLAUSE_BY_YEAR[int(year)])
    grade_str = str(grade).strip().upper()
    band = _BAND_BY_GRADE(int(grade_str[1:] if grade_str.startswith("G") else grade_str))
    listed = tiers.get(city)
    fallback_used = listed is None
    if listed:
        tier = listed
    else:
        country_prefix = {"India": "IN", "Japan": "JP", "Singapore": "SG"}.get(country, country[:2].upper())
        candidates = [(t, vals[band]) for t, vals in ceilings.items() if t.startswith(country_prefix)]
        if not candidates:
            return {"ok": False, "found": False, "data": None, "error": f"no tier found for country {country!r}"}
        tier = min(candidates, key=lambda tv: tv[1])[0]
    return {"ok": True, "found": True, "data": {"tier": tier, "ceiling": ceilings[tier][band], "city_listed_in_table": not fallback_used,
                                                 "fallback_rule_applied": fallback_used, "band": band}, "error": None}


SYSTEM_35C = A.SYSTEM.replace(
    "you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility\ncondition) that actually applies, and use check_rate_ceiling rather than doing that arithmetic yourself.",
    "you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility\ncondition) that actually applies. For a hotel claim, use lookup_hotel_ceiling (not a number you read off a retrieved table yourself) to get the correct ceiling.")

AGENT_TOOL_SPECS_35C = {
    "lookup_hotel_ceiling": ({"city": ("str", None), "country": ("str", None), "year": ("amount", None), "grade": ("str", None)},
                             "The nightly hotel ceiling for a city, resolved from the Travel and Accommodation Policy's own tier and "
                             "ceiling tables (including the stated fallback for a city not listed in the tier table). Use this instead "
                             "of reading a ceiling number off a retrieved table yourself for a hotel claim. grade is the employee grade "
                             "exactly as returned by get_employee_profile, e.g. 'G4'."),
}


def specs_and_tools_35c(case: dict) -> tuple:
    """v1: offers lookup_hotel_ceiling alongside the old check_rate_ceiling. Session finding: the model
    called lookup_hotel_ceiling on only 3/13 cases and zero of the Chennai/Kobe cases it was built for,
    defaulting to the familiar check_rate_ceiling instead -- a tool-confusion confound, not a test of
    whether the interface fix itself works. Kept for the record; see specs_and_tools_35c_v2 below."""
    specs = {"search_policy_corpus": AT.AGENT_TOOL_SPECS["search_policy_corpus"], "lookup_hotel_ceiling": AGENT_TOOL_SPECS_35C["lookup_hotel_ceiling"],
             "check_rate_ceiling": AT.AGENT_TOOL_SPECS["check_rate_ceiling"], **{n: (s, d) for n, (fn, s, d) in T.TOOLS.items()}, "record_decision": A.RECORD_SPEC}
    case_tools = {"search_policy_corpus": AT.make_search_policy_corpus(case), "lookup_hotel_ceiling": lookup_hotel_ceiling, "check_rate_ceiling": AT.check_rate_ceiling,
                  "record_decision": A.record_decision, **{n: fn for n, (fn, s, d) in T.TOOLS.items()}}
    return specs, case_tools


def specs_and_tools_35c_v2(case: dict) -> tuple:
    """v2: removes check_rate_ceiling entirely for hotel claims so lookup_hotel_ceiling is the only path
    to a ceiling number -- no competing tool for the model to default to instead. This is the real,
    unconfounded test of whether the ACI/poka-yoke fix works when it is actually used."""
    specs = {"search_policy_corpus": AT.AGENT_TOOL_SPECS["search_policy_corpus"], "lookup_hotel_ceiling": AGENT_TOOL_SPECS_35C["lookup_hotel_ceiling"],
             **{n: (s, d) for n, (fn, s, d) in T.TOOLS.items()}, "record_decision": A.RECORD_SPEC}
    case_tools = {"search_policy_corpus": AT.make_search_policy_corpus(case), "lookup_hotel_ceiling": lookup_hotel_ceiling,
                  "record_decision": A.record_decision, **{n: fn for n, (fn, s, d) in T.TOOLS.items()}}
    return specs, case_tools


# ================================================================== Exp 36: parallel loop + poka-yoke v2
# 35C's lookup_hotel_ceiling still took city/country as model-supplied arguments -- so a model confused
# by a note's distractor city (X2-005's note says "Bengaluru", the bill says "Chennai") could in
# principle still pass the wrong one in. check_hotel_ceiling below removes that argument entirely: city
# and country are closed over from the claim's own authoritative bill object at tool-construction time,
# never supplied by the model, so passing the wrong city is no longer a class of error the model *can*
# make through this tool. Only `grade` remains a model-supplied argument (it must still have called
# get_employee_profile and read the result correctly).

def make_check_hotel_ceiling(case: dict):
    """Closure bound to this claim's own bill.city/bill.country/transaction_date -- the poka-yoke: there
    is no city/country argument for the model to get wrong. Returns the resolved tier, ceiling and the
    controlling clause ids (TRV-2.2, the year's TRV-3.x, TRV-6.1) in one call."""
    city, country, year = case["bill"]["city"], case["bill"]["country"], int(case["transaction_date"][:4])

    def check_hotel_ceiling(grade) -> dict:
        r = lookup_hotel_ceiling(city, country, year, grade)
        if not r["ok"]:
            return r
        clause = _CLAUSE_BY_YEAR[year]
        return {**r, "data": {**r["data"], "policy_evidence": ["TRV-2.2", clause, "TRV-6.1"]}}

    return check_hotel_ceiling


AGENT_TOOL_SPECS_36 = {
    "check_hotel_ceiling": ({"grade": ("str", None)},
                            "The nightly hotel ceiling that applies to THIS claim's own city and country (resolved from the Travel "
                            "and Accommodation Policy's tier and ceiling tables, including the stated fallback for an unlisted city) -- "
                            "use this for any hotel claim instead of reading a ceiling off a retrieved table yourself. grade is the "
                            "employee grade exactly as returned by get_employee_profile, e.g. 'G4'. Returns tier, ceiling and the "
                            "controlling policy_evidence clause ids."),
}


def specs_and_tools_36(case: dict) -> tuple:
    specs = {"search_policy_corpus": AT.AGENT_TOOL_SPECS["search_policy_corpus"], "check_hotel_ceiling": AGENT_TOOL_SPECS_36["check_hotel_ceiling"],
             **{n: (s, d) for n, (fn, s, d) in T.TOOLS.items()}, "record_decision": A.RECORD_SPEC}
    case_tools = {"search_policy_corpus": AT.make_search_policy_corpus(case), "check_hotel_ceiling": make_check_hotel_ceiling(case),
                  "record_decision": A.record_decision, **{n: fn for n, (fn, s, d) in T.TOOLS.items()}}
    return specs, case_tools


SYSTEM_36 = """You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement.
You have no policy text or enterprise records up front: decide what to look up. This claim cannot be decided on enterprise
records alone -- you must call search_policy_corpus at least once to find the rule that actually applies. For a hotel claim,
call check_hotel_ceiling to get the correct ceiling (it already knows this claim's own city and country; never estimate a
ceiling yourself). Use the enterprise tools only for the specific records the claim or an earlier observation points you to.
If an excerpt or record you retrieve names a further clause or identifier (an exception id, a delegation id, a second policy
clause), look that up too before deciding -- do not guess a rule from memory when you could retrieve it.

PARALLEL TURNS: at each turn you may issue MULTIPLE independent tool calls at once, as a list, whenever they do not depend
on each other's results -- for example employee profile, travel request and a policy search can all be issued together in
turn 1. Only split calls across turns when a later call genuinely needs a fact an earlier call in the same turn would
produce (for example, an exception id discovered from a travel request must be looked up in a later turn). Batching
independent calls saves you turns against the step cap below.
Guardrails: at most {max_steps} turns (each turn may contain several calls). Do not repeat an identical tool call across
turns. All tools are read-only. Stop and call record_decision as soon as you have enough evidence -- do not keep
calling tools you do not need. record_decision is your only way to answer; call it exactly once, alone (not batched with
other calls).
At each turn, return ONLY one JSON object: {{"calls": [{{"tool": "<name>", "args": {{...}}}}, ...]}} -- a list of one or more calls.
Available tools:
{tools}"""


# ================================================================== Exp 37: policy oracle for the agent
# Isolates whether perfect policy retrieval alone fixes the agent (mirrors Exp 11's policy oracle, but
# for the agent architecture instead of the single-shot resolver). search_policy_corpus is replaced by
# a tool that hands back the exact required+supporting clauses from the PRIVATE ground truth -- an
# evaluator-only diagnostic, never a runtime component (same rule Exp 11/16 followed: this could not
# exist in production, since it requires already knowing the answer's controlling clauses).

def make_oracle_policy_tool(gt_record: dict):
    from . import policy
    ids = gt_record["required_policy_ids"] + gt_record["supporting_policy_ids"]
    text = policy.render(ids)

    def get_correct_policy_excerpts() -> dict:
        return {"ok": True, "found": True, "data": {"excerpts": text, "n_clauses": len(ids)}, "error": None}

    return get_correct_policy_excerpts


AGENT_TOOL_SPECS_ORACLE = {
    "get_correct_policy_excerpts": ({}, "Returns the exact policy excerpts that control this claim. Read them carefully and apply "
                                         "them yourself -- this tool does not compute a decision or a ceiling for you."),
}


def specs_and_tools_oracle(case: dict, gt_record: dict) -> tuple:
    specs = {"get_correct_policy_excerpts": AGENT_TOOL_SPECS_ORACLE["get_correct_policy_excerpts"], "check_rate_ceiling": AT.AGENT_TOOL_SPECS["check_rate_ceiling"],
             **{n: (s, d) for n, (fn, s, d) in T.TOOLS.items()}, "record_decision": A.RECORD_SPEC}
    case_tools = {"get_correct_policy_excerpts": make_oracle_policy_tool(gt_record), "check_rate_ceiling": AT.check_rate_ceiling,
                  "record_decision": A.record_decision, **{n: fn for n, (fn, s, d) in T.TOOLS.items()}}
    return specs, case_tools


SYSTEM_ORACLE = A.SYSTEM.replace(
    "you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility\ncondition) that actually applies, and use check_rate_ceiling rather than doing that arithmetic yourself.",
    "call get_correct_policy_excerpts once to get the exact rule (a ceiling, a threshold, an eligibility condition) that\napplies to this claim -- it is guaranteed complete and correct, read it carefully -- and use check_rate_ceiling rather than doing that arithmetic yourself.")


# ================================================================== Exp 39: true two-hop agentic RAG
# Exp 38's audit found the doc_category mask was never actually the blocker (approval/exceptions/
# circular already pass as crosscut categories regardless of doc_category) -- the real cause is that
# governance content simply never ranks in the top-K for a surface-topic query like "meal reimbursement
# policy", verified directly: even with the mask fully open, APR-1.1 does not appear in the top 8 for
# that query. So the fix here is NOT "remove the category lock" (already a no-op); it is to guarantee
# governance content surfaces regardless of how the agent phrases its query, by running a second,
# fixed-query retrieval pass restricted to the governance categories and merging it into every call's
# results -- a poka-yoke for retrieval itself, not a prompt request to "please re-query."
GOV_CATEGORIES = {"approval", "exceptions", "circular"}
GOV_QUERY = "manager approval delegation authority validity exception policy"


def make_search_policy_corpus_v2(case: dict):
    """Wraps AT.make_search_policy_corpus with a guaranteed second pass over governance-only chunks,
    merged into the same observation -- the agent never has to think to ask for it separately."""
    base = AT.make_search_policy_corpus(case)
    R = AT._R()

    def search_policy_corpus(query: str, doc_category: str = None, region: str = None) -> dict:
        primary = base(query, doc_category, region)
        import numpy as np
        from . import embed
        qv = embed.embed(AT.EMB, [GOV_QUERY], tag="AGENT_SEARCH_GOV")[0]
        mask = np.array([c["category"] in GOV_CATEGORIES for c in R.chunks])
        gov_ranked = R.rank("dense", "unused", qv, 3, mask)
        gov_ctx = R.context(gov_ranked)
        merged = primary["data"]["excerpts"] + "\n\n[governance context, always included]\n" + gov_ctx
        return {"ok": True, "found": True, "data": {"excerpts": merged, "n_chunks": primary["data"]["n_chunks"] + len(gov_ranked)}, "error": None}

    return search_policy_corpus


def _wrap_hint(fn, hint_if):
    """Wraps a read-only enterprise tool so its observation gets one extra field, unverified_policy_domain,
    when the wrapped predicate says this observation reveals something that needs a governance-policy
    lookup before deciding -- a nudge at the tool-observation layer instead of prompt-only instruction."""
    def wrapped(**kwargs):
        r = fn(**kwargs)
        if r.get("ok") and r.get("found") and hint_if(r["data"]):
            r = {**r, "data": {**r["data"], "unverified_policy_domain": "Must call search_policy_corpus for APPROVAL / DELEGATION / CIRCULAR rules before deciding."}}
        return r
    return wrapped


def specs_and_tools_39(case: dict) -> tuple:
    """Fix 1 (cross-domain RAG guarantee) + Fix 2 (Exp 36's poka-yoke retained)."""
    hinted_validate = _wrap_hint(T.validate_approval, lambda d: d.get("delegation_used") or not d.get("valid", True))
    hinted_travel = _wrap_hint(T.get_travel_request, lambda d: bool(d.get("exception_id")))
    hinted_exception = _wrap_hint(T.get_exception_record, lambda d: False)  # found records need no extra hint; missing ones return found=False (no hint path) by design
    specs = {"search_policy_corpus": AT.AGENT_TOOL_SPECS["search_policy_corpus"], "check_hotel_ceiling": AGENT_TOOL_SPECS_36["check_hotel_ceiling"],
             **{n: (s, d) for n, (fn, s, d) in T.TOOLS.items()}, "record_decision": A.RECORD_SPEC}
    case_tools = {"search_policy_corpus": make_search_policy_corpus_v2(case), "check_hotel_ceiling": make_check_hotel_ceiling(case),
                  "validate_approval": hinted_validate, "get_travel_request": hinted_travel, "get_exception_record": hinted_exception,
                  "record_decision": A.record_decision, **{n: fn for n, (fn, s, d) in T.TOOLS.items() if n not in ("validate_approval", "get_travel_request", "get_exception_record")}}
    return specs, case_tools


SYSTEM_39 = A.SYSTEM.replace(
    "you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility\ncondition) that actually applies, and use check_rate_ceiling rather than doing that arithmetic yourself.",
    "you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility\ncondition) that actually applies. For a hotel claim, use check_hotel_ceiling (not a number you read off a table yourself). "
    "If any observation includes 'unverified_policy_domain', you must call search_policy_corpus again before deciding -- the first search did not cover what that observation raised.")


def run_parallel(case: dict, model: str | None = None, max_steps: int = 8, tag: str = "AGENT_V2_PARALLEL",
                  system_template: str | None = None, specs: dict | None = None, case_tools: dict | None = None) -> dict:
    """Exp 36's loop: one LLM call per turn may return several tool calls, all executed (and logged)
    within that same turn, so the step cap bounds LLM round-trips rather than individual tool calls.
    Everything else (dedup via `seen`, read-only tools, step-cap-hit escalates) matches src/agent.run."""
    import json, os
    from . import llm
    model = model or os.environ["PAID_MODEL"]
    if specs is None or case_tools is None:
        d_specs, d_tools = A.default_specs_and_tools(case)
        specs = specs or d_specs
        case_tools = case_tools or d_tools
    system = (system_template or SYSTEM_36).format(max_steps=max_steps, tools=A._catalogue(specs))
    visible = {k: v for k, v in case.items() if k != "split"}
    messages = [{"role": "system", "content": system}, {"role": "user", "content": f"CLAIM:\n{json.dumps(visible, indent=1, default=str)}"}]
    seen, trace, cost, wrong_tool, tokens_in, tokens_out = {}, [], 0.0, 0, 0, 0
    for step in range(max_steps):
        r = llm.chat(model, messages, temperature=0, max_tokens=700, tag=tag, case_id=case["case_id"])
        cost += r["cost_usd"]; tokens_in += r["input_tokens"]; tokens_out += r["output_tokens"]
        try:
            d = json.loads(r["text"])
        except Exception:
            d = {"calls": [{"tool": "record_decision", "args": {"decision": "ESCALATE", "policy_evidence": [], "missing_fields": [], "explanation": "Could not parse a structured response."}}]}
        calls = d.get("calls")
        if not isinstance(calls, list):
            calls = [d] if d.get("tool") else []
        obs_lines, final = [], None
        for call in calls:
            name, args = call.get("tool"), call.get("args") or {}
            if name == "record_decision":
                obs = A._call(name, args, case_tools, specs)
                if obs["ok"]:
                    final = obs["data"]; break
                trace.append({"tool": name, "args": args, "observation": obs}); obs_lines.append(f"record_decision REJECTED: {json.dumps(obs)}")
                continue
            key = (name, tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in args.items())))
            if key in seen:
                obs = seen[key]
            else:
                obs = A._call(name, args, case_tools, specs)
                seen[key] = obs
                if not obs.get("ok") or not obs.get("found"):
                    wrong_tool += 1
            trace.append({"tool": name, "args": args, "observation": obs})
            obs_lines.append(f"{name}({json.dumps(args)}) -> {json.dumps(obs, default=str)}")
        if final:
            return {**final, "trace": trace, "turns": step + 1, "cost_usd": round(cost, 6), "input_tokens": tokens_in, "output_tokens": tokens_out,
                    "wrong_tool_calls": wrong_tool, "step_cap_hit": False}
        messages += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": "OBSERVATIONS:\n" + "\n".join(obs_lines)}]
    return {"decision": "ESCALATE", "policy_evidence": [], "missing_fields": [], "explanation": f"Step cap ({max_steps} turns) reached; escalated instead of guessing.",
            "trace": trace, "turns": max_steps, "cost_usd": round(cost, 6), "input_tokens": tokens_in, "output_tokens": tokens_out, "wrong_tool_calls": wrong_tool, "step_cap_hit": True}


# ================================================================== Exp 40: move the decision into code
# Three of this session's recurring failures were all "the model has to compose several correct facts
# into one of four decisions": hallucinated validate_approval arguments (required_type='hotel'/'meal'
# instead of the real enum), REJECT-vs-REQUEST_INFORMATION confusion on a missing/invalid exception
# (EXC-2.1's own mapping is fixed, not a judgement call), and false approvals reached despite an
# earlier tool call already saying something was invalid. All three follow the same pattern as the
# tier-substitution fix that worked (Exp 35C/36): take the decision away from the model instead of
# asking it to be careful.

def make_check_approval(case: dict):
    """Argument-free (bound to the claim): derives required_level/required_types itself via
    rules_v2.need_level/TYPES (the same policy mechanics validate_approval's own docstring already
    permits reusing), calls the typed validate_approval tool with the CORRECT arguments -- the model
    can no longer pass 'hotel'/'meal'/'G4' where an enum was needed -- and maps the reason_code to a
    policy_disposition using workflow_v2's own tested mapping, so the model does not have to re-derive
    'WRONG_APPROVAL_TYPE means ESCALATE' itself."""
    f = RT.parse(case)
    c2 = dict(case, form=f)
    et = f.get("expense_type")

    def check_approval() -> dict:
        amount_sgd = RV.sgd(c2)
        lvl = RV.need_level(c2, amount_sgd)
        if lvl == 9:
            return {"ok": True, "found": True, "data": {"valid": False, "reason_code": "FINANCE_THRESHOLD", "policy_disposition": "ESCALATE",
                                                          "policy_evidence": ["APR-1.3"], "reason": "Above SGD 5000 requires Finance review."}, "error": None}
        if lvl == 0:
            return {"ok": True, "found": True, "data": {"valid": True, "reason_code": "NOT_REQUIRED", "policy_disposition": None, "policy_evidence": [],
                                                          "reason": "No approval is required for this amount."}, "error": None}
        required_level = {1: "MANAGER", 2: "DIRECTOR"}[lvl]
        types = list(RV.TYPES.get(et, ("GENERAL",)))
        r = T.validate_approval(expense_id=case["case_id"], required_level=required_level, required_types=types, transaction_date=case["transaction_date"], amount_sgd=amount_sgd)
        if not r["ok"]:
            return r
        d = r["data"]
        if d["valid"]:
            disposition, clause = None, []
        elif d["reason_code"] == "NO_APPROVAL_ON_FILE":
            disposition, clause = "REQUEST_INFORMATION", ["APR-3.1"]
        elif d["reason_code"] in ("WRONG_APPROVAL_TYPE", "DELEGATION_LIMIT_OR_LEVEL", "CONFLICTING_RECORDS"):
            disposition, clause = "ESCALATE", ["APR-2.2"]
        else:
            disposition, clause = "REQUEST_INFORMATION", ["APR-2.1"]
        return {"ok": True, "found": True, "data": {**d, "policy_disposition": disposition, "policy_evidence": clause}, "error": None}

    return check_approval


def make_check_hotel_compliance(case: dict):
    """Extends check_hotel_ceiling (Exp 36's poka-yoke) to the full hotel sub-decision: ceiling AND
    exception status, using rules_v2.exception_for's exact, tested EXC-2.1 mapping -- so the model no
    longer has to decide for itself whether a missing exception id means REJECT or REQUEST_INFORMATION
    (Exp 33/36/37 all found it gets this wrong). Still argument-minimal: only `grade` is model-supplied."""
    ceiling_tool = make_check_hotel_ceiling(case)
    f = RT.parse(case)

    def check_hotel_compliance(grade, nights=None) -> dict:
        if f.get("expense_type") != "HOTEL":
            # domain guard: Exp 41 found the model calling this tool on a non-hotel (meal) claim and
            # treating its output as if it applied -- refuse outright rather than let a manufactured
            # "ceiling" feed a wrong decision.
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a HOTEL expense; check_hotel_compliance does not apply here"}
        r = ceiling_tool(grade)
        if not r["ok"]:
            return r
        d = r["data"]
        # nights is rarely regex-extractable from a hardened free-text note (that's the point of the
        # hardening); RT.parse's own value is used only when the model doesn't supply one, and a missing
        # value here is reported rather than silently defaulted, since defaulting to 1 previously gave a
        # wrong rate that happened to still land on the right disposition by luck, not correctness.
        nights = nights or f.get("nights")
        if not nights:
            return {"ok": False, "found": False, "data": None, "error": "nights not stated in the retrieved fact set or the claim; read the employee note for the number of nights and pass it explicitly"}
        rate = round(case["bill"]["total"] / int(nights), 2)
        compliant = rate <= d["ceiling"] + 1e-9
        base = {**d, "nightly_rate": rate}
        if compliant:
            return {"ok": True, "found": True, "data": {**base, "compliant": True, "policy_disposition": None, "reason": "Within the applicable ceiling."}, "error": None}
        tr = RV.travel_request(case) or {}
        exc_id = f.get("exception_ref") or tr.get("exception_id")
        st = RV.exception_for(case, "TRV-6.1", exc_id)
        if st == "VALID":
            return {"ok": True, "found": True, "data": {**base, "compliant": True, "policy_disposition": None, "reason": "A valid exception covers the overage."}, "error": None}
        if st == "WRONG_SCOPE":
            return {"ok": True, "found": True, "data": {**base, "compliant": False, "policy_disposition": "ESCALATE", "policy_evidence": ["EXC-2.1"],
                                                          "reason": "Exception names a different policy or employee -- Finance must review."}, "error": None}
        if st == "MISSING_ID":
            return {"ok": True, "found": True, "data": {**base, "compliant": False, "policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["EXC-2.1"],
                                                          "reason": "Cited exception identifier does not exist; request the correct reference."}, "error": None}
        if st == "NONE":
            return {"ok": True, "found": True, "data": {**base, "compliant": False, "policy_disposition": "REJECT", "policy_evidence": ["TRV-6.1"],
                                                          "reason": f"Nightly rate {rate:.0f} exceeds ceiling {d['ceiling']:.0f}; no exception cited."}, "error": None}
        return {"ok": True, "found": True, "data": {**base, "compliant": False, "policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["EXC-2.1"],
                                                      "reason": "Cited exception is not approved or is outside its validity window."}, "error": None}

    return check_hotel_compliance


def make_check_project_budget(case: dict):
    """Closes the DYNAMIC_PROJECT_BUDGET_CHAIN gap Exp 33 found: no resolved-fact family existed for
    CIRC-26-02's active-project-record/open-cost-centre check, so the model was guessing. Mirrors
    rules_v2.software()'s exact condition: ESCALATE iff the project is not ACTIVE or its cost centre is
    not OPEN. Argument-free (bound to the claim's own project_id/transaction_date)."""
    f = RT.parse(case)

    def check_project_budget() -> dict:
        # domain guard, same reason as check_hotel_compliance's: SWE-1.2/CIRC-26-02 only governs
        # software subscriptions charged to a project above SGD 1000 from 2026-02-01 -- every claim has
        # a background project_id regardless of type, so without this guard the tool answers a question
        # that was never asked (Exp 42 finding: it fired on two HOTEL claims and both went wrong).
        if f.get("expense_type") != "SOFTWARE":
            # charge_to itself is not reliably regex-extractable from a hardened note (the same issue as
            # 'nights' elsewhere), so the guard only checks expense_type; a SOFTWARE claim not actually
            # charged to a project just gets a harmless "no project record" from get_project_status below.
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a software subscription; check_project_budget does not apply here"}
        pj = T.get_project_status(project_id=case.get("project_id"))
        if not pj["found"]:
            return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "No project record on file; this check does not apply."}, "error": None}
        pjd = pj["data"]
        # APR-5.2: a project with a parent is charged to the PARENT's cost centre, not its own.
        cc = pjd["cost_centre"]
        if pjd.get("parent_project_id"):
            parent = T.get_project_status(project_id=pjd["parent_project_id"])
            if parent["found"]:
                cc = parent["data"]["cost_centre"]
        cb = T.get_cost_centre_budget(cost_centre=cc, year=case["transaction_date"][:4])
        project_active = pjd["project_status"] == "ACTIVE"
        if not project_active:
            return {"ok": True, "found": True, "data": {"project_active": False, "policy_disposition": "ESCALATE", "policy_evidence": ["SWE-1.2", "CIRC-26-02"],
                                                          "reason": "Project is not active."}, "error": None}
        if not cb["found"]:
            return {"ok": True, "found": True, "data": {"project_active": True, "policy_disposition": None, "reason": "No cost-centre budget record on file; this check does not apply further."}, "error": None}
        cbd = cb["data"]
        amount_sgd = RV.sgd(dict(case, form=f))
        # APR-5.1: FROZEN + above SGD 200 -> ESCALATE; OPEN but remaining budget < claim -> REQUEST_INFORMATION (budget-owner approval).
        if cbd["status"] == "FROZEN":
            if amount_sgd > 200:
                return {"ok": True, "found": True, "data": {"project_active": True, "cost_centre_status": "FROZEN", "policy_disposition": "ESCALATE",
                                                              "policy_evidence": ["APR-5.1"], "reason": "Cost centre is frozen and the amount exceeds SGD 200."}, "error": None}
            return {"ok": True, "found": True, "data": {"project_active": True, "cost_centre_status": "FROZEN", "policy_disposition": None, "reason": "Frozen cost centre, but amount is within the SGD 200 exemption."}, "error": None}
        remaining = float(cbd["budget_sgd"]) - float(cbd["committed_sgd"])
        if remaining < amount_sgd:
            return {"ok": True, "found": True, "data": {"project_active": True, "cost_centre_status": cbd["status"], "remaining_budget_sgd": remaining, "policy_disposition": "REQUEST_INFORMATION",
                                                          "policy_evidence": ["APR-5.1"], "reason": f"Remaining budget (SGD {remaining:.0f}) is smaller than the claim; budget-owner approval must be requested."}, "error": None}
        return {"ok": True, "found": True, "data": {"project_active": True, "cost_centre_status": cbd["status"], "remaining_budget_sgd": remaining, "policy_disposition": None,
                                                      "reason": "Project active, cost centre open, and remaining budget covers the claim."}, "error": None}
    return check_project_budget


AGENT_TOOL_SPECS_40 = {
    "check_approval": ({}, "Whether the approval this claim needs is on file and valid, resolved for THIS claim's own expense type and "
                            "amount (you do not supply required_level/required_types -- they cannot be wrong). Returns valid, reason_code and "
                            "policy_disposition (None if compliant, else the disposition this reason_code requires -- use it directly, do not "
                            "re-derive it)."),
    "check_hotel_compliance": ({"grade": ("str", None), "nights": ("amount", None)}, "The full hotel ceiling-and-exception check for THIS "
                                "claim (city/country/exception are resolved automatically). Returns compliant and policy_disposition (None if "
                                "compliant, else the required disposition) -- use policy_disposition directly rather than deciding REJECT vs "
                                "REQUEST_INFORMATION yourself. grade is the employee grade exactly as returned by get_employee_profile, e.g. "
                                "'G4'. nights is the number of nights stated in the employee's own note -- read it from the claim yourself, "
                                "it is not resolved automatically."),
}


def specs_and_tools_40(case: dict) -> tuple:
    specs = {"search_policy_corpus": AT.AGENT_TOOL_SPECS["search_policy_corpus"], "check_approval": AGENT_TOOL_SPECS_40["check_approval"],
             "check_hotel_compliance": AGENT_TOOL_SPECS_40["check_hotel_compliance"],
             **{n: (s, d) for n, (fn, s, d) in T.TOOLS.items() if n != "validate_approval"}, "record_decision": A.RECORD_SPEC}
    case_tools = {"search_policy_corpus": make_search_policy_corpus_v2(case), "check_approval": make_check_approval(case), "check_hotel_compliance": make_check_hotel_compliance(case),
                  "record_decision": A.record_decision, **{n: fn for n, (fn, s, d) in T.TOOLS.items() if n != "validate_approval"}}
    return specs, case_tools


SYSTEM_40 = A.SYSTEM.replace(
    "you must call search_policy_corpus at least once to find the rule (a ceiling, a threshold, an eligibility\ncondition) that actually applies, and use check_rate_ceiling rather than doing that arithmetic yourself.",
    "you must call search_policy_corpus at least once to find the general rule that applies. For approval validity, call check_approval "
    "(it resolves the correct required level/type itself). For a hotel claim, call check_hotel_compliance instead of computing a ceiling "
    "or judging an exception yourself. Both return policy_disposition directly when they find a problem -- use that value as your decision "
    "for that issue rather than re-deriving REJECT vs REQUEST_INFORMATION vs ESCALATE yourself. "
    "If any observation includes 'unverified_policy_domain', you must call search_policy_corpus again before deciding.")


AGENT_TOOL_SPECS_42 = {"check_project_budget": ({}, "Whether THIS claim's project is active and its cost centre is open (SWE-1.2/CIRC-26-02, for software "
                                                     "subscriptions charged to a project above SGD 1000 from Feb 2026). Returns policy_disposition directly "
                                                     "(None if no issue, else ESCALATE) -- use it rather than guessing whether the project chain is valid.")}


def specs_and_tools_42(case: dict) -> tuple:
    """Exp 40/41 + this session's two follow-ups: a domain guard on check_hotel_compliance, and
    check_project_budget for the DYNAMIC_PROJECT_BUDGET_CHAIN gap Exp 33 identified."""
    base_specs, base_tools = specs_and_tools_40(case)
    specs = {**base_specs, "check_project_budget": AGENT_TOOL_SPECS_42["check_project_budget"]}
    case_tools = {**base_tools, "check_project_budget": make_check_project_budget(case)}
    return specs, case_tools


SYSTEM_42 = SYSTEM_40.replace(
    "For a hotel claim, call check_hotel_compliance instead of computing a ceiling or judging an exception yourself.",
    "For a hotel claim (not any other expense type), call check_hotel_compliance instead of computing a ceiling or judging an exception "
    "yourself. For a software subscription charged to a project, call check_project_budget.")


def gate_disposition(result: dict) -> dict:
    """Generalizes gate_approve (Exp 40 finding: the model ignored a correct check_approval disposition
    on 3/5 DYNAMIC_DELEGATION_CHAIN cases and reached the wrong decision anyway, e.g. by calling the
    wrong domain tool). Any policy_disposition already present in the trace is authoritative: if the
    model's final decision disagrees with the single disposition on record, override to it; if two
    tools disagree with each other, that is a genuine conflict and the safe answer is ESCALATE."""
    seen = []
    for step in result.get("trace", []):
        d = (step.get("observation") or {}).get("data")
        pd = d.get("policy_disposition") if isinstance(d, dict) else None
        if pd:
            seen.append((step["tool"], pd))
    if not seen:
        return result
    unique = {pd for _, pd in seen}
    if len(unique) == 1:
        correct = unique.pop()
        if result["decision"] != correct:
            return {**result, "decision": correct, "explanation": result.get("explanation", "") +
                    f" [Exp 41 gate: overridden to {correct} per {seen[0][0]}'s policy_disposition; the model's own answer ({result['decision']}) contradicted it.]"}
        return result
    if result["decision"] != "ESCALATE":
        return {**result, "decision": "ESCALATE", "explanation": result.get("explanation", "") + f" [Exp 41 gate: conflicting dispositions {seen} -> ESCALATE.]"}
    return result


def gate_approve(result: dict) -> dict:
    """Point 5: a code-level check before any APPROVE is accepted. Scans the already-returned trace for
    a policy_disposition or a valid/compliant=False signal from check_approval/check_hotel_compliance;
    if the model still answered APPROVE despite one being present, override to ESCALATE server-side
    rather than trusting the model's own reconciliation of a known negative signal."""
    if result.get("decision") != "APPROVE":
        return result
    for step in result.get("trace", []):
        d = (step.get("observation") or {}).get("data") or {}
        if d.get("policy_disposition") or d.get("valid") is False or d.get("compliant") is False:
            return {**result, "decision": "ESCALATE", "explanation": result.get("explanation", "") +
                    f" [Exp 40 gate: overridden from APPROVE -- {step['tool']} returned a disposition of {d.get('policy_disposition')!r} that was not honored.]"}
    return result
