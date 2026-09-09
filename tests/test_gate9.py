import shutil
import tempfile
import unittest
from pathlib import Path

from test_helpers import FIXTURES_DIR, run_gate


class TestGate9Imbalance(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="gate9_test_")
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)

    def test_good_fixture_passes_and_emits_simulated_named_outputs(self):
        d = FIXTURES_DIR / "gate9_good"
        outdir = Path(self._tmpdir) / "good"
        r = run_gate(
            "gate9_imbalance.py",
            "--table", str(d / "table.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate9_imbalance OVERALL: PASS", r.stdout)
        out = outdir / "SIMULATED_GATE9_IMBALANCE_REPORT.tsv"
        self.assertTrue(out.exists())
        text = out.read_text()
        self.assertIn("CORE_HR_SIM", text)
        self.assertIn("DDR_SIGNALING_SIM", text)
        self.assertIn("True", text)  # stable_within_tolerance
        self.assertNotIn("\tFalse\n", text)

    def test_bad_fixture_reproduces_and_rejects_an_uncorrected_prior_odds_conversion(self):
        """Exact ACCEPTANCE criterion: gate9 rejects a reference-set
        class-imbalance sweep whose recovered LR scales roughly linearly
        with the imbalance ratio -- the exact signature of an uncorrected
        (or double-corrected) prior-odds conversion, the mechanism this
        task's own text names as 'what broke v2'."""
        d = FIXTURES_DIR / "gate9_bad"
        outdir = Path(self._tmpdir) / "bad"
        r = run_gate(
            "gate9_imbalance.py",
            "--table", str(d / "table.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate9_imbalance OVERALL: FAIL", r.stdout)
        self.assertIn("exceeds tolerance", r.stdout)
        self.assertIn("CORE_HR_UNCORRECTED", r.stdout)

    def test_missing_ratio_coverage_fails(self):
        """A test_case missing one of the 3 required ratios cannot
        support the invariance claim at all -- must fail loudly, not
        silently pass on partial coverage."""
        d = Path(self._tmpdir) / "incomplete_fixture"
        d.mkdir()
        (d / "table.tsv").write_text(
            "test_case\tclass_ratio_label\tn_pathogenic_ref\tn_benign_ref\trecovered_lr\treplicate_index\n"
            "CORE_HR_PARTIAL\t1:1\t300\t300\t8.0\t0\n"
            "CORE_HR_PARTIAL\t1:5\t60\t300\t8.1\t0\n"
        )
        outdir = Path(self._tmpdir) / "incomplete_out"
        r = run_gate(
            "gate9_imbalance.py",
            "--table", str(d / "table.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate9_imbalance OVERALL: FAIL", r.stdout)
        self.assertIn("missing ratio label", r.stdout)
        self.assertIn("1:20", r.stdout)


if __name__ == "__main__":
    unittest.main()
