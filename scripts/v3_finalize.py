"""V3 holdout, step 4: write the final visible cases (coarse merchant category) and the isolated ground
truth, both under experiments/v3_holdout/, never ExpenseGuard_DATASET/. Mirrors scripts/exp60_finalize.py
exactly, retargeted.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "v3_holdout"
sys.path.insert(0, str(ROOT))

from dataset_generator.semantic import COARSE
from dataset_generator import engine
from scripts.v3_generate_cases import load_tables

drafted = json.loads((HOLDOUT / "cases_drafted.json").read_text())
S = engine.State(load_tables())

visible, gt = [], []
for r in drafted:
    b = dict(r["bill"]); fine_cat = b["merchant_category"]
    ec = {"case_id": r["case_id"], "employee_id": r["employee_id"], "transaction_date": r["transaction_date"],
          "submission_date": r["submission_date"], "bill": b, "form": r["form"], "project_id": r["project_id"],
          "employee_description": r["note"]}
    final_gt = engine.evaluate(ec, S)
    b["merchant_category"] = COARSE.get(fine_cat, "OTHER")
    visible.append({"case_id": r["case_id"], "employee_id": r["employee_id"], "transaction_date": r["transaction_date"],
                     "submission_date": r["submission_date"], "bill": b, "form": {}, "employee_description": r["note"],
                     "project_id": r["project_id"], "split": "V3_HOLDOUT"})
    gt.append({"case_id": r["case_id"], "expected_decision": final_gt["expected_decision"], "reason": final_gt["reason"],
               "archetype": r["archetype"], "touches": r["touches"], "difficulty": r["difficulty"],
               "hidden_form": r["form"], "note_style": r["style"], "note_attempts": r["attempts"], "note_problems": r["problems"]})

(HOLDOUT / "cases.jsonl").write_text("\n".join(json.dumps(v) for v in visible) + "\n")
(HOLDOUT / "ground_truth_private.jsonl").write_text("\n".join(json.dumps(g) for g in gt) + "\n")
print(f"Wrote {len(visible)} visible cases and {len(gt)} ground-truth rows.")
