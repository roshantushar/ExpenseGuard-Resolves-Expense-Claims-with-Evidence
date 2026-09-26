"""Experiment 29: abstention and escalation behaviour, computed from saved predictions (dev + val, 80 cases; no new model calls).
Definitions: escalated = ESCALATE; abstained = ESCALATE or REQUEST_INFORMATION (the system declined to auto-resolve); auto-resolved = APPROVE or REJECT.
Ground truth is joined after the fact."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, evaluate
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

gt = evaluate.load_gt()
SP = ["development", "validation"]
def load(fn): return {r["case_id"]: r for s in SP for r in (json.loads(l) for l in Path(fn(s)).read_text().splitlines() if l.strip())}
systems = {
    "rules (Exp 2)": load(lambda s: C.RESULTS / s / "exp02" / "predictions.jsonl"),
    "fixed workflow (Exp 18)": load(lambda s: C.RESULTS / s / "exp18" / "predictions.jsonl"),
    "gpt-4o-mini RAG + facts (Exp 12)": load(lambda s: C.RESULTS / s / "exp12_hybrid" / "predictions_openai_gpt-4o-mini.jsonl"),
    "llama3.2:3b RAG + facts (Exp 12)": load(lambda s: C.RESULTS / s / "exp12_hybrid" / "predictions_llama3.2_3b.jsonl"),
    "gpt-4o-mini full policy (Exp 4)": load(lambda s: C.RESULTS / s / "exp04_long_context" / "predictions_openai_gpt-4o-mini.jsonl"),
    "always escalate (control)": {c: {"predicted_decision": "ESCALATE"} for c in gt if gt[c]["split"] != "FINAL_TEST"},
}
out = {}
for name, pred in systems.items():
    ids = [c for c in pred if gt[c]["split"] != "FINAL_TEST"]
    n = len(ids)
    P = lambda c: pred[c]["predicted_decision"]; E = lambda c: gt[c]["expected_decision"]
    esc = [c for c in ids if P(c) == "ESCALATE"]; abst = [c for c in ids if P(c) in ("ESCALATE", "REQUEST_INFORMATION")]; auto = [c for c in ids if P(c) in ("APPROVE", "REJECT")]
    need = [c for c in ids if E(c) in ("ESCALATE", "REQUEST_INFORMATION")]                        # cases that should not be auto-resolved
    auto_err = [c for c in auto if P(c) != E(c)]
    wrong_all = [c for c in ids if P(c) != E(c)]
    out[name] = {"n": n, "escalation_rate": round(len(esc) / n, 3), "abstention_rate": round(len(abst) / n, 3), "auto_resolved": len(auto),
                 "error_rate_among_auto_resolved": f"{len(auto_err)}/{len(auto)}", "abstention_recall_on_cases_needing_review": f"{sum(P(c) in ('ESCALATE','REQUEST_INFORMATION') for c in need)}/{len(need)}",
                 "unnecessary_escalations": f"{sum(E(c) != 'ESCALATE' for c in esc)}/{len(esc)}", "escalation_recall": f"{sum(P(c) == 'ESCALATE' for c in ids if E(c) == 'ESCALATE')}/{sum(E(c) == 'ESCALATE' for c in ids)}",
                 "correct_rate": round(sum(P(c) == E(c) for c in ids) / n, 3), "share_of_all_errors_that_were_abstentions": f"{sum(P(c) in ('ESCALATE','REQUEST_INFORMATION') for c in wrong_all)}/{len(wrong_all)}"}
    print(f"{name:36s}", {k: v for k, v in out[name].items() if k != 'n'})
o = C.RESULTS / "development" / "exp29"; o.mkdir(parents=True, exist_ok=True)
(o / "summary.json").write_text(json.dumps(out, indent=2))
ks = list(out)
fig, ax = plt.subplots(1, 3, figsize=(20, 4.6))
short = [k.replace(" (", "\n(") for k in ks]
ax[0].bar(range(len(ks)), [out[k]["escalation_rate"] for k in ks], color="C3"); ax[0].set_title("Escalation rate (human-review load)")
frac = lambda s: int(s.split("/")[0]) / max(1, int(s.split("/")[1]))
ax[1].bar(range(len(ks)), [frac(out[k]["error_rate_among_auto_resolved"]) for k in ks], color="C1"); ax[1].set_title("Error rate among auto-resolved (APPROVE/REJECT) cases")
ax[2].bar(range(len(ks)), [out[k]["correct_rate"] for k in ks], color="C0"); ax[2].set_title("Correct Disposition Rate")
for a in ax: a.set_xticks(range(len(ks))); a.set_xticklabels(short, fontsize=6); a.set_ylim(0, 1)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp29_abstention.png", dpi=130)
