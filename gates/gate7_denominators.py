#!/usr/bin/env python3
"""GATE 7 — Denominators.

Reads a rates table (metric_name, numerator, denominator, excluded_count,
excluded_reason, rate) and asserts, per Standing Rule 5 ("Every rate,
accuracy, or proportion is reported with its denominator and with the
count of observations excluded from it by any filter"):

  - every row has a positive denominator (a rate over zero observations
    is not a rate).
  - every row has an EXPLICIT excluded_count (may be 0, but must not be
    blank/NA/missing). This is the literal ACCEPTANCE-section rule: "A
    reported accuracy with no AMBIGUOUS/excluded count is FAIL."
  - numerator does not exceed denominator.
  - if a `rate` value is reported, it matches numerator/denominator
    within a small numerical tolerance (a mismatched rate/numerator/
    denominator triple is itself a data-integrity bug this gate catches).

Usage:
  gate7_denominators.py --rates-table FILE

Exit 0 = all checks pass. Exit 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_float, to_int  # noqa: E402

RATE_TOLERANCE = 1e-6
MISSING_TOKENS = {"", "NA", "N/A", "NONE", "NULL"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rates-table", required=True, type=Path)
    args = ap.parse_args()

    report = GateReport("gate7_denominators")

    try:
        rows = read_tsv(args.rates_table)
    except FileNotFoundError as e:
        report.check("rates table present", False, str(e))
        report.print_and_exit()
        return
    report.check("rates table present", True, f"{args.rates_table.name}, {len(rows)} metric row(s)")

    denominator_failures = []
    excluded_count_failures = []
    numerator_failures = []
    rate_consistency_failures = []

    for row in rows:
        name = row.get("metric_name", "?")

        try:
            denominator = to_float(row["denominator"], "denominator", name)
        except (KeyError, ValueError) as e:
            denominator_failures.append(str(e))
            continue
        if denominator <= 0:
            denominator_failures.append(f"{name}: denominator={denominator} is not positive")

        excluded_raw = row.get("excluded_count") or ""
        if excluded_raw.strip().upper() in MISSING_TOKENS:
            excluded_count_failures.append(f"{name}: excluded_count is missing/blank/NA — not an acceptable result")
        else:
            try:
                excluded = to_int(excluded_raw, "excluded_count", name)
                if excluded < 0:
                    excluded_count_failures.append(f"{name}: excluded_count={excluded} is negative")
            except ValueError as e:
                excluded_count_failures.append(str(e))

        try:
            numerator = to_float(row["numerator"], "numerator", name)
        except (KeyError, ValueError) as e:
            numerator_failures.append(str(e))
            continue
        if numerator > denominator:
            numerator_failures.append(f"{name}: numerator={numerator} > denominator={denominator}")

        rate_raw = (row.get("rate") or "").strip()
        if rate_raw and denominator > 0:
            reported_rate = to_float(rate_raw, "rate", name)
            computed_rate = numerator / denominator
            if abs(reported_rate - computed_rate) > RATE_TOLERANCE:
                rate_consistency_failures.append(
                    f"{name}: reported rate {reported_rate} != numerator/denominator {computed_rate:.6f}"
                )

    report.check(
        "every row has a positive denominator",
        len(denominator_failures) == 0,
        "; ".join(denominator_failures) if denominator_failures else f"all {len(rows)} row(s) have a positive denominator",
    )
    report.check(
        "every row has an explicit (non-blank) excluded_count",
        len(excluded_count_failures) == 0,
        "; ".join(excluded_count_failures) if excluded_count_failures else f"all {len(rows)} row(s) carry an explicit excluded_count",
    )
    report.check(
        "numerator never exceeds denominator",
        len(numerator_failures) == 0,
        "; ".join(numerator_failures) if numerator_failures else f"all {len(rows)} row(s) OK",
    )
    report.check(
        "reported rate (if present) matches numerator/denominator",
        len(rate_consistency_failures) == 0,
        "; ".join(rate_consistency_failures) if rate_consistency_failures else f"all reported rates internally consistent",
    )

    report.print_and_exit()


if __name__ == "__main__":
    main()
