import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "artifact_checksum_check.py"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                           cwd=str(REPO_ROOT), timeout=60)


class TestArtifactChecksumCheck(unittest.TestCase):
    """Snapshot/verify pair against this repository's own real
    git-tracked files, in an isolated temp copy so this test never
    touches the real working tree."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="checksum_test_")
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.snapshot_path = Path(self._tmpdir) / "snapshot.json"

    def test_snapshot_then_verify_with_no_changes_passes(self):
        r1 = run("snapshot", "--out", str(self.snapshot_path))
        self.assertEqual(r1.returncode, 0, msg=r1.stdout + r1.stderr)
        self.assertTrue(self.snapshot_path.exists())

        r2 = run("verify", "--snapshot", str(self.snapshot_path))
        self.assertEqual(r2.returncode, 0, msg=r2.stdout + r2.stderr)
        self.assertIn("artifact_checksum_check OVERALL: PASS", r2.stdout)

    def test_unexpected_change_to_a_tracked_file_fails(self):
        r1 = run("snapshot", "--out", str(self.snapshot_path))
        self.assertEqual(r1.returncode, 0, msg=r1.stdout + r1.stderr)

        target = REPO_ROOT / "tests/test_helpers.py"
        original = target.read_text(encoding="utf-8")
        try:
            target.write_text(original + "\nUNEXPECTED TEST APPEND\n", encoding="utf-8")
            r2 = run("verify", "--snapshot", str(self.snapshot_path))
            self.assertEqual(r2.returncode, 1, msg=r2.stdout + r2.stderr)
            self.assertIn("UNEXPECTED", r2.stdout)
            self.assertIn("tests/test_helpers.py", r2.stdout)
            self.assertIn("artifact_checksum_check OVERALL: FAIL", r2.stdout)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_declared_expected_change_does_not_fail(self):
        r1 = run("snapshot", "--out", str(self.snapshot_path))
        self.assertEqual(r1.returncode, 0, msg=r1.stdout + r1.stderr)

        target = REPO_ROOT / "tests/test_helpers.py"
        original = target.read_text(encoding="utf-8")
        try:
            target.write_text(original + "\nDECLARED-EXPECTED TEST APPEND\n", encoding="utf-8")
            r2 = run("verify", "--snapshot", str(self.snapshot_path), "--expect-changed", "tests/test_helpers.py")
            self.assertEqual(r2.returncode, 0, msg=r2.stdout + r2.stderr)
            self.assertIn("artifact_checksum_check OVERALL: PASS", r2.stdout)
            self.assertIn("EXPECTED", r2.stdout)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_missing_snapshot_fails_loudly(self):
        r = run("verify", "--snapshot", str(Path(self._tmpdir) / "does_not_exist.json"))
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("snapshot file not found", r.stdout)


if __name__ == "__main__":
    unittest.main()
