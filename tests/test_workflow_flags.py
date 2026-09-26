"""Freeze-time checks: the escalate branch and the currency-ambiguity flag. Run: python -m unittest discover -s tests"""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import flags, workflow, config as C


def case(cid):
    return next(json.loads(l) for l in (C.CASES / "all_cases.jsonl").read_text().splitlines() if f'"{cid}"' in l)


class Freeze(unittest.TestCase):
    def test_over_ceiling_hotel_without_exception_or_conference_escalates(self):
        for cid in ("EXP-0120", "EXP-0111", "EXP-0114"):
            d = workflow.run(case(cid))
            self.assertEqual(d["decision"], "ESCALATE", cid)
            self.assertIn("GEP26-4.1", d["policy_evidence"])

    def test_invalid_or_expired_exception_still_rejects(self):
        self.assertEqual(workflow.run(case("EXP-0110"))["decision"], "REJECT")   # expired exception
        self.assertEqual(workflow.run(case("EXP-0109"))["decision"], "REJECT")   # conference not registered

    def test_currency_flag(self):
        for cid in ("EXP-0082", "EXP-0085", "EXP-0086", "EXP-0089", "EXP-0098", "EXP-0104"):
            self.assertTrue(flags.currency_ambiguous(case(cid)), cid)
        for cid in ("EXP-0084", "EXP-0001", "EXP-0091", "EXP-0075"):              # SGD claims and ordinary JPY/INR claims are not flagged
            self.assertFalse(flags.currency_ambiguous(case(cid)), cid)


if __name__ == "__main__":
    unittest.main()
