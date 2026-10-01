"""Generates the two README comparison charts from numbers already published and sourced elsewhere in
this project (docs/exp60_fresh_holdout.md, docs/exp61_v3_holdout.md) -- no new computation, no new LLM
calls, just a visual of existing, cited results. Run after any of those numbers change.

Usage: python3 scripts/export_readme_charts.py
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "current" / "plots"
OUT.mkdir(parents=True, exist_ok=True)

FROZEN = "#8a8f98"
CANDIDATE = "#4c8bf5"


def accuracy_chart():
    labels = ["Exp 60\n(50 cases)", "Exp 61\n(30 cases, pre-registered)"]
    frozen = [44.0, 36.7]
    candidate = [68.0, 66.7]
    x = range(len(labels))
    w = 0.32
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.bar([i - w / 2 for i in x], frozen, width=w, label="Frozen resolver (official)", color=FROZEN)
    ax.bar([i + w / 2 for i in x], candidate, width=w, label="Guarded candidate", color=CANDIDATE)
    for i, v in enumerate(frozen):
        ax.text(i - w / 2, v + 1.5, f"{v:g}%", ha="center", fontsize=9)
    for i, v in enumerate(candidate):
        ax.text(i + w / 2, v + 1.5, f"{v:g}%", ha="center", fontsize=9, fontweight="bold")
    ax.set_ylim(0, 85)
    ax.set_ylabel("Accuracy (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_title("Guarded candidate improves accuracy on both fresh holdouts")
    ax.legend(loc="lower right", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.02, -0.02,
              "Two independently generated holdouts, never tuned against. Safety must still be assessed\n"
              "separately -- Exp 61 found one false approval the candidate's first test (Exp 60) missed.",
              fontsize=7.5, color="#666")
    fig.tight_layout()
    fig.savefig(OUT / "exp60_61_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def safety_business_chart():
    labels = ["Safe-automation rate\n(correct, no human needed)", "False-rejection rate\n(among truly approvable claims)"]
    frozen = [42.0, 100.0]
    candidate = [66.0, 10.0]
    x = range(len(labels))
    w = 0.32
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.bar([i - w / 2 for i in x], frozen, width=w, label="Frozen resolver (official)", color=FROZEN)
    ax.bar([i + w / 2 for i in x], candidate, width=w, label="Guarded candidate", color=CANDIDATE)
    for i, v in enumerate(frozen):
        ax.text(i - w / 2, v + 2, f"{v:g}%", ha="center", fontsize=9)
    for i, v in enumerate(candidate):
        ax.text(i + w / 2, v + 2, f"{v:g}%", ha="center", fontsize=9, fontweight="bold")
    ax.set_ylim(0, 112)
    ax.set_ylabel("%")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_title("The safety/business tradeoff behind Exp 60's headline accuracy")
    ax.legend(loc="upper left", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.02, -0.03,
              "Both designs held 0 false approvals on Exp 60. The frozen resolver's 0%-FAR headline hides\n"
              "that it wrongly blocked every genuinely approvable claim (20/20) -- a real cost, not a danger.",
              fontsize=7.5, color="#666")
    fig.tight_layout()
    fig.savefig(OUT / "safety_business_tradeoff.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    accuracy_chart()
    safety_business_chart()
    print(f"Wrote {OUT / 'exp60_61_comparison.png'}")
    print(f"Wrote {OUT / 'safety_business_tradeoff.png'}")
