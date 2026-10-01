"""Exp 60 step 2: add each case's supporting enterprise rows to the ISOLATED copy, compute independent
ground truth via dataset_generator.engine.evaluate(), draft notes via dataset_generator.semantic (real
paid calls, gpt-4o-mini), re-verify with the drafted note substituted in, and write the outputs -- all
under experiments/exp60_holdout/, never ExpenseGuard_DATASET/.
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "exp60_holdout"
sys.path.insert(0, str(ROOT))

from scripts.exp60_generate_cases import CASES, ENTERPRISE, append_row, load_tables, NEUTRAL_DESC
from dataset_generator import engine, semantic as SEM
from dataset_generator import world as W
SEM.CACHE = HOLDOUT / "semantic_cache.json"


def build_engine_case(spec, description):
    return {
        "case_id": spec["case_id"], "employee_id": spec["employee_id"], "transaction_date": spec["transaction_date"],
        "submission_date": spec["submission_date"], "bill": spec["bill"], "form": spec["form"],
        "employee_description": description, "project_id": spec["project_id"],
    }


def main():
    print("Adding enterprise rows to the isolated copy...")
    added = 0
    for spec in CASES:
        for table, row in spec["new_rows"]:
            append_row(table, row); added += 1
    print(f"Added {added} rows across {len({t for s in CASES for t,_ in s['new_rows']})} tables.")

    print("\nLoading isolated tables for the independent engine.State...")
    S = engine.State(load_tables())

    print("\n--- Pass 1: ground truth with a neutral placeholder description ---")
    results = []
    errors = []
    for spec in CASES:
        ec = build_engine_case(spec, spec.get("note_override") or NEUTRAL_DESC)
        try:
            gt = engine.evaluate(ec, S)
        except Exception as e:  # noqa
            errors.append((spec["case_id"], repr(e)[:200])); continue
        results.append((spec, gt))

    if errors:
        print(f"\n{len(errors)} cases failed to evaluate -- STOPPING before any model call:")
        for cid, err in errors:
            print(f"  {cid}: {err}")
        return

    print(f"All {len(results)} cases evaluated successfully with the independent engine.")
    from collections import Counter
    dist = Counter(gt["expected_decision"] for _, gt in results)
    print("Decision distribution (pre-note):", dict(dist))

    out_path = HOLDOUT / "cases_pass1_preview.json"
    out_path.write_text(json.dumps([{"case_id": s["case_id"], "archetype": s["archetype"], "touches": s["touches"], "difficulty": s["difficulty"],
                                      "expected_decision": gt["expected_decision"], "reason": gt["reason"], "missing_fields": gt["missing_fields"]}
                                     for s, gt in results], indent=1))
    print(f"\nWrote pass-1 preview (no notes drafted, no model calls made) to {out_path}")
    print("Review this before drafting any notes.")


if __name__ == "__main__":
    main()
