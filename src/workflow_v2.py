"""Experiment 18: fixed enterprise workflow for V2. Same policy math as src/rules_v2.py, but every enterprise lookup goes
through src/tools.py's typed tools (call_tool) instead of touching data/03_enterprise_data directly. Branching is only
if/else on tool observations and note-parsed facts; no model is involved. Policy constants (ceiling tables, thresholds)
are reused from rules_v2 as module-level constants -- they are transcribed policy text, not enterprise data, so importing
them is not "table access". Guardrails: max call count, call de-duplication, per-call timeout (in call_tool), and
escalate-on-tool-failure instead of guessing."""
from __future__ import annotations
import time
from . import rules_text as RT, rules_v2 as RV, tools

TYPES = RV.TYPES


class StepCapExceeded(RuntimeError):
    pass


class Trace:
    """Tool caller with guardrails: identical calls are de-duplicated (served from the first observation), a hard step cap
    stops the run, and any failed call is recorded so the workflow escalates instead of guessing."""

    def __init__(self, max_calls: int = 10, timeout_s: float = 5.0):
        self.calls, self.max_calls, self.timeout_s, self.seen, self.failed, self.deduped = [], max_calls, timeout_s, {}, [], 0

    def __call__(self, name, **args):
        key = (name, tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in args.items())))
        if key in self.seen:
            self.deduped += 1
            return self.seen[key]
        if len(self.calls) >= self.max_calls:
            raise StepCapExceeded(f"step cap {self.max_calls} reached")
        t0 = time.perf_counter()
        r = tools.call_tool(name, args, timeout_s=self.timeout_s)
        self.seen[key] = r
        if not r["ok"]:
            self.failed.append({"tool": name, "error": r["error"]})
        self.calls.append({"tool": name, "args": args, "ok": r["ok"], "found": r["found"], "data": r["data"], "error": r["error"], "latency_ms": round((time.perf_counter() - t0) * 1000, 3)})
        return r


def out(decision, policy=(), missing=(), reason=""):
    return {"decision": decision, "policy_evidence": list(policy), "missing_fields": list(missing), "reason": reason, "manual_review_required": decision == "ESCALATE"}


def sgd_amount(c, call):
    b = c["bill"]; y, m = int(c["transaction_date"][:4]), int(c["transaction_date"][5:7])
    if b["currency"] == "SGD":
        return b["total"]
    r = call("get_fx_rate", currency=b["currency"], year=str(y), month=str(m))
    return b["total"] * float(r["data"]["sgd_per_unit"]) if r["found"] else b["total"]


def grade(c, call):
    r = call("get_employee_profile", employee_id=c["employee_id"])
    return int(r["data"]["grade"][1:]) if r["found"] else 1


def need_level(c, call, amount_sgd):
    y = RV.Y(c); reg = RV.region(c)
    if amount_sgd > 5000:
        return "FINANCE"
    if amount_sgd > (1500 if y < 2 else 2000):
        return "DIRECTOR"
    local = c["bill"]["total"] > RV.LOCAL_MGR[reg][y] if reg in ("IN", "JP") else amount_sgd > 500
    return "MANAGER" if (local or amount_sgd > 500) else "NONE"


def check_approval(c, call, need, types, amount_sgd):
    """Calls the resolved validate_approval tool (Exp 17) instead of interpreting a raw approval row."""
    if need == "NONE":
        return None
    r = call("validate_approval", expense_id=c["case_id"], required_level=need, required_types=list(types), transaction_date=c["transaction_date"], amount_sgd=amount_sgd)
    d = r["data"]
    if d["valid"]:
        return None
    if d["reason_code"] == "NO_APPROVAL_ON_FILE":
        return out("REQUEST_INFORMATION", ["APR-3.1"], ["manager_approval" if need == "MANAGER" else "director_approval"], d["reason"])
    if d["reason_code"] in ("WRONG_APPROVAL_TYPE", "DELEGATION_LIMIT_OR_LEVEL", "CONFLICTING_RECORDS"):
        return out("ESCALATE", ["APR-2.2"], (), d["reason"])
    return out("REQUEST_INFORMATION", ["APR-2.1"], ["valid_approval"], d["reason"])


def submission(c, call):
    y = c["transaction_date"][:4]; from . import tables as T; age = T.days_between(c["transaction_date"], c["submission_date"]); r = RV.region(c)
    win, hard = 45, {"2024": 60, "2025": 90, "2026": 75}[y]
    if y == "2024":
        return None if age <= 60 else out("REJECT", ["GEP24-2.1"], (), f"Submitted {age} days after transaction (limit 60).")
    if age <= win:
        return None
    relief = "2025-03-10" <= c["transaction_date"] <= "2025-03-14"
    pol = f"GEP{y[2:]}-2.1"
    if age > hard and not relief:
        return out("ESCALATE", [pol], (), f"Submitted {age} days late; Finance review.")
    a = check_approval(c, call, "MANAGER", ("GENERAL",), sgd_amount(c, call))
    if a:
        return out("REQUEST_INFORMATION", [pol], ["manager_approval"], f"Submitted {age} days after transaction; manager approval needed.")
    return None


def duplicates(c, call):
    b = c["bill"]
    r = call("search_previous_expenses", employee_id=c["employee_id"], merchant=b["merchant"])
    prev = r["data"] or []
    for p in prev:
        if p["bill_number"] == b["bill_number"] or (p["transaction_date"] == c["transaction_date"] and abs(float(p["amount"]) - b["total"]) < 0.005):
            return out("REJECT", ["DUP-1.1"], (), f"Exact duplicate of {p['expense_id']}.")
    from datetime import date
    d0 = date.fromisoformat(c["transaction_date"])
    for p in prev:
        gap = abs((d0 - date.fromisoformat(p["transaction_date"])).days); amt = float(p["amount"]); rel = abs(amt - b["total"]) / amt if amt else 9
        if gap <= 3 and rel <= 0.02:
            return out("REQUEST_INFORMATION", ["DUP-1.2"], ["duplicate_clarification"], f"Possible duplicate of {p['expense_id']}.")
    return None


def split(c, call, f, amount_sgd):
    """DUP-2.1/2.2: related purchases (same employee, merchant, project, within 3 days, differing >2%) are combined for the approval threshold."""
    from datetime import date
    b = c["bill"]; r = call("search_previous_expenses", employee_id=c["employee_id"], merchant=b["merchant"])
    prev = r["data"] or []; d0 = date.fromisoformat(c["transaction_date"]); comb = amount_sgd; found = False
    for p in prev:
        if p.get("project_id") != c.get("project_id"):
            continue
        gap = abs((d0 - date.fromisoformat(p["transaction_date"])).days); amt = float(p["amount"])
        if gap <= 3 and abs(amt - b["total"]) / max(amt, 1e-9) > 0.02:
            fx = call("get_fx_rate", currency=p["currency"], year=p["transaction_date"][:4], month=str(int(p["transaction_date"][5:7]))) if p["currency"] != "SGD" else None
            rate = float(fx["data"]["sgd_per_unit"]) if fx and fx["found"] else 1.0
            comb += amt * rate; found = True
    if not found:
        return None
    reg = RV.region(c); thr = RV.LOCAL_MGR[reg][RV.Y(c)] * (1.0) if reg in ("IN", "JP") else 500
    if comb > thr >= amount_sgd:
        r = call("validate_approval", expense_id=c["case_id"], required_level="MANAGER", required_types=["COMBINED_SPEND"], transaction_date=c["transaction_date"], amount_sgd=comb)
        d = r["data"]
        if not d["approval_present"]:
            return out("REQUEST_INFORMATION", ["DUP-2.1", "DUP-2.2"], ["combined_spend_approval"], "Combined amount crosses an approval threshold; approval absent.")
        if d["approval_type"] != "COMBINED_SPEND":
            return out("ESCALATE", ["DUP-2.2"], (), "Approval of another type conflicts with combined spend.")
    return None



def meal(c, call, f, amount_sgd):
    b, desc = c["bill"], c["employee_description"]; y = RV.Y(c); r = RV.region(c); yr = int(c["transaction_date"][:4]); d = c["transaction_date"]
    n = f.get("attendees_total"); ext = f.get("external_attendees") or 0; client = f.get("expense_type") == "MEAL_CLIENT" or ext > 0
    alc = f.get("alcohol_amount") or 0
    if r == "IN" and alc:
        return out("REJECT", ["IN-2.4"], (), "Alcohol is not reimbursable in India.")
    if alc and not client:
        return out("REJECT", ["SG-2.4" if r == "SG" else "JP-2.4"], (), "Alcohol permitted only with external attendees.")
    if alc:
        lim = 0.30 if (r == "JP" or (r == "SG" and yr == 2026)) else 0.35
        if alc > lim * b["total"] + 1e-9:
            return out("REJECT", ["MEAL-2.1"], (), "Alcohol exceeds the share limit.")
    if not n:
        return out("REQUEST_INFORMATION", ["MEAL-3.2"], ["attendee_count"], "Attendee count needed.")
    if client and ext > 0 and not f.get("external_names"):
        return out("REQUEST_INFORMATION", ["MEAL-1.2"], ["external_attendee_names"], "External attendee names required.")
    tip = f.get("tip_amount") or 0
    if r == "JP" and tip > 0:
        return out("REJECT", ["JP-2.5"], (), "Gratuities not reimbursable in Japan.")
    ceil = (RV.CLIENT_MEAL if client else RV.EMP_MEAL)[r][y]
    if b["total"] / n > ceil + 1e-9:
        return out("REJECT", ["MEAL-1.2" if client else "MEAL-1.1"], (), f"Per-person spend {b['total'] / n:.0f} exceeds ceiling {ceil}.")
    pre = b["total"] - tip
    if tip and pre > 0 and tip > 0.15 * pre and r != "JP":
        a = check_approval(c, call, "MANAGER", ("GENERAL", "ENTERTAINMENT"), amount_sgd)
        if a:
            return out("REQUEST_INFORMATION", ["MEAL-2.2"], ["manager_approval"], "Gratuity above 15% needs manager approval.")
    return None


def airfare(c, call, f, amount_sgd):
    y = int(c["transaction_date"][:4]); g = grade(c, call)
    tr = travel_valid(c, call, f.get("departure_date") or c["transaction_date"])
    if not tr:
        return out("REQUEST_INFORMATION", ["TRV-1.1"], ["approved_travel_request"], "No approved travel request.")
    cabin, hrs = f.get("cabin"), f.get("flight_hours") or 0
    pe_hours = 5.5 if (y == 2025 and c["transaction_date"] >= "2025-04-01") else 6
    ok = cabin == "ECONOMY" or (cabin == "PREMIUM_ECONOMY" and hrs > pe_hours and g >= 4) or (cabin == "BUSINESS" and (g >= 7 or (g >= 6 and hrs > 9)))
    if not ok:
        exc_id = f.get("exception_ref") or tr.get("exception_id")
        st = exception_status(c, call, "AIR-2.2", exc_id)
        if st == "WRONG_SCOPE":
            return out("ESCALATE", ["EXC-2.1"], (), "Exception names a different policy or employee.")
        if st == "MISSING_ID":
            return out("REQUEST_INFORMATION", ["EXC-2.1"], ["exception_reference"], "Cited exception identifier does not exist.")
        if st != "VALID":
            return out("REJECT", ["AIR-2.1", "AIR-2.2"], (), f"{cabin} not permitted for grade G{g}, {hrs}h.")
    if f.get("booked_date") and f.get("departure_date"):
        from . import tables as T
        if T.days_between(f["booked_date"], f["departure_date"]) < 14:
            a = check_approval(c, call, "MANAGER", ("TRAVEL", "GENERAL"), amount_sgd)
            if a:
                return out("REQUEST_INFORMATION", ["AIR-3.1"], ["manager_approval"], "Booked fewer than 14 days ahead; approval needed.")
    return None


def gift(c, call, f, amount_sgd):
    b = c["bill"]; y = RV.Y(c); r = RV.region(c); d = c["transaction_date"]
    if f.get("recipient_type") in ("GOVERNMENT",) or f.get("gift_form") in ("CASH", "GIFT_CARD", "VOUCHER", "CASH_EQUIVALENT"):
        return out("REJECT", ["GIFT-1.2", "GIFT-1.3"], (), "Prohibited recipient or cash equivalent.")
    miss = [k for k in ("recipient_name", "recipient_org") if not f.get(k)]
    if miss:
        return out("REQUEST_INFORMATION", ["GIFT-1.4"], miss, "Recipient details missing.")
    cap = RV.GIFT[r][y]
    if b["total"] > cap:
        return out("REJECT", ["GIFT-2.1"], (), f"Gift {b['total']} exceeds per-gift ceiling {cap}.")
    prev = call("search_previous_expenses", employee_id=c["employee_id"])
    prior = sum(float(p["amount"]) for p in (prev["data"] or []) if p.get("category") == "GIFT" and p.get("counterparty") == f.get("recipient_org") and p["transaction_date"][:4] == d[:4])
    if prior + b["total"] > RV.GIFT_ANNUAL[r][y]:
        return out("REJECT", ["GIFT-2.2"], (), "Annual ceiling for the recipient organisation exceeded.")
    return None


def telecom(c, call, f, amount_sgd):
    r = RV.region(c); y = RV.Y(c); m = f.get("billing_month") or c["transaction_date"][:7]
    prev = call("search_previous_expenses", employee_id=c["employee_id"])
    prior = sum(float(p["amount"]) for p in (prev["data"] or []) if p.get("category") == "TELECOM" and p["transaction_date"][:7] == m)
    if prior + c["bill"]["total"] > RV.TELECOM[r][y] + 1e-9:
        return out("REJECT", ["TEL-2.1"], (), "Monthly telecom ceiling would be exceeded.")
    return None


def training(c, call, f, amount_sgd):
    if not f.get("learning_plan_id"):
        return out("REQUEST_INFORMATION", ["TRN-2.4"], ["learning_plan_id"], "Learning plan identifier required.")
    return None


def mileage(c, call, f, amount_sgd):
    r = RV.region(c); y = RV.Y(c)
    calc = RV.MILEAGE[r][y] * (f.get("distance_km") or 0)
    if c["bill"]["total"] > calc + 0.005:
        return out("REJECT", ["GRD-4.1"], (), f"Claim exceeds calculated {calc:.2f}.")
    return None


def ground(c, call, f, amount_sgd):
    if not f.get("origin") or not f.get("destination"):
        return out("REQUEST_INFORMATION", ["GRD-1.1"], ["origin", "destination"], "Route details missing.")
    home = "HOME" in (f.get("origin_type"), f.get("destination_type"))
    if home:
        late = (f.get("departure_time") or "00:00") > "22:00" and (f.get("activity_end_time") or "00:00") > "21:30"
        if not late:
            return out("REJECT", ["GRD-1.2"], (), "Commute is not reimbursable.")
    return None


def car(c, call, f, amount_sgd):
    if grade(c, call) < 4:
        return out("REJECT", ["GRD-3.1"], (), "Car rental requires grade G4+.")
    a = check_approval(c, call, "MANAGER", ("GENERAL", "TRAVEL"), amount_sgd)
    return a


def equipment(c, call, f, amount_sgd):
    if amount_sgd > 1000:
        return out("REJECT", ["SWE-2.1"], (), "Equipment above SGD 1000 is a capital asset.")
    if amount_sgd > 300:
        a = check_approval(c, call, "MANAGER", ("GENERAL",), amount_sgd)
        if a:
            return a
    return None


def travel_valid(c, call, on):
    r = call("get_travel_request", employee_id=c["employee_id"], date=on)
    return r["data"] if r["found"] and r["data"]["status"] == "APPROVED" else None


def exception_status(c, call, policy_id, exc_id):
    if not exc_id:
        return "NONE"
    r = call("get_exception_record", exception_id=exc_id)
    if not r["found"]:
        return "MISSING_ID"
    e = r["data"]
    if e["employee_id"] != c["employee_id"] or e["policy_id"] != policy_id:
        return "WRONG_SCOPE"
    if e["status"] != "APPROVED" or not (e["valid_from"] <= c["transaction_date"] <= e["valid_to"]):
        return "INVALID"
    return "VALID"


def hotel(c, call, f, amount_sgd):
    b = c["bill"]; y = int(c["transaction_date"][:4])
    tr = travel_valid(c, call, c["transaction_date"])
    if not tr:
        return out("REQUEST_INFORMATION", ["TRV-1.1"], ["approved_travel_request"], "No approved travel request covers the transaction date.")
    if not f.get("nights"):
        return out("REQUEST_INFORMATION", ["TRV-4.2"], ["number_of_nights"], "Number of nights not stated.")
    loc = RV.TIER.get(f.get("city") or b["city"])
    tier_vals = RV.HOTEL[y].get(loc)
    if tier_vals is None:
        return out("ESCALATE", ["GEP26-4.1"], (), "Hotel location tier could not be determined.")
    ceil = tier_vals[RV.band(grade(c, call))]
    if loc == "JP-TOKYO" and y == 2025 and c["transaction_date"] >= "2025-07-01":
        ceil = RV.rnd(ceil * 1.05)
    if loc == "IN-T1" and y == 2026 and c["transaction_date"] >= "2026-04-01":
        ceil = RV.rnd(ceil * 1.06)
    nights = f["nights"]; rate = b["total"] / nights
    if nights > 14 and y >= 2025:
        ceil *= 0.9
    ev = f.get("conference_ref") or tr.get("event_id")
    if ev:
        cf = call("get_conference_registration", event_id=ev)
        if cf["found"] and cf["data"]["employee_id"] == c["employee_id"] and cf["data"]["registration_status"] == "REGISTERED" and cf["data"]["official_partner_hotel"] == b["merchant"]:
            up = ceil * (1.2 if y < 2026 else 1.25)
            if rate <= up + 1e-9:
                return None
    if rate <= ceil + 1e-9:
        return None
    exc_id = f.get("exception_ref") or tr.get("exception_id")
    st = exception_status(c, call, "TRV-6.1", exc_id)
    if st == "VALID":
        return None
    if st == "WRONG_SCOPE":
        return out("ESCALATE", ["EXC-2.1"], (), "Exception names a different policy or employee.")
    if st == "MISSING_ID":
        return out("REQUEST_INFORMATION", ["EXC-2.1"], ["exception_reference"], "Cited exception identifier does not exist.")
    return out("REJECT", ["TRV-6.1"], (), f"Nightly rate {rate:.0f} exceeds ceiling {ceil:.0f}; no valid exception.")


def software(c, call, f, amount_sgd):
    if not f.get("business_owner"):
        return out("REQUEST_INFORMATION", ["SWE-1.1"], ["business_owner"], "Named business owner required.")
    if amount_sgd > 500:
        need = "MANAGER"
        a = check_approval(c, call, need, TYPES.get("SOFTWARE", ("GENERAL",)), amount_sgd)
        if a:
            return a
    if amount_sgd > 1000 and c["transaction_date"] >= "2026-02-01":
        pj = call("get_project_status", project_id=c.get("project_id"))
        active = pj["found"] and pj["data"]["project_status"] == "ACTIVE"
        cb = None
        if pj["found"]:
            cb = call("get_cost_centre_budget", cost_centre=pj["data"]["cost_centre"], year=c["transaction_date"][:4])
        open_budget = bool(cb and cb["found"] and cb["data"]["status"] == "OPEN")
        if not active or not open_budget:
            return out("ESCALATE", ["SWE-1.2", "CIRC-26-02"], (), "Project not active or cost centre not open.")
    return None


def conference(c, call, f, amount_sgd=None):
    ref = f.get("conference_ref")
    r = call("get_conference_registration", event_id=ref) if ref else {"found": False}
    if not r["found"] or r["data"]["employee_id"] != c["employee_id"] or r["data"]["registration_status"] != "REGISTERED":
        return out("REJECT", ["TRN-1.1"], (), "No REGISTERED conference entry for the employee.")
    return None


def merchant_restricted(c, call):
    m = call("get_merchant_metadata", merchant_name=c["bill"]["merchant"])
    if not m["found"]:
        return None
    risk = m["data"].get("risk_class")
    if risk == "RESTRICTED_PROHIBITED":
        return out("REJECT", ["CARD-3.1"], (), "Prohibited merchant class.")
    if risk == "RESTRICTED_REVIEW":
        return out("ESCALATE", ["CARD-3.1"], (), "Restricted merchant requires Finance review.")
    return None


CATEGORY_TOOLS = {"HOTEL": hotel, "SOFTWARE": software, "CONFERENCE_FEE": conference, "MEAL_CLIENT": meal, "MEAL_EMPLOYEE": meal, "AIRFARE": airfare,
                   "GIFT": gift, "TELECOM": telecom, "TRAINING": training, "MILEAGE": mileage, "GROUND_TRANSPORT": ground, "CAR_RENTAL": car, "EQUIPMENT": equipment}


def decide(c: dict, trace: "Trace" = None) -> dict:
    call = trace or Trace()
    try:
        d = _decide(c, call)
    except StepCapExceeded as e:
        d = out("ESCALATE", ["GEP26-4.1"], (), f"Step cap reached ({e}); escalated instead of guessing.")
    if call.failed and d["decision"] != "ESCALATE":
        d = out("ESCALATE", ["GEP26-4.1"], (), f"Lookup failed ({call.failed[0]['tool']}: {call.failed[0]['error']}); escalated instead of guessing.")
    d["trace"] = call.calls
    d["tool_calls"] = len(call.calls)
    d["deduped_calls"] = call.deduped
    d["step_cap_hit"] = isinstance(getattr(call, "_step_cap_hit", None), bool) and call._step_cap_hit
    return d


def _decide(c: dict, call: "Trace") -> dict:
    b = c["bill"]
    if not (b.get("merchant") and b.get("total") and c["employee_description"].strip()):
        return out("REQUEST_INFORMATION", ["GEP26-1.3"], ["business_purpose"], "Mandatory documentation missing.")
    r = merchant_restricted(c, call)
    if r:
        return r
    if b["merchant_category"] in ("CONSUMER_SERVICE", "STREAMING", "FITNESS"):
        return out("REJECT", ["CARD-2.1"], (), "Consumer service presumed personal.")
    f = RT.parse(c)
    sub = submission(c, call)
    if sub:
        return sub
    dup = duplicates(c, call)
    if dup:
        return dup
    et = f.get("expense_type"); amount_sgd = sgd_amount(c, call)
    spl = split(c, call, f, amount_sgd)
    if spl:
        return spl
    per = CATEGORY_TOOLS.get(et)
    if per:
        r = per(c, call, f, amount_sgd)
        if r:
            return r
    lvl = need_level(c, call, amount_sgd)
    if et not in ("SOFTWARE", "EQUIPMENT", "CAR_RENTAL") and lvl == "FINANCE":
        return out("ESCALATE", ["APR-1.3"], (), "Above SGD 5000 requires Finance review.")
    if et not in ("SOFTWARE", "EQUIPMENT", "CAR_RENTAL") and lvl != "NONE":
        r = check_approval(c, call, lvl, TYPES.get(et, ("GENERAL",)), amount_sgd)
        if r:
            return r
    return out("APPROVE", [], (), "No rule triggered; all applicable checks pass.")
