"""ExpenseGuard V2 - assemble: build scenarios, add background enterprise data, shuffle and assign ids, run the reference engine, assign splits."""
from __future__ import annotations
import random, re
from collections import Counter
from . import world as W, builder, cases_a, cases_b, cases_c, engine

BG_MERCHANTS = ["Central Stationers", "Lunch Bowl Cafe", "Airport Express Kiosk", "Metro Print Shop", "Green Leaf Catering", "Harbor Office Supply", "QuickFix IT Services", "Corner Bakery Co",
                "Blue Line Couriers", "City Parking Services", "Sunrise Bookstore", "Northside Pharmacy", "Urban Laundry", "Paper & Pen Depot", "TransitCard Top-up", "Skyview Coffee", "Delta Copy Centre",
                "Evergreen Florists", "Harvest Deli", "Tech Repair Lab", "Anchor Water Co", "Pinnacle Signage", "Riverside Cafe", "Summit Uniforms", "Lantern Printing", "Bridge Street Grocer"]
NOISE_TYPES = ["MEAL_EMPLOYEE", "MEAL_CLIENT", "GROUND_TRANSPORT", "HOTEL", "AIRFARE", "SOFTWARE", "EQUIPMENT", "OTHER"]
VISIBLE = ["case_id", "employee_id", "transaction_date", "submission_date", "bill", "form", "employee_description", "project_id", "split"]


def rand_date(rng, y=None):
    y = y or rng.choice(W.YEARS)
    return f"{y}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def add_background(b):
    """Historical expenses (2-3k), noise enterprise rows, hard-negative distractors, projects and budgets. Noise never uses a case merchant or the categories that feed cumulative caps."""
    rng = random.Random(W.SEED + 7)
    for name in BG_MERCHANTS:
        b.T["merchant_directory"].append(dict(merchant_name=name, merchant_category=rng.choice(["RESTAURANT", "EQUIPMENT", "RIDE_HAIL", "SOFTWARE", "OTHER"]), country=rng.choice(["Singapore", "India", "Japan"]), city="", risk_class="STANDARD", active="TRUE"))
    for e in b.T["employees"]:
        for _ in range(rng.randint(6, 10)):
            et = rng.choice(NOISE_TYPES); ccy = W.REGION[e["region"]]["ccy"]; scale = {"SGD": 1, "INR": 60, "JPY": 110}[ccy]
            b.prev(e, rng.choice(BG_MERCHANTS), rand_date(rng), round(rng.uniform(8, 260) * scale, 2), ccy, et, "Routine historical business expense", project=f"PRJ-{rng.randint(1, 60):03d}", eid=b.nid("HIST-", 5))
    # hard negatives around the duplicate and split cases: same employee and merchant but outside the rule (too far apart, other category, other employee)
    for c in list(b.cases):
        if c["_arch"] in ("B6", "B7") and rng.random() < 0.9:
            e = next(x for x in b.T["employees"] if x["employee_id"] == c["employee_id"]); other = rng.choice([x for x in b.T["employees"] if x["employee_id"] != e["employee_id"]])
            m, t, ccy, tot = c["bill"]["merchant"], c["transaction_date"], c["bill"]["currency"], c["bill"]["total"]
            b.prev(e, m, b.plus(t, -rng.randint(5, 20)), tot, ccy, c["form"]["expense_type"], "Ad hoc purchase", project=c["project_id"], eid=b.nid("PREV-N", 4))   # same amount, too far apart, not recurring
            b.prev(other, m, t, tot, ccy, c["form"]["expense_type"], "Other employee, same charge", eid=b.nid("PREV-N", 4))                                         # different employee
            b.prev(e, m, b.plus(t, -1), tot, ccy, "OTHER", "Different expense type", eid=b.nid("PREV-N", 4), bill=b.bill_no("H"))                                     # near in time, other category
    # noise in the other tables (never touches a case employee or a case key)
    unused = [e for e in b.T["employees"] if e["employee_id"] not in b.used]
    for i, e in enumerate(unused[:70]):
        s = rand_date(rng, rng.choice(W.YEARS)); b.travel(e, s, b.plus(s, rng.randint(1, 5)), status=rng.choice(["APPROVED", "APPROVED", "PENDING", "REJECTED"]), dest=rng.choice(list(W.CITY_LOC)), purpose=rng.choice(["Client visit", "Training", "Site audit"]))
    for e in unused[70:120]:
        b.T["manager_approvals"].append(dict(approval_id=b.nid("APR-"), expense_id=f"EXP-BG-{rng.randint(1, 9999):04d}", employee_id=e["employee_id"], manager_id=e["manager_id"], approval_type=rng.choice(["GENERAL", "TRAVEL", "SOFTWARE"]),
                                             status="APPROVED", approver_level="MANAGER", start_date=rand_date(rng), end_date="2026-12-31", delegation_id=""))
    for e in unused[120:150]:
        b.T["policy_exceptions"].append(dict(exception_id=b.nid("EXC-"), employee_id=e["employee_id"], expense_id=f"EXP-BG-{rng.randint(1, 9999):04d}", policy_id="TRV-6.1", exception_type="HOTEL_LIMIT", status=rng.choice(["APPROVED", "EXPIRED"]),
                                             valid_from="2025-01-01", valid_to="2025-03-31"))
    for e in unused[150:170]:
        b.conference(e, rand_date(rng), rng.choice(BG_MERCHANTS), status=rng.choice(["REGISTERED", "NOT_REGISTERED"]))
    for _ in range(25): b.delegation(f"M{rng.randint(1, 40):03d}", rng.choice(["MANAGER", "DIRECTOR"]), rand_date(rng, 2025), "2026-12-31", float(rng.choice([800, 1500, 3000])))
    have = {p["project_id"] for p in b.T["project_registry"]}
    for n in range(1, 61):
        pid = f"PRJ-{n:03d}"
        if pid not in have: b.T["project_registry"].append(dict(project_id=pid, parent_project_id="", client=f"Client-{rng.randint(1, 40):02d}", project_status=rng.choice(["ACTIVE"] * 4 + ["CLOSED"]), cost_centre=f"CC-{rng.randint(1, 24):02d}", billable=rng.choice(["TRUE", "FALSE"])))
    have = {(r["cost_centre"], int(r["year"])) for r in b.T["cost_centre_budgets"]}
    for n in range(1, 25):
        for y in W.YEARS:
            if (f"CC-{n:02d}", y) not in have: b.T["cost_centre_budgets"].append(dict(cost_centre=f"CC-{n:02d}", year=y, budget_sgd=float(rng.choice([40000, 60000, 90000])), committed_sgd=float(rng.randint(5000, 30000)), status="OPEN"))


def assemble():
    b = builder.Builder()
    cases_a.build(b); cases_b.build(b); cases_c.build(b)
    add_background(b)
    rng = random.Random(W.SEED + 11)
    order = list(b.cases); rng.shuffle(order)
    keymap = {c["_key"]: f"X2-{i + 1:03d}" for i, c in enumerate(order)}
    for tab in ("manager_approvals", "policy_exceptions"):
        for r in b.T[tab]:
            if r["expense_id"] in keymap: r["expense_id"] = keymap[r["expense_id"]]
    cases = []
    for c in order:
        c = dict(c); c["case_id"] = keymap[c["_key"]]; cases.append(c)
    S = engine.State(b.T)
    for c in cases:
        c["_gt"] = engine.evaluate(c, S)
    return b, cases, S


def assign_splits(cases, rng):
    """150 cases -> 70 development / 30 validation / 50 final, stratified by intended outcome first and then by architecture group."""
    quota = {"FINAL_TEST": {"APPROVE": 13, "REJECT": 13, "REQUEST_INFORMATION": 12, "ESCALATE": 12}, "VALIDATION": {"APPROVE": 8, "REJECT": 8, "REQUEST_INFORMATION": 7, "ESCALATE": 7}}
    for oc in ("APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE"):
        grp = sorted([c for c in cases if c["_gt"]["expected_decision"] == oc], key=lambda c: (c["_group"], rng.random()))
        nf, nv = quota["FINAL_TEST"][oc], quota["VALIDATION"][oc]; nd = len(grp) - nf - nv
        want = {"FINAL_TEST": nf, "VALIDATION": nv, "DEVELOPMENT": nd}; got = {k: 0 for k in want}
        for i, c in enumerate(grp):                       # spread each split evenly along the group-sorted list
            k = max(want, key=lambda s: (want[s] * (i + 1) / len(grp)) - got[s]); c["split"] = k; got[k] += 1
    return cases


if __name__ == "__main__":
    b, cases, S = assemble()
    bad = [(c["case_id"], c["_arch"], c["_want"], c["_gt"]["expected_decision"], c["_gt"]["reason"]) for c in cases if c["_want"] != c["_gt"]["expected_decision"]]
    print("cases", len(cases), "mismatches", len(bad))
    for x in sorted(bad, key=lambda x: x[1]): print(x)
    print(Counter(c["_gt"]["expected_decision"] for c in cases))
    print({t: len(v) for t, v in b.T.items()})
