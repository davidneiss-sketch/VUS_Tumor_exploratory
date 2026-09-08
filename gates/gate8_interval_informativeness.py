#!/usr/bin/env python3
"""GATE 8 — Interval informativeness. NEW AND MANDATORY (per this task):
runs against PRODUCTION output files on every pipeline invocation,
alongside gate5 and gate6 (see DEPLOYMENT_LOG.md), not only against test
fixtures.

The problem this gate exists to catch: an ACMG-mapping rule (PROTOCOL.md
§9) that only looks at which side of a threshold the CI LOWER bound falls
on will assign a strength to ANY interval, no matter how wide, skewed, or
numerically degenerate. `STAKE_ANALYSIS.md`'s ablation (P-DEC-1) produced
a row with CI = [759.6, 3.65e9] -- read by §9's rule exactly as written,
that is `PATHOGENIC_VERY_STRONG` (8 ACMG points, the maximum tier), from
an estimator whose own bootstrap distribution has a multi-order-of-
magnitude-heavier right tail than its median (see `INTERVAL_INSTABILITY.md`
and `STAKE_ANALYSIS.md` Step 2 for the verified mechanism: Silverman-
bandwidth Gaussian KDE evaluated near a zero-inflated small sample's
sparse tail). Existing gates do not catch this: gate4 only checks that a
CI contains its own point estimate and that widths vary across strata --
both hold here. This gate adds two further, independent checks that a
*wide-but-internally-consistent* interval can still fail.

Per PROTOCOL.md §9 (copied verbatim, boundaries only -- gate8 does not
read this from PROTOCOL.md at runtime, matching gate6_recovery.py's own
precedent of hardcoding PROTOCOL-sourced numeric constants with a
citation, not live-parsing them):

  OddsPath boundaries, pathogenic side: 2.08, 4.33, 18.7, 350
  OddsPath boundaries, benign side (reciprocals): 0.48, 0.053

======================================================================
THRESHOLDS -- PRE-SPECIFIED HERE, WITH RATIONALE, BEFORE THIS GATE IS
RUN AGAINST ANY EXISTING OUTPUT (this file was written and these two
constants fixed before gate8 was ever invoked against ABLATION_TABLE.tsv
-- see INTERVAL_INSTABILITY.md and the commit history for the order of
operations). Neither value was chosen by looking at which rows would
pass or fail; both are derived from properties of the OddsPath ladder
itself, which is a *fixed pre-registered target*, not something this
task discovered by looking at ABLATION_TABLE.tsv's specific numbers.
======================================================================

1. MAX_TIERS_SPANNED = 2. A CI is `UNINFORMATIVE` if it spans MORE than 2
   of the ACMG tiers PROTOCOL.md §9 defines (BENIGN_STRONG,
   BENIGN_SUPPORTING, NO_EVIDENCE, PATHOGENIC_SUPPORTING,
   PATHOGENIC_MODERATE, PATHOGENIC_STRONG, PATHOGENIC_VERY_STRONG) --
   i.e. it may straddle at most ONE tier boundary (2 adjacent tiers),
   reflecting ordinary estimation uncertainty about which side of a
   single boundary the true value sits on. Crossing 2+ boundaries (3+
   tiers) means the interval cannot distinguish between ACMG calls that
   differ by several evidence points (e.g. SUPPORTING=1 point vs.
   VERY_STRONG=8 points) -- that is not "some uncertainty about the
   exact tier," it is "no information about the tier at all."

2. MAX_UPPER_POINT_RATIO = 18.7. The CI upper bound must not exceed the
   point estimate by more than this multiplicative factor. Derived, not
   picked freely: 350 / 18.7 ≈ 18.72 is the ratio between the two LARGEST
   adjacent boundaries on PROTOCOL's own OddsPath ladder (VERY_STRONG's
   floor over STRONG's floor) -- the single widest "one tier's worth" of
   multiplicative room the ladder itself contains anywhere on it. Using
   18.7 (already a named PROTOCOL.md constant, not a new invented number)
   as the ceiling says: an interval may be no wider, relative to its own
   point estimate, than the single widest tier the pre-registered ladder
   defines. Anything wider than that is not "imprecise," it has lost the
   point estimate's information content entirely.

3. ABSOLUTE_UPPER_CEILING = 10000. Independent of the point estimate:
   PROTOCOL.md §9 defines no tier above `PATHOGENIC_VERY_STRONG` (CI
   lower bound > 350) -- there is no ACMG-evidentiary distinction between
   a CI upper bound of 351 and one of 3.65 BILLION; both saturate the
   same, highest, tier. 10000 is fixed as ~28.6x the highest MEANINGFUL
   boundary (350), generous headroom for a genuinely very-strong, still
   physically plausible finding (every SYNTHETIC_FULL_N point estimate in
   this project's own existing output tops out in the low hundreds), while
   catching anything that reaches multiple orders of magnitude beyond any
   evidentiary meaning as the numerical degeneracy it is.

A row fails EITHER check independently -- both are checked, both are
reported, and a row failing either is `UNINFORMATIVE` regardless of the
other.

Usage:
  gate8_interval_informativeness.py --table FILE --id-cols COL[,COL...]
      --point-col NAME --ci-low-col NAME --ci-high-col NAME --outdir DIR

Exit 0 = every row with a computable interval is INFORMATIVE (or
correctly marked NOT_APPLICABLE, e.g. INSUFFICIENT_N). Exit 1 = at least
one row is UNINFORMATIVE.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_float, write_tsv  # noqa: E402

# PROTOCOL.md §9, copied verbatim (see gate8's own docstring above for why
# this is hardcoded rather than live-parsed, matching gate6_recovery.py's
# precedent).
ODDSPATH_BOUNDARIES = [0.053, 0.48, 2.08, 4.33, 18.7, 350.0]
TIER_LABELS = [  # in ascending-LR order, one more than len(ODDSPATH_BOUNDARIES)
    "BENIGN_STRONG", "BENIGN_SUPPORTING", "NO_EVIDENCE",
    "PATHOGENIC_SUPPORTING", "PATHOGENIC_MODERATE", "PATHOGENIC_STRONG",
    "PATHOGENIC_VERY_STRONG",
]

MAX_TIERS_SPANNED = 2               # see docstring rationale #1
MAX_UPPER_POINT_RATIO = 18.7        # see docstring rationale #2
ABSOLUTE_UPPER_CEILING = 10000.0    # see docstring rationale #3

OUTPUT_COLUMNS = ["row_id", "point_estimate", "ci_low", "ci_high", "tiers_spanned",
                   "upper_point_ratio", "acmg_tier", "gate8_status", "reason"]


def tier_of(value: float) -> str:
    idx = 0
    for b in ODDSPATH_BOUNDARIES:
        if value > b:
            idx += 1
        else:
            break
    return TIER_LABELS[idx]


def tiers_spanned(ci_low: float, ci_high: float) -> int:
    """1 + the number of OddsPath boundaries strictly inside (ci_low,
    ci_high) -- a CI entirely within one tier spans 1 tier; crossing one
    boundary spans 2; etc."""
    crossed = sum(1 for b in ODDSPATH_BOUNDARIES if ci_low < b < ci_high)
    return crossed + 1


def evaluate_row(row_id: str, point: float, ci_low: float, ci_high: float) -> dict:
    reasons = []
    span = tiers_spanned(ci_low, ci_high)
    if span > MAX_TIERS_SPANNED:
        reasons.append(f"interval spans {span} ACMG tiers (from {tier_of(ci_low)} to {tier_of(ci_high)}), "
                        f"exceeding MAX_TIERS_SPANNED={MAX_TIERS_SPANNED}")

    ratio = (ci_high / point) if point > 0 else float("inf")
    if point <= 0:
        reasons.append(f"point estimate {point} is not a positive LR -- upper/point ratio is undefined")
    elif ratio > MAX_UPPER_POINT_RATIO:
        reasons.append(f"CI upper bound is {ratio:.2f}x the point estimate, exceeding "
                        f"MAX_UPPER_POINT_RATIO={MAX_UPPER_POINT_RATIO}")

    if ci_high > ABSOLUTE_UPPER_CEILING:
        reasons.append(f"CI upper bound {ci_high:g} exceeds ABSOLUTE_UPPER_CEILING={ABSOLUTE_UPPER_CEILING:g}")

    status = "UNINFORMATIVE" if reasons else "INFORMATIVE"
    return {
        "row_id": row_id, "point_estimate": point, "ci_low": ci_low, "ci_high": ci_high,
        "tiers_spanned": span, "upper_point_ratio": round(ratio, 4) if ratio != float("inf") else "inf",
        "acmg_tier": "" if status == "UNINFORMATIVE" else tier_of(point),
        "gate8_status": status,
        "reason": "; ".join(reasons) if reasons else "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True, type=Path)
    ap.add_argument("--id-cols", required=True, help="Comma-separated column name(s) identifying each row.")
    ap.add_argument("--point-col", required=True)
    ap.add_argument("--ci-low-col", required=True)
    ap.add_argument("--ci-high-col", required=True)
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args()

    report = GateReport("gate8_interval_informativeness")

    try:
        rows = read_tsv(args.table)
    except FileNotFoundError as e:
        report.check("input table present", False, str(e))
        report.print_and_exit()
        return
    report.check("input table present", True, f"{args.table.name} ({len(rows)} rows)")

    id_cols = args.id_cols.split(",")
    out_rows = []
    n_informative = n_uninformative = n_not_applicable = 0

    for r in rows:
        row_id = "/".join(r.get(c, "") for c in id_cols)
        point_s, lo_s, hi_s = r.get(args.point_col, ""), r.get(args.ci_low_col, ""), r.get(args.ci_high_col, "")
        if not point_s or not lo_s or not hi_s:
            out_rows.append({
                "row_id": row_id, "point_estimate": "", "ci_low": "", "ci_high": "",
                "tiers_spanned": "", "upper_point_ratio": "", "acmg_tier": "",
                "gate8_status": "NOT_APPLICABLE", "reason": "no computable interval on this row (e.g. INSUFFICIENT_N)",
            })
            n_not_applicable += 1
            continue
        point = to_float(point_s, args.point_col, row_id)
        ci_low = to_float(lo_s, args.ci_low_col, row_id)
        ci_high = to_float(hi_s, args.ci_high_col, row_id)
        evaluated = evaluate_row(row_id, point, ci_low, ci_high)
        out_rows.append(evaluated)
        if evaluated["gate8_status"] == "INFORMATIVE":
            n_informative += 1
        else:
            n_uninformative += 1

    args.outdir.mkdir(parents=True, exist_ok=True)
    out_path = args.outdir / "SIMULATED_GATE8_INTERVAL_REPORT.tsv"
    write_tsv(out_path, out_rows, OUTPUT_COLUMNS)

    report.check("SIMULATED_GATE8_INTERVAL_REPORT.tsv emitted", True,
                 f"{out_path} ({len(out_rows)} rows: {n_informative} INFORMATIVE, "
                 f"{n_uninformative} UNINFORMATIVE, {n_not_applicable} NOT_APPLICABLE)")
    report.check("every row with a computable interval is INFORMATIVE",
                 n_uninformative == 0,
                 "no row exceeded either threshold" if n_uninformative == 0
                 else f"{n_uninformative} row(s) UNINFORMATIVE — see {out_path.name} for detail")

    report.print_and_exit()


if __name__ == "__main__":
    main()
