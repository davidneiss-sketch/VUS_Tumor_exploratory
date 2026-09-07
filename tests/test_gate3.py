import unittest

from test_helpers import FIXTURES_DIR, run_gate


class TestGate3Runtime(unittest.TestCase):
    def test_good_fixture_passes(self):
        d = FIXTURES_DIR / "gate3_good"
        r = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"))
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate3_runtime OVERALL: PASS", r.stdout)

    def test_bad_fixture_fails_on_nonzero_exit_and_runtime_floor(self):
        d = FIXTURES_DIR / "gate3_bad"
        r = run_gate("gate3_runtime.py", "--phase-log", str(d / "phase_log.tsv"))
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate3_runtime OVERALL: FAIL", r.stdout)
        self.assertIn("[FAIL] every phase exited 0", r.stdout)
        self.assertIn("copy_number_calling: exit_code=1", r.stdout)
        self.assertIn("[FAIL] every phase's per-sample runtime exceeds its floor", r.stdout)
        self.assertIn("hrd_scoring", r.stdout)


if __name__ == "__main__":
    unittest.main()
