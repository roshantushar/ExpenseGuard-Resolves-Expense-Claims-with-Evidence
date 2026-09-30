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

DOC = Path(__file__).resolve().parents[1] / "ExpenseGuard_DATASET" / "01_policy_corpus" / "source_documents" / "D04_TRV.md"

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

    def check_hotel_compliance(grade, nights=None, check_in_date=None, check_out_date=None) -> dict:
        if f.get("expense_type") != "HOTEL":
            # domain guard: Exp 41 found the model calling this tool on a non-hotel (meal) claim and
            # treating its output as if it applied -- refuse outright rather than let a manufactured
            # "ceiling" feed a wrong decision.
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a HOTEL expense; check_hotel_compliance does not apply here"}
        # TRV-1.1 prerequisite, checked first in both rules_v2.hotel() and workflow_v2.hotel() but
        # missing here until Exp 51's validation run caught it (X2-115: a compliant ceiling with no
        # approved travel request silently returned "no issue," leading to a false approval) -- a ceiling
        # or exception being fine is meaningless if there was never an approved trip to begin with.
        tr = RV.travel_request(case)
        if not tr or tr.get("status") != "APPROVED":
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["TRV-1.1"], "missing_fields": ["approved_travel_request"],
                                                          "reason": "No approved travel request covers the transaction date."}, "error": None}
        r = ceiling_tool(grade)
        if not r["ok"]:
            return r
        d = r["data"]
        # nights is rarely regex-extractable from a hardened free-text note (that's the point of the
        # hardening); RT.parse's own value is used only when the model doesn't supply one. Prefer
        # check_in_date/check_out_date when given: the model has been observed miscounting nights from a
        # stated date range itself (X2-104: "23rd to 25th August" computed as 3 nights instead of 2,
        # confused by a self-correction sentence in the note) -- the same class of arithmetic error this
        # tool already exists to prevent for the ceiling division. Code computes the difference instead.
        if check_in_date and check_out_date:
            from datetime import date as _date
            try:
                nights = (_date.fromisoformat(check_out_date) - _date.fromisoformat(check_in_date)).days
            except ValueError:
                return {"ok": False, "found": False, "data": None, "error": "check_in_date/check_out_date must be YYYY-MM-DD"}
        else:
            nights = nights or f.get("nights")
        if not nights:
            return {"ok": False, "found": False, "data": None, "error": "nights not stated; pass check_in_date and check_out_date (preferred, code computes the count) or nights directly"}
        rate = round(case["bill"]["total"] / int(nights), 2)
        compliant = rate <= d["ceiling"] + 1e-9
        base = {**d, "nightly_rate": rate}
        if compliant:
            return {"ok": True, "found": True, "data": {**base, "compliant": True, "policy_disposition": None, "reason": "Within the applicable ceiling."}, "error": None}
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
    "check_hotel_compliance": ({"grade": ("str", None), "nights": ("amount?", None), "check_in_date": ("str?", None), "check_out_date": ("str?", None)},
                                "The full hotel ceiling-and-exception check for THIS claim (city/country/exception are resolved automatically). "
                                "Returns compliant and policy_disposition (None if compliant, else the required disposition) -- use "
                                "policy_disposition directly rather than deciding REJECT vs REQUEST_INFORMATION yourself. grade is the employee "
                                "grade exactly as returned by get_employee_profile, e.g. 'G4'. PREFER passing check_in_date and check_out_date "
                                "(YYYY-MM-DD, exactly as stated in the note) over counting nights yourself -- do the arithmetic in your head and "
                                "you will sometimes miscount, especially if the note corrects itself mid-sentence; only pass nights directly when "
                                "no clear date range is stated."),
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


# ================================================================== Exp 47: broad category coverage
# Exp 45 found false approvals concentrated entirely in categories with no guarded tool. Two are closed
# here: check_meal_compliance (mirrors rules_v2.meal() exactly; Exp 45's meal false approvals traced to
# RT.parse misreading the note -- one even flipped MEAL_EMPLOYEE to MEAL_CLIENT, which uses a materially
# higher ceiling, so is_client/attendees/external/alcohol/tip are all model-supplied, the same fix
# pattern as nights/city for hotels) and check_workflow_compliance (a broad net: reuses workflow_v2.decide,
# already tested end-to-end in Exp 18 through typed tools only, as a NEGATIVE-signal source for every
# other category -- its REJECT/REQUEST_INFORMATION/ESCALATE verdicts are trusted, but never its own
# APPROVE, since workflow_v2 itself has a measured 13.5% false-approval rate; trusting only its negative
# verdicts keeps that risk out while still catching real violations it does correctly detect).

def make_check_meal_compliance(case: dict):
    f = RT.parse(case)

    def check_meal_compliance(is_client_meal: bool, attendees_total, external_attendees=0, external_names=None, alcohol_amount=0, tip_amount=0) -> dict:
        # external_names is deliberately accepted as whatever the model naturally wants to pass (the
        # actual name(s), a comma-joined string, a list, or nothing/empty) rather than a bool the model
        # has to compute -- a live run showed it consistently passing [] / "" / null for "no names" and
        # getting rejected every time by a strict bool check, burning the whole turn budget on retries.
        # Only the truthiness of what's given matters here: were names actually provided or not.
        has_names = bool(external_names) and (not isinstance(external_names, (list, str)) or len(external_names) > 0)
        if f.get("expense_type") not in ("MEAL_CLIENT", "MEAL_EMPLOYEE"):
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a meal expense; check_meal_compliance does not apply here"}
        b = case["bill"]; y = RV.Y(case); r = RV.region(case); yr = int(case["transaction_date"][:4]); d = case["transaction_date"]
        client = bool(is_client_meal) or (external_attendees or 0) > 0
        alc = float(alcohol_amount or 0)
        if r == "IN" and alc:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["IN-2.4"], "reason": "Alcohol is not reimbursable in India."}, "error": None}
        if alc and not client:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["SG-2.4" if r == "SG" else "JP-2.4"], "reason": "Alcohol permitted only with external attendees."}, "error": None}
        if alc:
            lim = 0.30 if (r == "JP" or (r == "SG" and yr == 2026)) else 0.35
            if alc > lim * b["total"] + 1e-9:
                return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["MEAL-2.1"], "reason": "Alcohol exceeds the share limit."}, "error": None}
        n = attendees_total
        if not n:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["MEAL-3.2"], "reason": "Attendee count needed."}, "error": None}
        if client and (external_attendees or 0) > 0 and not has_names:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["MEAL-1.2"], "reason": "External attendee names required."}, "error": None}
        tip = float(tip_amount or 0)
        if r == "JP" and tip > 0:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["JP-2.5"], "reason": "Gratuities not reimbursable in Japan."}, "error": None}
        ceil = (RV.CLIENT_MEAL if client else RV.EMP_MEAL)[r][y]
        if client and r == "SG" and yr == 2025 and d >= "2025-07-01":
            ceil = 128
        if client and r == "JP" and yr == 2026 and d >= "2026-05-01":
            ceil = 13500
        if not client:
            if r == "SG" and yr == 2025 and d >= "2025-09-01": ceil = 52
            if r == "JP" and yr == 2025 and d >= "2025-10-01": ceil = 5200
            if r == "IN" and yr == 2025 and d >= "2025-11-01": ceil = 2100
        per_person = b["total"] / n
        if per_person > ceil + 1e-9:
            return {"ok": True, "found": True, "data": {"per_person_spend": round(per_person, 2), "ceiling": ceil, "policy_disposition": "REJECT",
                                                          "policy_evidence": ["MEAL-1.2" if client else "MEAL-1.1"], "reason": f"Per-person spend {per_person:.0f} exceeds ceiling {ceil}."}, "error": None}
        pre = b["total"] - tip
        if tip and pre > 0 and tip > 0.15 * pre and r != "JP":
            return {"ok": True, "found": True, "data": {"per_person_spend": round(per_person, 2), "ceiling": ceil, "policy_disposition": "REQUEST_INFORMATION",
                                                          "policy_evidence": ["MEAL-2.2"], "reason": "Gratuity above 15% needs manager approval; confirm approval on file."}, "error": None}
        return {"ok": True, "found": True, "data": {"per_person_spend": round(per_person, 2), "ceiling": ceil, "policy_disposition": None, "reason": "Within ceiling, no issue found."}, "error": None}

    return check_meal_compliance


def make_check_gift_compliance(case: dict):
    """Mirrors rules_v2.gift() exactly. Recipient fields, gift form and prior-annual-spend context are
    all model-supplied -- the same reason as everywhere else: not reliably regex-extractable."""
    f = RT.parse(case)

    def check_gift_compliance(recipient_type: str = None, gift_form: str = None, recipient_name: str = None, recipient_org: str = None) -> dict:
        if f.get("expense_type") != "GIFT":
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a gift expense; check_gift_compliance does not apply here"}
        b, y, r, d = case["bill"], RV.Y(case), RV.region(case), case["transaction_date"]
        if (recipient_type or "").upper() in ("GOVERNMENT", "TENDER_DECISION_MAKER", "PUBLIC_OFFICIAL") or (gift_form or "").upper() in ("CASH", "GIFT_CARD", "VOUCHER", "CASH_EQUIVALENT"):
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["GIFT-1.2", "GIFT-1.3"], "reason": "Prohibited recipient or cash equivalent."}, "error": None}
        miss = [k for k, v in (("recipient_name", recipient_name), ("recipient_org", recipient_org)) if not v]
        if miss:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["GIFT-1.4"], "missing_fields": miss, "reason": "Recipient details missing."}, "error": None}
        cap = RV.GIFT[r][y]
        if r == "SG" and d >= "2026-06-01":
            cap = 130
        if b["total"] > cap:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["GIFT-2.1"], "reason": f"Gift {b['total']} exceeds per-gift ceiling {cap}."}, "error": None}
        hist = T.search_previous_expenses(employee_id=case["employee_id"], date_from=f"{d[:4]}-01-01", date_to=f"{d[:4]}-12-31")
        prior_rows = hist["data"] or [] if hist["found"] else []
        prior = sum(float(p["amount"]) for p in prior_rows if p.get("category") == "GIFT" and p.get("counterparty") == recipient_org)
        if prior + b["total"] > RV.GIFT_ANNUAL[r][y]:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["GIFT-2.2"], "reason": "Annual gift ceiling for the recipient organisation exceeded."}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "Within per-gift and annual ceilings, recipient details given, no prohibited form."}, "error": None}

    return check_gift_compliance


def make_check_ground_transport_compliance(case: dict):
    """Mirrors rules_v2.ground() exactly. origin/destination/whether either end is home are model-
    supplied (the same reason as attendees_total for meals: not reliably regex-extractable from a
    hardened note)."""
    f = RT.parse(case)

    _UNSTATED = {"unknown", "not stated", "not known", "n/a", "na", "none", "unspecified", "not specified", "not given", "unclear", ""}

    def check_ground_transport_compliance(origin: str = None, destination: str = None, either_end_is_home: bool = False,
                                           departure_time: str = None, activity_end_time: str = None) -> dict:
        if f.get("expense_type") != "GROUND_TRANSPORT":
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a ground-transport expense; check_ground_transport_compliance does not apply here"}
        # the model has been observed passing a placeholder like "unknown" instead of omitting the
        # argument when the note genuinely doesn't state it -- a non-empty string still passes `not x`,
        # so normalize known placeholders to missing before checking.
        if origin and str(origin).strip().lower() in _UNSTATED:
            origin = None
        if destination and str(destination).strip().lower() in _UNSTATED:
            destination = None
        if not origin or not destination:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["GRD-1.1"], "missing_fields": ["origin", "destination"],
                                                          "reason": "Route details missing."}, "error": None}
        if either_end_is_home:
            late = (departure_time or "00:00") > "22:00" and (activity_end_time or "00:00") > "21:30"
            if not late:
                return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["GRD-1.2"], "reason": "Commute is not reimbursable."}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "Route stated and not an ordinary commute."}, "error": None}

    return check_ground_transport_compliance


AGENT_TOOL_SPECS_47 = {
    "check_gift_compliance": ({"recipient_type": ("str?", None), "gift_form": ("str?", None), "recipient_name": ("str?", None), "recipient_org": ("str?", None)},
                              "The full gift compliance check for THIS claim (prohibited recipient/cash-equivalent, per-gift ceiling, annual "
                              "per-recipient-organisation ceiling). Read recipient_type (e.g. GOVERNMENT/PUBLIC_OFFICIAL if applicable), gift_form "
                              "(e.g. CASH/GIFT_CARD/VOUCHER if applicable), recipient_name and recipient_org yourself from the note. Returns "
                              "policy_disposition directly."),
    "check_ground_transport_compliance": ({"origin": ("str?", None), "destination": ("str?", None), "either_end_is_home": ("bool?", None),
                                           "departure_time": ("str?", None), "activity_end_time": ("str?", None)},
                                          "The ground-transport compliance check for THIS claim. Read origin, destination, whether either end "
                                          "is the employee's home, and (if home is involved) the departure/activity-end times yourself from the "
                                          "note. Returns policy_disposition directly."),
    "check_meal_compliance": ({"is_client_meal": ("bool", None), "attendees_total": ("amount", None), "external_attendees": ("amount?", None),
                               "external_names": ("text_or_list?", None), "alcohol_amount": ("amount?", None), "tip_amount": ("amount?", None)},
                              "The full meal compliance check for THIS claim (alcohol, tip, per-person ceiling with temporal amendments). Read "
                              "is_client_meal, attendees_total, external_attendees, alcohol_amount and tip_amount yourself from the employee's "
                              "note -- do not trust a superficial reading; a note can describe a colleague as external-sounding without them being "
                              "an external guest. external_names: pass the actual name(s) if the note states them, or omit/leave blank if it "
                              "doesn't -- do not pass true/false. Returns policy_disposition directly."),
}


def make_check_workflow_compliance(case: dict):
    from . import workflow_v2 as WF
    f = RT.parse(case)

    # ALLOWLIST, not a denylist: Exp 47 found check_workflow_compliance regressed cases across meal,
    # delegation, gift, mileage AND approval-tier categories -- because workflow_v2.decide() internally
    # calls RT.parse for every category-specific check (attendees, gift recipient, tip, alcohol...), the
    # exact same fragile free-text extraction responsible for the tier/nights/attendee bugs found
    # elsewhere this session. A denylist naming only the checks WITH a dedicated fix (hotel, software,
    # meal) leaves every other category's fragile check trusted by default -- backwards. Trusting only
    # the checks that never depend on a free-text field at all is the safe default: duplicates
    # (DUP-*, bill/date-based), submission window (GEP*-2.1/2.2, date-based), merchant/consumer-service
    # restriction (CARD-*), and mandatory-documentation (GEP*-1.3, bill-field presence). Every other
    # category (gift, delegation-consequence outside hotel/software, mileage, telecom, training,
    # conference, car, equipment) is left unresolved here until it gets the same model-argument-based
    # treatment check_hotel_compliance/check_meal_compliance already received.
    _TRUSTED_PREFIXES = ("DUP-", "CARD-")
    _TRUSTED_EXACT_SUFFIXES = ("-2.1", "-2.2", "-1.3")  # GEP24/25/26-2.1 (submission window), -2.2 (late/outage), -1.3 (mandatory docs)

    def _is_trusted(policy_evidence: list) -> bool:
        return any(c.startswith(_TRUSTED_PREFIXES) or (c.startswith("GEP") and c.endswith(_TRUSTED_EXACT_SUFFIXES)) for c in policy_evidence)

    def check_workflow_compliance() -> dict:
        # CARD-2.1 ("consumer service presumed personal") is checked by rules_v2/workflow_v2 against the
        # VISIBLE, coarsened bill.merchant_category (round-3 hardening deliberately coarsened it to "OTHER"
        # etc.), so it can never trigger there -- but the TRUE category is still on file in the merchant
        # directory (real enterprise data, not free text), and the model has been observed missing it
        # (X2-013, MovieBox+). This is not a free-text-parsing shortcut: get_merchant_metadata is a tool
        # the agent already has direct access to; this only makes the cross-check systematic.
        mm = T.get_merchant_metadata(merchant_name=case["bill"]["merchant"])
        if mm["found"] and mm["data"].get("merchant_category") in ("CONSUMER_SERVICE", "STREAMING", "FITNESS"):
            return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["CARD-2.1"],
                                                          "reason": f"Merchant directory lists {case['bill']['merchant']} as {mm['data']['merchant_category']}; consumer service presumed personal."}, "error": None}
        try:
            d = WF.decide(case)
        except Exception as e:  # noqa
            return {"ok": False, "found": False, "data": None, "error": f"workflow error: {type(e).__name__}"}
        if d["decision"] == "APPROVE" or not _is_trusted(d.get("policy_evidence", [])):
            # workflow_v2's own APPROVE is not trusted as a positive signal (it has a measured 13.5% FAR,
            # Exp 30); a non-APPROVE verdict outside the trusted (free-text-independent) checks is ALSO
            # not trusted, since it can be just as wrong as a false approval when it rests on a misread
            # note field. Either way this is reported as "no issue found here", not a resolved answer.
            return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "No violation found among this tool's trusted (free-text-independent) checks."}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": d["decision"], "policy_evidence": d.get("policy_evidence", []),
                                                      "missing_fields": d.get("missing_fields", []), "reason": d.get("reason", "")}, "error": None}

    return check_workflow_compliance


AGENT_TOOL_SPECS_47["check_workflow_compliance"] = ({}, "Checks THIS claim for duplicate submission, a late/very-late submission, a restricted or "
                    "consumer-service merchant, and mandatory documentation -- the checks that never depend on reading a category-specific field "
                    "from the note (so they cannot be wrong the way a ceiling or attendee count can be). Call this for any claim before concluding "
                    "APPROVE. It does NOT check telecom, training, mileage, car rental or equipment category rules -- for those, and for any "
                    "claim it returns no issue on, still form your own judgement from search_policy_corpus and the enterprise tools.")


def specs_and_tools_47(case: dict) -> tuple:
    base_specs, base_tools = specs_and_tools_42(case)
    specs = {**base_specs, "check_meal_compliance": AGENT_TOOL_SPECS_47["check_meal_compliance"], "check_workflow_compliance": AGENT_TOOL_SPECS_47["check_workflow_compliance"],
             "check_ground_transport_compliance": AGENT_TOOL_SPECS_47["check_ground_transport_compliance"], "check_gift_compliance": AGENT_TOOL_SPECS_47["check_gift_compliance"]}
    case_tools = {**base_tools, "check_meal_compliance": make_check_meal_compliance(case), "check_workflow_compliance": make_check_workflow_compliance(case),
                  "check_ground_transport_compliance": make_check_ground_transport_compliance(case), "check_gift_compliance": make_check_gift_compliance(case)}
    return specs, case_tools


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


SYSTEM_47 = SYSTEM_42.replace(
    "For a software subscription charged to a project, call check_project_budget.",
    "For a software subscription charged to a project, call check_project_budget. For a meal claim, call check_meal_compliance -- read every "
    "argument yourself from the note; do not assume a colleague described in passing is an external guest, or vice versa. For a gift claim, call "
    "check_gift_compliance. For a ground-transport claim, call check_ground_transport_compliance. For any claim, also call "
    "check_workflow_compliance before concluding APPROVE -- it catches duplicates, late submission, and restricted merchants, which apply "
    "regardless of category.")


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
        d = (step.get("observation") or {}).get("data")
        if not isinstance(d, dict):
            continue
        if d.get("policy_disposition") or d.get("valid") is False or d.get("compliant") is False:
            return {**result, "decision": "ESCALATE", "explanation": result.get("explanation", "") +
                    f" [Exp 40 gate: overridden from APPROVE -- {step['tool']} returned a disposition of {d.get('policy_disposition')!r} that was not honored.]"}
    return result
