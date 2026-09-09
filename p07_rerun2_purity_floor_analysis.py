#!/usr/bin/env python3
"""P07-RERUN2 STEP 5 -- re-derive the purity x depth operating region on
the CURRENT (post-P06R4, subtype-latent) simulator, pooled AND per PAM50
subtype, to check whether P07's original 0.25 purity-floor proposal
(PROPOSED_DEVIATIONS.md section 1, derived on the pre-subtype simulator)
still holds -- and specifically whether it holds WITHIN each subtype or
only pooled (this task's own explicit framing: "A floor that works
pooled but fails in Basal is not a usable floor, and Basal is where the
study's evidence is expected to be strongest.").

Method: identical to PROPOSED_DEVIATIONS.md section 1's own "clean
direction accuracy" metric -- excludes true-AMBIGUOUS/NOT_EVALUABLE loci
(scored against a category that has no single correct direction answer
by construction), 0.05-wide purity bands, n reported for every cell.

SIMULATED: read-only import of loh_caller.py's own load_loci() (no
modification, no re-derivation of the caller's method) plus this
script's own binning/aggregation. Writes only to
SIMULATED_loh_validation/, does not modify simulate.py, PROTOCOL.md, or
loh_caller.py.

Run: python3 p07_rerun2_purity_floor_analysis.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import loh_caller as lc  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
OUT_DIR = REPO_ROOT / "SIMULATED_loh_validation"

PURITY_BAND_WIDTH = 0.05
MIN_PURITY, MAX_PURITY = 0.10, 0.95
HIGH_RELIABILITY_THRESHOLD = 0.95  # PROPOSED_DEVIATIONS.md section 1's own ">=95%" bar


def purity_bands() -> list[tuple[str, float, float]]:
    bands = []
    lo = MIN_PURITY
    while lo < MAX_PURITY - 1e-9:
        hi = round(lo + PURITY_BAND_WIDTH, 2)
        bands.append((f"{lo:.2f}-{hi:.2f}", lo, hi))
        lo = hi
    return bands


def clean_accuracy_by_purity(loci: list[dict]) -> list[dict]:
    rows = []
    for band_name, lo, hi in purity_bands():
        in_band = [r for r in loci if lo <= r["purity"] < hi]
        # "Clean" metric, per PROPOSED_DEVIATIONS.md section 1: exclude
        # true-AMBIGUOUS/NOT_EVALUABLE loci (no single correct direction
        # answer by construction), score only definitive-truth loci.
        clean = [r for r in in_band if r["true_direction_category"] not in ("AMBIGUOUS", "NOT_EVALUABLE")]
        excluded = [r for r in in_band if r["true_direction_category"] in ("AMBIGUOUS", "NOT_EVALUABLE")]
        if not clean:
            continue
        n_correct = sum(1 for r in clean if r["correct"])
        accuracy = round(n_correct / len(clean), 6)
        rows.append({
            "purity_band": band_name, "n_clean_definitive": len(clean), "n_excluded_ambiguous_ne": len(excluded),
            "n_correct": n_correct, "accuracy": accuracy,
        })
    return rows


def main() -> None:
    print(BANNER)
    loci, _ = lc.load_loci()

    all_rows = []
    print("\n=== POOLED (all subtypes) ===")
    for r in clean_accuracy_by_purity(loci):
        r["subtype"] = "POOLED"
        all_rows.append(r)
        print(f"  {r['purity_band']}: n={r['n_clean_definitive']} (excluded {r['n_excluded_ambiguous_ne']}) "
              f"accuracy={r['accuracy']:.4f}")

    for subtype in lc.PAM50_SUBTYPES:
        loci_st = [r for r in loci if r["pam50_subtype"] == subtype]
        print(f"\n=== {subtype} ===")
        for r in clean_accuracy_by_purity(loci_st):
            r["subtype"] = subtype
            all_rows.append(r)
            print(f"  {r['purity_band']}: n={r['n_clean_definitive']} (excluded {r['n_excluded_ambiguous_ne']}) "
                  f"accuracy={r['accuracy']:.4f}")

    out_path = OUT_DIR / "SIMULATED_PURITY_FLOOR_BY_SUBTYPE.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        cols = ["subtype", "purity_band", "n_clean_definitive", "n_excluded_ambiguous_ne", "n_correct", "accuracy"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(all_rows)} rows)")

    # First purity band (reading upward) at which each subtype (and
    # pooled) reaches >=95% clean accuracy AND stays >=95% for every
    # band above it (a "floor", not a lucky single band) -- computed,
    # not asserted.
    print(f"\n=== First purity band reaching and holding >= {HIGH_RELIABILITY_THRESHOLD:.0%} clean accuracy ===")
    for subtype_name in ["POOLED"] + lc.PAM50_SUBTYPES:
        rows_for_subtype = [r for r in all_rows if r["subtype"] == subtype_name]
        floor_band = None
        for i, r in enumerate(rows_for_subtype):
            if all(rr["accuracy"] >= HIGH_RELIABILITY_THRESHOLD for rr in rows_for_subtype[i:]):
                floor_band = r["purity_band"]
                break
        n_at_floor = next((r["n_clean_definitive"] for r in rows_for_subtype
                            if r["purity_band"] == floor_band), None) if floor_band else None
        print(f"  {subtype_name:12s}: floor={floor_band!r} (n at that band={n_at_floor})"
              if floor_band else f"  {subtype_name:12s}: NEVER reaches/holds >= {HIGH_RELIABILITY_THRESHOLD:.0%} "
                                  f"in the tested range -- reported explicitly, not silently omitted")


if __name__ == "__main__":
    main()
