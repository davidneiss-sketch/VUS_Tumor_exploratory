#!/usr/bin/env python3
"""GATE 3 — Runtime reality.

Reads a per-phase runtime log (phase, command, exit_code, wall_clock_sec,
peak_rss_mb, cpu_hours, bytes_read, n_samples) and asserts:
  - every phase's exit_code is 0 (Standing Rule 4: nonzero exit is failure
    even if a file appeared -- this gate is where that rule is mechanically
    enforced for the pipeline's own phases).
  - every phase's per-sample wall-clock time (wall_clock_sec / n_samples)
    exceeds a pre-specified, TRACK-CONDITIONAL floor. This is the tripwire
    against a stub or cached/no-op phase silently standing in for real
    per-sample work.

TRACK-CONDITIONAL DESIGN (this gate's own housekeeping fix): a single
runtime floor cannot bind on both a toy/SIMULATED run (legitimately fast)
and a Track B run claiming real exome-scale work (which must take
materially longer). Two floor sets exist, both fixed constants recorded in
GATE3.json (never inferred from the data being checked):

  - TRACK_S: this gate's original floors -- deliberately small, calibrated
    only to catch a stub that finishes in milliseconds on toy/SIMULATED
    inputs. Still ARBITRARY (not literature-derived) -- see GATE3.json.
  - TRACK_B: derived from real, live-cited tool runtimes wherever such a
    citation could be found and verified (see GATE_HOUSEKEEPING.md for the
    full research trail and every URL). Per Standing Rule 3, no number is
    invented where no genuine citation exists: `signature_assignment` has
    NO verified Track B floor (SigProfilerAssignment's real per-exome
    runtime could not be found or verified despite a genuine search) and
    is intentionally left `None` here -- a Track B phase log entry for
    this phase cannot be validated by this gate and is reported as a hard
    failure (BLOCKED), never silently passed or silently given the looser
    Track S floor.

`--track` is REQUIRED: a caller must declare which track a phase log
represents before this gate will check it. There is no default, by design
-- silently defaulting to one track would be exactly the kind of silent
substitution Standing Rule 4 forbids.

Usage:
  gate3_runtime.py --phase-log FILE --track {TRACK_S,TRACK_B} [--floors-file FILE]

Exit 0 = all checks pass. Exit 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_float, to_int  # noqa: E402

# TRACK_S: this gate's original floors (seconds of wall-clock time per
# sample). Conservative lower bounds meant to catch a phase that did not
# really do per-sample work on a toy/SIMULATED-scale run -- not meant to
# model real-world runtime. ARBITRARY, unchanged from this gate's original
# design (recorded in GATE3.json, not literature-derived).
TRACK_S_FLOORS: dict[str, float] = {
    "copy_number_calling": 5.0,
    "hrd_scoring": 1.0,
    "signature_assignment": 2.0,
    "loh_binomial_test": 0.02,
    "second_hit_scan": 0.05,
}

# TRACK_B: derived from real per-exome/per-genome tool timings, live-cited
# where a genuine citation exists. `None` = no verified figure exists;
# see GATE3.json's "track_b_derivation" list and GATE_HOUSEKEEPING.md for
# the full citation trail (every URL, what was and wasn't found, and the
# disclosed ARBITRARY conservatism factors applied on top of each cited
# figure -- these floors are NOT presented as literature-precise numbers,
# only as literature-anchored conservative lower bounds).
TRACK_B_FLOORS: dict[str, float | None] = {
    "copy_number_calling": 90.0,     # ASCAT README WGS figure / 20 (ARBITRARY WGS->WES margin)
    "hrd_scoring": 24.0,             # scarHRD README qualitative figure, low-end interpretation / 5 (ARBITRARY margin)
    "signature_assignment": None,    # UNVERIFIED -- no usable SigProfilerAssignment runtime citation found
    "loh_binomial_test": 0.02,       # in-house code, no third-party tool to benchmark; same as TRACK_S
    "second_hit_scan": 0.05,         # in-house code, no third-party tool to benchmark; same as TRACK_S
}

FALLBACK_FLOOR = 0.5  # used for any phase name not listed in the selected track's dict, either track

TRACKS = {"TRACK_S": TRACK_S_FLOORS, "TRACK_B": TRACK_B_FLOORS}


def load_floors(track: str, path: Path | None) -> dict[str, float | None]:
    floors = dict(TRACKS[track])
    if path is not None:
        rows = read_tsv(path)
        for row in rows:
            floors[row["phase"]] = float(row["floor_sec_per_sample"])
    return floors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-log", required=True, type=Path)
    ap.add_argument("--track", required=True, choices=sorted(TRACKS), help="Which floor set applies to this phase log. No default -- a caller must declare it.")
    ap.add_argument("--floors-file", type=Path, default=None, help="Optional override floors (phase, floor_sec_per_sample), layered on top of the selected --track's defaults.")
    args = ap.parse_args()

    report = GateReport("gate3_runtime")

    try:
        rows = read_tsv(args.phase_log)
    except FileNotFoundError as e:
        report.check("phase log present", False, str(e))
        report.print_and_exit()
        return
    report.check("phase log present", True, f"{args.phase_log.name}, {len(rows)} phase(s), track={args.track}")

    try:
        floors = load_floors(args.track, args.floors_file)
    except FileNotFoundError as e:
        report.check("floors file loadable (if provided)", False, str(e))
        report.print_and_exit()
        return

    exit_code_failures = []
    runtime_floor_failures = []
    field_failures = []
    unverified_floor_failures = []

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
            if floor is None:
                # Standing Rule 4: never substitute silently. A phase with
                # no verified Track B floor cannot be validated by this
                # gate at all -- that is reported as a hard failure
                # (BLOCKED), never as a silent pass or a silent fallback
                # to the (looser) Track S floor.
                unverified_floor_failures.append(
                    f"{phase}: no verified {args.track} floor exists (UNVERIFIED per Standing Rule 3 -- "
                    f"see GATE3.json track_b_derivation and GATE_HOUSEKEEPING.md); this phase's runtime "
                    f"cannot be tripwire-checked under {args.track} until a real citation is found"
                )
                continue
            per_sample = wall_clock / n_samples
            if per_sample < floor:
                runtime_floor_failures.append(
                    f"{phase}: {per_sample:.4f} sec/sample < floor {floor} sec/sample "
                    f"(wall_clock={wall_clock}s, n_samples={n_samples}, track={args.track})"
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
        "; ".join(runtime_floor_failures) if runtime_floor_failures else f"all {len(rows)} phase(s) at/above floor (track={args.track}, floors: {floors})",
    )
    report.check(
        f"no phase relies on an UNVERIFIED {args.track} floor",
        len(unverified_floor_failures) == 0,
        "; ".join(unverified_floor_failures) if unverified_floor_failures else "every phase in this log has a verified floor for this track",
    )

    report.print_and_exit()


if __name__ == "__main__":
    main()
