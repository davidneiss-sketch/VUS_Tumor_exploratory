#!/usr/bin/env python3
"""P-DIAG-1 STEP 1 and STEP 4 -- Monte Carlo error on the CI endpoints.

Repeats the FULL, fixed-population (n=1848/1848, no subsampling) patient
-clustered bootstrap under multiple independent seeds, for BOTH arms
(STEP 1 for CORE_HR, STEP 4 for DDR_SIGNALING's pass-robustness), and
reports the resulting spread of the upper CI bound.

SIMULATED: read-only imports of logistic_estimator.py, simulate.py, and
production_v2_run.py's own mixture bootstrap function (unmodified, called
as-is). Does NOT change lambda, the bootstrap replicate count used in the
COMMITTED production run, the seed used there, or any estimator
parameter -- this diagnostic script uses its OWN, separate, disclosed
seed set and a REDUCED B (see below), written only to
residual_diagnosis/, never touching production_v2/ or any other
committed artifact.

B_DIAGNOSTIC=500 (reduced from the committed run's B=2000) across
N_SEEDS=15 independent seeds, per arm -- disclosed reduction for
tractability (15 seeds x 2 arms x 500 replicates x ~0.11s/fit =~ 28
minutes), per Standing Rule 4. This is enough to characterize the ORDER
OF MAGNITUDE of seed-to-seed Monte Carlo noise on the upper percentile
estimate; STEP 1's own "how large would B need to be" question is
answered analytically below using the classical percentile-SE scaling
law (SE ~ 1/sqrt(B)), calibrated against this run's own empirical SE at
B=500 -- not by brute-force running B=2000 many times over, which the
task's own runtime-cost framing anticipates as a real question, not a
free experiment.

Run: python3 residual_diagnosis_seed_variation.py
"""
from __future__ import annotations

import csv
import math
import random
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import logistic_estimator as le  # noqa: E402
import production_v2_run as prod  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
OUT_DIR = REPO_ROOT / "residual_diagnosis"

N_SEEDS = 15
B_DIAGNOSTIC = 500  # reduced from the committed run's B=2000, disclosed
B_COMMITTED = 2000  # for the SE-scaling extrapolation only, not re-run here
SEED_BASE = 88000000  # ARBITRARY, disclosed, distinct from every other seed this session (LOCAL_SEED=20260910 etc.)
REF_COVARIATES = {"purity": 0.5, "wgd": 0}

CI_MISS_TO_EXPLAIN = 0.0529  # CORE_HR: 5.826333 - 5.773397 (the committed run's own upper bound)


def main() -> None:
    print(BANNER)
    t_start = time.time()
    OUT_DIR.mkdir(exist_ok=True)

    pop = le.load_population()
    pop_by_arm = {"CORE_HR": {"Pathogenic": [], "Benign": []}, "DDR_SIGNALING": {"Pathogenic": [], "Benign": []}}
    for r in pop:
        pop_by_arm[r["arm"]][r["true_class"]].append(r)

    truth_by_quantity = {}
    with open(REPO_ROOT / "SIMULATED_TRUTH.tsv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            truth_by_quantity[row["quantity"]] = row

    CV_SELECTED_LAMBDA = {"CORE_HR": 30.0, "DDR_SIGNALING": 100.0}

    all_rows = []
    summary = {}
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        injected = float(truth_by_quantity[f"{arm.lower()}_joint_LR"]["injected_value"])
        lam = CV_SELECTED_LAMBDA[arm]

        upper_bounds, lower_bounds, points = [], [], []
        print(f"\n--- {arm}: {N_SEEDS} seeds, B={B_DIAGNOSTIC} each ---")
        for seed_idx in range(N_SEEDS):
            seed = SEED_BASE + seed_idx * 1000 + hash(arm) % 997
            rng = random.Random(seed)
            ci_low, ci_high, replicates = prod.bootstrap_ci_mixture(
                path_records, benign_records, le.EVAL_POINT, REF_COVARIATES["purity"],
                REF_COVARIATES["wgd"], lam, rng, B_DIAGNOSTIC)
            point = statistics.median(replicates)  # for reporting only; the committed run's own point comes from the full-data fit, unaffected by bootstrap seed
            upper_bounds.append(ci_high)
            lower_bounds.append(ci_low)
            points.append(point)
            all_rows.append({"arm": arm, "seed_index": seed_idx, "seed": seed, "b": B_DIAGNOSTIC,
                              "ci_low": ci_low, "ci_high": ci_high, "bootstrap_median": point,
                              "contains_injected": ci_low <= injected <= ci_high})
            print(f"  seed {seed_idx:2d} (seed={seed}): CI=[{ci_low:.4f}, {ci_high:.4f}]  "
                  f"contains_injected={ci_low <= injected <= ci_high}")

        mean_upper = statistics.mean(upper_bounds)
        se_upper = statistics.stdev(upper_bounds)  # empirical SE across seeds, at B_DIAGNOSTIC
        mean_lower = statistics.mean(lower_bounds)
        se_lower = statistics.stdev(lower_bounds)
        n_containing = sum(1 for r in all_rows if r["arm"] == arm and r["contains_injected"])

        # Classical percentile-SE scaling: SE(B) ~ SE(B_DIAGNOSTIC) * sqrt(B_DIAGNOSTIC / B)
        se_at_committed_b = se_upper * math.sqrt(B_DIAGNOSTIC / B_COMMITTED)

        summary[arm] = {
            "injected": injected, "mean_upper_bound": mean_upper, "se_upper_bound": se_upper,
            "mean_lower_bound": mean_lower, "se_lower_bound": se_lower,
            "n_seeds_containing_injected": n_containing, "n_seeds_total": N_SEEDS,
            "se_upper_bound_extrapolated_to_B_committed": se_at_committed_b,
        }
        print(f"  {arm}: mean upper bound={mean_upper:.4f}, SE(upper, B={B_DIAGNOSTIC})={se_upper:.4f}")
        print(f"  {arm}: extrapolated SE(upper, B={B_COMMITTED})={se_at_committed_b:.4f}")
        print(f"  {arm}: {n_containing}/{N_SEEDS} seeds' CI contains the injected value {injected:.4f}")
        print(f"  elapsed so far: {time.time()-t_start:.1f}s")

    # How large would B need to be for SE(upper) << 0.0529?
    core_hr_se_at_2000 = summary["CORE_HR"]["se_upper_bound_extrapolated_to_B_committed"]
    # SE(B) = SE(500) * sqrt(500/B)  =>  B = 500 * (SE(500)/target_SE)^2
    core_hr_se_at_500 = summary["CORE_HR"]["se_upper_bound"]
    for target_fraction in (0.5, 0.1):
        target_se = CI_MISS_TO_EXPLAIN * target_fraction
        if core_hr_se_at_500 > 0:
            required_b = B_DIAGNOSTIC * (core_hr_se_at_500 / target_se) ** 2
            per_fit_seconds = 0.112  # benchmarked this session at full n=1848, ~constant across lambda
            est_runtime_seconds = required_b * per_fit_seconds
            print(f"\nFor SE(upper) <= {target_fraction:.0%} of {CI_MISS_TO_EXPLAIN} ({target_se:.5f}): "
                  f"B ~= {required_b:,.0f}, estimated single-seed runtime ~= {est_runtime_seconds/60:.1f} min")

    out_path = OUT_DIR / "SIMULATED_SEED_VARIATION.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "seed_index", "seed", "b", "ci_low", "ci_high", "bootstrap_median", "contains_injected"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(all_rows)} rows)")

    summary_path = OUT_DIR / "SIMULATED_SEED_VARIATION_SUMMARY.tsv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "injected", "mean_upper_bound", "se_upper_bound", "mean_lower_bound", "se_lower_bound",
                "n_seeds_containing_injected", "n_seeds_total", "se_upper_bound_extrapolated_to_B_committed"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for arm, s in summary.items():
            w.writerow({"arm": arm, **s})
    print(f"Wrote {summary_path}")
    print(f"\nTotal elapsed: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
