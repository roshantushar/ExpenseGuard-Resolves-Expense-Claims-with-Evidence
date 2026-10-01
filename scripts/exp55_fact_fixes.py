"""Exp 55: diagnostic-only, dev split only. Five separate, standalone candidate fact-fixes, tested one at
a time against the UNCHANGED, frozen SYSTEM_LLM_STEP prompt (src/resolver.py) -- only the DETERMINISTIC
FACTS block given to the LLM is corrected, never the prompt. Live gpt-4o-mini calls across the full 36-case
dev-residual set for each variant (unaffected cases hit the existing cache at $0; only cases whose facts
actually changed incur new cost). Does not modify src/resolver.py, src/hybrid_facts.py, src/rules_v2.py, or
src/rules_text.py (all frozen) -- reuses them unmodified and only patches the fact dict handed to the prompt.

Root causes found by inspection before writing this:
  - hybrid_facts.h2_temporal's applicable_hotel_ceiling_local_currency and applicable_meal_ceiling_per_person
    use the static base table only. rules_v2.hotel()/meal() -- the functions that actually DETECT violations --
    already apply the correct circular/temporal-precedence adjustments (CIRC-25-06 Tokyo +5%, CIRC-26-04
    India-T1 +6%, CIRC-25-11 India meal ceiling replacement, etc). The fact shown to the LLM and the logic
    used to judge compliance have silently drifted apart.
  - rules_text.parse()'s attendee-counting regex has no pattern for "myself, N colleagues, and M external
    guests" (X2-047's exact phrasing).
  - rules_text.parse()'s business_owner regex has no pattern for "managed by NAME" (X2-078).
  - rules_text.parse()'s distance_km regex requires an explicit "km" unit; it cannot parse two odometer
    readings ("started at X and ended at Y") at all (X2-088).
"""
from __future__ import annotations
import json
from src import config as C, resolver as R, llm_exp, retrieval, retrievers, embed, hybrid_facts as HF, rules_text as RT, rules_v2 as RV

DIAGNOSTIC_5 = ["X2-011", "X2-047", "X2-078", "X2-088", "X2-125"]

OWNER_RE = __import__("re").compile(r"managed by\s+([A-Z][a-z]+ [A-Z][a-z]+)")
ATTENDEE_RE = __import__("re").compile(rf"myself,\s*{RT.NUMBER}\s*colleagues?,?\s*and\s*{RT.NUMBER}\s*external guests?", __import__("re").I)

# rules_text.num()/NUMBER have no "thousand" support at all -- cannot parse "twenty-three thousand three
# hundred ten". Needed for X2-088's odometer readings; built here rather than touching the frozen file.
_WORDNUM = rf"(?:\d+|(?:{RT.NUMW})(?:[- ](?:{RT.NUMW}))?(?:\s+thousand)?(?:\s+(?:and\s+)?(?:{RT.NUMW})(?:[- ](?:{RT.NUMW}))?\s+hundred)?(?:\s+(?:and\s+)?(?:{RT.NUMW})(?:[- ](?:{RT.NUMW}))?)?)"
ODOMETER_RE = __import__("re").compile(rf"started at\s*({_WORDNUM})\s*and ended at\s*({_WORDNUM})", __import__("re").I)


def word_num(tok: str):
    tok = tok.lower().strip()
    if tok.isdigit():
        return int(tok)
    total, chunk = 0, 0
    for w in __import__("re").split(r"[-\s]+", tok):
        if w in ("and",):
            continue
        elif w == "thousand":
            total += (chunk or 1) * 1000; chunk = 0
        elif w == "hundred":
            chunk = (chunk or 1) * 100
        elif w in RT.TENS:
            chunk += RT.TENS[w]
        elif w in RT.UNITS:
            chunk += RT.UNITS[w]
        else:
            return None
    return total + chunk


def hotel_ceiling_fixed(cc, f, base_ceiling):
    """Reuses rules_v2.hotel()'s exact circular-adjustment logic instead of the static table lookup."""
    y = int(cc["transaction_date"][:4])
    tier = RV.TIER.get(f.get("city") or cc["bill"]["city"])
    ceil = base_ceiling
    if tier == "JP-TOKYO" and y == 2025 and cc["transaction_date"] >= "2025-07-01":
        ceil = RV.rnd(ceil * 1.05)
    if tier == "IN-T1" and y == 2026 and cc["transaction_date"] >= "2026-04-01":
        ceil = RV.rnd(ceil * 1.06)
    return ceil


def meal_ceiling_fixed(cc, f, base_ceiling, client):
    """Reuses rules_v2.meal()'s exact circular-adjustment logic instead of the static table lookup."""
    r = RV.region(cc); yr = int(cc["transaction_date"][:4]); d = cc["transaction_date"]
    ceil = base_ceiling
    if client and r == "SG" and yr == 2025 and d >= "2025-07-01": ceil = 128
    if client and r == "JP" and yr == 2026 and d >= "2026-05-01": ceil = 13500
    if not client:
        if r == "SG" and yr == 2025 and d >= "2025-09-01": ceil = 52
        if r == "JP" and yr == 2025 and d >= "2025-10-01": ceil = 5200
        if r == "IN" and yr == 2025 and d >= "2025-11-01": ceil = 2100
    return ceil


def apply_fix(cc, fix: str, base_facts: dict, f: dict) -> dict:
    facts = dict(base_facts)
    b = cc["bill"]; desc = cc["employee_description"]
    if fix == "hotel_circular" and "applicable_hotel_ceiling_local_currency" in facts:
        facts["applicable_hotel_ceiling_local_currency"] = hotel_ceiling_fixed(cc, f, facts["applicable_hotel_ceiling_local_currency"])
    if fix == "meal_circular" and "applicable_meal_ceiling_per_person" in facts and isinstance(facts["applicable_meal_ceiling_per_person"], (int, float)):
        client = f.get("expense_type") == "MEAL_CLIENT" or (f.get("external_attendees") or 0) > 0
        facts["applicable_meal_ceiling_per_person"] = meal_ceiling_fixed(cc, f, facts["applicable_meal_ceiling_per_person"], client)
    if fix == "attendee_count" and facts.get("per_person_amount") == "unknown_from_claim_text":
        m = ATTENDEE_RE.search(desc)
        if m:
            n_col, n_ext = RT.num(m.group(1)), RT.num(m.group(2))
            if n_col is not None and n_ext is not None:
                total = 1 + n_col + n_ext
                facts["per_person_amount"] = round(b["total"] / total, 2)
                facts["attendees_total_corrected"] = total
    if fix == "business_owner":
        m = OWNER_RE.search(desc)
        if m:
            facts["business_owner_named_in_note"] = m.group(1)
    if fix == "mileage_odometer" and f.get("expense_type") == "MILEAGE" and not f.get("distance_km"):
        m = ODOMETER_RE.search(desc)
        if m:
            start, end = word_num(m.group(1)), word_num(m.group(2))
            if start is not None and end is not None and end > start:
                dist = end - start
                rate = RV.MILEAGE[RV.region(cc)][RV.Y(cc)]
                facts["distance_km_corrected"] = dist
                facts["mileage_calculated_amount"] = round(dist * rate, 2)
    return facts


def run_variant(fix_name: str | None, tag: str):
    cases = llm_exp.cases_for("DEVELOPMENT")
    det = {c["case_id"]: R.deterministic(c) for c in cases}
    residual = [c for c in cases if not det[c["case_id"]][1]]

    RTr = retrievers.Retriever(R.EMB, R.CFG)
    qv = embed.embed(R.EMB, [retrieval.claim_query(cc) for cc in residual], tag=tag)
    ctx = {cc["case_id"]: RTr.context(RTr.rank("dense", "unused", q, R.K, R._mask(RTr.chunks, cc))) for cc, q in zip(residual, qv)}

    facts = {}
    for cc in residual:
        f, fam = HF.extract(cc)
        base = HF.facts_block(fam, R.FACT_LEVELS)
        facts[cc["case_id"]] = apply_fix(cc, fix_name, base, f) if fix_name else base

    def user_fn(cc):
        return f"CLAIM:\n{json.dumps(llm_exp.visible(cc), indent=1)}\n\nDETERMINISTIC FACTS:\n{json.dumps(facts[cc['case_id']], indent=1, default=str)}\n\nRETRIEVED POLICY EXCERPTS:\n{ctx[cc['case_id']]}"

    summary, recs, rows = llm_exp.run(tag, "openai/gpt-4o-mini", "DEVELOPMENT", R.SYSTEM_LLM_STEP, user_fn, cases=residual, config={"fact_fix": fix_name})

    gt = {json.loads(l)["case_id"]: json.loads(l)["expected_decision"] for l in open(C.ROOT / "ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")}
    det_correct = sum(1 for c in cases if det[c["case_id"]][1] and det[c["case_id"]][0]["decision"] == gt[c["case_id"]])
    overall_correct = det_correct + summary["correct"]
    approve_total = sum(1 for cid in gt if any(c["case_id"] == cid for c in cases) and gt[cid] == "APPROVE")
    approve_hits = sum(1 for r in recs if gt[r["case_id"]] == "APPROVE" and r["predicted_decision"] == "APPROVE")
    approve_hits += sum(1 for c in cases if det[c["case_id"]][1] and gt[c["case_id"]] == "APPROVE" and det[c["case_id"]][0]["decision"] == "APPROVE")
    five_hits = sum(1 for r in recs if r["case_id"] in DIAGNOSTIC_5 and r["predicted_decision"] == "APPROVE")

    print(f"\n=== {tag} (fix={fix_name}) ===")
    print(f"(a) of the 5 diagnostic cases now APPROVE: {five_hits}/5")
    print(f"(b) APPROVE recall across 18 approvable dev cases: {approve_hits}/18")
    print(f"(c) false approvals among 52 non-approvable dev cases: {summary['false_approvals']}")
    print(f"(d) overall accuracy across 70 dev cases: {overall_correct}/70")
    print(f"cost this run: ${summary['total_cost_usd']:.4f}")
    for r in recs:
        if r["case_id"] in DIAGNOSTIC_5:
            print(" ", r["case_id"], "->", r["predicted_decision"], "|", (r.get("explanation") or "")[:150])
    return summary, recs


if __name__ == "__main__":
    import sys
    fix = sys.argv[1] if len(sys.argv) > 1 else None
    tag = f"EXP55_{(fix or 'BASELINE').upper()}"
    run_variant(fix, tag)
