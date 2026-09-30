"""ExpenseGuard V2 - scenario builder: name pools, enterprise-state helpers, claim assembly. Cases reference approvals/exceptions by a temporary key that is
mapped to the final shuffled case id after all cases exist (so case ids carry no information)."""
from __future__ import annotations
import random, re
from collections import Counter
from datetime import date, timedelta
from . import world as W

TABLES = ["employees", "travel_requests", "manager_approvals", "policy_exceptions", "project_registry", "conference_registry", "merchant_directory", "fx_rates", "previous_expenses", "approval_delegations", "cost_centre_budgets"]
SG_R = [f"{a} {b}" for a in ["Marina", "Orchard", "Clarke Quay", "Tanjong", "Raffles", "Kallang", "Bugis", "Telok Ayer"] for b in ["Dining Room", "Kitchen", "Bistro", "Grill", "Noodle House", "Terrace"]]
IN_R = [f"{a} {b}" for a in ["Spice", "Saffron", "Mumbai", "Bengal", "Deccan", "Malabar", "Punjab", "Lotus"] for b in ["Courtyard", "Table", "Kitchen", "Darbar", "Bistro", "Tiffin"]]
JP_R = [f"{a} {b}" for a in ["Sakura", "Kyoto", "Tokyo", "Osaka", "Fuji", "Hakone", "Ginza", "Shibuya"] for b in ["Grill", "Sushi", "Izakaya", "Kitchen", "Ramen House", "Teppan"]]
REST = {"SG": SG_R, "IN": IN_R, "JP": JP_R}
HOTEL_PREFIX = ["Grand", "Royal", "Harbour", "Crown", "Meridian", "Palace", "Skyline", "Garden", "Regency", "Summit"]
RIDE = {"SG": ["SwiftCab SG", "MetroRide", "ZipTaxi", "IslandCab"], "IN": ["QuickCab", "RideNow India", "Auto Bharat", "MetroWheels"], "JP": ["TokyoGo Taxi", "NipponRide", "Sakura Cab", "KantoCab"]}
SOFT = ["CloudSuite Pro", "DataLoom", "CodeForge", "PixelDesk", "Metric Harbor", "Signal Stack", "Quill Analytics", "BrightBoard", "Vector Notes", "Helix Docs", "Ledger Loop", "TaskOrbit", "SprintMill", "InsightPad", "Pipeline Forge", "Beacon Suite"]
EQUIP = ["OfficeMart", "TechBazaar", "DeskWorks", "GadgetHub", "Keystone Supplies", "ErgoStore", "PeriphPoint", "Circuit City Trade"]
GIFTS = ["Heritage Hampers", "Blossom & Co", "Gift Gallery", "Artisan Crate", "Tea & Tradition", "Orchid House Gifts", "Craft Collective", "Golden Basket"]
TRAINING = ["SkillBridge Academy", "Northwind Institute", "Apex Learning", "Meridian School of Data", "Cedar Professional Institute", "Praxis Academy", "Lighthouse Training"]
CONF_ORG = ["Applied AI Summit", "FinOps Forum", "Cloud Native Congress", "Data Leaders Conference", "Supply Chain Expo", "Cyber Assurance Summit", "Product Craft Live", "Sustainable Ops Forum"]
TELCO = {"SG": ["SingLink Mobile", "IslandTel"], "IN": ["Bharat Connect", "IndiaWave"], "JP": ["NipponTel", "KantoMobile"]}
CONSUMER = ["StreamNow", "FitLife Club", "GameVault", "CycleHouse Studio", "MovieBox+", "PureYoga Club"]
AIRL = ["Merlion Air", "Deccan Pacific", "Nippon Sky", "Meridian Airways", "Lotus Air"]
ORGS = ["Halcyon Freight", "Brightwater Bank", "Kestrel Logistics", "Omnia Retail", "Vantage Motors", "Solace Health", "Ironbridge Capital", "Zenith Foods", "Larkspur Media", "Tidewater Energy", "Crestline Insurance", "Quantum Textiles",
        "Alder & Finch", "Northgate Telecom", "Palmyra Hotels", "Redwood Pharma", "Sterling Ports", "Umbra Games", "Vireo Solar", "Willow Education", "Yarrow Systems", "Cobalt Mining", "Driftwood Travel", "Ember Foods"]
EVENTS = ["the quarterly business review", "contract renewal talks", "the product roadmap workshop", "a security audit debrief", "the migration kickoff", "budget alignment meetings", "the onboarding of a new account team",
          "a joint pilot retrospective", "the annual planning offsite", "an incident post-mortem", "a partnership scoping session", "the procurement panel", "a training day for their analysts", "the launch readiness review"]
CITY_HOTELS = {}


class Builder:
    def __init__(self):
        self.rng = random.Random(W.SEED)
        self.T = {t: [] for t in TABLES}
        self.T["employees"] = W.employees(self.rng)
        self.T["fx_rates"] = W.fx_table(self.rng)
        self.used, self.texts, self.cases, self.mer, self.k = set(), set(), [], {}, 0
        self.bills = set()
        self.ids = Counter()

    # ---- ids
    def nid(self, prefix, width=4):
        self.ids[prefix] += 1
        return f"{prefix}{self.ids[prefix]:0{width}d}"

    def key(self): self.k += 1; return f"@K{self.k:03d}"

    def bill_no(self, tag="B"):
        while True:
            n = f"{tag}{self.rng.randint(100000, 999999)}"
            if n not in self.bills: self.bills.add(n); return n

    # ---- people, merchants
    def emp(self, region=None, gmin=1, gmax=8, reuse=False):
        c = [e for e in self.T["employees"] if (region is None or e["region"] == region) and gmin <= int(e["grade"][1:]) <= gmax and (reuse or e["employee_id"] not in self.used)]
        e = self.rng.choice(c); self.used.add(e["employee_id"]); return e

    def merchant(self, kind, region=None, city=None, risk="STANDARD", name=None):
        pool = {"RESTAURANT": REST.get(region, []), "RIDE_HAIL": RIDE.get(region, []), "SOFTWARE": SOFT, "EQUIPMENT": EQUIP, "GIFT_RETAIL": GIFTS, "TRAINING_PROVIDER": TRAINING,
                "CONFERENCE_ORGANISER": CONF_ORG, "TELECOM": TELCO.get(region, []), "CONSUMER_SERVICE": CONSUMER, "AIRLINE": AIRL}.get(kind, [])
        if name is None:
            free = [n for n in pool if n not in self.mer] or pool
            name = self.rng.choice(free)
        if name not in self.mer:
            self.mer[name] = 1
            self.T["merchant_directory"].append(dict(merchant_name=name, merchant_category=kind, country=W.REGION[region]["country"] if region else "Singapore", city=city or "", risk_class=risk, active="TRUE"))
        return name

    def hotel(self, city, partner_of=None):
        n = f"{self.rng.choice(HOTEL_PREFIX)} {city} Hotel"
        while n in self.mer: n = f"{self.rng.choice(HOTEL_PREFIX)} {city} {self.rng.choice(['Hotel', 'Suites', 'Residence', 'Inn'])}"
        return self.merchant("HOTEL", W.CITY_REGION[city], city, name=n)

    # ---- dates
    def dt(self, y, m=None, d=None):
        m = m or self.rng.randint(1, 12); d = d or self.rng.randint(3, 26)
        return f"{y}-{m:02d}-{d:02d}"

    @staticmethod
    def plus(t, days): return (date.fromisoformat(t) + timedelta(days=days)).isoformat()

    # ---- enterprise rows
    def travel(self, emp, start, end=None, status="APPROVED", event=None, exc=None, dest=None, purpose="Client visit"):
        r = dict(travel_id=self.nid("TR-"), employee_id=emp["employee_id"], start_date=start, end_date=end or start, destination=dest or "", purpose=purpose, status=status, event_id=event or "", exception_id=exc or "")
        self.T["travel_requests"].append(r); return r

    def approval(self, key, emp, typ="GENERAL", status="APPROVED", level="MANAGER", start=None, end=None, deleg=None):
        r = dict(approval_id=self.nid("APR-"), expense_id=key, employee_id=emp["employee_id"], manager_id=emp["manager_id"], approval_type=typ, status=status, approver_level=level, start_date=start or "2024-01-01", end_date=end or "2026-12-31", delegation_id=deleg or "")
        self.T["manager_approvals"].append(r); return r

    def exception(self, emp, key, policy, status="APPROVED", vf=None, vt=None, etype="HOTEL_LIMIT"):
        r = dict(exception_id=self.nid("EXC-"), employee_id=emp["employee_id"], expense_id=key, policy_id=policy, exception_type=etype, status=status, valid_from=vf, valid_to=vt); self.T["policy_exceptions"].append(r); return r

    def conference(self, emp, date_, hotel, status="REGISTERED", name=None):
        r = dict(event_id=self.nid("CONF-", 3), employee_id=emp["employee_id"], event_name=name or self.rng.choice(CONF_ORG), event_date=date_, registration_status=status, official_partner_hotel=hotel); self.T["conference_registry"].append(r); return r

    def project(self, parent=None, status="ACTIVE", cc=None):
        r = dict(project_id=self.nid("PRJ-", 3), parent_project_id=parent or "", client=f"Client-{self.rng.randint(1, 40):02d}", project_status=status, cost_centre=cc or f"CC-{self.rng.randint(1, 24):02d}", billable=self.rng.choice(["TRUE", "FALSE"]))
        self.T["project_registry"].append(r); return r

    def delegation(self, mgr, delegate_level, start, end, limit, delegate=None):
        r = dict(delegation_id=self.nid("DEL-", 3), manager_id=mgr, delegate_id=delegate or self.rng.choice(self.T["employees"])["employee_id"], delegate_level=delegate_level, start_date=start, end_date=end, max_amount_sgd=limit, status="ACTIVE")
        self.T["approval_delegations"].append(r); return r

    def prev(self, emp, merchant, t, amount, ccy, category, purpose="Business expense", counterparty="", project=None, bill=None, eid=None):
        r = dict(expense_id=eid or self.nid("PREV-", 5), employee_id=emp["employee_id"], merchant=merchant, transaction_date=t, amount=amount, currency=ccy, bill_number=bill or self.bill_no("H"), business_purpose=purpose, status="REIMBURSED",
                 project_id=project or "", category=category, counterparty=counterparty)
        self.T["previous_expenses"].append(r); return r

    # ---- claim assembly
    def unique(self, text):
        n = re.sub(r"\W+", " ", text.lower()).strip()
        if n in self.texts: return False
        self.texts.add(n); return True

    def claim(self, group, arch, want, emp, t, age, merchant, mcat, country, city, total, et, form, desc, items=None, project=None, charge_to="COST_CENTRE", key=None):
        ccy = W.REGION[W.COUNTRY_TO_REGION[country]]["ccy"]
        f = dict(expense_type=et, charge_to=charge_to, approval_ref=None, **form)
        it = items or [dict(description=et.replace("_", " ").title(), amount=total)]
        c = dict(_key=key or self.key(), _group=group, _arch=arch, _want=want, employee_id=emp["employee_id"], transaction_date=t, submission_date=self.plus(t, age),
                 bill=dict(merchant=merchant, country=country, city=city, currency=ccy, total=total, bill_number=self.bill_no("B"), merchant_category=mcat, line_items=it), form=f,
                 employee_description=desc, project_id=project or f"PRJ-{self.rng.randint(1, 60):03d}")
        self.cases.append(c); return c
