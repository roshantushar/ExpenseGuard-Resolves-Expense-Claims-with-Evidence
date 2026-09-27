"""Experiment 2b: V2-adapted deterministic rules. No model, no retrieval. Reads only the claim plus the enterprise tables (runtime-safe).
Constants are transcribed from the V2 policy corpus (regional addenda, TRV, APR, EXC, circulars). Extends the V1-era src/rules.py, which is left untouched."""
from __future__ import annotations
from datetime import date
from . import tables as T

REG = {"Singapore": "SG", "India": "IN", "Japan": "JP"}
LEVEL = {"MANAGER": 1, "DIRECTOR": 2, "FINANCE": 3}
Y = lambda c: int(c["transaction_date"][:4]) - 2024
EMP_MEAL = {"SG": (45, 50, 55), "IN": (1800, 2000, 2200), "JP": (4500, 5000, 5500)}
CLIENT_MEAL = {"SG": (120, 120, 130), "IN": (4500, 4500, 5000), "JP": (12000, 12000, 13000)}
GIFT = {"SG": (100, 120, 120), "IN": (3500, 4000, 4500), "JP": (6000, 6000, 7000)}
GIFT_ANNUAL = {"SG": (400, 450, 450), "IN": (14000, 15000, 16000), "JP": (24000, 26000, 28000)}
TELECOM = {"SG": (80, 90, 90), "IN": (2500, 2500, 3000), "JP": (9000, 9000, 10000)}
MILEAGE = {"SG": (0.6, 0.6, 0.65), "IN": (11, 12, 12), "JP": (35, 37, 37)}
ENTERTAIN = {"SG": (180, 190, 200), "IN": (6500, 7000, 7500), "JP": (16000, 17000, 18000)}
LOCAL_MGR = {"SG": (500, 500, 500), "IN": (20000,) * 3, "JP": (45000, 45000, 50000)}  # local-currency manager threshold (SG: SGD 500)
TIER = {"Singapore": "SG-CENTRAL", "Mumbai": "IN-T1", "Delhi": "IN-T1", "Bengaluru": "IN-T1", "Pune": "IN-T2", "Jaipur": "IN-T2", "Kochi": "IN-T2", "Tokyo": "JP-TOKYO",
        "Osaka": "JP-MAJOR", "Nagoya": "JP-MAJOR", "Yokohama": "JP-MAJOR", "Fukuoka": "JP-OTHER", "Sapporo": "JP-OTHER", "Sendai": "JP-OTHER"}
HOTEL = {2024: {"SG-CENTRAL": (280, 330, 390, 480), "IN-T1": (9000, 12000, 16000, 21000), "IN-T2": (6000, 8500, 11000, 15000), "JP-TOKYO": (28000, 32000, 38000, 46000), "JP-MAJOR": (24000, 28000, 34000, 41000), "JP-OTHER": (20000, 24000, 29000, 35000)},
         2025: {"SG-CENTRAL": (300, 350, 410, 500), "IN-T1": (10000, 13000, 17000, 22000), "IN-T2": (6500, 9000, 11800, 16000), "JP-TOKYO": (30000, 34000, 40000, 49000), "JP-MAJOR": (25500, 29500, 35500, 43000), "JP-OTHER": (21500, 25500, 30500, 37000)},
         2026: {"SG-CENTRAL": (320, 370, 430, 520), "IN-T1": (11000, 14500, 18500, 24000), "IN-T2": (7000, 9800, 12800, 17500), "JP-TOKYO": (32000, 36000, 42000, 52000), "JP-MAJOR": (27500, 31500, 37500, 46000), "JP-OTHER": (23000, 27000, 32500, 39500)}}
TRAIN = {2024: (1800, 3200, 4800, 6500), 2025: (2000, 3500, 5000, 7000), 2026: (2200, 3800, 5400, 7500)}


def out(decision, policy=(), missing=(), reason=""):
    return {"decision": decision, "policy_evidence": list(policy), "missing_fields": list(missing), "reason": reason, "manual_review_required": decision == "ESCALATE"}


def rnd(x, unit=100):  # round half up
    return int(x / unit + 0.5) * unit


def band(g, four=False):
    return 0 if g <= 3 else 1 if g <= 5 else 2 if g <= 7 else 3


def grade(c):
    return int(T.employee(c["employee_id"]).get("grade", "G1")[1:] or 1)


def sgd(c):
    b = c["bill"]
    return b["total"] * T.fx_to_sgd(b["currency"], c["transaction_date"])


def rows(name, **kw):
    return [r for r in T.table(name) if all(r.get(k) == v for k, v in kw.items())]


def within(d, a, b):
    return a <= d <= b


def region(c):
    return REG.get(c["bill"]["country"], "")


def approval_record(c):
    return next(iter(rows("manager_approvals", expense_id=c["case_id"])), None)


def approval_state(c, need_level, types):
    """None if valid approval; else (decision, policy, missing, reason)."""
    a = approval_record(c)
    if not a:
        return ("REQUEST_INFORMATION", ["APR-3.1"], ["manager_approval" if need_level == 1 else "director_approval"], "Required approval record is absent.")
    d = c["transaction_date"]
    if a["status"] not in ("APPROVED", "DELEGATED"):
        return ("REQUEST_INFORMATION", ["APR-2.1"], ["valid_approval"], f"Approval status is {a['status']}.")
    if a["approval_type"] not in types and a["approval_type"] != "GENERAL":
        return ("ESCALATE", ["APR-2.2"], [], f"Approval type {a['approval_type']} does not cover this expense (conflicting evidence).")
    if a["start_date"] and not within(d, a["start_date"], a["end_date"]):
        return ("REQUEST_INFORMATION", ["APR-2.1"], ["valid_approval"], "Approval does not cover the transaction date.")
    if a["status"] == "DELEGATED":
        dl = next(iter(rows("approval_delegations", delegation_id=a["delegation_id"])), None)
        if not dl or not within(d, dl["start_date"], dl["end_date"]) or dl["status"] != "ACTIVE":
            return ("REQUEST_INFORMATION", ["APR-4.2"], ["valid_approval"], "Delegation is outside its validity period.")
        if sgd(c) > float(dl["max_amount_sgd"]) or LEVEL[dl["delegate_level"]] < need_level:
            return ("ESCALATE", ["APR-4.2"], [], "Delegation limit or level insufficient.")
        return None
    if LEVEL[a["approver_level"]] < need_level:
        return ("REQUEST_INFORMATION", ["APR-2.1"], ["approval_at_required_level"], "Approver level is below what the amount requires.")
    return None


def need_level(c, amount_sgd=None):
    """0 none, 1 manager, 2 director; 9 finance review."""
    amount = sgd(c) if amount_sgd is None else amount_sgd
    y = Y(c); r = region(c); b = c["bill"]
    if amount > 5000:
        return 9
    if amount > (1500 if y < 2 else 2000):
        return 2
    local = b["total"] > LOCAL_MGR[r][y] if r in ("IN", "JP") else amount > 500
    return 1 if (local or amount > 500) else 0


def submission(c):
    y = c["transaction_date"][:4]; age = T.days_between(c["transaction_date"], c["submission_date"]); r = region(c)
    win, hard = 45, {"2024": 60, "2025": 90, "2026": 75}[y]
    if y == "2026" and r == "IN" and c["bill"]["country"] == "India":
        win = 60
    if y == "2024":
        return None if age <= 60 else out("REJECT", ["GEP24-2.1"], (), f"Submitted {age} days after transaction (limit 60).")
    if age <= win:
        return None
    relief = "2025-03-10" <= c["transaction_date"] <= "2025-03-14"
    pol = f"GEP{y[2:]}-2.1"
    if age > hard and not relief:
        return out("ESCALATE", [pol], (), f"Submitted {age} days late; Finance review.")
    a = approval_state(c, 1, ("GENERAL",))
    if a:
        return out("REQUEST_INFORMATION", [pol], ["manager_approval"], f"Submitted {age} days after transaction; manager approval needed.")
    return None


def budget(c):
    pj = next(iter(rows("project_registry", project_id=c.get("project_id"))), None)
    for _ in range(5):  # APR-5.2: charge to the parent project's cost centre
        par = next(iter(rows("project_registry", project_id=pj["parent_project_id"])), None) if pj and pj["parent_project_id"] else None
        if not par:
            break
        pj = par
    cc = pj["cost_centre"] if pj else T.employee(c["employee_id"]).get("cost_centre")
    cb = next(iter(rows("cost_centre_budgets", cost_centre=cc, year=c["transaction_date"][:4])), None)
    if not cb:
        return None
    if cb["status"] == "FROZEN" and sgd(c) > 200:
        return out("ESCALATE", ["APR-5.1"], (), "Cost centre is frozen; Finance review.")
    if cb["status"] == "OPEN" and float(cb["budget_sgd"]) - float(cb["committed_sgd"]) < sgd(c):
        return out("REQUEST_INFORMATION", ["APR-5.1"], ["budget_owner_approval"], "Remaining cost-centre budget is below the claim.")
    return None


def same_kind(c, p):
    return p["category"] in (c["form"]["expense_type"], c["bill"]["merchant_category"])


def duplicates(c):
    b = c["bill"]; d0 = date.fromisoformat(c["transaction_date"])
    for p in rows("previous_expenses", employee_id=c["employee_id"], merchant=b["merchant"]):
        if p["bill_number"] == b["bill_number"] or (p["transaction_date"] == c["transaction_date"] and abs(float(p["amount"]) - b["total"]) < 0.005):
            return out("REJECT", ["DUP-1.1"], (), f"Exact duplicate of {p['expense_id']}.")
    for p in rows("previous_expenses", employee_id=c["employee_id"], merchant=b["merchant"]):
        gap = abs((d0 - date.fromisoformat(p["transaction_date"])).days); amt = float(p["amount"]); rel = abs(amt - b["total"]) / amt if amt else 9
        if gap <= 3 and rel <= 0.02 and same_kind(c, p):
            return out("REQUEST_INFORMATION", ["DUP-1.2"], ["duplicate_clarification"], f"Possible duplicate of {p['expense_id']}.")
    return None


def split(c):
    """DUP-2.1/2.2: related purchases (same employee, merchant, project, within 3 days, differing >2%) are combined for the approval threshold."""
    b = c["bill"]; d0 = date.fromisoformat(c["transaction_date"]); comb = sgd(c); found = False
    for p in rows("previous_expenses", employee_id=c["employee_id"], merchant=b["merchant"], project_id=c.get("project_id")):
        gap = abs((d0 - date.fromisoformat(p["transaction_date"])).days); amt = float(p["amount"])
        if gap <= 3 and abs(amt - b["total"]) / max(amt, 1e-9) > 0.02 and same_kind(c, p):
            comb += amt * T.fx_to_sgd(p["currency"], p["transaction_date"]); found = True
    if not found:
        return None
    r = region(c); fx = T.fx_to_sgd(b["currency"], c["transaction_date"])
    thr = LOCAL_MGR[r][Y(c)] * fx if r in ("IN", "JP") else 500
    if comb > thr >= sgd(c):
        a = approval_record(c)
        if not a:
            return out("REQUEST_INFORMATION", ["DUP-2.1", "DUP-2.2"], ["combined_spend_approval"], "Combined amount crosses an approval threshold; approval absent.")
        if a["approval_type"] != "COMBINED_SPEND":
            return out("ESCALATE", ["DUP-2.2"], (), "Approval type conflicts with combined spend.")
    return None


def exception_for(c, policy_id, exc_id):
    """Returns 'VALID' | ('ESCALATE'|'REQUEST_INFORMATION'|'ORDINARY')"""
    if not exc_id:
        return "NONE"
    e = next(iter(rows("policy_exceptions", exception_id=exc_id)), None)
    if not e:
        return "MISSING_ID"
    if e["employee_id"] != c["employee_id"] or e["policy_id"] != policy_id:
        return "WRONG_SCOPE"
    if e["status"] != "APPROVED" or not within(c["transaction_date"], e["valid_from"], e["valid_to"]):
        return "INVALID"
    return "VALID"


def travel_request(c, on=None):
    on = on or c["transaction_date"]
    for t in rows("travel_requests", employee_id=c["employee_id"]):
        if within(on, t["start_date"], t["end_date"]):
            return t
    return None


def hotel(c):
    b, f = c["bill"], c["form"]; y = int(c["transaction_date"][:4]); r = region(c)
    tr = travel_request(c)
    if not tr or tr["status"] != "APPROVED":
        return out("REQUEST_INFORMATION", ["TRV-1.1"], ["approved_travel_request"], "No approved travel request covers the transaction date.")
    tier = TIER.get(f.get("city") or b["city"]) or TIER.get(b["city"])
    ceil = HOTEL[y][tier][band(grade(c))]
    if tier == "JP-TOKYO" and y == 2025 and c["transaction_date"] >= "2025-07-01":
        ceil = rnd(ceil * 1.05)
    if tier == "IN-T1" and y == 2026 and c["transaction_date"] >= "2026-04-01":
        ceil = rnd(ceil * 1.06)
    conf = next(iter(rows("conference_registry", event_id=tr["event_id"])), None) if tr["event_id"] else None
    partner = bool(conf and conf["employee_id"] == c["employee_id"] and conf["registration_status"] == "REGISTERED" and conf["official_partner_hotel"] == b["merchant"])
    if partner:
        ceil = ceil * (1.2 if y < 2026 else 1.25)
    nights = f.get("nights") or 1
    if nights > 14 and y >= 2025:
        ceil *= 0.9
    rate = b["total"] / nights
    if rate <= ceil + 1e-9:
        return None
    exc_id = f.get("exception_ref") or tr.get("exception_id")
    st = exception_for(c, "TRV-6.1", exc_id)
    if st == "VALID":
        return None
    if st == "WRONG_SCOPE":
        return out("ESCALATE", ["EXC-2.1"], (), "Exception names a different policy or employee.")
    if st == "MISSING_ID":
        return out("REQUEST_INFORMATION", ["EXC-2.1"], ["exception_reference"], "Cited exception identifier does not exist.")
    if conf and not partner and tr["event_id"]:
        pass
    return out("REJECT", ["TRV-6.1"], (), f"Nightly rate {rate:.0f} exceeds ceiling {ceil:.0f}; no valid exception.")


def airfare(c):
    f = c["form"]; y = int(c["transaction_date"][:4]); g = grade(c)
    tr = travel_request(c, f.get("departure_date"))
    if not tr or tr["status"] != "APPROVED":
        return out("REQUEST_INFORMATION", ["TRV-1.1"], ["approved_travel_request"], "No approved travel request.")
    cabin, hrs = f.get("cabin"), f.get("flight_hours") or 0
    pe_hours = 5.5 if (y == 2025 and c["transaction_date"] >= "2025-04-01") else 6
    ok = cabin == "ECONOMY" or (cabin == "PREMIUM_ECONOMY" and hrs > pe_hours and g >= 4) or (cabin == "BUSINESS" and (g >= 7 or (g >= 6 and hrs > 9)))
    if not ok:
        st = exception_for(c, "AIR-2.2", f.get("exception_ref") or tr.get("exception_id"))
        if st == "WRONG_SCOPE":
            return out("ESCALATE", ["EXC-2.1"], (), "Exception names a different policy or employee.")
        if st == "MISSING_ID":
            return out("REQUEST_INFORMATION", ["EXC-2.1"], ["exception_reference"], "Cited exception identifier does not exist.")
        if st != "VALID":
            return out("REJECT", ["AIR-2.1", "AIR-2.2"], (), f"{cabin} not permitted for grade G{g}, {hrs}h.")
    if f.get("booked_date") and f.get("departure_date") and T.days_between(f["booked_date"], f["departure_date"]) < 14:
        a = approval_state(c, 1, ("TRAVEL", "GENERAL"))
        if a:
            return out("REQUEST_INFORMATION", ["AIR-3.1"], ["manager_approval"], "Booked fewer than 14 days ahead; approval needed.")
    return None


def meal(c):
    b, f, desc = c["bill"], c["form"], c["employee_description"]; y = Y(c); r = region(c); yr = int(c["transaction_date"][:4]); d = c["transaction_date"]
    n = f.get("attendees_total"); ext = f.get("external_attendees") or 0; client = f["expense_type"] == "MEAL_CLIENT" or ext > 0
    alc = f.get("alcohol_amount") or 0
    if r == "IN" and alc:
        return out("REJECT", ["IN-2.4"], (), "Alcohol is not reimbursable in India.")
    if alc and (not client):
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
    ceil = (CLIENT_MEAL if client else EMP_MEAL)[r][y]
    if client and r == "SG" and yr == 2025 and d >= "2025-07-01":
        ceil = 128
    if client and r == "JP" and yr == 2026 and d >= "2026-05-01":
        ceil = 13500
    if not client:
        if r == "SG" and yr == 2025 and d >= "2025-09-01": ceil = 52
        if r == "JP" and yr == 2025 and d >= "2025-10-01": ceil = 5200
        if r == "IN" and yr == 2025 and d >= "2025-11-01": ceil = 2100
    if b["total"] / n > ceil + 1e-9:
        return out("REJECT", ["MEAL-1.2" if client else "MEAL-1.1"], (), f"Per-person spend {b['total'] / n:.0f} exceeds ceiling {ceil}.")
    pre = b["total"] - tip
    if tip and pre > 0 and tip > 0.15 * pre and r != "JP":
        a = approval_state(c, 1, ("GENERAL", "ENTERTAINMENT"))
        if a:
            return out("REQUEST_INFORMATION", ["MEAL-2.2"], ["manager_approval"], "Gratuity above 15% needs manager approval.")
    return None


def gift(c):
    b, f = c["bill"], c["form"]; y = Y(c); r = region(c); d = c["transaction_date"]
    if f.get("recipient_type") in ("GOVERNMENT", "TENDER_DECISION_MAKER", "PUBLIC_OFFICIAL") or f.get("gift_form") in ("CASH", "GIFT_CARD", "VOUCHER", "CASH_EQUIVALENT"):
        return out("REJECT", ["GIFT-1.2", "GIFT-1.3"], (), "Prohibited recipient or cash equivalent.")
    miss = [k for k in ("recipient_name", "recipient_org") if not f.get(k)]
    if miss:
        return out("REQUEST_INFORMATION", ["GIFT-1.4"], miss, "Recipient details missing.")
    cap = GIFT[r][y]
    if r == "SG" and d >= "2026-06-01":
        cap = 130
    if b["total"] > cap:
        return out("REJECT", ["GIFT-2.1"], (), f"Gift {b['total']} exceeds per-gift ceiling {cap}.")
    prior = sum(float(p["amount"]) for p in rows("previous_expenses", employee_id=c["employee_id"], category="GIFT", counterparty=f["recipient_org"]) if p["transaction_date"][:4] == d[:4])
    if prior + b["total"] > GIFT_ANNUAL[r][y]:
        return out("REJECT", ["GIFT-2.2"], (), "Annual gift ceiling for the recipient organisation exceeded.")
    return None


def software(c):
    f = c["form"]; amt = sgd(c); d = c["transaction_date"]
    if not f.get("business_owner"):
        return out("REQUEST_INFORMATION", ["SWE-1.1"], ["business_owner"], "Named business owner required.")
    if f.get("billing") == "ANNUAL" and amt > 3000:
        return out("ESCALATE", ["SWE-1.3"], (), "Prepaid annual plan above SGD 3000 must go through Finance.")
    if amt > 1000 and d >= "2026-02-01":
        a = approval_state(c, 1, ("SOFTWARE", "GENERAL"))
        if a:
            return out(*a[:1], a[1], a[2], a[3])
        pj = next(iter(rows("project_registry", project_id=c.get("project_id"))), None)
        cb = next(iter(rows("cost_centre_budgets", cost_centre=pj["cost_centre"], year=d[:4])), None) if pj else None
        if (pj and pj["project_status"] != "ACTIVE") or (cb and cb["status"] != "OPEN"):
            return out("ESCALATE", ["SWE-1.2", "CIRC-26-02"], (), "Project not active or cost centre not open.")
        return None
    if amt > 500:
        a = approval_state(c, 1, ("SOFTWARE", "GENERAL"))
        if a:
            return out(a[0], a[1], a[2], a[3])
    return None


def equipment(c):
    amt = sgd(c)
    if amt > 1000:
        return out("REJECT", ["SWE-2.1"], (), "Equipment above SGD 1000 is a capital asset.")
    if amt > 300:
        a = approval_state(c, 1, ("GENERAL",))
        if a:
            return out(a[0], a[1], a[2], a[3])
    return None


def telecom(c):
    r = region(c); y = Y(c); m = (c["form"].get("billing_month") or c["transaction_date"][:7])
    prior = sum(float(p["amount"]) for p in rows("previous_expenses", employee_id=c["employee_id"], category="TELECOM") if p["transaction_date"][:7] == m)
    if prior + c["bill"]["total"] > TELECOM[r][y] + 1e-9:
        return out("REJECT", ["TEL-2.1"], (), "Monthly telecom ceiling would be exceeded.")
    return None


def training(c):
    f = c["form"]; y = int(c["transaction_date"][:4]); amt = sgd(c)
    if not f.get("learning_plan_id"):
        return out("REQUEST_INFORMATION", ["TRN-2.4"], ["learning_plan_id"], "Learning plan identifier required.")
    prior = 0.0
    for p in rows("previous_expenses", employee_id=c["employee_id"], category="TRAINING"):
        if p["transaction_date"][:4] == str(y):
            prior += float(p["amount"]) * T.fx_to_sgd(p["currency"], p["transaction_date"])
    if prior + amt > TRAIN[y][band(grade(c))]:
        a = approval_state(c, 2, ("TRAINING",))
        if a:
            return out(a[0], a[1], a[2] or ["director_approval"], a[3])
    return None


def conference(c):
    ref = c["form"].get("conference_ref"); e = next(iter(rows("conference_registry", event_id=ref)), None) if ref else None
    if not e or e["employee_id"] != c["employee_id"] or e["registration_status"] != "REGISTERED":
        return out("REJECT", ["TRN-1.1"], (), "No REGISTERED conference entry for the employee.")
    return None


def ground(c):
    f = c["form"]
    if not f.get("origin") or not f.get("destination"):
        return out("REQUEST_INFORMATION", ["GRD-1.1"], ["origin", "destination"], "Route details missing.")
    home = "HOME" in (f.get("origin_type"), f.get("destination_type"))
    if home:
        late = (f.get("departure_time") or "00:00") > "22:00" and (f.get("activity_end_time") or "00:00") > "21:30"
        if not late:
            return out("REJECT", ["GRD-1.2"], (), "Commute is not reimbursable.")
    return None


def car(c):
    if grade(c) < 4:
        return out("REJECT", ["GRD-3.1"], (), "Car rental requires grade G4+.")
    a = approval_state(c, 1, ("GENERAL", "TRAVEL"))
    return out(a[0], a[1], a[2], a[3]) if a else None


def mileage(c):
    r = region(c); y = Y(c)
    calc = MILEAGE[r][y] * (c["form"].get("distance_km") or 0)
    if c["bill"]["total"] > calc + 0.005:
        return out("REJECT", ["GRD-4.1"], (), f"Claim exceeds calculated {calc:.2f}.")
    return None


TYPES = {"HOTEL": ("TRAVEL", "GENERAL"), "AIRFARE": ("TRAVEL", "GENERAL"), "GROUND_TRANSPORT": ("TRAVEL", "GENERAL"), "CAR_RENTAL": ("TRAVEL", "GENERAL"), "SOFTWARE": ("SOFTWARE", "GENERAL"),
         "TRAINING": ("TRAINING", "GENERAL"), "CONFERENCE_FEE": ("TRAINING", "GENERAL"), "MEAL_CLIENT": ("ENTERTAINMENT", "GENERAL"), "MEAL_EMPLOYEE": ("GENERAL",)}


def decide(c: dict) -> dict:
    b, f = c["bill"], c["form"]; et = f.get("expense_type")
    if not (b.get("merchant") and b.get("total") and c["employee_description"].strip()):
        return out("REQUEST_INFORMATION", ["GEP26-1.3"], ["business_purpose"], "Mandatory documentation missing.")
    m = next(iter(rows("merchant_directory", merchant_name=b["merchant"])), None)
    if m and m["risk_class"] == "RESTRICTED_PROHIBITED":
        return out("REJECT", ["CARD-3.1"], (), "Prohibited merchant class.")
    if m and m["risk_class"] == "RESTRICTED_REVIEW":
        return out("ESCALATE", ["CARD-3.1"], (), "Restricted merchant requires Finance review.")
    if b["merchant_category"] in ("CONSUMER_SERVICE", "STREAMING", "FITNESS"):
        return out("REJECT", ["CARD-2.1"], (), "Consumer service presumed personal.")
    dl = c["employee_description"].lower()
    conflict = {"HOTEL": ("hotel", "nights"), "AIRFARE": ("flight", "airfare"), "GROUND_TRANSPORT": ("taxi", "cab", "ride")}
    for kind, kws in conflict.items():
        if et != kind and any(k in dl for k in kws) and et in ("GROUND_TRANSPORT", "HOTEL", "AIRFARE"):
            return out("REQUEST_INFORMATION", ["GEP26-4.1", "GEP26-1.2"], ["correct_business_purpose"], "Description conflicts with the bill category.")
    for fn in (duplicates, submission):
        o = fn(c)
        if o:
            return o
    per = {"HOTEL": hotel, "AIRFARE": airfare, "MEAL_CLIENT": meal, "MEAL_EMPLOYEE": meal, "GIFT": gift, "SOFTWARE": software, "EQUIPMENT": equipment, "TELECOM": telecom,
           "TRAINING": training, "CONFERENCE_FEE": conference, "GROUND_TRANSPORT": ground, "CAR_RENTAL": car, "MILEAGE": mileage}.get(et)
    if per:
        o = per(c)
        if o:
            return o
    for fn in (split, budget):
        o = fn(c)
        if o:
            return o
    lvl = need_level(c)
    if et not in ("SOFTWARE", "EQUIPMENT", "CAR_RENTAL") and lvl:
        if lvl == 9:
            return out("ESCALATE", ["APR-1.3"], (), "Above SGD 5000 requires Finance review.")
        a = approval_state(c, lvl, TYPES.get(et, ("GENERAL",)))
        if a:
            return out(a[0], a[1], a[2], a[3])
    return out("APPROVE", [], (), "No rule triggered.")
