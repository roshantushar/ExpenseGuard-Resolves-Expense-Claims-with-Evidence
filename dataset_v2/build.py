"""ExpenseGuard V2 - build the complete dataset package into ExpenseGuard_V2_DATASET/.  Usage: python -m dataset_v2.build"""
from __future__ import annotations
import csv, hashlib, json, random, shutil, sys
from collections import Counter
from pathlib import Path
from . import world as W, assemble, engine, render, policy_text, faq, semantic

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ExpenseGuard_V2_DATASET"
FAMILY = dict(A1="EMPLOYEE_MEAL_TEMPORAL", A2="CLIENT_MEAL", A3="ALCOHOL_REGIONAL", A4="PERSONAL_SPEND", A5="SUBMISSION_WINDOW", A6="GROUND_TRANSPORT", A7="MILEAGE", A8="GIFT_RULES", A9="EVIDENCE_CONFLICT", A10="EQUIPMENT_TIERS",
              A11="GRATUITY_REGIONAL", A12="FX_THRESHOLD", A13="FINANCE_THRESHOLD", B1="HOTEL_CEILING", B2="HOTEL_CONFERENCE", B3="HOTEL_EXCEPTION", B4="AIRFARE_CABIN", B5="SOFTWARE_APPROVAL", B6="DUPLICATE_CHECK", B7="SPLIT_TRANSACTION",
              B8="GIFT_ANNUAL_CAP", B9="TRAINING_CAP", B10="TELECOM_MONTHLY", B11="APPROVAL_TIERS", B12="RESTRICTED_MERCHANT", B13="CONFERENCE_FEE", B14="CAR_RENTAL", C1="DYNAMIC_HOTEL_DISCOVERY",
              C2="DYNAMIC_DELEGATION_CHAIN", C3="DYNAMIC_PROJECT_BUDGET_CHAIN", C4="DYNAMIC_DEEP_HOTEL_CHAIN")
CHALLENGE_QUOTA = {"A_SELF_CONTAINED": 4, "B_WORKFLOW": 7, "C_AGENT_DYNAMIC": 4}
NO_CHALLENGE = {"A9", "B3"}                        # these quote identifiers or depend on wording


def challenge_desc(c, rng):
    return _challenge_core(c, rng) + f" Receipt ref {c['bill']['bill_number']}."


def _challenge_core(c, rng):
    """Alternative phrasing written independently of the main templates (different structure and vocabulary; same structured facts). Not human-reviewed."""
    f, b = c["form"], c["bill"]; et = f["expense_type"]; m = b["merchant"]; city = b["city"]
    if et == "MEAL_EMPLOYEE": return f"Nothing fancy: the {f['attendees_total']} of us stayed on after the session and ate at {m}. Nobody from outside the company joined."
    if et in ("MEAL_CLIENT", "ENTERTAINMENT"): return f"Guests were in town, so we hosted {f['external_attendees']} of their people at {m}; {f['attendees_total']} at the table counting us. The figure is the whole tab."
    if et == "HOTEL": return f"Put up in {city} for {f['nights']} evenings on assignment. The figure is what the property charged, no upgrades, no extras."
    if et == "AIRFARE": return f"Booked the {f['cabin'].replace('_', ' ').lower()} seat myself; the sector is roughly {f['flight_hours']:g} hours in the air."
    if et == "GROUND_TRANSPORT": return f"Needed to get from {f.get('origin') or 'a client location'} to {f.get('destination') or 'the office'}; a cab was the only sensible option."
    if et == "GIFT": return f"A token of thanks for a contact at {f.get('recipient_org') or 'a partner firm'}; picked it up at {m}."
    if et == "SOFTWARE": return f"{m} plan; I am the owner on record and it underpins our team's day-to-day analysis."
    if et == "EQUIPMENT": return f"Needed {f.get('item', 'kit')} in a hurry and {m} had stock."
    if et == "TRAINING": return f"Course through {m}, tied to development plan {f['learning_plan_id']}."
    if et == "TELECOM": return f"Phone and data usage for work calls this month, billed by {m}."
    if et == "CONFERENCE_FEE": return f"Delegate pass, reference {f['conference_ref']}, which I am attending for work."
    if et == "MILEAGE": return f"Own vehicle for the site trip; the odometer says {f['distance_km']} km."
    if et == "CAR_RENTAL": return f"Self-drive hire from {m} for a field day."
    return f"Charge at {m}; purpose as stated on the form."


def pick_challenge(cases, rng):
    final = [c for c in cases if c["split"] == "FINAL_TEST" and c["_arch"] not in NO_CHALLENGE]
    chosen, cnt = [], Counter()
    for grp, q in CHALLENGE_QUOTA.items():
        pool = [c for c in final if c["_group"] == grp]; rng.shuffle(pool)
        for _ in range(q):
            best = min(pool, key=lambda c: cnt[c["_gt"]["expected_decision"]]); pool.remove(best); chosen.append(best); cnt[best["_gt"]["expected_decision"]] += 1
    return chosen


def human_review_reason(g):
    r = g["reason"].lower()
    for k, v in [("prepaid", "PROCUREMENT_THRESHOLD"), ("merchant", "RESTRICTED_MERCHANT"), ("finance review threshold", "FINANCE_THRESHOLD"), ("delegation", "DELEGATION_LIMIT_OR_LEVEL"), ("different type", "CONFLICTING_APPROVAL"),
                 ("another type", "CONFLICTING_APPROVAL"), ("frozen", "COST_CENTRE_FROZEN"), ("project is not active", "PROJECT_NOT_ACTIVE"), ("parent project", "PROJECT_NOT_ACTIVE"), ("exception scope", "EXCEPTION_SCOPE_MISMATCH"),
                 ("approval tier", "LATE_SUBMISSION_FINANCE_TIER")]:
        if k in r: return v
    return "UNSPECIFIED"


def write_csv(path, rows):
    cols = list(rows[0]) if rows else []
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def main():
    if OUT.exists(): shutil.rmtree(OUT)
    for d in ("01_policy_corpus", "02_cases", "03_enterprise_data", "04_ground_truth_PRIVATE", "05_generation", "06_docs"): (OUT / d).mkdir(parents=True)
    b, cases, S = assemble.assemble()
    rng = random.Random(W.SEED + 13)
    assemble.assign_splits(cases, rng)
    for c in pick_challenge(cases, rng):
        c["_challenge"] = True; c["employee_description"] = challenge_desc(c, rng)
    for c in cases:                                        # engine result must not depend on wording; re-derive after rewriting
        c["_gt"] = engine.evaluate(c, S)
    assert all(c["_want"] == c["_gt"]["expected_decision"] for c in cases), "intended and engine outcomes diverged"
    sem = semantic.apply(cases, S)                          # visible claims: facts only in LLM-drafted notes; hidden truth stays in the ground truth
    print("semantic layer:", json.dumps({k: v for k, v in sem.items() if k != "failed"}), "failed:", sem["failed"])
    stats = render.build_corpus(OUT / "01_policy_corpus")
    meta = json.loads((OUT / "01_policy_corpus" / "policy_metadata.json").read_text())
    cl2doc = {cid: d["doc_id"] for d in meta for cid in d["clause_ids"]}
    cases.sort(key=lambda c: c["case_id"])
    vis = [c["_vis"] for c in cases]
    (OUT / "02_cases" / "all_cases.jsonl").write_text("\n".join(json.dumps(v) for v in vis) + "\n")
    for sp, fn in (("DEVELOPMENT", "development"), ("VALIDATION", "validation"), ("FINAL_TEST", "final_test")):
        (OUT / "02_cases" / f"{fn}.jsonl").write_text("\n".join(json.dumps(v) for v in vis if v["split"] == sp) + "\n")
    write_csv(OUT / "02_cases" / "all_cases.csv", [dict(case_id=v["case_id"], split=v["split"], employee_id=v["employee_id"], transaction_date=v["transaction_date"], submission_date=v["submission_date"], merchant=v["bill"]["merchant"],
                                                        merchant_category=v["bill"]["merchant_category"], country=v["bill"]["country"], currency=v["bill"]["currency"], total=v["bill"]["total"],
                                                        employee_description=v["employee_description"], project_id=v["project_id"]) for v in vis])
    for t, rows in b.T.items():
        write_csv(OUT / "03_enterprise_data" / f"{t}.csv", sorted(rows, key=lambda r: json.dumps(r, sort_keys=True)) if t == "previous_expenses" else rows)
    gts, manifest = [], []
    for c in cases:
        g = c["_gt"]; ids = g["controlling_clause_ids"] + g["context_clause_ids"]; docs_ = sorted({cl2doc[i] for i in ids})
        esc = g["expected_decision"] == "ESCALATE"
        rec = dict(case_id=c["case_id"], split=c["split"], expected_decision=g["expected_decision"], architecture_group=c["_group"], case_family=FAMILY[c["_arch"]], archetype=c["_arch"],
                   required_policy_ids=g["controlling_clause_ids"], supporting_policy_ids=g["context_clause_ids"], required_doc_ids=docs_, cross_document=len(docs_) >= 2,
                   temporal_amendment_case=any(i.startswith("CIRC-") for i in g["controlling_clause_ids"]), missing_fields=g["missing_fields"], manual_touch_required=esc, human_review_reason=human_review_reason(g) if esc else None,
                   tool_path=g["tool_path"], minimum_required_tools=g["minimum_required_tools"], branch_trigger=g["branch_trigger"], dynamic_branching=c["_group"] == "C_AGENT_DYNAMIC",
                   agent_required_candidate=c["_group"] == "C_AGENT_DYNAMIC", reason=g["reason"], facts=g["facts"], independent_challenge=bool(c.get("_challenge")), hidden_form=c["_hidden_form"], hidden_merchant_category=c["_hidden_cat"], hidden_description=c["_orig_desc"],
                   semantic=dict(style=c["_sem"]["style"], attempts=c["_sem"]["attempts"], unresolved=c["_sem"]["problems"], manual_review=c["_sem"].get("manual_review")),
                   challenge_source="independently authored alternative phrasing (not human-reviewed)" if c.get("_challenge") else "")
        gts.append(rec)
        manifest.append({k: rec[k] for k in ("case_id", "split", "architecture_group", "case_family", "expected_decision", "cross_document", "independent_challenge")})
    (OUT / "04_ground_truth_PRIVATE" / "ground_truth.jsonl").write_text("\n".join(json.dumps(r) for r in gts) + "\n")
    write_csv(OUT / "04_ground_truth_PRIVATE" / "case_family_manifest.csv", manifest)
    shutil.copy(ROOT / "ExpenseGuard_FINAL_CURRENT_DATASET" / "04_ground_truth_PRIVATE" / "guardrail_cases.csv", OUT / "04_ground_truth_PRIVATE" / "guardrail_cases.csv")
    cfg = dict(seed=W.SEED, cases=len(cases), splits=dict(Counter(c["split"] for c in cases)), challenge_final_cases=sum(1 for c in cases if c.get("_challenge")), corpus=stats, semantic={k: v for k, v in sem.items()},
               historical_expenses=len(b.T["previous_expenses"]), tables=len(b.T))
    (OUT / "05_generation" / "generation_config.json").write_text(json.dumps(cfg, indent=1))
    print(json.dumps(cfg, indent=1))
    return cfg


if __name__ == "__main__":
    main()
