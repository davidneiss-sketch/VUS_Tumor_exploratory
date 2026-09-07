#!/usr/bin/env python3
"""GATE 3 — Runtime reality.

Reads a per-phase runtime log (phase, command, exit_code, wall_clock_sec,
peak_rss_mb, cpu_hours, bytes_read, n_samples) and asserts:
  - every phase's exit_code is 0 (Standing Rule 4: nonzero exit is failure
    even if a file appeared -- this gate is where that rule is mechanically
    enforced for the pipeline's own phases).
  - every phase's per-sample wall-clock time (wall_clock_sec / n_samples)
    exceeds a pre-specified floor. This is the tripwire against a stub or
    cached/no-op phase silently standing in for real per-sample work: real
    copy-number calling, signature assignment, etc. cannot legitimately
    finish in a few milliseconds per sample.

Per-phase floors are fixed constants (DEFAULT_FLOORS below), not
"data-driven" -- they may be overridden per-deployment via
--floors-file (phase, floor_sec_per_sample), but the floors file itself
must be checked in, versioned, and named in the run log; this gate never
infers a floor from the data it is checking.

Usage:
  gate3_runtime.py --phase-log FILE [--floors-file FILE]

Exit 0 = all checks pass. Exit 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_float, to_int  # noqa: E402

# Fixed, pre-specified per-phase floors (seconds of wall-clock time per
# sample). Conservative lower bounds meant to catch a phase that did not
# really do per-sample work, not to model expected real-world runtime.
DEFAULT_FLOORS: dict[str, float] = {
    "copy_number_calling": 5.0,
    "hrd_scoring": 1.0,
    "signature_assignment": 2.0,
    "loh_binomial_test": 0.02,
    "second_hit_scan": 0.05,
}
FALLBACK_FLOOR = 0.5  # used for any phase name not listed above


def load_floors(path: Path | None) -> dict[str, float]:
    floors = dict(DEFAULT_FLOORS)
    if path is not None:
        rows = read_tsv(path)
        for row in rows:
            floors[row["phase"]] = float(row["floor_sec_per_sample"])
    return floors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-log", required=True, type=Path)
    ap.add_argument("--floors-file", type=Path, default=None)
    args = ap.parse_args()

    report = GateReport("gate3_runtime")

    try:
        rows = read_tsv(args.phase_log)
    except FileNotFoundError as e:
        report.check("phase log present", False, str(e))
        report.print_and_exit()
        return
    report.check("phase log present", True, f"{args.phase_log.name}, {len(rows)} phase(s)")

    try:
        floors = load_floors(args.floors_file)
    except FileNotFoundError as e:
        report.check("floors file loadable (if provided)", False, str(e))
        report.print_and_exit()
        return

    exit_code_failures = []
    runtime_floor_failures = []
    field_failures = []

    for row in rows:
        phase = row.get("phase", "?")
        try:
            exit_code = to_int(row["exit_code"], "exit_code", phase)
            wall_clock = to_float(row["wall_clock_sec"], "wall_clock_sec", phase)
            n_samples = to_int(row["n_samples"], "n_samples", phase)
            # These are required fields even though this gate doesn't
            # threshold on them directly -- their presence is part of
            # "per-phase command, exit code, wall clock, peak RSS,
            # CPU-hours, bytes read" being genuinely recorded.
            _ = row["command"]
            _ = to_float(row["peak_rss_mb"], "peak_rss_mb", phase)
            _ = to_float(row["cpu_hours"], "cpu_hours", phase)
            _ = to_int(row["bytes_read"], "bytes_read", phase)
        except (KeyError, ValueError) as e:
            field_failures.append(f"{phase}: {e}")
            continue

        if exit_code != 0:
            exit_code_failures.append(f"{phase}: exit_code={exit_code} (command: {row.get('command')})")

        if n_samples > 0:
            floor = floors.get(phase, FALLBACK_FLOOR)
            per_sample = wall_clock / n_samples
            if per_sample < floor:
                runtime_floor_failures.append(
                    f"{phase}: {per_sample:.4f} sec/sample < floor {floor} sec/sample "
                    f"(wall_clock={wall_clock}s, n_samples={n_samples})"
                )

    report.check(
        "every phase has all required runtime fields recorded",
        len(field_failures) == 0,
        "; ".join(field_failures) if field_failures else f"all {len(rows)} phase(s) have command/exit_code/wall_clock/peak_rss/cpu_hours/bytes_read",
    )
    report.check(
        "every phase exited 0",
        len(exit_code_failures) == 0,
        "; ".join(exit_code_failures) if exit_code_failures else f"all {len(rows)} phase(s) exited 0",
    )
    report.check(
        "every phase's per-sample runtime exceeds its floor",
        len(runtime_floor_failures) == 0,
        "; ".join(runtime_floor_failures) if runtime_floor_failures else f"all {len(rows)} phase(s) at/above floor (floors: {floors})",
    )

    report.print_and_exit()


if __name__ == "__main__":
    main()
