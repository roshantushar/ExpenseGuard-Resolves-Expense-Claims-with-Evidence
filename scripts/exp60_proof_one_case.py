"""Exp 60 proof step: redirect the runtime's enterprise-table reads to an isolated copy
(experiments/exp60_holdout/enterprise_data/, never ExpenseGuard_DATASET/03_enterprise_data/) and run ONE
new, hand-built case through both the frozen resolver and the Exp 59 candidate, end to end, with no model
calls. Confirms the redirection mechanism actually works and touches nothing in the real dataset before
any of the other 49 cases get built or any paid call is made.
"""
from __future__ import annotations
import json
from src import config as C

C.ENTERPRISE = C.ROOT / "experiments" / "exp60_holdout" / "enterprise_data"  # redirect BEFORE any table() call

from src import resolver as R, rules_text as RT, rules_v2 as RV, tables as T
from scripts.exp59_final_fix import deterministic_fixed, run_one_v59

CASE = {
    "case_id": "X3-001",
    "employee_id": "E0159",
    "transaction_date": "2025-09-11",
    "submission_date": "2025-09-14",
    "bill": {
        "merchant": "Garden Tokyo Hotel", "country": "Japan", "city": "Tokyo", "currency": "JPY",
        "total": 69800.0, "bill_number": "B3-000001", "merchant_category": "TRAVEL",
        "line_items": [{"description": "Charges", "amount": 69800.0}],
    },
    "form": {},
    "employee_description": (
        "Two nights at the Garden Tokyo Hotel for a client visit, in from the 10th of September through "
        "the 12th, 2025. Billed in full on departure, no extras on the folio."
    ),
    "project_id": "PRJ-031",
    "split": "EXP60_HOLDOUT",
}

EXPECTED_REASONING = (
    "JP-TOKYO tier, grade G4 (band G4-G5), 2025 base ceiling 34,000 JPY. Transaction date 2025-09-11 is "
    "after CIRC-25-06's 2025-07-01 effective date, so the ceiling is adjusted: 34,000 x 1.05 = 35,700 JPY. "
    "2 nights (Sep 10 -> Sep 12), total 69,800 JPY -> nightly rate 34,900 JPY. 34,900 <= 35,700: compliant. "
    "Deliberately chosen BETWEEN the base ceiling (34,000, would REJECT) and the circular-adjusted ceiling "
    "(35,700, APPROVEs) to directly test whether the circular is applied. Travel request TR-9001 (APPROVED, "
    "isolated copy only) covers the date. Manager approval APR-9001 (isolated copy only) is on file. "
    "Expected: APPROVE."
)


def main():
    print("config.ENTERPRISE =", C.ENTERPRISE)
    assert "exp60_holdout" in str(C.ENTERPRISE), "REDIRECTION FAILED -- refusing to proceed against the real dataset"

    emp = T.employee("E0159")
    print("\nEmployee record read from isolated copy:", emp)
    assert emp, "employee lookup failed against isolated tables"

    print("\nEXPECTED (hand-reasoned, independent of runtime code):")
    print(EXPECTED_REASONING)

    print("\n--- Frozen resolver (official, unmodified) ---")
    f = RT.parse(CASE)
    c2 = dict(CASE, form=f)
    d = RV.decide(c2)
    print(json.dumps(d, indent=1))

    print("\n--- Exp 59 candidate, deterministic routing ---")
    d2, conclusive = deterministic_fixed(CASE)
    print(json.dumps(d2, indent=1), "| conclusive:", conclusive)

    if not conclusive:
        print("\n--- Exp 59 candidate would proceed to the agent (no model call made in this proof step) ---")

    print("\n(No paid model calls were made in this proof step.)")


if __name__ == "__main__":
    main()
