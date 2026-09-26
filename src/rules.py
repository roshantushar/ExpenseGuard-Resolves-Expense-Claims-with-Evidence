"""Experiment 2: deterministic rules baseline. No model, no retrieval. Reads only the claim plus
static reference tables (frozen FX, employee grade, exact-duplicate history, approval records).
Policy constants below are transcribed from the policy corpus."""
from __future__ import annotations
import re
from . import tables as T

REGION = {"Singapore": "SG", "India": "IN", "Japan": "JP"}
EMP_MEAL = {"SG": (45, 50, 55), "IN": (1800, 2000, 2200), "JP": (4500, 5000, 5500)}
CLIENT_MEAL = {"SG": (120, 120, 130), "IN": (4500, 4500, 5000), "JP": (12000, 12000, 13000)}
# HIST-1.x nightly hotel ceilings by year (2024, 2025, 2026): location -> per grade band (G1-3, G4-5, G6+)
HOTEL = {"SG": ((280, 330, 390), (300, 350, 410), (320, 370, 430)), "TOKYO": ((28000, 32000, 38000), (30000, 34000, 40000), (32000, 36000, 42000)),
         "JP": ((23000, 27000, 33000), (25000, 29000, 35000), (27000, 31000, 37000)), "IN": ((9000, 12000, 16000), (10000, 13000, 17000), (11000, 14500, 18500))}
NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def _out(decision, policy, missing=(), reason=""):
    return {"decision": decision, "policy_evidence": list(policy), "missing_fields": list(missing), "reason": reason,
            "manual_review_required": decision == "ESCALATE"}


def attendees(text: str):
    t = text.lower()
    m = re.search(r"(\w+) attendees total", t)
    if m and m.group(1) in NUM:
        return NUM[m.group(1)]
    n = sum(NUM[w] for w, _ in re.findall(r"\b(one|two|three|four|five|six) (external|employees?|client|customer|colleagues?)", t))
    return n or None


def has_approval(case) -> bool:
    return any(r["expense_id"] == case["case_id"] and r["status"] == "APPROVED" for r in T.table("manager_approvals"))


def decide(c: dict) -> dict:
    b, desc = c["bill"], c["employee_description"]
    year = int(c["transaction_date"][:4]); yi = year - 2024
    region = REGION.get(b["country"], "")
    cat = b["merchant_category"]
    items = " ".join(i["description"] for i in b["line_items"]).lower()
    # 1 documentation (GEP24-1.2 / GEP25-1.2)
    miss = [k for k, v in [("merchant", b.get("merchant")), ("transaction_date", c["transaction_date"]), ("currency", b.get("currency")),
                           ("total", b.get("total")), ("business_purpose", desc.strip())] if not v]
    if miss:
        return _out("REQUEST_INFORMATION", ["GEP25-1.2"], miss, "Mandatory documentation fields are missing.")
    # 2 exact duplicate (CARD-4.1)
    for p in T.table("previous_expenses"):
        if p["employee_id"] == c["employee_id"] and p["merchant"] == b["merchant"] and (
                p["bill_number"] == b["bill_number"] or (p["transaction_date"] == c["transaction_date"] and float(p["amount"]) == b["total"])):
            return _out("REJECT", ["CARD-4.1"], (), f"Exact duplicate of {p['expense_id']}.")
    # 3 submission window (GEP24-2.1 / GEP25-2.1 / GEP26-2.1)
    age = T.days_between(c["transaction_date"], c["submission_date"])
    if year == 2024 and age > 60:
        return _out("REJECT", ["GEP24-2.1"], (), f"Submitted {age} days after transaction (limit 60).")
    if year >= 2025 and age > 45:
        hard = 90 if year == 2025 else 75
        pol = "GEP25-2.1" if year == 2025 else "GEP26-2.1"
        if age > hard:
            return _out("ESCALATE", [pol], (), f"Submitted {age} days after transaction; Finance review required.")
        if not has_approval(c):
            return _out("REQUEST_INFORMATION", [pol], ["manager_approval"], f"Submitted {age} days late; manager approval needed.")
    # 4 category rules
    if cat in ("CONSUMER_SERVICE", "STREAMING", "FITNESS") or re.search(r"\bpersonal use\b|\bfor myself\b", desc.lower()):
        return _out("REJECT", ["CARD-1.1", "CARD-2.2"], (), "Personal or consumer-service spend.")
    if "not itemised" in items or "personal item" in items:
        return _out("REQUEST_INFORMATION", ["GEP26-2.2"], ["itemised_business_amount"], "Mixed personal/business bill is not itemised.")
    amount_sgd = b["total"] * T.fx_to_sgd(b["currency"], c["transaction_date"])
    if cat == "RESTAURANT":
        if re.search(r"\b(taxi|cab|ride|flight|hotel)\b", desc.lower()):
            return _out("REQUEST_INFORMATION", ["GEP26-1.2"], ["correct_business_purpose"], "Bill category conflicts with the description.")
        alc = sum(i["amount"] for i in b["line_items"] if "alcohol" in i["description"].lower())
        if alc and region == "IN":
            return _out("REJECT", ["MEAL-2.1", "IN-2.1"], (), "Alcohol is not reimbursable in India.")
        if alc and (region == "SG") and alc > 0.35 * b["total"]:
            return _out("REJECT", ["MEAL-2.1", "SG-2.1"], (), "Alcohol exceeds 35% of bill.")
        n = attendees(desc)
        client = bool(re.search(r"client|customer|external", items + " " + desc.lower())) and "employee meal" not in items
        if n is None:
            return _out("REQUEST_INFORMATION", ["MEAL-3.1"], ["attendee_count"], "Attendee count needed for per-person ceiling.")
        cap = (CLIENT_MEAL if client and "two employees" not in desc.lower() else EMP_MEAL)[region][yi]
        pol = ("MEAL-1.2" if cap == CLIENT_MEAL[region][yi] else "MEAL-1.1", f"{region}-1.{'2' if cap == CLIENT_MEAL[region][yi] else '1'}")
        if b["total"] / n > cap:
            return _out("REJECT", pol, (), f"Per-person spend {b['total'] / n:.0f} exceeds ceiling {cap}.")
    elif cat == "RIDE_HAIL":
        if not re.search(r"\bfrom\b|airport|hotel|client|office|event", desc.lower()):
            return _out("REQUEST_INFORMATION", ["TRV-3.1"], ["origin", "destination"], "Route details missing.")
    elif cat == "OFFICE_SUPPLIES":
        if re.fullmatch(r"\s*(business expense|supplies|misc\w*)\.?\s*", desc.lower()):
            return _out("REQUEST_INFORMATION", ["GEP26-1.1"], ["business_purpose"], "Description too generic.")
    elif cat == "HOTEL":
        loc = "TOKYO" if "tokyo" in b["merchant"].lower() else region
        g = int(T.employee(c["employee_id"]).get("grade", "G1")[1:])
        ceiling = HOTEL[loc][yi][0 if g <= 3 else 1 if g <= 5 else 2]
        if b["total"] > ceiling:
            return _out("ESCALATE", ["TRV-1.2", "CONF-2.1"], (), "Over hotel ceiling; conference/exception evidence needed.")
    # 5 generic approval thresholds (APR-1.1 / APR-1.3), also CIRC-26-02 for software
    if amount_sgd > 5000:
        return _out("ESCALATE", ["APR-1.3"], (), "Above SGD 5000 requires Finance review.")
    if amount_sgd > 500 and not has_approval(c):
        return _out("REQUEST_INFORMATION", ["APR-1.1"], ["manager_approval"], f"SGD {amount_sgd:.0f} exceeds 500; approval record absent.")
    return _out("APPROVE", [], (), "No rule triggered.")


def facts(c: dict) -> str:
    """Exp 12: deterministic calculations handed to the LLM (arithmetic, dates, FX, thresholds, exact duplicate, approval-record lookup).
    Semantic judgments (client vs employee meal, description specificity, evidence conflict, applicability) are left to the model."""
    b, desc = c["bill"], c["employee_description"]
    year = int(c["transaction_date"][:4]); yi = year - 2024
    region = REGION.get(b["country"], "")
    rate = T.fx_to_sgd(b["currency"], c["transaction_date"])
    sgd = b["total"] * rate
    out = [f"Amount: {b['total']:g} {b['currency']} = SGD {sgd:.2f} (frozen monthly rate {rate} for {c['transaction_date'][:7]})."]
    age = T.days_between(c["transaction_date"], c["submission_date"])
    win = {2024: "limit 60 days; later needs an approved exception", 2025: "45 days; 46-90 needs manager approval; >90 needs Finance escalation",
           2026: "45 days; 46-75 needs manager approval; >75 needs Finance review"}[year]
    out.append(f"Submission: {age} days after the transaction ({year} window: {win}).")
    n = attendees(desc)
    if b["merchant_category"] == "RESTAURANT":
        alc = sum(i["amount"] for i in b["line_items"] if "alcohol" in i["description"].lower())
        if n:
            pp = b["total"] / n
            out.append(f"Meal: {n} attendees detected from the description; per-person spend {pp:.2f} {b['currency']}. {region} {year} ceilings per person: "
                       f"employee-only {EMP_MEAL[region][yi]}, client {CLIENT_MEAL[region][yi]} ({b['currency']}). "
                       f"Exceeds employee ceiling: {pp > EMP_MEAL[region][yi]}; exceeds client ceiling: {pp > CLIENT_MEAL[region][yi]}.")
        else:
            out.append("Meal: attendee count could not be determined from the description.")
        if alc:
            out.append(f"Alcohol line items total {alc:g} = {100 * alc / b['total']:.0f}% of the bill.")
    if b["merchant_category"] == "HOTEL":
        loc = "TOKYO" if "tokyo" in b["merchant"].lower() else region
        g = int(T.employee(c["employee_id"]).get("grade", "G1")[1:])
        ceil = HOTEL[loc][yi][0 if g <= 3 else 1 if g <= 5 else 2]
        out.append(f"Hotel: employee grade G{g}; base nightly ceiling for {loc} in {year} is {ceil} {b['currency']}; claim {'exceeds' if b['total'] > ceil else 'is within'} the base ceiling "
                   f"(claimed {b['total']:g}, ratio {b['total'] / ceil:.2f}).")
    dup = next((p["expense_id"] for p in T.table("previous_expenses") if p["employee_id"] == c["employee_id"] and p["merchant"] == b["merchant"] and
                (p["bill_number"] == b["bill_number"] or (p["transaction_date"] == c["transaction_date"] and float(p["amount"]) == b["total"]))), None)
    out.append(f"Exact duplicate in previous expenses: {'YES, ' + dup if dup else 'no'}.")
    thr = "above SGD 5000 (Finance review)" if sgd > 5000 else "above SGD 1500 (director approval)" if sgd > 1500 else "above SGD 500 (manager approval)" if sgd > 500 else "below the SGD 500 approval threshold"
    out.append(f"Approval threshold: amount is {thr}. Manager approval record on file for this expense: {'yes' if has_approval(c) else 'no'}.")
    return "\n".join("- " + x for x in out)
