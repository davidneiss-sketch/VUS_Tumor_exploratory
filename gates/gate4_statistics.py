#!/usr/bin/env python3
"""GATE 4 — Statistics sanity.

Reads an LR table (stratum, gene_group, status, point_estimate, ci_low,
ci_high, n_replicates, n_pathogenic, n_benign) and asserts:
  - every bootstrap CI contains its own point estimate (ci_low <= point
    <= ci_high) for every fitted stratum. A CI that excludes its own
    point estimate indicates a broken bootstrap (e.g. percentile/point
    computed from different resamples, or a sign/transform bug) and is
    always a bug, never a legitimate result.
  - replicate count matches PROTOCOL.md §7.3 (B = 2000) for every fitted
    stratum.
  - CI widths vary across strata (a pipeline that prints the same CI
    width everywhere is not actually bootstrapping per-stratum).
  - every row -- fitted or INSUFFICIENT_N -- carries n_pathogenic and
    n_benign (PROTOCOL.md §8: "never a silently blank or omitted row").

status must be exactly "FITTED" or "INSUFFICIENT_N" (PROTOCOL.md's
literal printed string for an under-powered stratum); any other value is
itself a failure.

Usage:
  gate4_statistics.py --lr-table FILE [--expected-replicates 2000]

Exit 0 = all checks pass. Exit 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_float, to_int  # noqa: E402

VALID_STATUSES = {"FITTED", "INSUFFICIENT_N"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lr-table", required=True, type=Path)
    ap.add_argument("--expected-replicates", type=int, default=2000)
    args = ap.parse_args()

    report = GateReport("gate4_statistics")

    try:
        rows = read_tsv(args.lr_table)
    except FileNotFoundError as e:
        report.check("LR table present", False, str(e))
        report.print_and_exit()
        return
    report.check("LR table present", True, f"{args.lr_table.name}, {len(rows)} stratum row(s)")

    status_failures = []
    ci_contains_point_failures = []
    replicate_failures = []
    denominator_failures = []
    widths = []

    for row in rows:
        stratum = row.get("stratum", "?")
        status = row.get("status", "")
        if status not in VALID_STATUSES:
            status_failures.append(f"{stratum}: status={status!r}, expected one of {sorted(VALID_STATUSES)}")
            continue

        # Denominators required on EVERY row, fitted or not.
        try:
            n_path = to_int(row["n_pathogenic"], "n_pathogenic", stratum)
            n_benign = to_int(row["n_benign"], "n_benign", stratum)
            if n_path < 0 or n_benign < 0:
                denominator_failures.append(f"{stratum}: negative n_pathogenic/n_benign ({n_path}/{n_benign})")
        except (KeyError, ValueError) as e:
            denominator_failures.append(f"{stratum}: {e}")

        if status == "INSUFFICIENT_N":
            continue  # no numeric LR/CI/replicate checks apply to an unfit stratum

        try:
            point = to_float(row["point_estimate"], "point_estimate", stratum)
            ci_low = to_float(row["ci_low"], "ci_low", stratum)
            ci_high = to_float(row["ci_high"], "ci_high", stratum)
            n_rep = to_int(row["n_replicates"], "n_replicates", stratum)
        except (KeyError, ValueError) as e:
            ci_contains_point_failures.append(f"{stratum}: {e}")
            continue

        if not (ci_low <= point <= ci_high):
            ci_contains_point_failures.append(
                f"{stratum}: CI [{ci_low}, {ci_high}] does not contain point estimate {point}"
            )

        if n_rep != args.expected_replicates:
            replicate_failures.append(f"{stratum}: n_replicates={n_rep} != expected {args.expected_replicates}")

        widths.append((stratum, ci_high - ci_low))

    report.check(
        "every row's status is FITTED or INSUFFICIENT_N",
        len(status_failures) == 0,
        "; ".join(status_failures) if status_failures else f"all {len(rows)} row(s) have a valid status",
    )
    report.check(
        "every fitted row carries n_pathogenic and n_benign (non-negative)",
        len(denominator_failures) == 0,
        "; ".join(denominator_failures) if denominator_failures else f"all {len(rows)} row(s) carry valid denominators",
    )
    report.check(
        "every bootstrap CI contains its own point estimate",
        len(ci_contains_point_failures) == 0,
        "; ".join(ci_contains_point_failures) if ci_contains_point_failures else f"all {len(widths)} fitted row(s) OK",
    )
    report.check(
        f"replicate count matches protocol (B={args.expected_replicates})",
        len(replicate_failures) == 0,
        "; ".join(replicate_failures) if replicate_failures else f"all {len(widths)} fitted row(s) OK",
    )

    distinct_widths = {round(w, 6) for _, w in widths}
    widths_vary = len(widths) < 2 or len(distinct_widths) > 1
    report.check(
        "CI widths vary across strata",
        widths_vary,
        f"{len(distinct_widths)} distinct CI width(s) across {len(widths)} fitted stratum/strata"
        if widths
        else "no fitted strata to compare",
    )

    report.print_and_exit()


if __name__ == "__main__":
    main()
