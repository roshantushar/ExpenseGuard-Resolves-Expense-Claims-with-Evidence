"""Central paths and settings. Ground-truth path is only for evaluator/audit code."""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = os.environ.get("EG_DATASET", "v2")  # "v2" (harder dataset, default) or "v1" (original, frozen)
DATA = ROOT / ("ExpenseGuard_V2_DATASET" if VERSION == "v2" else "ExpenseGuard_FINAL_CURRENT_DATASET")
CASES = DATA / "02_cases"
POLICY = DATA / "01_policy_corpus"
ENTERPRISE = DATA / "03_enterprise_data"
GROUND_TRUTH = DATA / "04_ground_truth_PRIVATE"  # evaluator-only, never import from runtime code
SHARED = ROOT / "results"                                  # single run log + LLM cache are shared across dataset versions
RESULTS = SHARED / "v2" if VERSION == "v2" else SHARED     # per-version experiment outputs and plots
DOCS = ROOT / "docs" / "v2" if VERSION == "v2" else ROOT / "docs"


def load_env() -> None:
    """Minimal .env reader (no dependency)."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
