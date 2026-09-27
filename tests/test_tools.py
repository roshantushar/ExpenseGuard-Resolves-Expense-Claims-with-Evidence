"""Experiment 17: unit tests for the typed read-only tools. Run: python -m unittest discover -s tests -v"""
import json, sys, time, unittest
from unittest import mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import tools


class ToolTests(unittest.TestCase):
    def test_valid_calls_return_compact_json(self):
        r = tools.call_tool("get_employee_profile", {"employee_id": "E0001"})
        self.assertTrue(r["ok"] and r["found"]); self.assertEqual(r["data"]["employee_id"], "E0001"); self.assertIn("grade", r["data"]); json.dumps(r)
        self.assertTrue(tools.call_tool("get_project_status", {"project_id": "PRJ-001"})["found"])
        self.assertTrue(tools.call_tool("get_exception_record", {"exception_id": "EXC-0001"})["found"])
        self.assertTrue(tools.call_tool("get_conference_registration", {"event_id": "CONF-001"})["found"])
        self.assertTrue(tools.call_tool("get_manager_approval", {"expense_id": "X2-143"})["found"])
        self.assertTrue(tools.call_tool("get_travel_request", {"employee_id": "E0060", "date": "2025-06-17"})["found"])
        self.assertTrue(tools.call_tool("search_previous_expenses", {"employee_id": "E0091"})["found"])
        self.assertTrue(tools.call_tool("get_approval_delegation", {"delegation_id": "DEL-001"})["found"])
        self.assertTrue(tools.call_tool("get_cost_centre_budget", {"cost_centre": "CC-S01", "year": "2026"})["found"])

    def test_missing_records_are_clear_not_found(self):
        for name, args in [("get_employee_profile", {"employee_id": "E9999"}), ("get_exception_record", {"exception_id": "EXC-9999"}),
                           ("get_conference_registration", {"event_id": "CONF-999"}), ("get_manager_approval", {"expense_id": "X2-999"}),
                           ("get_travel_request", {"employee_id": "E0001", "date": "2000-01-01"}), ("get_approval_delegation", {"delegation_id": "DEL-999"})]:
            r = tools.call_tool(name, args)
            self.assertTrue(r["ok"] and not r["found"] and r["data"] is None and r["error"] is None, name)

    def test_invalid_identifiers_rejected(self):
        for name, args in [("get_employee_profile", {"employee_id": "bob"}), ("get_project_status", {"project_id": "PRJ-1"}),
                           ("get_travel_request", {"employee_id": "E0001", "date": "yesterday"}), ("get_approval_delegation", {"delegation_id": "delegation-1"})]:
            r = tools.call_tool(name, args)
            self.assertFalse(r["ok"]); self.assertIn("format", r["error"])

    def test_malformed_arguments_rejected(self):
        self.assertFalse(tools.call_tool("get_employee_profile", {})["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", {"employee_id": "E0001", "x": "1"})["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", {"employee_id": 1})["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", "E0001")["ok"])
        self.assertFalse(tools.call_tool("get_employee_profile", {"employee_id": ""})["ok"])

    def test_unknown_tool(self):
        r = tools.call_tool("delete_expense", {"expense_id": "X2-001"})
        self.assertFalse(r["ok"]); self.assertIn("unknown tool", r["error"])

    def test_timeout(self):
        orig = tools.TOOLS["get_employee_profile"]
        tools.TOOLS["get_employee_profile"] = (lambda employee_id: time.sleep(1), orig[1], orig[2])
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
        for name, (fn, spec, desc) in tools.TOOLS.items():
            self.assertTrue(name.startswith(("get_", "search_", "validate_")), name); self.assertGreater(len(desc), 30)

    def test_no_ground_truth_access(self):
        src = (Path(tools.__file__)).read_text()
        for bad in ("GROUND_TRUTH", "04_ground_truth", "hidden", "expected_decision"):
            self.assertNotIn(bad, src)
        blob = json.dumps([tools.call_tool("get_manager_approval", {"expense_id": "X2-143"}), tools.call_tool("get_exception_record", {"exception_id": "EXC-0001"})])
        for bad in ("expected_", "case_family", "architecture_group"):
            self.assertNotIn(bad, blob)


class ValidateApprovalTests(unittest.TestCase):
    """Fixtures for validate_approval, the resolved business-fact tool. Each patches only src/tables.table so the test is
    independent of what the current synthetic dataset happens to contain."""
    APPR = {"approval_id": "APR-TEST", "expense_id": "X2-999", "employee_id": "E0001", "manager_id": "M001", "approval_type": "TRAVEL",
            "status": "APPROVED", "approver_level": "MANAGER", "start_date": "2025-01-01", "end_date": "2025-12-31", "delegation_id": ""}
    DELEG = {"delegation_id": "DEL-TEST", "manager_id": "M001", "delegate_id": "E0002", "delegate_level": "MANAGER",
             "start_date": "2025-01-01", "end_date": "2025-12-31", "max_amount_sgd": "1000.0", "status": "ACTIVE"}

    def _tables(self, approvals=(), delegations=()):
        def table(name):
            return {"manager_approvals": list(approvals), "approval_delegations": list(delegations)}.get(name, [])
        return table

    def _call(self, approvals=(), delegations=(), **kw):
        args = {"expense_id": "X2-999", "required_level": "MANAGER", "required_types": ["TRAVEL"], "transaction_date": "2025-06-01", "amount_sgd": 500.0}
        args.update(kw)
        with mock.patch("src.tables.table", side_effect=self._tables(approvals, delegations)):
            return tools.call_tool("validate_approval", args)

    def test_valid_approval(self):
        r = self._call(approvals=[self.APPR])
        self.assertTrue(r["data"]["valid"]); self.assertEqual(r["data"]["reason_code"], "VALID")

    def test_expired_approval(self):
        r = self._call(approvals=[{**self.APPR, "start_date": "2024-01-01", "end_date": "2024-12-31"}])
        self.assertFalse(r["data"]["valid"]); self.assertEqual(r["data"]["reason_code"], "OUTSIDE_DATE_RANGE")

    def test_wrong_approval_type(self):
        r = self._call(approvals=[{**self.APPR, "approval_type": "SOFTWARE"}], required_types=["TRAVEL"])
        self.assertFalse(r["data"]["valid"]); self.assertEqual(r["data"]["reason_code"], "WRONG_APPROVAL_TYPE")

    def test_insufficient_authority(self):
        r = self._call(approvals=[{**self.APPR, "approver_level": "MANAGER"}], required_level="DIRECTOR")
        self.assertFalse(r["data"]["valid"]); self.assertEqual(r["data"]["reason_code"], "INSUFFICIENT_AUTHORITY_LEVEL")

    def test_valid_delegation(self):
        r = self._call(approvals=[{**self.APPR, "status": "DELEGATED", "delegation_id": "DEL-TEST"}], delegations=[self.DELEG])
        self.assertTrue(r["data"]["delegation_used"]); self.assertTrue(r["data"]["delegation_valid"]); self.assertTrue(r["data"]["valid"])

    def test_expired_delegation(self):
        r = self._call(approvals=[{**self.APPR, "status": "DELEGATED", "delegation_id": "DEL-TEST"}],
                        delegations=[{**self.DELEG, "start_date": "2024-01-01", "end_date": "2024-06-01"}])
        self.assertTrue(r["data"]["delegation_used"]); self.assertFalse(r["data"]["delegation_valid"]); self.assertEqual(r["data"]["reason_code"], "DELEGATION_INVALID")

    def test_delegation_over_limit(self):
        r = self._call(approvals=[{**self.APPR, "status": "DELEGATED", "delegation_id": "DEL-TEST"}], delegations=[self.DELEG], amount_sgd=5000.0)
        self.assertTrue(r["data"]["delegation_valid"]); self.assertFalse(r["data"]["valid"]); self.assertEqual(r["data"]["reason_code"], "DELEGATION_LIMIT_OR_LEVEL")

    def test_no_approval_found(self):
        r = self._call(approvals=[])
        self.assertFalse(r["data"]["approval_present"]); self.assertFalse(r["data"]["valid"]); self.assertEqual(r["data"]["reason_code"], "NO_APPROVAL_ON_FILE")

    def test_malformed_date_rejected(self):
        r = self._call(transaction_date="01/06/2025")
        self.assertFalse(r["ok"])

    def test_malformed_required_types_rejected(self):
        r = self._call(required_types="TRAVEL")  # must be a list, not a bare string
        self.assertFalse(r["ok"])

    def test_underlying_record_missing_is_not_an_error(self):
        r = self._call(approvals=[])
        self.assertTrue(r["ok"])  # absence is a resolved fact (NO_APPROVAL_ON_FILE), not a tool error

    def test_irrelevant_field_changes_do_not_change_the_verdict(self):
        """The tool must return a business fact, not merely repackage the row: changing a field the policy does not care
        about (manager_id, approval_id) must not change the resolved validity."""
        r1 = self._call(approvals=[self.APPR])
        r2 = self._call(approvals=[{**self.APPR, "approval_id": "APR-DIFFERENT", "manager_id": "M999"}])
        self.assertEqual(r1["data"]["valid"], r2["data"]["valid"]); self.assertEqual(r1["data"]["reason_code"], r2["data"]["reason_code"])


if __name__ == "__main__":
    unittest.main()
