"""Experiment 0: dataset integrity and leakage audit. Writes results/exp00_dataset_validation.json
and results/plots/exp00_*.png. Audit code, so it is allowed to read the private ground truth."""
from __future__ import annotations
import csv, json, subprocess, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def rows(name):
    return list(csv.DictReader(open(C.ENTERPRISE / name, encoding="utf-8")))


checks = []  # (name, passed, detail)


def check(name, ok, detail=""):
    checks.append({"check": name, "passed": bool(ok), "detail": detail})


cases = jl(C.CASES / "all_cases.jsonl")
gt = jl(C.GROUND_TRUTH / "ground_truth.jsonl")
gt_by = {g["case_id"]: g for g in gt}
meta = json.loads((C.POLICY / "policy_metadata.json").read_text(encoding="utf-8"))
clauses = {c for d in meta for c in d["clause_ids"]}

# 1-3 ids, splits, architecture
check("unique case ids", len({c["case_id"] for c in cases}) == 120)
check("cases and ground truth cover same ids", {c["case_id"] for c in cases} == set(gt_by))
check("split 60/20/40", Counter(c["split"] for c in cases) == Counter(DEVELOPMENT=60, VALIDATION=20, FINAL_TEST=40))
check("split files match all_cases", all(
    {c["case_id"] for c in jl(C.CASES / f)} == {c["case_id"] for c in cases if c["split"] == s}
    for f, s in [("development.jsonl", "DEVELOPMENT"), ("validation.jsonl", "VALIDATION"), ("final_test.jsonl", "FINAL_TEST")]))
check("case split == ground-truth split", all(c["split"] == gt_by[c["case_id"]]["split"] for c in cases))
check("architecture 65/40/15", Counter(g["architecture_group"] for g in gt) == Counter(A_SELF_CONTAINED=65, B_WORKFLOW=40, C_AGENT_DYNAMIC=15))
ch = [g for g in gt if g["independent_challenge"]]
check("10 challenge cases, all in final test", len(ch) == 10 and all(g["split"] == "FINAL_TEST" for g in ch))
check("csv export matches jsonl", {r["case_id"] for r in csv.DictReader(open(C.CASES / "all_cases.csv", encoding="utf-8"))} == set(gt_by))

# 4 policy ids
bad = [(g["case_id"], p) for g in gt for p in g["required_policy_ids"] + ([g["triggered_policy_id"]] if g["triggered_policy_id"] else []) if p not in clauses]
check("all required/triggered policy ids exist in corpus", not bad, str(bad[:5]))
sd = [d["doc_id"] for d in meta if not d.get("effective_from")]
check("every policy doc has effective_from", not sd, str(sd))

# 5 enterprise references
emp = {r["employee_id"] for r in rows("employees.csv")}
proj = {r["project_id"] for r in rows("project_registry.csv")}
trav, appr, exc, conf, prev = rows("travel_requests.csv"), rows("manager_approvals.csv"), rows("policy_exceptions.csv"), rows("conference_registry.csv"), rows("previous_expenses.csv")
events = {r["event_id"] for r in conf}
excs = {r["exception_id"] for r in exc}
prev_ids = {r["expense_id"] for r in prev}
bad = [c["case_id"] for c in cases if c["employee_id"] not in emp]
check("case employee ids in employees.csv", not bad, str(bad[:5]))
bad = [c["case_id"] for c in cases if c["project_id"] not in proj]
check("case project ids in project_registry.csv", not bad, str(bad[:5]))
check("travel.employee_id valid", all(r["employee_id"] in emp for r in trav))
check("travel.event_id valid", all(not r["event_id"] or r["event_id"] in events for r in trav))
check("travel.exception_id valid", all(not r["exception_id"] or r["exception_id"] in excs for r in trav))
check("project.exception_id valid", all(not r["exception_id"] or r["exception_id"] in excs for r in rows("project_registry.csv")))
check("approval/exception/conference/previous employee ids valid", all(r["employee_id"] in emp for t in (appr, exc, conf, prev) for r in t))
case_ids = set(gt_by)
check("approval/exception expense_id point to real cases", all(r["expense_id"] in case_ids for r in appr + exc if r["expense_id"]))
fx = {(r["year"], r["month"], r["currency"]) for r in rows("fx_rates.csv")}
need = {(c["transaction_date"][:4], str(int(c["transaction_date"][5:7])), c["bill"]["currency"]) for c in cases}
check("FX rate exists for every case year/month/currency", need <= fx, str(sorted(need - fx)[:5]))

# 6-7 duplicate and split links
bad = [(g["case_id"], x) for g in gt for x in g["matched_expense_ids"] + g["related_expense_ids"] if x not in prev_ids and x not in case_ids]
check("duplicate/split links resolve", not bad, str(bad[:5]))
bad = [g["case_id"] for g in gt if g["duplicate_status"] in ("EXACT_DUPLICATE", "POSSIBLE_DUPLICATE", "LEGITIMATE_REPEAT") and not g["matched_expense_ids"]]
check("duplicate cases list matched ids", not bad, str(bad[:5]))
bad = [g["case_id"] for g in gt if g["split_transaction_status"] not in ("NONE", "") and not g["related_expense_ids"]]
check("split cases list related ids", not bad, str(bad[:5]))
badc = []
cm = {c["case_id"]: c for c in cases}
pm = {r["expense_id"]: r for r in prev}
for g in gt:
    if g["combined_amount"] is not None and g["related_expense_ids"] and g["related_expense_ids"][0] in pm:
        cur = cm[g["case_id"]]["bill"]["total"]
        tot = cur + sum(float(pm[x]["amount"]) for x in g["related_expense_ids"] if x in pm)
        if abs(tot - g["combined_amount"]) > 0.01:
            badc.append((g["case_id"], tot, g["combined_amount"]))
check("split combined_amount == current + related (same currency)", not badc, str(badc[:5]))
bad = [g["case_id"] for g in gt if g["architecture_group"] == "C_AGENT_DYNAMIC" and (g["workflow_sufficient"] or not g["branch_trigger"])]
check("agent candidates flagged non-workflow with branch trigger", not bad, str(bad[:5]))
bad = [g["case_id"] for g in gt if g["expected_decision"] == "REQUEST_INFORMATION" and g["case_family"] == "MISSING_INFORMATION" and not g["missing_fields"]]
check("missing-info cases list missing_fields", not bad, str(bad[:5]))

# 9 leakage of private fields into runtime-visible artifacts
gt_keys = {"expected_decision", "required_policy_ids", "architecture_group", "case_family", "acceptable_tool_paths", "duplicate_status",
           "split_transaction_status", "wrong_behaviour_to_catch", "branch_trigger", "independent_challenge", "challenge_source",
           "minimum_required_tools", "agent_required_candidate", "workflow_sufficient", "manual_touch_required"}
check("no ground-truth keys in case files", not any(gt_keys & set(c) or gt_keys & set(c["bill"]) for c in cases))
blob = "\n".join(json.dumps(c) for c in cases)
labels = ["independent_challenge", "agent_required", "DYNAMIC_AGENT", "A_SELF_CONTAINED", "B_WORKFLOW", "wrong_behaviour", "EXPECTED_", "expected_decision"]
check("no label strings in case text", not [l for l in labels if l in blob], str([l for l in labels if l in blob]))
policy_txt = "\n".join(p.read_text(encoding="utf-8") for p in (C.POLICY / "source_documents").glob("*.md")) + json.dumps(meta)
hit = [l for l in labels + ["EXP-0"] if l in policy_txt]
check("no labels or case ids in policy docs/metadata", not hit, str(hit))
ent_txt = "\n".join(p.read_text(encoding="utf-8") for p in C.ENTERPRISE.glob("*.csv"))
hit = [l for l in labels if l in ent_txt]
check("no labels in enterprise tables", not hit, str(hit))
strs = {g["reason"] for g in gt if g["reason"]} | {g["wrong_behaviour_to_catch"] for g in gt if g["wrong_behaviour_to_catch"]}
hit = [s[:40] for s in strs if s in blob or s in policy_txt or s in ent_txt]
check("ground-truth reasons absent from visible data", not hit, str(hit[:3]))
# case ids inside enterprise tables (join keys) are expected for approvals/exceptions; flag anything else
tables_with_case_ids = [n.name for n in C.ENTERPRISE.glob("*.csv") if "EXP-0" in n.read_text(encoding="utf-8")]
check("case ids appear only in approvals/exceptions/(history) tables", set(tables_with_case_ids) <= {"manager_approvals.csv", "policy_exceptions.csv", "previous_expenses.csv"}, str(tables_with_case_ids))

# 10 packaged validator
r = subprocess.run([sys.executable, str(C.DATA / "05_generation" / "validate_dataset.py")], capture_output=True, text=True, env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
check("packaged validate_dataset.py passes", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:])

failed = [c for c in checks if not c["passed"]]
summary = {"experiment": "EXP00_DATASET_VALIDATION", "n_checks": len(checks), "n_failed": len(failed), "passed": not failed,
           "checks": checks,
           "distributions": {
               "split": Counter(c["split"] for c in cases), "architecture": Counter(g["architecture_group"] for g in gt),
               "decision_by_split": {s: Counter(g["expected_decision"] for g in gt if g["split"] == s) for s in ("DEVELOPMENT", "VALIDATION", "FINAL_TEST")},
               "family": Counter(g["case_family"] for g in gt), "currency": Counter(c["bill"]["currency"] for c in cases),
               "year": Counter(c["transaction_date"][:4] for c in cases)}}
(C.RESULTS / "exp00_dataset_validation.json").write_text(json.dumps(summary, indent=2, default=dict))

# plots
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
d = summary["distributions"]
sp = ["DEVELOPMENT", "VALIDATION", "FINAL_TEST"]
decs = ["APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE"]
bottom = [0] * 3
for dc in decs:
    v = [d["decision_by_split"][s].get(dc, 0) for s in sp]
    ax[0].bar(sp, v, bottom=bottom, label=dc); bottom = [a + b for a, b in zip(bottom, v)]
ax[0].set_title("Expected decision by split"); ax[0].legend(fontsize=7)
fam = sorted(d["family"].items(), key=lambda x: x[1])
ax[1].barh([f for f, _ in fam], [n for _, n in fam]); ax[1].set_title("Cases per family"); ax[1].tick_params(labelsize=7)
ax[2].bar(list(d["architecture"]), list(d["architecture"].values())); ax[2].set_title("Architecture group"); ax[2].tick_params(labelsize=7)
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp00_dataset_distributions.png", dpi=130)

for c in checks:
    print(("PASS " if c["passed"] else "FAIL ") + c["check"] + ("" if c["passed"] else f"  -> {c['detail']}"))
print(f"\n{len(checks)-len(failed)}/{len(checks)} checks passed")
sys.exit(1 if failed else 0)
