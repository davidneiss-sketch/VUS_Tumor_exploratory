import shutil
import tempfile
import unittest
from pathlib import Path

from test_helpers import FIXTURES_DIR, run_gate


class TestGate6Recovery(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="gate6_test_")
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)

    def test_good_fixture_passes_and_emits_simulated_named_outputs(self):
        d = FIXTURES_DIR / "gate6_good"
        outdir = Path(self._tmpdir) / "good"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate6_recovery OVERALL: PASS", r.stdout)
        self.assertTrue((outdir / "SIMULATED_RECOVERY_TABLE.tsv").exists())
        self.assertTrue((outdir / "SIMULATED_RECOVERY_TABLE.md").exists())
        md_text = (outdir / "SIMULATED_RECOVERY_TABLE.md").read_text()
        self.assertTrue(md_text.startswith("SIMULATED DATA — NOT A SCIENTIFIC RESULT"))
        self.assertIn("SIMULATED_PASS", (outdir / "SIMULATED_RECOVERY_TABLE.tsv").read_text())

    def test_bad_ci_fixture_rejects_ci_7_47_to_11_25_against_injected_4_5(self):
        """Exact ACCEPTANCE criterion: gate6 rejects a recovered CI of
        [7.47, 11.25] against an injected 4.5."""
        d = FIXTURES_DIR / "gate6_bad_ci"
        outdir = Path(self._tmpdir) / "bad_ci"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate6_recovery OVERALL: FAIL", r.stdout)
        self.assertIn("SIMULATED_FAIL", r.stdout)
        self.assertIn("[7.47, 11.25]", r.stdout)
        self.assertIn("does not contain injected value 4.5", r.stdout)
        table_text = (outdir / "SIMULATED_RECOVERY_TABLE.tsv").read_text()
        self.assertIn("SIMULATED_FAIL", table_text)

    def test_bad_estimand_fixture_rejects_or_vs_lr(self):
        """Exact ACCEPTANCE criterion: gate6 rejects an OR-vs-LR comparison."""
        d = FIXTURES_DIR / "gate6_bad_estimand"
        outdir = Path(self._tmpdir) / "bad_estimand"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("MISMATCH — AUTOMATIC FAIL", r.stdout)
        self.assertIn("truth=LR, recovered=OR", r.stdout)


if __name__ == "__main__":
    unittest.main()
