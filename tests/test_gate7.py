import unittest

from test_helpers import FIXTURES_DIR, run_gate


class TestGate7Denominators(unittest.TestCase):
    def test_good_fixture_passes(self):
        d = FIXTURES_DIR / "gate7_good"
        r = run_gate("gate7_denominators.py", "--rates-table", str(d / "rates_table.tsv"))
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate7_denominators OVERALL: PASS", r.stdout)

    def test_bad_fixture_rejects_accuracy_with_no_excluded_count(self):
        """Exact ACCEPTANCE-adjacent criterion: a reported accuracy with no
        AMBIGUOUS/excluded count is FAIL."""
        d = FIXTURES_DIR / "gate7_bad"
        r = run_gate("gate7_denominators.py", "--rates-table", str(d / "rates_table.tsv"))
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate7_denominators OVERALL: FAIL", r.stdout)
        self.assertIn("[FAIL] every row has an explicit (non-blank) excluded_count", r.stdout)
        self.assertIn("accuracy_no_denominator_disclosure", r.stdout)


if __name__ == "__main__":
    unittest.main()
