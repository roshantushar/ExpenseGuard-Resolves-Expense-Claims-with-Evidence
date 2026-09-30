"""ExpenseGuard V2 - strict dataset validator. Reads only the packaged files, rebuilds the enterprise state from the CSVs and re-derives every label with the reference engine.
Usage: python -m dataset_v2.validate"""
from __future__ import annotations
import csv, json, re, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dataset_v2 import engine, world as W

OUT = ROOT / "ExpenseGuard_V2_DATASET"
checks = []


def check(name, ok, detail=""):
    checks.append(dict(check=name, passed=bool(ok), detail=str(detail)[:300]))


def jl(p): return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def load_tables():
    T = {}
    for p in sorted((OUT / "03_enterprise_data").glob("*.csv")):
        with open(p, encoding="utf-8") as f: T[p.stem] = list(csv.DictReader(f))
    for r in T["fx_rates"]: r["year"], r["month"] = int(r["year"]), int(r["month"])
    return T


def main():
    cases, gt = jl(OUT / "02_cases" / "all_cases.jsonl"), jl(OUT / "04_ground_truth_PRIVATE" / "ground_truth.jsonl")
    gb = {g["case_id"]: g for g in gt}
    T = load_tables(); meta = json.loads((OUT / "01_policy_corpus" / "policy_metadata.json").read_text())
    clauses = {c for d in meta for c in d["clause_ids"]}
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in sorted((OUT / "01_policy_corpus" / "source_documents").glob("*.md")))
    # ---- shape
    ids = [c["case_id"] for c in cases]
    check("150 unique case ids", len(ids) == 150 == len(set(ids)))
    check("cases and ground truth cover the same ids", set(ids) == set(gb))
    check("split 70/30/50", Counter(c["split"] for c in cases) == Counter(DEVELOPMENT=70, VALIDATION=30, FINAL_TEST=50), Counter(c["split"] for c in cases))
    check("split files match all_cases", all({c["case_id"] for c in jl(OUT / "02_cases" / f)} == {c["case_id"] for c in cases if c["split"] == s} for f, s in [("development.jsonl", "DEVELOPMENT"), ("validation.jsonl", "VALIDATION"), ("final_test.jsonl", "FINAL_TEST")]))
    check("groups 40/80/30", Counter(g["architecture_group"] for g in gt) == Counter(A_SELF_CONTAINED=40, B_WORKFLOW=80, C_AGENT_DYNAMIC=30), Counter(g["architecture_group"] for g in gt))
    oc = Counter(g["expected_decision"] for g in gt)
    check("four-way outcomes balanced (each 33-42)", all(33 <= oc[k] <= 42 for k in ("APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE")), dict(oc))
    for sp in ("DEVELOPMENT", "VALIDATION", "FINAL_TEST"):
        so = Counter(g["expected_decision"] for g in gt if g["split"] == sp); n = sum(so.values())
        check(f"{sp} has every outcome within 18-36%", all(0.18 <= so[k] / n <= 0.36 for k in oc), dict(so))
    ch = [g for g in gt if g["independent_challenge"]]
    check("15 challenge cases, all in FINAL_TEST", len(ch) == 15 and all(g["split"] == "FINAL_TEST" for g in ch))
    check("cross-document cases >= 110", sum(g["cross_document"] for g in gt) >= 110, sum(g["cross_document"] for g in gt))
    check("temporal-amendment cases present (>= 20)", sum(g["temporal_amendment_case"] for g in gt) >= 20, sum(g["temporal_amendment_case"] for g in gt))
    # ---- corpus
    check("20-22 policy documents", 20 <= len(meta) <= 22, len(meta))
    words = len(corpus.split())
    check("corpus >= 35k words", words >= 35000, words)
    try:
        import pypdf
        pages = len(pypdf.PdfReader(str(OUT / "01_policy_corpus" / "Northstar_Expense_Policy_Corpus_2024_2026.pdf")).pages)
    except Exception as e:  # noqa
        pages = -1
    check("PDF has 65-75 pages", 65 <= pages <= 75, pages)
    allids = [c for d in meta for c in d["clause_ids"]]
    check("clause ids unique", len(allids) == len(set(allids)))
    heads = re.findall(r"^## (\S+) - ", corpus, re.M)
    check("every clause id has a heading in the sources", set(heads) == clauses, len(set(heads) ^ clauses))
    # every schedule value appears in the corpus text
    miss = []
    for S in (W.EMP_MEAL, W.CLIENT_MEAL, W.ENTERTAIN, W.GIFT, W.GIFT_ANNUAL, W.TELECOM, W.MILEAGE, W.TRAIN_CAP, W.HOTEL):
        for k, byyear in S.base.items():
            for y, v in byyear.items():
                if not (f"{v:,}" in corpus or f"{v:g}" in corpus): miss.append((S.name, k, y, v))
    check("every schedule value appears in the corpus", not miss, miss[:3])
    check("every circular appears in the corpus", all(a["id"] in corpus and a["eff"] in corpus for a in W.AMEND))
    notes = re.findall(r"Interpretive guidance: (.+)", corpus)
    check("commentary contains no digits or currency codes (except tier labels)", not [n for n in notes if re.search(r"\d|%|\b(SGD|INR|JPY)\b", re.sub(r"Tier-\d", "Tier", n))], len(notes))
    # ---- ground truth
    bad = [g["case_id"] for g in gt if [i for i in g["required_policy_ids"] + g["supporting_policy_ids"] if i not in clauses]]
    check("all cited clause ids exist in the corpus", not bad, bad[:3])
    check("controlling clauses present for every case", all(g["required_policy_ids"] for g in gt))
    check("self-contained cases need no enterprise tool", all(not g["minimum_required_tools"] for g in gt if g["architecture_group"] == "A_SELF_CONTAINED"))
    check("workflow cases need at least one tool", all(g["minimum_required_tools"] for g in gt if g["architecture_group"] == "B_WORKFLOW"))
    check("dynamic cases need >= 2 tools and a branch trigger", all(len(g["minimum_required_tools"]) >= 2 and g["branch_trigger"] for g in gt if g["architecture_group"] == "C_AGENT_DYNAMIC"))
    check("missing-field lists only on REQUEST_INFORMATION", all((g["expected_decision"] == "REQUEST_INFORMATION") == bool(g["missing_fields"]) for g in gt))
    check("manual-touch flag equals ESCALATE", all(g["manual_touch_required"] == (g["expected_decision"] == "ESCALATE") for g in gt))
    # ---- reference-engine reproduction from the packaged files
    S = engine.State(T); diff = []
    for c in cases:
        g = gb[c["case_id"]]; r = engine.evaluate(dict(c, bill=dict(c["bill"], merchant_category=g["hidden_merchant_category"]), form=g["hidden_form"], employee_description=g["hidden_description"]), S)
        if (r["expected_decision"], r["controlling_clause_ids"], r["missing_fields"], [t["tool"] for t in r["tool_path"]]) != (g["expected_decision"], g["required_policy_ids"], g["missing_fields"], [t["tool"] for t in g["tool_path"]]): diff.append(c["case_id"])
    check("ground truth reproduced by the reference engine from the packaged files", not diff, diff[:5])
    # ---- semantic layer
    hid = {k for g in gt for k in g["hidden_form"]} - {"expense_type", "approval_ref", "charge_to"}
    check("visible forms expose no decision-critical structured facts", all(not (hid & set(c["form"])) and "expense_type" not in c["form"] for c in cases))
    check("every claim has a validated free-text note (no unresolved semantic problems)", all(not g["semantic"]["unresolved"] for g in gt), [g["case_id"] for g in gt if g["semantic"]["unresolved"]][:8])
    check("visible bills carry one generic line item (no alcohol/tip line items)", all(len(c["bill"]["line_items"]) == 1 for c in cases))
    check("notes are 12-110 words (characters/5 for unspaced scripts)", all(12 <= max(len(c["employee_description"].split()), len(c["employee_description"]) // (3 if re.search(r"[\u3000-\u9fff]", c["employee_description"]) else 5)) <= 110 for c in cases))
    check("visible merchant categories are coarse", {c["bill"]["merchant_category"] for c in cases} <= {"TRAVEL", "FOOD_AND_DRINK", "TECH_AND_SUPPLIES", "EDUCATION_AND_EVENTS", "RETAIL", "OTHER"})
    # ---- referential integrity
    emp = {r["employee_id"] for r in T["employees"]}; proj = {r["project_id"] for r in T["project_registry"]}
    check("case employees and projects exist", all(c["employee_id"] in emp and c["project_id"] in proj for c in cases))
    check("11 enterprise tables", len(T) == 11, sorted(T))
    check("2000-3000 historical expenses", 2000 <= len(T["previous_expenses"]) <= 3000, len(T["previous_expenses"]))
    cid = set(ids)
    check("approval and exception links point at real cases or background ids", all(r["expense_id"] in cid or r["expense_id"].startswith("EXP-BG-") for r in T["manager_approvals"] + T["policy_exceptions"]))
    ex = {r["exception_id"] for r in T["policy_exceptions"]}; ev = {r["event_id"] for r in T["conference_registry"]}; dg = {r["delegation_id"] for r in T["approval_delegations"]}
    check("travel links (event, exception) resolve except deliberate missing exceptions", all((not r["event_id"] or r["event_id"] in ev) for r in T["travel_requests"]))
    check("delegation links resolve", all((not r["delegation_id"]) or r["delegation_id"] in dg for r in T["manager_approvals"]))
    fx = {(r["year"], r["month"], r["currency"]) for r in T["fx_rates"]}
    check("FX rate exists for every case month and currency", all((int(c["transaction_date"][:4]), int(c["transaction_date"][5:7]), c["bill"]["currency"]) in fx for c in cases))
    check("hard-negative history rows present", sum(r["expense_id"].startswith("PREV-N") for r in T["previous_expenses"]) >= 30, sum(r["expense_id"].startswith("PREV-N") for r in T["previous_expenses"]))
    # ---- uniqueness and leakage
    norm = lambda t: re.sub(r"\W+", " ", t.lower()).strip()
    check("all 150 employee descriptions are unique", len({norm(c["employee_description"]) for c in cases}) == 150)
    check("all bill numbers unique", len({c["bill"]["bill_number"] for c in cases}) == 150)
    check("no employee shared across splits", all(len({c["split"] for c in cases if c["employee_id"] == e}) == 1 for e in {c["employee_id"] for c in cases}))
    forbidden = {"expected_decision", "required_policy_ids", "supporting_policy_ids", "architecture_group", "case_family", "archetype", "tool_path", "minimum_required_tools", "branch_trigger", "independent_challenge", "challenge_source", "_gt", "_want", "_key"}
    check("no ground-truth keys in case files", not any(forbidden & (set(c) | set(c["bill"]) | set(c["form"])) for c in cases))
    blob = json.dumps(cases)
    labels = ["independent_challenge", "A_SELF_CONTAINED", "B_WORKFLOW", "C_AGENT_DYNAMIC", "expected_decision", "@K0", "challenge_source"]
    check("no label strings in cases", not [l for l in labels if l in blob])
    tables_txt = "\n".join(p.read_text(encoding="utf-8") for p in (OUT / "03_enterprise_data").glob("*.csv"))
    check("no label strings in policy corpus or tables", not [l for l in labels + ["EXPECTED_"] if l in corpus or l in tables_txt])
    check("no answer text from ground truth in visible data", not [g["reason"][:40] for g in gt if g["reason"] and (g["reason"] in blob or g["reason"] in corpus or g["reason"] in tables_txt)])
    case_ids_in_tables = [p.stem for p in (OUT / "03_enterprise_data").glob("*.csv") if re.search(r"X2-\d{3}", p.read_text(encoding="utf-8"))]
    check("case ids appear in tables only as approval/exception join keys", set(case_ids_in_tables) <= {"manager_approvals", "policy_exceptions"}, case_ids_in_tables)
    check("challenge cases carry no marker in visible fields", not any("challenge" in json.dumps(c).lower() for c in cases if gb[c["case_id"]]["independent_challenge"]))
    failed = [c for c in checks if not c["passed"]]
    (OUT / "06_docs").mkdir(exist_ok=True)
    (OUT / "06_docs" / "validation_report.json").write_text(json.dumps(dict(n_checks=len(checks), n_failed=len(failed), passed=not failed, checks=checks), indent=1))
    for c in checks: print(("PASS " if c["passed"] else "FAIL ") + c["check"] + ("" if c["passed"] else f"  -> {c['detail']}"))
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
