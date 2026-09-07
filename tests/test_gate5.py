import unittest

from test_helpers import FIXTURES_DIR, run_gate


def _run_gate5(d):
    return run_gate(
        "gate5_tripwires.py",
        "--metrics", str(d / "metrics.tsv"),
        "--thresholds", str(d / "thresholds.tsv"),
        "--circularity", str(d / "circularity.tsv"),
        "--lr-table", str(d / "lr_table.tsv"),
    )


class TestGate5Tripwires(unittest.TestCase):
    def test_good_fixture_passes(self):
        r = _run_gate5(FIXTURES_DIR / "gate5_good")
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate5_tripwires OVERALL: PASS", r.stdout)

    def test_bad_fixture_flags_auc_0998(self):
        """Exact ACCEPTANCE criterion: gate5 flags an AUC of 0.998."""
        r = _run_gate5(FIXTURES_DIR / "gate5_bad")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("0.998", r.stdout)
        self.assertIn("[FAIL] no concordance/AUC-like metric exceeds ceiling", r.stdout)

    def test_bad_fixture_flags_exact_benchmark_match(self):
        """Exact ACCEPTANCE criterion: gate5 flags an exact benchmark match."""
        r = _run_gate5(FIXTURES_DIR / "gate5_bad")
        self.assertIn("exact_match_metric", r.stdout)
        self.assertIn("[FAIL] no control matches its cited benchmark within", r.stdout)

    def test_bad_fixture_flags_threshold_bias_inconsistency(self):
        r = _run_gate5(FIXTURES_DIR / "gate5_bad")
        self.assertIn("[FAIL] every derived threshold's reported bias matches its recomputed bias", r.stdout)

    def test_bad_fixture_flags_zero_circularity_exclusions(self):
        r = _run_gate5(FIXTURES_DIR / "gate5_bad")
        self.assertIn("[FAIL] no gene group has a circularity-exclusion count of zero", r.stdout)
        self.assertIn("CORE_HR", r.stdout)

    def test_bad_fixture_flags_narrow_negative_control(self):
        r = _run_gate5(FIXTURES_DIR / "gate5_bad")
        self.assertIn("[FAIL] no negative-control CI is narrower than a comparable-n", r.stdout)


if __name__ == "__main__":
    unittest.main()
