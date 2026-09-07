import unittest

from test_helpers import FIXTURES_DIR, REPO_ROOT, run_gate


class TestGate4Statistics(unittest.TestCase):
    def test_good_fixture_passes(self):
        d = FIXTURES_DIR / "gate4_good"
        r = run_gate("gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"))
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("gate4_statistics OVERALL: PASS", r.stdout)
        self.assertIn("read live from", r.stdout)

    def test_bad_fixture_rejects_ci_excluding_its_own_estimate(self):
        """Exact ACCEPTANCE criterion: gate4 rejects a table with a CI
        excluding its estimate."""
        d = FIXTURES_DIR / "gate4_bad"
        r = run_gate("gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"))
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate4_statistics OVERALL: FAIL", r.stdout)
        self.assertIn("[FAIL] every bootstrap CI contains its own point estimate", r.stdout)
        self.assertIn("does not contain point estimate", r.stdout)

    def test_replicate_count_is_read_from_protocol_not_hardcoded(self):
        """The task's exact fix: gate4 must read B from PROTOCOL.md rather
        than a hardcoded 2000, and fail if PROTOCOL.md's B and the LR
        table's own n_replicates disagree -- proving this isn't just a
        renamed hardcoded default. This fixture's n_replicates=500 must be
        rejected against the REAL repo PROTOCOL.md's B=2000, using no
        --expected-replicates override at all."""
        d = FIXTURES_DIR / "gate4_replicate_mismatch"
        r = run_gate("gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"))
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("gate4_statistics OVERALL: FAIL", r.stdout)
        self.assertIn("n_replicates=500 != expected 2000", r.stdout)

    def test_missing_protocol_file_fails_loudly_not_silently_defaulted(self):
        """Standing Rule 4: no PROTOCOL.md to read means this gate cannot
        derive an expected replicate count at all -- that must fail loudly,
        never silently fall back to a hardcoded 2000."""
        d = FIXTURES_DIR / "gate4_good"
        r = run_gate(
            "gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"),
            "--protocol", str(REPO_ROOT / "PROTOCOL_DOES_NOT_EXIST.md"),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("PROTOCOL.md not found", r.stdout)

    def test_protocol_internal_disagreement_fails_loudly(self):
        """If PROTOCOL.md itself states two different B values, that is a
        protocol authoring bug this gate must surface, not silently
        resolve by picking the first/last match."""
        d = FIXTURES_DIR / "gate4_good"
        protocol = FIXTURES_DIR / "gate4_protocol_disagrees" / "PROTOCOL.md"
        r = run_gate(
            "gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"),
            "--protocol", str(protocol),
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("PROTOCOL.md itself disagrees about B", r.stdout)
        self.assertIn("[2000, 5000]", r.stdout)

    def test_explicit_override_disagreeing_with_protocol_fails(self):
        """A caller cannot silently override PROTOCOL.md's own B via
        --expected-replicates -- an explicit value that disagrees with the
        real PROTOCOL.md (B=2000) must itself be a hard failure."""
        d = FIXTURES_DIR / "gate4_good"
        r = run_gate(
            "gate4_statistics.py", "--lr-table", str(d / "lr_table.tsv"),
            "--expected-replicates", "999",
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("disagrees with PROTOCOL.md's B=2000", r.stdout)


if __name__ == "__main__":
    unittest.main()
