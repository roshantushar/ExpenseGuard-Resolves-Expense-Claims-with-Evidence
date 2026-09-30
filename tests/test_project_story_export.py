"""Tests for scripts/export_project_story.py -- the canonical data source for the Project Story UI
tab. These are regression checks against known-correct values already verified by hand against the
underlying result files; if a real experiment result changes, these tests should change with it (not be
adjusted to make a wrong number pass). Run: python -m unittest discover -s tests"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_project_story", ROOT / "scripts/export_project_story.py")
export_project_story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_project_story)


class DatasetStats(unittest.TestCase):
    def test_split_sizes_from_real_ground_truth(self):
        gt = [json.loads(l) for l in open(ROOT / "ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")]
        stats = export_project_story.dataset_stats(gt)
        self.assertEqual(stats["total"], 150)
        self.assertEqual(stats["development"], 70)
        self.assertEqual(stats["validation"], 30)
        self.assertEqual(stats["final_test"], 50)

    def test_counts_a_synthetic_list_correctly(self):
        rows = [{"split": "DEVELOPMENT"}] * 2 + [{"split": "VALIDATION"}] * 1 + [{"split": "FINAL_TEST"}] * 3
        stats = export_project_story.dataset_stats(rows)
        self.assertEqual(stats, {"total": 6, "development": 2, "validation": 1, "final_test": 3})


class Exp32Official(unittest.TestCase):
    def test_matches_the_frozen_final_test_summary(self):
        summary = json.load(open(ROOT / "results/current/final_test/exp32_final_test/summary.json"))
        out = export_project_story.exp32_official(summary)
        self.assertEqual(out["n"], 50)
        self.assertEqual(out["correct"], 30)
        self.assertEqual(out["accuracy_pct"], 60.0)
        self.assertEqual(out["false_approvals"], 0)
        self.assertEqual(out["non_approvable"], 37)
        self.assertEqual(out["far_pct"], 0.0)

    def test_returns_none_when_summary_missing(self):
        self.assertIsNone(export_project_story.exp32_official(None))


class PathPerformance(unittest.TestCase):
    def test_deterministic_22_of_22_and_residual_8_of_28_on_final_test(self):
        gt = {json.loads(l)["case_id"]: json.loads(l) for l in open(ROOT / "ExpenseGuard_DATASET/04_ground_truth_PRIVATE/ground_truth.jsonl")}
        preds = [json.loads(l) for l in open(ROOT / "results/current/final_test/exp32_final_test/predictions.jsonl")]
        out = export_project_story.path_performance(preds, gt)
        self.assertEqual(out["deterministic"], {"correct": 22, "n": 22})
        self.assertEqual(out["llm_residual"], {"correct": 8, "n": 28})
        self.assertEqual(out["approve_recall"], {"correct": 0, "n": 13})


class Exp33FailureBreakdown(unittest.TestCase):
    def test_20_errors_sum_correctly_not_the_old_18_count(self):
        """Regression guard: an earlier, incorrect summary claimed 9+5+4=18. The real classification
        file has 5 categories summing to 20 (7+5+4+2+2), which this test locks in."""
        out = export_project_story.exp33_failure_breakdown(
            ROOT / "results/current/final_test/exp33_failure_analysis/failure_classification.csv")
        self.assertEqual(out["total_errors"], 20)
        self.assertEqual(sum(out["categories"].values()), 20)
        self.assertEqual(out["categories"]["policy_reasoning_composition"], 7)
        self.assertEqual(out["categories"]["missing_information_confusion"], 5)
        self.assertEqual(out["categories"]["resolved_fact_error"], 4)
        self.assertEqual(out["categories"]["missed_escalation"], 2)
        self.assertEqual(out["categories"]["over_conservative_bias"], 2)

    def test_returns_none_when_file_missing(self):
        self.assertIsNone(export_project_story.exp33_failure_breakdown(ROOT / "does/not/exist.csv"))


class ArchitectureComparison(unittest.TestCase):
    def test_fixed_workflow_vs_selective_resolver_on_dev(self):
        out = export_project_story.exp18_vs_exp30_vs_llm_only()
        self.assertEqual(out["fixed_workflow"]["accuracy_pct"], 64.3)
        self.assertEqual(out["fixed_workflow"]["far_pct"], 13.5)
        self.assertEqual(out["selective_resolver"]["accuracy_pct"], 61.4)
        self.assertEqual(out["selective_resolver"]["far_pct"], 0.0)


class GuardedCandidate(unittest.TestCase):
    def test_dev_and_validation_confirmed_numbers(self):
        out = export_project_story.guarded_candidate()
        self.assertEqual(out["development"]["correct"], 44)
        self.assertEqual(out["development"]["n"], 70)
        self.assertEqual(out["development"]["far_pct"], 0.0)
        self.assertEqual(out["validation"]["correct"], 21)
        self.assertEqual(out["validation"]["n"], 30)
        self.assertEqual(out["validation"]["far_pct"], 0.0)


class GeneratedExportFile(unittest.TestCase):
    """Confirms the exporter can run end to end and produce the file the UI actually fetches, and that
    it never touches or requires write access to the frozen final-test artifacts."""
    def test_main_writes_a_well_formed_json_file(self):
        export_project_story.main()
        out_path = ROOT / "ui/frontend/public/data/project_story.json"
        self.assertTrue(out_path.exists())
        data = json.loads(out_path.read_text())
        self.assertEqual(data["dataset"]["total"], 150)
        self.assertEqual(data["exp32_official"]["correct"], 30)

    def test_frozen_final_test_artifacts_are_never_written_by_this_module(self):
        src = (ROOT / "scripts/export_project_story.py").read_text()
        self.assertNotIn("final_test/exp32_final_test/predictions.jsonl\", \"w", src)
        self.assertNotIn("open(str(ROOT) + \"/results/current/final_test", src)


if __name__ == "__main__":
    unittest.main()
