"""Exp 60 step 5 (the actual result): frozen resolver vs. the Exp 59 candidate, both run ONCE against the
same 50 fresh, never-before-seen cases (experiments/exp60_holdout/), reported together. Ground truth is
read only here, by this evaluation script -- never by resolver.py, agent.py, or any runtime code (same
discipline tests/test_no_leakage.py enforces for the real dataset). config.ENTERPRISE is redirected to the
isolated copy before anything else runs.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "exp60_holdout"
sys.path.insert(0, str(ROOT))

from src import config as C
C.ENTERPRISE = HOLDOUT / "enterprise_data"  # redirect BEFORE importing anything that reads tables

from src import resolver as R, evaluate as EV
from scripts.exp59_final_fix import deterministic_fixed, run_one_v59


def load_cases():
    return [json.loads(l) for l in (HOLDOUT / "cases.jsonl").read_text().splitlines() if l.strip()]


def load_gt():
    return {r["case_id"]: r for r in (json.loads(l) for l in (HOLDOUT / "ground_truth_private.jsonl").read_text().splitlines() if l.strip())}


def patch_evaluate_load_gt(gt):
    """resolver.resolve_batch()'s internal llm_exp.run() self-evaluates against the OFFICIAL ground truth
    file -- a leakage-safety feature (it's the evaluator, allowed to read it), not something built to take
    a custom case set. Redirects evaluate.load_gt() to also serve the Exp 60 cases, with the extra fields
    evaluate.evaluate() expects filled with neutral defaults (not used for anything in this script)."""
    def patched():
        out = {}
        for cid, g in gt.items():
            out[cid] = {**g, "case_family": g["archetype"], "architecture_group": "EXP60_HOLDOUT", "independent_challenge": False,
                        "manual_touch_required": g["expected_decision"] == "ESCALATE", "missing_fields": []}
        return out
    EV.load_gt = patched


def main():
    assert "exp60_holdout" in str(C.ENTERPRISE), "REDIRECTION FAILED"
    cases = load_cases()
    gt = load_gt()
    patch_evaluate_load_gt(gt)
    print(f"{len(cases)} cases loaded, config.ENTERPRISE = {C.ENTERPRISE}")

    frozen, candidate = {}, {}
    for i, c in enumerate(cases, 1):
        cid = c["case_id"]
        # -- frozen resolver (official, unmodified) --
        d, conclusive = R.deterministic(c)
        if conclusive:
            frozen[cid] = d["decision"]
        else:
            out = R.resolve_batch([c])
            frozen[cid] = out[cid]["decision"]

        # -- Exp 59 candidate --
        d2, conclusive2 = deterministic_fixed(c)
        if conclusive2:
            candidate[cid] = d2["decision"]
        else:
            candidate[cid] = run_one_v59(c, "EXP60_CANDIDATE")["decision"]

        print(f"[{i}/{len(cases)}] {cid:8s} gt={gt[cid]['expected_decision']:20s} frozen={frozen[cid]:20s} candidate={candidate[cid]:20s}"
              + ("  <-- DIFFER" if frozen[cid] != candidate[cid] else ""))

    def metrics(d):
        correct = sum(1 for c in cases if d[c["case_id"]] == gt[c["case_id"]]["expected_decision"])
        approve_ids = [c["case_id"] for c in cases if gt[c["case_id"]]["expected_decision"] == "APPROVE"]
        ah = sum(1 for cid in approve_ids if d[cid] == "APPROVE")
        non_ids = [c["case_id"] for c in cases if gt[c["case_id"]]["expected_decision"] != "APPROVE"]
        fa = sum(1 for cid in non_ids if d[cid] == "APPROVE")
        auto = sum(1 for c in cases if d[c["case_id"]] != "ESCALATE")
        return dict(correct=correct, n=len(cases), approve_hits=ah, approve_total=len(approve_ids),
                    false_approvals=fa, non_approvable=len(non_ids), automated=auto)

    fm, cm = metrics(frozen), metrics(candidate)
    print(f"\nFROZEN RESOLVER (official, unmodified): accuracy {fm['correct']}/{fm['n']}, APPROVE recall {fm['approve_hits']}/{fm['approve_total']}, "
          f"false approvals {fm['false_approvals']}/{fm['non_approvable']}, automated (non-ESCALATE) {fm['automated']}/{fm['n']}")
    print(f"EXP 59 CANDIDATE: accuracy {cm['correct']}/{cm['n']}, APPROVE recall {cm['approve_hits']}/{cm['approve_total']}, "
          f"false approvals {cm['false_approvals']}/{cm['non_approvable']}, automated (non-ESCALATE) {cm['automated']}/{cm['n']}")

    (HOLDOUT / "comparison_result.json").write_text(json.dumps({"frozen": frozen, "candidate": candidate, "frozen_metrics": fm, "candidate_metrics": cm}, indent=1))
    print(f"\nWrote {HOLDOUT / 'comparison_result.json'}")


if __name__ == "__main__":
    main()
