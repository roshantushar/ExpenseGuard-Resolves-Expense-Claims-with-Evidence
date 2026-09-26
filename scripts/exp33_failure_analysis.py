"""Experiment 33: failure analysis of the final test. One primary category per incorrect prediction (plan taxonomy). Categories for the primary system are assigned
by rule from the case family, expected and predicted decisions (and inspected by hand in docs/exp33); categories for the baselines use the same rule and are heuristic
(arithmetic and retrieval errors of the LLM baselines are not separately diagnosed). Ground truth is joined after the run."""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config as C, evaluate, flags, llm, llm_exp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = C.RESULTS / "final" / "exp32"
gt = evaluate.load_gt()
cases = {c["case_id"]: c for c in llm_exp.cases_for("FINAL_TEST")}
CATS = ["RETRIEVAL_MISS", "RETRIEVAL_DISTRACTOR", "WRONG_POLICY_VERSION", "POLICY_PRECEDENCE_ERROR", "REASONING_ERROR", "ARITHMETIC_ERROR", "MISSING_FIELD_ERROR", "DUPLICATE_FALSE_POSITIVE",
        "DUPLICATE_FALSE_NEGATIVE", "SPLIT_TRANSACTION_MISS", "WRONG_TOOL", "TOOL_ARGUMENT_ERROR", "TOOL_RESULT_MISREAD", "LOOP", "PREMATURE_STOP", "FAILED_TO_ESCALATE", "OVER_ESCALATION", "PROMPT_INJECTION", "SYSTEM_ERROR"]


def category(fam, exp, pred, err):
    if err: return "SYSTEM_ERROR"
    if pred is None: return "SYSTEM_ERROR"
    if fam == "SPLIT_TRANSACTION": return "SPLIT_TRANSACTION_MISS"
    if fam == "DUPLICATE_CHECK": return "DUPLICATE_FALSE_POSITIVE" if exp in ("APPROVE",) else "DUPLICATE_FALSE_NEGATIVE"
    if pred == "ESCALATE" and exp != "ESCALATE": return "OVER_ESCALATION"
    if exp == "ESCALATE": return "FAILED_TO_ESCALATE"
    if exp == "REQUEST_INFORMATION": return "MISSING_FIELD_ERROR"
    if fam == "TEMPORAL_POLICY_VERSION": return "WRONG_POLICY_VERSION"
    if fam == "REGIONAL_PRECEDENCE": return "POLICY_PRECEDENCE_ERROR"
    return "REASONING_ERROR"


systems = {"router (frozen system)": "router_frozen_system", "rules only": "rules_only", "gpt-4o-mini RAG + code facts": "gpt-4o-mini_RAG_+_code_facts", "llama3.2:3b RAG + code facts": "llama3.2:3b_RAG_+_code_facts"}
out = {}
for name, tag in systems.items():
    pred = {json.loads(l)["case_id"]: json.loads(l) for l in (D / f"predictions_{tag}.jsonl").read_text().splitlines()}
    fails = []
    for cid, p in pred.items():
        g = gt[cid]
        if p["predicted_decision"] != g["expected_decision"]:
            fails.append({"case_id": cid, "family": g["case_family"], "expected": g["expected_decision"], "predicted": p["predicted_decision"], "category": category(g["case_family"], g["expected_decision"], p["predicted_decision"], p.get("error")),
                          "challenge": g["independent_challenge"], "currency_flagged": flags.currency_ambiguous(cases[cid]), "false_approval": p["predicted_decision"] == "APPROVE" and g["expected_decision"] != "APPROVE",
                          "system_reason": (p.get("reason") or p.get("explanation") or "")[:160]})
    out[name] = {"n_failures": len(fails), "categories": dict(Counter(f["category"] for f in fails)), "failures": fails}
    print(f"{name:32s} {len(fails)} failures", dict(Counter(f["category"] for f in fails)))
    llm.log_event(type="experiment_summary", run_id=f"EXP33-{tag}", experiment="EXP33_FAILURE_ANALYSIS", split="FINAL_TEST", model=name, n_failures=len(fails), categories=out[name]["categories"])
o = C.RESULTS / "final" / "exp33"; o.mkdir(parents=True, exist_ok=True)
(o / "failures.json").write_text(json.dumps(out, indent=2))
used = [c for c in CATS if any(c in out[n]["categories"] for n in out)]
fig, ax = plt.subplots(1, 2, figsize=(16, 4.8))
w = 0.2
for j, n in enumerate(out):
    ax[0].bar([i + (j - 1.5) * w for i in range(len(used))], [out[n]["categories"].get(c, 0) for c in used], w, label=n)
ax[0].set_xticks(range(len(used))); ax[0].set_xticklabels([c.replace("_", "\n") for c in used], fontsize=6); ax[0].legend(fontsize=7); ax[0].set_title("Final-test failures by primary category (all 40 cases)")
r = out["router (frozen system)"]["categories"]
ax[1].bar(list(r) or ["none"], list(r.values()) or [0], color="C0"); ax[1].set_title(f"Primary system: {out['router (frozen system)']['n_failures']} failures, all currency-flagged"); ax[1].tick_params(labelsize=7)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp33_final_failures.png", dpi=130)
