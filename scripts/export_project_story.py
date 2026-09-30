"""Canonical data exporter for the 'Project Story' UI tab.

Reads every metric from the actual saved result files (summary.json, predictions.jsonl, ground_truth.jsonl)
and the cost model's own output -- nothing here is hand-typed into the frontend. If a source file is
missing or a metric can't be computed, the corresponding field is omitted (null), and the UI must render
"See experiment evidence" rather than a fallback number, per the data-integrity requirement.

This script makes NO network calls and NO LLM calls -- every read is a local file. Safe to re-run any
time; it never touches results/current/final_test/exp32_final_test/ or the ground-truth file, only reads them.

Output: ui/frontend/public/data/project_story.json
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _read_jsonl(path: Path):
    if not path.exists():
        return None
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def dataset_stats(gt: list) -> dict:
    return {
        "total": len(gt),
        "development": sum(1 for g in gt if g["split"] == "DEVELOPMENT"),
        "validation": sum(1 for g in gt if g["split"] == "VALIDATION"),
        "final_test": sum(1 for g in gt if g["split"] == "FINAL_TEST"),
    }


def exp32_official(summary: dict | None) -> dict | None:
    if not summary:
        return None
    return {
        "n": summary["n"], "correct": summary["correct"],
        "accuracy_pct": round(summary["correct_disposition_rate"] * 100, 1),
        "false_approvals": summary["false_approvals"], "non_approvable": summary["non_approvable"],
        "far_pct": round(summary["false_approval_rate"] * 100, 1),
        "human_review_rate_pct": round(summary["human_review_rate"] * 100, 1),
    }


def path_performance(preds: list | None, gt_by_id: dict) -> dict | None:
    if not preds:
        return None
    det = [p for p in preds if p.get("path") == "deterministic"]
    res = [p for p in preds if p.get("path") == "llm_residual"]
    def acc(rows):
        if not rows:
            return None
        correct = sum(1 for r in rows if r["predicted_decision"] == gt_by_id[r["case_id"]]["expected_decision"])
        return {"correct": correct, "n": len(rows)}
    approve_truth = [r for r in preds if gt_by_id[r["case_id"]]["expected_decision"] == "APPROVE"]
    approve_recall = None
    if approve_truth:
        hit = sum(1 for r in approve_truth if r["predicted_decision"] == "APPROVE")
        approve_recall = {"correct": hit, "n": len(approve_truth)}
    return {"deterministic": acc(det), "llm_residual": acc(res), "approve_recall": approve_recall}


def exp33_failure_breakdown(csv_path: Path) -> dict | None:
    if not csv_path.exists():
        return None
    import csv as csv_mod
    rows = list(csv_mod.DictReader(csv_path.open()))
    from collections import Counter
    cats = Counter(r["primary_category"] for r in rows)
    return {"total_errors": len(rows), "categories": dict(cats)}


def exp18_vs_exp30_vs_llm_only() -> dict:
    """The three-way comparison from Exp 30's own doc (LLM-for-all / fixed workflow / selective).
    Values traced to docs/exp30_selective_router.md's own table, computed from
    results/current/development/exp30_selective_router/ and results/current/development/exp18_fixed_workflow/."""
    exp18 = _read_json(ROOT / "results/current/development/exp18_fixed_workflow/summary.json")
    exp30 = _read_json(ROOT / "results/current/development/exp30_selective_router/summary.json")
    out = {}
    if exp18:
        out["fixed_workflow"] = {"n": exp18["n"], "correct": exp18["correct"],
                                  "accuracy_pct": round(exp18["correct_disposition_rate"] * 100, 1),
                                  "far_pct": round(exp18["false_approval_rate"] * 100, 1)}
    if exp30:
        out["selective_resolver"] = {"n": exp30["n"], "correct": exp30["correct"],
                                      "accuracy_pct": round(exp30["correct_disposition_rate"] * 100, 1),
                                      "far_pct": round(exp30["false_approval_rate"] * 100, 1)}
    return out


def agent_hard_subset() -> dict | None:
    """Exp 20's bounded-agent pilot on the 13-case C_AGENT_DYNAMIC dev subset."""
    s = _read_json(ROOT / "results/current/development/exp20_bounded_agent/summary.json")
    if not s:
        return None
    return {"n": s["n"], "correct": s["correct"], "accuracy_pct": round(s["correct_disposition_rate"] * 100, 1),
            "far_pct": round(s["false_approval_rate"] * 100, 1)}


def guarded_candidate() -> dict | None:
    dev = _read_json(ROOT / "results/current/dev/exp52_final_confirmed/summary.json")
    val = _read_json(ROOT / "results/current/validation/exp52_final_confirmed/summary.json")
    if not dev or not val:
        return None
    def fmt(s):
        return {"n": s["n"], "correct": s["correct"], "accuracy_pct": round(s["correct_disposition_rate"] * 100, 1),
                "false_approvals": s["false_approvals"], "non_approvable": s["non_approvable"],
                "far_pct": round(s["false_approval_rate"] * 100, 1),
                "human_review_rate_pct": round(s["human_review_rate"] * 100, 1)}
    return {"development": fmt(dev), "validation": fmt(val)}


def cost_scenarios() -> dict:
    """Computed live from scripts/cost_model.py -- the actual source of truth -- instead of a
    hand-copied duplicate (a prior version of this function hardcoded a copy of cost_model.py's output,
    which silently went stale when cost_model.py's cost total was corrected to include false-rejection
    and unnecessary-info-request costs)."""
    import importlib.util as ilu, sys
    spec = ilu.spec_from_file_location("cost_model", ROOT / "scripts/cost_model.py")
    cost_model = ilu.module_from_spec(spec)
    sys.modules["cost_model"] = cost_model  # dataclasses needs the module registered to resolve its own annotations
    spec.loader.exec_module(cost_model)
    measured, ai_cost_per_claim = cost_model.measured_and_costs()
    key = {"fixed_workflow": "Fixed workflow (Exp 18) — dev",
           "frozen_final_test": "Official frozen selective resolver (Exp 32) — final test",
           "guarded_dev": "Guarded-agent candidate (Exp 52) — dev"}
    labels = {"low": "1,000 claims/mo, $20/hr reviewer", "base": "10,000 claims/mo, $35/hr reviewer",
              "high": "100,000 claims/mo, $60/hr reviewer"}
    out = {}
    for scen_name, a in cost_model.SCENARIOS.items():
        row = {"label": labels[scen_name]}
        for short_name, full_name in key.items():
            row[short_name] = cost_model.cost_per_1000(measured[full_name], ai_cost_per_claim[full_name], a)["total_expected_cost_usd"]
        out[scen_name] = row
    return out


def main():
    gt = _read_jsonl(ROOT / "ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")
    gt_by_id = {g["case_id"]: g for g in gt} if gt else {}
    exp32_summary = _read_json(ROOT / "results/current/final_test/exp32_final_test/summary.json")
    exp32_preds = _read_jsonl(ROOT / "results/current/final_test/exp32_final_test/predictions.jsonl")

    out = {
        "dataset": dataset_stats(gt) if gt else None,
        "exp32_official": exp32_official(exp32_summary),
        "exp32_path_performance": path_performance(exp32_preds, gt_by_id) if exp32_preds else None,
        "exp33_failures": exp33_failure_breakdown(ROOT / "results/current/final_test/exp33_failure_analysis/failure_classification.csv"),
        "architecture_comparison": exp18_vs_exp30_vs_llm_only(),
        "agent_hard_subset": agent_hard_subset(),
        "guarded_candidate": guarded_candidate(),
        "cost_scenarios": cost_scenarios(),
    }

    out_path = ROOT / "ui/frontend/public/data/project_story.json"
    out_path.write_text(json.dumps(out, indent=1))
    print(f"wrote {out_path}")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
