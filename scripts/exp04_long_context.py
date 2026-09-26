"""Experiment 4: claim + the complete policy corpus (all 12 source documents, verbatim) in one prompt.
Usage: python scripts/exp04_long_context.py [SPLIT ...]   (default: DEVELOPMENT VALIDATION)  models from .env"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C, llm, llm_exp
C.load_env()
EXP = "EXP04_LONG_CONTEXT"
splits = sys.argv[1:] or ["DEVELOPMENT", "VALIDATION"]
models = [os.environ["PAID_MODEL"], os.environ["LOCAL_MODEL"]]
CORPUS = "\n\n=====\n\n".join(p.read_text(encoding="utf-8") for p in sorted((C.POLICY / "source_documents").glob("*.md")))
SYSTEM = ("You are ExpenseGuard, a finance assistant deciding whether an employee expense claim is ready for reimbursement, using ONLY the company policy corpus below. "
          "Policies have effective dates and regions: apply the version in force on the transaction date and let regional addenda override global rules. Convert currencies only if a conversion is needed and state the assumption.\n"
          + llm_exp.SCHEMA + "\n\nCOMPANY POLICY CORPUS:\n" + CORPUS)
n_cases = sum(len(llm_exp.cases_for(s)) for s in splits)
est_in = n_cases * (len(SYSTEM) // 4 + 350)
print(f"Projected: {n_cases} cases x paid model ~{est_in/1e6:.2f}M input tokens ~ ${est_in*0.15/1e6 + n_cases*250*0.6/1e6:.3f}; spent so far ${llm.spent():.4f} of ${os.environ['MAX_BUDGET_USD']}; policy ~{len(CORPUS)//4} tokens")
for split in splits:
    res = {}
    for m in models:
        res[m] = llm_exp.run(EXP, m, split, SYSTEM, lambda c: "CLAIM:\n" + json.dumps(llm_exp.visible(c), indent=1), config={"temperature": 0, "policy": "full corpus verbatim", "policy_tokens_est": len(CORPUS) // 4})
        s = res[m][0]
        print(split, m, {k: s[k] for k in ("correct", "n", "false_approvals", "non_approvable", "human_review_rate", "schema_valid", "wrong_policy_version_cases", "decision_counts", "median_latency_ms", "total_tokens", "total_cost_usd")})
    llm_exp.plot(EXP, split, res, f"Exp 4: full-policy long context ({split.lower()})")
