"""Group B: 80 fixed multi-tool cases (the evidence path is fixed once the claim type is known)."""
from __future__ import annotations
from . import world as W
from .builder import ORGS, EVENTS
from .cases_a import CITY, COUNTRY, MEALW, FIRSTN, _u

STAY_REASON = ["the client workshop", "a partner summit", "the audit fieldwork", "a regional planning offsite", "the data-centre cutover", "customer onboarding", "the integration sprint"]


def hotel_claim(b, group, arch, want, city, t, grade, nights, factor, travel="APPROVED", conf=None, exc=None, extra=None, key=None, cited=None, conf_ref=False, exc_ref=False, travel_dates=None,
                partner=True, approval="director", amount_over=None, charge_to="COST_CENTRE", project=None):
    """Creates a hotel claim whose nightly rate is `factor` times the base ceiling (after circular amendments) for the employee's grade band."""
    rng = b.rng; loc = W.CITY_LOC[city]; reg = W.CITY_REGION[city]
    e = b.emp(None, grade, grade); key = key or b.key()
    base, _, _ = W.HOTEL.get((loc, W.band(grade)), t)
    nightly = round(base * factor) if reg != "SG" else round(base * factor, 2)
    total = round(nightly * nights, 2) if reg == "SG" else float(nightly * nights)
    m = b.hotel(city)
    if travel:
        s, en = travel_dates or (t, b.plus(t, nights))
        b.travel(e, s, en, status=travel, event=(conf or {}).get("event_id") if conf else None, exc=(exc or {}).get("exception_id") if exc else None, dest=city)
    d = _u(b, lambda: rng.choice([f"Stayed {nights} nights in {city} for {rng.choice(STAY_REASON)}.", f"Accommodation in {city} while on {rng.choice(STAY_REASON)}; {nights} nights.",
                                  f"{nights}-night stay at the {city} property during {rng.choice(STAY_REASON)}.", f"Lodging for {nights} nights, {city}, covering {rng.choice(STAY_REASON)}."]))
    form = dict(nights=nights, city=city, conference_ref=None, exception_ref=None)
    c = b.claim(group, arch, want, e, t, rng.randint(4, 25), m, "HOTEL", COUNTRY[reg], city, total, "HOTEL", form, d, project=project, charge_to=charge_to, key=key)
    if approval == "director": b.approval(key, e, "TRAVEL", level="DIRECTOR")
    return c, e, m, key


def build(b):
    rng = b.rng
    G = "B_WORKFLOW"

    # B1 hotel ceilings (9): profile + travel request
    for want, city, t, grade, nights, fac, trv in [
        ("APPROVE", "Singapore", "2025-06-16", 5, 3, 0.95, "APPROVED"), ("APPROVE", "Tokyo", "2025-08-18", 4, 2, 0.98, "APPROVED"),           # 34,884 > 34,000 base but within the amended 35,700
        ("APPROVE", "Mumbai", "2026-05-12", 6, 3, 0.97, "APPROVED"),                                                                            # 19,000 vs base 18,500 / amended 19,600
        ("REJECT", "Singapore", "2026-03-09", 3, 4, 1.15, "APPROVED"), ("REJECT", "Nagoya", "2025-04-14", 6, 16, 0.95, "APPROVED"),            # long stay factor
        ("REJECT", "Tokyo", "2025-05-19", 4, 2, 1.03, "APPROVED"),                                                                              # above base 34,000, before the July circular
        ("REQUEST_INFORMATION", "Pune", "2025-09-22", 5, 3, 0.9, "PENDING"), ("REQUEST_INFORMATION", "Singapore", "2024-10-07", 4, 2, 0.9, None),
        ("REQUEST_INFORMATION", "Fukuoka", "2026-02-16", 3, 3, 0.9, "REJECTED")]:
        hotel_claim(b, G, "B1", want, city, t, grade, nights, fac, travel=trv)
    # B2 conference lodging with the event quoted on the claim (6)
    for want, city, t, grade, fac, status, partner_ok, in [
        ("APPROVE", "Singapore", "2025-05-12", 5, 1.15, "REGISTERED", True), ("APPROVE", "Osaka", "2026-03-23", 4, 1.22, "REGISTERED", True), ("APPROVE", "Tokyo", "2025-09-15", 6, 1.15, "REGISTERED", True),
        ("REJECT", "Bengaluru", "2025-10-13", 5, 1.1, "REGISTERED", False), ("REJECT", "Singapore", "2026-04-20", 4, 1.1, "NOT_REGISTERED", True), ("REJECT", "Mumbai", "2025-02-17", 7, 1.3, "REGISTERED", True)]:
        key = b.key(); e = b.emp(None, grade, grade)
        # build through the helper for numbers, but attach the conference to the same employee
        loc = W.CITY_LOC[city]; reg = W.CITY_REGION[city]; base, _, _ = W.HOTEL.get((loc, W.band(grade)), t)
        nights = rng.randint(2, 4); nightly = round(base * fac, 2) if reg == "SG" else round(base * fac); total = round(nightly * nights, 2)
        hn = b.hotel(city); other = b.hotel(city)
        cf = b.conference(e, t, hn if partner_ok else other, status=status)
        b.travel(e, t, b.plus(t, nights), event=cf["event_id"], dest=city, purpose="Approved conference")
        d = _u(b, lambda: rng.choice([f"Stayed {nights} nights in {city} while attending {cf['event_name']} ({cf['event_id']}).", f"Lodging for {cf['event_name']} in {city}, {nights} nights; event reference {cf['event_id']}."]))
        c = b.claim(G, "B2", want, e, t, rng.randint(4, 25), hn, "HOTEL", COUNTRY[reg], city, float(total), "HOTEL", dict(nights=nights, city=city, conference_ref=cf["event_id"], exception_ref=None), d, key=key)
        b.approval(key, e, "TRAVEL", level="DIRECTOR")
    # B3 hotel-limit exception quoted on the claim (8)
    for want, city, t, grade, kind in [("APPROVE", "Singapore", "2025-03-24", 5, "ok"), ("APPROVE", "Tokyo", "2026-02-09", 6, "ok"), ("REJECT", "Osaka", "2025-11-10", 4, "expired"), ("REJECT", "Singapore", "2026-05-26", 3, "daterange"),
                                       ("ESCALATE", "Mumbai", "2025-07-14", 5, "policy"), ("ESCALATE", "Singapore", "2024-09-16", 6, "employee"), ("REQUEST_INFORMATION", "Pune", "2026-01-19", 4, "missing"), ("REQUEST_INFORMATION", "Fukuoka", "2025-12-08", 5, "notrip")]:
        key = b.key(); c, e, m, _ = hotel_claim(b, G, "B3", want, city, t, grade, rng.randint(2, 4), 1.3, travel=("PENDING" if kind == "notrip" else "APPROVED"), key=key)
        other = b.emp(None, 1, 8) if kind == "employee" else None
        if kind == "missing": ref = "EXC-" + str(rng.randint(900, 999)).zfill(4)
        else:
            vf, vt = (b.plus(t, -30), b.plus(t, 30)) if kind != "daterange" else (b.plus(t, -40), b.plus(t, -5))
            ex = b.exception(other or e, key, "AIR-2.2" if kind == "policy" else "TRV-6.1", status="EXPIRED" if kind == "expired" else "APPROVED", vf=vf, vt=vt); ref = ex["exception_id"]
        c["form"]["exception_ref"] = ref
        c["employee_description"] = _u(b, lambda: f"Stayed in {city} on the {c['employee_description'].split()[-3] if False else 'client'} trip; written exception {ref} covers the rate.")
    # B4 airfare (6)
    def air(want, arch, t, grade, cabin, hrs, ahead, trip="APPROVED", exc_kind=None, total=None, approval=False):
        e = b.emp(None, grade, grade); key = b.key(); dep = b.plus(t, ahead); m = b.merchant("AIRLINE", "SG", "Singapore")
        exc = None
        if trip: b.travel(e, dep, b.plus(dep, 3), status=trip, dest="Tokyo", exc=None)
        if exc_kind: exc = b.exception(e, key, "TRV-6.1" if exc_kind == "mismatch" else "AIR-2.2", vf=b.plus(t, -30), vt=b.plus(t, 60), etype="CABIN")
        total = total or {"ECONOMY": 420.0, "PREMIUM_ECONOMY": 640.0, "BUSINESS": 1850.0}[cabin]
        if approval: b.approval(key, e, "TRAVEL", level="DIRECTOR" if total > W.APPROVAL_SGD["director"][int(t[:4])] else "MANAGER")
        d = _u(b, lambda: rng.choice([f"Flight to {rng.choice(['Tokyo', 'Osaka', 'Mumbai', 'Bengaluru'])} for {rng.choice(STAY_REASON)}, {cabin.replace('_', ' ').lower()} fare.", f"Air ticket booked {ahead} days before departure for {rng.choice(STAY_REASON)}.", f"Return airfare, {hrs:g} hours each way, {cabin.replace('_', ' ').lower()}."]))
        c = b.claim(G, arch, want, e, t, rng.randint(2, 15), m, "AIRLINE", "Singapore", "Singapore", total, "AIRFARE", dict(cabin=cabin, flight_hours=hrs, booked_date=t, departure_date=dep, exception_ref=exc["exception_id"] if exc else None), d, key=key)
        return c
    air("APPROVE", "B4", "2025-07-08", 5, "PREMIUM_ECONOMY", 7.0, 30, approval=True)
    air("REJECT", "B4", "2025-03-10", 3, "PREMIUM_ECONOMY", 8.0, 25)
    air("REJECT", "B4", "2026-01-19", 5, "BUSINESS", 8.0, 21, total=1850.0)
    air("REQUEST_INFORMATION", "B4", "2024-11-04", 4, "ECONOMY", 6.5, 6)
    air("REQUEST_INFORMATION", "B4", "2025-09-02", 5, "ECONOMY", 5.0, 20, trip="PENDING")
    air("ESCALATE", "B4", "2026-02-23", 5, "BUSINESS", 9.5, 28, exc_kind="mismatch")

    # B5 software (8)
    def soft(want, t, total, billing="MONTHLY", appr="ok", proj="ACTIVE", cc="OPEN", budget=True):
        e = b.emp(); key = b.key(); m = b.merchant("SOFTWARE", None); big = total > 1000 and t >= "2026-02-01"
        pr = None
        if big:
            b.ids["CCS"] += 1; p = b.project(status=proj, cc=f"CC-S{b.ids['CCS']:02d}"); pr = p["project_id"]
            b.T["cost_centre_budgets"].append(dict(cost_centre=p["cost_centre"], year=int(t[:4]), budget_sgd=60000.0, committed_sgd=(59900.0 if not budget else 20000.0), status=cc))
        if appr == "ok": b.approval(key, e, "SOFTWARE")
        elif appr == "wrong": b.approval(key, e, "ENTERTAINMENT")
        d = _u(b, lambda: rng.choice([f"{billing.title()} plan for {m}, used by the {rng.choice(['research', 'design', 'reporting', 'security'])} group.", f"Subscription to {m} for the {rng.choice(EVENTS)}.", f"{m} licences, business owner is me; renewing for the team."]))
        return b.claim(G, "B5", want, e, t, rng.randint(2, 15), m, "SOFTWARE", "Singapore", "Singapore", float(total), "SOFTWARE", dict(business_owner=e["name"], billing=billing), d, project=pr, key=key)
    soft("APPROVE", "2025-06-24", 720)
    soft("REQUEST_INFORMATION", "2025-08-19", 640, appr=None)
    soft("REQUEST_INFORMATION", "2026-03-17", 1350, appr=None)
    soft("REQUEST_INFORMATION", "2026-05-05", 1250, budget=False)
    soft("ESCALATE", "2026-06-30", 1500, cc="FROZEN")
    soft("ESCALATE", "2026-04-21", 1200, proj="CLOSED")
    soft("ESCALATE", "2026-05-14", 1150, cc="FROZEN")
    soft("ESCALATE", "2025-09-29", 900, appr="wrong")

    # B6 duplicates and recurring (8): software charges below the approval tier
    def dup(want, kind, t, total):
        e = b.emp(); m = b.merchant("SOFTWARE", None); key = b.key(); bn = None
        if kind == "billno": bn = b.bill_no("D"); b.prev(e, m, b.plus(t, -rng.randint(6, 40)), total + 9, "SGD", "SOFTWARE", "Design tool seat", bill=bn)
        elif kind == "dateamt": b.prev(e, m, t, total, "SGD", "SOFTWARE", "Design tool seat")
        elif kind == "near": b.prev(e, m, b.plus(t, -rng.randint(1, 2)), round(total * 0.988, 2), "SGD", "SOFTWARE", "Design tool seat")
        elif kind == "near_same_day": b.prev(e, m, t, round(total * 1.015, 2), "SGD", "SOFTWARE", "Design tool seat")
        elif kind == "recurring": b.prev(e, m, b.plus(t, -rng.randint(28, 33)), round(total * rng.choice([1.0, 0.97, 1.03]), 2), "SGD", "SOFTWARE", "Recurring monthly subscription")
        d = _u(b, lambda: rng.choice([f"Seat at {m} for the {rng.choice(['research', 'design', 'reporting'])} group.", f"{m} charge for this period, business owner is me.", f"Subscription payment to {m}."]))
        c = b.claim(G, "B6", want, e, t, rng.randint(2, 15), m, "SOFTWARE", "Singapore", "Singapore", float(total), "SOFTWARE", dict(business_owner=e["name"], billing="MONTHLY"), d)
        if bn: c["bill"]["bill_number"] = bn
        return c
    for want, kind, t, total in [("REJECT", "billno", "2025-04-16", 180), ("REJECT", "dateamt", "2026-01-22", 240), ("REJECT", "billno", "2024-08-13", 95), ("REQUEST_INFORMATION", "near", "2025-11-18", 310),
                                 ("REQUEST_INFORMATION", "near", "2026-03-03", 145), ("REQUEST_INFORMATION", "near_same_day", "2025-02-25", 260), ("APPROVE", "recurring", "2026-06-15", 182), ("APPROVE", "recurring", "2025-05-21", 240)]:
        dup(want, kind, t, total)

    # B7 split transactions (8): equipment bought in two parts for the same project
    def split(want, reg, t, cur, prv, appr):
        e = b.emp(); key = b.key(); m = b.merchant("EQUIPMENT", reg, CITY[reg]); pj = b.project(); ccy = W.REGION[reg]["ccy"]
        b.prev(e, m, b.plus(t, -rng.randint(0, 2)), prv, ccy, "EQUIPMENT", "Project equipment purchase", project=pj["project_id"])
        if appr == "combined": b.approval(key, e, "COMBINED_SPEND")
        elif appr == "other": b.approval(key, e, "TRAVEL")
        d = _u(b, lambda: rng.choice([f"Second delivery of project equipment from {m}.", f"More kit for the {rng.choice(['lab', 'site', 'training room'])} from {m}, same project.", f"{m} order, follow-up to earlier purchase."]))
        return b.claim(G, "B7", want, e, t, rng.randint(2, 15), m, "EQUIPMENT", COUNTRY[reg], CITY[reg], float(cur), "EQUIPMENT", dict(item="project equipment"), d, project=pj["project_id"], key=key)
    for want, reg, t, cur, prv, appr in [("APPROVE", "SG", "2026-08-04", 290, 280, "combined"), ("REQUEST_INFORMATION", "SG", "2025-08-05", 285, 275, None), ("ESCALATE", "SG", "2025-07-08", 292, 281, "other"),
                                         ("REQUEST_INFORMATION", "IN", "2026-03-10", 11500, 10000, None), ("ESCALATE", "IN", "2025-09-15", 11800, 10100, "other"), ("REQUEST_INFORMATION", "JP", "2026-02-12", 28000, 24500, None),
                                         ("ESCALATE", "JP", "2026-04-08", 27500, 25000, "other"), ("ESCALATE", "JP", "2025-10-06", 26000, 24000, "other")]:
        split(want, reg, t, cur, prv, appr)

    # B8 gift annual ceilings (6)
    def gift(want, reg, t, cur, earlier, org=None):
        e = b.emp(); key = b.key(); m = b.merchant("GIFT_RETAIL", reg, CITY[reg]); org = org or rng.choice(ORGS); ccy = W.REGION[reg]["ccy"]
        for k, amt in enumerate(earlier): b.prev(e, b.merchant("GIFT_RETAIL", reg, CITY[reg]), b.plus(t[:4] + "-01-05", 40 * (k + 1)), amt, ccy, "GIFT", f"Gift to {org}", counterparty=org)
        b.prev(e, m, f"{int(t[:4]) - 1}-12-10", earlier[0], ccy, "GIFT", f"Gift to {org}", counterparty=org)                    # previous-year gift: must not count
        d = _u(b, lambda: rng.choice([f"Gift for {org} after {rng.choice(EVENTS)}, bought at {m}.", f"Another present for our contact at {org}; {m} receipt attached.", f"Hamper from {m} for {org}."]))
        return b.claim(G, "B8", want, e, t, rng.randint(2, 15), m, "GIFT_RETAIL", COUNTRY[reg], CITY[reg], float(cur), "GIFT", dict(recipient_name="Ms. Wu", recipient_org=org, recipient_type="COMMERCIAL", gift_form="ITEM"), d)
    for want, reg, t, cur, earlier in [("APPROVE", "SG", "2025-09-22", 110, [200, 140]), ("REJECT", "SG", "2025-11-04", 100, [200, 180]), ("REJECT", "IN", "2026-07-13", 4300, [6000, 5800]),
                                       ("APPROVE", "JP", "2025-06-30", 5400, [10500, 10000]), ("APPROVE", "SG", "2026-07-08", 128, [150, 150]), ("REJECT", "JP", "2024-10-21", 5500, [9500, 9500])]:
        gift(want, reg, t, cur, earlier)

    # B9 training ceilings (5)
    def train(want, reg, t, grade, cur, earlier, appr=None, level="MANAGER", atype="TRAINING"):
        e = b.emp(None, grade, grade); key = b.key(); m = b.merchant("TRAINING_PROVIDER", reg, CITY[reg]); ccy = W.REGION[reg]["ccy"]; fx = 1.0 if ccy == "SGD" else (0.0160 if ccy == "INR" else 0.0090)
        for k, amt in enumerate(earlier): b.prev(e, b.merchant("TRAINING_PROVIDER", reg, CITY[reg]), f"{t[:4]}-0{2 + k}-1{k + 1}", amt, ccy, "TRAINING", "External course")
        if appr: b.approval(key, e, atype, level=level)
        d = _u(b, lambda: rng.choice([f"Course at {m} on {rng.choice(['cloud security', 'data engineering', 'negotiation skills', 'leadership'])}.", f"Workshop fees, {m}; part of my development plan.", f"{m} programme registration."]))
        return b.claim(G, "B9", want, e, t, rng.randint(2, 15), m, "TRAINING_PROVIDER", COUNTRY[reg], CITY[reg], float(cur), "TRAINING", dict(learning_plan_id=f"LP-{rng.randint(1000, 9999)}", provider=m), d, key=key)
    train("APPROVE", "SG", "2025-06-11", 4, 900, [900, 900], appr=True)
    train("REQUEST_INFORMATION", "SG", "2026-03-04", 3, 800, [900, 800])
    train("REQUEST_INFORMATION", "SG", "2025-08-12", 6, 1900, [3000, 2200], appr=True, level="MANAGER")
    train("ESCALATE", "SG", "2026-05-18", 4, 1200, [2500, 1300], appr=True, atype="SOFTWARE")
    train("ESCALATE", "SG", "2025-09-24", 8, 5200, [3000, 2500], appr=True, level="DIRECTOR", atype="TRAINING")

    # B10 telecom monthly totals (3)
    def tele(want, reg, t, cur, earlier):
        e = b.emp(); m = b.merchant("TELECOM", reg, CITY[reg]); ccy = W.REGION[reg]["ccy"]
        for k, amt in enumerate(earlier): b.prev(e, m, f"{t[:7]}-0{2 + k}", amt, ccy, "TELECOM", "Mobile plan")
        b.prev(e, m, b.plus(t[:7] + "-01", -20), earlier[0], ccy, "TELECOM", "Mobile plan")                                       # previous month: must not count
        d = _u(b, lambda: rng.choice([f"Mobile data and calls for work, {m}.", f"{m} bill, business usage share.", f"Phone plan charge for client calls this month."]))
        return b.claim(G, "B10", want, e, t, rng.randint(2, 15), m, "TELECOM", COUNTRY[reg], CITY[reg], float(cur), "TELECOM", dict(billing_month=t[:7]), d)
    tele("REJECT", "SG", "2025-05-24", 45, [60]); tele("REJECT", "JP", "2026-09-22", 3200, [7500]); tele("APPROVE", "IN", "2025-07-25", 1100, [1200])

    # B11 approval tiers on large client events (6)
    def big(want, reg, t, total, n, appr=None, level="MANAGER", atype="GENERAL", ended=False):
        e = b.emp(); key = b.key(); m = b.merchant("RESTAURANT", reg, CITY[reg]); org = rng.choice(ORGS)
        if appr:
            b.approval(key, e, atype, level=level, start="2024-01-01", end=(b.plus(t, -3) if ended else "2026-12-31"))
        d = _u(b, lambda: rng.choice([f"Catering for the {org} summit reception at {m}; {n} people attended.", f"Client reception hosted for {org} at {m}, {n} guests and staff.", f"Large {rng.choice(MEALW)} for {org} delegates at {m}."]))
        return b.claim(G, "B11", want, e, t, rng.randint(2, 15), m, "RESTAURANT", COUNTRY[reg], CITY[reg], float(total), "MEAL_CLIENT",
                       dict(attendees_total=n, external_attendees=max(1, n // 2), external_names=f"delegates of {org}", alcohol_amount=0.0, tip_amount=0.0), d, key=key)
    big("REQUEST_INFORMATION", "SG", "2026-03-11", 1900, 16)
    big("REQUEST_INFORMATION", "IN", "2025-06-17", 70000, 20, appr=True, ended=True)
    big("ESCALATE", "IN", "2026-08-19", 90000, 24, appr=True, atype="SOFTWARE")
    big("ESCALATE", "JP", "2025-06-03", 150000, 14, appr=True, atype="TRAVEL")
    big("ESCALATE", "SG", "2025-10-15", 900, 8, appr=True, atype="SOFTWARE")
    big("ESCALATE", "SG", "2026-01-27", 1200, 10, appr=True, atype="TRAINING")

    # B12 restricted merchants (3)
    for want, name, risk, t in [("REJECT", "Golden Dice Casino", "RESTRICTED_PROHIBITED", "2025-04-18"), ("ESCALATE", "GiftCard Express", "RESTRICTED_REVIEW", "2026-02-24"), ("ESCALATE", "PrepaidPlus Reseller", "RESTRICTED_REVIEW", "2025-11-26")]:
        e = b.emp(); cat = "ENTERTAINMENT_VENUE" if risk == "RESTRICTED_PROHIBITED" else "PREPAID_CARD_RESELLER"; m = b.merchant(cat, "SG", "Singapore", risk=risk, name=name + f" {t[:4]}")
        d = _u(b, lambda: rng.choice([f"Client evening at {m}.", f"Payment to {m} for a client-related purchase.", f"{m} charge, business purpose explained on the form."]))
        b.claim(G, "B12", want, e, t, rng.randint(2, 15), m, cat, "Singapore", "Singapore", 240.0, "OTHER", {}, d)
    # B13 conference fees (2)
    for want, t, status in [("APPROVE", "2025-05-06", "REGISTERED"), ("REJECT", "2026-01-28", "NOT_REGISTERED")]:
        e = b.emp(); m = b.merchant("CONFERENCE_ORGANISER", None); cf = b.conference(e, b.plus(t, 30), "TBD", status=status, name=m)
        b.claim(G, "B13", want, e, t, rng.randint(2, 15), m, "CONFERENCE_ORGANISER", "Singapore", "Singapore", 480.0, "CONFERENCE_FEE", dict(conference_ref=cf["event_id"]),
                _u(b, lambda: f"Registration fee for {m} ({cf['event_id']}); attending for the {rng.choice(EVENTS)}."))
    # B14 car rental (2)
    for want, grade, t, appr in [("REJECT", 2, "2025-08-11", False), ("REQUEST_INFORMATION", 5, "2026-04-14", False)]:
        e = b.emp(None, grade, grade); m = b.merchant("CAR_RENTAL", None, name=f"DriveEasy Rentals {t[:4]}")
        b.claim(G, "B14", want, e, t, rng.randint(2, 15), m, "CAR_RENTAL", "Singapore", "Singapore", 210.0, "CAR_RENTAL", {}, _u(b, lambda: rng.choice([f"Hired a car from {m} for the site inspection day.", f"Rental from {m} for the regional visit."])))
