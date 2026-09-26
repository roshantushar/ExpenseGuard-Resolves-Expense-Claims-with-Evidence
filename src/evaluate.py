"""Evaluator: joins private ground truth AFTER the run. Never import from runtime code."""
from __future__ import annotations
import json, statistics as st
from collections import Counter, defaultdict
from . import config as C
from .metrics import wilson, pct


def load_gt() -> dict:
    return {g["case_id"]: g for g in (json.loads(l) for l in (C.GROUND_TRUTH / "ground_truth.jsonl").read_text().splitlines() if l.strip())}


def evaluate(recs: list, gt: dict) -> tuple:
    """recs need case_id, predicted_decision, manual_review_required, missing_fields, latency_ms, input_tokens, output_tokens, model_cost_usd.
    Returns (summary, per-case evaluation rows)."""
    rows, fam = [], defaultdict(lambda: [0, 0])
    for r in recs:
        g = gt[r["case_id"]]
        ok = r["predicted_decision"] == g["expected_decision"]
        fam[g["case_family"]][0] += ok; fam[g["case_family"]][1] += 1
        rows.append({"case_id": r["case_id"], "expected_decision": g["expected_decision"], "predicted_decision": r["predicted_decision"], "correct": ok,
                     "case_family": g["case_family"], "architecture_group": g["architecture_group"], "independent_challenge": g["independent_challenge"],
                     "false_approval": r["predicted_decision"] == "APPROVE" and g["expected_decision"] != "APPROVE",
                     "manual_review_predicted": r.get("manual_review_required", r["predicted_decision"] == "ESCALATE"), "manual_touch_expected": g["manual_touch_required"],
                     "expected_missing_fields": g["missing_fields"], "predicted_missing_fields": r.get("missing_fields", [])})
    n, ok = len(rows), sum(x["correct"] for x in rows)
    nonap = [x for x in rows if x["expected_decision"] != "APPROVE"]
    fa = sum(x["false_approval"] for x in nonap)
    mi = [x for x in rows if x["expected_decision"] == "REQUEST_INFORMATION" and x["expected_missing_fields"]]
    lat = [r["latency_ms"] for r in recs]
    summary = {"n": n, "correct": ok, "correct_disposition_rate": round(ok / n, 4), "wilson95": wilson(ok, n),
               "false_approvals": fa, "non_approvable": len(nonap), "false_approval_rate": round(fa / len(nonap), 4) if nonap else None,
               "human_review_rate": round(sum(x["manual_review_predicted"] for x in rows) / n, 4),
               "over_escalation": sum(x["manual_review_predicted"] and x["expected_decision"] != "ESCALATE" for x in rows),
               "missed_escalation": sum(x["expected_decision"] == "ESCALATE" and x["predicted_decision"] != "ESCALATE" for x in rows),
               "missing_field_exact_match": f"{sum(set(x['predicted_missing_fields']) == set(x['expected_missing_fields']) for x in mi)}/{len(mi)}",
               "by_family": {k: f"{a}/{b}" for k, (a, b) in fam.items()},
               "confusion": {f"{e}->{p}": c for (e, p), c in Counter((x["expected_decision"], x["predicted_decision"]) for x in rows).items()},
               "errors": sum(bool(r.get("error")) for r in recs),
               "median_latency_ms": st.median(lat) if lat else 0, "p95_latency_ms": pct(lat, 0.95),
               "input_tokens": sum(r["input_tokens"] for r in recs), "output_tokens": sum(r["output_tokens"] for r in recs),
               "total_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in recs), "total_cost_usd": round(sum(r["model_cost_usd"] for r in recs), 6)}
    return summary, rows
