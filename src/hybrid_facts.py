"""Experiment 12: deterministic fact extraction for the hybrid RAG+rules resolver. No ground truth; reads only the claim, the note (via src/rules_text.py's regex
parser, best-effort) and the enterprise tables (via src/rules_v2.py's general policy-mechanics functions, which key off case_id/employee_id/transaction_date, not
off note-parsed fields, so they are exact regardless of parsing quality). Facts are grouped into four families so Exp 12 can test each one's contribution
separately (H1 arithmetic, H2 temporal/precedence, H3 evidence validation, H4 duplicate/split). The LLM is given facts, never a suggested final decision:
it still applies the retrieved policy text and makes the call, so this measures whether removing mechanics (not removing judgment) fixes the errors Exp 11 found
persist even under perfect policy evidence."""
from __future__ import annotations
from . import rules_text as RT, rules_v2 as RV, tables as T


def _fmt_state(s):
    return "VALID" if s is None else f"{s[0]}: {s[3]}"


def h1_arithmetic(cc, f):
    """FX-normalized amount, submission age, and any per-attendee/per-km/per-night arithmetic the note lets us compute. Fields the note did not state are marked
    unknown rather than guessed, so the LLM knows to treat them as missing evidence, not zero."""
    b = cc["bill"]
    out = {"sgd_equivalent": round(RV.sgd(cc), 2), "submission_age_days": T.days_between(cc["transaction_date"], cc["submission_date"])}
    n, ext = f.get("attendees_total"), f.get("external_attendees")
    if n:
        out["per_person_amount"] = round(b["total"] / n, 2)
    else:
        out["per_person_amount"] = "unknown_from_claim_text"
    if f.get("distance_km"):
        r = RV.MILEAGE[RV.region(cc)][RV.Y(cc)]; out["mileage_calculated_amount"] = round(f["distance_km"] * r, 2)
    if f.get("nights"):
        out["nightly_rate"] = round(b["total"] / f["nights"], 2)
    if f.get("tip_amount") is not None and f.get("alcohol_amount") is not None:
        pre_tip = b["total"] - f["tip_amount"]
        out["tip_pct_of_pre_tip_bill"] = round(100 * f["tip_amount"] / pre_tip, 1) if pre_tip else 0
    return out


def h2_temporal(cc, f):
    """Which policy year and regional addendum apply, and the deterministic submission-window outcome (this already encodes precedence: which year's window,
    whether a circular outage-relief window applies, whether the late tier needs manager approval or Finance escalation)."""
    y = int(cc["transaction_date"][:4]); reg = RV.region(cc)
    out = {"transaction_year": y, "applicable_region_addendum": reg or "none (default schedule)", "submission_window_check": None}
    sub = RV.submission(cc)
    out["submission_window_check"] = {"decision": sub["decision"], "reason": sub["reason"]} if sub else "within window, no approval required"
    et = f.get("expense_type")
    if et == "HOTEL" and f.get("nights"):
        loc = RV.TIER.get(f.get("city") or cc["bill"]["city"]); band = RV.band(RV.grade(cc))
        if loc: out["applicable_hotel_ceiling_local_currency"] = RV.HOTEL[y][loc][band]
    if et in ("MEAL_CLIENT", "MEAL_EMPLOYEE"):
        table = RV.CLIENT_MEAL if et == "MEAL_CLIENT" or (f.get("external_attendees") or 0) > 0 else RV.EMP_MEAL
        out["applicable_meal_ceiling_per_person"] = table[reg][RV.Y(cc)] if reg in table else "no regional addendum: SGD 60 (employee) / SGD 110 (client) default"
    return out


def h3_evidence(cc, f):
    """Approval, travel-request, exception, conference-registration and budget validity — all resolved from the real enterprise tables (exact regardless of
    note-parsing quality), plus their status expressed the way the policy states it (valid / wrong type / wrong date / delegated / missing)."""
    out = {}
    lvl = RV.need_level(cc); out["approval_threshold_level"] = {0: "none", 1: "manager", 2: "director", 9: "finance_review"}[lvl]
    appr = RV.approval_record(cc)
    out["approval_record_present"] = bool(appr)
    if appr:
        et = f.get("expense_type"); types = RV.TYPES.get(et, ("GENERAL",))
        s = RV.approval_state(cc, max(lvl, 1), types)
        out["approval_validity"] = _fmt_state(s); out["approval_record_type"] = appr["approval_type"]; out["approval_record_status"] = appr["status"]
    else:
        out["approval_validity"] = "not on file"
    if f.get("expense_type") in ("HOTEL", "AIRFARE"):
        tr = RV.travel_request(cc, f.get("departure_date"))
        out["approved_travel_request_present"] = bool(tr and tr["status"] == "APPROVED")
    exc_id = f.get("exception_ref")
    if exc_id:
        pid = "TRV-6.1" if f.get("expense_type") == "HOTEL" else "AIR-2.2"
        out["exception_status"] = RV.exception_for(cc, pid, exc_id)
    if f.get("conference_ref"):
        conf = next(iter(RV.rows("conference_registry", event_id=f["conference_ref"])), None)
        out["conference_registration_status"] = conf["registration_status"] if conf else "reference not found"
    bud = RV.budget(cc); out["cost_centre_budget_check"] = {"decision": bud["decision"], "reason": bud["reason"]} if bud else "no budget issue"
    return out


def h4_duplicate_split(cc, f):
    """Exact/possible duplicate and split-transaction state, from the previous-expenses table (exact, regardless of note wording)."""
    dup = RV.duplicates(cc); spl = RV.split(cc)
    return {"duplicate_check": ({"decision": dup["decision"], "reason": dup["reason"]} if dup else "no duplicate found"),
            "split_transaction_check": ({"decision": spl["decision"], "reason": spl["reason"]} if spl else "no related recent transaction crosses a threshold")}


FAMILIES = {"H1_arithmetic": h1_arithmetic, "H2_temporal_precedence": h2_temporal, "H3_evidence_validation": h3_evidence, "H4_duplicate_split": h4_duplicate_split}


def extract(cc: dict) -> tuple:
    """Returns (parsed_form, {family_name: facts_dict})."""
    f = RT.parse(cc)
    cc_form = dict(cc, form=f)   # rules_v2's functions read c["form"]; substitute the note-parsed form so same_kind()/exception_for() etc. see it
    fam = {}
    for name, fn in FAMILIES.items():
        try:
            fam[name] = fn(cc_form, f)
        except Exception as e:  # noqa
            fam[name] = {"error": repr(e)[:150]}
    return f, fam


def facts_block(fam: dict, levels: list) -> dict:
    """Combine the named families (cumulative H-levels) into one facts dict for the prompt."""
    out = {}
    for lv in levels:
        out.update(fam[lv])
    return out
