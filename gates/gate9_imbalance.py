#!/usr/bin/env python3
"""GATE 9 -- Class-imbalance invariance of the prior-odds conversion.
NEW AND MANDATORY (this task): runs against production output on every
pipeline invocation, alongside gate4, gate6, and gate8.

The problem this gate exists to catch: PROPOSED_PROTOCOL_AMENDMENT.md's
replacement estimator converts a fitted probability to a likelihood
ratio by dividing out the reference set's own class-balance-implied
prior odds (`LR(X) = [p_hat/(1-p_hat)] * [n_benign_ref/n_path_ref]`).
This conversion is valid ONLY if the fit itself applies no additional,
undocumented class-balance correction (no class_weight="balanced", no
resampling, no explicit prior/offset). If it does, the recovered LR is
silently wrong -- and this task's own text names this exact mechanism as
"what broke v2." No test in this repository caught it before now
(`ESTIMATOR_OPTIONS.md` searched for a "class-imbalance test" under that
name and did not find one -- reported UNVERIFIED, not assumed to exist;
this gate is that test, built rather than left unbuilt).

**What a correct conversion guarantees**: for the SAME underlying
feature distributions, evaluated at the SAME point, the recovered LR
must be INVARIANT to the reference set's own class-balance ratio --
whether the reference set was assembled 1:1, 1:5, or 1:20
(Pathogenic:Benign or any other ratio), the conversion should recover
statistically the same LR, because the fitted SLOPE coefficients are a
consistent estimate of the population slopes regardless of the
case-control sampling ratio (Prentice & Pyke 1979), and the intercept
term the ratio DOES bias is exactly what the prior-odds division removes.
An UNCORRECTED or DOUBLE-CORRECTED conversion violates this invariance
directly and detectably -- an uncorrected LR scales roughly linearly with
the reference set's own imbalance ratio.

Input schema (TSV): test_case, class_ratio_label, n_pathogenic_ref,
n_benign_ref, recovered_lr[, replicate_index]. Rows sharing a
`test_case` are compared against each other across their distinct
`class_ratio_label` values (mean recovered_lr per label, if multiple
replicate rows exist per label).

Checks:
  1. every test_case has recovered_lr rows spanning AT LEAST the 3
     ratios this task specifies (1:1, 1:5, 1:20) -- an incomplete sweep
     cannot support the invariance claim at all.
  2. for every test_case, the recovered LR (mean per ratio label) is
     stable across ratios within a pre-specified tolerance -- see
     TOLERANCE_MAX_RATIO below.

======================================================================
THRESHOLD -- PRE-SPECIFIED HERE, WITH RATIONALE, BEFORE THIS GATE IS RUN
AGAINST ANY PRODUCTION OUTPUT.
======================================================================

TOLERANCE_MAX_RATIO = 2.0. The largest per-ratio mean recovered LR must
not exceed the smallest by more than a factor of 2, for a given
test_case. Rationale: a correct conversion's remaining ratio-to-ratio
variation is pure finite-sample noise (fewer minority-class observations
at 1:20 than 1:1 increases estimation VARIANCE, not the expectation) --
at the sample sizes this gate's own production run uses (n as low as 15
for the minority class at 1:20), a factor-of-2 band comfortably covers
that noise (see CALIBRATION_DIAGNOSTICS.md's own bootstrap SDs for the
same order of magnitude of finite-sample spread this gate's tolerance is
sized against). An UNCORRECTED conversion, by contrast, scales
LR roughly linearly with the reference-set ratio itself -- a 1:1 to
1:20 sweep would produce roughly a 20x spread under that failure mode,
20x through 2x with room to spare, not a borderline case this threshold
would need to be tuned to catch.

Usage:
  gate9_imbalance.py --table FILE --outdir DIR

Exit 0 = all checks pass. Exit 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, write_tsv, to_float, to_int  # noqa: E402

REQUIRED_RATIO_LABELS = {"1:1", "1:5", "1:20"}
TOLERANCE_MAX_RATIO = 2.0


def evaluate(rows: list[dict]) -> tuple[list[dict], GateReport]:
    report = GateReport("gate9_imbalance")

    by_test_case: dict[str, dict[str, list[float]]] = {}
    parse_failures = []
    for row in rows:
        tc = row.get("test_case", "")
        label = row.get("class_ratio_label", "")
        try:
            lr = to_float(row["recovered_lr"], "recovered_lr", f"{tc}/{label}")
            to_int(row["n_pathogenic_ref"], "n_pathogenic_ref", f"{tc}/{label}")
            to_int(row["n_benign_ref"], "n_benign_ref", f"{tc}/{label}")
        except (KeyError, ValueError) as e:
            parse_failures.append(str(e))
            continue
        by_test_case.setdefault(tc, {}).setdefault(label, []).append(lr)

    report.check("every row parses (recovered_lr, n_pathogenic_ref, n_benign_ref numeric)",
                 len(parse_failures) == 0,
                 "; ".join(parse_failures) if parse_failures else f"all {len(rows)} row(s) parsed")

    if not by_test_case:
        report.check("at least one test_case present", False, "no rows / no test_case column found")
        return [], report
    report.check("at least one test_case present", True, f"{len(by_test_case)} test_case(s): {sorted(by_test_case)}")

    output_rows = []
    coverage_failures = []
    stability_failures = []
    for tc, labels in sorted(by_test_case.items()):
        present = set(labels.keys())
        missing = REQUIRED_RATIO_LABELS - present
        if missing:
            coverage_failures.append(f"{tc}: missing ratio label(s) {sorted(missing)} (has {sorted(present)})")

        means = {label: sum(vals) / len(vals) for label, vals in labels.items()}
        checked_labels = sorted(REQUIRED_RATIO_LABELS & present)
        if len(checked_labels) >= 2:
            checked_means = [means[l] for l in checked_labels]
            max_mean, min_mean = max(checked_means), min(checked_means)
            spread_ratio = max_mean / min_mean if min_mean > 0 else float("inf")
            stable = spread_ratio <= TOLERANCE_MAX_RATIO
            if not stable:
                stability_failures.append(
                    f"{tc}: recovered LR spread across ratios = {spread_ratio:.3f}x "
                    f"(means: {', '.join(f'{l}={means[l]:.4f}' for l in checked_labels)}) "
                    f"exceeds tolerance {TOLERANCE_MAX_RATIO}x"
                )
            for label in sorted(present):
                output_rows.append({
                    "test_case": tc, "class_ratio_label": label, "n_replicates": len(labels[label]),
                    "mean_recovered_lr": means[label], "spread_ratio_vs_other_labels": spread_ratio,
                    "stable_within_tolerance": stable,
                })

    report.check("every test_case has recovered LR rows for all 3 required ratios (1:1, 1:5, 1:20)",
                 len(coverage_failures) == 0,
                 "; ".join(coverage_failures) if coverage_failures else f"all {len(by_test_case)} test_case(s) complete")
    report.check(f"recovered LR is stable across class ratios within {TOLERANCE_MAX_RATIO}x tolerance, per test_case",
                 len(stability_failures) == 0,
                 "; ".join(stability_failures) if stability_failures else f"all {len(by_test_case)} test_case(s) stable")

    return output_rows, report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args()

    report = GateReport("gate9_imbalance")
    try:
        rows = read_tsv(args.table)
    except FileNotFoundError as e:
        report.check("input table present", False, str(e))
        report.print_and_exit()
        return
    report.check("input table present", True, f"{args.table.name}, {len(rows)} row(s)")

    output_rows, eval_report = evaluate(rows)
    report.checks.extend(eval_report.checks)

    if output_rows:
        out_path = args.outdir / "SIMULATED_GATE9_IMBALANCE_REPORT.tsv"
        write_tsv(out_path, output_rows,
                  ["test_case", "class_ratio_label", "n_replicates", "mean_recovered_lr",
                   "spread_ratio_vs_other_labels", "stable_within_tolerance"])
        report.check("SIMULATED_GATE9_IMBALANCE_REPORT.tsv emitted", True,
                     f"{out_path} ({len(output_rows)} rows)")

    report.print_and_exit()


if __name__ == "__main__":
    main()
