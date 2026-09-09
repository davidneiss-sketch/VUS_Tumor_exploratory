#!/usr/bin/env python3
"""P-AMD-3a -- re-run of P-DIAG-1's STEP 1/STEP 4 seed-variation sweep, on
the CORRECTED (subtype-blind) mixture computation, per this task's own
explicit instruction to re-establish the shrinkage attribution on the
corrected computation.

Repeats the FULL, fixed-population (n=1848/1848, no subsampling) patient
-clustered bootstrap under multiple independent seeds, for BOTH arms,
using production_v2_run.py's now-CORRECTED bootstrap_ci_mixture (P-AMD-3a
fix), and reports the resulting spread of the upper CI bound -- same
method, same disclosed B and seed-count reduction as P-DIAG-1's own
residual_diagnosis_seed_variation.py, applied to the corrected estimand.

SIMULATED: read-only imports; does not modify PROTOCOL.md,
logistic_estimator.py, or simulate.py. Written only to mixture_fix/,
separate from production_v2/ and from residual_diagnosis/ (left
untouched as P-DIAG-1's historical pre-fix record).

Run: python3 mixture_fix_seed_variation.py
"""
from __future__ import annotations

import csv
import random
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import logistic_estimator as le  # noqa: E402
import production_v2_run as prod  # noqa: E402 -- CORRECTED bootstrap_ci_mixture

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
OUT_DIR = REPO_ROOT / "mixture_fix"

N_SEEDS = 15
B_DIAGNOSTIC = 500  # same disclosed reduction as P-DIAG-1 (committed run's own B=2000)
SEED_BASE = 89000000  # ARBITRARY, disclosed, distinct from every other seed used this session
REF_COVARIATES = {"purity": 0.5, "wgd": 0}
CV_SELECTED_LAMBDA = {"CORE_HR": 30.0, "DDR_SIGNALING": 100.0}  # verified this task, same grid points as before


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

    all_rows = []
    summary = {}
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        injected = float(truth_by_quantity[f"{arm.lower()}_joint_LR"]["injected_value"])
        lam = CV_SELECTED_LAMBDA[arm]

        upper_bounds, lower_bounds = [], []
        print(f"\n--- {arm}: {N_SEEDS} seeds, B={B_DIAGNOSTIC} each (CORRECTED subtype-blind design) ---")
        for seed_idx in range(N_SEEDS):
            seed = SEED_BASE + seed_idx * 1000 + hash(arm) % 997
            rng = random.Random(seed)
            ci_low, ci_high, replicates = prod.bootstrap_ci_mixture(
                path_records, benign_records, le.EVAL_POINT, REF_COVARIATES["purity"],
                REF_COVARIATES["wgd"], lam, rng, B_DIAGNOSTIC)
            point = statistics.median(replicates)
            upper_bounds.append(ci_high)
            lower_bounds.append(ci_low)
            all_rows.append({"arm": arm, "seed_index": seed_idx, "seed": seed, "b": B_DIAGNOSTIC,
                              "ci_low": ci_low, "ci_high": ci_high, "bootstrap_median": point,
                              "contains_injected": ci_low <= injected <= ci_high})
            print(f"  seed {seed_idx:2d} (seed={seed}): CI=[{ci_low:.4f}, {ci_high:.4f}]  "
                  f"contains_injected={ci_low <= injected <= ci_high}")

        mean_upper = statistics.mean(upper_bounds)
        se_upper = statistics.stdev(upper_bounds)
        mean_lower = statistics.mean(lower_bounds)
        se_lower = statistics.stdev(lower_bounds)
        n_containing = sum(1 for r in all_rows if r["arm"] == arm and r["contains_injected"])

        summary[arm] = {
            "injected": injected, "mean_upper_bound": mean_upper, "se_upper_bound": se_upper,
            "mean_lower_bound": mean_lower, "se_lower_bound": se_lower,
            "n_seeds_containing_injected": n_containing, "n_seeds_total": N_SEEDS,
        }
        print(f"  {arm}: mean upper bound={mean_upper:.4f}, SE(upper, B={B_DIAGNOSTIC})={se_upper:.4f}")
        print(f"  {arm}: {n_containing}/{N_SEEDS} seeds' CI contains the injected value {injected:.4f}")
        print(f"  elapsed so far: {time.time()-t_start:.1f}s")

    out_path = OUT_DIR / "SIMULATED_SEED_VARIATION_POST_FIX.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "seed_index", "seed", "b", "ci_low", "ci_high", "bootstrap_median", "contains_injected"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(all_rows)} rows)")

    summary_path = OUT_DIR / "SIMULATED_SEED_VARIATION_POST_FIX_SUMMARY.tsv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "injected", "mean_upper_bound", "se_upper_bound", "mean_lower_bound", "se_lower_bound",
                "n_seeds_containing_injected", "n_seeds_total"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for arm, s in summary.items():
            w.writerow({"arm": arm, **s})
    print(f"Wrote {summary_path}")
    print(f"\nTotal elapsed: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
