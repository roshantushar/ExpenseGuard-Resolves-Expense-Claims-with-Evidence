"""Read-only access to the enterprise tables (runtime-safe: no ground truth)."""
from __future__ import annotations
import csv
from datetime import date
from functools import lru_cache
from . import config as C


@lru_cache(maxsize=None)
def table(name: str) -> list:
    with open(C.ENTERPRISE / f"{name}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def employee(eid: str) -> dict:
    return next((r for r in table("employees") if r["employee_id"] == eid), {})


def fx_to_sgd(currency: str, txn_date: str) -> float:
    y, m = int(txn_date[:4]), int(txn_date[5:7])
    r = next(r for r in table("fx_rates") if int(r["year"]) == y and int(r["month"]) == m and r["currency"] == currency)
    return float(r["sgd_per_unit"])


def days_between(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days
