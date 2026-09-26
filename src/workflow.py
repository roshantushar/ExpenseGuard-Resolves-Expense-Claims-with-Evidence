"""Experiment 18: fixed enterprise workflow. Claim-level rules first (src/rules.py); hotel and software claims then follow a fixed, pre-declared tool
sequence through src/tools.py. Branching happens only through if/else on tool observations; no model is involved."""
from __future__ import annotations
import re, time
from . import history, rules, tables as T, tools

FLOW_POLICY = {"HOTEL": "TRV-1.1/TRV-1.2/CONF-2.1", "SOFTWARE": "CARD-2.1/CIRC-26-02"}


class StepCapExceeded(RuntimeError):
    pass


class Trace:
    """Tool caller with guardrails: identical calls are de-duplicated (served from the first observation), a hard step cap stops the run,
    and any failed call (timeout, validation error) is recorded so the workflow can escalate instead of guessing."""

    def __init__(self, max_calls: int = 8, timeout_s: float = 5.0):
        self.calls, self.max_calls, self.timeout_s, self.seen, self.failed, self.deduped = [], max_calls, timeout_s, {}, [], 0

    def __call__(self, name, **args):
        key = (name, tuple(sorted(args.items())))
        if key in self.seen:
            self.deduped += 1
            return self.seen[key]
        if len(self.calls) >= self.max_calls:
            raise StepCapExceeded(f"step cap {self.max_calls} reached")
        t0 = time.perf_counter()
        r = tools.call_tool(name, args, timeout_s=self.timeout_s)
        self.seen[key] = r
        if not r["ok"]:
            self.failed.append({"tool": name, "error": r["error"]})
        self.calls.append({"tool": name, "args": args, "ok": r["ok"], "found": r["found"], "data": r["data"], "error": r["error"], "latency_ms": round((time.perf_counter() - t0) * 1000, 3)})
        return r


def _out(decision, policy, missing=(), reason=""):
    return rules._out(decision, policy, missing, reason)


def _hotel(c, call):
    b, year = c["bill"], int(c["transaction_date"][:4])
    prof = call("get_employee_profile", employee_id=c["employee_id"])
    grade = int(prof["data"]["grade"][1:]) if prof["found"] else 1
    region = rules.REGION.get(b["country"], "")
    loc = "TOKYO" if "tokyo" in b["merchant"].lower() else region
    ceiling = rules.HOTEL[loc][year - 2024][0 if grade <= 3 else 1 if grade <= 5 else 2]
    cited = (re.search(r"EXC-[A-Z]+-\d{3}", c["employee_description"]) or [None])[0]
    tr = call("get_travel_request", employee_id=c["employee_id"], date=c["transaction_date"])
    trip_ok = tr["found"] and tr["data"]["status"] == "APPROVED"
    if not trip_ok and not cited:
        return _out("REQUEST_INFORMATION", ["TRV-1.1", "TRV-5.1"], ["approved_travel_request"], "No approved travel request covers the stay.")
    if trip_ok and b["total"] <= ceiling:
        return _out("APPROVE", ["TRV-1.2"], (), "Within the base hotel ceiling with an approved trip.")
    exc_id = cited or (tr["data"]["exception_id"] if trip_ok else None)
    if exc_id:
        ex = call("get_exception_record", exception_id=exc_id)
        d = ex["data"]
        if ex["found"] and d["status"] == "APPROVED" and d["valid_from"] <= c["transaction_date"] <= d["valid_to"] and d["employee_id"] == c["employee_id"] and d["policy_id"] == "TRV-1.2":
            return _out("APPROVE", ["TRV-1.2", "APR-2.2"], (), f"Approved hotel-limit exception {exc_id} covers the date.")
        return _out("REJECT", ["TRV-1.2", "APR-2.2"], (), f"Exception {exc_id} is not valid for this claim (status/date/employee).")
    if trip_ok and tr["data"]["event_id"]:
        cf = call("get_conference_registration", event_id=tr["data"]["event_id"])
        d = cf["data"]
        if cf["found"] and d["registration_status"] == "REGISTERED" and d["official_partner_hotel"] == b["merchant"] and b["total"] <= ceiling * float(d["approved_rate_multiplier"]):
            return _out("APPROVE", ["CONF-2.1", "TRV-1.3"], (), "Registered conference at the official partner hotel; within the conference ceiling.")
        return _out("REJECT", ["CONF-2.1", "CONF-2.2"], (), "Over the ceiling and the conference exception does not apply.")
    # Over the ceiling with an approved trip but neither an exception nor a conference on record: the claim does not establish whether an exception applies.
    # GEP26-4.1: missing evidence must result in request-for-information or escalation, not a guessed rejection (decision recorded in the Exp 32 freeze manifest).
    return _out("ESCALATE", ["GEP26-4.1", "TRV-1.2"], (), "Over the hotel ceiling; no exception or conference on record. Escalated for Finance to determine whether an exception applies.")


def _software(c, call):
    b = c["bill"]
    sgd = b["total"] * T.fx_to_sgd(b["currency"], c["transaction_date"])
    if sgd <= 500:
        return _out("APPROVE", ["CARD-2.1"], (), "Below the approval threshold.")
    ap = call("get_manager_approval", expense_id=c["case_id"])
    ok = ap["found"] and any(r["status"] == "APPROVED" for r in ap["data"])
    if not ok:
        return _out("REQUEST_INFORMATION", ["CARD-2.1", "APR-3.1"], ["manager_approval"], "Approval record required above SGD 500 and none found.")
    if sgd > 1000 and c["transaction_date"] >= "2026-02-01":
        pr = call("get_project_status", project_id=c["project_id"])
        if not pr["found"] or pr["data"]["project_status"] != "ACTIVE":
            return _out("ESCALATE", ["CIRC-26-02"], (), "Software above SGD 1000 needs an active project record; project is not active.")
    return _out("APPROVE", ["CARD-2.1", "CIRC-26-02"], (), "Approval on file and project active.")


def run(c: dict, trace: "Trace" = None) -> dict:
    call = trace or Trace()
    try:
        d = _run(c, call)
    except StepCapExceeded as e:
        d = _out("ESCALATE", ["GEP26-4.1"], (), f"Step cap reached ({e}); escalated instead of guessing.")
    if call.failed and d["decision"] != "ESCALATE":
        d = _out("ESCALATE", ["GEP26-4.1"], (), f"Lookup failed ({call.failed[0]['tool']}: {call.failed[0]['error']}); escalated instead of guessing.")
    d["trace"] = call.calls
    d["tool_calls"] = len(call.calls)
    d["deduped_calls"] = call.deduped
    return d


def _run(c: dict, call) -> dict:
    base = rules.decide(c)
    hist = call("search_previous_expenses", employee_id=c["employee_id"], merchant=c["bill"]["merchant"])
    prev = hist["data"] if hist["found"] else []
    dup_class, dup_ids = history.classify_duplicate_rule(c, prev)
    split = history.split_check(c, prev)
    if dup_class == "EXACT_DUPLICATE":
        d = _out("REJECT", ["CARD-4.1"], (), f"Exact duplicate of {dup_ids[0]}.")
        return d
    if dup_class == "POSSIBLE_DUPLICATE":
        d = _out("REQUEST_INFORMATION", ["CARD-4.1"], ["duplicate_clarification"], f"Possible duplicate of {dup_ids[0]}; clarification needed.")
        return d
    if split["decision"] is not None:
        d = _out(split["decision"], [x for x in ("CARD-3.1", split["triggered_policy"] or "APR-1.3") if x], ["manager_approval"] if split["decision"] == "REQUEST_INFORMATION" else (),
                 f"Related purchases {split['related_ids']}; combined {split['combined_amount']}; {split['note']}.")
        return d
    cat = c["bill"]["merchant_category"]
    hotel_needs_evidence = cat == "HOTEL" and (base["decision"] == "APPROVE" or "CONF-2.1" in base["policy_evidence"])
    software_needs_evidence = cat == "SOFTWARE" and base["decision"] in ("APPROVE", "REQUEST_INFORMATION") and (not base["missing_fields"] or base["missing_fields"] == ["manager_approval"])
    if hotel_needs_evidence:
        d = _hotel(c, call)
    elif software_needs_evidence:
        d = _software(c, call)
    else:
        d = base
    return d
