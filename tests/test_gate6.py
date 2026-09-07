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
            "--scope", str(d / "scope.tsv"),
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
            "--scope", str(d / "scope.tsv"),
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
            "--scope", str(d / "scope.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("MISMATCH — AUTOMATIC FAIL", r.stdout)
        self.assertIn("truth=LR, recovered=OR", r.stdout)

    def test_no_scope_file_means_every_quantity_undeclared_and_fails(self):
        """Omitting --scope entirely must NOT silently pass -- every truth
        quantity is treated as undeclared, a hard failure per quantity.
        This is the exact scope bug the housekeeping fix targets: a gate
        that scores (or skips) a subset without a declared reason."""
        d = FIXTURES_DIR / "gate6_good"
        outdir = Path(self._tmpdir) / "no_scope"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate6_recovery OVERALL: FAIL", r.stdout)
        self.assertIn("UNDECLARED SCOPE", r.stdout)

    def test_scope_mixed_in_scope_out_of_scope_and_undeclared(self):
        """Every SIMULATED_TRUTH.tsv quantity must appear in the recovery
        table with a scope status: IN_SCOPE+recovered scores normally,
        declared NOT_IN_SCOPE is reported as BLOCKED (not a failure by
        itself), and an UNDECLARED quantity is a hard failure that also
        fails the whole gate -- exactly the task's three required
        outcomes in one fixture."""
        d = FIXTURES_DIR / "gate6_scope_mixed"
        outdir = Path(self._tmpdir) / "scope_mixed"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--scope", str(d / "scope.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate6_recovery OVERALL: FAIL", r.stdout)
        self.assertIn("UNDECLARED SCOPE", r.stdout)
        self.assertIn("UNDECLARED_Q", r.stdout)

        table_text = (outdir / "SIMULATED_RECOVERY_TABLE.tsv").read_text()
        rows = {line.split("\t")[0]: line for line in table_text.splitlines()[1:] if line}
        self.assertIn("IN_SCOPE_Q", rows)
        self.assertIn("SIMULATED_PASS", rows["IN_SCOPE_Q"])
        self.assertIn("IN_SCOPE", rows["IN_SCOPE_Q"])
        self.assertIn("OUT_OF_SCOPE_Q", rows)
        self.assertIn("BLOCKED", rows["OUT_OF_SCOPE_Q"])
        self.assertIn("NOT_IN_SCOPE", rows["OUT_OF_SCOPE_Q"])
        self.assertIn("UNDECLARED_Q", rows)
        self.assertIn("SIMULATED_FAIL", rows["UNDECLARED_Q"])
        self.assertIn("UNDECLARED", rows["UNDECLARED_Q"])
        # A declared-out-of-scope row must never be silently omitted from the table.
        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
