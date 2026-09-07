import unittest

from test_helpers import FIXTURES_DIR, run_gate


class TestGate3Runtime(unittest.TestCase):
    def test_good_fixture_passes_track_s(self):
        d = FIXTURES_DIR / "gate3_good"
        r = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"), "--track", "TRACK_S")
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate3_runtime OVERALL: PASS", r.stdout)

    def test_bad_fixture_fails_on_nonzero_exit_and_runtime_floor(self):
        d = FIXTURES_DIR / "gate3_bad"
        r = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"), "--track", "TRACK_S")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate3_runtime OVERALL: FAIL", r.stdout)
        self.assertIn("[FAIL] every phase exited 0", r.stdout)
        self.assertIn("copy_number_calling: exit_code=1", r.stdout)
        self.assertIn("[FAIL] every phase's per-sample runtime exceeds its floor", r.stdout)
        self.assertIn("hrd_scoring", r.stdout)

    def test_track_required(self):
        """--track has no default -- Standing Rule 4: a caller must declare
        which track a phase log represents, never silently assumed."""
        d = FIXTURES_DIR / "gate3_good"
        r = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"))
        self.assertNotEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("--track", r.stderr)

    def test_same_runtime_passes_track_s_but_fails_track_b(self):
        """The exact scenario this gate's track-conditional fix targets: a
        run that would pass the old single (Track S) floor but claims
        Track B (real exome-scale) work. copy_number_calling here is
        6 sec/sample (passes TRACK_S's 5.0 floor) and hrd_scoring is
        1.5 sec/sample (passes TRACK_S's 1.0 floor) -- both structurally
        identical to gate3_good's fixture. Under TRACK_B (floors 90.0 and
        24.0, respectively -- see GATE3.json) both must fail: this is the
        tripwire binding on the case that actually matters."""
        d = FIXTURES_DIR / "gate3_trackb_stub"

        r_s = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"), "--track", "TRACK_S")
        self.assertEqual(r_s.returncode, 0, msg=r_s.stdout + r_s.stderr)
        self.assertIn("gate3_runtime OVERALL: PASS", r_s.stdout)

        r_b = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"), "--track", "TRACK_B")
        self.assertEqual(r_b.returncode, 1, msg=r_b.stdout + r_b.stderr)
        self.assertIn("gate3_runtime OVERALL: FAIL", r_b.stdout)
        self.assertIn("[FAIL] every phase's per-sample runtime exceeds its floor", r_b.stdout)
        self.assertIn("copy_number_calling", r_b.stdout)
        self.assertIn("hrd_scoring", r_b.stdout)

    def test_track_b_signature_assignment_is_unverified_and_blocks(self):
        """Per Standing Rule 3, signature_assignment has no verified TRACK_B
        floor (no usable SigProfilerAssignment per-exome runtime citation
        was found -- see GATE3.json). A TRACK_B phase log including it must
        fail this gate outright, regardless of how plausible its runtime
        looks, rather than silently passing or falling back to TRACK_S."""
        d = FIXTURES_DIR / "gate3_trackb_unverified"
        r = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"), "--track", "TRACK_B")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate3_runtime OVERALL: FAIL", r.stdout)
        self.assertIn("no phase relies on an UNVERIFIED TRACK_B floor", r.stdout)
        self.assertIn("signature_assignment", r.stdout)
        self.assertIn("UNVERIFIED", r.stdout)


if __name__ == "__main__":
    unittest.main()
