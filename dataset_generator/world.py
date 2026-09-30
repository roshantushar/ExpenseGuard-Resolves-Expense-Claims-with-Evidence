"""ExpenseGuard V2 - world model: one structured source of truth for every number in the policy corpus.
The policy text (policy.py) and the reference engine (engine.py) both read these schedules, so text and labels cannot disagree."""
from __future__ import annotations
import random
from datetime import date, timedelta

SEED = 6202
YEARS = [2024, 2025, 2026]
REGION = {"SG": {"country": "Singapore", "ccy": "SGD"}, "IN": {"country": "India", "ccy": "INR"}, "JP": {"country": "Japan", "ccy": "JPY"}}
COUNTRY_TO_REGION = {v["country"]: k for k, v in REGION.items()}
BANDS = [("G1-G3", 1, 3), ("G4-G5", 4, 5), ("G6-G7", 6, 7), ("G8+", 8, 9)]


def band(grade: int) -> str:
    return next(n for n, lo, hi in BANDS if lo <= grade <= hi)


def yv(a, b, c):
    return {2024: a, 2025: b, 2026: c}


# ---------------------------------------------------------------- amendments (finance circulars)
# kind: 'set' (absolute new value) or 'pct' (percentage change, rounded to `round`). Applies from `eff` until the end of that year.
AMEND = [
    dict(id="CIRC-24-07", eff="2024-07-01", sched=None, key=None, title="Conference partner-hotel amendment",
         note="For approved conferences from 1 July 2024 the partner-hotel uplift applies even when the trip request was approved before the conference registry entry was created."),
    dict(id="CIRC-25-03", eff="2025-03-01", sched=None, key=None, title="Finance system outage relief",
         note="For transactions dated 10 March 2025 to 14 March 2025 inclusive, formally recorded system outage relief applies: the Finance-escalation tier for late submission is replaced by the manager-approval tier."),
    dict(id="CIRC-25-04", eff="2025-04-01", sched="AIR_PE_HOURS", key="ALL", kind="set", value=5.5, title="Premium economy threshold revision"),
    dict(id="CIRC-25-06", eff="2025-07-01", sched="HOTEL", key="JP-TOKYO", kind="pct", value=5, round=100, title="Tokyo accommodation uplift"),
    dict(id="CIRC-25-07", eff="2025-07-01", sched="CLIENT_MEAL", key="SG", kind="set", value=128, title="Singapore client meal ceiling revision"),
    dict(id="CIRC-25-09", eff="2025-09-01", sched="EMP_MEAL", key="SG", kind="set", value=52, title="Singapore employee meal ceiling revision"),
    dict(id="CIRC-25-10", eff="2025-10-01", sched="EMP_MEAL", key="JP", kind="set", value=5200, title="Japan employee meal ceiling revision"),
    dict(id="CIRC-25-11", eff="2025-11-01", sched="EMP_MEAL", key="IN", kind="set", value=2100, title="India employee meal ceiling revision"),
    dict(id="CIRC-26-02", eff="2026-02-01", sched=None, key=None, title="Software approval circular",
         note="Software subscriptions above SGD 1000 equivalent require both manager approval and an active project record with an open cost centre, from 1 February 2026."),
    dict(id="CIRC-26-04", eff="2026-04-01", sched="HOTEL", key="IN-T1", kind="pct", value=6, round=100, title="India Tier-1 accommodation uplift"),
    dict(id="CIRC-26-05", eff="2026-05-01", sched="CLIENT_MEAL", key="JP", kind="set", value=13500, title="Japan client meal ceiling revision"),
    dict(id="CIRC-26-06", eff="2026-06-01", sched="GIFT", key="SG", kind="set", value=130, title="Singapore gift ceiling revision"),
]
OUTAGE = ("2025-03-10", "2025-03-14")


class Sched:
    """Effective-dated schedule with amendments. get(key, date) -> (value, controlling_clause_ids, context_clause_ids)."""

    def __init__(self, name, base, clause_by_year):
        self.name, self.base, self.cby = name, base, clause_by_year

    def clause(self, key, y):
        return self.cby(key, y) if callable(self.cby) else self.cby[y]

    def get(self, key, d: str):
        y = int(d[:4])
        v, ctrl, ctx = self.base[key][y], [self.clause(key, y)], []
        for a in sorted((a for a in AMEND if a["sched"] == self.name and a["key"] in (key, "ALL")), key=lambda a: a["eff"]):
            if a["eff"] <= d and a["eff"][:4] == str(y):
                base_v = v
                if a["kind"] == "set":
                    v = a["value"]
                else:
                    r = a["round"]
                    v = int(int(base_v * (100 + a["value"]) / 100 / r + 0.5) * r)
                ctx += ctrl
                ctrl = [a["id"]]
        return v, ctrl, ctx

    def keys(self):
        return list(self.base)


EMP_MEAL = Sched("EMP_MEAL", {"SG": yv(45, 50, 55), "IN": yv(1800, 2000, 2200), "JP": yv(4500, 5000, 5500)}, lambda k, y: f"{k}-2.1")
CLIENT_MEAL = Sched("CLIENT_MEAL", {"SG": yv(120, 120, 130), "IN": yv(4500, 4500, 5000), "JP": yv(12000, 12000, 13000)}, lambda k, y: f"{k}-2.2")
ENTERTAIN = Sched("ENTERTAIN", {"SG": yv(180, 190, 200), "IN": yv(6500, 7000, 7500), "JP": yv(16000, 17000, 18000)}, lambda k, y: f"{k}-2.3")
GIFT = Sched("GIFT", {"SG": yv(100, 120, 120), "IN": yv(3500, 4000, 4500), "JP": yv(6000, 6000, 7000)}, lambda k, y: f"{k}-3.1")
GIFT_ANNUAL = Sched("GIFT_ANNUAL", {"SG": yv(400, 450, 450), "IN": yv(14000, 15000, 16000), "JP": yv(24000, 26000, 28000)}, lambda k, y: f"{k}-3.2")
TELECOM = Sched("TELECOM", {"SG": yv(80, 90, 90), "IN": yv(2500, 2500, 3000), "JP": yv(9000, 9000, 10000)}, lambda k, y: f"{k}-5.1")
MILEAGE = Sched("MILEAGE", {"SG": yv(0.60, 0.60, 0.65), "IN": yv(11, 12, 12), "JP": yv(35, 37, 37)}, lambda k, y: f"{k}-4.1")
TRAIN_CAP = Sched("TRAIN_CAP", {"G1-G3": yv(1800, 2000, 2200), "G4-G5": yv(3200, 3500, 3800), "G6-G7": yv(4800, 5000, 5400), "G8+": yv(6500, 7000, 7500)},
                  {2024: "TRN-2.1", 2025: "TRN-2.2", 2026: "TRN-2.3"})
AIR_PE_HOURS = Sched("AIR_PE_HOURS", {"ALL": yv(6.0, 6.0, 6.0)}, {2024: "AIR-2.1", 2025: "AIR-2.1", 2026: "AIR-2.1"})
_H = {"SG-CENTRAL": {"G1-G3": yv(280, 300, 320), "G4-G5": yv(330, 350, 370), "G6-G7": yv(390, 410, 430), "G8+": yv(480, 500, 520)},
      "IN-T1": {"G1-G3": yv(9000, 10000, 11000), "G4-G5": yv(12000, 13000, 14500), "G6-G7": yv(16000, 17000, 18500), "G8+": yv(21000, 22000, 24000)},
      "IN-T2": {"G1-G3": yv(6000, 6500, 7000), "G4-G5": yv(8500, 9000, 9800), "G6-G7": yv(11000, 11800, 12800), "G8+": yv(15000, 16000, 17500)},
      "JP-TOKYO": {"G1-G3": yv(28000, 30000, 32000), "G4-G5": yv(32000, 34000, 36000), "G6-G7": yv(38000, 40000, 42000), "G8+": yv(46000, 49000, 52000)},
      "JP-MAJOR": {"G1-G3": yv(24000, 25500, 27500), "G4-G5": yv(28000, 29500, 31500), "G6-G7": yv(34000, 35500, 37500), "G8+": yv(41000, 43000, 46000)},
      "JP-OTHER": {"G1-G3": yv(20000, 21500, 23000), "G4-G5": yv(24000, 25500, 27000), "G6-G7": yv(29000, 30500, 32500), "G8+": yv(35000, 37000, 39500)}}


class _Hotel(Sched):
    def __init__(self):
        super().__init__("HOTEL", {(loc, b): v for loc, bands in _H.items() for b, v in bands.items()}, {2024: "TRV-3.1", 2025: "TRV-3.2", 2026: "TRV-3.3"})

    def get(self, loc_band, d):  # loc_band = (loc, band)
        loc, b = loc_band
        y = int(d[:4])
        v, ctrl, ctx = self.base[(loc, b)][y], [self.cby[y]], []
        for a in sorted((a for a in AMEND if a["sched"] == "HOTEL" and a["key"] == loc), key=lambda a: a["eff"]):
            if a["eff"] <= d and a["eff"][:4] == str(y):
                v = int(int(v * (100 + a["value"]) / 100 / a["round"] + 0.5) * a["round"]); ctx += ctrl; ctrl = [a["id"]]
        return v, ctrl, ctx


HOTEL = _Hotel()
HOTEL_LOCS = {"SG-CENTRAL": ["Singapore"], "IN-T1": ["Mumbai", "Delhi", "Bengaluru"], "IN-T2": ["Pune", "Jaipur", "Kochi"], "JP-TOKYO": ["Tokyo"], "JP-MAJOR": ["Osaka", "Nagoya", "Yokohama"], "JP-OTHER": ["Fukuoka", "Sapporo", "Sendai"]}
CITY_LOC = {c: loc for loc, cs in HOTEL_LOCS.items() for c in cs}
CITY_REGION = {c: loc[:2] for c, loc in CITY_LOC.items()}
# V3: cities deliberately left OUT of HOTEL_LOCS/CITY_LOC (so TRV-2.2's rendered tier table never lists
# them) but given a region here so a case can still be placed there. TRV-2.2 already states the fallback
# rule for exactly this situation: "A city not listed takes the lowest tier for its country." Ground
# truth (city_tier, used by dataset_generator.engine) implements that rule; src/rules_v2.py's runtime TIER
# table deliberately does not, so these claims can only be resolved by retrieving and applying TRV-2.2's
# text, not by a table lookup (see docs/exp09b_rag_necessity.md).
CITY_REGION.update({"Chennai": "IN", "Kobe": "JP"})
LOWEST_TIER = {"SG": "SG-CENTRAL", "IN": "IN-T2", "JP": "JP-OTHER"}


def city_tier(city: str) -> str:
    """Ground-truth-only tier resolution: the listed tier if the city is in CITY_LOC, otherwise TRV-2.2's
    stated fallback (the lowest tier for the city's country). Never imported by src/rules_v2.py."""
    return CITY_LOC.get(city) or LOWEST_TIER[CITY_REGION[city]]
CONF_UPLIFT = {2024: 20, 2025: 20, 2026: 25}          # percent, official partner hotel of a registered approved conference
LONG_STAY_NIGHTS, LONG_STAY_FACTOR = 14, 90          # stays longer than 14 nights: 90 percent of the ceiling (from 2025-01-01)

# ---------------------------------------------------------------- fixed rule parameters
SUBMIT = {2024: dict(ok=60), 2025: dict(ok=45, approval=90), 2026: dict(ok=45, approval=75)}
IN_SUBMIT_2026 = 60                                    # India addendum: 60-day window for domestic claims in 2026 (approval tier unchanged)
APPROVAL_SGD = {"manager": {2024: 500, 2025: 500, 2026: 500}, "director": {2024: 1500, 2025: 1500, 2026: 2000}, "finance": {2024: 5000, 2025: 5000, 2026: 5000}}
REGIONAL_MGR = {"IN": {2024: 20000, 2025: 20000, 2026: 20000}, "JP": {2024: 45000, 2025: 45000, 2026: 50000}}   # local currency; stricter than the SGD tier
JP_ENTERTAIN_COUNTRY_MGR = 60000
ALCOHOL = {"SG": {2024: 35, 2025: 35, 2026: 30}, "JP": {2024: 30, 2025: 30, 2026: 30}}                        # max share of the bill, percent
TIP_MAX_PCT = 15
SOFTWARE_TIERS = dict(low=500, high=1000, prepaid_finance=3000)
EQUIP = dict(no_approval=300, approval=1000)           # above 1000 SGD equivalent: capital asset, procure via Finance
LATE_NIGHT = dict(start="22:00", activity_end="21:30")
CARD_RENTAL_MIN_GRADE = 4
AIR = dict(pe_min_grade=4, biz_min_grade=7, biz_hours=9.0, biz_hours_grade=6, advance_days=14)
NEAR_DUP_TOL_PCT, NEAR_DUP_DAYS, SPLIT_DAYS, RECUR_MIN, RECUR_MAX = 2, 3, 3, 26, 35
CC_FROZEN_MIN_SGD = 200


# ---------------------------------------------------------------- reference tables
def fx_table(rng: random.Random):
    rows, inr, jpy = [], 0.0160, 0.0090
    for y in YEARS:
        for m in range(1, 13):
            inr = round(min(0.0170, max(0.0150, inr + rng.uniform(-0.00025, 0.00025))), 5)
            jpy = round(min(0.0098, max(0.0084, jpy + rng.uniform(-0.00012, 0.00012))), 5)
            rows += [dict(year=y, month=m, currency="SGD", sgd_per_unit=1.0), dict(year=y, month=m, currency="INR", sgd_per_unit=inr), dict(year=y, month=m, currency="JPY", sgd_per_unit=jpy)]
    return rows


DEPTS = ["Engineering", "Sales", "Finance", "Operations", "Legal", "HR", "Marketing", "Data Science", "Customer Success", "Procurement"]
FIRST = ["Aarav", "Mei", "Kenji", "Priya", "Wei", "Haruto", "Ananya", "Jun", "Sakura", "Rohan", "Li", "Yuki", "Vikram", "Hana", "Arjun", "Mika", "Devi", "Ren", "Nikhil", "Aiko", "Siti", "Daiki", "Kavya", "Tao", "Emi"]
LAST = ["Tan", "Sharma", "Sato", "Lim", "Iyer", "Suzuki", "Wong", "Nair", "Tanaka", "Goh", "Reddy", "Kobayashi", "Chua", "Menon", "Ito", "Ong", "Kapoor", "Yamamoto", "Ng", "Rao"]


def employees(rng: random.Random, n=300):
    rows = []
    for i in range(1, n + 1):
        reg = ["SG", "IN", "JP"][(i - 1) % 3]
        grade = rng.choices(range(1, 9), weights=[10, 14, 16, 16, 14, 12, 8, 4])[0]
        rows.append(dict(employee_id=f"E{i:04d}", name=f"{rng.choice(FIRST)} {rng.choice(LAST)}", grade=f"G{grade}", region=reg, department=rng.choice(DEPTS), manager_id=f"M{(i % 40) + 1:03d}",
                         status="ACTIVE", cost_centre=f"CC-{(i % 24) + 1:02d}"))
    return rows


def parse_date(s): return date.fromisoformat(s)


def days_between(a, b): return (parse_date(b) - parse_date(a)).days
