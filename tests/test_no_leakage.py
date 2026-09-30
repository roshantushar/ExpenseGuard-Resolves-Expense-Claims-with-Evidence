"""Guardrail GR-10: runtime code must never touch the private ground-truth directory or evaluator modules. Run: python -m unittest discover -s tests"""
import re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ["tools", "rules_v2", "rules_text", "hybrid_facts", "workflow_v2", "tables", "retrievers", "retrieval", "chunking", "policy", "llm", "embed", "llm_exp", "agent", "agent_tools", "agent_variants", "resolver"]
EVALUATOR = ["evaluate", "retrieval_eval"]


class NoLeakage(unittest.TestCase):
    def test_runtime_modules_do_not_reference_ground_truth(self):
        for m in RUNTIME:
            src = (ROOT / "src" / f"{m}.py").read_text()
            for bad in ("GROUND_TRUTH", "04_ground_truth", "ground_truth.jsonl", "guardrail_cases"):
                if m == "llm_exp" and bad == "GROUND_TRUTH":  # llm_exp only imports the evaluator to score after a run
                    continue
                self.assertNotIn(bad, src, f"{m}.py references {bad}")

    def test_runtime_modules_do_not_import_evaluator(self):
        for m in RUNTIME:
            src = (ROOT / "src" / f"{m}.py").read_text()
            for ev in EVALUATOR:
                if m == "llm_exp":  # orchestration module scores after the run (documented)
                    continue
                self.assertIsNone(re.search(rf"import .*\b{ev}\b|from \.{ev}|from \. import .*\b{ev}\b", src), f"{m}.py imports {ev}")

    def test_case_and_policy_files_carry_no_labels(self):
        blob = (ROOT / "ExpenseGuard_DATASET" / "02_cases" / "all_cases.jsonl").read_text()
        for bad in ("expected_decision", "required_policy_ids", "architecture_group", "independent_challenge"):
            self.assertNotIn(bad, blob)


if __name__ == "__main__":
    unittest.main()
