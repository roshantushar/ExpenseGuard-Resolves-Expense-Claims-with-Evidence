"""Experiment 17: typed, read-only enterprise tools. Every call goes through call_tool(), which validates the tool name and
arguments, enforces a timeout, and returns compact JSON: {"ok", "found", "data", "error"}. Reads only data/03_enterprise_data."""
from __future__ import annotations
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from . import tables as T

ID = {"employee_id": r"E\d{4}", "project_id": r"PRJ-\d{3}", "exception_id": r"EXC-[A-Z]+-\d{3}", "event_id": r"CONF-\d{3}", "expense_id": r"EXP-\d{4}",
      "date": r"\d{4}-\d{2}-\d{2}", "date_from": r"\d{4}-\d{2}-\d{2}", "date_to": r"\d{4}-\d{2}-\d{2}"}


def _res(found, data=None):
    return {"ok": True, "found": bool(found), "data": data if found else None, "error": None}


def get_employee_profile(employee_id):
    r = next((r for r in T.table("employees") if r["employee_id"] == employee_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("employee_id", "grade", "region", "department", "manager_id", "status")})


def get_travel_request(employee_id, date):
    rs = [r for r in T.table("travel_requests") if r["employee_id"] == employee_id and r["start_date"] <= date <= r["end_date"]]
    return _res(bool(rs), rs and {k: rs[0][k] for k in ("travel_id", "status", "destination", "purpose", "start_date", "end_date", "event_id", "exception_id")})


def get_manager_approval(expense_id):
    rs = [{k: r[k] for k in ("approval_id", "approval_type", "status", "employee_id", "start_date", "end_date")} for r in T.table("manager_approvals") if r["expense_id"] == expense_id]
    return _res(bool(rs), rs or None)


def get_exception_record(exception_id):
    r = next((r for r in T.table("policy_exceptions") if r["exception_id"] == exception_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("exception_id", "employee_id", "policy_id", "exception_type", "status", "valid_from", "valid_to")})


def get_project_status(project_id):
    r = next((r for r in T.table("project_registry") if r["project_id"] == project_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("project_id", "project_status", "billable", "travel_allowed")})


def search_previous_expenses(employee_id, merchant=None, date_from=None, date_to=None):
    rs = [r for r in T.table("previous_expenses") if r["employee_id"] == employee_id and (not merchant or r["merchant"] == merchant)
          and (not date_from or r["transaction_date"] >= date_from) and (not date_to or r["transaction_date"] <= date_to)]
    return _res(bool(rs), [{k: r[k] for k in ("expense_id", "employee_id", "merchant", "transaction_date", "amount", "currency", "bill_number", "business_purpose", "project_id")} for r in rs[:10]] or None)


def get_conference_registration(event_id):
    r = next((r for r in T.table("conference_registry") if r["event_id"] == event_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("event_id", "employee_id", "event_name", "registration_status", "official_partner_hotel", "approved_rate_multiplier")})


def get_merchant_metadata(merchant_name):
    r = next((r for r in T.table("merchant_directory") if r["merchant_name"] == merchant_name), None)
    return _res(bool(r), r and {k: r[k] for k in ("merchant_name", "merchant_category", "country", "active")})


# name -> (function, required args, optional args, description). Descriptions say what the tool is and what it is NOT for.
TOOLS = {
    "get_employee_profile": (get_employee_profile, ["employee_id"], [], "Employee grade, region, department and status by employee_id. Use for grade-dependent limits."),
    "get_travel_request": (get_travel_request, ["employee_id", "date"], [], "The employee's travel request covering a date (status, destination, and any linked event_id or exception_id). Use to establish trip approval."),
    "get_manager_approval": (get_manager_approval, ["expense_id"], [], "Manager approval records attached to an expense_id, with approval type and validity. Not for policy exceptions."),
    "get_exception_record": (get_exception_record, ["exception_id"], [], "An already-approved policy exception by exception_id (status, policy, validity dates). Not for ordinary manager approvals."),
    "get_project_status": (get_project_status, ["project_id"], [], "Project status (ACTIVE/CLOSED), billable and travel_allowed flags by project_id."),
    "search_previous_expenses": (search_previous_expenses, ["employee_id"], ["merchant", "date_from", "date_to"], "An employee's earlier reimbursed expenses, optionally filtered by merchant and date range. Use for duplicate and split checks."),
    "get_conference_registration": (get_conference_registration, ["event_id"], [], "Conference registration status and official partner hotel by event_id (discovered from a travel request)."),
    "get_merchant_metadata": (get_merchant_metadata, ["merchant_name"], [], "Merchant category, country and active flag by exact merchant name."),
}
_POOL = ThreadPoolExecutor(max_workers=2)


def _err(msg):
    return {"ok": False, "found": False, "data": None, "error": msg}


def call_tool(name: str, args: dict, timeout_s: float = 5.0) -> dict:
    if name not in TOOLS:
        return _err(f"unknown tool: {name}")
    fn, req, opt, _ = TOOLS[name]
    if not isinstance(args, dict):
        return _err("arguments must be an object")
    missing = [a for a in req if a not in args]
    extra = [a for a in args if a not in req + opt]
    if missing or extra:
        return _err(f"missing {missing} unexpected {extra}")
    for k, v in args.items():
        if not isinstance(v, str) or not v.strip():
            return _err(f"{k} must be a non-empty string")
        if k in ID and not re.fullmatch(ID[k], v):
            return _err(f"{k} has invalid format: {v!r}")
    fut = _POOL.submit(fn, **args)
    try:
        return fut.result(timeout=timeout_s)
    except FutureTimeout:
        return _err("timeout")
    except Exception as e:  # noqa
        return _err(f"tool error: {type(e).__name__}")
