"""Extended evaluation metrics (evaluator-side: joins private ground truth AFTER a run; never import from runtime code).
Complements evaluate.evaluate with per-class P/R/F1, wrongful rejection, escalation errors, citation quality, missing-field P/R, auto-resolved error rate, cost per correct."""
from __future__ import annotations
from .evaluate import load_gt

D = ["APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE"]


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return p, r, f


def extended(recs: list, gt: dict | None = None) -> dict:
    """recs: prediction records (case_id, predicted_decision, policy_evidence, missing_fields, model_cost_usd, ...)."""
    gt = gt or load_gt()
    pairs = [(gt[r["case_id"]], r) for r in recs]
    n = len(pairs)
    out = {"n": n, "per_class": {}}
    for d in D:
        tp = sum(g["expected_decision"] == d and r["predicted_decision"] == d for g, r in pairs)
        fp = sum(g["expected_decision"] != d and r["predicted_decision"] == d for g, r in pairs)
        fn = sum(g["expected_decision"] == d and r["predicted_decision"] != d for g, r in pairs)
        p, rc, f = _prf(tp, fp, fn)
        out["per_class"][d] = {"support": tp + fn, "precision": p, "recall": rc, "f1": f}
    fs = [v["f1"] for v in out["per_class"].values() if v["f1"] is not None]
    out["macro_f1"] = round(sum(fs) / len(fs), 4) if fs else None
    appr = [(g, r) for g, r in pairs if g["expected_decision"] == "APPROVE"]
    out["wrongful_rejections"] = f"{sum(r['predicted_decision'] == 'REJECT' for g, r in appr)}/{len(appr)}"
    out["wrongful_rejection_rate"] = round(sum(r["predicted_decision"] == "REJECT" for g, r in appr) / len(appr), 4) if appr else None
    out["over_escalation_rate"] = round(sum(r["predicted_decision"] == "ESCALATE" and g["expected_decision"] != "ESCALATE" for g, r in pairs) / n, 4)
    esc = [(g, r) for g, r in pairs if g["expected_decision"] == "ESCALATE"]
    out["missed_escalation_rate"] = round(sum(r["predicted_decision"] != "ESCALATE" for g, r in esc) / len(esc), 4) if esc else None
    auto = [(g, r) for g, r in pairs if r["predicted_decision"] != "ESCALATE"]
    out["auto_resolved"] = len(auto)
    out["error_rate_among_auto_resolved"] = round(sum(r["predicted_decision"] != g["expected_decision"] for g, r in auto) / len(auto), 4) if auto else None
    # citation quality: cited vs required policy IDs (gold), cases that cite anything
    cp, cr, cn = [], [], 0
    for g, r in pairs:
        cited, req = set(map(str, r.get("policy_evidence") or [])), set(g["required_policy_ids"])
        if cited:
            cn += 1; cp.append(len(cited & req) / len(cited))
        if req: cr.append(len(cited & req) / len(req))
    out["citation_precision"] = round(sum(cp) / len(cp), 4) if cp else None
    out["citation_recall"] = round(sum(cr) / len(cr), 4) if cr else None
    out["cases_citing_anything"] = cn
    # missing-field P/R over cases where fields are expected or predicted
    tp = fp = fn = 0
    for g, r in pairs:
        e, p = set(g["missing_fields"]), set(r.get("missing_fields") or [])
        tp += len(e & p); fp += len(p - e); fn += len(e - p)
    out["missing_field_precision"], out["missing_field_recall"], _ = _prf(tp, fp, fn)
    correct = sum(g["expected_decision"] == r["predicted_decision"] for g, r in pairs)
    cost = sum(r.get("model_cost_usd", 0) or 0 for r in recs)
    out["cost_per_correct_usd"] = round(cost / correct, 6) if correct else None
    return out


def table(ext: dict):
    """Flat one-row dict for comparison tables."""
    r = lambda x: None if x is None else round(x, 3)
    return {"macro_F1": ext["macro_f1"], "wrongful_reject": ext["wrongful_rejections"], "over_escal_rate": ext["over_escalation_rate"], "missed_escal_rate": ext["missed_escalation_rate"],
            "err_among_auto": ext["error_rate_among_auto_resolved"], "cite_prec": ext["citation_precision"], "cite_rec": ext["citation_recall"],
            "mf_prec": r(ext["missing_field_precision"]), "mf_rec": r(ext["missing_field_recall"]), "cost/correct": ext["cost_per_correct_usd"]}
