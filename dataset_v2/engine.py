"""ExpenseGuard V2 - reference policy engine. Deterministically derives the ground truth (decision, controlling clauses, missing fields, tool path) for a claim
from the claim, the enterprise state and the schedules in world.py. It is evaluator-side code: nothing here ships to runtime systems."""
from __future__ import annotations
import re
from . import world as W

DOCS_CONFLICT = {"meal": ["dinner", "lunch", "breakfast", "meal", "restaurant", "catering", "supper"], "transport": ["taxi", "cab", "ride", "grab", "gojek", "uber", "transfer", "ola"],
                 "hotel": ["hotel", "accommodation", "lodging", "room", "stay"]}
BILL_FAMILY = {"RESTAURANT": "meal", "HOTEL": "hotel", "RIDE_HAIL": "transport"}
RISK_CATEGORIES = {"ENTERTAINMENT_VENUE", "PREPAID_CARD_RESELLER"}
LEVEL = {"MANAGER": 1, "DIRECTOR": 2, "FINANCE": 3}
MEALS = {"MEAL_EMPLOYEE", "MEAL_CLIENT", "ENTERTAINMENT"}


class State:
    """Enterprise tables (lists of dicts) with the same lookups the runtime tools expose."""

    def __init__(self, t): self.t = t

    def _one(self, table, key, val): return next((r for r in self.t[table] if r[key] == val), None)

    def get_employee_profile(self, employee_id): return self._one("employees", "employee_id", employee_id)
    def get_travel_request(self, employee_id, date):
        return next((r for r in self.t["travel_requests"] if r["employee_id"] == employee_id and r["start_date"] <= date <= r["end_date"]), None)
    def get_manager_approval(self, expense_id): return [r for r in self.t["manager_approvals"] if r["expense_id"] == expense_id]
    def get_exception_record(self, exception_id): return self._one("policy_exceptions", "exception_id", exception_id)
    def get_project_status(self, project_id): return self._one("project_registry", "project_id", project_id)
    def search_previous_expenses(self, employee_id, merchant=None): return [r for r in self.t["previous_expenses"] if r["employee_id"] == employee_id and (not merchant or r["merchant"] == merchant)]
    def get_conference_registration(self, event_id): return self._one("conference_registry", "event_id", event_id)
    def get_merchant_metadata(self, merchant_name): return self._one("merchant_directory", "merchant_name", merchant_name)
    def get_approval_delegation(self, delegation_id): return self._one("approval_delegations", "delegation_id", delegation_id)
    def get_cost_centre_budget(self, cost_centre, year): return next((r for r in self.t["cost_centre_budgets"] if r["cost_centre"] == cost_centre and int(r["year"]) == int(year)), None)
    def fx(self, ccy, d):
        y, m = int(d[:4]), int(d[5:7])
        return next(float(r["sgd_per_unit"]) for r in self.t["fx_rates"] if r["year"] == y and r["month"] == m and r["currency"] == ccy)


class Done(Exception):
    pass


class Run:
    def __init__(self, S, c):
        self.S, self.c = S, c
        self.calls, self.needed, self.ctrl, self.ctx, self.facts, self.branch = [], [], [], [], {}, []
        self.res, self.cache, self.appr_level = None, {}, 0

    def call(self, name, **args):
        key = (name, tuple(sorted(args.items())))
        if key not in self.cache:
            self.calls.append({"tool": name, "args": args})
            self.cache[key] = getattr(self.S, name)(**args)
        return self.cache[key]

    def need(self, name):
        if name not in self.needed: self.needed.append(name)

    def cite(self, ids, ctx=()):
        for i in ([ids] if isinstance(ids, str) else ids):
            if i not in self.ctrl: self.ctrl.append(i)
        for i in ([ctx] if isinstance(ctx, str) else ctx):
            if i not in self.ctx and i not in self.ctrl: self.ctx.append(i)

    def done(self, decision, reason, missing=()):
        self.res = dict(decision=decision, reason=reason, missing_fields=list(missing))
        raise Done


def sgd_of(R, amount, ccy, d): return amount * R.S.fx(ccy, d)


def mgr_threshold(R, reg, y, d):
    """Applicable manager-approval threshold in SGD equivalent (stricter of the global SGD tier and the regional local-currency tier)."""
    g = W.APPROVAL_SGD["manager"][y]
    if reg in W.REGIONAL_MGR:
        loc = W.REGIONAL_MGR[reg][y]
        ccy = W.REGION[reg]["ccy"]
        loc_sgd = loc * R.S.fx(ccy, d)
        if loc_sgd < g:
            return loc_sgd, [f"{reg}-6.1"], ["APR-1.1"]
    return g, ["APR-1.1"], []


def required_level(R, sgd, reg, y, d):
    fin, dirn = W.APPROVAL_SGD["finance"][y], W.APPROVAL_SGD["director"][y]
    thr, ctrl, ctx = mgr_threshold(R, reg, y, d)
    if sgd > fin: return "FINANCE", ["APR-1.3"], []
    if sgd > dirn: return "DIRECTOR", ["APR-1.2"], []
    if sgd > thr: return "MANAGER", ctrl, ctx
    return None, [], []


def check_approval(R, level, types, sgd, required_for, ctrl_ids):
    """Approval validity per APR-2.1 and delegation per APR-4.x. Returns None if a valid approval covers the expense; otherwise finishes the run."""
    c = R.c; t = c["transaction_date"]; R.appr_level = max(R.appr_level, LEVEL[level])
    recs = R.call("get_manager_approval", expense_id=c["case_id"]); R.need("get_manager_approval")
    R.cite(ctrl_ids, ["APR-2.1"])
    ok_types = set(types) | {"GENERAL"}
    good = [r for r in recs if r["employee_id"] == c["employee_id"] and r["approval_type"] in ok_types]
    if not good:
        if recs:
            R.cite(["APR-2.2", "APR-1.3"]); R.branch.append("approval record of a different type"); R.done("ESCALATE", "An approval exists but its type does not cover this expense; conflicting evidence goes to Finance.")
        R.cite("APR-3.1"); R.done("REQUEST_INFORMATION", f"No valid approval record for {required_for}.", ["manager_approval"])
    r = good[0]
    if not (r["start_date"] <= t <= r["end_date"]) or r["status"] not in ("APPROVED", "DELEGATED"):
        R.cite("APR-3.1"); R.done("REQUEST_INFORMATION", "Approval record does not cover the transaction date or is not approved.", ["manager_approval"])
    if r["status"] == "DELEGATED":
        R.branch.append("approval status DELEGATED -> delegation record")
        d = R.call("get_approval_delegation", delegation_id=r["delegation_id"]); R.need("get_approval_delegation"); R.cite(["APR-4.1"], ["APR-4.2"])
        if not d or not (d["start_date"] <= t <= d["end_date"]):
            R.cite("APR-4.2"); R.done("REQUEST_INFORMATION", "Delegation is outside its validity period; a valid approval is requested.", ["valid_approval"])
        if sgd > float(d["max_amount_sgd"]) or LEVEL[d["delegate_level"]] < LEVEL[level]:
            R.cite("APR-4.2"); R.done("ESCALATE", "Delegation is valid but the amount exceeds its limit or the delegate holds a lower level than required.")
        return None
    if LEVEL[r["approver_level"]] < LEVEL[level]:
        R.cite("APR-3.1"); R.done("REQUEST_INFORMATION", f"Approval is at level {r['approver_level']}; {level} is required.", ["approval_at_required_level"])
    return None


def project_chain(R, sgd):
    """Charge-to-project claims: project status, optional parent project, cost-centre budget (APR-5.x)."""
    c = R.c; y = int(c["transaction_date"][:4])
    p = R.call("get_project_status", project_id=c["project_id"]); R.need("get_project_status"); R.cite("APR-5.2")
    if not p or p["project_status"] != "ACTIVE":
        R.cite("APR-5.1"); R.done("ESCALATE", "Project is not active; charging it needs Finance review.")
    cc = p["cost_centre"]
    if p.get("parent_project_id"):
        R.branch.append("project has a parent project -> parent lookup")
        par = R.call("get_project_status", project_id=p["parent_project_id"])
        if not par or par["project_status"] != "ACTIVE":
            R.cite("APR-5.1"); R.done("ESCALATE", "Parent project is not active.")
        cc = par["cost_centre"]
    b = R.call("get_cost_centre_budget", cost_centre=cc, year=str(y)); R.need("get_cost_centre_budget"); R.cite("APR-5.1")
    if b["status"] == "FROZEN" and sgd > W.CC_FROZEN_MIN_SGD:
        R.branch.append("cost centre FROZEN"); R.done("ESCALATE", "Cost centre is frozen; Finance review required.")
    if float(b["budget_sgd"]) - float(b["committed_sgd"]) < sgd:
        R.branch.append("remaining budget below claim"); R.done("REQUEST_INFORMATION", "Remaining budget is smaller than the claim; budget-owner approval requested.", ["budget_owner_approval"])


def evaluate(c: dict, S: State) -> dict:
    R = Run(S, c)
    try:
        _eval(R)
    except Done:
        pass
    r = R.res
    return dict(expected_decision=r["decision"], reason=r["reason"], missing_fields=r["missing_fields"], controlling_clause_ids=R.ctrl, context_clause_ids=R.ctx,
                tool_path=R.calls, minimum_required_tools=R.needed, branch_trigger="; ".join(R.branch), facts=R.facts)


def _hotel(R):
    S, c = R.S, R.c
    b, f = c["bill"], c["form"]; t = c["transaction_date"]; y = int(t[:4]); total = float(b["total"])
    prof = R.call("get_employee_profile", employee_id=c["employee_id"]); R.need("get_employee_profile")
    band = W.band(int(prof["grade"][1:])); loc = W.CITY_LOC[f["city"]]
    base, ctrl, cx = W.HOTEL.get((loc, band), t); R.cite(ctrl + ["TRV-2.1"], cx + ["TRV-1.1"])
    tr = R.call("get_travel_request", employee_id=c["employee_id"], date=t); R.need("get_travel_request")
    if not tr or tr["status"] != "APPROVED": R.cite(["TRV-1.1", "TRV-1.2"]); R.done("REQUEST_INFORMATION", "No approved travel request covers the stay.", ["approved_travel_request"])
    nightly = total / int(f["nights"]); R.facts["nightly_rate"] = round(nightly, 2)
    ls = W.LONG_STAY_FACTOR / 100 if (int(f["nights"]) > W.LONG_STAY_NIGHTS and y >= 2025) else 1.0
    if ls != 1.0: R.cite("TRV-4.1")
    if nightly <= base * ls: return
    ev = f.get("conference_ref") or tr.get("event_id"); ex = f.get("exception_ref") or tr.get("exception_id")
    if not f.get("conference_ref") and tr.get("event_id"): R.branch.append("travel record links a conference event")
    if not f.get("exception_ref") and tr.get("exception_id"): R.branch.append("travel record links an exception")
    if ev:
        cf = R.call("get_conference_registration", event_id=ev); R.need("get_conference_registration"); R.cite(["TRV-5.2", "TRN-1.1"], ["TRV-5.1", "TRN-4.1"])
        if cf and cf["registration_status"] == "REGISTERED" and cf["official_partner_hotel"] == b["merchant"] and cf["employee_id"] == c["employee_id"]:
            up = (100 + W.CONF_UPLIFT[y]) / 100
            if nightly <= base * up * ls: return
    if ex:
        e = R.call("get_exception_record", exception_id=ex); R.need("get_exception_record"); R.cite(["TRV-6.1", "EXC-1.2", "EXC-2.1"], ["EXC-2.2"])
        if not e: R.done("REQUEST_INFORMATION", "Cited exception identifier does not exist.", ["exception_reference"])
        if e["employee_id"] != c["employee_id"] or e["policy_id"] != "TRV-6.1": R.branch.append("exception names a different policy or employee"); R.done("ESCALATE", "Exception scope does not match; Finance decides.")
        if e["status"] != "APPROVED" or not (e["valid_from"] <= t <= e["valid_to"]): R.done("REJECT", "Exception is not approved or does not cover the date.")
        return
    R.cite("TRV-6.1"); R.done("REJECT", "Above the ceiling with no partner uplift or exception.")


def _eval(R):
    S, c = R.S, R.c
    b, f = c["bill"], c["form"]; t = c["transaction_date"]; y = int(t[:4])
    reg = W.COUNTRY_TO_REGION[b["country"]]; ccy = b["currency"]; et = f["expense_type"]; total = float(b["total"])
    sgd = sgd_of(R, total, ccy, t); R.facts["sgd_equivalent"] = round(sgd, 2)
    # -- restricted merchants (merchant directory lookup only for categories that can be restricted)
    if b["merchant_category"] in RISK_CATEGORIES:
        mm = R.call("get_merchant_metadata", merchant_name=b["merchant"]); R.need("get_merchant_metadata"); R.cite(["CARD-3.1"], ["CARD-4.1", "EXC-3.1"])
        if mm and mm["risk_class"] == "RESTRICTED_PROHIBITED": R.branch.append("merchant RESTRICTED_PROHIBITED"); R.done("REJECT", "Merchant risk class is prohibited.")
        if mm and mm["risk_class"] == "RESTRICTED_REVIEW": R.branch.append("merchant RESTRICTED_REVIEW"); R.done("ESCALATE", "Merchant risk class requires Finance review.")
    # -- personal spend
    if et == "OTHER" and b["merchant_category"] == "CONSUMER_SERVICE":
        R.cite(["CARD-1.1", "CARD-2.1"], ["GEP%d-1.2" % (y - 2000)]); R.done("REJECT", "Consumer service presumed personal spend.")
    # -- prohibited by content
    if et == "GIFT":
        if f.get("recipient_type") == "GOVERNMENT": R.cite("GIFT-1.2", ["EXC-3.1", "GIFT-1.5"]); R.done("REJECT", "Gift to a public official or government-affiliated body.")
        if f.get("gift_form") == "CASH_EQUIVALENT": R.cite("GIFT-1.3", ["EXC-3.1", "GIFT-1.6"]); R.done("REJECT", "Cash equivalents are prohibited as gifts.")
    if et in MEALS:
        alc = float(f.get("alcohol_amount") or 0)
        if alc > 0:
            R.cite([], ["MEAL-1.4"])
            if reg == "IN": R.cite(["IN-2.4"], ["MEAL-2.1"]); R.done("REJECT", "Alcohol is not reimbursable in India.")
            if int(f.get("external_attendees") or 0) == 0: R.cite([f"{reg}-2.4"], ["MEAL-2.1"]); R.done("REJECT", "Alcohol is permitted only with external attendees.")
            lim = W.ALCOHOL[reg][y]
            if alc / total * 100 > lim: R.cite([f"{reg}-2.4"], ["MEAL-2.1"]); R.done("REJECT", f"Alcohol share exceeds {lim} percent.")
        if reg == "JP" and float(f.get("tip_amount") or 0) > 0: R.cite("JP-2.5"); R.done("REJECT", "Gratuities are not reimbursable in Japan.")
    # -- documentation completeness
    miss, cl = [], ["GEP%d-1.3" % (y - 2000)]
    def need_f(key, name, clause):
        if f.get(key) in (None, "", 0) and key != "alcohol_amount": miss.append(name); cl.append(clause)
    if et in MEALS: need_f("attendees_total", "attendee_count", "MEAL-3.2")
    if et in ("MEAL_CLIENT", "ENTERTAINMENT"): need_f("external_names", "external_attendee_names", "MEAL-1.2")
    if et == "GROUND_TRANSPORT":
        need_f("origin", "origin", "GRD-1.1"); need_f("destination", "destination", "GRD-1.1")
    if et == "GIFT": need_f("recipient_name", "recipient_name", "GIFT-1.4"); need_f("recipient_org", "recipient_organisation", "GIFT-1.4")
    if et == "TRAINING": need_f("learning_plan_id", "learning_plan_id", "TRN-2.4")
    if et == "CERTIFICATION": need_f("dev_plan_id", "development_plan_id", "TRN-3.1")
    if et == "SOFTWARE": need_f("business_owner", "business_owner", "SWE-1.1")
    if et == "MILEAGE": need_f("distance_km", "distance_km", "GRD-4.1")
    if et == "HOTEL": need_f("nights", "number_of_nights", "TRV-4.2")
    if miss: R.cite(cl); R.done("REQUEST_INFORMATION", "Mandatory fields are missing.", miss)
    # -- evidence conflict between bill and description
    fam = BILL_FAMILY.get(b["merchant_category"])
    words = set(re.findall(r"[a-z]+", c["employee_description"].lower()))
    dfams = {k for k, ws in DOCS_CONFLICT.items() if words & set(ws)}
    if fam and dfams and fam not in dfams:
        R.cite(["GEP%d-4.1" % (y - 2000), "GEP%d-1.2" % (y - 2000)]); R.done("REQUEST_INFORMATION", "The bill and the description describe different expenses.", ["clarified_business_purpose"])
    # -- submission window
    age = W.days_between(t, c["submission_date"]); R.facts["age_days"] = age
    yy = y - 2000
    if y == 2024:
        if age > 60: R.cite(f"GEP{yy}-2.1"); R.done("REJECT", "Submitted after the 60-day window.")
    else:
        ok, appr = W.SUBMIT[y]["ok"], W.SUBMIT[y]["approval"]; regional = False
        if y == 2026 and reg == "IN": ok, appr, regional = W.IN_SUBMIT_2026, 75, True
        if age > ok:
            outage = y == 2025 and W.OUTAGE[0] <= t <= W.OUTAGE[1]
            if age > appr and not outage:
                R.cite([f"GEP{yy}-2.1"] + (["IN-7.1"] if regional else [])); R.done("ESCALATE", "Submitted after the approval tier; Finance escalation.")
            R.cite([f"GEP{yy}-2.1"] + (["IN-7.1"] if regional else []), ["CIRC-25-03"] if outage else [])
            if outage and age > appr: R.branch.append("outage relief")
            if not f.get("approval_ref"): R.done("REQUEST_INFORMATION", "Late claim needs manager approval.", ["manager_approval"])
            check_approval(R, "MANAGER", ["GENERAL"], sgd, "a late claim", [f"GEP{yy}-2.1"])
    # -- history: duplicates and splits (universal check; only decisive when it finds something)
    prev = R.call("search_previous_expenses", employee_id=c["employee_id"], merchant=b["merchant"])
    for p in prev:
        if p["bill_number"] == b["bill_number"] or (p["transaction_date"] == t and float(p["amount"]) == total):
            R.need("search_previous_expenses"); R.cite("DUP-1.1"); R.done("REJECT", f"Exact duplicate of {p['expense_id']}.")
    for p in prev:
        gap = abs(W.days_between(p["transaction_date"], t))
        if p["currency"] == ccy and gap <= W.NEAR_DUP_DAYS and abs(float(p["amount"]) - total) <= W.NEAR_DUP_TOL_PCT / 100 * total and p["category"] == et:
            R.need("search_previous_expenses"); R.cite("DUP-1.2"); R.done("REQUEST_INFORMATION", f"Possible duplicate of {p['expense_id']}.", ["duplicate_clarification"])
    for p in prev:
        gap = W.days_between(p["transaction_date"], t)
        if p["currency"] == ccy and W.RECUR_MIN <= gap <= W.RECUR_MAX and "recurring" in p["business_purpose"].lower() and abs(float(p["amount"]) - total) <= 0.05 * total:
            R.need("search_previous_expenses"); R.cite([], ["DUP-1.3"]); R.branch.append("recurring charge, not a duplicate")
    rel = [p for p in prev if p["currency"] == ccy and p["project_id"] == c["project_id"] and abs(W.days_between(p["transaction_date"], t)) <= W.SPLIT_DAYS
           and abs(float(p["amount"]) - total) > W.NEAR_DUP_TOL_PCT / 100 * total and p["category"] == et and not p["expense_id"].startswith("HIST-")]
    if rel:
        thr, cc_, cx_ = mgr_threshold(R, reg, y, t)
        comb = (total + sum(float(p["amount"]) for p in rel)) * S.fx(ccy, t); R.facts["combined_sgd"] = round(comb, 2)
        if comb > thr >= sgd:
            R.need("search_previous_expenses"); R.branch.append("split: combined amount crosses the manager threshold"); R.cite(["DUP-2.1", "DUP-2.2"] + cc_, cx_)
            recs = R.call("get_manager_approval", expense_id=c["case_id"]); R.need("get_manager_approval")
            good = [r for r in recs if r["approval_type"] == "COMBINED_SPEND" and r["status"] == "APPROVED" and r["start_date"] <= t <= r["end_date"]]
            if good: pass
            elif recs: R.cite("APR-2.2"); R.done("ESCALATE", "Approval of another type conflicts with the related spend.")
            else: R.done("REQUEST_INFORMATION", "Combined spend needs approval; none on file.", ["combined_spend_approval"])
    # ---------------------------------------------------------------- category rules
    if et == "MEAL_EMPLOYEE":
        v, ctrl, cx = W.EMP_MEAL.get(reg, t); pp = total / int(f["attendees_total"]); R.facts["per_person"] = round(pp, 2); R.cite(ctrl, cx + ["MEAL-1.1"])
        if pp > v: R.done("REJECT", "Per-person spend exceeds the employee meal ceiling.")
    elif et == "MEAL_CLIENT":
        v, ctrl, cx = W.CLIENT_MEAL.get(reg, t); pp = total / int(f["attendees_total"]); R.facts["per_person"] = round(pp, 2); R.cite(ctrl, cx + ["MEAL-1.2"])
        if pp > v: R.done("REJECT", "Per-attendee spend exceeds the client meal ceiling.")
    elif et == "ENTERTAINMENT":
        v, ctrl, cx = W.ENTERTAIN.get(reg, t); pe = total / int(f["external_attendees"]); R.facts["per_external"] = round(pe, 2); R.cite(ctrl, cx + ["MEAL-1.3"])
        if pe > v: R.done("REJECT", "Per-external-attendee spend exceeds the entertainment ceiling.")
        if reg == "SG" and total > W.SOFTWARE_TIERS["low"]:
            R.cite("SG-6.2"); check_approval(R, "MANAGER", ["ENTERTAINMENT"], sgd, "entertainment", ["SG-6.2"])
        if reg == "IN" and total > W.REGIONAL_MGR["IN"][y]:
            R.cite("IN-6.2"); check_approval(R, "MANAGER", ["ENTERTAINMENT"], sgd, "entertainment", ["IN-6.2"])
        if reg == "JP" and total > W.JP_ENTERTAIN_COUNTRY_MGR:
            R.cite("JP-6.2"); check_approval(R, "DIRECTOR", ["ENTERTAINMENT"], sgd, "entertainment above the country-manager threshold", ["JP-6.2"])
    elif et == "HOTEL":
        _hotel(R)
    elif et == "AIRFARE":
        prof = R.call("get_employee_profile", employee_id=c["employee_id"]); R.need("get_employee_profile"); g = int(prof["grade"][1:])
        tr = R.call("get_travel_request", employee_id=c["employee_id"], date=f["departure_date"]); R.need("get_travel_request")
        if not tr or tr["status"] != "APPROVED": R.cite(["TRV-1.1"]); R.done("REQUEST_INFORMATION", "No approved travel request covers the flight.", ["approved_travel_request"])
        cabin, hrs = f["cabin"], float(f["flight_hours"]); pe, pc, px = W.AIR_PE_HOURS.get("ALL", t)
        allowed = cabin == "ECONOMY" or (cabin == "PREMIUM_ECONOMY" and hrs > pe and g >= W.AIR["pe_min_grade"]) or (cabin == "BUSINESS" and (g >= W.AIR["biz_min_grade"] or (g >= W.AIR["biz_hours_grade"] and hrs > W.AIR["biz_hours"])))
        R.cite(["AIR-1.1"] if cabin == "ECONOMY" else pc + ["AIR-2.2"] if cabin == "BUSINESS" else pc, px)
        if not allowed:
            ex = f.get("exception_ref") or tr.get("exception_id")
            if not ex: R.done("REJECT", "Cabin not permitted for this grade and flight time.")
            e = R.call("get_exception_record", exception_id=ex); R.need("get_exception_record"); R.cite(["EXC-1.2", "EXC-2.1"])
            if not e: R.done("REQUEST_INFORMATION", "Cited exception identifier does not exist.", ["exception_reference"])
            if e["employee_id"] != c["employee_id"] or e["policy_id"] != "AIR-2.2": R.done("ESCALATE", "Exception scope does not match.")
            if e["status"] != "APPROVED" or not (e["valid_from"] <= f["departure_date"] <= e["valid_to"]): R.done("REJECT", "Exception is not approved or does not cover the date.")
        if W.days_between(f["booked_date"], f["departure_date"]) < W.AIR["advance_days"]:
            check_approval(R, "MANAGER", ["TRAVEL"], sgd, "late-booked airfare", ["AIR-3.1"])
    elif et == "GROUND_TRANSPORT":
        R.cite("GRD-1.1")
        home_dest = f.get("destination_type") == "HOME"; commute = f.get("origin_type") in ("HOME", "OFFICE") and f.get("destination_type") in ("HOME", "OFFICE")
        if commute:
            late = f.get("departure_time") and f["departure_time"] >= W.LATE_NIGHT["start"] and f.get("activity_end_time") and f["activity_end_time"] > W.LATE_NIGHT["activity_end"] and home_dest
            if late: R.cite(["GRD-2.1"], ["GRD-1.2"]); R.done("APPROVE", "Late-night home transport after documented business activity.")
            R.cite("GRD-1.2"); R.done("REJECT", "Commuting is not reimbursable.")
    elif et == "MILEAGE":
        rate, ctrl, cx = W.MILEAGE.get(reg, t); allowed = float(f["distance_km"]) * rate; R.facts["allowed_amount"] = round(allowed, 2); R.cite(ctrl, cx + ["GRD-4.1"])
        if total > allowed + 0.005: R.done("REJECT", "Claim exceeds distance times the mileage rate.")
    elif et == "CAR_RENTAL":
        prof = R.call("get_employee_profile", employee_id=c["employee_id"]); R.need("get_employee_profile"); R.cite("GRD-3.1")
        if int(prof["grade"][1:]) < W.CARD_RENTAL_MIN_GRADE: R.done("REJECT", "Grade below the car rental minimum.")
        check_approval(R, "MANAGER", ["TRAVEL"], sgd, "car rental", ["GRD-3.1"])
    elif et == "GIFT":
        v, ctrl, cx = W.GIFT.get(reg, t); R.cite(ctrl + ["GIFT-2.1"], cx)
        if total > v: R.done("REJECT", "Gift value exceeds the per-gift ceiling.")
        cap, c2, x2 = W.GIFT_ANNUAL.get(reg, t); yr = t[:4]
        earlier = sum(float(p["amount"]) for p in R.call("search_previous_expenses", employee_id=c["employee_id"]) if p["category"] == "GIFT" and p["counterparty"] == f["recipient_org"] and p["transaction_date"][:4] == yr)
        R.need("search_previous_expenses"); R.cite(c2 + ["GIFT-2.2"], x2); R.facts["gifts_ytd_incl_current"] = earlier + total
        if earlier + total > cap: R.done("REJECT", "Annual ceiling for the recipient organisation would be exceeded.")
    elif et == "TRAINING":
        prof = R.call("get_employee_profile", employee_id=c["employee_id"]); R.need("get_employee_profile"); bnd = W.band(int(prof["grade"][1:]))
        cap, ctrl, cx = W.TRAIN_CAP.get(bnd, t)
        hist = [p for p in R.call("search_previous_expenses", employee_id=c["employee_id"]) if p["category"] == "TRAINING" and p["transaction_date"][:4] == t[:4]]; R.need("search_previous_expenses")
        cum = sum(float(p["amount"]) * S.fx(p["currency"], p["transaction_date"]) for p in hist) + sgd; R.facts["training_ytd_sgd"] = round(cum, 2); R.cite(ctrl + ["TRN-2.5"], cx)
        if cum > cap: R.branch.append("annual training ceiling exceeded"); check_approval(R, "DIRECTOR", ["TRAINING"], sgd, "training above the annual ceiling", ["TRN-2.5"])
    elif et == "CERTIFICATION":
        R.cite("TRN-3.1"); check_approval(R, "MANAGER", ["TRAINING"], sgd, "a certification exam", ["TRN-3.1"])
    elif et == "CONFERENCE_FEE":
        cf = R.call("get_conference_registration", event_id=f["conference_ref"]); R.need("get_conference_registration"); R.cite(["TRN-1.1", "TRN-1.2"])
        if not cf: R.done("REQUEST_INFORMATION", "Conference reference does not exist.", ["conference_reference"])
        if cf["registration_status"] != "REGISTERED" or cf["employee_id"] != c["employee_id"]: R.done("REJECT", "Employee is not a registered attendee of an approved event.")
    elif et == "SOFTWARE":
        R.cite("SWE-1.1")
        if f.get("billing") == "ANNUAL_PREPAID" and sgd > W.SOFTWARE_TIERS["prepaid_finance"]: R.cite("SWE-1.3"); R.done("ESCALATE", "Prepaid annual plan above the Finance procurement threshold.")
        if sgd > W.SOFTWARE_TIERS["low"]:
            big = sgd > W.SOFTWARE_TIERS["high"] and t >= "2026-02-01"
            check_approval(R, "MANAGER", ["SOFTWARE"], sgd, "a software subscription", ["SWE-1.2", "CIRC-26-02"] if big else ["SWE-1.1"])
            if big: project_chain(R, sgd)
    elif et == "EQUIPMENT":
        R.cite("SWE-2.1")
        if sgd > W.EQUIP["approval"]: R.done("REJECT", "Capital asset: procure through Finance.")
        if sgd > W.EQUIP["no_approval"]: check_approval(R, "MANAGER", ["GENERAL"], sgd, "equipment", ["SWE-2.1"])
    elif et == "TELECOM":
        cap, ctrl, cx = W.TELECOM.get(reg, t)
        earlier = sum(float(p["amount"]) for p in R.call("search_previous_expenses", employee_id=c["employee_id"]) if p["category"] == "TELECOM" and p["transaction_date"][:7] == t[:7]); R.need("search_previous_expenses")
        R.cite(ctrl + ["TEL-1.2", "TEL-2.1"], cx); R.facts["telecom_month_total"] = earlier + total
        if earlier + total > cap: R.done("REJECT", "Monthly telecom ceiling would be exceeded.")
    # ---------------------------------------------------------------- generic approval tiers (any discretionary expense)
    lvl, ctrl, cx = required_level(R, sgd, reg, y, t)
    if lvl == "FINANCE": R.cite(ctrl); R.done("ESCALATE", "Above the Finance review threshold.")
    if lvl and LEVEL[lvl] > R.appr_level:
        types = ["GENERAL", "ENTERTAINMENT"] if et in MEALS else ["TRAVEL"] if et in ("HOTEL", "AIRFARE", "CAR_RENTAL") else ["SOFTWARE"] if et == "SOFTWARE" else ["TRAINING"] if et in ("TRAINING", "CERTIFICATION") else ["GENERAL"]
        R.branch.append("amount crosses an approval threshold"); check_approval(R, lvl, types, sgd, f"an expense above the {lvl.lower()} threshold", ctrl)
    if f.get("charge_to") == "PROJECT" and et != "SOFTWARE": project_chain(R, sgd)
    R.done("APPROVE", "All applicable checks pass.")
