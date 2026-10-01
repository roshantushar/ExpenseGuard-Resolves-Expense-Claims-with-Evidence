"""V3 holdout, step 1: 30 new, never-before-seen cases against an ISOLATED copy of the enterprise tables
(experiments/v3_holdout/enterprise_data/ -- never ExpenseGuard_DATASET/), pre-registered by
experiments/v3_freeze_manifest.yaml before this file was written. Mirrors scripts/exp60_generate_cases.py's
method exactly (same independent reference engine, same real note-drafting pipeline, same isolation
discipline) but with entirely new case_ids (X4-*), new bill/approval/travel/delegation ids (B4-*/*-95xx),
and new employee/date/amount combinations -- no case content reused from Exp 60's X3-* set.

Where a case's threshold math (hotel ceiling vs. amendment date, mileage rate, etc.) mirrors an
already-validated Exp 60 scenario shape, the amount/date relationship is kept identical to that
already-confirmed-correct boundary so ground-truth risk stays low; only identity (employee, project,
ids) and cosmetic details change. Pass-1 ground truth (scripts/v3_run_generation.py) is still reviewed by
hand before any note-drafting call is made, exactly as Exp 60 was.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "v3_holdout"
ENTERPRISE = HOLDOUT / "enterprise_data"
sys.path.insert(0, str(ROOT))

from dataset_generator import semantic as SEM
SEM.CACHE = HOLDOUT / "semantic_cache.json"  # redirect BEFORE any call -- never touch the real one

NEUTRAL_DESC = "See attached receipt for details of this business expense."


def load_tables() -> dict:
    t = {}
    for f in ENTERPRISE.glob("*.csv"):
        with open(f, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if f.stem == "fx_rates":
            for r in rows:
                r["year"] = int(r["year"]); r["month"] = int(r["month"])
        t[f.stem] = rows
    return t


def append_row(table: str, row: dict):
    path = ENTERPRISE / f"{table}.csv"
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f)); fieldnames = rows[0].keys() if rows else row.keys()
    rows.append(row)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)


def bill(merchant, country, city, currency, total, bn, cat):
    return {"merchant": merchant, "country": country, "city": city, "currency": currency, "total": float(total),
            "bill_number": bn, "merchant_category": cat, "line_items": [{"description": "Charges", "amount": float(total)}]}


CASES = []


def add(n, arch, touches, difficulty, employee_id, b, txn, sub, project_id, form, new_rows=(), note_override=None):
    cid = f"X4-{n:03d}"
    CASES.append(dict(case_id=cid, archetype=arch, touches=touches, difficulty=difficulty, employee_id=employee_id,
                       bill=b, transaction_date=txn, submission_date=sub, project_id=project_id, form=form,
                       new_rows=new_rows, note_override=note_override))


# --- Hotel (5): circular-boundary fix -- same amount/date-boundary shape as Exp 60's validated X3-001..005,
# new employee/project/ids ---
add(1, "HOTEL_CEILING", "hotel_circular", "hard", "E0048",
    bill("Garden Tokyo Hotel", "Japan", "Tokyo", "JPY", 69800, "B4-000001", "HOTEL"),
    "2025-09-12", "2025-09-15", "PRJ-034", {"expense_type": "HOTEL", "city": "Tokyo", "nights": 2},
    [("travel_requests", {"travel_id": "TR-9501", "employee_id": "E0048", "start_date": "2025-09-11", "end_date": "2025-09-13", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9501", "expense_id": "X4-001", "employee_id": "E0048", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(2, "HOTEL_CEILING", "hotel_circular (negative control)", "hard", "E0048",
    bill("Garden Tokyo Hotel", "Japan", "Tokyo", "JPY", 69800, "B4-000002", "HOTEL"),
    "2025-06-12", "2025-06-15", "PRJ-034", {"expense_type": "HOTEL", "city": "Tokyo", "nights": 2},
    [("travel_requests", {"travel_id": "TR-9502", "employee_id": "E0048", "start_date": "2025-06-11", "end_date": "2025-06-13", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9502", "expense_id": "X4-002", "employee_id": "E0048", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(3, "HOTEL_CEILING", "hotel_circular (India)", "hard", "E0023",
    bill("Royal Mumbai Hotel", "India", "Mumbai", "INR", 45900, "B4-000003", "HOTEL"),
    "2026-04-06", "2026-04-09", "PRJ-045", {"expense_type": "HOTEL", "city": "Mumbai", "nights": 3},
    [("travel_requests", {"travel_id": "TR-9503", "employee_id": "E0023", "start_date": "2026-04-05", "end_date": "2026-04-09", "destination": "Mumbai", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9503", "expense_id": "X4-003", "employee_id": "E0023", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(4, "HOTEL_CONFERENCE", "hotel_partner_uplift", "hard", "E0013",
    bill("Garden Singapore Hotel", "Singapore", "Singapore", "SGD", 1260, "B4-000004", "HOTEL"),
    "2025-09-21", "2025-09-24", "PRJ-010", {"expense_type": "HOTEL", "city": "Singapore", "nights": 3},
    [("travel_requests", {"travel_id": "TR-9504", "employee_id": "E0013", "start_date": "2025-09-20", "end_date": "2025-09-23", "destination": "Singapore", "purpose": "Conference", "status": "APPROVED", "event_id": "CONF-9501", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9504", "expense_id": "X4-004", "employee_id": "E0013", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""}),
     ("conference_registry", {"event_id": "CONF-9501", "employee_id": "E0013", "registration_status": "REGISTERED", "official_partner_hotel": "Garden Singapore Hotel"})])

add(5, "HOTEL_CEILING", "hotel_circular (well above, control)", "medium", "E0048",
    bill("Garden Tokyo Hotel", "Japan", "Tokyo", "JPY", 112000, "B4-000005", "HOTEL"),
    "2025-09-16", "2025-09-19", "PRJ-034", {"expense_type": "HOTEL", "city": "Tokyo", "nights": 2},
    [("travel_requests", {"travel_id": "TR-9505", "employee_id": "E0048", "start_date": "2025-09-15", "end_date": "2025-09-17", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9505", "expense_id": "X4-005", "employee_id": "E0048", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

# --- Meal (4) ---
add(6, "EMPLOYEE_MEAL_TEMPORAL", "meal_attendee_roles", "hard", "E0048",
    bill("Fuji Grill", "Japan", "Tokyo", "JPY", 15300, "B4-000006", "RESTAURANT"),
    "2025-11-11", "2025-11-14", "PRJ-034", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 3, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0}, [])

add(7, "CLIENT_MEAL", "meal_attendee_roles (client)", "medium", "E0013",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 1400, "B4-000007", "RESTAURANT"),
    "2025-08-12", "2025-08-15", "PRJ-010", {"expense_type": "MEAL_CLIENT", "attendees_total": 11, "external_attendees": 5, "external_names": "delegates from Harbour Freight", "alcohol_amount": 0, "tip_amount": 0},
    [("manager_approvals", {"approval_id": "APR-9507", "expense_id": "X4-007", "employee_id": "E0013", "manager_id": "M014", "approval_type": "ENTERTAINMENT", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(8, "ALCOHOL_REGIONAL", "control", "easy", "E0023",
    bill("Bengal Tiffin", "India", "Mumbai", "INR", 5200.0, "B4-000008", "RESTAURANT"),
    "2025-09-22", "2025-09-25", "PRJ-045", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 3, "external_attendees": 0, "alcohol_amount": 850, "tip_amount": 0}, [])

add(9, "CLIENT_MEAL", "control", "easy", "E0013",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 310.0, "B4-000009", "RESTAURANT"),
    "2025-08-13", "2025-08-16", "PRJ-010", {"expense_type": "MEAL_CLIENT", "attendees_total": 3, "external_attendees": 1, "external_names": None, "alcohol_amount": 0, "tip_amount": 0}, [])

# --- Mileage (4): odometer/distance-math fix ---
add(10, "MILEAGE", "mileage_odometer", "medium", "E0013",
    bill("Private vehicle mileage SG 2025", "Singapore", "Singapore", "SGD", 39.0, "B4-000010", "MILEAGE"),
    "2025-07-08", "2025-07-11", "PRJ-010", {"expense_type": "MILEAGE", "distance_km": 65}, [])

add(11, "MILEAGE", "mileage_odometer (negative control)", "medium", "E0013",
    bill("Private vehicle mileage SG 2025", "Singapore", "Singapore", "SGD", 58.0, "B4-000011", "MILEAGE"),
    "2025-07-09", "2025-07-12", "PRJ-010", {"expense_type": "MILEAGE", "distance_km": 65}, [])

add(12, "MILEAGE", "control (plain km)", "easy", "E0023",
    bill("Private vehicle mileage IN 2026", "India", "Mumbai", "INR", 480.0, "B4-000012", "MILEAGE"),
    "2026-03-05", "2026-03-08", "PRJ-045", {"expense_type": "MILEAGE", "distance_km": 40}, [])

add(13, "MILEAGE", "mileage_odometer (decoy)", "hard", "E0048",
    bill("Private vehicle mileage SG 2025", "Singapore", "Singapore", "SGD", 21.0, "B4-000013", "MILEAGE"),
    "2025-07-14", "2025-07-17", "PRJ-010", {"expense_type": "MILEAGE", "distance_km": 35}, [])

# --- Software (4): named-business-owner fix ---
add(14, "SOFTWARE_APPROVAL", "software_owner_phrasing", "easy", "E0013",
    bill("Vector Notes", "Singapore", "Singapore", "SGD", 215.0, "B4-000014", "SOFTWARE"),
    "2025-06-16", "2025-06-19", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": "Ren Wong", "billing": "MONTHLY", "charge_to": "COST_CENTRE"}, [])

add(15, "SOFTWARE_APPROVAL", "software_owner_phrasing (new wording)", "hard", "E0013",
    bill("SprintMill", "Singapore", "Singapore", "SGD", 245.0, "B4-000015", "SOFTWARE"),
    "2025-06-21", "2025-06-24", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": "Kavya Rao", "billing": "MONTHLY", "charge_to": "COST_CENTRE"}, [])

add(16, "SOFTWARE_APPROVAL", "control (no owner)", "easy", "E0013",
    bill("Vector Notes", "Singapore", "Singapore", "SGD", 215.0, "B4-000016", "SOFTWARE"),
    "2025-06-26", "2025-06-29", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": None, "billing": "MONTHLY", "charge_to": "COST_CENTRE"}, [])

add(17, "SOFTWARE_APPROVAL", "control (over high tier)", "medium", "E0013",
    bill("SprintMill", "Singapore", "Singapore", "SGD", 1550.0, "B4-000017", "SOFTWARE"),
    "2026-03-05", "2026-03-08", "PRJ-034", {"expense_type": "SOFTWARE", "business_owner": "Ren Wong", "billing": "MONTHLY", "charge_to": "PROJECT"},
    [("manager_approvals", {"approval_id": "APR-9517", "expense_id": "X4-017", "employee_id": "E0013", "manager_id": "M014", "approval_type": "SOFTWARE", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

# --- Gift (4): government-recipient gate ---
add(18, "GIFT_RULES", "gift_recipient_government", "easy", "E0048",
    bill("Blossom & Co", "Japan", "Tokyo", "JPY", 5800.0, "B4-000018", "GIFT_RETAIL"),
    "2026-01-21", "2026-01-24", "PRJ-034", {"expense_type": "GIFT", "recipient_type": "GOVERNMENT", "gift_form": "ITEM", "recipient_name": "Ms. Sato", "recipient_org": "Ministry of Trade"}, [])

add(19, "GIFT_RULES", "gift_recipient_government (negative control)", "easy", "E0013",
    bill("Golden Basket", "Singapore", "Singapore", "SGD", 95.0, "B4-000019", "GIFT_RETAIL"),
    "2025-12-06", "2025-12-09", "PRJ-010", {"expense_type": "GIFT", "recipient_type": "COMMERCIAL", "gift_form": "ITEM", "recipient_name": "Mr. Koh", "recipient_org": "Anchor Freight"}, [])

add(20, "GIFT_RULES", "control (cash equivalent)", "easy", "E0013",
    bill("Golden Basket", "Singapore", "Singapore", "SGD", 85.0, "B4-000020", "GIFT_RETAIL"),
    "2025-12-11", "2025-12-14", "PRJ-010", {"expense_type": "GIFT", "recipient_type": "COMMERCIAL", "gift_form": "CASH_EQUIVALENT", "recipient_name": "Ms. Ang", "recipient_org": "Solstice Partners"}, [])

add(21, "GIFT_ANNUAL_CAP", "control (annual cap)", "medium", "E0048",
    bill("Blossom & Co", "Japan", "Tokyo", "JPY", 5200.0, "B4-000021", "GIFT_RETAIL"),
    "2025-10-02", "2025-10-05", "PRJ-034", {"expense_type": "GIFT", "recipient_type": "COMMERCIAL", "gift_form": "ITEM", "recipient_name": "Mr. Endo", "recipient_org": "Chuo Partners Ltd"},
    [("previous_expenses", {"expense_id": "PREV-9521", "employee_id": "E0048", "merchant": "Blossom & Co", "transaction_date": "2025-03-02", "amount": "23000", "currency": "JPY", "bill_number": "B4-PRIOR-9521", "business_purpose": "Gift", "project_id": "", "category": "GIFT", "counterparty": "Chuo Partners Ltd"})])

# --- Evidence-consistency (3): bill/note conflict gate, notes hand-written on purpose ---
add(22, "EVIDENCE_CONFLICT", "control (no conflict)", "easy", "E0023",
    bill("QuickCab", "India", "Mumbai", "INR", 510.0, "B4-000022", "RIDE_HAIL"),
    "2026-02-21", "2026-02-24", "PRJ-045", {"expense_type": "GROUND_TRANSPORT", "origin": "client office", "destination": "hotel", "origin_type": "CLIENT_SITE", "destination_type": "OTHER"},
    [], note_override="Took a QuickCab ride from the client's office back to my hotel after the meeting ran late.")

add(23, "EVIDENCE_CONFLICT", "evidence_consistency", "medium", "E0013",
    bill("Garden Singapore Hotel", "Singapore", "Singapore", "SGD", 360.0, "B4-000023", "HOTEL"),
    "2025-09-06", "2025-09-09", "PRJ-010", {"expense_type": "HOTEL", "city": "Singapore", "nights": 1},
    [], note_override="Team dinner to wrap up the quarter, attaching the group meal receipt.")

add(24, "EVIDENCE_CONFLICT", "evidence_consistency (meal bill/taxi note)", "medium", "E0048",
    bill("Fuji Grill", "Japan", "Tokyo", "JPY", 7200.0, "B4-000024", "RESTAURANT"),
    "2025-11-03", "2025-11-06", "PRJ-034", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 2, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0},
    [], note_override="Cab fare for a cross-town client meeting today, driver's receipt attached.")

# --- Airfare (3) ---
add(25, "AIRFARE_CABIN", "airfare_biz_wording", "medium", "E0018",
    bill("Merlion Air", "Singapore", "Singapore", "SGD", 3300.0, "B4-000025", "AIRLINE"),
    "2026-01-16", "2026-01-19", "PRJ-010", {"expense_type": "AIRFARE", "cabin": "BUSINESS", "flight_hours": 10.0, "booked_date": "2025-12-21", "departure_date": "2026-01-16"},
    [("travel_requests", {"travel_id": "TR-9525", "employee_id": "E0018", "start_date": "2026-01-15", "end_date": "2026-01-18", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9525", "expense_id": "X4-025", "employee_id": "E0018", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(26, "AIRFARE_CABIN", "control (wrong cabin)", "easy", "E0013",
    bill("Meridian Airways", "Singapore", "Singapore", "SGD", 2900.0, "B4-000026", "AIRLINE"),
    "2025-10-06", "2025-10-09", "PRJ-010", {"expense_type": "AIRFARE", "cabin": "BUSINESS", "flight_hours": 4.0, "booked_date": "2025-09-02", "departure_date": "2025-10-06"},
    [("travel_requests", {"travel_id": "TR-9526", "employee_id": "E0013", "start_date": "2025-10-05", "end_date": "2025-10-08", "destination": "Mumbai", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""})])

add(27, "TRAINING_CAP", "control (within cap)", "easy", "E0013",
    bill("Praxis Academy", "Singapore", "Singapore", "SGD", 920.0, "B4-000027", "TRAINING_PROVIDER"),
    "2025-04-11", "2025-04-14", "PRJ-010", {"expense_type": "TRAINING", "learning_plan_id": "LP-9501"},
    [("manager_approvals", {"approval_id": "APR-9527", "expense_id": "X4-027", "employee_id": "E0013", "manager_id": "M014", "approval_type": "TRAINING", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

# --- Control group (3): categories no Exp 53-60 fix touched ---
add(28, "DUPLICATE_CHECK", "control (exact duplicate)", "easy", "E0064",
    bill("SprintMill", "Singapore", "Singapore", "SGD", 199.0, "B4-000028", "SOFTWARE"),
    "2025-06-16", "2025-06-19", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": "Priya Nair", "billing": "MONTHLY", "charge_to": "COST_CENTRE"},
    [("previous_expenses", {"expense_id": "PREV-9528", "employee_id": "E0064", "merchant": "SprintMill", "transaction_date": "2025-06-16", "amount": "199.0", "currency": "SGD", "bill_number": "B4-000028", "business_purpose": "Recurring monthly subscription", "project_id": "", "category": "SOFTWARE", "counterparty": ""})])

add(29, "SUBMISSION_WINDOW", "control (late)", "easy", "E0013",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 95.0, "B4-000029", "RESTAURANT"),
    "2025-01-06", "2025-06-02", "PRJ-010", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 2, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0}, [])

add(30, "RESTRICTED_MERCHANT", "control", "easy", "E0013",
    bill("Golden Dice Casino 2025", "Singapore", "Singapore", "SGD", 210.0, "B4-000030", "ENTERTAINMENT_VENUE"),
    "2025-07-02", "2025-07-05", "PRJ-010", {"expense_type": "OTHER"}, [])


if __name__ == "__main__":
    print(f"Defined {len(CASES)} cases. Archetypes: {sorted({c['archetype'] for c in CASES})}")
    print("Next: python -m scripts.v3_run_generation to add enterprise rows, compute ground truth, and (separately, after review) draft notes.")
