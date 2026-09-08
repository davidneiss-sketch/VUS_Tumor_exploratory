import shutil
import tempfile
import unittest
from pathlib import Path

from test_helpers import FIXTURES_DIR, run_gate


class TestGate8IntervalInformativeness(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="gate8_test_")
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)

    def test_good_fixture_passes_and_emits_simulated_named_outputs(self):
        d = FIXTURES_DIR / "gate8_good"
        outdir = Path(self._tmpdir) / "good"
        r = run_gate(
            "gate8_interval_informativeness.py",
            "--table", str(d / "table.tsv"),
            "--id-cols", "arm,feature_subset,n_scenario",
            "--point-col", "point_estimate",
            "--ci-low-col", "ci_low",
            "--ci-high-col", "ci_high",
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate8_interval_informativeness OVERALL: PASS", r.stdout)
        out = outdir / "SIMULATED_GATE8_INTERVAL_REPORT.tsv"
        self.assertTrue(out.exists())
        text = out.read_text()
        self.assertIn("INFORMATIVE", text)
        self.assertIn("NOT_APPLICABLE", text)  # the INSUFFICIENT_N-style blank row
        self.assertNotIn("UNINFORMATIVE", text)  # UNINFORMATIVE would match, but so would the substring
        # of NOT_APPLICABLE-adjacent text -- confirm no row's gate8_status is literally UNINFORMATIVE
        self.assertNotIn("\tUNINFORMATIVE\t", text)

    def test_bad_fixture_reproduces_and_rejects_the_3_65_billion_row(self):
        """Exact ACCEPTANCE criterion: gate8 rejects the row this task's
        own trigger described -- CI=[759.6, 3.65 BILLION], which
        PROTOCOL.md §9's CI-lower-bound rule alone would read as
        PATHOGENIC_VERY_STRONG (the maximum ACMG tier)."""
        d = FIXTURES_DIR / "gate8_bad"
        outdir = Path(self._tmpdir) / "bad"
        r = run_gate(
            "gate8_interval_informativeness.py",
            "--table", str(d / "table.tsv"),
            "--id-cols", "arm,feature_subset,n_scenario",
            "--point-col", "point_estimate",
            "--ci-low-col", "ci_low",
            "--ci-high-col", "ci_high",
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate8_interval_informativeness OVERALL: FAIL", r.stdout)
        self.assertIn("UNINFORMATIVE", r.stdout)
        table_text = (outdir / "SIMULATED_GATE8_INTERVAL_REPORT.tsv").read_text()
        self.assertIn("DDR_SIGNALING/LOH_GIS_SBS3/REALISTIC_N_35", table_text)
        self.assertIn("3645407853.257834", table_text)
        self.assertIn("exceeds ABSOLUTE_UPPER_CEILING", table_text)
        self.assertIn("exceeding MAX_UPPER_POINT_RATIO", table_text)
        # the well-behaved second row in the same fixture must still pass,
        # proving gate8 evaluates rows independently rather than failing
        # the whole table indiscriminately once one row is bad
        self.assertIn("CORE_HR/LOH_GIS_SBS3/SYNTHETIC_FULL_N\t101.240291\t71.274566\t158.671059\t1\t1.5673\tPATHOGENIC_STRONG\tINFORMATIVE",
                       table_text)

    def test_tier_span_alone_can_reject_a_narrower_but_still_ambiguous_interval(self):
        """A CI that never gets numerically absurd (upper/point ratio and
        absolute ceiling both fine) can still be UNINFORMATIVE purely by
        spanning too many ACMG tiers -- the two checks are independent,
        per this task's own instruction ('FAIL any row... OR... FAIL any
        row...')."""
        d = Path(self._tmpdir) / "tier_span_fixture"
        d.mkdir()
        # SUPPORTING (2.08,4.33] up through VERY_STRONG (>350): spans 4
        # tiers, crosses 3 boundaries -- but point=100, ci_high=400 is
        # only a 4x ratio and well under the absolute ceiling, so this
        # row would pass the ratio/ceiling checks and must be caught by
        # tier span alone.
        (d / "table.tsv").write_text(
            "row\tpoint_estimate\tci_low\tci_high\n"
            "wide_span_only\t100.0\t3.0\t400.0\n"
        )
        outdir = Path(self._tmpdir) / "tier_span_out"
        r = run_gate(
            "gate8_interval_informativeness.py",
            "--table", str(d / "table.tsv"),
            "--id-cols", "row",
            "--point-col", "point_estimate",
            "--ci-low-col", "ci_low",
            "--ci-high-col", "ci_high",
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        table_text = (outdir / "SIMULATED_GATE8_INTERVAL_REPORT.tsv").read_text()
        self.assertIn("UNINFORMATIVE", table_text)
        self.assertIn("spans", table_text)
        self.assertIn("exceeding MAX_TIERS_SPANNED", table_text)
        self.assertNotIn("exceeding MAX_UPPER_POINT_RATIO", table_text)
        self.assertNotIn("exceeds ABSOLUTE_UPPER_CEILING", table_text)


if __name__ == "__main__":
    unittest.main()
