#!/usr/bin/env python3
"""PART B -- runs any pipeline command wrapped, UNCONDITIONALLY, in both
of Part B's checks: preflight_collision_check.py BEFORE the command
runs, and artifact_checksum_check.py's snapshot/verify pair around it.
This is the "unconditional" invocation pattern this task's own
ACCEPTANCE section requires -- not two standalone scripts a future
session might forget to call, but the actual, only, documented way any
gate or production script is invoked from here on in this session.

SIMULATED: orchestrates the two checks above and the wrapped command;
writes only its own snapshot bookkeeping file (in a temp location, not a
repo artifact) plus whatever the wrapped command itself writes.

Usage:
  run_with_integrity_checks.py --expect-changed GLOB [GLOB ...] -- CMD [ARGS...]

Exit code: the wrapped command's own exit code if both integrity checks
pass; 1 if the PREFLIGHT check itself fails (the command is never run);
1 if the wrapped command exits 0 but the POST-RUN checksum check finds
an unexpected change (the command's own success does not override an
integrity failure -- Standing Rule 4: nonzero exit is failure even if a
file appeared, and an integrity failure is exactly that class of thing).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-changed", nargs="+", required=True,
                     help="Glob pattern(s), repo-relative, this command is expected to create/modify/delete.")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="'-- CMD ARGS...' -- the command to run wrapped.")
    args = ap.parse_args()

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("[FAIL] no command given after '--'")
        sys.exit(1)

    print(f"=== run_with_integrity_checks: preflight ===")
    preflight = subprocess.run([sys.executable, str(SCRIPTS_DIR / "preflight_collision_check.py")],
                                cwd=REPO_ROOT)
    if preflight.returncode != 0:
        print("[FAIL] preflight_collision_check failed -- refusing to run the wrapped command")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        snapshot_path = Path(tmp) / "snapshot.json"
        print(f"=== run_with_integrity_checks: snapshot ===")
        snap = subprocess.run([sys.executable, str(SCRIPTS_DIR / "artifact_checksum_check.py"),
                                "snapshot", "--out", str(snapshot_path)], cwd=REPO_ROOT)
        if snap.returncode != 0:
            print("[FAIL] could not snapshot artifact checksums -- refusing to run the wrapped command")
            sys.exit(1)

        print(f"=== run_with_integrity_checks: running wrapped command: {' '.join(cmd)} ===")
        result = subprocess.run(cmd, cwd=REPO_ROOT)
        cmd_exit = result.returncode

        print(f"=== run_with_integrity_checks: post-run integrity verify ===")
        verify = subprocess.run([sys.executable, str(SCRIPTS_DIR / "artifact_checksum_check.py"),
                                  "verify", "--snapshot", str(snapshot_path),
                                  "--expect-changed", *args.expect_changed], cwd=REPO_ROOT)

    print(f"=== run_with_integrity_checks summary: wrapped command exit={cmd_exit}, "
          f"integrity verify exit={verify.returncode} ===")
    sys.exit(cmd_exit if verify.returncode == 0 else 1)


if __name__ == "__main__":
    main()
