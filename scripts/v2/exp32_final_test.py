"""Exp 32: the frozen final test. Runs the frozen src/resolver.py once over all 50 final-test claims, saves the full
prediction trace, then evaluates. Per the freeze manifest (experiments/exp32_freeze_manifest_v2.yaml): no case is
inspected or rerun individually mid-run; the full batch completes, predictions are written to disk exactly as
produced, and only then does any analysis happen. This script performs no mid-run branching on results and prints
nothing about individual cases before the batch is complete and saved.

Usage: python -m scripts.v2.exp32_final_test
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src import config as C, llm, llm_exp, resolver, evaluate

EXP = "EXP32_FINAL_TEST"


def main():
    t0 = time.time()
    cases = llm_exp.cases_for("FINAL_TEST")
    assert len(cases) == 50, f"expected 50 final-test claims, found {len(cases)}"
    spent_before = llm.spent()

    out = resolver.resolve_batch(cases)  # the one and only call into the frozen pipeline; no per-case inspection here

    recs = [{"case_id": cid, "predicted_decision": r["decision"], "policy_evidence": r.get("policy_evidence", []), "missing_fields": r.get("missing_fields", []),
             "manual_review_required": r["decision"] == "ESCALATE", "path": r["path"], "latency_ms": r.get("latency_ms", 0), "input_tokens": r.get("input_tokens", 0),
             "output_tokens": r.get("output_tokens", 0), "model_cost_usd": r.get("model_cost_usd", 0.0), "error": r.get("error")} for cid, r in out.items()]

    out_dir = C.RESULTS / "final_test" / "exp32_final_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "predictions.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")  # locked: written before any evaluation happens

    gt = evaluate.load_gt()  # evaluator opens ground truth only now, after predictions are locked to disk
    summary, rows = evaluate.evaluate(recs, gt)
    (out_dir / "evaluation.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (out_dir / "summary.json").write_text(json.dumps({**summary, "wall_clock_s": round(time.time() - t0, 1), "spend_this_run_usd": round(llm.spent() - spent_before, 6)}, indent=1, default=str))

    print(f"Exp 32 complete: {summary['correct']}/{summary['n']} | spend this run ${llm.spent() - spent_before:.4f} | wall clock {time.time() - t0:.1f}s")
    print("Predictions locked to", out_dir / "predictions.jsonl")


if __name__ == "__main__":
    main()
