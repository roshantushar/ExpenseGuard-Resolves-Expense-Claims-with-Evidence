"""Corrected Exp 60 accounting: same 50 cases, same frozen resolver, candidate now includes the
require-category-tool gate (scripts/exp60_require_tool_gate.py). Also applies the one clearly-labeled
ground-truth correction (X3-049, CONFERENCE_FEE type-list gap in the test-generation reference tool --
see docs/exp60_fresh_holdout.md's correction note). Cases, enterprise data, and the frozen resolver are
byte-identical to the original Exp 60 run. Accepts --model to run the candidate with a different model
(e.g. openai/gpt-4o) as a separate, clearly-labeled comparison -- not a silent replacement of the
gpt-4o-mini result already reported.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "exp60_holdout"
sys.path.insert(0, str(ROOT))

from src import config as C
C.ENTERPRISE = HOLDOUT / "enterprise_data"

from src import resolver as R, evaluate as EV
from scripts.exp60_require_tool_gate import run_candidate
from scripts.exp59_final_fix import deterministic_fixed
from scripts.exp60_run_comparison import load_cases, load_gt, patch_evaluate_load_gt

GT_CORRECTION = {"X3-049": "APPROVE"}  # rules_v2.TYPES treats TRAINING approval as valid for CONFERENCE_FEE; engine.py's own generic type list omits the category entirely -- not a confirmed system failure


def main(model: str | None = None, run_frozen: bool = True):
    cases = load_cases()
    gt = load_gt()
    for cid, correction in GT_CORRECTION.items():
        gt[cid]["expected_decision"] = correction
    patch_evaluate_load_gt(gt)

    frozen, candidate = {}, {}
    for i, c in enumerate(cases, 1):
        cid = c["case_id"]
        if run_frozen:
            d, conclusive = R.deterministic(c)
            frozen[cid] = d["decision"] if conclusive else R.resolve_batch([c])[cid]["decision"]
        d2, conclusive2 = deterministic_fixed(c)
        candidate[cid] = d2["decision"] if conclusive2 else run_candidate(c, model=model, tag="EXP60_CANDIDATE_MODEL")["decision"]
        frozen_s = frozen.get(cid, "(skipped)")
        tag = "  <-- DIFFER" if run_frozen and frozen[cid] != candidate[cid] else ""
        print(f"[{i}/{len(cases)}] {cid:8s} gt={gt[cid]['expected_decision']:20s} frozen={frozen_s:20s} candidate={candidate[cid]:20s}{tag}")

    def metrics(d):
        correct = sum(1 for c in cases if d[c["case_id"]] == gt[c["case_id"]]["expected_decision"])
        approve_ids = [c["case_id"] for c in cases if gt[c["case_id"]]["expected_decision"] == "APPROVE"]
        ah = sum(1 for cid in approve_ids if d[cid] == "APPROVE")
        non_ids = [c["case_id"] for c in cases if gt[c["case_id"]]["expected_decision"] != "APPROVE"]
        fa = sum(1 for cid in non_ids if d[cid] == "APPROVE")
        return dict(correct=correct, n=len(cases), approve_hits=ah, approve_total=len(approve_ids), false_approvals=fa, non_approvable=len(non_ids))

    if run_frozen:
        fm = metrics(frozen)
        print(f"\nFROZEN: accuracy {fm['correct']}/{fm['n']}, APPROVE recall {fm['approve_hits']}/{fm['approve_total']}, false approvals {fm['false_approvals']}/{fm['non_approvable']}")
    cm = metrics(candidate)
    print(f"CANDIDATE (model={model or 'default'}): accuracy {cm['correct']}/{cm['n']}, APPROVE recall {cm['approve_hits']}/{cm['approve_total']}, false approvals {cm['false_approvals']}/{cm['non_approvable']}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=None)
    p.add_argument("--skip-frozen", action="store_true")
    a = p.parse_args()
    main(model=a.model, run_frozen=not a.skip_frozen)
