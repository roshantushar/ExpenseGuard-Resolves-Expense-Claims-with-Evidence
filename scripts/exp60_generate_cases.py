"""Exp 60: generate 50 new, never-before-seen cases against an ISOLATED copy of the enterprise tables
(experiments/exp60_holdout/enterprise_data/ -- never ExpenseGuard_DATASET/). Ground truth is computed by
dataset_generator.engine.evaluate(), which is a genuinely independent reference implementation from
src/rules_v2.py (different table representations, cross-validated against rules_v2.py on all 150 existing
cases by the original build.py, but not the same code) -- this avoids testing the frozen resolver against
labels derived from its own logic. Notes are drafted by dataset_generator.semantic.call()/fact_sheet(),
the SAME note-drafting machinery used for the original dataset, with its own CACHE redirected to an
isolated file so the real dataset_generator/semantic_cache.json is never touched.

Two-pass ground truth, mirroring semantic.process()'s own design: (1) evaluate with a neutral placeholder
description to get the intended decision before any note exists; (2) after the real note is drafted,
re-evaluate with that note substituted in, to catch a note accidentally tripping the bill/note
evidence-conflict check. Any mismatch is reported, not silently accepted.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "exp60_holdout"
ENTERPRISE = HOLDOUT / "enterprise_data"
sys.path.insert(0, str(ROOT))

from dataset_generator import engine, semantic as SEM
SEM.CACHE = HOLDOUT / "semantic_cache.json"  # redirect BEFORE any call -- never touch the real one

NEUTRAL_DESC = "See attached receipt for details of this business expense."


def load_tables() -> dict:
    """csv.DictReader always returns strings. dataset_generator.engine.State.fx() does a raw `==` against
    an int year/month (the real pipeline evaluates against in-memory Python objects built by assemble.py,
    never round-tripped through CSV, so this mismatch never surfaces there) -- coerced here, at the loading
    boundary, rather than touching engine.py itself."""
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


# ---------------------------------------------------------------- the 50 cases
CASES = []


def add(n, arch, touches, difficulty, employee_id, b, txn, sub, project_id, form, new_rows=(), note_override=None):
    cid = f"X3-{n:03d}"
    CASES.append(dict(case_id=cid, archetype=arch, touches=touches, difficulty=difficulty, employee_id=employee_id,
                       bill=b, transaction_date=txn, submission_date=sub, project_id=project_id, form=form,
                       new_rows=new_rows, note_override=note_override))


# --- Hotel (6): circular-boundary fix ---
add(1, "HOTEL_CEILING", "hotel_circular", "hard", "E0048",
    bill("Garden Tokyo Hotel", "Japan", "Tokyo", "JPY", 69800, "B3-000001", "HOTEL"),
    "2025-09-11", "2025-09-14", "PRJ-031", {"expense_type": "HOTEL", "city": "Tokyo", "nights": 2},
    [("travel_requests", {"travel_id": "TR-9001", "employee_id": "E0048", "start_date": "2025-09-10", "end_date": "2025-09-12", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9001", "expense_id": "X3-001", "employee_id": "E0048", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(2, "HOTEL_CEILING", "hotel_circular (negative control)", "hard", "E0048",
    bill("Garden Tokyo Hotel", "Japan", "Tokyo", "JPY", 69800, "B3-000002", "HOTEL"),
    "2025-05-11", "2025-05-14", "PRJ-031", {"expense_type": "HOTEL", "city": "Tokyo", "nights": 2},
    [("travel_requests", {"travel_id": "TR-9002", "employee_id": "E0048", "start_date": "2025-05-10", "end_date": "2025-05-12", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9002", "expense_id": "X3-002", "employee_id": "E0048", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(3, "HOTEL_CEILING", "hotel_circular (India)", "hard", "E0023",
    bill("Royal Mumbai Hotel", "India", "Mumbai", "INR", 45900, "B3-000003", "HOTEL"),
    "2026-05-05", "2026-05-08", "PRJ-034", {"expense_type": "HOTEL", "city": "Mumbai", "nights": 3},
    [("travel_requests", {"travel_id": "TR-9003", "employee_id": "E0023", "start_date": "2026-05-04", "end_date": "2026-05-08", "destination": "Mumbai", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9003", "expense_id": "X3-003", "employee_id": "E0023", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(4, "HOTEL_CEILING", "hotel_circular (India, negative control)", "hard", "E0023",
    bill("Royal Mumbai Hotel", "India", "Mumbai", "INR", 45900, "B3-000004", "HOTEL"),
    "2026-02-05", "2026-02-08", "PRJ-034", {"expense_type": "HOTEL", "city": "Mumbai", "nights": 3},
    [("travel_requests", {"travel_id": "TR-9004", "employee_id": "E0023", "start_date": "2026-02-04", "end_date": "2026-02-08", "destination": "Mumbai", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9004", "expense_id": "X3-004", "employee_id": "E0023", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(5, "HOTEL_CEILING", "hotel_circular (well above, control)", "medium", "E0048",
    bill("Garden Tokyo Hotel", "Japan", "Tokyo", "JPY", 110000, "B3-000005", "HOTEL"),
    "2025-09-15", "2025-09-18", "PRJ-031", {"expense_type": "HOTEL", "city": "Tokyo", "nights": 2},
    [("travel_requests", {"travel_id": "TR-9005", "employee_id": "E0048", "start_date": "2025-09-14", "end_date": "2025-09-16", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9005", "expense_id": "X3-005", "employee_id": "E0048", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(6, "HOTEL_CONFERENCE", "hotel_partner_uplift", "hard", "E0013",
    bill("Garden Singapore Hotel", "Singapore", "Singapore", "SGD", 1260, "B3-000006", "HOTEL"),
    "2025-08-20", "2025-08-23", "PRJ-010", {"expense_type": "HOTEL", "city": "Singapore", "nights": 3},
    [("travel_requests", {"travel_id": "TR-9006", "employee_id": "E0013", "start_date": "2025-08-19", "end_date": "2025-08-22", "destination": "Singapore", "purpose": "Conference", "status": "APPROVED", "event_id": "CONF-9001", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9006", "expense_id": "X3-006", "employee_id": "E0013", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""}),
     ("conference_registry", {"event_id": "CONF-9001", "employee_id": "E0013", "registration_status": "REGISTERED", "official_partner_hotel": "Garden Singapore Hotel"})])

# --- Meal (6): attendee-role / circular fix ---
add(7, "EMPLOYEE_MEAL_TEMPORAL", "meal_attendee_roles", "hard", "E0048",
    bill("Fuji Grill", "Japan", "Tokyo", "JPY", 15300, "B3-000007", "RESTAURANT"),
    "2025-11-10", "2025-11-13", "PRJ-031", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 3, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0}, [])

add(8, "EMPLOYEE_MEAL_TEMPORAL", "meal_attendee_roles (negative control)", "hard", "E0048",
    bill("Fuji Grill", "Japan", "Tokyo", "JPY", 19500, "B3-000008", "RESTAURANT"),
    "2025-11-12", "2025-11-15", "PRJ-031", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 3, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0}, [])

add(9, "CLIENT_MEAL", "meal_attendee_roles (client)", "medium", "E0013",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 1400, "B3-000009", "RESTAURANT"),
    "2025-08-05", "2025-08-08", "PRJ-010", {"expense_type": "MEAL_CLIENT", "attendees_total": 11, "external_attendees": 5, "external_names": "delegates from Ember Foods", "alcohol_amount": 0, "tip_amount": 0},
    [("manager_approvals", {"approval_id": "APR-9009", "expense_id": "X3-009", "employee_id": "E0013", "manager_id": "M014", "approval_type": "ENTERTAINMENT", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(10, "EMPLOYEE_MEAL_TEMPORAL", "meal_circular (India, negative control)", "medium", "E0023",
    bill("Bengal Tiffin", "India", "Mumbai", "INR", 8800, "B3-000010", "RESTAURANT"),
    "2025-09-20", "2025-09-23", "PRJ-034", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 4, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0}, [])

add(11, "ALCOHOL_REGIONAL", "control", "easy", "E0023",
    bill("Bengal Tiffin", "India", "Mumbai", "INR", 5000, "B3-000011", "RESTAURANT"),
    "2025-09-21", "2025-09-24", "PRJ-034", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 3, "external_attendees": 0, "alcohol_amount": 800, "tip_amount": 0}, [])

add(12, "CLIENT_MEAL", "control", "easy", "E0013",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 300, "B3-000012", "RESTAURANT"),
    "2025-08-06", "2025-08-09", "PRJ-010", {"expense_type": "MEAL_CLIENT", "attendees_total": 3, "external_attendees": 1, "external_names": None, "alcohol_amount": 0, "tip_amount": 0}, [])

# --- Mileage (4) ---
add(13, "MILEAGE", "mileage_odometer", "medium", "E0013",
    bill("Private vehicle mileage SG 2025", "Singapore", "Singapore", "SGD", 36.0, "B3-000013", "MILEAGE"),
    "2025-07-02", "2025-07-05", "PRJ-010", {"expense_type": "MILEAGE", "distance_km": 60}, [])

add(14, "MILEAGE", "mileage_odometer (negative control)", "medium", "E0013",
    bill("Private vehicle mileage SG 2025", "Singapore", "Singapore", "SGD", 55.0, "B3-000014", "MILEAGE"),
    "2025-07-03", "2025-07-06", "PRJ-010", {"expense_type": "MILEAGE", "distance_km": 60}, [])

add(15, "MILEAGE", "control (plain km)", "easy", "E0023",
    bill("Private vehicle mileage IN 2026", "India", "Mumbai", "INR", 480.0, "B3-000015", "MILEAGE"),
    "2026-03-01", "2026-03-04", "PRJ-034", {"expense_type": "MILEAGE", "distance_km": 40}, [])

add(16, "MILEAGE", "mileage_odometer (decoy)", "hard", "E0048",
    bill("Private vehicle mileage SG 2025", "Singapore", "Singapore", "SGD", 21.0, "B3-000016", "MILEAGE"),
    "2025-07-10", "2025-07-13", "PRJ-031", {"expense_type": "MILEAGE", "distance_km": 35}, [])

# --- Software (4) ---
add(17, "SOFTWARE_APPROVAL", "software_owner_phrasing", "easy", "E0013",
    bill("Vector Notes", "Singapore", "Singapore", "SGD", 210.0, "B3-000017", "SOFTWARE"),
    "2025-06-15", "2025-06-18", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": "Devi Lim", "billing": "MONTHLY", "charge_to": "COST_CENTRE"}, [])

add(18, "SOFTWARE_APPROVAL", "software_owner_phrasing (new wording)", "hard", "E0013",
    bill("SprintMill", "Singapore", "Singapore", "SGD", 240.0, "B3-000018", "SOFTWARE"),
    "2025-06-20", "2025-06-23", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": "Marcus Tan", "billing": "MONTHLY", "charge_to": "COST_CENTRE"}, [])

add(19, "SOFTWARE_APPROVAL", "control (no owner)", "easy", "E0013",
    bill("Vector Notes", "Singapore", "Singapore", "SGD", 210.0, "B3-000019", "SOFTWARE"),
    "2025-06-25", "2025-06-28", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": None, "billing": "MONTHLY", "charge_to": "COST_CENTRE"}, [])

add(20, "SOFTWARE_APPROVAL", "control (over high tier)", "medium", "E0013",
    bill("SprintMill", "Singapore", "Singapore", "SGD", 1500.0, "B3-000020", "SOFTWARE"),
    "2026-03-01", "2026-03-04", "PRJ-034", {"expense_type": "SOFTWARE", "business_owner": "Devi Lim", "billing": "MONTHLY", "charge_to": "PROJECT"},
    [("manager_approvals", {"approval_id": "APR-9020", "expense_id": "X3-020", "employee_id": "E0013", "manager_id": "M014", "approval_type": "SOFTWARE", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

# --- Airfare (5) ---
add(21, "AIRFARE_CABIN", "airfare_biz_wording", "medium", "E0018",
    bill("Merlion Air", "Singapore", "Singapore", "SGD", 3200.0, "B3-000021", "AIRLINE"),
    "2026-01-15", "2026-01-18", "PRJ-010", {"expense_type": "AIRFARE", "cabin": "BUSINESS", "flight_hours": 10.0, "booked_date": "2025-12-20", "departure_date": "2026-01-15"},
    [("travel_requests", {"travel_id": "TR-9021", "employee_id": "E0018", "start_date": "2026-01-14", "end_date": "2026-01-17", "destination": "Tokyo", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9021", "expense_id": "X3-021", "employee_id": "E0018", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "DIRECTOR", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(22, "AIRFARE_CABIN", "airfare_relative_date", "hard", "E0018",
    bill("Merlion Air", "Singapore", "Singapore", "SGD", 800.0, "B3-000022", "AIRLINE"),
    "2026-02-15", "2026-02-18", "PRJ-010", {"expense_type": "AIRFARE", "cabin": "ECONOMY", "flight_hours": 3.0, "booked_date": "2026-01-18", "departure_date": "2026-02-15"},
    [("travel_requests", {"travel_id": "TR-9022", "employee_id": "E0018", "start_date": "2026-02-14", "end_date": "2026-02-17", "destination": "Osaka", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("manager_approvals", {"approval_id": "APR-9022", "expense_id": "X3-022", "employee_id": "E0018", "manager_id": "", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(23, "AIRFARE_CABIN", "airfare_relative_date (negative control)", "hard", "E0018",
    bill("Merlion Air", "Singapore", "Singapore", "SGD", 800.0, "B3-000023", "AIRLINE"),
    "2026-03-15", "2026-03-18", "PRJ-010", {"expense_type": "AIRFARE", "cabin": "ECONOMY", "flight_hours": 3.0, "booked_date": "2026-02-13", "departure_date": "2026-03-15"}, [])

add(24, "AIRFARE_CABIN", "control (wrong cabin)", "easy", "E0013",
    bill("Meridian Airways", "Singapore", "Singapore", "SGD", 2800.0, "B3-000024", "AIRLINE"),
    "2025-10-05", "2025-10-08", "PRJ-010", {"expense_type": "AIRFARE", "cabin": "BUSINESS", "flight_hours": 4.0, "booked_date": "2025-09-01", "departure_date": "2025-10-05"},
    [("travel_requests", {"travel_id": "TR-9024", "employee_id": "E0013", "start_date": "2025-10-04", "end_date": "2025-10-07", "destination": "Mumbai", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""})])

add(25, "AIRFARE_CABIN", "airfare_exception_scope", "hard", "E0013",
    bill("Meridian Airways", "Singapore", "Singapore", "SGD", 2800.0, "B3-000025", "AIRLINE"),
    "2025-10-10", "2025-10-13", "PRJ-010", {"expense_type": "AIRFARE", "cabin": "BUSINESS", "flight_hours": 4.0, "booked_date": "2025-09-05", "departure_date": "2025-10-10", "exception_ref": "EXC-9025"},
    [("travel_requests", {"travel_id": "TR-9025", "employee_id": "E0013", "start_date": "2025-10-09", "end_date": "2025-10-12", "destination": "Mumbai", "purpose": "Client visit", "status": "APPROVED", "event_id": "", "exception_id": ""}),
     ("policy_exceptions", {"exception_id": "EXC-9025", "employee_id": "E0013", "policy_id": "TRV-6.1", "exception_type": "HOTEL_LIMIT", "status": "APPROVED", "valid_from": "2025-01-01", "valid_to": "2025-12-31"})])

# --- Training (3) ---
add(26, "TRAINING_CAP", "control (within cap)", "easy", "E0013",
    bill("Praxis Academy", "Singapore", "Singapore", "SGD", 900.0, "B3-000026", "TRAINING_PROVIDER"),
    "2025-04-10", "2025-04-13", "PRJ-010", {"expense_type": "TRAINING", "learning_plan_id": "LP-9001"},
    [("manager_approvals", {"approval_id": "APR-9026", "expense_id": "X3-026", "employee_id": "E0013", "manager_id": "M014", "approval_type": "TRAINING", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(27, "TRAINING_CAP", "control (no plan id)", "easy", "E0013",
    bill("Cedar Professional Institute", "Singapore", "Singapore", "SGD", 700.0, "B3-000027", "TRAINING_PROVIDER"),
    "2025-04-15", "2025-04-18", "PRJ-010", {"expense_type": "TRAINING", "learning_plan_id": None}, [])

add(28, "TRAINING_CAP", "training_over_cap", "medium", "E0013",
    bill("Praxis Academy", "Singapore", "Singapore", "SGD", 3800.0, "B3-000028", "TRAINING_PROVIDER"),
    "2025-05-10", "2025-05-13", "PRJ-010", {"expense_type": "TRAINING", "learning_plan_id": "LP-9002"}, [])

# --- Gift (4): government-recipient gate ---
add(29, "GIFT_RULES", "gift_recipient_government", "easy", "E0048",
    bill("Blossom & Co", "Japan", "Tokyo", "JPY", 5500.0, "B3-000029", "GIFT_RETAIL"),
    "2026-01-20", "2026-01-23", "PRJ-031", {"expense_type": "GIFT", "recipient_type": "GOVERNMENT", "gift_form": "ITEM", "recipient_name": "Mr. Tanaka", "recipient_org": "Ministry of Digital Affairs"}, [])

add(30, "GIFT_RULES", "gift_recipient_government (negative control)", "easy", "E0013",
    bill("Golden Basket", "Singapore", "Singapore", "SGD", 90.0, "B3-000030", "GIFT_RETAIL"),
    "2025-12-05", "2025-12-08", "PRJ-010", {"expense_type": "GIFT", "recipient_type": "COMMERCIAL", "gift_form": "ITEM", "recipient_name": "Ms. Chua", "recipient_org": "Kestrel Logistics"}, [])

add(31, "GIFT_RULES", "control (cash equivalent)", "easy", "E0013",
    bill("Golden Basket", "Singapore", "Singapore", "SGD", 80.0, "B3-000031", "GIFT_RETAIL"),
    "2025-12-10", "2025-12-13", "PRJ-010", {"expense_type": "GIFT", "recipient_type": "COMMERCIAL", "gift_form": "CASH_EQUIVALENT", "recipient_name": "Mr. Lee", "recipient_org": "Meridian Partners"}, [])

add(32, "GIFT_ANNUAL_CAP", "control (annual cap)", "medium", "E0048",
    bill("Blossom & Co", "Japan", "Tokyo", "JPY", 5000.0, "B3-000032", "GIFT_RETAIL"),
    "2025-10-01", "2025-10-04", "PRJ-031", {"expense_type": "GIFT", "recipient_type": "COMMERCIAL", "gift_form": "ITEM", "recipient_name": "Ms. Ito", "recipient_org": "Kanto Partners Ltd"},
    [("previous_expenses", {"expense_id": "PREV-9032", "employee_id": "E0048", "merchant": "Blossom & Co", "transaction_date": "2025-03-01", "amount": "22000", "currency": "JPY", "bill_number": "B3-PRIOR-9032", "business_purpose": "Gift", "project_id": "", "category": "GIFT", "counterparty": "Kanto Partners Ltd"})])

# --- Evidence-consistency (4): bill/note conflict gate, notes hand-written on purpose ---
add(33, "EVIDENCE_CONFLICT", "control (no conflict)", "easy", "E0023",
    bill("QuickCab", "India", "Mumbai", "INR", 480.0, "B3-000033", "RIDE_HAIL"),
    "2026-02-20", "2026-02-23", "PRJ-034", {"expense_type": "GROUND_TRANSPORT", "origin": "client office", "destination": "hotel", "origin_type": "CLIENT_SITE", "destination_type": "OTHER"},
    [], note_override="Took a QuickCab ride from the client's office back to my hotel after the meeting ran late.")

add(34, "EVIDENCE_CONFLICT", "evidence_consistency", "medium", "E0013",
    bill("Garden Singapore Hotel", "Singapore", "Singapore", "SGD", 350.0, "B3-000034", "HOTEL"),
    "2025-09-05", "2025-09-08", "PRJ-010", {"expense_type": "HOTEL", "city": "Singapore", "nights": 1},
    [], note_override="Dinner with the regional team to close out the quarter, bill attached for the group meal.")

# Note: engine.py's independent evidence-conflict check (BILL_FAMILY) only covers meal/transport/hotel --
# airline is not a recognized family there (though src/rules_v2.py's own conflict check DOES cover AIRFARE).
# Redesigned to a pairing the independent evaluator can actually verify: a meal bill, a note describing a
# taxi ride -- a different family pairing than X3-034 (hotel bill / meal note), still genuinely novel.
add(35, "EVIDENCE_CONFLICT", "evidence_consistency (meal bill/taxi note)", "medium", "E0018",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 60.0, "B3-000035", "RESTAURANT"),
    "2025-11-02", "2025-11-05", "PRJ-010", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 2, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0},
    [], note_override="Took a cab across town for a same-day client meeting, receipt from the driver attached.")

add(36, "EVIDENCE_CONFLICT", "evidence_consistency (non-English)", "hard", "E0023",
    bill("Bengal Tiffin", "India", "Mumbai", "INR", 1200.0, "B3-000036", "RESTAURANT"),
    "2025-12-01", "2025-12-04", "PRJ-034", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 3, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0},
    [], note_override="Yeh bill hotel mein teen raat rukne ka hai, conference ke paas.")

# --- Control group (14): categories Exp 59 did not touch ---
add(37, "DUPLICATE_CHECK", "control (exact duplicate)", "easy", "E0055",
    bill("SprintMill", "Singapore", "Singapore", "SGD", 199.0, "B3-000037", "SOFTWARE"),
    "2025-06-15", "2025-06-18", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": "Priya Nair", "billing": "MONTHLY", "charge_to": "COST_CENTRE"},
    [("previous_expenses", {"expense_id": "PREV-9037", "employee_id": "E0055", "merchant": "SprintMill", "transaction_date": "2025-06-15", "amount": "199.0", "currency": "SGD", "bill_number": "B3-000037", "business_purpose": "Recurring monthly subscription", "project_id": "", "category": "SOFTWARE", "counterparty": ""})])

add(38, "DUPLICATE_CHECK", "control (near-duplicate)", "medium", "E0055",
    bill("SprintMill", "Singapore", "Singapore", "SGD", 240.0, "B3-000038", "SOFTWARE"),
    "2025-07-15", "2025-07-18", "PRJ-010", {"expense_type": "SOFTWARE", "business_owner": "Priya Nair", "billing": "MONTHLY", "charge_to": "COST_CENTRE"},
    [("previous_expenses", {"expense_id": "PREV-9038", "employee_id": "E0055", "merchant": "SprintMill", "transaction_date": "2025-07-17", "amount": "238.0", "currency": "SGD", "bill_number": "B3-PRIOR-9038", "business_purpose": "One-off consulting add-on", "project_id": "", "category": "SOFTWARE", "counterparty": ""})])

add(39, "SPLIT_TRANSACTION", "control", "medium", "E0013",
    bill("OfficeMart", "Singapore", "Singapore", "SGD", 320.0, "B3-000039", "EQUIPMENT"),
    "2025-07-20", "2025-07-23", "PRJ-010", {"expense_type": "EQUIPMENT", "item": "monitor"},
    [("previous_expenses", {"expense_id": "PREV-9039", "employee_id": "E0013", "merchant": "OfficeMart", "transaction_date": "2025-07-19", "amount": "310", "currency": "SGD", "bill_number": "B3-PRIOR-9039", "business_purpose": "Equipment", "project_id": "PRJ-010", "category": "EQUIPMENT", "counterparty": ""})])

add(40, "SUBMISSION_WINDOW", "control (late)", "easy", "E0013",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 90.0, "B3-000040", "RESTAURANT"),
    "2025-01-05", "2025-06-01", "PRJ-010", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 2, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0}, [])

# CIRC-25-03 relief keys off the TRANSACTION date falling in the outage window (2025-03-10 to -14), not
# the submission date -- my first draft had this backwards.
add(41, "SUBMISSION_WINDOW", "control (outage relief)", "medium", "E0013",
    bill("Kallang Dining Room", "Singapore", "Singapore", "SGD", 90.0, "B3-000041", "RESTAURANT"),
    "2025-03-12", "2025-06-20", "PRJ-010", {"expense_type": "MEAL_EMPLOYEE", "attendees_total": 2, "external_attendees": 0, "alcohol_amount": 0, "tip_amount": 0}, [])

add(42, "RESTRICTED_MERCHANT", "control", "easy", "E0013",
    bill("Golden Dice Casino 2025", "Singapore", "Singapore", "SGD", 200.0, "B3-000042", "ENTERTAINMENT_VENUE"),
    "2025-07-01", "2025-07-04", "PRJ-010", {"expense_type": "OTHER"}, [])

add(43, "PERSONAL_SPEND", "control", "easy", "E0048",
    bill("MovieBox+", "Japan", "Tokyo", "JPY", 1500.0, "B3-000043", "CONSUMER_SERVICE"),
    "2025-07-05", "2025-07-08", "PRJ-031", {"expense_type": "OTHER"}, [])

add(44, "FINANCE_THRESHOLD", "control", "easy", "E0013",
    bill("OfficeMart", "Singapore", "Singapore", "SGD", 5800.0, "B3-000044", "EQUIPMENT"),
    "2025-08-10", "2025-08-13", "PRJ-010", {"expense_type": "EQUIPMENT", "item": "workstation"}, [])

add(45, "APPROVAL_TIERS", "control (valid delegation)", "medium", "E0013",
    bill("Praxis Academy", "Singapore", "Singapore", "SGD", 600.0, "B3-000045", "TRAINING_PROVIDER"),
    "2025-04-20", "2025-04-23", "PRJ-010", {"expense_type": "TRAINING", "learning_plan_id": "LP-9003"},
    [("approval_delegations", {"delegation_id": "DEL-9045", "manager_id": "M014", "delegate_id": "E0064", "delegate_level": "MANAGER", "start_date": "2025-04-01", "end_date": "2025-06-01", "max_amount_sgd": "1000.0", "status": "ACTIVE"}),
     ("manager_approvals", {"approval_id": "APR-9045", "expense_id": "X3-045", "employee_id": "E0013", "manager_id": "M014", "approval_type": "TRAINING", "status": "DELEGATED", "approver_level": "MANAGER", "start_date": "2025-04-01", "end_date": "2025-06-01", "delegation_id": "DEL-9045"})])

add(46, "APPROVAL_TIERS", "control (expired delegation)", "medium", "E0013",
    bill("Praxis Academy", "Singapore", "Singapore", "SGD", 600.0, "B3-000046", "TRAINING_PROVIDER"),
    "2025-04-25", "2025-04-28", "PRJ-010", {"expense_type": "TRAINING", "learning_plan_id": "LP-9004"},
    [("approval_delegations", {"delegation_id": "DEL-9046", "manager_id": "M014", "delegate_id": "E0064", "delegate_level": "MANAGER", "start_date": "2025-01-01", "end_date": "2025-03-01", "max_amount_sgd": "1000.0", "status": "EXPIRED"}),
     ("manager_approvals", {"approval_id": "APR-9046", "expense_id": "X3-046", "employee_id": "E0013", "manager_id": "M014", "approval_type": "TRAINING", "status": "DELEGATED", "approver_level": "MANAGER", "start_date": "2025-01-01", "end_date": "2025-03-01", "delegation_id": "DEL-9046"})])

add(47, "TELECOM_MONTHLY", "control", "easy", "E0013",
    bill("IslandTel", "Singapore", "Singapore", "SGD", 150.0, "B3-000047", "TELECOM"),
    "2025-09-01", "2025-09-04", "PRJ-010", {"expense_type": "TELECOM", "billing_month": "2025-09"}, [])

add(48, "EQUIPMENT_TIERS", "control", "easy", "E0013",
    bill("GadgetHub", "Singapore", "Singapore", "SGD", 320.0, "B3-000048", "EQUIPMENT"),
    "2025-09-10", "2025-09-13", "PRJ-010", {"expense_type": "EQUIPMENT", "item": "keyboard and mouse"},
    [("manager_approvals", {"approval_id": "APR-9048", "expense_id": "X3-048", "employee_id": "E0013", "manager_id": "M014", "approval_type": "GENERAL", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(49, "CONFERENCE_FEE", "control (approval type mismatch -> escalate)", "easy", "E0013",
    bill("Data Leaders Conference", "Singapore", "Singapore", "SGD", 800.0, "B3-000049", "CONFERENCE_ORGANISER"),
    "2025-10-15", "2025-10-18", "PRJ-010", {"expense_type": "CONFERENCE_FEE", "conference_ref": "CONF-9002"},
    [("conference_registry", {"event_id": "CONF-9002", "employee_id": "E0013", "registration_status": "REGISTERED", "official_partner_hotel": ""}),
     ("manager_approvals", {"approval_id": "APR-9049", "expense_id": "X3-049", "employee_id": "E0013", "manager_id": "M014", "approval_type": "TRAINING", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])

add(50, "CAR_RENTAL", "control", "easy", "E0013",
    bill("DriveEasy Rentals 2025", "Singapore", "", "SGD", 220.0, "B3-000050", "CAR_RENTAL"),
    "2025-07-15", "2025-07-18", "PRJ-010", {"expense_type": "CAR_RENTAL"},
    [("manager_approvals", {"approval_id": "APR-9050", "expense_id": "X3-050", "employee_id": "E0013", "manager_id": "M014", "approval_type": "TRAVEL", "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2024-01-01", "end_date": "2026-12-31", "delegation_id": ""})])


if __name__ == "__main__":
    print(f"Defined {len(CASES)} cases. Categories: {sorted({c['archetype'] for c in CASES})}")
    print("Next: python -m scripts.exp60_run_generation to add enterprise rows, compute ground truth, and (separately, after review) draft notes.")
