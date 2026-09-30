"""V2 Experiment 0: dataset integrity and leakage audit. Runs the packaged validator and plots distributions. Audit code: may read ground truth. No model calls."""
from __future__ import annotations
import json, subprocess, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from src import config as C
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

r = subprocess.run([sys.executable, "-m", "dataset_v2.validate"], cwd=ROOT, capture_output=True, text=True)
print(r.stdout[-400:])
rep = json.loads((C.DATA / "06_docs" / "validation_report.json").read_text())
jl = lambda p: [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
gt, cases = jl(C.GROUND_TRUTH / "ground_truth.jsonl"), jl(C.CASES / "all_cases.jsonl")
dist = dict(split=Counter(c["split"] for c in cases), group=Counter(g["architecture_group"] for g in gt), outcome=Counter(g["expected_decision"] for g in gt), family=Counter(g["case_family"] for g in gt),
            currency=Counter(c["bill"]["currency"] for c in cases), year=Counter(c["transaction_date"][:4] for c in cases), cross_doc=sum(g["cross_document"] for g in gt), temporal=sum(g["temporal_amendment_case"] for g in gt),
            n_controlling=Counter(len(g["required_policy_ids"]) for g in gt), n_tools=Counter(len(g["minimum_required_tools"]) for g in gt),
            outcome_by_split={s: Counter(g["expected_decision"] for g in gt if g["split"] == s) for s in ("DEVELOPMENT", "VALIDATION", "FINAL_TEST")})
out = C.RESULTS / "exp00"; out.mkdir(parents=True, exist_ok=True)
(out / "summary.json").write_text(json.dumps(dict(n_checks=rep["n_checks"], n_failed=rep["n_failed"], passed=rep["passed"], distributions=dist), indent=1, default=dict))
fig, ax = plt.subplots(1, 4, figsize=(20, 3.9)); dec = ["APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE"]; sp = list(dist["outcome_by_split"]); bot = [0] * 3
for d in dec:
    v = [dist["outcome_by_split"][s][d] for s in sp]; ax[0].bar(sp, v, bottom=bot, label=d); bot = [a + b for a, b in zip(bot, v)]
ax[0].set_title("Outcome by split"); ax[0].legend(fontsize=7)
ax[1].bar(list(dist["group"]), list(dist["group"].values())); ax[1].set_title("Architecture group"); ax[1].tick_params(labelsize=7)
ax[2].bar([str(k) for k in sorted(dist["n_controlling"])], [dist["n_controlling"][k] for k in sorted(dist["n_controlling"])]); ax[2].set_title("Controlling clauses per case")
ax[3].bar([str(k) for k in sorted(dist["n_tools"])], [dist["n_tools"][k] for k in sorted(dist["n_tools"])]); ax[3].set_title("Minimum tools per case")
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp00_dataset_distributions.png", dpi=130)
print(dict(n_checks=rep["n_checks"], failed=rep["n_failed"], cross_doc=dist["cross_doc"], temporal=dist["temporal"]))
