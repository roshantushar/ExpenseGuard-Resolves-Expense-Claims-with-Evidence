"""Generates cross-experiment cost/accuracy/latency plots from real, already-saved result files --
every `summary*.json` under results/current/ (81 of them, spanning Exp 0-61) plus the per-call ledger
(results/run_log.jsonl). No new LLM calls, no new computation beyond aggregation.

Usage: python3 scripts/export_experiment_analysis_plots.py
Output: results/current/plots/analysis_*.png
"""
from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cost_model import measured_and_costs, cost_per_1000, SCENARIOS  # noqa: E402 -- measured_and_costs() only reads results/ and ground truth, never writes
RESULTS = ROOT / "results" / "current"
OUT = RESULTS / "plots"
OUT.mkdir(parents=True, exist_ok=True)
RUN_LOG = ROOT / "results" / "run_log.jsonl"

SPLIT_COLOR = {
    "development": "#4c8bf5",
    "validation": "#f5a623",
    "final_test": "#e8505b",
    "holdout": "#9b59b6",
    "other": "#8a8f98",
}

MODEL_LABEL = {
    "openai/gpt-4o-mini": "gpt-4o-mini (paid)",
    "openai/gpt-4o": "gpt-4o (paid)",
    "llama3.2:3b": "llama3.2:3b (free/local)",
    "google/gemini-2.5-flash-lite": "gemini-2.5-flash-lite (paid)",
}


def split_for(path: Path) -> str:
    parts = path.relative_to(RESULTS).parts
    if "development" in parts or parts[0] == "dev":
        return "development"
    if "validation" in parts:
        return "validation"
    if "final_test" in parts:
        return "final_test"
    if "holdout" in parts[0]:
        return "holdout"
    return "other"


def model_for(path: Path, data: dict) -> str:
    if data.get("model"):
        return data["model"]
    stem = path.stem  # summary_openai_gpt-4o-mini
    if stem.startswith("summary_"):
        tail = stem[len("summary_") :]
        for known in ("openai_gpt-4o-mini", "openai_gpt-4o", "llama3.2_3b", "google_gemini-2.5-flash-lite"):
            if tail.startswith(known):
                return known.replace("_", "/", 1).replace("llama3.2/3b", "llama3.2:3b")
    return "unknown"


def load_records():
    records = []
    for path in sorted(RESULTS.glob("**/summary*.json")):
        if "embeddings" in path.parts or "plots" in path.parts or "cache" in str(path):
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if "total_cost_usd" not in data or "n" not in data:
            continue
        exp_dir = path.parent.name
        suffix = path.stem[len("summary_") :] if path.stem.startswith("summary_") else None
        records.append(
            {
                "experiment": exp_dir,
                "run_label": f"{exp_dir} [{suffix}]" if suffix else exp_dir,
                "split": split_for(path),
                "model": model_for(path, data),
                "n": data.get("n", 0),
                "accuracy": data.get("correct_disposition_rate"),
                "far": data.get("false_approval_rate"),
                "cost": data.get("total_cost_usd", 0.0),
                "median_latency_ms": data.get("median_latency_ms"),
                "p95_latency_ms": data.get("p95_latency_ms"),
                "total_tokens": data.get("total_tokens"),
            }
        )
    return records


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)


def plot_cost_per_experiment(records):
    recs = sorted((r for r in records if r["cost"]), key=lambda r: r["cost"], reverse=True)[:30]
    recs.reverse()
    fig, ax = plt.subplots(figsize=(8, 10))
    colors = [SPLIT_COLOR[r["split"]] for r in recs]
    ax.barh([r["run_label"] for r in recs], [r["cost"] for r in recs], color=colors)
    ax.set_xlabel("Cost (USD)")
    ax.set_title("Top 30 experiment runs by LLM cost (of 81 logged runs)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in SPLIT_COLOR.values()]
    ax.legend(handles, SPLIT_COLOR.keys(), loc="lower right", fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_cost_per_experiment.png", dpi=150)
    plt.close(fig)


def plot_cost_vs_accuracy(records):
    recs = [r for r in records if r["accuracy"] is not None and r["cost"] > 0]
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for split, color in SPLIT_COLOR.items():
        pts = [r for r in recs if r["split"] == split]
        if not pts:
            continue
        ax.scatter(
            [r["cost"] for r in pts],
            [r["accuracy"] * 100 for r in pts],
            s=[max(20, r["n"] * 3) for r in pts],
            color=color,
            alpha=0.65,
            label=split,
            edgecolors="white",
            linewidths=0.5,
        )
    ax.set_xscale("log")
    ax.set_xlabel("Run cost, USD (log scale)")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Cost vs. accuracy across every experiment run\n(bubble size = claims evaluated)")
    ax.legend(fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_cost_vs_accuracy.png", dpi=150)
    plt.close(fig)


def plot_cost_by_model(records):
    totals = defaultdict(float)
    counts = defaultdict(int)
    for r in records:
        totals[r["model"]] += r["cost"]
        counts[r["model"]] += 1
    items = sorted(((m, c) for m, c in totals.items() if m != "unknown"), key=lambda x: x[1], reverse=True)
    labels = [MODEL_LABEL.get(m, m) for m, _ in items]
    values = [c for _, c in items]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, values, color=["#2ecc71" if "free" in l else "#4c8bf5" for l in labels])
    for b, (m, _) in zip(bars, items):
        label = "$0.000 (free)" if b.get_height() == 0 else f"${b.get_height():.3f}"
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{label}\n({counts[m]} runs)",
                ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("Total cost (USD)")
    ax.set_title("Total logged cost by model, across all experiment runs")
    ax.set_ylim(0, max(values) * 1.18)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_cost_by_model.png", dpi=150)
    plt.close(fig)


def plot_accuracy_by_model_same_experiment(records):
    by_exp = defaultdict(dict)
    for r in records:
        if r["accuracy"] is None or r["model"] == "unknown":
            continue
        by_exp[r["experiment"]][r["model"]] = r["accuracy"] * 100
    multi = {e: m for e, m in by_exp.items() if len(m) >= 2}
    if not multi:
        return
    models = sorted({m for v in multi.values() for m in v})
    exps = sorted(multi.keys())
    fig, ax = plt.subplots(figsize=(8.5, 5))
    w = 0.8 / len(models)
    colors = plt.cm.tab10.colors
    for i, model in enumerate(models):
        ys = [multi[e].get(model, 0) for e in exps]
        xs = [j + i * w for j in range(len(exps))]
        ax.bar(xs, ys, width=w, label=MODEL_LABEL.get(model, model), color=colors[i % len(colors)])
    ax.set_xticks([j + w * (len(models) - 1) / 2 for j in range(len(exps))])
    ax.set_xticklabels(exps, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Same experiment, different model: paid vs. free/local accuracy")
    ax.legend(fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_accuracy_by_model.png", dpi=150)
    plt.close(fig)


def plot_latency_distribution(records):
    by_model = defaultdict(list)
    for r in records:
        if r["median_latency_ms"]:
            by_model[r["model"]].append(r["median_latency_ms"])
    items = [(MODEL_LABEL.get(m, m), v) for m, v in by_model.items() if m != "unknown" and len(v) >= 2]
    items.sort(key=lambda x: x[0])
    if not items:
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([v for _, v in items], tick_labels=[l for l, _ in items], showfliers=False)
    ax.set_ylabel("Median latency per run (ms)")
    ax.set_title("Latency spread by model, across all experiment runs")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_latency_by_model.png", dpi=150)
    plt.close(fig)


def plot_cumulative_spend():
    if not RUN_LOG.exists():
        return
    points = []
    total = 0.0
    with RUN_LOG.open() as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "llm_call" or d.get("cached"):
                continue  # cache hits log a nominal cost_usd but spend no real money
            cost = d.get("cost_usd")
            ts = d.get("ts")
            if cost is None or not ts:
                continue
            total += cost
            points.append((ts, total))
    if not points:
        return
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(len(points)), [p[1] for p in points], color="#4c8bf5", linewidth=1.5)
    ax.axhline(9.00, color="#e8505b", linestyle="--", linewidth=1, label="Current MAX_BUDGET_USD cap ($9.00)")
    ax.set_xlabel(f"Uncached (real-money) LLM call # (chronological, {len(points)} of them)")
    ax.set_ylabel("Cumulative spend (USD)")
    ax.set_title("Project spend over its full development history")
    ax.legend(fontsize=8, loc="upper left")
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_cumulative_spend.png", dpi=150)
    plt.close(fig)


def plot_cost_breakdown_by_architecture():
    """Business-angle: where the money actually goes per 1,000 claims (base scenario), by architecture --
    not just total cost, but AI inference vs. human review vs. each error type, stacked."""
    measured, ai_cost = measured_and_costs()
    a = SCENARIOS["base"]
    components = ["ai_cost_usd", "human_review_cost_usd", "false_approval_cost_usd",
                  "false_rejection_cost_usd", "unnecessary_info_request_cost_usd"]
    component_labels = ["AI inference", "Human review (escalation)", "False approval",
                         "False rejection", "Unnecessary info request"]
    colors = ["#4c8bf5", "#f5a623", "#e8505b", "#9b59b6", "#8a8f98"]
    names = list(measured.keys())
    short = [n.split(" (")[0].replace("Official frozen selective resolver", "Frozen resolver")
             .replace("Fixed workflow", "Fixed workflow").replace("Guarded-agent candidate", "Guarded agent")
             + "\n" + n.split("— ")[-1] for n in names]
    breakdown = [cost_per_1000(measured[n], ai_cost[n], a) for n in names]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bottom = [0.0] * len(names)
    for comp, label, color in zip(components, component_labels, colors):
        vals = [b[comp] for b in breakdown]
        ax.bar(short, vals, bottom=bottom, label=label, color=color)
        bottom = [bo + v for bo, v in zip(bottom, vals)]
    for i, total in enumerate(bottom):
        ax.text(i, total, f"${total:,.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_ylabel("Expected cost per 1,000 claims (USD)")
    ax.set_title("Where the cost actually comes from, per architecture\n(base scenario: 10k claims/mo, $35/hr reviewer)")
    ax.legend(fontsize=8, loc="upper right")
    plt.setp(ax.get_xticklabels(), fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_cost_breakdown_by_architecture.png", dpi=150)
    plt.close(fig)


def plot_safety_vs_automation():
    """Business-angle: safe automation rate vs. human review rate -- the two numbers a reviewer actually
    cares about (how much gets handled safely without a human, vs. how much still needs one)."""
    measured, _ = measured_and_costs()
    fig, ax = plt.subplots(figsize=(7, 5.5))
    for name, m in measured.items():
        label = name.replace("Official frozen selective resolver", "Frozen resolver").replace("Guarded-agent candidate", "Guarded agent")
        color = "#4c8bf5" if "Frozen" in label or "Fixed" in label else "#e8505b"
        marker = "o" if "final test" in name else ("s" if "validation" in name else "^")
        ax.scatter(m["escalation_rate"] * 100, m["safe_automation_rate"] * 100, s=140, color=color,
                   marker=marker, edgecolors="white", linewidths=1, zorder=3)
        ax.annotate(label, (m["escalation_rate"] * 100, m["safe_automation_rate"] * 100),
                   textcoords="offset points", xytext=(8, 4), fontsize=7.5)
    ax.set_xlabel("Human review rate (%) — lower is less reviewer burden")
    ax.set_ylabel("Safe automation rate (%) — higher is better")
    ax.set_title("The business tradeoff: review burden vs. safely-automated claims")
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "analysis_safety_vs_automation.png", dpi=150)
    plt.close(fig)


def main():
    records = load_records()
    print(f"loaded {len(records)} experiment-run records from summary*.json files")
    plot_cost_per_experiment(records)
    plot_cost_vs_accuracy(records)
    plot_cost_by_model(records)
    plot_accuracy_by_model_same_experiment(records)
    plot_latency_distribution(records)
    plot_cumulative_spend()
    plot_cost_breakdown_by_architecture()
    plot_safety_vs_automation()
    print(f"wrote plots to {OUT}")


if __name__ == "__main__":
    main()
