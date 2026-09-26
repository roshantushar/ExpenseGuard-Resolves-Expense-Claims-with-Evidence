"""Label-free flag defined before the final test (Exp 32 manifest): currency-threshold ambiguity.
A claim is flagged when it is in a non-SGD currency and an SGD-equivalent approval threshold that applies to its type is crossed by the raw amount but not by the FX-converted amount:
- software (CARD-2.1 / CIRC-26-02): raw total > 1000 while the SGD equivalent is <= 1000;
- split-transaction candidates (APR-1.1): combined raw total > 500 while the combined SGD equivalent is <= 500.
Uses only the claim, the frozen FX table and previous expenses; never labels."""
from __future__ import annotations
from . import history, tables as T


def currency_ambiguous(c: dict) -> bool:
    b = c["bill"]
    if b["currency"] == "SGD":
        return False
    rate = T.fx_to_sgd(b["currency"], c["transaction_date"])
    if b["merchant_category"] == "SOFTWARE" and b["total"] > 1000 >= b["total"] * rate:
        return True
    rel = history.related_expenses(c)
    if rel:
        combined = b["total"] + sum(float(p["amount"]) for p in rel)
        return combined > 500 >= combined * rate
    return False
