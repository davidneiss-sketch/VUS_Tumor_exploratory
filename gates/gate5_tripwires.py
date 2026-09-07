#!/usr/bin/env python3
"""GATE 5 — Tripwires. MANDATORY: runs against PRODUCTION output files on
every pipeline invocation, not only against test fixtures (see
DEPLOYMENT_LOG.md for the record of every production run this gate has
actually scanned, by file name).

Flags five specific red-flag patterns, each a fixed, pre-specified
constant -- none of these ceilings is inferred from the data being
checked:

  1. Concordance/AUC above ceiling (AUC_CEILING = 0.95): real biological
     classifiers essentially never legitimately hit near-perfect
     discrimination on held-out data; a value this high is far more often
     a leakage/overfitting bug than a genuine result.
  2. Any control value matching its cited benchmark within
     BENCHMARK_MATCH_CEILING_PCT = 1%: a suspiciously exact match usually
     means the benchmark was hard-coded into the "independent" estimate
     rather than the two being genuinely computed apart.
  3. A derived threshold inconsistent with its own reported bias
     (THRESHOLD_BIAS_CONSISTENCY_EPSILON_PCT = 1.0 percentage point): if
     the recomputed relative difference between derived and reference
     threshold disagrees with the bias the pipeline itself reported, the
     reporting is self-inconsistent.
  4. A circularity-exclusion count of exactly zero (PROTOCOL.md §4.3):
     implausible that none of a large reference set ever overlaps the
     protocol's own calibration/circularity sources.
  5. A negative-control CI narrower than a comparable-n positive-control
     CI (comparable = total n within ±20%): negative controls should be
     at least as noisy as positive controls at matched n, never tighter.

Any single flag is a gate FAILURE (exit 1) -- these are tripwires, not
warnings; a fired tripwire means a human must look, not that the pipeline
proceeds anyway.

Usage:
  gate5_tripwires.py --metrics FILE --thresholds FILE --circularity FILE
                      --lr-table FILE

Exit 0 = no tripwire fired. Exit 1 = at least one tripwire fired.
"""
from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_float, to_int  # noqa: E402

AUC_CEILING = 0.95
BENCHMARK_MATCH_CEILING_PCT = 1.0  # percent
THRESHOLD_BIAS_CONSISTENCY_EPSILON_PCT = 1.0  # percentage points
CONTROL_N_BAND_PCT = 20.0  # percent, for "comparable n"

AUC_LIKE_METRIC_SUBSTRINGS = ("auc", "concordance", "c_index", "c-index")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True, type=Path)
    ap.add_argument("--thresholds", required=True, type=Path)
    ap.add_argument("--circularity", required=True, type=Path)
    ap.add_argument("--lr-table", required=True, type=Path)
    args = ap.parse_args()

    report = GateReport("gate5_tripwires")

    try:
        metrics_rows = read_tsv(args.metrics)
        threshold_rows = read_tsv(args.thresholds)
        circularity_rows = read_tsv(args.circularity)
        lr_rows = read_tsv(args.lr_table)
    except FileNotFoundError as e:
        report.check("all required input files present", False, str(e))
        report.print_and_exit()
        return
    report.check(
        "all required input files present",
        True,
        f"metrics={args.metrics.name}, thresholds={args.thresholds.name}, "
        f"circularity={args.circularity.name}, lr_table={args.lr_table.name}",
    )

    # --- Tripwire 1: concordance/AUC above ceiling ---
    auc_flags = []
    for row in metrics_rows:
        name = row.get("metric_name") or ""
        if any(s in name.lower() for s in AUC_LIKE_METRIC_SUBSTRINGS):
            value = to_float(row["value"], "value", name)
            if value > AUC_CEILING:
                auc_flags.append(f"{name}={value} > ceiling {AUC_CEILING}")
    report.check(
        f"no concordance/AUC-like metric exceeds ceiling ({AUC_CEILING})",
        len(auc_flags) == 0,
        "; ".join(auc_flags) if auc_flags else "no AUC/concordance metric exceeded the ceiling",
    )

    # --- Tripwire 2: control matches benchmark within 1% ---
    benchmark_flags = []
    for row in metrics_rows:
        name = row.get("metric_name") or ""
        bench_str = (row.get("benchmark_value") or "").strip()
        if not bench_str or bench_str.upper() in ("NA", "N/A", "NONE"):
            continue
        value = to_float(row["value"], "value", name)
        bench = to_float(bench_str, "benchmark_value", name)
        if bench == 0:
            continue
        rel_diff_pct = abs(value - bench) / abs(bench) * 100.0
        if rel_diff_pct <= BENCHMARK_MATCH_CEILING_PCT:
            benchmark_flags.append(
                f"{name}: value={value} vs benchmark={bench} "
                f"(source={row.get('benchmark_source', '?')}) — {rel_diff_pct:.3f}% apart, <= {BENCHMARK_MATCH_CEILING_PCT}% ceiling"
            )
    report.check(
        f"no control matches its cited benchmark within {BENCHMARK_MATCH_CEILING_PCT}%",
        len(benchmark_flags) == 0,
        "; ".join(benchmark_flags) if benchmark_flags else "no suspiciously exact benchmark match",
    )

    # --- Tripwire 3: derived threshold inconsistent with its own reported bias ---
    threshold_flags = []
    for row in threshold_rows:
        name = row.get("threshold_name", "?")
        derived = to_float(row["derived_threshold"], "derived_threshold", name)
        reference = to_float(row["reference_threshold"], "reference_threshold", name)
        reported_bias_pct = to_float(row["reported_bias_pct"], "reported_bias_pct", name)
        if reference == 0:
            threshold_flags.append(f"{name}: reference_threshold is 0, cannot compute relative bias")
            continue
        actual_bias_pct = (derived - reference) / abs(reference) * 100.0
        if abs(actual_bias_pct - reported_bias_pct) > THRESHOLD_BIAS_CONSISTENCY_EPSILON_PCT:
            threshold_flags.append(
                f"{name}: recomputed bias {actual_bias_pct:.3f}% vs reported bias {reported_bias_pct}% "
                f"(disagree by more than {THRESHOLD_BIAS_CONSISTENCY_EPSILON_PCT}pp)"
            )
    report.check(
        "every derived threshold's reported bias matches its recomputed bias",
        len(threshold_flags) == 0,
        "; ".join(threshold_flags) if threshold_flags else f"all {len(threshold_rows)} threshold row(s) self-consistent",
    )

    # --- Tripwire 4: circularity exclusion count of zero ---
    zero_exclusion_flags = []
    for row in circularity_rows:
        gene_group = row.get("gene_group", "?")
        count = to_int(row["excluded_count"], "excluded_count", gene_group)
        if count == 0:
            zero_exclusion_flags.append(f"{gene_group}: circularity exclusion count is 0")
    report.check(
        "no gene group has a circularity-exclusion count of zero",
        len(zero_exclusion_flags) == 0,
        "; ".join(zero_exclusion_flags) if zero_exclusion_flags else f"all {len(circularity_rows)} gene-group row(s) have nonzero exclusions",
    )

    # --- Tripwire 5: negative-control CI narrower than comparable-n positive-control CI ---
    neg_rows = [r for r in lr_rows if r.get("control_type") == "negative_control"]
    pos_rows = [r for r in lr_rows if r.get("control_type") == "positive_control"]
    control_flags = []
    for neg, pos in [(n, p) for n in neg_rows for p in pos_rows]:
        neg_n = to_int(neg["n_pathogenic"], "n_pathogenic", neg.get("stratum", "?")) + to_int(neg["n_benign"], "n_benign", neg.get("stratum", "?"))
        pos_n = to_int(pos["n_pathogenic"], "n_pathogenic", pos.get("stratum", "?")) + to_int(pos["n_benign"], "n_benign", pos.get("stratum", "?"))
        if pos_n == 0:
            continue
        n_diff_pct = abs(neg_n - pos_n) / pos_n * 100.0
        if n_diff_pct > CONTROL_N_BAND_PCT:
            continue  # not comparable n
        neg_width = to_float(neg["ci_high"], "ci_high", neg.get("stratum", "?")) - to_float(neg["ci_low"], "ci_low", neg.get("stratum", "?"))
        pos_width = to_float(pos["ci_high"], "ci_high", pos.get("stratum", "?")) - to_float(pos["ci_low"], "ci_low", pos.get("stratum", "?"))
        if neg_width < pos_width:
            control_flags.append(
                f"{neg.get('stratum')} (n={neg_n}, width={neg_width:.3f}) narrower than "
                f"{pos.get('stratum')} (n={pos_n}, width={pos_width:.3f}) at comparable n"
            )
    report.check(
        f"no negative-control CI is narrower than a comparable-n (±{CONTROL_N_BAND_PCT}%) positive-control CI",
        len(control_flags) == 0,
        "; ".join(control_flags) if control_flags else f"{len(neg_rows)} negative-control / {len(pos_rows)} positive-control row(s) compared, no violation",
    )

    report.print_and_exit()


if __name__ == "__main__":
    main()
