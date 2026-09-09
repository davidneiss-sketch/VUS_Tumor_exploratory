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
        [7.47, 11.25] against an injected 4.5. UPDATED (P-AMD-3b,
        PROTOCOL_DEVIATIONS.md Entry 3): CI containment is no longer the
        gating reason -- it is STILL computed and reported (informational),
        but the quantity now fails on relative-bias tolerance alone
        (106.67% >> 25%). This is the exact fixture
        PROPOSED_GATE6_AMENDMENT.md computed still fails under the amended
        criterion -- if this test ever passes, the amendment is wrong."""
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
        # Containment is still COMPUTED and REPORTED (informational)...
        self.assertIn("does NOT contain injected value 4.5", r.stdout)
        # ...but the actual FAIL reason is relative bias, not containment.
        self.assertIn("relative bias 1.0667 exceeds tolerance 0.25", r.stdout)
        table_text = (outdir / "SIMULATED_RECOVERY_TABLE.tsv").read_text()
        self.assertIn("SIMULATED_FAIL", table_text)
        self.assertIn("False", table_text)  # ci_contains_injected column, reported not gating

    def test_amended_criterion_fails_bad_ci_fixture_on_relative_bias_not_containment(self):
        """The Part B regression test that decides whether the amendment is
        sound: gate6_bad_ci is the exact case that motivated building
        gate6. If the amended criterion passed it, the amendment would be
        wrong (per this task's own explicit HALT condition). It still
        fails -- on relative bias alone, since containment no longer
        gates -- confirmed explicitly here, separate from the containment
        -reporting assertions above."""
        d = FIXTURES_DIR / "gate6_bad_ci"
        outdir = Path(self._tmpdir) / "bad_ci_amended"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--scope", str(d / "scope.tsv"),
            "--outdir", str(outdir),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate6_recovery OVERALL: FAIL", r.stdout)
        table_text = (outdir / "SIMULATED_RECOVERY_TABLE.tsv").read_text()
        rows = {line.split("\t")[0]: line for line in table_text.splitlines()[1:] if line}
        self.assertIn("SIMULATED_FAIL", rows["BAD_CI_QUANTITY"])

    def test_wrong_sign_bias_fixture_fails_directional_check_within_tolerance(self):
        """New for the amendment: a quantity whose relative bias is WELL
        WITHIN the 0.25 tolerance, but whose direction is the OPPOSITE of
        what the estimator's own characterized shrinkage curve predicts,
        must FAIL -- this is exactly what the directional check exists to
        catch, since tolerance alone would pass it."""
        d = FIXTURES_DIR / "gate6_wrong_sign_bias"
        outdir = Path(self._tmpdir) / "wrong_sign"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--scope", str(d / "scope.tsv"),
            "--outdir", str(outdir),
            "--bias-prediction", str(d / "bias_prediction.tsv"),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate6_recovery OVERALL: FAIL", r.stdout)
        self.assertIn("WRONG SIGN", r.stdout)
        table_text = (outdir / "SIMULATED_RECOVERY_TABLE.tsv").read_text()
        rows = {line.split("\t")[0]: line for line in table_text.splitlines()[1:] if line}
        self.assertIn("SIMULATED_FAIL", rows["WRONG_SIGN_QUANTITY"])
        self.assertIn("FAIL", rows["WRONG_SIGN_QUANTITY"].split("\t"))  # directional_check column itself

    def test_correct_sign_within_slack_bias_fixture_passes(self):
        """Control for the wrong-sign test: the SAME magnitude of bias, but
        in the PREDICTED direction, passes -- confirms the directional
        check discriminates on sign/magnitude, not merely on the presence
        of any bias."""
        d = FIXTURES_DIR / "gate6_correct_sign_bias"
        outdir = Path(self._tmpdir) / "correct_sign"
        r = run_gate(
            "gate6_recovery.py",
            "--truth", str(d / "truth.tsv"),
            "--recovered", str(d / "recovered.tsv"),
            "--scope", str(d / "scope.tsv"),
            "--outdir", str(outdir),
            "--bias-prediction", str(d / "bias_prediction.tsv"),
        )
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate6_recovery OVERALL: PASS", r.stdout)

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
