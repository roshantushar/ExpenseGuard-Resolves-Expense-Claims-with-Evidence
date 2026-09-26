"""Exp 14 and 15: duplicate and split-transaction logic over previous_expenses. Runtime-safe (claim + enterprise tables only)."""
from __future__ import annotations
from datetime import date
from . import tables as T

SPLIT_DAYS = 3        # related purchases: same employee, merchant, project, currency within this many days
DUP_AMOUNT_TOL = 0.02  # near-duplicate: amount within 2%
THRESHOLD_SGD = 500    # APR-1.1


def _d(s): return date.fromisoformat(s)


def _same_party(c, p):
    return p["employee_id"] == c["employee_id"] and p["merchant"] == c["bill"]["merchant"] and p["currency"] == c["bill"]["currency"]


def _prev(prev):
    return T.table("previous_expenses") if prev is None else prev


def exact_duplicate(c, prev=None):
    """Approach A: exact deterministic match (same bill number, or same employee + merchant + date + amount)."""
    b = c["bill"]
    for p in _prev(prev):
        if p["employee_id"] == c["employee_id"] and p["merchant"] == b["merchant"] and (
                p["bill_number"] == b["bill_number"] or (p["transaction_date"] == c["transaction_date"] and float(p["amount"]) == b["total"])):
            return p
    return None


def fuzzy_candidates(c, prev=None):
    """Approach B: candidate generation. Same employee, merchant, currency; amount within tolerance; within 35 days."""
    b = c["bill"]
    out = []
    for p in _prev(prev):
        if _same_party(c, p) and p["bill_number"] != b["bill_number"] and abs(float(p["amount"]) - b["total"]) <= DUP_AMOUNT_TOL * b["total"] \
                and abs((_d(p["transaction_date"]) - _d(c["transaction_date"])).days) <= 35:
            out.append(p)
    return out


def classify_duplicate_rule(c, prev=None):
    """Approach B: fully deterministic class. Returns (class, matched expense ids)."""
    ex = exact_duplicate(c, prev)
    if ex:
        return "EXACT_DUPLICATE", [ex["expense_id"]]
    cands = fuzzy_candidates(c, prev)
    if not cands:
        return "NONE", []
    p = cands[0]
    gap = abs((_d(p["transaction_date"]) - _d(c["transaction_date"])).days)
    recurring = "monthly" in p["business_purpose"].lower() or "recurring" in c["employee_description"].lower()
    if gap <= 3 and not recurring:
        return "POSSIBLE_DUPLICATE", [p["expense_id"]]
    return ("LEGITIMATE_REPEAT" if recurring else "POSSIBLE_DUPLICATE"), [p["expense_id"]]


def related_expenses(c, prev=None):
    """Exp 15: previous purchases that may have been split from the current one (same employee, merchant, project, currency, within SPLIT_DAYS, not a near-duplicate)."""
    b = c["bill"]
    return [p for p in _prev(prev) if _same_party(c, p) and p["project_id"] == c["project_id"] and p["bill_number"] != b["bill_number"]
            and abs((_d(p["transaction_date"]) - _d(c["transaction_date"])).days) <= SPLIT_DAYS
            and abs(float(p["amount"]) - b["total"]) > DUP_AMOUNT_TOL * b["total"]]


def split_check(c, prev=None):
    """Combine amounts deterministically, test APR-1.1, look up approval evidence. Returns a dict of findings and a disposition."""
    rel = related_expenses(c, prev)
    if not rel:
        return {"related_ids": [], "split_detected": False, "combined_amount": None, "triggered_policy": "", "decision": None, "note": "no related transactions"}
    b = c["bill"]
    combined = b["total"] + sum(float(p["amount"]) for p in rel)
    rate = T.fx_to_sgd(b["currency"], c["transaction_date"])
    alone_sgd, comb_sgd = b["total"] * rate, combined * rate
    triggered = comb_sgd > THRESHOLD_SGD >= alone_sgd
    appr = [r for r in T.table("manager_approvals") if r["expense_id"] == c["case_id"] and r["status"] == "APPROVED"]
    covers = any(r["approval_type"] == "COMBINED_DISCRETIONARY_SPEND" for r in appr)
    if triggered:
        dec = "APPROVE" if covers else "ESCALATE" if appr else "REQUEST_INFORMATION"   # other-purpose approval = conflicting evidence (APR-1.3)
    else:
        dec = "ESCALATE" if appr and not covers else None                              # unrelated approval on file next to related spend: conflict
    return {"related_ids": [p["expense_id"] for p in rel], "split_detected": triggered, "combined_amount": combined, "combined_sgd": round(comb_sgd, 2), "alone_sgd": round(alone_sgd, 2),
            "triggered_policy": "APR-1.1" if triggered else "", "decision": dec, "note": "approval covers combined spend" if covers else "approval of another purpose" if appr else "no approval record"}
