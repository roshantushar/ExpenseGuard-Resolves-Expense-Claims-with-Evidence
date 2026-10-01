"""Exp 56: a single, shared, correct hotel-ceiling calculator, applied consistently everywhere a hotel
ceiling is exposed to a model or agent. src/rules_v2.py (frozen) already gets this right inside hotel() --
but only as a side effect of computing a REJECT/None decision, not as a reusable, inspectable function, and
only for the deterministic resolver's own use. src/agent_variants.py's lookup_hotel_ceiling (the guarded
agent's tool) and src/hybrid_facts.py's applicable_hotel_ceiling_local_currency (the single-shot resolver's
fact) each independently reimplemented the base lookup and both skipped every circular/uplift/long-stay
adjustment. This module does not edit any of those three files. It is a new, standalone Exp 56 candidate;
Exp 32/45/47-52's saved results and the files behind them are untouched.

Order applied, per policy: base yearly ceiling (TRV-3.x, by tier and grade band) -> effective circular
(CIRC-25-06 Tokyo +5% from 2025-07-01, CIRC-26-04 India-T1 +6% from 2026-04-01) -> eligible partner-hotel
uplift (registered conference stay at the event's official partner hotel: +20% before 2026, +25% from
2026) -> long-stay factor (>14 nights from 2025: x0.9) -> exception check (a cited TRV-6.1 exception,
validated against the exceptions table, can still clear an over-ceiling claim).
"""
from __future__ import annotations
from src import rules_v2 as RV


def compute_hotel_ceiling(case: dict, grade: str, nights: int) -> dict:
    """Returns {ceiling, clause_ids, steps: [(label, value)]} -- the number AND which clauses/adjustments
    produced it, in the order they were applied, so a caller (or a human reviewing the trace) can see
    exactly how the final figure was reached."""
    b = case["bill"]; y = int(case["transaction_date"][:4]); d = case["transaction_date"]
    band = RV.band(int(str(grade).upper().lstrip("G")))
    tier = RV.TIER.get(b["city"])
    fallback_used = tier is None
    if tier is None:
        # matches agent_variants.lookup_hotel_ceiling's fallback: an unlisted city (e.g. Chennai, not in
        # TRV-2.2's table) uses the lowest-ceiling tier for its country, rather than erroring out -- an
        # earlier version of this function returned a hard error here, which sent the agent around it to
        # misread a raw (and wrong-year) policy table on its own (X2-104).
        country_prefix = {"India": "IN", "Japan": "JP", "Singapore": "SG"}.get(b["country"], b["country"][:2].upper())
        candidates = [(t, RV.HOTEL[y][t][band]) for t in RV.HOTEL[y] if t.startswith(country_prefix)]
        if not candidates:
            return {"ok": False, "error": f"no tier found for country {b['country']!r}"}
        tier = min(candidates, key=lambda tv: tv[1])[0]
    base = RV.HOTEL[y][tier][band]
    steps = [("base_yearly_ceiling", base, "TRV-3." + {2024: "1", 2025: "2", 2026: "3"}[y])]
    ceiling = base
    clauses = ["TRV-2.2", "TRV-3." + {2024: "1", 2025: "2", 2026: "3"}[y]]
    if tier == "JP-TOKYO" and y == 2025 and d >= "2025-07-01":
        ceiling = RV.rnd(ceiling * 1.05)
        steps.append(("circular_uplift_CIRC-25-06", ceiling, "CIRC-25-06")); clauses.append("CIRC-25-06")
    if tier == "IN-T1" and y == 2026 and d >= "2026-04-01":
        ceiling = RV.rnd(ceiling * 1.06)
        steps.append(("circular_uplift_CIRC-26-04", ceiling, "CIRC-26-04")); clauses.append("CIRC-26-04")
    tr = RV.travel_request(case)
    conf = next(iter(RV.rows("conference_registry", event_id=tr["event_id"])), None) if tr and tr.get("event_id") else None
    partner = bool(conf and conf["employee_id"] == case["employee_id"] and conf["registration_status"] == "REGISTERED" and conf["official_partner_hotel"] == b["merchant"])
    if partner:
        ceiling = ceiling * (1.2 if y < 2026 else 1.25)
        steps.append(("partner_hotel_conference_uplift", ceiling, "TRV-4.1")); clauses.append("TRV-4.1")
    if nights and nights > 14 and y >= 2025:
        ceiling *= 0.9
        steps.append(("long_stay_factor", ceiling, "TRV-5.1")); clauses.append("TRV-5.1")
    rate = b["total"] / nights if nights else None
    compliant = rate is not None and rate <= ceiling + 1e-9
    result = {"ok": True, "tier": tier, "band": band, "ceiling": round(ceiling, 2), "nightly_rate": round(rate, 2) if rate is not None else None,
              "compliant": compliant, "policy_evidence": clauses, "steps": steps, "fallback_tier_used": fallback_used}
    if not compliant and rate is not None:
        exc_id = None  # exception lookup requires the note-parsed form; caller supplies it if relevant
        result["reason"] = f"Nightly rate {rate:.0f} exceeds ceiling {ceiling:.0f}; no exception cited here."
    else:
        result["reason"] = "Within the applicable ceiling." if compliant else "Cannot compute: nights unknown."
    return result


from src import rules_text as RT


def make_check_hotel_compliance_v56(case: dict):
    """Drop-in replacement for agent_variants.make_check_hotel_compliance, same call signature and
    same TRV-1.1 / exception-status structure, but the ceiling itself comes from compute_hotel_ceiling
    (base -> circular -> partner uplift -> long-stay) instead of the uncorrected base-table lookup."""
    f = RT.parse(case)

    def check_hotel_compliance(grade, nights=None, check_in_date=None, check_out_date=None) -> dict:
        if f.get("expense_type") != "HOTEL":
            return {"ok": False, "found": False, "data": None, "error": "this claim is not a HOTEL expense; check_hotel_compliance does not apply here"}
        tr = RV.travel_request(case)
        if not tr or tr.get("status") != "APPROVED":
            return {"ok": True, "found": True, "data": {"policy_disposition": "REQUEST_INFORMATION", "policy_evidence": ["TRV-1.1"], "missing_fields": ["approved_travel_request"],
                                                          "reason": "No approved travel request covers the transaction date."}, "error": None}
        if check_in_date and check_out_date:
            from datetime import date as _date
            try:
                nights = (_date.fromisoformat(check_out_date) - _date.fromisoformat(check_in_date)).days
            except ValueError:
                return {"ok": False, "found": False, "data": None, "error": "check_in_date/check_out_date must be YYYY-MM-DD"}
        else:
            nights = nights or f.get("nights")
        if not nights:
            return {"ok": False, "found": False, "data": None, "error": "nights not stated; pass check_in_date and check_out_date (preferred) or nights directly"}
        r = compute_hotel_ceiling(case, grade, int(nights))
        if not r["ok"]:
            return {"ok": False, "found": False, "data": None, "error": r["error"]}
        if r["compliant"]:
            return {"ok": True, "found": True, "data": {**r, "policy_disposition": None}, "error": None}
        exc_id = f.get("exception_ref") or tr.get("exception_id")
        st = RV.exception_for(case, "TRV-6.1", exc_id)
        if st == "VALID":
            return {"ok": True, "found": True, "data": {**r, "compliant": True, "policy_disposition": None, "reason": "A valid exception covers the overage."}, "error": None}
        if st == "WRONG_SCOPE":
            return {"ok": True, "found": True, "data": {**r, "policy_disposition": "ESCALATE", "policy_evidence": r["policy_evidence"] + ["EXC-2.1"],
                                                          "reason": "Exception names a different policy or employee -- Finance must review."}, "error": None}
        if st == "MISSING_ID":
            return {"ok": True, "found": True, "data": {**r, "policy_disposition": "REQUEST_INFORMATION", "policy_evidence": r["policy_evidence"] + ["EXC-2.1"],
                                                          "reason": "Cited exception identifier does not exist; request the correct reference."}, "error": None}
        # st is "NONE" (no exception cited) or "INVALID" (cited but not approved / outside its date window)
        # -- rules_v2.hotel()'s own catch-all treats both the same way: REJECT. Exp 58's first version only
        # handled "NONE" explicitly and fell through to a REQUEST_INFORMATION default for "INVALID" (X2-012,
        # an EXPIRED exception) -- a bug this replicated from agent_variants.make_check_hotel_compliance,
        # which has the same gap. Fixed here to match rules_v2.hotel()'s behavior exactly.
        return {"ok": True, "found": True, "data": {**r, "policy_disposition": "REJECT", "policy_evidence": r["policy_evidence"] + (["EXC-2.1"] if st == "INVALID" else []),
                                                      "reason": r["reason"] if st == "NONE" else "Cited exception is not approved or is outside its validity window; treated as no valid exception."}, "error": None}

    return check_hotel_compliance


if __name__ == "__main__":
    import json, sys
    sys.path.insert(0, ".")
    from src import llm_exp
    cases = {c["case_id"]: c for c in llm_exp.cases_for("DEVELOPMENT")}
    for cid, grade, nights in [("X2-011", "G4", 2), ("X2-029", "G4", 3), ("X2-139", "G4", 3), ("X2-132", "G4", 2), ("X2-148", "G4", 2)]:
        c = cases.get(cid)
        if not c:
            continue
        r = compute_hotel_ceiling(c, grade, nights)
        print(cid, json.dumps(r, indent=1))
