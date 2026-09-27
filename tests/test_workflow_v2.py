"""Experiment 18: unit tests for the V2 fixed workflow. Run: python -m unittest discover -s tests -v"""
import ast, sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import llm_exp, workflow_v2 as WF, tools


def dev_case(cid):
    return next(c for c in llm_exp.cases_for("DEVELOPMENT") if c["case_id"] == cid)


class NoDirectTableAccess(unittest.TestCase):
    def test_workflow_v2_never_calls_tables_directly(self):
        """Acceptance criterion: zero direct table access from workflow_v2.py. The only allowed table use is
        `tables.days_between`, a pure date helper with no enterprise data in it; every data lookup must go through
        src/tools.py's call_tool()."""
        src = Path(WF.__file__).read_text()
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        bad = [ast.dump(n)[:120] for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == "table"]
        self.assertEqual(bad, [], f"direct T.table(...) call(s) found: {bad}")
        self.assertIn("from . import tables as T", src)  # only for days_between
        self.assertNotIn("T.table(", src)


class GuardrailTests(unittest.TestCase):
    def test_step_cap_escalates_instead_of_looping(self):
        c = dev_case("X2-011")
        trace = WF.Trace(max_calls=1)
        d = WF.decide(c, trace)
        self.assertEqual(d["decision"], "ESCALATE")
        self.assertLessEqual(d["tool_calls"], 1)

    def test_deduplication_is_logged_and_effective(self):
        c = dev_case("X2-011")
        trace = WF.Trace()
        WF.decide(c, trace)
        self.assertIsInstance(trace.deduped, int)
        # calling the same lookup twice through the trace must be served from cache, not double-counted
        before = len(trace.calls)
        trace("get_employee_profile", employee_id=c["employee_id"])
        trace("get_employee_profile", employee_id=c["employee_id"])
        self.assertEqual(len(trace.calls), before)  # no new calls recorded, both served from the cache
        self.assertGreaterEqual(trace.deduped, 1)

    def test_tool_failure_escalates_rather_than_guesses(self):
        c = dev_case("X2-011")
        orig = tools.call_tool
        def failing(name, args, timeout_s=5.0):
            if name == "get_travel_request":
                return {"ok": False, "found": False, "data": None, "error": "simulated tool failure"}
            return orig(name, args, timeout_s)
        with mock.patch("src.tools.call_tool", side_effect=failing):
            d = WF.decide(c)
        self.assertEqual(d["decision"], "ESCALATE")

    def test_trace_records_latency_and_call_shape(self):
        c = dev_case("X2-011")
        trace = WF.Trace()
        WF.decide(c, trace)
        for call in trace.calls:
            self.assertEqual(set(call), {"tool", "args", "ok", "found", "data", "error", "latency_ms"})
            self.assertGreaterEqual(call["latency_ms"], 0)


class DecisionSanityTests(unittest.TestCase):
    def test_no_errors_across_all_development_claims(self):
        for c in llm_exp.cases_for("DEVELOPMENT"):
            d = WF.decide(c)
            self.assertIn(d["decision"], ("APPROVE", "REJECT", "REQUEST_INFORMATION", "ESCALATE"))
            self.assertIsInstance(d["tool_calls"], int)


if __name__ == "__main__":
    unittest.main()
