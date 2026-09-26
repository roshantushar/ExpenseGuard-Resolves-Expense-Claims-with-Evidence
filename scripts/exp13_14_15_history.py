"""Experiments 13 (missing information), 14 (duplicate detection) and 15 (split transactions). Development + validation (80 cases).
13 re-scores existing predictions (rules, Exp 12 hybrid gpt-4o-mini / llama); 14 and 15 run new deterministic pipelines, plus LLM adjudication for ambiguous duplicates."""
from __future__ import annotations
import json, os, re, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, llm_exp, evaluate, history, policy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C.load_env()
SPLITS = ["DEVELOPMENT", "VALIDATION"]
cases = [dict(c, _split=s) for s in SPLITS for c in llm_exp.cases_for(s)]
gt = evaluate.load_gt()
OUT = C.RESULTS / "development" / "exp13_14_15"; OUT.mkdir(parents=True, exist_ok=True)
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
summary = {}


def jl(p): return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def log(exp, name, rows, agg):
    rid = f"{exp}-{name}-{uuid.uuid4().hex[:6]}"
    for r in rows: llm.log_event(type="evaluation", run_id=rid, experiment=exp, split="DEV+VAL", model=name, **r)
    llm.log_event(type="experiment_summary", run_id=rid, experiment=exp, split="DEV+VAL", model=name, **agg)


# ============================ Exp 13: missing information ============================
def canon(f: str) -> set:
    """Map a free-form requested-field name onto the dataset's field vocabulary (evaluator-side, keyword based)."""
    f = f.lower()
    s = set()
    if "origin" in f or "start" in f or "pickup" in f or f in ("from", "from_location"): s.add("origin")
    if "destination" in f or "drop" in f or f in ("to", "to_location"): s.add("destination")
    if "route" in f or "trip_details" in f or "journey" in f: s |= {"origin", "destination"}
    if "attendee" in f or "participant" in f or "guest" in f:
        if any(k in f for k in ("name", "organi", "external", "client")): s.add("external_attendee_names")
        if any(k in f for k in ("count", "number", "total")): s.add("attendee_count")
        if not s & {"external_attendee_names", "attendee_count"}: s |= {"external_attendee_names", "attendee_count"}
    if any(k in f for k in ("itemi", "business_amount", "business_portion", "personal_item", "personal_amount", "breakdown")): s.add("business_amount")
    if "purpose" in f or "justification" in f or "reason" in f:
        s.add("correct_business_purpose" if any(k in f for k in ("correct", "clarif", "conflict", "mismatch")) else "specific_business_purpose")
    if "duplicate" in f or "previous_claim" in f: s.add("duplicate_clarification")
    if "travel" in f and ("approv" in f or "request" in f): s.add("approved_travel_request")
    return s or {f}


sources = {"rules (Exp 2)": lambda sp: jl(C.RESULTS / sp.lower() / "exp02" / "predictions.jsonl")}
for m in models:
    tag = m.replace("/", "_").replace(":", "_")
    sources[f"RAG + code facts, {m.split('/')[-1]} (Exp 12)"] = (lambda tag: lambda sp: jl(C.RESULTS / sp.lower() / "exp12_hybrid" / f"predictions_{tag}.jsonl"))(tag)
e13 = {}
for name, load in sources.items():
    pred = {p["case_id"]: p for sp in SPLITS for p in load(sp)}
    fam = [c["case_id"] for c in cases if gt[c["case_id"]]["case_family"] == "MISSING_INFORMATION"]
    tp = fp = fn = exact = ri_ok = 0
    for cid in fam:
        g, p = gt[cid], pred[cid]
        ri_ok += p["predicted_decision"] == "REQUEST_INFORMATION"
        want = set(g["missing_fields"]); got = set().union(*[canon(x) for x in p["missing_fields"]]) if p["predicted_decision"] == "REQUEST_INFORMATION" else set()
        tp += len(want & got); fp += len(got - want); fn += len(want - got); exact += want == got
    others = [c["case_id"] for c in cases if gt[c["case_id"]]["expected_decision"] != "REQUEST_INFORMATION"]
    unnecessary = sum(pred[cid]["predicted_decision"] == "REQUEST_INFORMATION" for cid in others)
    e13[name] = {"n_missing_cases": len(fam), "ri_disposition_correct": f"{ri_ok}/{len(fam)}", "field_precision": round(tp / (tp + fp), 3) if tp + fp else 0.0,
                 "field_recall": round(tp / (tp + fn), 3) if tp + fn else 0.0, "exact_field_set": f"{exact}/{len(fam)}",
                 "unnecessary_request_rate": round(unnecessary / len(others), 3), "unnecessary_requests": f"{unnecessary}/{len(others)}"}
    print("Exp13", name, e13[name])
summary["exp13"] = e13

# ============================ Exp 14: duplicates ============================
CLASSES = ["EXACT_DUPLICATE", "POSSIBLE_DUPLICATE", "LEGITIMATE_REPEAT", "NONE"]
DISP = {"EXACT_DUPLICATE": "REJECT", "POSSIBLE_DUPLICATE": "REQUEST_INFORMATION", "LEGITIMATE_REPEAT": "APPROVE", "NONE": "APPROVE"}
ADJ_SYSTEM = ("You review one expense claim against a candidate earlier expense for possible duplication (claim-level compliance check; never accuse the employee of fraud). "
              "Policy: " + policy.render(["CARD-4.1", "CARD-3.1"]) + "\nClasses: EXACT_DUPLICATE (same employee, merchant and bill number already reimbursed); POSSIBLE_DUPLICATE (very similar but not identical; "
              "the employee must clarify); LEGITIMATE_REPEAT (a genuine recurring or separate expense, e.g. a regular monthly subscription on a different date); NONE.\n"
              'Return ONLY JSON: {"class": one of the four, "reason": "<=1 sentence"}.')


def adjudicate(model, c, cand):
    b = c["bill"]
    user = (f"CLAIM: employee {c['employee_id']}, merchant {b['merchant']}, amount {b['total']:g} {b['currency']}, date {c['transaction_date']}, bill number {b['bill_number']}, "
            f"description: \"{c['employee_description']}\"\nCANDIDATE EARLIER EXPENSE(S): " + "; ".join(
                f"{p['expense_id']}: employee {p['employee_id']}, merchant {p['merchant']}, {p['amount']} {p['currency']}, date {p['transaction_date']}, bill number {p['bill_number']}, purpose \"{p['business_purpose']}\", status {p['status']}" for p in cand))
    r = llm.chat(model, [{"role": "system", "content": ADJ_SYSTEM}, {"role": "user", "content": user}], tag="EXP14_ADJUDICATION", case_id=c["case_id"], split=c["_split"], max_tokens=150)
    try:
        d = json.loads(r["text"]); k = d.get("class")
        return (k if k in CLASSES else "NONE"), r
    except Exception:
        return "NONE", r


def run_dup(name, fn):
    rows, cost = [], {"in": 0, "out": 0, "usd": 0.0}
    for c in cases:
        g = gt[c["case_id"]]
        pred, matched = fn(c, cost)
        rows.append({"case_id": c["case_id"], "expected_class": g["duplicate_status"], "predicted_class": pred, "correct": pred == g["duplicate_status"],
                     "matched_ids": matched, "expected_matched": g["matched_expense_ids"], "case_family": g["case_family"], "expected_decision": g["expected_decision"], "mapped_decision": DISP[pred]})
    pos = lambda k: k in ("EXACT_DUPLICATE", "POSSIBLE_DUPLICATE")
    tp = sum(pos(r["expected_class"]) and pos(r["predicted_class"]) for r in rows); fp = sum(not pos(r["expected_class"]) and pos(r["predicted_class"]) for r in rows)
    fn = sum(pos(r["expected_class"]) and not pos(r["predicted_class"]) for r in rows)
    none = [r for r in rows if r["expected_class"] == "NONE"]; leg = [r for r in rows if r["expected_class"] == "LEGITIMATE_REPEAT"]
    fam = [r for r in rows if r["case_family"] == "DUPLICATE_CHECK"]
    agg = {"class_accuracy": f"{sum(r['correct'] for r in rows)}/{len(rows)}", "duplicate_precision": round(tp / (tp + fp), 3) if tp + fp else 0.0, "duplicate_recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
           "false_positive_rate_on_NONE": f"{sum(pos(r['predicted_class']) for r in none)}/{len(none)}", "false_block_rate_on_LEGITIMATE_REPEAT": f"{sum(pos(r['predicted_class']) for r in leg)}/{len(leg)}",
           "family_disposition_correct": f"{sum(r['mapped_decision'] == r['expected_decision'] for r in fam)}/{len(fam)}", "matched_id_correct": f"{sum(set(r['matched_ids']) == set(r['expected_matched']) for r in rows if pos(r['expected_class']) or r['expected_class'] == 'LEGITIMATE_REPEAT')}/{sum(pos(r['expected_class']) or r['expected_class'] == 'LEGITIMATE_REPEAT' for r in rows)}",
           "input_tokens": cost["in"], "output_tokens": cost["out"], "cost_usd": round(cost["usd"], 6)}
    log("EXP14_DUPLICATES", name, rows, agg)
    print("Exp14", name, agg)
    return agg


def approach_a(c, cost):
    ex = history.exact_duplicate(c)
    return ("EXACT_DUPLICATE", [ex["expense_id"]]) if ex else ("NONE", [])


def approach_b(c, cost): return history.classify_duplicate_rule(c)


def approach_c(model):
    def f(c, cost):
        ex = history.exact_duplicate(c)
        if ex: return "EXACT_DUPLICATE", [ex["expense_id"]]
        cand = history.fuzzy_candidates(c)
        if not cand: return "NONE", []
        k, r = adjudicate(model, c, cand)
        cost["in"] += r["input_tokens"]; cost["out"] += r["output_tokens"]; cost["usd"] += r["cost_usd"]
        return k, [p["expense_id"] for p in cand]
    return f


e14 = {"A exact match": run_dup("A_exact", approach_a), "B exact + fuzzy rules": run_dup("B_fuzzy_rules", approach_b)}
for m in models:
    e14[f"C exact + fuzzy candidates + LLM adjudication ({m.split('/')[-1]})"] = run_dup(f"C_{m.split('/')[-1]}", approach_c(m))
summary["exp14"] = e14

# ============================ Exp 15: split transactions ============================
rows15 = []
for c in cases:
    g = gt[c["case_id"]]; s = history.split_check(c)
    pos_gt = g["split_transaction_status"] == "RELATED_SPLIT"
    rows15.append({"case_id": c["case_id"], "gt_split": pos_gt, "pred_split_detected": s["split_detected"], "gt_related": g["related_expense_ids"], "pred_related": s["related_ids"],
                   "gt_combined": g["combined_amount"], "pred_combined": s["combined_amount"], "gt_policy": g["triggered_policy_id"], "pred_policy": s["triggered_policy"],
                   "gt_decision": g["expected_decision"], "pred_decision": s["decision"], "combined_sgd": s.get("combined_sgd"), "case_family": g["case_family"]})
P = [r for r in rows15 if r["gt_split"]]
linked_ok = sum(set(r["pred_related"]) == set(r["gt_related"]) for r in P)
false_links = sum(bool(r["pred_related"]) for r in rows15 if not r["gt_split"])
tp = sum(r["pred_split_detected"] for r in P); fp = sum(r["pred_split_detected"] for r in rows15 if not r["gt_split"])
e15 = {"n_split_cases": len(P), "related_transaction_retrieval_correct": f"{linked_ok}/{len(P)}", "false_links_on_non_split_cases": f"{false_links}/{len(rows15) - len(P)}",
       "split_precision": round(tp / (tp + fp), 3) if tp + fp else 0.0, "split_recall": f"{tp}/{len(P)}",
       "combined_amount_correct": f"{sum(r['pred_combined'] == r['gt_combined'] for r in P)}/{len(P)}",
       "triggered_policy_correct": f"{sum(r['pred_policy'] == r['gt_policy'] for r in P)}/{len(P)}",
       "disposition_correct_on_split_cases": f"{sum(r['pred_decision'] == r['gt_decision'] for r in P)}/{len(P)}",
       "combined_sgd_of_cases_labelled_above_threshold": {r['case_id']: r['combined_sgd'] for r in P}}
log("EXP15_SPLIT", "deterministic_pipeline", rows15, {k: v for k, v in e15.items() if k != "combined_sgd_of_cases_labelled_above_threshold"})
print("Exp15", json.dumps(e15, indent=1))
summary["exp15"] = e15
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
(OUT / "exp15_rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows15) + "\n")

# ============================ plots ============================
fig, ax = plt.subplots(1, 3, figsize=(20, 4.6))
ns = list(e13)
for j, (k, lab) in enumerate([("field_precision", "field precision"), ("field_recall", "field recall"), ("unnecessary_request_rate", "unnecessary-request rate")]):
    ax[0].bar([i + (j - 1) * 0.27 for i in range(len(ns))], [e13[n][k] for n in ns], 0.27, label=lab)
ax[0].set_xticks(range(len(ns))); ax[0].set_xticklabels([n.replace(", ", ",\n").replace(" (", "\n(") for n in ns], fontsize=6); ax[0].legend(fontsize=7); ax[0].set_ylim(0, 1); ax[0].set_title("Exp 13: missing-information requests")
na = list(e14)
frac = lambda s: int(s.split("/")[0]) / max(1, int(s.split("/")[1]))
for j, (k, lab) in enumerate([("duplicate_precision", "precision"), ("duplicate_recall", "recall")]):
    ax[1].bar([i + (j - 0.5) * 0.3 for i in range(len(na))], [e14[n][k] for n in na], 0.3, label=lab)
ax[1].bar([i + 0.4 for i in range(len(na))], [frac(e14[n]["false_block_rate_on_LEGITIMATE_REPEAT"]) for n in na], 0.2, label="false-block rate (legit repeats)", color="C3")
ax[1].set_xticks(range(len(na))); ax[1].set_xticklabels(["A exact", "B fuzzy rules", "C + gpt-4o-mini", "C + llama"], fontsize=7); ax[1].legend(fontsize=7); ax[1].set_ylim(0, 1.05); ax[1].set_title("Exp 14: duplicate detection")
ks = ["related_transaction_retrieval_correct", "combined_amount_correct", "triggered_policy_correct", "disposition_correct_on_split_cases"]
ax[2].bar(["related\nretrieval", "combined\namount", "triggered\npolicy", "disposition"], [frac(e15[k]) for k in ks], color="C2"); ax[2].set_ylim(0, 1.05)
ax[2].set_title(f"Exp 15: split transactions (n={e15['n_split_cases']}; recall {e15['split_recall']})")
plt.tight_layout(); plt.savefig(C.RESULTS / "plots" / "exp13_14_15_history.png", dpi=130)
