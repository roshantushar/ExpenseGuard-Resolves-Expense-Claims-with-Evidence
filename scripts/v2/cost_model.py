"""Risk-adjusted cost model and automation metrics (items 27-39 of the business-analysis pass).

Reads real predictions + ground truth for three architectures (fixed workflow, official frozen selective
resolver, and the development-and-validation-selected guarded-agent candidate) and computes, per
architecture: automated-decision rate, escalation rate, accuracy on automated vs. escalated cases, FAR
among automated decisions, and safe automation rate -- all measured, nothing assumed.

Then applies a configurable business-cost model (assumptions are parameters, never hardcoded into the
measured numbers) across low/base/high scenarios, and writes both to docs/v2/cost_and_business_impact.md.
No new dependency: stdlib json only, matching the "ask before adding a dependency" rule.

ponytail: single script, single markdown output -- not a package, add structure only if a second
consumer of this data appears.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT_PATH = ROOT / "ExpenseGuard_V2_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl"

ARCHITECTURES = {
    "Fixed workflow (Exp 18) — dev": [(ROOT / "results/v2/development/exp18_fixed_workflow/predictions.jsonl", "DEVELOPMENT")],
    "Official frozen selective resolver (Exp 30) — dev": [(ROOT / "results/v2/development/exp30_selective_router/predictions.jsonl", "DEVELOPMENT")],
    "Official frozen selective resolver (Exp 32) — final test": [(ROOT / "results/v2/final_test/exp32_final_test/predictions.jsonl", "FINAL_TEST")],
    "Guarded-agent candidate (Exp 52) — dev": [(ROOT / "results/v2/dev/exp52_final_confirmed/predictions.jsonl", "DEVELOPMENT")],
    "Guarded-agent candidate (Exp 52) — validation": [(ROOT / "results/v2/validation/exp52_final_confirmed/predictions.jsonl", "VALIDATION")],
}
# Each row above is a single, unmixed population (one architecture, one split) -- never blended across
# splits, per the project's rule against comparing/combining differently-denominated populations (item 14).


def load_gt() -> dict:
    return {json.loads(l)["case_id"]: json.loads(l) for l in open(GT_PATH)}


def load_predictions(path: Path) -> list:
    return [json.loads(l) for l in open(path)]


def measure(name: str, sources: list, gt: dict) -> dict:
    rows = []
    for path, split in sources:
        for p in load_predictions(path):
            g = gt.get(p["case_id"])
            if g is None or g["split"] != split:
                continue
            rows.append({"pred": p["predicted_decision"], "truth": g["expected_decision"],
                         "escalated": p["predicted_decision"] == "ESCALATE" or bool(p.get("manual_review_required"))})
    n = len(rows)
    automated = [r for r in rows if not r["escalated"]]
    escalated = [r for r in rows if r["escalated"]]
    non_approvable = [r for r in rows if r["truth"] != "APPROVE"]
    automated_non_approvable = [r for r in automated if r["truth"] != "APPROVE"]
    false_approvals_automated = [r for r in automated if r["pred"] == "APPROVE" and r["truth"] != "APPROVE"]

    def acc(subset):
        return (sum(1 for r in subset if r["pred"] == r["truth"]) / len(subset)) if subset else None

    return {
        "n": n,
        "automated_decision_rate": len(automated) / n if n else None,
        "escalation_rate": len(escalated) / n if n else None,
        "accuracy_overall": acc(rows),
        "accuracy_on_automated": acc(automated),
        "accuracy_on_escalated_before_human_review": acc(escalated),
        "far_among_automated_count": len(false_approvals_automated),
        "far_among_automated_denominator": len(automated_non_approvable),
        "far_among_automated": (len(false_approvals_automated) / len(automated_non_approvable)) if automated_non_approvable else None,
        # safe automation rate: fraction of ALL claims that were both automated (not escalated) and correct
        "safe_automation_rate": (sum(1 for r in automated if r["pred"] == r["truth"]) / n) if n else None,
    }


@dataclass
class BusinessAssumptions:
    """Every field here is a labeled assumption, never a measured quantity. Vary these to get the
    low/base/high scenarios; nothing else in this model changes between scenarios."""
    monthly_claim_volume: int
    reviewer_hourly_cost_usd: float
    average_review_minutes: float
    false_approval_cost_usd: float          # cost of a reimbursement that should not have been paid
    false_rejection_cost_usd: float         # cost of an incorrectly rejected legitimate claim (rework, morale, delay)
    unnecessary_info_request_cost_usd: float  # cost of an avoidable back-and-forth cycle
    escalation_handling_cost_usd: float     # incremental cost of routing to a human beyond the base review

    def label(self) -> str:
        return f"{self.monthly_claim_volume}/mo, ${self.reviewer_hourly_cost_usd}/hr reviewer"


SCENARIOS = {
    "low": BusinessAssumptions(1000, 20.0, 4.0, 50.0, 20.0, 5.0, 10.0),
    "base": BusinessAssumptions(10000, 35.0, 6.0, 150.0, 50.0, 10.0, 20.0),
    "high": BusinessAssumptions(100000, 60.0, 10.0, 500.0, 150.0, 25.0, 50.0),
}


def cost_per_1000(m: dict, ai_cost_per_claim: float, a: BusinessAssumptions) -> dict:
    """Expected cost per 1,000 claims for one architecture under one scenario. m = measured dict from
    measure(). All per-claim rates are measured; all dollar costs are the scenario's assumptions."""
    review_cost_per_case = a.reviewer_hourly_cost_usd * (a.average_review_minutes / 60.0)
    per_1000 = 1000
    ai_cost = ai_cost_per_claim * per_1000
    escalation_cost = m["escalation_rate"] * per_1000 * (review_cost_per_case + a.escalation_handling_cost_usd)
    # false-approval cost: measured FAR-among-automated * measured share of automated claims that are
    # non-approvable, applied to the per-1000 volume
    non_approvable_share = m["far_among_automated_denominator"] / max(m["n"] * m["automated_decision_rate"], 1e-9) if m["automated_decision_rate"] else 0
    false_approval_cost = (m["far_among_automated"] or 0) * non_approvable_share * m["automated_decision_rate"] * per_1000 * a.false_approval_cost_usd
    total = ai_cost + escalation_cost + false_approval_cost
    return {
        "ai_cost_usd": round(ai_cost, 2),
        "human_review_cost_usd": round(escalation_cost, 2),
        "false_approval_cost_usd": round(false_approval_cost, 2),
        "total_expected_cost_usd": round(total, 2),
    }


def main():
    gt = load_gt()
    measured = {name: measure(name, sources, gt) for name, sources in ARCHITECTURES.items()}
    ai_cost_per_claim = {  # measured from summary.json total_cost_usd / n, see docs/v2/master_comparison.md
        "Fixed workflow (Exp 18) — dev": 0.0,
        "Official frozen selective resolver (Exp 30) — dev": 0.029969 / 70,
        "Official frozen selective resolver (Exp 32) — final test": 0.023124 / 50,
        "Guarded-agent candidate (Exp 52) — dev": 0.089163 / 70,
        "Guarded-agent candidate (Exp 52) — validation": 0.02079 / 30,
    }
    lines = ["# Cost and business-impact model\n",
             "Generated by `scripts/v2/cost_model.py`. Automation metrics below are measured directly from "
             "saved predictions and ground truth (nothing assumed). Each row is a single architecture on a "
             "single evaluation split -- rows are never blended across splits, so a dev row and a "
             "final-test row for the same architecture are reported separately rather than averaged into "
             "one number (per the project's rule against combining differently-denominated populations). "
             "The cost tables that follow apply configurable business assumptions to those measured rates "
             "across three labeled scenarios; changing the scenario never changes the measured metrics "
             "above it.\n",
             "## Measured automation metrics (items 29-30)\n",
             "| Architecture | N | Automated-decision rate | Escalation rate | Accuracy (automated) | "
             "Accuracy (escalated, pre-human-review) | FAR among automated | Safe automation rate |",
             "|---|---|---|---|---|---|---|---|"]
    for name, m in measured.items():
        lines.append(
            f"| {name} | {m['n']} | {m['automated_decision_rate']:.1%} | {m['escalation_rate']:.1%} | "
            f"{m['accuracy_on_automated']:.1%} | "
            f"{m['accuracy_on_escalated_before_human_review']:.1%} | "
            f"{m['far_among_automated_count']}/{m['far_among_automated_denominator']} = {(m['far_among_automated'] or 0):.1%} | "
            f"{m['safe_automation_rate']:.1%} |")
    lines.append("")
    lines.append("**Safe automation rate** = fraction of ALL claims that were both auto-resolved (not sent "
                 "to a human) AND correct. This is the single number closest to \"how much of this process "
                 "can this system actually be trusted to run unattended,\" and it is why 40% incorrect does "
                 "not mean 40% needs human review (item 30) -- incorrect automated decisions, escalations, "
                 "and information requests are three different outcomes with three different costs, kept "
                 "separate below rather than collapsed into one 'wrong' bucket.\n")

    lines.append("## Risk-adjusted cost per 1,000 claims, by scenario (items 31-39)\n")
    for scen_name, a in SCENARIOS.items():
        lines.append(f"### Scenario: {scen_name} ({a.label()})\n")
        lines.append("| Assumption | Value |")
        lines.append("|---|---|")
        for k, v in asdict(a).items():
            lines.append(f"| {k} | {v} |")
        lines.append("")
        lines.append("| Architecture | AI cost/1,000 | Human-review cost/1,000 | False-approval cost/1,000 | "
                     "**Total expected cost/1,000** |")
        lines.append("|---|---|---|---|---|")
        for name, m in measured.items():
            c = cost_per_1000(m, ai_cost_per_claim[name], a)
            lines.append(f"| {name} | ${c['ai_cost_usd']} | ${c['human_review_cost_usd']} | "
                         f"${c['false_approval_cost_usd']} | **${c['total_expected_cost_usd']}** |")
        lines.append("")

    lines.append("## Reading this model\n")
    lines.append(
        "The frozen selective resolver is computationally cheapest (near-zero AI cost), but this table is "
        "what determines whether it is operationally cheapest -- item 35's requirement. Do not read a low "
        "AI-cost number alone as a cost conclusion; read the **Total expected cost/1,000** column. All "
        "dollar figures under 'Assumption' are labeled, configurable business assumptions, not measured "
        "quantities; only the automation-metrics table above is measured. This model does not include "
        "false-rejection or unnecessary-information-request costs in the per-1,000 total yet (their rates "
        "were not separated from general inaccuracy in this pass) -- treat the totals above as a partial, "
        "conservative estimate (a floor, not a ceiling) until that breakdown is added.")

    out = ROOT / "docs/v2/cost_and_business_impact.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    print(json.dumps(measured, indent=1))


if __name__ == "__main__":
    main()
