import unittest

from test_helpers import FIXTURES_DIR, run_gate


class TestGate4Statistics(unittest.TestCase):
    def test_good_fixture_passes(self):
        d = FIXTURES_DIR / "gate4_good"
        r = run_gate("gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"))
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate4_statistics OVERALL: PASS", r.stdout)

    def test_bad_fixture_rejects_ci_excluding_its_own_estimate(self):
        """Exact ACCEPTANCE criterion: gate4 rejects a table with a CI
        excluding its estimate."""
        d = FIXTURES_DIR / "gate4_bad"
        r = run_gate("gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"))
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate4_statistics OVERALL: FAIL", r.stdout)
        self.assertIn("[FAIL] every bootstrap CI contains its own point estimate", r.stdout)
        self.assertIn("does not contain point estimate", r.stdout)


if __name__ == "__main__":
    unittest.main()
