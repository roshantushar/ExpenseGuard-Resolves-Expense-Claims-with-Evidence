"""Experiment 17: unit tests for the typed read-only tools. Run: python -m unittest discover -s tests -v"""
import json, sys, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import tools


class ToolTests(unittest.TestCase):
    def test_valid_calls_return_compact_json(self):
        r = tools.call_tool("get_employee_profile", {"employee_id": "E0001"})
        self.assertTrue(r["ok"] and r["found"]); self.assertEqual(r["data"]["grade"], "G3"); json.dumps(r)
        self.assertTrue(tools.call_tool("get_project_status", {"project_id": "PRJ-001"})["found"])
        self.assertTrue(tools.call_tool("get_exception_record", {"exception_id": "EXC-WF-002"})["found"])
        self.assertTrue(tools.call_tool("get_conference_registration", {"event_id": "CONF-000"})["found"])
        self.assertTrue(tools.call_tool("get_merchant_metadata", {"merchant_name": "Grand Harbour Hotel"})["found"])
        self.assertTrue(tools.call_tool("get_manager_approval", {"expense_id": "EXP-0084"})["found"])
        self.assertTrue(tools.call_tool("get_travel_request", {"employee_id": "E0171", "date": "2026-03-01"})["found"])
        self.assertTrue(tools.call_tool("search_previous_expenses", {"employee_id": "E0013", "merchant": "Sakura Grill"})["found"])

    def test_missing_records_are_clear_not_found(self):
        for name, args in [("get_employee_profile", {"employee_id": "E9999"}), ("get_exception_record", {"exception_id": "EXC-XX-999"}),
                           ("get_conference_registration", {"event_id": "CONF-999"}), ("get_manager_approval", {"expense_id": "EXP-9999"}),
                           ("get_travel_request", {"employee_id": "E0001", "date": "2000-01-01"})]:
            r = tools.call_tool(name, args)
            self.assertTrue(r["ok"] and not r["found"] and r["data"] is None and r["error"] is None, name)

    def test_invalid_identifiers_rejected(self):
        for name, args in [("get_employee_profile", {"employee_id": "bob"}), ("get_project_status", {"project_id": "PRJ-1"}), ("get_travel_request", {"employee_id": "E0001", "date": "yesterday"})]:
            r = tools.call_tool(name, args)
            self.assertFalse(r["ok"]); self.assertIn("invalid format", r["error"])

    def test_malformed_arguments_rejected(self):
        self.assertFalse(tools.call_tool("get_employee_profile", {})["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", {"employee_id": "E0001", "x": "1"})["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", {"employee_id": 1})["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", "E0001")["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", {"employee_id": ""})["ok"])

    def test_unknown_tool(self):
        r = tools.call_tool("delete_expense", {"expense_id": "EXP-0001"})
        self.assertFalse(r["ok"]); self.assertIn("unknown tool", r["error"])

    def test_timeout(self):
        orig = tools.TOOLS["get_employee_profile"]
        tools.TOOLS["get_employee_profile"] = (lambda employee_id: time.sleep(1), *orig[1:])
        try:
            r = tools.call_tool("get_employee_profile", {"employee_id": "E0001"}, timeout_s=0.1)
        finally:
            tools.TOOLS["get_employee_profile"] = orig
        self.assertEqual(r["error"], "timeout")

    def test_empty_search_result(self):
        r = tools.call_tool("search_previous_expenses", {"employee_id": "E0001", "merchant": "No Such Merchant"})
        self.assertTrue(r["ok"] and not r["found"] and r["data"] is None)

    def test_response_schema(self):
        for r in (tools.call_tool("get_employee_profile", {"employee_id": "E0001"}), tools.call_tool("nope", {})):
            self.assertEqual(set(r), {"ok", "found", "data", "error"})

    def test_all_tools_read_only_and_have_descriptions(self):
        for name, (fn, req, opt, desc) in tools.TOOLS.items():
            self.assertTrue(name.startswith(("get_", "search_")), name); self.assertGreater(len(desc), 30)

    def test_no_ground_truth_access(self):
        src = (Path(tools.__file__)).read_text()
        for bad in ("GROUND_TRUTH", "04_ground_truth", "hidden", "expected_decision"):
            self.assertNotIn(bad, src)
        blob = json.dumps([tools.call_tool("get_manager_approval", {"expense_id": "EXP-0084"}), tools.call_tool("get_exception_record", {"exception_id": "EXC-WF-002"})])
        for bad in ("expected_", "case_family", "architecture_group"):
            self.assertNotIn(bad, blob)


if __name__ == "__main__":
    unittest.main()
