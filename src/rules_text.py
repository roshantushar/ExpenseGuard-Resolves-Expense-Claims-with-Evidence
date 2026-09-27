"""Experiment 2c: rules + regex text parsing. Best-effort deterministic reader of the free-text note: it rebuilds the structured facts with regular expressions and keyword lists
(number words, dates, cabin/gift/venue keywords) and then applies the frozen src/rules_v2.py logic. No model, no ground truth. Shows how far parsing alone gets on the semantic dataset."""
from __future__ import annotations
import re
from . import rules_v2 as R, tables as T

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
       "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20, "thirtieth": 30}
MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
CAT = {"HOTEL": "HOTEL", "AIRLINE": "AIRFARE", "RIDE_HAIL": "GROUND_TRANSPORT", "GIFT_RETAIL": "GIFT", "SOFTWARE": "SOFTWARE", "EQUIPMENT": "EQUIPMENT", "TELECOM": "TELECOM", "TRAINING_PROVIDER": "TRAINING",
       "CONFERENCE_ORGANISER": "CONFERENCE_FEE", "MILEAGE": "MILEAGE", "CAR_RENTAL": "CAR_RENTAL"}
NUMW = "|".join(sorted(list(UNITS) + list(TENS), key=len, reverse=True))


def num(tok):
    tok = tok.lower().strip()
    if re.fullmatch(r"\d+(\.\d+)?", tok):
        return float(tok) if "." in tok else int(tok)
    parts = re.split(r"[-\s]+", tok)
    if parts and all(p in UNITS or p in TENS or p == "and" or p == "hundred" for p in parts):
        tot = 0
        for p in parts:
            if p in UNITS: tot += UNITS[p]
            elif p in TENS: tot += TENS[p]
            elif p == "hundred": tot = (tot or 1) * 100
        return tot
    return None


NUMBER = rf"(\d+(?:\.\d+)?|(?:{NUMW})(?:[- ](?:{NUMW}))?(?: hundred(?: (?:and )?(?:{NUMW})(?:[- ](?:{NUMW}))?)?)?)"


def dates_in(text, year_hint):
    out = []
    for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})", text):
        out.append((m.start(), m.group(0)))
    pat = rf"\b({'|'.join(MONTHS)})\s+(\d{{1,2}}(?:st|nd|rd|th)?|{'|'.join(ORD)}(?:[- ](?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth))?|(?:twenty|thirty)[- ](?:{'|'.join(ORD)}))(?:,?\s+((?:19|20)\d\d|two thousand[ -]\w+(?:[- ]\w+)?|twenty[ -]twenty[- ]\w+))?"
    for m in re.finditer(pat, text, re.I):
        mon = MONTHS[m.group(1).lower()]; d = m.group(2).lower(); day = None
        if re.match(r"\d", d): day = int(re.sub(r"\D", "", d))
        else:
            ps = re.split(r"[- ]", d); day = sum(ORD.get(p, TENS.get(p, 0)) for p in ps)
        y = year_hint
        if m.group(3):
            g = m.group(3).lower()
            if re.fullmatch(r"\d{4}", g): y = int(g)
            else:
                mm = re.search(r"(twenty|thirty)[- ]?(\w+)?$", g); y = 2000 + (TENS.get(mm.group(1), 20) if mm else 25) + (UNITS.get(mm.group(2), 0) if mm and mm.group(2) else 0) if "thousand" not in g else 2000 + TENS.get(g.split()[-1].split("-")[0], 0) + UNITS.get(g.split("-")[-1], 0)
        try:
            out.append((m.start(), f"{y}-{mon:02d}-{day:02d}"))
        except Exception:
            pass
    return [d for _, d in sorted(out)]


def parse(c: dict) -> dict:
    b, txt = c["bill"], c["employee_description"]; t = txt.lower(); yr = int(c["transaction_date"][:4])
    f = {"charge_to": "PROJECT" if re.search(r"prj-\d+|project budget|charged to (the )?project", t) else "COST_CENTRE", "approval_ref": None}
    mcat = next((r["merchant_category"] for r in T.table("merchant_directory") if r["merchant_name"] == b["merchant"]), b["merchant_category"])   # bill category is coarse: use the directory
    et = CAT.get(mcat, "OTHER")
    if mcat == "RESTAURANT":
        emp_only = re.search(r"\bno external\b|all employees|employees only|colleagues only|entirely (made up of )?employees|only employees|nobody from outside|no guests|internal", t)
        guests = re.search(r"guest|client|delegate|external|hosted|from [A-Z]", txt) and not emp_only
        et = "MEAL_CLIENT" if guests else "MEAL_EMPLOYEE"
    f["expense_type"] = et
    ref = lambda p: (re.search(p, txt, re.I) or [None])[0]
    f["conference_ref"] = ref(r"CONF-\d+"); f["exception_ref"] = ref(r"EXC-\d+"); f["learning_plan_id"] = ref(r"LP-\d+")
    if et in ("MEAL_CLIENT", "MEAL_EMPLOYEE"):
        n = None
        m = re.search(rf"{NUMBER}\s*(?:pax|people|persons|of us|attendees|employees|diners)", t) or re.search(rf"total (?:of |number of people )?{NUMBER}", t)
        if m: n = num(m.group(1))
        elif (m := re.search(rf"with {NUMBER} colleagues", t)): n = (num(m.group(1)) or 0) + 1
        elif (m := re.search(rf"employee, {NUMBER} colleagues?", t)):
            n = 1 + (num(m.group(1)) or 0) + sum((num(x) or 0) for x in re.findall(rf"{NUMBER} (?:external|delegates|guests)", t))
        ext = sum((num(x) or 0) for x in re.findall(rf"{NUMBER} (?:external|delegates|guests|other guests?)", t) if x) if not re.search(r"no external", t) else 0
        if not ext and et == "MEAL_CLIENT": ext = 1
        f.update(attendees_total=n, external_attendees=ext, external_names=("named guests" if et == "MEAL_CLIENT" and re.search(r"[A-Z][a-z]+\.? [A-Z]|mr\.|ms\.|dr\.|from [A-Z]|delegates|of [A-Z]", txt) else None), alcohol_amount=0.0 if re.search(r"no alcohol", t) else None, tip_amount=0.0 if re.search(r"no (alcohol|voluntary)|voluntary charge", t) else None)
        if f["alcohol_amount"] is None: f["alcohol_amount"] = 0.0
        if f["tip_amount"] is None: f["tip_amount"] = 0.0
    if et == "HOTEL":
        m = re.search(rf"{NUMBER} nights?", t); f["nights"] = num(m.group(1)) if m else None
        ds = dates_in(txt, yr)
        if f["nights"] is None and len(ds) >= 2:
            f["nights"] = (R.date.fromisoformat(ds[1]) - R.date.fromisoformat(ds[0])).days if hasattr(R, "date") else None
        f["city"] = b["city"]
    if et == "AIRFARE":
        f["cabin"] = "BUSINESS" if re.search(r"business|lie-flat", t) else "PREMIUM_ECONOMY" if re.search(r"premium|extra.legroom", t) else "ECONOMY"
        m = re.search(rf"{NUMBER}(?: and a half)?\s*(?:hrs?|hours)", t); h = num(m.group(1)) if m else None
        if m and "and a half" in m.group(0): h = (h or 0) + 0.5
        f["flight_hours"] = h
        ds = dates_in(txt, yr); f["booked_date"] = ds[0] if ds else None; f["departure_date"] = ds[1] if len(ds) > 1 else (ds[0] if ds else None)
    if et == "MILEAGE":
        m = re.search(rf"{NUMBER}\s*(?:km|kilomet)", t); f["distance_km"] = num(m.group(1)) if m else None
    if et == "GIFT":
        f["gift_form"] = "CASH_EQUIVALENT" if re.search(r"voucher|gift card|prepaid|redeem|store credit|stored", t) else "ITEM"
        f["recipient_type"] = "GOVERNMENT" if re.search(r"state-owned|statutory|authority|ministry|public university|public hospital|public.sector|municipal|agency", t) else "COMMERCIAL"
        nm = re.search(r"\b(?:Ms|Mr|Dr)\.? [A-Z][a-z]+", txt); f["recipient_name"] = nm.group(0) if nm else None
        orgs = {p["counterparty"] for p in T.table("previous_expenses") if p["counterparty"]}
        f["recipient_org"] = next((o for o in orgs if o.lower() in t), None)
        if not f["recipient_org"]:
            mo = re.search(r"(?:of|from|at|with) ([A-Z][A-Za-z&]+(?: [A-Z][A-Za-z&]+)*)", txt); f["recipient_org"] = mo.group(1) if mo else None
    if et == "SOFTWARE":
        m = re.search(r"(?:owner(?:ship)?(?: of this subscription)?(?: is| by| of)?|owned by|under the name of|named)\s+([A-Z][a-z]+ [A-Z][a-z]+)", txt) or re.search(r"([A-Z][a-z]+ [A-Z][a-z]+) (?:is|as) (?:the )?(?:named )?business owner", txt)
        f["business_owner"] = m.group(1) if m else None
        f["billing"] = "ANNUAL_PREPAID" if re.search(r"annual|up.?front|prepaid|whole year", t) else "MONTHLY"
    if et == "EQUIPMENT":
        f["item"] = "equipment"
    if et == "TRAINING":
        f["provider"] = "provider"
    if et == "TELECOM":
        f["billing_month"] = c["transaction_date"][:7]
    if et == "GROUND_TRANSPORT":
        m = re.search(r"from ([\w' ]+?) to ([\w' ]+?)(?:[.,;]| for | after |$)", txt)
        f["origin"] = m.group(1) if m else None; f["destination"] = m.group(2) if m else (("client office" if "client" in t else None))
        kind = lambda s: "HOME" if s and re.search(r"\bhome\b", s.lower()) else "OFFICE" if s and "office" in s.lower() else "AIRPORT" if s and "airport" in s.lower() else "CLIENT_SITE" if s and "client" in s.lower() else "OTHER"
        f["origin_type"], f["destination_type"] = kind(f["origin"]), kind(f["destination"])
        tm = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", txt)
        f["departure_time"] = f"{tm[0][0]:0>2}:{tm[0][1]}" if tm else None; f["activity_end_time"] = f"{tm[1][0]:0>2}:{tm[1][1]}" if len(tm) > 1 else None
    if et == "CONFERENCE_FEE":
        pass
    return f


def decide(c: dict) -> dict:
    f = parse(c)
    return R.decide(dict(c, form=f))
