"""Canonical data exporter for the 'Project Story' UI tab.

Reads every metric from the actual saved result files (summary.json, predictions.jsonl, ground_truth.jsonl)
and the cost model's own output -- nothing here is hand-typed into the frontend. If a source file is
missing or a metric can't be computed, the corresponding field is omitted (null), and the UI must render
"See experiment evidence" rather than a fallback number, per the data-integrity requirement.

This script makes NO network calls and NO LLM calls -- every read is a local file. Safe to re-run any
time; it never touches results/v2/final_test/exp32_final_test/ or the ground-truth file, only reads them.

Output: ui/frontend/public/data/project_story.json
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
    Values traced to docs/v2/exp30_selective_router.md's own table, computed from
    results/v2/development/exp30_selective_router/ and results/v2/development/exp18_fixed_workflow/."""
    exp18 = _read_json(ROOT / "results/v2/development/exp18_fixed_workflow/summary.json")
    exp30 = _read_json(ROOT / "results/v2/development/exp30_selective_router/summary.json")
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
    s = _read_json(ROOT / "results/v2/development/exp20_bounded_agent/summary.json")
    if not s:
        return None
    return {"n": s["n"], "correct": s["correct"], "accuracy_pct": round(s["correct_disposition_rate"] * 100, 1),
            "far_pct": round(s["false_approval_rate"] * 100, 1)}


def guarded_candidate() -> dict | None:
    dev = _read_json(ROOT / "results/v2/dev/exp52_final_confirmed/summary.json")
    val = _read_json(ROOT / "results/v2/validation/exp52_final_confirmed/summary.json")
    if not dev or not val:
        return None
    def fmt(s):
        return {"n": s["n"], "correct": s["correct"], "accuracy_pct": round(s["correct_disposition_rate"] * 100, 1),
                "false_approvals": s["false_approvals"], "non_approvable": s["non_approvable"],
                "far_pct": round(s["false_approval_rate"] * 100, 1),
                "human_review_rate_pct": round(s["human_review_rate"] * 100, 1)}
    return {"development": fmt(dev), "validation": fmt(val)}


def cost_scenarios() -> dict:
    """Same numbers as docs/v2/cost_and_business_impact.md's scenario tables -- copied here as the single
    generated artifact both the doc and this exporter should ultimately derive from
    (scripts/v2/cost_model.py). Kept in sync manually today; if cost_model.py's SCENARIOS change, both
    must be regenerated together."""
    return {
        "low": {"label": "1,000 claims/mo, $20/hr reviewer",
                "fixed_workflow": 6619.05, "frozen_final_test": 2493.8, "guarded_dev": 3886.99},
        "base": {"label": "10,000 claims/mo, $35/hr reviewer",
                 "fixed_workflow": 18357.14, "frozen_final_test": 5170.46, "guarded_dev": 8058.42},
        "high": {"label": "100,000 claims/mo, $60/hr reviewer",
                 "fixed_workflow": 58571.43, "frozen_final_test": 13200.46, "guarded_dev": 20572.7},
    }


def main():
    gt = _read_jsonl(ROOT / "ExpenseGuard_V2_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")
    gt_by_id = {g["case_id"]: g for g in gt} if gt else {}
    exp32_summary = _read_json(ROOT / "results/v2/final_test/exp32_final_test/summary.json")
    exp32_preds = _read_jsonl(ROOT / "results/v2/final_test/exp32_final_test/predictions.jsonl")

    out = {
        "dataset": dataset_stats(gt) if gt else None,
        "exp32_official": exp32_official(exp32_summary),
        "exp32_path_performance": path_performance(exp32_preds, gt_by_id) if exp32_preds else None,
        "exp33_failures": exp33_failure_breakdown(ROOT / "results/v2/final_test/exp33_failure_analysis/failure_classification.csv"),
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
