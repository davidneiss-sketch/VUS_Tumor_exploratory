#!/usr/bin/env python3
"""P-AMD-3b Part D -- confirm every tier movement CONSERVATIVE_ASSIGNMENT_ANALYSIS.md
identifies (and every one gate6_recovery.py's new NEAR_TIER_BOUNDARY
column can flag) is CONSERVATIVE: the estimator's known downward
(pathogenic-direction) shrinkage bias should only ever cause an
UNDER-call (recovered ACMG tier <= true tier), never an OVER-call. This
is a real, distinct finding if false -- per this task's own explicit
instruction, a non-conservative movement means HALT and do not add the
shrinkage-property disclosure text to PROTOCOL.md.

Method: for every pathogenic-direction (injected > 1) quantity with both
a recovered CI and a declared bias-prediction entry, compares the ACMG-
equivalent tier (PROTOCOL.md §9's OddsPath thresholds) the INJECTED
(true) value alone would receive against the tier the RECOVERED CI LOWER
BOUND receives. "Conservative" means recovered tier's points <= true
tier's points (same tier, or a LOWER one) -- never a HIGHER one.

SIMULATED: read-only imports of gate6_recovery.py's own
ODDSPATH_PATHOGENIC_BOUNDARIES table (not re-derived independently) and
csv reads of SIMULATED_TRUTH.tsv / production_v2's own recovered and
bias-prediction files. Does not modify any file it reads. Writes only
CONFIRM_TIER_DIRECTIONALITY_RESULT.md.

Run: python3 scripts/confirm_tier_directionality.py
Exit 0 = every checked movement is conservative. Exit 1 = at least one
movement is NON-conservative (an over-call) -- HALT condition.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "gates"))
from gate6_recovery import ODDSPATH_PATHOGENIC_BOUNDARIES  # noqa: E402 -- read-only import, not re-derived

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

TRUTH_PATH = REPO_ROOT / "SIMULATED_TRUTH.tsv"
RECOVERED_PATH = REPO_ROOT / "production_v2" / "SIMULATED_RECOVERED.tsv"
BIAS_PREDICTION_PATH = REPO_ROOT / "production_v2" / "SIMULATED_BIAS_PREDICTION.tsv"
OUT_PATH = REPO_ROOT / "CONFIRM_TIER_DIRECTIONALITY_RESULT.md"


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def tier_for_value(value: float) -> tuple[str, int]:
    """Returns (tier_name, points) for a pathogenic-direction LR value
    against PROTOCOL.md §9's boundaries (highest first). Below the lowest
    boundary -> NO_EVIDENCE, 0 points."""
    for boundary, tier_name, points in ODDSPATH_PATHOGENIC_BOUNDARIES:
        if value > boundary:
            return tier_name, points
    return "NO_EVIDENCE", 0


def main() -> None:
    print(BANNER)
    truth_by_quantity = {r["quantity"]: r for r in read_tsv(TRUTH_PATH)}
    recovered_by_quantity = {r["quantity"]: r for r in read_tsv(RECOVERED_PATH)}
    bias_prediction_by_quantity = {r["quantity"]: r for r in read_tsv(BIAS_PREDICTION_PATH)}

    rows = []
    any_non_conservative = False
    for q, pred_row in bias_prediction_by_quantity.items():
        truth_row = truth_by_quantity.get(q)
        rec_row = recovered_by_quantity.get(q)
        if truth_row is None or rec_row is None:
            print(f"[SKIP] {q}: missing truth or recovered row")
            continue
        injected = float(truth_row["injected_value"])
        if injected <= 1.0:
            print(f"[SKIP] {q}: not a pathogenic-direction quantity (injected={injected})")
            continue
        ci_low = float(rec_row["ci_low"])
        recovered_point = float(rec_row["recovered_point"])

        true_tier, true_points = tier_for_value(injected)
        recovered_tier, recovered_points = tier_for_value(ci_low)
        conservative = recovered_points <= true_points
        if not conservative:
            any_non_conservative = True

        verdict = "CONSERVATIVE" if conservative else "NON-CONSERVATIVE (OVER-CALL)"
        print(f"[{verdict}] {q}: injected={injected:.6f} -> true_tier={true_tier} ({true_points} pts); "
              f"recovered_point={recovered_point:.6f}, ci_low={ci_low:.6f} -> recovered_tier={recovered_tier} "
              f"({recovered_points} pts)")

        rows.append({
            "quantity": q, "injected": injected, "true_tier": true_tier, "true_points": true_points,
            "recovered_point": recovered_point, "ci_low": ci_low, "recovered_tier": recovered_tier,
            "recovered_points": recovered_points, "verdict": verdict,
        })

    overall = "ALL MOVEMENTS CONSERVATIVE" if not any_non_conservative else "NON-CONSERVATIVE MOVEMENT FOUND -- HALT"
    print(f"\nOVERALL: {overall}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(f"{BANNER}\n\n")
        f.write("# CONFIRM_TIER_DIRECTIONALITY_RESULT.md — P-AMD-3b Part D directionality confirmation\n\n")
        f.write("SIMULATED: verifies every tier movement identified by the estimator's known shrinkage "
                "bias is conservative (recovered ACMG tier <= true tier), per this task's own explicit "
                "HALT condition. Compares the tier PROTOCOL.md §9's OddsPath thresholds would assign to "
                "the INJECTED (true) value against the tier assigned to the RECOVERED CI lower bound, for "
                "every pathogenic-direction quantity with a declared bias-prediction entry.\n\n")
        f.write("| quantity | injected | true_tier | true_points | recovered_point | ci_low | "
                "recovered_tier | recovered_points | verdict |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['quantity']} | {r['injected']:.6f} | {r['true_tier']} | {r['true_points']} | "
                     f"{r['recovered_point']:.6f} | {r['ci_low']:.6f} | {r['recovered_tier']} | "
                     f"{r['recovered_points']} | {r['verdict']} |\n")
        f.write(f"\n**OVERALL: {overall}**\n")
    print(f"\nWrote {OUT_PATH}")

    sys.exit(1 if any_non_conservative else 0)


if __name__ == "__main__":
    main()
