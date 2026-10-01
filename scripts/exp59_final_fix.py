"""Exp 59: "fix them all." Addresses every item from the Exp 58 failure report:
  1. check_hotel_compliance's INVALID-exception-status gap -- fixed directly in hotel_ceiling_v56.py.
  2. rules_v2.decide()'s naive substring conflict-check (X2-028, X2-089, X2-117): false positives from
     (a) decoy sentences about a past/unrelated trip, (b) literal substring collisions inside an unrelated
     word ("applicable" contains "cab"). Fixed with word-boundary regex + decoy-sentence filtering, in a
     standalone decide_fixed() that otherwise replicates rules_v2.decide() exactly (frozen, not edited).
  3. The same fixed check exposed to the agent as a new check_evidence_consistency tool (X2-061: a
     ride-hailing bill, a note describing a hotel stay -- GEP26-4.1/1.2, not previously enforced by any
     agent tool).
  4. check_workflow_compliance's DUP-1.2 signal trusts workflow_v2.duplicates(), which is missing the
     same_kind() check rules_v2.duplicates() (frozen, correct) has -- caused a false "possible duplicate"
     on X2-078, a monthly software subscription matched against an unrelated, differently-categorized
     record one day prior. Fixed by cross-checking any DUP-1.2 signal against the correct rules_v2.duplicates().
  5. Two missing tools: check_airfare_compliance (X2-028/X2-080 -- cabin ceiling + exception status,
     mirrors rules_v2.airfare()) and check_training_compliance (X2-112, mirrors rules_v2.training()).
  6. check_meal_compliance trusts a bare external_attendees count the model computed itself -- on X2-066 the
     model classified a subsidiary colleague as "external," which is wrong per D07_MEAL.md line 36 ("an
     attendee is an employee ... including interns and secondees on payroll") and flips the ceiling from
     EMP_MEAL to the much higher CLIENT_MEAL table. Fixed with a new check_meal_compliance_v59 that takes
     attendee_roles (per-attendee classification) and applies the payroll/subsidiary/intern rule in code,
     not the model's own judgement.
  7. X2-008: the note explicitly states "I have not got the total number of people at the table" and the
     agent still guessed a decision. Addressed with one added system-prompt sentence, not a new tool -- this
     one genuinely is an instruction-following issue, not a missing computation.

Nothing in src/ is edited. Every fix is a new function reusing frozen rules_v2/workflow_v2 math unmodified
except where it is demonstrably wrong (item 4).
"""
from __future__ import annotations
import re
import json
from src import agent, agent_variants as V, llm_exp, rules_text as RT, rules_v2 as RV, workflow_v2 as WF, tables as T
from scripts.hotel_ceiling_v56 import make_check_hotel_compliance_v56
from scripts.exp58_full_agent_fix import make_check_mileage_compliance, make_check_software_compliance, MILEAGE_SPEC, SOFTWARE_SPEC

# ---------- 2/3. Fixed conflict check ----------

_CONFLICT_KWS = {"HOTEL": ("hotel", "nights"), "AIRFARE": ("flight", "airfare"), "GROUND_TRANSPORT": ("taxi", "cab", "ride")}
_DECOY_MARKERS = re.compile(r"\b(last year|last yr|previous(ly)?|earlier|initially|for reference|historically)\b", re.I)


def _split_sentences(text: str) -> list:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def conflict_detected(description: str, et: str) -> bool:
    """Word-boundary keyword match, restricted to sentences that are not themselves marked as referring to
    a past/different occasion. Fixes both known false-positive classes: substring collisions ("applicable"
    matching "cab") and decoy sentences ("last year's trip... 5 nights")."""
    live_sentences = [s for s in _split_sentences(description) if not _DECOY_MARKERS.search(s)]
    live_text = " ".join(live_sentences).lower()
    for kind, kws in _CONFLICT_KWS.items():
        if et != kind and et in ("GROUND_TRANSPORT", "HOTEL", "AIRFARE"):
            if any(re.search(rf"\b{re.escape(k)}\b", live_text) for k in kws):
                return True
    return False


def decide_fixed(c: dict) -> dict:
    """Replicates rules_v2.decide() exactly, with only the conflict-check block replaced."""
    b, f = c["bill"], c["form"]; et = f.get("expense_type")
    if not (b.get("merchant") and b.get("total") and c["employee_description"].strip()):
        return RV.out("REQUEST_INFORMATION", ["GEP26-1.3"], ["business_purpose"], "Mandatory documentation missing.")
    m = next(iter(RV.rows("merchant_directory", merchant_name=b["merchant"])), None)
    if m and m["risk_class"] == "RESTRICTED_PROHIBITED":
        return RV.out("REJECT", ["CARD-3.1"], (), "Prohibited merchant class.")
    if m and m["risk_class"] == "RESTRICTED_REVIEW":
        return RV.out("ESCALATE", ["CARD-3.1"], (), "Restricted merchant requires Finance review.")
    if b["merchant_category"] in ("CONSUMER_SERVICE", "STREAMING", "FITNESS"):
        return RV.out("REJECT", ["CARD-2.1"], (), "Consumer service presumed personal.")
    if conflict_detected(c["employee_description"], et):
        return RV.out("REQUEST_INFORMATION", ["GEP26-4.1", "GEP26-1.2"], ["correct_business_purpose"], "Description conflicts with the bill category.")
    for fn in (RV.duplicates, RV.submission):
        o = fn(c)
        if o:
            return o
    per = {"HOTEL": RV.hotel, "AIRFARE": RV.airfare, "MEAL_CLIENT": RV.meal, "MEAL_EMPLOYEE": RV.meal, "GIFT": RV.gift, "SOFTWARE": RV.software, "EQUIPMENT": RV.equipment,
           "TELECOM": RV.telecom, "TRAINING": RV.training, "CONFERENCE_FEE": RV.conference, "GROUND_TRANSPORT": RV.ground, "CAR_RENTAL": RV.car, "MILEAGE": RV.mileage}.get(et)
    if per:
        o = per(c)
        if o:
            return o
    for fn in (RV.split, RV.budget):
        o = fn(c)
        if o:
            return o
    lvl = RV.need_level(c)
    if et not in ("SOFTWARE", "EQUIPMENT", "CAR_RENTAL") and lvl:
        if lvl == 9:
            return RV.out("ESCALATE", ["APR-1.3"], (), "Above SGD 5000 requires Finance review.")
        a = RV.approval_state(c, lvl, RV.TYPES.get(et, ("GENERAL",)))
        if a:
            return RV.out(a[0], a[1], a[2], a[3])
    return RV.out("APPROVE", [], (), "No rule triggered.")


_RELATIVE_DEPARTURE_RE = re.compile(rf"{RT.NUMBER}\s*days?\s*(?:later|after)(?:\s*than)?(?:\s*the)?(?:\s*booking(?:\s*date)?)?", re.I)


def _fix_relative_departure_date(c: dict, f: dict) -> dict:
    """rules_text.parse()'s regex has no relative-date support ('departs 21 days later' / '28 days after
    the booking date') -- it silently leaves departure_date equal to booked_date, which makes the
    deterministic airfare() check miss the real travel request entirely and return a confident but wrong
    REQUEST_INFORMATION (X2-028, X2-080), never reaching the agent where this could otherwise be caught.
    Standalone correction, not a change to the frozen parser."""
    if f.get("expense_type") != "AIRFARE":
        return f
    # "biz class" isn't recognized by the frozen parser's cabin regex (business|lie-flat) -- silently
    # defaults to ECONOMY, which made X2-028's cabin-ceiling check wrongly pass.
    if f.get("cabin") == "ECONOMY" and re.search(r"\bbiz\b", c["employee_description"], re.I):
        f = {**f, "cabin": "BUSINESS"}
    if f.get("booked_date"):
        m = _RELATIVE_DEPARTURE_RE.search(c["employee_description"])
        if m:
            n = RT.num(m.group(1))
            if n is not None:
                from datetime import date, timedelta
                f = {**f, "departure_date": (date.fromisoformat(f["booked_date"]) + timedelta(days=int(n))).isoformat()}
    return f


def deterministic_fixed(c: dict) -> tuple:
    f = RT.parse(c)
    f = _fix_relative_departure_date(c, f)
    c2 = dict(c, form=f)
    d = decide_fixed(c2)
    needed = {"MEAL_CLIENT": ["attendees_total", "external_names"], "MEAL_EMPLOYEE": ["attendees_total"], "HOTEL": ["nights"], "AIRFARE": ["cabin", "flight_hours"],
              "MILEAGE": ["distance_km"], "GIFT": ["recipient_name", "recipient_org"], "SOFTWARE": ["business_owner"], "TRAINING": ["learning_plan_id"],
              "GROUND_TRANSPORT": ["origin", "destination"], "TELECOM": [], "EQUIPMENT": [], "CONFERENCE_FEE": [], "CAR_RENTAL": [], "OTHER": []}
    unresolved_field = any(f.get(k) is None for k in needed.get(f.get("expense_type"), []))
    fallback = d["reason"] == "No rule triggered."
    return d, (not fallback and not unresolved_field)


def make_check_evidence_consistency(case: dict):
    f = RT.parse(case)

    def check_evidence_consistency() -> dict:
        if conflict_detected(case["employee_description"], f.get("expense_type")):
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["GEP26-4.1", "GEP26-1.2"],
                                                          "missing_fields": ["correct_business_purpose"],
                                                          "reason": "The note describes a different expense type than the bill's own category -- clarify before deciding."}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "Note and bill category are consistent; no conflict found."}, "error": None}

    return check_evidence_consistency


EVIDENCE_SPEC = ({}, "Call this for EVERY claim before concluding a decision. Checks whether the free-text note actually "
                      "describes the same kind of expense as the bill's own category (e.g. a note describing a hotel stay "
                      "attached to a ride-hailing bill). Returns policy_disposition directly if there is a conflict.")

# ---------- 4. Duplicate check, cross-verified against the correct rules_v2.duplicates() ----------


def make_check_workflow_compliance_fixed(case: dict):
    original = V.make_check_workflow_compliance(case)
    f = RT.parse(case)
    c2 = dict(case, form=f)

    def check_workflow_compliance() -> dict:
        r = original()
        if r.get("ok") and isinstance(r.get("data"), dict) and "DUP-1.2" in (r["data"].get("policy_evidence") or []):
            # workflow_v2.duplicates() is missing the same_kind() check rules_v2.duplicates() (frozen,
            # correct) has -- cross-verify before trusting a possible-duplicate signal.
            real = RV.duplicates(c2)
            if not real:
                return {"ok": True, "found": True, "data": {"policy_disposition": None,
                                                              "reason": "No violation found among this tool's trusted checks (a workflow-reported possible duplicate did not match "
                                                                        "on expense category and was not trusted)."}, "error": None}
        return r

    return check_workflow_compliance


# ---------- 5. Missing tools: airfare, training ----------


def make_check_airfare_compliance(case: dict):
    f = RT.parse(case)

    def check_airfare_compliance(cabin: str, flight_hours=None, exception_id=None, departure_date=None) -> dict:
        if f.get("expense_type") != "AIRFARE":
            return {"ok": False, "found": False, "data": None, "error": "this claim is not an airfare expense; check_airfare_compliance does not apply here"}
        # rules_text.py's regex cannot compute a relative date ("28 days after the booking date") -- it was
        # silently leaving departure_date equal to booked_date, which misses the real travel request
        # entirely (X2-028, X2-080). The model can read and compute this itself from the note; prefer its
        # answer over the frozen parser's when given.
        tr = RV.travel_request(case, departure_date or f.get("departure_date"))
        if not tr or tr["status"] != "APPROVED":
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["TRV-1.1"], "missing_fields": ["approved_travel_request"],
                                                          "reason": "No approved travel request covers the departure date."}, "error": None}
        y = int(case["transaction_date"][:4]); g = RV.grade(case); hrs = float(flight_hours or 0)
        pe_hours = 5.5 if (y == 2025 and case["transaction_date"] >= "2025-04-01") else 6
        cabin = str(cabin).upper()
        ok = cabin == "ECONOMY" or (cabin == "PREMIUM_ECONOMY" and hrs > pe_hours and g >= 4) or (cabin == "BUSINESS" and (g >= 7 or (g >= 6 and hrs > 9)))
        if ok:
            return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": f"{cabin} is permitted for grade G{g} at {hrs}h."}, "error": None}
        exc_id = exception_id or f.get("exception_ref") or tr.get("exception_id")
        st = RV.exception_for(case, "AIR-2.2", exc_id)
        if st == "VALID":
            return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "A valid exception covers this cabin class."}, "error": None}
        if st == "WRONG_SCOPE":
            return {"ok": True, "found": True, "data": {"policy_disposition": "ESCALATE", "policy_evidence": ["EXC-2.1"],
                                                          "reason": "Exception names a different policy or employee -- Finance must review."}, "error": None}
        if st == "MISSING_ID":
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["EXC-2.1"],
                                                          "reason": "Cited exception identifier does not exist; request the correct reference."}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": "REJECT", "policy_evidence": ["AIR-2.1", "AIR-2.2"],
                                                      "reason": f"{cabin} not permitted for grade G{g}, {hrs}h; no valid exception."}, "error": None}

    return check_airfare_compliance


AIRFARE_SPEC = ({"cabin": ("str", None), "flight_hours": ("amount?", None), "exception_id": ("str?", None), "departure_date": ("str?", None)},
                 "For an AIRFARE claim: call this instead of judging the cabin class or an exception yourself. Pass the "
                 "cabin class and flight duration as stated in the note, any cited exception id, and departure_date as "
                 "YYYY-MM-DD -- if the note states the departure relative to the booking date (e.g. '28 days after "
                 "booking'), compute the actual calendar date yourself and pass that, not the booking date.")


def make_check_training_compliance(case: dict):
    f = RT.parse(case)

    def check_training_compliance(learning_plan_id=None) -> dict:
        if f.get("expense_type") != "TRAINING":
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a training expense; check_training_compliance does not apply here"}
        lp = learning_plan_id or f.get("learning_plan_id")
        if not lp:
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["TRN-2.4"], "missing_fields": ["learning_plan_id"],
                                                          "reason": "Learning plan identifier required."}, "error": None}
        y = int(case["transaction_date"][:4]); amt = RV.sgd(case)
        prior = 0.0
        for p in RV.rows("previous_expenses", employee_id=case["employee_id"], category="TRAINING"):
            if p["transaction_date"][:4] == str(y):
                prior += float(p["amount"]) * T.fx_to_sgd(p["currency"], p["transaction_date"])
        cap = RV.TRAIN[y][RV.band(RV.grade(case))]
        if prior + amt > cap:
            a = RV.approval_state(case, 2, ("TRAINING",))
            if a:
                return {"ok": True, "found": True, "data": {"policy_disposition": a[0], "policy_evidence": a[1], "missing_fields": a[2] or ["director_approval"], "reason": a[3]}, "error": None}
        return {"ok": True, "found": True, "data": {"policy_disposition": None, "reason": "Within the annual training cap, or a valid director approval is on file."}, "error": None}

    return check_training_compliance


TRAINING_SPEC = ({"learning_plan_id": ("str?", None)}, "For a TRAINING claim: call this instead of judging the annual cap yourself. Pass the learning plan id from the note if stated.")

# ---------- 6. Meal attendee classification moved into code ----------

_INTERNAL_ROLES = {"employee", "subsidiary_employee", "intern_payroll", "secondee_payroll"}
_EXTERNAL_ROLES = {"freelancer", "contractor", "agency_staff", "partner_staff", "customer_staff", "external_guest"}


def make_check_meal_compliance_v59(case: dict):
    original = V.make_check_meal_compliance(case)

    def check_meal_compliance(attendee_role_counts: list = None, alcohol_amount=0, tip_amount=0, external_names=None, is_client_meal=None, attendees_total=None, external_attendees=None) -> dict:
        # Prefer the counted classification: D07_MEAL.md is explicit that payroll subsidiary employees and
        # interns/secondees are EMPLOYEES, not external guests (X2-066: the model called an on-payroll
        # subsidiary colleague "external," swapping in the much higher client-meal ceiling).
        # attendee_role_counts is a list of "role:count" strings (e.g. ["employee:8", "external_guest:9"])
        # rather than one entry per individual attendee -- a large-party claim (X2-047: 18 attendees) showed
        # the model won't reliably enumerate every single person, and trusting len() of a partial list
        # silently undercounted the total. A count per role scales to any party size.
        if attendee_role_counts:
            counts = {}
            for item in attendee_role_counts:
                role, _, cnt = str(item).rpartition(":")
                if not role or role not in _INTERNAL_ROLES | _EXTERNAL_ROLES or not cnt.strip().isdigit():
                    return {"ok": False, "found": False, "data": None, "error": f"each entry must be 'role:count' with role in {sorted(_INTERNAL_ROLES | _EXTERNAL_ROLES)}, got {item!r}"}
                counts[role] = counts.get(role, 0) + int(cnt)
            n = sum(counts.values())
            ext = sum(v for k, v in counts.items() if k in _EXTERNAL_ROLES)
            is_client_meal = ext > 0
            attendees_total, external_attendees = n, ext
        return original(bool(is_client_meal), attendees_total, external_attendees or 0, external_names, alcohol_amount, tip_amount)

    return check_meal_compliance


MEAL_SPEC_V59 = ({"attendee_role_counts": ("list_str_ok_empty", None), "alcohol_amount": ("amount?", None), "tip_amount": ("amount?", None), "external_names": ("text_or_list?", None),
                  "is_client_meal": ("bool?", None), "attendees_total": ("amount?", None), "external_attendees": ("amount?", None)},
                 "For a MEAL claim: prefer attendee_role_counts -- a list of 'role:count' strings covering "
                 "EVERYONE at the meal including yourself, e.g. [\"employee:8\", \"subsidiary_employee:1\", "
                 "\"external_guest:9\"]. Roles employee|subsidiary_employee|intern_payroll|secondee_payroll all "
                 "count as internal (D07_MEAL.md is explicit that payroll subsidiary staff and interns/secondees "
                 "are employees, NOT external guests); freelancer|contractor|agency_staff|partner_staff|"
                 "customer_staff|external_guest are external. The counts must sum to the TRUE total number of "
                 "people present, not just the ones named individually -- do not omit unnamed colleagues from "
                 "the count. The tool classifies client-vs-employee and computes the total from these counts "
                 "itself -- do not decide that yourself and pass is_client_meal or external_attendees directly "
                 "unless attendee_role_counts genuinely cannot be determined.")

# ---------- 7. Prompt addition for explicit missing-info ----------

EXTRA_PROMPT_V59 = (" If the note explicitly states that a fact is not known, not available, or not yet obtained (e.g. "
                     "\"I don't have the count\", \"not yet confirmed\", \"I have not got the total number of X\"), "
                     "that fact is missing -- pass None/omit it to the compliance tool rather than inventing a number, "
                     "even if you can count some of the people or items named elsewhere in the note. Counting only the "
                     "people explicitly named is not the same as knowing the total the note says it does not have. "
                     "Never substitute your own guess, or a partial count, for a fact the note says outright is unknown."
                     " When counting meal attendees: always include yourself as one of the attendees, even though the "
                     "note describes itself in the first person and may not explicitly say 'myself' next to every "
                     "number. Watch for phrasing like 'myself and N colleagues, one of whom is X and another who is Y' "
                     "-- X and Y are describing which two of those N colleagues they are, not additional people on top "
                     "of N. Count each person actually present exactly once, including yourself, no more and no fewer."
                     " Call check_evidence_consistency for every claim before concluding a decision -- it checks whether "
                     "the note actually describes the same kind of expense as the bill's own category."
                     " For an airfare claim, call check_airfare_compliance instead of judging the cabin class yourself. "
                     "For a training claim, call check_training_compliance instead of judging the annual cap yourself.")


def build_tools_v59(case: dict):
    specs, case_tools = V.specs_and_tools_47(case)
    specs = {**specs, "check_evidence_consistency": EVIDENCE_SPEC, "check_airfare_compliance": AIRFARE_SPEC,
              "check_training_compliance": TRAINING_SPEC, "check_mileage_compliance": MILEAGE_SPEC, "check_software_compliance": SOFTWARE_SPEC,
              "check_meal_compliance": MEAL_SPEC_V59}
    case_tools = {**case_tools, "check_hotel_compliance": make_check_hotel_compliance_v56(case), "check_evidence_consistency": make_check_evidence_consistency(case),
                  "check_workflow_compliance": make_check_workflow_compliance_fixed(case), "check_airfare_compliance": make_check_airfare_compliance(case),
                  "check_training_compliance": make_check_training_compliance(case), "check_mileage_compliance": make_check_mileage_compliance(case),
                  "check_software_compliance": make_check_software_compliance(case), "check_meal_compliance": make_check_meal_compliance_v59(case)}
    system = V.SYSTEM_47 + EXTRA_PROMPT_V59
    return specs, case_tools, system


_GOV_RECIPIENT_RE = re.compile(r"state-owned|statutory|authority|ministry|public university|public hospital|public.sector|municipal|agency", re.I)


def gate_gift_recipient(case: dict, result: dict) -> dict:
    """check_gift_compliance trusts whatever recipient_type the model passes, with no code-level check --
    X2-054 (a gift to 'Kanto Regional Development Authority', in a Japanese-language note) showed the model
    pass recipient_type='EXTERNAL' in one run and the correct 'GOVERNMENT' in another, for the identical
    input, at temperature=0 -- the same run-to-run non-determinism observed on X2-061/X2-066, just showing
    up in a different tool with no gate protecting it. Enforces the same government-recipient keyword check
    rules_text.py's own parser uses, directly against the note text, regardless of what the model passed."""
    f = RT.parse(case)
    if f.get("expense_type") == "GIFT" and result.get("decision") == "APPROVE" and _GOV_RECIPIENT_RE.search(case["employee_description"]):
        return {**result, "decision": "REJECT", "policy_evidence": ["GIFT-1.2", "GIFT-1.3"],
                "explanation": result.get("explanation", "") + " [Exp 59 gate: overridden from APPROVE -- the note names a government/statutory/public-sector recipient, a prohibited gift recipient.]"}
    return result


def gate_evidence_consistency(case: dict, result: dict) -> dict:
    """check_evidence_consistency is advisory -- the model is told to call it, but a live run showed it
    doesn't always do so (X2-061 approved outright on a run where the tool was never invoked). Enforce the
    same check unconditionally here, the same way the disposition gate enforces a tool result the model
    did consult: this doesn't depend on the model's own tool-calling behavior at all."""
    f = RT.parse(case)
    if result.get("decision") == "APPROVE" and conflict_detected(case["employee_description"], f.get("expense_type")):
        return {**result, "decision": "REQUEST_INFORMATION", "policy_evidence": ["GEP26-4.1", "GEP26-1.2"], "missing_fields": ["correct_business_purpose"],
                "explanation": result.get("explanation", "") + " [Exp 59 gate: overridden from APPROVE -- the note describes a different expense type than the bill's own category.]"}
    return result


def run_one_v59(case, tag: str = "EXP59"):
    specs, case_tools, system = build_tools_v59(case)
    raw = agent.run(case, system_template=system, specs=specs, case_tools=case_tools, max_steps=8, tag=tag)
    result = V.gate_disposition(V.gate_approve(raw))
    result = gate_evidence_consistency(case, result)
    result = gate_gift_recipient(case, result)
    return result


if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else "X2-066"
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    c = cases[cid]
    r = run_one_v59(c, "EXP59_SINGLE")
    print(cid, "->", r["decision"], "|", r.get("explanation"))
    for i, step in enumerate(r["trace"], 1):
        print(f"turn {i}: {step['tool']} {step['args']} -> {json.dumps(step['observation'])[:250]}")
