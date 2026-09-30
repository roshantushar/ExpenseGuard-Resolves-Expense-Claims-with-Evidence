"""Central paths and settings. Ground-truth path is only for evaluator/audit code."""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v2"  # log tag only -- kept as-is for consistency with thousands of existing historical run_log.jsonl rows already tagged "v2"; not a path, not user-facing
DATA = ROOT / "ExpenseGuard_DATASET"
CASES = DATA / "02_cases"
POLICY = DATA / "01_policy_corpus"
ENTERPRISE = DATA / "03_enterprise_data"
GROUND_TRUTH = DATA / "04_ground_truth_PRIVATE"  # evaluator-only, never import from runtime code
SHARED = ROOT / "results"                        # single run log + LLM cache
RESULTS = SHARED / "current"                     # experiment outputs and plots
DOCS = ROOT / "docs"


def load_env() -> None:
    """Minimal .env reader (no dependency)."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
