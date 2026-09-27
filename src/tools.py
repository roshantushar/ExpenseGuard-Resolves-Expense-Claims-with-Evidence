"""Experiment 17: typed, read-only enterprise tools. Every call goes through call_tool(), which validates the tool name and
arguments against a typed spec (not "everything is a non-empty string" — some tools take a list or a date), enforces a
timeout, and returns compact JSON: {"ok", "found", "data", "error"}. Reads only data/03_enterprise_data plus src/rules_v2.py's
general policy-mechanics functions (also runtime-only, no ground truth: see tests/test_no_leakage.py).

Two tiers, matching the Exp 16 finding that raw enterprise rows do not reliably convey validity to a caller:
  LOW LEVEL   get_employee_profile, get_travel_request, get_manager_approval, get_exception_record, get_project_status,
              search_previous_expenses, get_conference_registration, get_merchant_metadata, get_approval_delegation,
              get_cost_centre_budget  -- raw rows, exactly as stored.
  RESOLVED    validate_approval  -- a business fact (valid: true/false) with the evidence trail, not a row to interpret.
"""
from __future__ import annotations
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from . import tables as T
from . import rules_v2 as RV

ID = {"employee_id": r"E\d{4}", "project_id": r"PRJ-\d{3}", "exception_id": r"EXC-\d{4}", "event_id": r"CONF-\d{3}", "expense_id": r"X2-\d{3}",
      "delegation_id": r"DEL-\d{3}", "cost_centre": r"CC-\S+"}
DATE = r"\d{4}-\d{2}-\d{2}"


def _res(found, data=None):
    return {"ok": True, "found": bool(found), "data": data if found else None, "error": None}


def get_employee_profile(employee_id):
    r = next((r for r in T.table("employees") if r["employee_id"] == employee_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("employee_id", "grade", "region", "department", "manager_id", "status")})


def get_travel_request(employee_id, date):
    rs = [r for r in T.table("travel_requests") if r["employee_id"] == employee_id and r["start_date"] <= date <= r["end_date"]]
    return _res(bool(rs), rs and {k: rs[0][k] for k in ("travel_id", "status", "destination", "purpose", "start_date", "end_date", "event_id", "exception_id")})


def get_manager_approval(expense_id):
    rs = [{k: r[k] for k in ("approval_id", "approval_type", "status", "employee_id", "approver_level", "start_date", "end_date", "delegation_id")} for r in T.table("manager_approvals") if r["expense_id"] == expense_id]
    return _res(bool(rs), rs or None)


def get_exception_record(exception_id):
    r = next((r for r in T.table("policy_exceptions") if r["exception_id"] == exception_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("exception_id", "employee_id", "policy_id", "exception_type", "status", "valid_from", "valid_to")})


def get_project_status(project_id):
    r = next((r for r in T.table("project_registry") if r["project_id"] == project_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("project_id", "parent_project_id", "project_status", "cost_centre", "billable")})


def search_previous_expenses(employee_id, merchant=None, date_from=None, date_to=None):
    rs = [r for r in T.table("previous_expenses") if r["employee_id"] == employee_id and (not merchant or r["merchant"] == merchant)
          and (not date_from or r["transaction_date"] >= date_from) and (not date_to or r["transaction_date"] <= date_to)]
    return _res(bool(rs), [{k: r[k] for k in ("expense_id", "employee_id", "merchant", "transaction_date", "amount", "currency", "bill_number", "business_purpose", "project_id", "category", "counterparty")} for r in rs[:10]] or None)


def get_conference_registration(event_id):
    r = next((r for r in T.table("conference_registry") if r["event_id"] == event_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("event_id", "employee_id", "event_name", "registration_status", "official_partner_hotel")})


def get_merchant_metadata(merchant_name):
    r = next((r for r in T.table("merchant_directory") if r["merchant_name"] == merchant_name), None)
    return _res(bool(r), r and {k: r[k] for k in ("merchant_name", "merchant_category", "country", "risk_class", "active")})


def get_approval_delegation(delegation_id):
    r = next((r for r in T.table("approval_delegations") if r["delegation_id"] == delegation_id), None)
    return _res(bool(r), r and {k: r[k] for k in ("delegation_id", "manager_id", "delegate_id", "delegate_level", "start_date", "end_date", "max_amount_sgd", "status")})


def get_cost_centre_budget(cost_centre, year):
    r = next((r for r in T.table("cost_centre_budgets") if r["cost_centre"] == cost_centre and r["year"] == year), None)
    return _res(bool(r), r and {k: r[k] for k in ("cost_centre", "year", "budget_sgd", "committed_sgd", "status")})


def get_fx_rate(currency, year, month):
    r = next((r for r in T.table("fx_rates") if r["currency"] == currency and r["year"] == year and r["month"] == str(int(month))), None)
    return _res(bool(r), r and {"currency": r["currency"], "year": r["year"], "month": r["month"], "sgd_per_unit": r["sgd_per_unit"]})


LEVEL_NAME = {"MANAGER": 1, "DIRECTOR": 2, "NONE": 0}


def validate_approval(expense_id, required_level, required_types, transaction_date, amount_sgd):
    """Resolved business fact, not a row to interpret: is there a valid approval (direct or delegated) for this expense at the
    required level and type, on the transaction date? Built from src/rules_v2.py's own APR-2.x/4.x logic (general rules, not
    per-case), so the same rules_v2 code Exp 2/12/16 already exercise is exposed here as a typed tool. Read-only.
    """
    need = LEVEL_NAME[required_level]
    matches = [r for r in T.table("manager_approvals") if r["expense_id"] == expense_id]
    # Exp 28 finding: reading only the first matching record silently hides a genuine conflict between two sources.
    # If more than one record exists and they disagree on type/status/level, that is a fact in itself (APR-1.3/2.2:
    # conflicting evidence requires Finance review) -- report it as CONFLICTING_RECORDS rather than picking one.
    distinct = {(r["approval_type"], r["status"], r["approver_level"]) for r in matches}
    if len(matches) > 1 and len(distinct) > 1:
        return _res(True, {"approval_present": True, "approval_id": [r["approval_id"] for r in matches], "approval_type": [r["approval_type"] for r in matches],
                            "authority_level": [r["approver_level"] for r in matches], "delegation_used": None, "delegation_valid": None, "valid": False,
                            "reason_code": "CONFLICTING_RECORDS", "reason": f"{len(matches)} approval records for this expense disagree ({sorted(distinct)}); Finance must resolve the conflict."})
    a = matches[0] if matches else None
    base = {"approval_present": bool(a), "approval_id": a["approval_id"] if a else None, "approval_type": a["approval_type"] if a else None,
            "authority_level": a["approver_level"] if a else None, "delegation_used": bool(a and a["status"] == "DELEGATED"), "delegation_valid": None}
    if not a:
        return _res(True, {**base, "valid": False, "reason_code": "NO_APPROVAL_ON_FILE", "reason": "No approval record is on file for this expense."})
    if a["status"] not in ("APPROVED", "DELEGATED"):
        return _res(True, {**base, "valid": False, "reason_code": "INVALID_STATUS", "reason": f"Approval status is {a['status']}, not APPROVED or DELEGATED."})
    if a["approval_type"] not in set(required_types) | {"GENERAL"}:
        return _res(True, {**base, "valid": False, "reason_code": "WRONG_APPROVAL_TYPE", "reason": f"Approval type {a['approval_type']} does not cover this expense category."})
    if not RV.within(transaction_date, a["start_date"], a["end_date"]):
        return _res(True, {**base, "valid": False, "reason_code": "OUTSIDE_DATE_RANGE", "reason": "Approval does not cover the transaction date."})
    if a["status"] == "DELEGATED":
        dl = next((r for r in T.table("approval_delegations") if r["delegation_id"] == a.get("delegation_id")), None)
        dl_valid = bool(dl and RV.within(transaction_date, dl["start_date"], dl["end_date"]) and dl["status"] == "ACTIVE")
        base["delegation_valid"] = dl_valid
        if not dl_valid:
            return _res(True, {**base, "valid": False, "reason_code": "DELEGATION_INVALID", "reason": "Delegation is missing, expired, or inactive."})
        if amount_sgd > float(dl["max_amount_sgd"]) or LEVEL_NAME.get(dl["delegate_level"], 0) < need:
            return _res(True, {**base, "valid": False, "reason_code": "DELEGATION_LIMIT_OR_LEVEL", "reason": "Delegation amount limit or delegate level is insufficient."})
        return _res(True, {**base, "valid": True, "reason_code": "VALID", "reason": "Delegated approval is valid for this amount and level."})
    if LEVEL_NAME.get(a["approver_level"], 0) < need:
        return _res(True, {**base, "valid": False, "reason_code": "INSUFFICIENT_AUTHORITY_LEVEL", "reason": f"Approver level {a['approver_level']} is below the required {required_level}."})
    return _res(True, {**base, "valid": True, "reason_code": "VALID", "reason": "Approval is valid for this amount, type and level."})


def _str(k): return ("str", k)
def _opt_str(k): return ("str?", k)
def _date(): return ("date", None)
def _enum(*vals): return ("enum", vals)
def _list_str(): return ("list_str", None)
def _amount(): return ("amount", None)


# name -> (function, {param: type_spec}, description). Descriptions say what the tool is and what it is NOT for.
TOOLS = {
    "get_employee_profile": (get_employee_profile, {"employee_id": _str("employee_id")}, "Employee grade, region, department and status by employee_id. Use for grade-dependent limits."),
    "get_travel_request": (get_travel_request, {"employee_id": _str("employee_id"), "date": _date()}, "The employee's travel request covering a date (status, destination, and any linked event_id or exception_id). Use to establish trip approval."),
    "get_manager_approval": (get_manager_approval, {"expense_id": _str("expense_id")}, "Raw manager-approval records attached to an expense_id, with type, status and dates. Not for policy exceptions. For a yes/no answer on validity, use validate_approval instead of interpreting this yourself."),
    "get_exception_record": (get_exception_record, {"exception_id": _str("exception_id")}, "An already-approved policy exception by exception_id (status, policy, validity dates). Not for ordinary manager approvals."),
    "get_project_status": (get_project_status, {"project_id": _str("project_id")}, "Project status (ACTIVE/CLOSED), parent project and cost centre by project_id."),
    "search_previous_expenses": (search_previous_expenses, {"employee_id": _str("employee_id"), "merchant": _opt_str("merchant"), "date_from": ("date?", None), "date_to": ("date?", None)},
                                  "An employee's earlier reimbursed expenses, optionally filtered by merchant and date range. Use for duplicate and split checks."),
    "get_conference_registration": (get_conference_registration, {"event_id": _str("event_id")}, "Conference registration status and official partner hotel by event_id (discovered from a travel request)."),
    "get_merchant_metadata": (get_merchant_metadata, {"merchant_name": _str(None)}, "Merchant category, country, risk class and active flag by exact merchant name."),
    "get_approval_delegation": (get_approval_delegation, {"delegation_id": _str("delegation_id")}, "Raw delegation record (delegate, level, validity dates, amount limit) by delegation_id. Not for the approval record itself."),
    "get_cost_centre_budget": (get_cost_centre_budget, {"cost_centre": _str("cost_centre"), "year": _str(None)}, "Cost-centre budget, committed spend and status (OPEN/FROZEN) for a given year."),
    "get_fx_rate": (get_fx_rate, {"currency": _str(None), "year": _str(None), "month": _str(None)}, "SGD-per-unit exchange rate for a currency in a given year and month (frozen monthly rate). Use to convert a claim amount to SGD equivalent."),
    "validate_approval": (validate_approval, {"expense_id": _str("expense_id"), "required_level": _enum("NONE", "MANAGER", "DIRECTOR"), "required_types": _list_str(),
                          "transaction_date": _date(), "amount_sgd": _amount()},
                          "RESOLVED business fact: is there a valid approval (direct or delegated) for this expense at the required level and type? Returns valid true/false with the evidence trail (approval_present, delegation_used, delegation_valid, reason_code), not a row to interpret yourself. Prefer this over get_manager_approval when you only need a validity answer."),
}
_POOL = ThreadPoolExecutor(max_workers=2)


def _err(msg):
    return {"ok": False, "found": False, "data": None, "error": msg}


def _check(kind, key, v):
    if kind == "str" or kind == "str?":
        if not isinstance(v, str) or not v.strip():
            return f"{key or 'value'} must be a non-empty string"
        if key in ID and not re.fullmatch(ID[key], v):
            return f"{key} has invalid format: {v!r}"
    elif kind == "date" or kind == "date?":
        if not isinstance(v, str) or not re.fullmatch(DATE, v):
            return f"value must be a date in YYYY-MM-DD format, got {v!r}"
    elif kind == "enum":
        if v not in key:  # key holds the allowed values tuple for enum
            return f"value must be one of {key}, got {v!r}"
    elif kind == "list_str":
        if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v):
            return f"value must be a non-empty list of strings, got {v!r}"
    elif kind == "amount":
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
            return f"value must be a non-negative number, got {v!r}"
    return None


def call_tool(name: str, args: dict, timeout_s: float = 5.0) -> dict:
    if name not in TOOLS:
        return _err(f"unknown tool: {name}")
    fn, spec, _ = TOOLS[name]
    if not isinstance(args, dict):
        return _err("arguments must be an object")
    req = [k for k, (kind, _) in spec.items() if not kind.endswith("?")]
    missing = [a for a in req if a not in args]
    extra = [a for a in args if a not in spec]
    if missing or extra:
        return _err(f"missing {missing} unexpected {extra}")
    for k, v in args.items():
        kind, key = spec[k]
        err = _check(kind, key if kind == "enum" else (key or k), v)
        if err:
            return _err(err)
    fut = _POOL.submit(fn, **args)
    try:
        return fut.result(timeout=timeout_s)
    except FutureTimeout:
        return _err("timeout")
    except Exception as e:  # noqa
        return _err(f"tool error: {type(e).__name__}")
