"""Experiment 3: generic LLM with the claim only (no policy, no tools). Usage: python scripts/exp03_no_policy.py [SPLIT] [model ...]"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm_exp
C.load_env()
EXP = "EXP03_NO_POLICY"
split = sys.argv[1] if len(sys.argv) > 1 else "DEVELOPMENT"
models = sys.argv[2:] or [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
SYSTEM = "You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement. No company policy document is provided; use only the claim and your general knowledge.\n" + llm_exp.SCHEMA
res = {}
for m in models:
    res[m] = llm_exp.run(EXP, m, split, SYSTEM, lambda c: "CLAIM:\n" + json.dumps(llm_exp.visible(c), indent=1), config={"temperature": 0, "policy": "none", "tools": "none"})
    s = res[m][0]
    print(m, {k: s[k] for k in ("correct", "n", "false_approvals", "non_approvable", "human_review_rate", "schema_valid", "unsupported_policy_assertion_rate", "median_latency_ms", "total_tokens", "total_cost_usd")})
llm_exp.plot(EXP, split, res, "Exp 3: generic LLM, no policy")
