#!/usr/bin/env python3
"""PART B -- post-run artifact integrity check. Checksums every
git-tracked file before and after a pipeline invocation and fails loudly
on any UNEXPECTED change (a file that changed, appeared, or disappeared
outside the invocation's own explicitly-declared expected-to-change
set).

SIMULATED: reads file contents to compute checksums; does not modify
any file itself (the snapshot/verify files it writes are its own
bookkeeping artifacts, not pipeline output).

Why this is a DIFFERENT mechanism from the one REVERSION_DIAGNOSIS.md
considered and rejected: that document rejected a raw byte checksum
SPECIFICALLY as gate6_recovery.py's own internal collision-detection
mechanism for SIMULATED_RECOVERY_TABLE.tsv, because that file
LEGITIMATELY changes on every correct re-score (a checksum diff there
would false-positive on ordinary, correct operation, catching nothing
real). This script does not replace or duplicate that -- it never
inspects SIMULATED_RECOVERY_TABLE.tsv's content for correctness, only
whether ANY file changed that the invoking caller did NOT declare it
intended to change. A caller that legitimately re-scores
SIMULATED_RECOVERY_TABLE.tsv simply lists it in its own
`--expect-changed` glob, and this check raises nothing for it -- while
still catching, e.g., a stray write to PROTOCOL.md, or one gate's
invocation silently touching a completely unrelated file it never
declared. This is the general safety net Part B's post-run layer
exists to provide; REVERSION_DIAGNOSIS.md's own, narrower rejection
does not apply to it.

Usage:
  artifact_checksum_check.py snapshot --out SNAPSHOT.json
  artifact_checksum_check.py verify --snapshot SNAPSHOT.json
      [--expect-changed GLOB [GLOB ...]]

`snapshot` computes SHA-256 of every file `git ls-files` reports
(git-tracked files -- the "committed artifact" set this task's own
wording names) and writes {path: sha256} to --out.

`verify` recomputes the same set's checksums, diffs against --snapshot,
and classifies every difference as EXPECTED (path matches one of
--expect-changed's glob patterns) or UNEXPECTED (fails the check). A
newly created or deleted git-tracked file (relative to the snapshot) is
also classified the same way. Untracked files are not covered by this
check (see module docstring's own scope note) -- a new, uncommitted
output file is not yet a "committed artifact" this check was asked to
protect; the preflight collision check (a static, pre-run property)
and the actual git-add/commit review step (this project's own
established human/session practice) are what govern untracked files.

Exit 0 = no unexpected change. Exit 1 = at least one unexpected change,
or the snapshot itself is missing/unreadable.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def git_tracked_files() -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {result.stderr}")
    return [line for line in result.stdout.splitlines() if line]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_snapshot() -> dict[str, str]:
    snapshot = {}
    for rel_path in git_tracked_files():
        full_path = REPO_ROOT / rel_path
        if full_path.is_file():
            snapshot[rel_path] = sha256_of(full_path)
    return snapshot


def cmd_snapshot(args: argparse.Namespace) -> int:
    snapshot = compute_snapshot()
    out_path = Path(args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
    print(f"Wrote snapshot of {len(snapshot)} git-tracked file(s) to {out_path}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot)
    if not snapshot_path.exists():
        print(f"[FAIL] snapshot file not found: {snapshot_path}")
        return 1
    with open(snapshot_path, encoding="utf-8") as f:
        before = json.load(f)

    after = compute_snapshot()
    expect_patterns = args.expect_changed or []

    def is_expected(rel_path: str) -> bool:
        return any(fnmatch.fnmatch(rel_path, pat) for pat in expect_patterns)

    changed = {p for p in before if p in after and before[p] != after[p]}
    created = {p for p in after if p not in before}
    deleted = {p for p in before if p not in after}

    all_diffs = {p: "changed" for p in changed}
    all_diffs.update({p: "created" for p in created})
    all_diffs.update({p: "deleted" for p in deleted})

    unexpected = {p: kind for p, kind in all_diffs.items() if not is_expected(p)}
    expected = {p: kind for p, kind in all_diffs.items() if is_expected(p)}

    print(f"=== artifact_checksum_check verify ===")
    print(f"[INFO] {len(before)} file(s) in snapshot, {len(after)} file(s) currently tracked")
    print(f"[INFO] {len(all_diffs)} total difference(s): {len(changed)} changed, {len(created)} created, "
          f"{len(deleted)} deleted")
    if expected:
        print(f"[EXPECTED, per --expect-changed] {len(expected)} file(s):")
        for p, kind in sorted(expected.items()):
            print(f"    {kind}: {p}")
    if unexpected:
        print(f"[FAIL] {len(unexpected)} UNEXPECTED change(s) -- not covered by any --expect-changed pattern:")
        for p, kind in sorted(unexpected.items()):
            print(f"    {kind}: {p}")
        print("artifact_checksum_check OVERALL: FAIL")
        return 1

    print("[PASS] no unexpected change found")
    print("artifact_checksum_check OVERALL: PASS")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    snap_ap = sub.add_parser("snapshot")
    snap_ap.add_argument("--out", required=True)

    verify_ap = sub.add_parser("verify")
    verify_ap.add_argument("--snapshot", required=True)
    verify_ap.add_argument("--expect-changed", nargs="*", default=[],
                            help="Glob pattern(s), repo-relative, of paths this invocation intended to change "
                                 "(create, modify, or delete). Any other difference is UNEXPECTED and fails.")

    args = ap.parse_args()
    if args.mode == "snapshot":
        sys.exit(cmd_snapshot(args))
    elif args.mode == "verify":
        sys.exit(cmd_verify(args))


if __name__ == "__main__":
    main()
