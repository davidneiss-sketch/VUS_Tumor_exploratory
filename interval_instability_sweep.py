#!/usr/bin/env python3
"""interval_instability_sweep.py -- P-DEC-1 follow-up: characterize the
class size below which PROTOCOL.md §7.1's estimator produces gate8-
UNINFORMATIVE intervals, by feature-vector dimension.

Reuses stake_ablation.py's estimator (Gaussian KDE + Jeffreys proportion +
product-of-marginals joint LR) and gate8_interval_informativeness.py's own
informativeness check, both read-only imports -- does not modify either
file, or simulate.py/signatures.py/loh_caller.py/PROTOCOL.md.

Run: python3 interval_instability_sweep.py
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "gates"))
import stake_ablation as sa  # noqa: E402
import gate8_interval_informativeness as g8  # noqa: E402

LOCAL_SEED = 20260909  # ARBITRARY, disclosed, local to this script only

N_VALUES = [12, 15, 20, 25, 30, 40, 50, 65, 75, 100, 130, 160]
R_REPEATS = 15   # independent random subsamples per (arm, dim, n) cell
B_SWEEP = 300    # bootstrap replicates per trial, reduced from PROTOCOL's B=2000
                 # for tractability across this sweep's ~1000+ trials (disclosed,
                 # not silent -- Standing Rule 4); each individual STAKE_ANALYSIS.md
                 # table row still used the fuller B=500/B=2000 as appropriate.

DIMENSIONS = [
    (1, "SBS3_ONLY", ("sbs3",)),
    (2, "LOH_SBS3", ("wt_lost", "sbs3")),
    (3, "LOH_GIS_SBS3", ("wt_lost", "gis", "sbs3")),
]


def run_one_trial(arm: str, subset: tuple, n: int, all_path: list, all_benign: list, rng: random.Random) -> str:
    n_path = min(n, len(all_path))
    n_benign = min(n, len(all_benign))
    path_sub = rng.sample(all_path, n_path)
    benign_sub = rng.sample(all_benign, n_benign)
    path = sa.pool_features(path_sub)
    benign = sa.pool_features(benign_sub)
    if n_path + n_benign < 20:
        return "INSUFFICIENT_N"
    try:
        point = sa.joint_lr_for_subset(subset, path, benign)
        ci_low, ci_high, _ = sa.bootstrap_ci(subset, path, benign, rng, B_SWEEP)
    except ZeroDivisionError:
        # A finer-grained failure mode than "UNINFORMATIVE": at small
        # enough n, the Gaussian-kernel density at EVAL_POINT can
        # underflow to exactly 0.0 in floating point for one class (no
        # resampled point close enough, relative to the tiny Silverman
        # bandwidth, to leave a nonzero sum) -- the LR is not merely wide,
        # it is UNDEFINED. Not caught by gate8 at all (gate8 only ever
        # sees a table row that already has numbers in it) -- reported
        # here as its own, more severe category.
        return "ZERO_DENSITY_UNDEFINED"
    evaluated = g8.evaluate_row(f"{arm}/{n}", point, ci_low, ci_high)
    return evaluated["gate8_status"]


def main() -> None:
    pop = sa.load_population()
    rng = random.Random(LOCAL_SEED)

    rows = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        all_path = [r for r in pop if r["arm"] == arm and r["true_class"] == "Pathogenic"]
        all_benign = [r for r in pop if r["arm"] == arm and r["true_class"] == "Benign"]
        for dim, label, subset in DIMENSIONS:
            for n in N_VALUES:
                statuses = [run_one_trial(arm, subset, n, all_path, all_benign, rng) for _ in range(R_REPEATS)]
                n_uninformative = sum(1 for s in statuses if s == "UNINFORMATIVE")
                n_informative = sum(1 for s in statuses if s == "INFORMATIVE")
                n_insufficient = sum(1 for s in statuses if s == "INSUFFICIENT_N")
                n_zero_density = sum(1 for s in statuses if s == "ZERO_DENSITY_UNDEFINED")
                n_bad = n_uninformative + n_zero_density  # both are "not a usable interval"
                rows.append({
                    "arm": arm, "dimension": dim, "feature_subset": label, "n_per_class": n,
                    "r_repeats": R_REPEATS, "n_uninformative": n_uninformative,
                    "n_zero_density_undefined": n_zero_density,
                    "n_informative": n_informative, "n_insufficient": n_insufficient,
                    "not_usable_fraction": round(n_bad / R_REPEATS, 4),
                })
                print(f"{arm}\t{label}\tn={n}\tUNINFORMATIVE={n_uninformative}/{R_REPEATS}\tZERO_DENSITY={n_zero_density}/{R_REPEATS}")

    out_path = REPO_ROOT / "SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv"
    columns = ["arm", "dimension", "feature_subset", "n_per_class", "r_repeats",
               "n_uninformative", "n_zero_density_undefined", "n_informative", "n_insufficient",
               "not_usable_fraction"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
