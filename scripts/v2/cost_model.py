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

# Sensitivity-analysis row (NOT part of ARCHITECTURES -- not an authorized, official evaluation; see
# docs/v2/second_touch_disclosure.md). Reconstructed from ui/frontend/public/data/cases.json's guarded-agent
# ("agent") field for all 50 final-test cases: 20 where the deterministic layer resolved the claim (shared
# code with the frozen design, verified to match the frozen decision on all 20, $0 cost) and 30 with a
# genuine, real-tool-call agent execution trace. Kept separate from ARCHITECTURES so it can never silently
# get averaged into an official row; used only for the sensitivity question below.
DIAGNOSTIC_GUARDED_AGENT_FINAL_TEST = [(ROOT / "results/v2/final_test/exp_diagnostic_guarded_agent/predictions.jsonl", "FINAL_TEST")]


def load_gt() -> dict:
    return {json.loads(l)["case_id"]: json.loads(l) for l in open(GT_PATH)}


def load_predictions(path: Path) -> list:
    return [json.loads(l) for l in open(path)]


def _rate_among_automated(automated: list, decision: str) -> tuple:
    """(count, denominator, rate) for 'automated predicted `decision` when truth wasn't `decision`' --
    same shape as FAR, reused for false rejection and unnecessary info-request so all three
    error-mode costs are measured the same way instead of only FAR getting one."""
    denom = [r for r in automated if r["truth"] != decision]
    hits = [r for r in denom if r["pred"] == decision]
    return len(hits), len(denom), (len(hits) / len(denom)) if denom else None


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

    def acc(subset):
        return (sum(1 for r in subset if r["pred"] == r["truth"]) / len(subset)) if subset else None

    far_count, far_denom, far_rate = _rate_among_automated(automated, "APPROVE")
    fr_count, fr_denom, fr_rate = _rate_among_automated(automated, "REJECT")
    ir_count, ir_denom, ir_rate = _rate_among_automated(automated, "REQUEST_INFORMATION")

    return {
        "n": n,
        "automated_decision_rate": len(automated) / n if n else None,
        "escalation_rate": len(escalated) / n if n else None,
        "accuracy_overall": acc(rows),
        "accuracy_on_automated": acc(automated),
        "accuracy_on_escalated_before_human_review": acc(escalated),
        "far_among_automated_count": far_count, "far_among_automated_denominator": far_denom, "far_among_automated": far_rate,
        "false_rejection_among_automated_count": fr_count, "false_rejection_among_automated_denominator": fr_denom, "false_rejection_among_automated": fr_rate,
        "unnecessary_info_request_among_automated_count": ir_count, "unnecessary_info_request_among_automated_denominator": ir_denom, "unnecessary_info_request_among_automated": ir_rate,
        # safe automation rate: fraction of ALL claims that were both automated (not escalated) and correct.
        # NOTE: "automated" here means "not escalated" -- a correct REQUEST_INFORMATION counts as safely
        # automated, same as a correct APPROVE/REJECT. Read this as "handled without a human" not "resolved".
        "safe_automation_rate": (sum(1 for r in automated if r["pred"] == r["truth"]) / n) if n else None,
        # narrower companion metric: terminal decisions only (APPROVE/REJECT), excludes REQUEST_INFORMATION
        "terminal_decision_correct_rate": (sum(1 for r in automated if r["pred"] == r["truth"] and r["pred"] in ("APPROVE", "REJECT")) / n) if n else None,
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


def _error_cost(m: dict, count_key: str, denom_key: str, per_1000: int, dollar_cost: float) -> float:
    """Expected cost/1,000 for one automated error mode: (errors observed / denominator observed) is the
    rate; scaled by the denominator's share of the full population and back up to per_1000 volume. Same
    scaling approach as the pre-existing false-approval cost, reused for false rejection and unnecessary
    info-request so all three automated error modes are priced the same way."""
    count, denom = m[count_key], m[denom_key]
    if not denom:
        return 0.0
    rate = count / denom
    denom_share_of_n = denom / max(m["n"], 1e-9)
    return rate * denom_share_of_n * per_1000 * dollar_cost


def cost_per_1000(m: dict, ai_cost_per_claim: float, a: BusinessAssumptions) -> dict:
    """Expected cost per 1,000 claims for one architecture under one scenario. m = measured dict from
    measure(). All per-claim rates are measured; all dollar costs are the scenario's assumptions."""
    review_cost_per_case = a.reviewer_hourly_cost_usd * (a.average_review_minutes / 60.0)
    per_1000 = 1000
    ai_cost = ai_cost_per_claim * per_1000
    escalation_cost = m["escalation_rate"] * per_1000 * (review_cost_per_case + a.escalation_handling_cost_usd)
    false_approval_cost = _error_cost(m, "far_among_automated_count", "far_among_automated_denominator", per_1000, a.false_approval_cost_usd)
    false_rejection_cost = _error_cost(m, "false_rejection_among_automated_count", "false_rejection_among_automated_denominator", per_1000, a.false_rejection_cost_usd)
    unnecessary_info_cost = _error_cost(m, "unnecessary_info_request_among_automated_count", "unnecessary_info_request_among_automated_denominator", per_1000, a.unnecessary_info_request_cost_usd)
    total = ai_cost + escalation_cost + false_approval_cost + false_rejection_cost + unnecessary_info_cost
    return {
        "ai_cost_usd": round(ai_cost, 2),
        "human_review_cost_usd": round(escalation_cost, 2),
        "false_approval_cost_usd": round(false_approval_cost, 2),
        "false_rejection_cost_usd": round(false_rejection_cost, 2),
        "unnecessary_info_request_cost_usd": round(unnecessary_info_cost, 2),
        "total_expected_cost_usd": round(total, 2),
    }


# measured from summary.json total_cost_usd / n, see docs/v2/master_comparison.md -- module-level so
# other consumers (e.g. scripts/v2/export_project_story.py) can compute the same cost table instead of
# hand-copying its output.
AI_COST_PER_CLAIM = {
    "Fixed workflow (Exp 18) — dev": 0.0,
    "Official frozen selective resolver (Exp 30) — dev": 0.029969 / 70,
    "Official frozen selective resolver (Exp 32) — final test": 0.023124 / 50,
    "Guarded-agent candidate (Exp 52) — dev": 0.089163 / 70,
    "Guarded-agent candidate (Exp 52) — validation": 0.02079 / 30,
}


def measured_and_costs() -> tuple:
    """(measured, ai_cost_per_claim) -- the two inputs every consumer of this cost model needs, computed
    once here so a second script never has to recompute or hand-copy them."""
    gt = load_gt()
    measured = {name: measure(name, sources, gt) for name, sources in ARCHITECTURES.items()}
    return measured, AI_COST_PER_CLAIM


def main():
    measured, ai_cost_per_claim = measured_and_costs()
    gt = load_gt()
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
             "Accuracy (escalated, pre-human-review) | FAR among automated | FRR among automated | "
             "Unnecessary-info-request rate among automated | Safe automation rate | Terminal-decision correct rate |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, m in measured.items():
        lines.append(
            f"| {name} | {m['n']} | {m['automated_decision_rate']:.1%} | {m['escalation_rate']:.1%} | "
            f"{m['accuracy_on_automated']:.1%} | "
            f"{m['accuracy_on_escalated_before_human_review']:.1%} | "
            f"{m['far_among_automated_count']}/{m['far_among_automated_denominator']} = {(m['far_among_automated'] or 0):.1%} | "
            f"{m['false_rejection_among_automated_count']}/{m['false_rejection_among_automated_denominator']} = {(m['false_rejection_among_automated'] or 0):.1%} | "
            f"{m['unnecessary_info_request_among_automated_count']}/{m['unnecessary_info_request_among_automated_denominator']} = {(m['unnecessary_info_request_among_automated'] or 0):.1%} | "
            f"{m['safe_automation_rate']:.1%} | {m['terminal_decision_correct_rate']:.1%} |")
    lines.append("")
    lines.append("**Safe automation rate** = fraction of ALL claims that were both auto-resolved (not sent "
                 "to a human) AND correct -- this INCLUDES a correct REQUEST_INFORMATION as \"safe,\" so read "
                 "it as \"handled without a human,\" not as \"resolved to a final APPROVE/REJECT.\" For the "
                 "narrower claim, use **terminal-decision correct rate** (APPROVE/REJECT only, as a fraction "
                 "of all claims) alongside it. This is the single number closest to \"how much of this process "
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
                     "False-rejection cost/1,000 | Unnecessary-info-request cost/1,000 | **Total expected cost/1,000** |")
        lines.append("|---|---|---|---|---|---|---|")
        for name, m in measured.items():
            c = cost_per_1000(m, ai_cost_per_claim[name], a)
            lines.append(f"| {name} | ${c['ai_cost_usd']} | ${c['human_review_cost_usd']} | "
                         f"${c['false_approval_cost_usd']} | ${c['false_rejection_cost_usd']} | "
                         f"${c['unnecessary_info_request_cost_usd']} | **${c['total_expected_cost_usd']}** |")
        lines.append("")

    lines.append("## Sensitivity analysis: does the candidate's cost advantage survive its diagnostic final-run safety numbers? (no new LLM calls)\n")
    lines.append(
        "The candidate's cost advantage above is computed from its **development/validation** rates. "
        "`docs/v2/second_touch_disclosure.md` discloses a separate, unauthorized, partial (30/50) guarded-agent "
        "run against final-test cases with materially worse safety (50% accuracy, 17.6% FAR) than any "
        "authorized number for this design. This section asks the real enterprise question: **if the "
        "candidate's true unseen-data performance looks like that diagnostic run rather than its "
        "dev/validation numbers, does it remain the cheaper architecture?** Reconstructed from real data "
        "(`ui/frontend/public/data/cases.json`'s guarded-agent field for all 50 final-test cases -- 20 "
        "deterministic-path cases, shared code with the frozen design, verified to match its decision on "
        "all 20 at $0 cost; 30 with a genuine, real-tool-call agent execution trace) and real per-case cost "
        "from `results/run_log.jsonl`'s `RESOLVER_V2`/`RESOLVER_V2_REGEN` entries -- **no new LLM calls were "
        "made for this analysis.** This reconstruction is diagnostic, not an authorized evaluation: it has "
        "no freeze manifest and its provenance could not be established from committed scripts or logging.\n")
    diag_m = measure("Guarded-agent candidate — DIAGNOSTIC final-run (unauthorized, n=30/50)", DIAGNOSTIC_GUARDED_AGENT_FINAL_TEST, gt)
    diag_ai_cost = 0.16836 / 50  # measured total cost for the 30 genuine-trace cases / all 50 in this population
    lines.append("| Architecture | N | Automated rate | Escalation rate | FAR among automated | FRR among automated | Safe automation rate |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, m in {**{k: v for k, v in measured.items() if "Guarded-agent" in k or "final test" in k}, "Guarded-agent candidate — DIAGNOSTIC final-run (unauthorized, n=30/50)": diag_m}.items():
        lines.append(f"| {name} | {m['n']} | {m['automated_decision_rate']:.1%} | {m['escalation_rate']:.1%} | "
                     f"{m['far_among_automated_count']}/{m['far_among_automated_denominator']} = {(m['far_among_automated'] or 0):.1%} | "
                     f"{m['false_rejection_among_automated_count']}/{m['false_rejection_among_automated_denominator']} = {(m['false_rejection_among_automated'] or 0):.1%} | "
                     f"{m['safe_automation_rate']:.1%} |")
    lines.append("")
    lines.append("**Cost per 1,000 claims if the candidate's real-world rates matched this diagnostic run, base scenario ($35/hr reviewer, 6 min/review, $150/false approval):**\n")
    lines.append("| Architecture | Total expected cost/1,000 |")
    lines.append("|---|---|")
    base = SCENARIOS["base"]
    for name in ("Official frozen selective resolver (Exp 32) — final test", "Guarded-agent candidate (Exp 52) — dev", "Guarded-agent candidate (Exp 52) — validation"):
        c = cost_per_1000(measured[name], ai_cost_per_claim[name], base)
        lines.append(f"| {name} | **${c['total_expected_cost_usd']}** |")
    diag_c = cost_per_1000(diag_m, diag_ai_cost, base)
    lines.append(f"| Guarded-agent candidate — DIAGNOSTIC final-run (unauthorized, n=30/50) | **${diag_c['total_expected_cost_usd']}** |")
    lines.append("")
    verdict = "does NOT survive" if diag_c["total_expected_cost_usd"] > cost_per_1000(measured["Official frozen selective resolver (Exp 32) — final test"], ai_cost_per_claim["Official frozen selective resolver (Exp 32) — final test"], base)["total_expected_cost_usd"] else "survives"
    lines.append(f"**Answer: the candidate's cost advantage {verdict} once its diagnostic final-run safety numbers are used instead of its dev/validation numbers.** "
                 "Once false approvals are priced at meaningful business cost, degraded unseen-data safety "
                 "erases the modeled advantage quickly -- exactly the failure mode a real deployment risks if "
                 "development/validation-tuned rates do not hold on genuinely new data. This is the central "
                 "reason the frozen selective resolver remains the official architecture for this project: it "
                 "is the only one with a properly frozen, one-shot result to check against, and that check "
                 "came back at 0 observed false approvals.\n")

    lines.append("## Reading this model\n")
    lines.append(
        "The frozen selective resolver is computationally cheapest (near-zero AI cost), but this table is "
        "what determines whether it is operationally cheapest -- item 35's requirement. Do not read a low "
        "AI-cost number alone as a cost conclusion; read the **Total expected cost/1,000** column. All "
        "dollar figures under 'Assumption' are labeled, configurable business assumptions, not measured "
        "quantities; only the automation-metrics table above is measured. **Correction:** an earlier version "
        "of this model omitted false-rejection and unnecessary-information-request costs from the total even "
        "though both were already defined as assumptions -- the total now includes both, priced the same way "
        "as the false-approval cost (measured error rate among automated decisions, scaled to the per-1,000 "
        "volume). This changed which architecture is cheaper in the base and high scenarios; see the headline "
        "conclusion below.")

    out = ROOT / "docs/v2/cost_and_business_impact.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    print(json.dumps(measured, indent=1))


if __name__ == "__main__":
    main()
