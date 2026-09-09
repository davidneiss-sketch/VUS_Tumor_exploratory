import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import build_output_path_inventory as inv  # noqa: E402


class TestPreflightCollisionCheck(unittest.TestCase):
    """A fixture with two producers claiming one path, confirming the
    preflight check fails -- this task's own explicit ACCEPTANCE
    criterion."""

    def _write_fixture(self, tmpdir: Path, colliding: bool) -> None:
        (tmpdir / "producer_a.py").write_text(
            'from pathlib import Path\n'
            'OUT = Path("shared_output.tsv")\n'
            'def main():\n'
            '    with open(OUT, "w") as f:\n'
            '        f.write("a")\n'
        )
        second_path = "shared_output.tsv" if colliding else "producer_b_output.tsv"
        (tmpdir / "producer_b.py").write_text(
            'from pathlib import Path\n'
            f'OUT = Path("{second_path}")\n'
            'def main():\n'
            '    with open(OUT, "w") as f:\n'
            '        f.write("b")\n'
        )

    def test_colliding_fixture_is_flagged_as_a_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self._write_fixture(tmpdir, colliding=True)
            rows = inv.build_inventory_rows(scan_dirs=[tmpdir], include_manual_rows=False)
            unsanctioned = [r for r in rows if r["shared_with_other_producer"] and not r["known_sanctioned_exception"]]
            self.assertEqual(len(unsanctioned), 2, msg=f"rows: {rows}")
            producers = {r["producer"] for r in unsanctioned}
            self.assertIn("producer_a.py", producers)
            self.assertIn("producer_b.py", producers)
            for r in unsanctioned:
                self.assertEqual(r["normalized_path"], "shared_output.tsv")

    def test_non_colliding_fixture_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self._write_fixture(tmpdir, colliding=False)
            rows = inv.build_inventory_rows(scan_dirs=[tmpdir], include_manual_rows=False)
            unsanctioned = [r for r in rows if r["shared_with_other_producer"] and not r["known_sanctioned_exception"]]
            self.assertEqual(len(unsanctioned), 0, msg=f"rows: {rows}")
            paths = {r["normalized_path"] for r in rows}
            self.assertIn("shared_output.tsv", paths)
            self.assertIn("producer_b_output.tsv", paths)

    def test_real_repository_has_zero_unsanctioned_collisions(self):
        """Live re-derivation against the actual, current repository --
        not just an isolated fixture. This is the same check
        scripts/preflight_collision_check.py runs; this test asserts it
        currently passes on this repo's own real source tree."""
        rows = inv.build_inventory_rows()
        unsanctioned = [r for r in rows if r["shared_with_other_producer"] and not r["known_sanctioned_exception"]]
        self.assertEqual(len(unsanctioned), 0,
                          msg=f"unsanctioned collisions found in the real repo: {unsanctioned}")


if __name__ == "__main__":
    unittest.main()
