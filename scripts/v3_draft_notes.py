"""V3 holdout, step 3: draft notes for the 27 non-evidence-conflict cases via dataset_generator.semantic.process()
(real paid calls, gpt-4o-mini) -- draft -> blind extraction check -> independent engine re-verification, up
to 4 attempts. Mirrors scripts/exp60_draft_notes.py exactly, retargeted to experiments/v3_holdout/. The 3
evidence-conflict cases (X4-022..024) keep their hand-written note_override, unmodified.
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "experiments" / "v3_holdout"
sys.path.insert(0, str(ROOT))

from scripts.v3_generate_cases import CASES, load_tables, NEUTRAL_DESC
from dataset_generator import engine, semantic as SEM
SEM.CACHE = HOLDOUT / "semantic_cache.json"

STYLE_BY_REGION = {"JP": ["local", "local", "dictated", "verbose"], "IN": ["local", "local", "dictated", "mixed"],
                    "SG": ["indirect", "dictated", "verbose", "secondhand", "terse"]}


def region_of(spec):
    return {"Japan": "JP", "India": "IN", "Singapore": "SG"}.get(spec["bill"]["country"], "SG")


def main():
    S = engine.State(load_tables())
    rng = random.Random(6202 + 61)  # distinct offset from Exp 60's rng seed (6202+60)

    out = []
    total_cost = 0.0
    for spec in CASES:
        if spec["note_override"]:
            out.append({**spec, "note": spec["note_override"], "style": "hand-written (evidence-conflict)", "attempts": 0, "problems": [], "cost": 0.0})
            continue
        c = {
            "case_id": spec["case_id"], "employee_id": spec["employee_id"], "transaction_date": spec["transaction_date"],
            "submission_date": spec["submission_date"], "bill": spec["bill"], "project_id": spec["project_id"],
            "_key": spec["case_id"], "_arch": "B99", "_hidden_form": spec["form"], "_orig_desc": NEUTRAL_DESC,
            "_gt": {"expected_decision": None},
        }
        ec = dict(c, form=spec["form"], employee_description=NEUTRAL_DESC)
        c["_gt"]["expected_decision"] = engine.evaluate(ec, S)["expected_decision"]
        c["_style"] = rng.choice(STYLE_BY_REGION[region_of(spec)])
        c["_flavor"] = SEM.flavor_for(c, rng)
        c["_derive"] = SEM.derive_for(c, rng)
        c["_noise"] = SEM.noise_for(c, rng)

        r = SEM.process(c, S, rng, {})
        total_cost += r["cost"]
        out.append({**spec, "note": r["note"], "style": r["style"], "attempts": r["attempts"], "problems": r["problems"], "cost": r["cost"]})
        flag = "  <-- PROBLEMS: " + "; ".join(r["problems"]) if r["problems"] else ""
        print(f"{spec['case_id']:8s} [{r['style']:10s} x{r['attempts']}] {r['note'][:90]!r}{flag}")

    print(f"\nTotal drafting cost: ${total_cost:.4f}")
    failed = [o["case_id"] for o in out if o["problems"]]
    print(f"Cases with unresolved validation problems after 4 attempts: {failed or 'none'}")

    out_path = HOLDOUT / "cases_drafted.json"
    out_path.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
