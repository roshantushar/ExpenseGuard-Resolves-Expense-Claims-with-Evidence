"""Group C: 30 dynamic agent-candidate cases. Which record must be read next depends on what the previous lookup returned, and chains are 3 to 6 lookups deep."""
from __future__ import annotations
from . import world as W
from .builder import ORGS, EVENTS
from .cases_a import COUNTRY, MEALW, _u
from .cases_b import STAY_REASON

G = "C_AGENT_DYNAMIC"


def hotel_dyn(b, arch, want, city, t, grade, nights, fac, event=None, exc=None, approval="director", trip="APPROVED"):
    """Hotel claim with NO reference on the claim; the travel record carries the linked event / exception identifiers.
    event: None or (status, partner_ok). exc: None or kind in ok|expired|policy|employee|missing."""
    rng = b.rng; loc = W.city_tier(city); reg = W.CITY_REGION[city]; e = b.emp(None, grade, grade); key = b.key()
    base, _, _ = W.HOTEL.get((loc, W.band(grade)), t)
    nightly = round(base * fac, 2) if reg == "SG" else round(base * fac); total = round(nightly * nights, 2)
    hn = b.hotel(city); other_h = b.hotel(city); ev_id = exc_id = None
    if event:
        cf = b.conference(e, t, hn if event[1] else other_h, status=event[0]); ev_id = cf["event_id"]
    if exc:
        if exc == "missing": exc_id = "EXC-" + str(rng.randint(900, 999)).zfill(4)
        else:
            oth = b.emp(None, 1, 8) if exc == "employee" else e
            ex = b.exception(oth, key, "AIR-2.2" if exc == "policy" else "TRV-6.1", status="EXPIRED" if exc == "expired" else "APPROVED", vf=b.plus(t, -20), vt=b.plus(t, 40)); exc_id = ex["exception_id"]
    if trip: b.travel(e, t, b.plus(t, nights), status=trip, event=ev_id, exc=exc_id, dest=city, purpose="Business trip")
    d = _u(b, lambda: rng.choice([f"Stayed {nights} nights in {city} for {rng.choice(STAY_REASON)}.", f"Accommodation in {city}, {nights} nights, {rng.choice(STAY_REASON)}.", f"{nights}-night stay in {city} covering {rng.choice(STAY_REASON)}."]))
    c = b.claim(G, arch, want, e, t, rng.randint(4, 25), hn, "HOTEL", COUNTRY[reg], city, float(total), "HOTEL", dict(nights=nights, city=city, conference_ref=None, exception_ref=None), d, key=key)
    if approval == "director": b.approval(key, e, "TRAVEL", level="DIRECTOR")
    return c, e, key


def build(b):
    rng = b.rng
    # C1 hotel discovery (10): travel request -> conference and/or exception, depending on what it links
    # 4 of the 10 use a city not in TRV-2.2's tier table (Chennai/Kobe): its ceiling is resolvable only by
    # retrieving and applying TRV-2.2's stated fallback rule (see world.city_tier's docstring); the
    # deterministic engine cannot resolve them at all (src/rules_v2.py's TIER lookup has no entry for
    # them and returns None), so these are genuinely RAG-necessary, not just RAG-assisted.
    hotel_dyn(b, "C1", "APPROVE", "Singapore", "2025-05-19", 5, 3, 1.15, event=("REGISTERED", True))
    hotel_dyn(b, "C1", "REQUEST_INFORMATION", "Chennai", "2026-06-08", 4, 3, 1.3, exc="missing")
    hotel_dyn(b, "C1", "REJECT", "Kobe", "2026-02-16", 5, 3, 1.12, event=("NOT_REGISTERED", True))
    hotel_dyn(b, "C1", "REJECT", "Singapore", "2025-09-01", 6, 4, 1.1, event=("REGISTERED", False))
    hotel_dyn(b, "C1", "APPROVE", "Kobe", "2025-11-17", 6, 3, 1.2, event=("NOT_REGISTERED", True), exc="ok")
    hotel_dyn(b, "C1", "ESCALATE", "Singapore", "2026-04-27", 5, 3, 1.3, event=("REGISTERED", False), exc="policy")
    hotel_dyn(b, "C1", "ESCALATE", "Chennai", "2025-08-25", 5, 2, 1.3, exc="employee")
    hotel_dyn(b, "C1", "ESCALATE", "Osaka", "2025-06-23", 4, 3, 1.3, exc="policy")
    hotel_dyn(b, "C1", "ESCALATE", "Singapore", "2024-10-14", 5, 2, 1.3, exc="policy")
    hotel_dyn(b, "C1", "ESCALATE", "Nagoya", "2026-03-30", 6, 3, 1.5, event=("REGISTERED", True), exc="employee")

    # C2 approval delegation chain (8): approval record says DELEGATED -> delegation record -> limit / level / validity
    def deleg(want, t, total, n, kind):
        e = b.emp(); key = b.key(); m = b.merchant("RESTAURANT", "SG", "Singapore"); org = rng.choice(ORGS); y = int(t[:4])
        lvl_needed = "DIRECTOR" if total > W.APPROVAL_SGD["director"][y] else "MANAGER"
        s, en, limit, dl = b.plus(t, -30), b.plus(t, 30), total + 500, lvl_needed
        if kind == "expired": s, en = b.plus(t, -60), b.plus(t, -10)
        elif kind == "notyet": s, en = b.plus(t, 5), b.plus(t, 40)
        elif kind == "limit": limit = total - 150
        elif kind == "level": dl = "MANAGER"
        dg = b.delegation(e["manager_id"], dl, s, en, float(limit))
        b.approval(key, e, "GENERAL", status="DELEGATED", level="MANAGER", deleg=dg["delegation_id"])
        d = _u(b, lambda: rng.choice([f"Client reception for {org} at {m}, {n} people.", f"Hosted {org} delegates for {rng.choice(MEALW)} at {m}; {n} attended.", f"{m}: {rng.choice(MEALW)} with {org} after {rng.choice(EVENTS)}, party of {n}."]))
        b.claim(G, "C2", want, e, t, rng.randint(3, 15), m, "RESTAURANT", "Singapore", "Singapore", float(total), "MEAL_CLIENT",
                dict(attendees_total=n, external_attendees=n // 2, external_names=f"delegates from {org}", alcohol_amount=0.0, tip_amount=0.0), d, key=key)
    for want, t, total, n, kind in [("APPROVE", "2025-06-10", 900, 10, "ok"), ("APPROVE", "2025-08-19", 1800, 18, "ok"), ("REQUEST_INFORMATION", "2025-04-08", 1100, 12, "expired"), ("REQUEST_INFORMATION", "2026-02-24", 950, 10, "notyet"),
                                    ("ESCALATE", "2025-07-15", 1200, 13, "limit"), ("ESCALATE", "2025-10-21", 1600, 16, "level"), ("ESCALATE", "2026-03-25", 2300, 20, "level"), ("ESCALATE", "2026-05-13", 950, 10, "limit")]:
        deleg(want, t, total, n, kind)

    # C3 project / budget chain (6): project -> parent project -> cost-centre budget
    cnt = [0]
    def proj_chain(want, t, total, kind):
        e = b.emp(); key = b.key(); m = b.merchant("SOFTWARE", None); cnt[0] += 1; ccn = f"CC-P{cnt[0]:02d}"; y = int(t[:4])
        par_status = "CLOSED" if kind == "parent_closed" else "ACTIVE"
        if kind == "no_parent":
            child = b.project(status="ACTIVE", cc=ccn)
        else:
            par = b.project(status=par_status, cc=ccn); child = b.project(parent=par["project_id"], status="CLOSED" if kind == "child_closed" else "ACTIVE", cc=f"CC-C{cnt[0]:02d}")
        status = "FROZEN" if kind == "frozen" else "OPEN"; committed = 59900.0 if kind in ("budget_short", "no_parent") else 12000.0
        b.T["cost_centre_budgets"].append(dict(cost_centre=ccn, year=y, budget_sgd=60000.0, committed_sgd=committed, status=status))
        b.approval(key, e, "SOFTWARE")
        d = _u(b, lambda: rng.choice([f"Annual-tier plan at {m} for the {rng.choice(['research', 'platform', 'insights'])} project.", f"{m} licences charged to the project; I am the business owner.", f"Subscription for {m}, project work."]))
        b.claim(G, "C3", want, e, t, rng.randint(3, 15), m, "SOFTWARE", "Singapore", "Singapore", float(total), "SOFTWARE", dict(business_owner=e["name"], billing="MONTHLY"), d, project=child["project_id"], charge_to="PROJECT", key=key)
    for want, t, total, kind in [("APPROVE", "2026-03-12", 1400, "ok"), ("ESCALATE", "2026-04-06", 1250, "parent_closed"), ("ESCALATE", "2026-05-20", 1800, "frozen"), ("ESCALATE", "2026-06-09", 1100, "frozen"),
                                 ("REQUEST_INFORMATION", "2026-07-14", 1550, "budget_short"), ("REQUEST_INFORMATION", "2026-08-25", 1300, "no_parent")]:
        proj_chain(want, t, total, kind)

    # C4 deep chain (6): hotel, exception or conference from the travel record, then a director-level approval that may be delegated
    def deep(want, t, fac, kind):
        y = int(t[:4]); nights = 5
        ev = ("REGISTERED", True) if kind == "conf_level" else None
        exc = None if kind == "conf_level" else ("expired" if kind == "exc_expired" else "ok")
        c, e, key = hotel_dyn(b, "C4", want, "Singapore", t, 5, nights, fac, event=ev, exc=exc, approval="none")
        need = "DIRECTOR"; total = c["bill"]["total"]
        s, en, limit, dl = b.plus(t, -30), b.plus(t, 30), total + 800, "DIRECTOR"
        if kind == "deleg_expired": s, en = b.plus(t, -60), b.plus(t, -5)
        elif kind == "deleg_limit": limit = 1500.0
        elif kind == "conf_level": dl = "MANAGER"
        if kind == "approved_manager": b.approval(key, e, "TRAVEL", level="MANAGER")
        elif kind != "exc_expired":
            dg = b.delegation(e["manager_id"], dl, s, en, float(limit)); b.approval(key, e, "TRAVEL", status="DELEGATED", level="MANAGER", deleg=dg["delegation_id"])
    for want, t, fac, kind in [("APPROVE", "2025-06-30", 1.3, "ok"), ("REJECT", "2025-08-05", 1.3, "exc_expired"), ("REQUEST_INFORMATION", "2026-03-16", 1.3, "deleg_expired"), ("REQUEST_INFORMATION", "2025-11-25", 1.3, "approved_manager"),
                               ("ESCALATE", "2026-04-13", 1.3, "deleg_limit"), ("ESCALATE", "2025-09-08", 1.15, "conf_level")]:
        deep(want, t, fac, kind)
