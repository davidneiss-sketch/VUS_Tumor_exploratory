#!/usr/bin/env python3
"""PART B -- preflight collision check. Run this BEFORE any pipeline
invocation (any gate, any production run, any script that writes output
files) to fail loudly if the CURRENT source tree has any output path
claimed by more than one producer, other than the one sanctioned
exception (gate6_recovery.py's own, deliberate, already merge-aware
handling of SIMULATED_RECOVERY_TABLE.tsv -- see
build_output_path_inventory.py's own module docstring and
OUTPUT_PATH_INVENTORY.tsv's `known_sanctioned_exception` column).

SIMULATED: read-only static analysis (delegates to
build_output_path_inventory.py's build_inventory_rows(), re-run fresh
against the CURRENT source tree every time this script runs -- not a
cached/possibly-stale committed OUTPUT_PATH_INVENTORY.tsv). Does not
modify any file.

This is the "preflight" half of Part B's two-layer defense: this check
catches a collision BEFORE anything runs (a static property of the
source code); artifact_checksum_check.py's snapshot/verify pair catches
an ACTUAL unexpected write AFTER something ran (a property of what
actually happened on disk). Both are needed -- a preflight check can
only catch a collision this static scanner can see (see
build_output_path_inventory.py's own documented scan limitations); the
checksum check is the safety net for anything that gets past it.

Usage:
  preflight_collision_check.py

Exit 0 = no unsanctioned collision found. Exit 1 = at least one
unsanctioned collision found (or the scan itself failed to parse a file).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "gates"))
from gates_common import GateReport  # noqa: E402
import build_output_path_inventory as inv  # noqa: E402


def main() -> None:
    report = GateReport("preflight_collision_check")

    rows = inv.build_inventory_rows()
    report.check("static output-path scan completed", True, f"{len(rows)} write call sites scanned")

    parse_errors = [r for r in rows if r["call_kind"] == "PARSE_ERROR"]
    report.check("every scanned .py file parsed without error", len(parse_errors) == 0,
                 "; ".join(f"{r['producer']}: {r['output_path']}" for r in parse_errors)
                 if parse_errors else "no parse errors")

    unsanctioned = [r for r in rows if r["shared_with_other_producer"] and not r["known_sanctioned_exception"]]
    if unsanctioned:
        detail_lines = [f"{r['producer']} -> {r['normalized_path']} (also written by: {r['other_producers']})"
                         for r in unsanctioned]
        report.check("no path is claimed by more than one producer (excluding the sanctioned gate6-merge exception)",
                      False, "; ".join(detail_lines))
    else:
        sanctioned = [r for r in rows if r["shared_with_other_producer"] and r["known_sanctioned_exception"]]
        report.check("no path is claimed by more than one producer (excluding the sanctioned gate6-merge exception)",
                      True, f"0 unsanctioned collisions; {len(sanctioned)} sanctioned-exception rows "
                            f"(gate6_recovery.py's own merge-aware SIMULATED_RECOVERY_TABLE.tsv handling, "
                            f"explicitly preserved per this project's own DO-NOT clause)")

    report.print_and_exit()


if __name__ == "__main__":
    main()
