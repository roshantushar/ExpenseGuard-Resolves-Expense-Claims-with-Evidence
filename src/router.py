"""Experiment 30: selective architecture router. Cheapest sufficient path per claim, decided from the claim only:
claim-only categories -> deterministic rules (no tools); claims that can depend on enterprise evidence (hotel, software, or any prior expense by the same
employee and merchant) -> fixed tool workflow. The bounded-agent branch is deliberately absent (Exp 19: not justified)."""
from __future__ import annotations
from . import rules, tables as T, workflow

EVIDENCE_CATEGORIES = {"HOTEL", "SOFTWARE"}


def needs_evidence(c: dict) -> bool:
    if c["bill"]["merchant_category"] in EVIDENCE_CATEGORIES:
        return True
    return any(p["employee_id"] == c["employee_id"] and p["merchant"] == c["bill"]["merchant"] for p in T.table("previous_expenses"))  # possible duplicate / split


def route(c: dict) -> dict:
    if needs_evidence(c):
        d = workflow.run(c); d["route"] = "workflow"
    else:
        d = rules.decide(c); d["trace"], d["tool_calls"], d["route"] = [], 0, "rules"
    return d
