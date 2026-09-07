import unittest

from test_helpers import FIXTURES_DIR, run_gate


class TestGate2DataReality(unittest.TestCase):
    def test_good_fixture_passes(self):
        d = FIXTURES_DIR / "gate2_good"
        r = run_gate(
            "gate2_data_reality.py",
            "--manifest", str(d / "manifest.tsv"),
            "--provenance", str(d / "provenance.tsv"),
            "--analyzed", str(d / "analyzed.tsv"),
            "--claimed-count", "1",
        )
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate2_data_reality OVERALL: PASS", r.stdout)

    def test_bad_fixture_fails_on_md5_mismatch_and_untraced_sample(self):
        d = FIXTURES_DIR / "gate2_bad"
        r = run_gate(
            "gate2_data_reality.py",
            "--manifest", str(d / "manifest.tsv"),
            "--provenance", str(d / "provenance.tsv"),
            "--analyzed", str(d / "analyzed.tsv"),
            "--claimed-count", "1",
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate2_data_reality OVERALL: FAIL", r.stdout)
        self.assertIn("md5", r.stdout.lower())
        self.assertIn("[FAIL] every raw file's on-disk size/md5/header matches its provenance record", r.stdout)
        self.assertIn("SAMPLE_GHOST", r.stdout)
        self.assertIn("[FAIL] every analyzed sample traces to a provenance row", r.stdout)


if __name__ == "__main__":
    unittest.main()
