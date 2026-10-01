"""Regenerates ui/frontend/public/data/cases.json's `agent` field for all 150 cases against the real,
current guarded-agent candidate (scripts.exp60_require_tool_gate.run_candidate -- the Exp 59-61 fix with
the disposition gate), replacing the earlier Exp 52-era data. `case_id`/`split`/`case_family`/`claim`/
`ground_truth`/`frozen` are preserved unchanged (the frozen design hasn't changed; re-running it would
just spend money to reproduce the same numbers already on disk).

This is the permanent version of the export step ui/README.md previously described as "not checked in as
a permanent script (it was a one-off session task)" -- that gap is now closed.

Usage: python3 scripts/export_cases_json.py
Cost: real, paid LLM calls for every case (~$0.0015-0.002/claim observed for this candidate in
results/run_log.jsonl's EXP60_CANDIDATE/EXP61_CANDIDATE rows) -- not a dry run.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config as C, llm
from scripts.exp60_require_tool_gate import run_candidate

C.load_env()

CASES_JSON = ROOT / "ui" / "frontend" / "public" / "data" / "cases.json"


def _clean_trace(trace):
    out = []
    for step in trace or []:
        obs = step.get("observation", {}) or {}
        out.append({"tool": step["tool"], "args": step.get("args", {}), "ok": obs.get("ok"),
                    "found": obs.get("found"), "data": obs.get("data"), "error": obs.get("error")})
    return out


def main():
    cases = json.loads(CASES_JSON.read_text())
    start_spent = llm.spent()
    print(f"Already spent this session: ${start_spent:.4f}")

    for i, entry in enumerate(cases):
        raw_case = {**entry["claim"], "split": entry["split"]}
        r = run_candidate(raw_case, model=None, tag="CASES_EXPORT_V2")
        correct = r["decision"] == entry["ground_truth"]["expected_decision"]
        entry["agent"] = {
            "decision": r["decision"],
            "policy_evidence": r.get("policy_evidence", []),
            "missing_fields": r.get("missing_fields", []),
            "explanation": r.get("explanation"),
            "turns": r.get("turns"),
            "trace": _clean_trace(r.get("trace")),
            "correct": correct,
        }
        spent_now = llm.spent()
        print(f"[{i+1}/{len(cases)}] {entry['case_id']} -> {r['decision']} "
              f"({'correct' if correct else 'wrong'}) | spent so far: ${spent_now:.4f}")

    CASES_JSON.write_text(json.dumps(cases, indent=1))
    print(f"\nWrote {CASES_JSON}")
    print(f"Total spend this run: ${llm.spent() - start_spent:.4f}")


if __name__ == "__main__":
    main()
