"""Group A: 40 self-contained cases (decision follows from the claim, the policy corpus and the FX table alone)."""
from __future__ import annotations
from . import world as W
from .builder import ORGS, EVENTS

CITY = {"SG": "Singapore", "IN": "Mumbai", "JP": "Tokyo"}
COUNTRY = {r: v["country"] for r, v in W.REGION.items()}
MEALW = ["dinner", "lunch", "supper", "working lunch", "team dinner"]
FIRSTN = ["Ms. Lim", "Mr. Rao", "Dr. Sato", "Ms. Iyer", "Mr. Tanaka", "Ms. Goh", "Mr. Menon", "Ms. Ito", "Mr. Chua", "Ms. Nair"]


def _u(b, fn, tries=30):
    for _ in range(tries):
        t = fn()
        if b.unique(t): return t
    raise RuntimeError("could not build a unique description")


def build(b):
    rng = b.rng

    def meal(want, arch, reg, t, et, pp, n, ext=0, names=True, alc=0.0, tip=0.0, age=None, drop_n=False, total=None, org=None):
        e = b.emp(); m = b.merchant("RESTAURANT", reg, CITY[reg])
        total = total if total is not None else round(pp * n, 2)
        org = org or rng.choice(ORGS); ev = rng.choice(EVENTS)
        form = dict(attendees_total=None if drop_n else n, external_attendees=ext, external_names=(f"{rng.choice(FIRSTN)} and {ext - 1 if ext > 1 else 'colleague'} from {org}" if names and ext else None), alcohol_amount=alc, tip_amount=tip)
        if et == "MEAL_EMPLOYEE":
            d = _u(b, lambda: rng.choice([f"{rng.choice(MEALW).capitalize()} at {m} for the {rng.choice(['delivery', 'platform', 'analytics', 'ops'])} team after {ev}; {n} of us, no guests.",
                                          f"Team {rng.choice(MEALW)} at {m} following {ev}. Colleagues only.", f"Working {rng.choice(['lunch', 'dinner'])} with the squad at {m} during {ev}. All employees."]))
        else:
            d = _u(b, lambda: rng.choice([f"Hosted {ext} guest(s) from {org} at {m} for {rng.choice(MEALW)} after {ev}. Party of {n if n else 'several'}.",
                                          f"Client {rng.choice(MEALW)} with {org} at {m} to follow up on {ev}; {ext} external attendee(s).", f"{org} visited us for {ev}, so we took them to {m} for {rng.choice(MEALW)}."]))
        it = [dict(description="Food and beverages", amount=round(total - alc - tip, 2))] + ([dict(description="Alcohol", amount=alc)] if alc else []) + ([dict(description="Gratuity", amount=tip)] if tip else [])
        return b.claim("A_SELF_CONTAINED", arch, want, e, t, age if age is not None else rng.randint(3, 25), m, "RESTAURANT", COUNTRY[reg], CITY[reg], total, et, form, d, it)

    # A1 employee meals (5): amendments and mid-year values
    meal("APPROVE", "A1", "SG", "2025-10-14", "MEAL_EMPLOYEE", 51.5, 3)
    meal("APPROVE", "A1", "IN", "2025-11-20", "MEAL_EMPLOYEE", 2080, 4)
    meal("APPROVE", "A1", "JP", "2026-03-10", "MEAL_EMPLOYEE", 5450, 4)
    meal("REJECT", "A1", "SG", "2025-08-20", "MEAL_EMPLOYEE", 51, 4)
    meal("REJECT", "A1", "JP", "2025-11-05", "MEAL_EMPLOYEE", 5350, 3)
    # A2 client meals (5)
    meal("APPROVE", "A2", "SG", "2025-08-05", "MEAL_CLIENT", 127, 3, ext=1)
    meal("APPROVE", "A2", "JP", "2026-06-12", "MEAL_CLIENT", 13400, 3, ext=2)
    meal("REJECT", "A2", "SG", "2025-04-15", "MEAL_CLIENT", 125, 3, ext=1)
    meal("REQUEST_INFORMATION", "A2", "IN", "2026-02-10", "MEAL_CLIENT", 4800, 3, ext=2, names=False)
    meal("REQUEST_INFORMATION", "A2", "SG", "2024-09-17", "MEAL_CLIENT", 0, 0, ext=2, drop_n=True, total=420.0)
    # A3 alcohol (5)
    meal("REJECT", "A3", "IN", "2025-05-14", "MEAL_CLIENT", 2133.33, 3, ext=2, alc=800.0, total=6400.0)
    meal("REJECT", "A3", "SG", "2026-02-18", "MEAL_CLIENT", 100, 4, ext=2, alc=140.0, total=400.0)
    meal("REJECT", "A3", "SG", "2025-06-10", "MEAL_EMPLOYEE", 45, 4, ext=0, alc=30.0, total=180.0)
    meal("APPROVE", "A3", "JP", "2025-09-09", "MEAL_CLIENT", 10666.67, 3, ext=2, alc=8000.0, total=32000.0)
    meal("APPROVE", "A3", "SG", "2024-11-12", "MEAL_CLIENT", 120, 3, ext=1, alc=118.8, total=360.0)
    # A11 gratuity in Japan (1)
    meal("REJECT", "A11", "JP", "2026-04-18", "MEAL_CLIENT", 12000, 3, ext=2, tip=3000.0, total=36000.0)

    # A4 personal spend (2)
    for reg, t, total in (("SG", "2026-03-04", 24.9), ("JP", "2025-08-22", 9800.0)):
        e = b.emp(); m = b.merchant("CONSUMER_SERVICE", reg, CITY[reg])
        d = _u(b, lambda: rng.choice([f"Monthly {rng.choice(['subscription', 'membership'])} at {m}, mostly for home use.", f"{m} charge that landed on my card; I use it in the evenings for myself.", f"Renewal for {m}; keeps me sane during the busy quarter."]))
        b.claim("A_SELF_CONTAINED", "A4", "REJECT", e, t, rng.randint(3, 20), m, "CONSUMER_SERVICE", COUNTRY[reg], CITY[reg], total, "OTHER", {}, d)

    # A5 submission windows (6): small equipment purchases
    def eq(want, reg, t, age, total, approval_ref=None):
        e = b.emp(); m = b.merchant("EQUIPMENT", reg, CITY[reg]); item = rng.choice(["USB-C hub", "wireless mouse", "laptop stand", "HDMI adapter", "noise-cancelling headset", "webcam", "monitor arm"])
        d = _u(b, lambda: rng.choice([f"Bought a {item} at {m} for the project room.", f"{item.capitalize()} from {m}; needed it for the {rng.choice(['analytics', 'sales', 'support'])} desk.", f"Small purchase of a {item} at {m}."]))
        c = b.claim("A_SELF_CONTAINED", "A5", want, e, t, age, m, "EQUIPMENT", COUNTRY[reg], CITY[reg], total, "EQUIPMENT", dict(item=item), d)
        return c
    eq("APPROVE", "SG", "2025-06-12", 44, 89.0)
    eq("REJECT", "SG", "2024-05-06", 63, 120.0)
    eq("ESCALATE", "SG", "2025-06-02", 96, 150.0)
    eq("ESCALATE", "SG", "2026-04-10", 80, 210.0)
    eq("REQUEST_INFORMATION", "SG", "2026-05-11", 60, 175.0)
    eq("APPROVE", "IN", "2026-03-19", 58, 7400.0)

    # A6 ground transport (4)
    def gt(want, reg, t, total, otype, dtype, origin, dest, dep=None, end=None):
        e = b.emp(); m = b.merchant("RIDE_HAIL", reg, CITY[reg])
        d = _u(b, lambda: rng.choice([f"Cab ride with {m} {('to ' + dest) if dest else 'for a meeting'}.", f"Took a {m} ride after {rng.choice(['a late review', 'the client call', 'the site visit'])}.", f"{m} fare; details on the receipt."]))
        return b.claim("A_SELF_CONTAINED", "A6", want, e, t, rng.randint(3, 20), m, "RIDE_HAIL", COUNTRY[reg], CITY[reg], total, "GROUND_TRANSPORT",
                       dict(origin=origin, destination=dest, origin_type=otype, destination_type=dtype, departure_time=dep, activity_end_time=end), d)
    gt("REQUEST_INFORMATION", "SG", "2025-03-25", 22.0, "OTHER", "CLIENT_SITE", None, "Client office")
    gt("REJECT", "IN", "2026-01-15", 420.0, "HOME", "OFFICE", "Home", "Bengaluru office")
    gt("APPROVE", "SG", "2025-10-22", 34.0, "OFFICE", "HOME", "Office", "Home", "22:40", "22:05")
    gt("APPROVE", "JP", "2025-05-29", 6800.0, "AIRPORT", "CLIENT_SITE", "Haneda Airport", "Client site in Shinagawa")

    # A7 mileage (2)
    for want, reg, t, km, total in (("APPROVE", "SG", "2025-09-16", 48, 28.8), ("REJECT", "IN", "2026-04-08", 120, 1620.0)):
        e = b.emp(); m = b.merchant("MILEAGE", reg, CITY[reg], name=f"Private vehicle mileage {reg} {t[:4]}")
        d = _u(b, lambda: rng.choice([f"Drove my own car to the client site and back, {km} km in total.", f"Personal vehicle used for the site inspection; odometer shows {km} km.", f"Mileage for the {rng.choice(['warehouse', 'plant', 'data centre'])} visit, {km} km."]))
        b.claim("A_SELF_CONTAINED", "A7", want, e, t, rng.randint(3, 20), m, "MILEAGE", COUNTRY[reg], CITY[reg], total, "MILEAGE", dict(distance_km=km), d)

    # A8 gifts (4)
    def gift(want, reg, t, total, rtype="COMMERCIAL", gform="ITEM", org=None, name="Ms. Ho", org_missing=False):
        e = b.emp(); m = b.merchant("GIFT_RETAIL", reg, CITY[reg]); org = org or rng.choice(ORGS)
        d = _u(b, lambda: rng.choice([f"Thank-you present for a contact at {org}, bought at {m}.", f"Small gift for the {org} team after {rng.choice(EVENTS)}.", f"{m} purchase, a gift for our counterpart at {org}."]))
        return b.claim("A_SELF_CONTAINED", "A8", want, e, t, rng.randint(3, 20), m, "GIFT_RETAIL", COUNTRY[reg], CITY[reg], total, "GIFT",
                       dict(recipient_name=name, recipient_org=None if org_missing else org, recipient_type=rtype, gift_form=gform), d)
    gift("REJECT", "JP", "2026-02-03", 5500.0, rtype="GOVERNMENT", org="Ministry of Trade Liaison Office")
    gift("REJECT", "SG", "2025-12-05", 100.0, gform="CASH_EQUIVALENT")
    gift("REJECT", "SG", "2026-06-20", 140.0)
    gift("REQUEST_INFORMATION", "IN", "2025-04-11", 3800.0, org_missing=True)

    # A9 evidence conflict (2)
    e = b.emp(); m = b.merchant("RESTAURANT", "SG", "Singapore")
    b.claim("A_SELF_CONTAINED", "A9", "REQUEST_INFORMATION", e, "2025-08-27", 9, m, "RESTAURANT", "Singapore", "Singapore", 96.0, "MEAL_EMPLOYEE", dict(attendees_total=2, external_attendees=0, external_names=None, alcohol_amount=0.0, tip_amount=0.0),
            _u(b, lambda: "Taxi from the airport to the customer office after a delayed flight."))
    e = b.emp(); m = b.merchant("RIDE_HAIL", "IN", "Mumbai")
    b.claim("A_SELF_CONTAINED", "A9", "REQUEST_INFORMATION", e, "2026-02-25", 11, m, "RIDE_HAIL", "India", "Mumbai", 1890.0, "GROUND_TRANSPORT",
            dict(origin="Bandra Kurla Complex", destination="Andheri", origin_type="CLIENT_SITE", destination_type="CLIENT_SITE", departure_time=None, activity_end_time=None), _u(b, lambda: "Two nights at the hotel next to the conference venue."))

    # A10 equipment tiers (2)
    for want, reg, t, total in (("APPROVE", "JP", "2025-07-14", 25000.0), ("REJECT", "SG", "2026-01-20", 1899.0)):
        e = b.emp(); m = b.merchant("EQUIPMENT", reg, CITY[reg]); item = "docking station" if want == "APPROVE" else "workstation laptop"
        b.claim("A_SELF_CONTAINED", "A10", want, e, t, rng.randint(3, 20), m, "EQUIPMENT", COUNTRY[reg], CITY[reg], total, "EQUIPMENT", dict(item=item),
                _u(b, lambda: rng.choice([f"{item.capitalize()} bought at {m} for my desk.", f"Replacement {item} from {m}.", f"{m} order: one {item} for daily work."])))

    # A12 large-looking local amounts that convert to small SGD (2)
    for reg, t, total in (("JP", "2025-05-22", 44000.0),):
        e = b.emp(); m = b.merchant("SOFTWARE", None); m2 = m
        b.claim("A_SELF_CONTAINED", "A12", "APPROVE", e, t, rng.randint(3, 20), m2, "SOFTWARE", COUNTRY[reg], CITY[reg], total, "SOFTWARE", dict(business_owner=e["name"], billing="MONTHLY"),
                _u(b, lambda: rng.choice([f"Monthly seat for {m2}, used by the {rng.choice(['research', 'design', 'reporting'])} group.", f"{m2} subscription charge for this month's project work.", f"Licence renewal at {m2}; I own it for the team."])))

    # A13 above the Finance review threshold: escalated from the claim alone (1)
    e = b.emp(); m = b.merchant("RESTAURANT", "SG", "Singapore"); org = rng.choice(ORGS)
    b.claim("A_SELF_CONTAINED", "A13", "ESCALATE", e, "2025-05-27", 12, m, "RESTAURANT", "Singapore", "Singapore", 5600.0, "MEAL_CLIENT",
            dict(attendees_total=50, external_attendees=30, external_names=f"delegates of {org}", alcohol_amount=0.0, tip_amount=0.0),
            _u(b, lambda: f"Reception for the {org} regional summit at {m}; fifty guests and staff attended."))
