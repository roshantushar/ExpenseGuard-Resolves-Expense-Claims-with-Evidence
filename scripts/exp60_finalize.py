"""Exp 60 step 4: write the final visible cases (coarse merchant category, matching the original dataset's
own convention -- the resolver/agent never sees the fine-grained category, only the merchant directory
lookup does) and the isolated ground truth, both under experiments/exp60_holdout/, never ExpenseGuard_DATASET/.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "exp60_holdout"
sys.path.insert(0, str(ROOT))

from dataset_generator.semantic import COARSE
from dataset_generator import engine
from scripts.exp60_generate_cases import load_tables

drafted = json.loads((HOLDOUT / "cases_drafted.json").read_text())
S = engine.State(load_tables())

visible, gt = [], []
for r in drafted:
    b = dict(r["bill"]); fine_cat = b["merchant_category"]
    # Ground truth re-derived against the FINAL drafted note (fine-grained category, matching how
    # process() itself re-verified during drafting) -- not the earlier neutral-placeholder pass.
    ec = {"case_id": r["case_id"], "employee_id": r["employee_id"], "transaction_date": r["transaction_date"],
          "submission_date": r["submission_date"], "bill": b, "form": r["form"], "project_id": r["project_id"],
          "employee_description": r["note"]}
    final_gt = engine.evaluate(ec, S)
    b["merchant_category"] = COARSE.get(fine_cat, "OTHER")
    visible.append({"case_id": r["case_id"], "employee_id": r["employee_id"], "transaction_date": r["transaction_date"],
                     "submission_date": r["submission_date"], "bill": b, "form": {}, "employee_description": r["note"],
                     "project_id": r["project_id"], "split": "EXP60_HOLDOUT"})
    gt.append({"case_id": r["case_id"], "expected_decision": final_gt["expected_decision"], "reason": final_gt["reason"],
               "archetype": r["archetype"], "touches": r["touches"], "difficulty": r["difficulty"],
               "hidden_form": r["form"], "note_style": r["style"], "note_attempts": r["attempts"], "note_problems": r["problems"]})

(HOLDOUT / "cases.jsonl").write_text("\n".join(json.dumps(v) for v in visible) + "\n")
(HOLDOUT / "ground_truth_private.jsonl").write_text("\n".join(json.dumps(g) for g in gt) + "\n")
print(f"Wrote {len(visible)} visible cases and {len(gt)} ground-truth rows.")
