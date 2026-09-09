#!/usr/bin/env python3
"""STEP 1 (calibration) and STEP 4 (log-linearity check) of the
logistic-regression-implementation task.

SIMULATED: read-only imports of simulate.py and logistic_estimator.py.
Does not modify PROTOCOL.md, simulate.py, or logistic_estimator.py.

Part A -- Calibration: 5-fold (variant-grouped = sample-grouped, per
logistic_estimator.py's own docstring) held-out reliability curve, Brier
score, and ECE, for both arms, using logistic_estimator.py's own
calibration_diagnostics() (real function, not re-implemented here).

Part B -- Log-linearity check, two independent methods:
  B1. Residual grid: the FITTED model's log-LR vs. simulate.py's own
      TRUE analytic log joint LR (simulate.joint_lr, which is exact for
      subtype=LumA -- SUBTYPE_Z_SHIFT/SUBTYPE_GIS_SHIFT are both 0.0 for
      LumA, confirmed in TRUTH_DELTA.md's subtype-fix addendum -- so this
      is a genuine ground-truth comparison, not an approximation of one),
      across a grid of (gis, sbs3) values, wt_lost/purity/subtype/wgd
      held fixed. Reports the residual (log fitted - log true) at every
      grid point -- a flat, near-zero residual across the grid supports
      log-linearity; a systematic trend across the grid is evidence
      against it.
  B2. Nested model comparison: an AUGMENTED model adds a
      gis_squared term and a gis*wt_lost interaction term to the base
      model; 5-fold CV mean deviance is compared between base and
      augmented. If the augmented model's held-out deviance is not
      meaningfully lower, that is evidence the base log-linear model is
      an adequate approximation (not proof of exactness).

Run: python3 logistic_calibration_and_loglinearity.py
"""
from __future__ import annotations

import csv
import math
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import simulate  # noqa: E402
import logistic_estimator as le  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
LOCAL_SEED = 20260910

CV_K = 5
GIS_GRID = [20.0, 30.0, 42.0, 55.0, 70.0]
SBS3_GRID = [0.05, 0.15, 0.30, 0.45, 0.60]
FIXED_FOR_GRID = {"wt_lost": 1, "purity": 0.5, "subtype": "LumA", "wgd": 0}


def part_a_calibration(pop_by_arm: dict, rng: random.Random) -> dict:
    results = {}
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        cv_result = le.select_lambda_cv(path_records, benign_records, CV_K, rng)
        lam = cv_result["lambda_1se"]
        calib = le.calibration_diagnostics(path_records, benign_records, lam, CV_K, rng)
        results[arm] = {"lambda_1se": lam, "lambda_min": cv_result["lambda_min"], **calib}
    return results


def build_augmented_design_row(record: dict, std_params: dict) -> list[float]:
    """Base design row + gis_squared (standardized gis, squared) +
    gis*wt_lost interaction term."""
    base = le.build_design_row(record, std_params)
    gis_mean, gis_sd = std_params["gis"]
    gis_std = (float(record["gis"]) - gis_mean) / gis_sd
    wt_lost = float(record["wt_lost"])
    return base + [gis_std ** 2, gis_std * wt_lost]


def fit_augmented(X_aug: list[list[float]], y: list[float], lam: float) -> list[float]:
    return le.fit_ridge_logistic(X_aug, y, lam)


def part_b1_residual_grid(pop_by_arm: dict, lambdas: dict) -> list[dict]:
    rows = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        X, y, std_params = le.build_design_matrix(path_records, benign_records)
        beta = le.fit_ridge_logistic(X, y, lambdas[arm])
        n_path_ref, n_benign_ref = len(path_records), len(benign_records)
        for gis in GIS_GRID:
            for sbs3 in SBS3_GRID:
                point = {"wt_lost": FIXED_FOR_GRID["wt_lost"], "gis": gis, "sbs3": sbs3}
                design_row = le.eval_point_design_row(point, FIXED_FOR_GRID["purity"], FIXED_FOR_GRID["subtype"],
                                                        FIXED_FOR_GRID["wgd"], std_params)
                p_hat = le.predict_proba(beta, design_row)
                fitted_lr = le.probability_to_lr(p_hat, n_path_ref, n_benign_ref, verbose=False)
                true_lr = simulate.joint_lr(arm, point)
                residual = math.log(fitted_lr) - math.log(true_lr)
                rows.append({
                    "arm": arm, "gis": gis, "sbs3": sbs3, "fitted_lr": fitted_lr, "true_lr": true_lr,
                    "log_residual": residual,
                })
    return rows


def part_b2_nested_comparison(pop_by_arm: dict, rng: random.Random) -> list[dict]:
    rows = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        folds = le.make_folds(path_records, benign_records, CV_K, rng)
        base_devs, aug_devs = [], []
        for train_path, train_benign, test_path, test_benign in folds:
            X_train, y_train, std_params = le.build_design_matrix(train_path, train_benign)
            X_test_base = [le.build_design_row(r, std_params) for r in test_path + test_benign]
            y_test = [1.0] * len(test_path) + [0.0] * len(test_benign)
            beta_base = le.fit_ridge_logistic(X_train, y_train, 1.0)
            p_base = [le.predict_proba(beta_base, row) for row in X_test_base]
            base_devs.append(le.deviance(y_test, p_base))

            X_train_aug = [build_augmented_design_row(r, std_params) for r in train_path + train_benign]
            X_test_aug = [build_augmented_design_row(r, std_params) for r in test_path + test_benign]
            beta_aug = fit_augmented(X_train_aug, y_train, 1.0)
            p_aug = [le.predict_proba(beta_aug, row) for row in X_test_aug]
            aug_devs.append(le.deviance(y_test, p_aug))
        mean_base = sum(base_devs) / len(base_devs)
        mean_aug = sum(aug_devs) / len(aug_devs)
        rows.append({
            "arm": arm, "base_model_mean_cv_deviance": mean_base, "augmented_model_mean_cv_deviance": mean_aug,
            "relative_improvement": (mean_base - mean_aug) / mean_base,
        })
    return rows


def main() -> None:
    print(BANNER)
    rng = random.Random(LOCAL_SEED)
    pop = le.load_population()
    pop_by_arm = {"CORE_HR": {"Pathogenic": [], "Benign": []}, "DDR_SIGNALING": {"Pathogenic": [], "Benign": []}}
    for r in pop:
        pop_by_arm[r["arm"]][r["true_class"]].append(r)

    print("=== Part A: calibration ===")
    calib_results = part_a_calibration(pop_by_arm, rng)
    calib_path = REPO_ROOT / "SIMULATED_CALIBRATION_RESULTS.tsv"
    with open(calib_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "lambda_1se", "lambda_min", "bin", "n", "mean_predicted", "observed_fraction"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for arm, res in calib_results.items():
            for b in res["bins"]:
                w.writerow({"arm": arm, "lambda_1se": res["lambda_1se"], "lambda_min": res["lambda_min"],
                            "bin": b["bin"], "n": b["n"], "mean_predicted": b["mean_predicted"],
                            "observed_fraction": b["observed_fraction"]})
    print(f"Wrote {calib_path}")
    for arm, res in calib_results.items():
        print(f"  {arm}: lambda.1se={res['lambda_1se']}, lambda.min={res['lambda_min']}, "
              f"Brier={res['brier_score']:.4f}, ECE={res['ece']:.4f}, n_held_out={res['n_held_out']}")

    print("\n=== Part B1: residual grid vs. true analytic joint LR ===")
    lambdas = {arm: res["lambda_1se"] for arm, res in calib_results.items()}
    b1_rows = part_b1_residual_grid(pop_by_arm, lambdas)
    b1_path = REPO_ROOT / "SIMULATED_LOGLINEARITY_RESIDUAL_GRID.tsv"
    with open(b1_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "gis", "sbs3", "fitted_lr", "true_lr", "log_residual"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in b1_rows:
            w.writerow(r)
    print(f"Wrote {b1_path} ({len(b1_rows)} rows)")
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        residuals = [r["log_residual"] for r in b1_rows if r["arm"] == arm]
        mean_r = sum(residuals) / len(residuals)
        sd_r = (sum((x - mean_r) ** 2 for x in residuals) / (len(residuals) - 1)) ** 0.5
        print(f"  {arm}: mean log-residual={mean_r:.4f}, sd={sd_r:.4f}, "
              f"range=[{min(residuals):.4f}, {max(residuals):.4f}]")

    print("\n=== Part B2: nested model comparison (base vs. +gis^2 +gis*wt_lost) ===")
    b2_rows = part_b2_nested_comparison(pop_by_arm, rng)
    b2_path = REPO_ROOT / "SIMULATED_LOGLINEARITY_NESTED_COMPARISON.tsv"
    with open(b2_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "base_model_mean_cv_deviance", "augmented_model_mean_cv_deviance", "relative_improvement"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in b2_rows:
            w.writerow(r)
    print(f"Wrote {b2_path}")
    for r in b2_rows:
        print(f"  {r['arm']}: base_deviance={r['base_model_mean_cv_deviance']:.4f}, "
              f"augmented_deviance={r['augmented_model_mean_cv_deviance']:.4f}, "
              f"relative_improvement={r['relative_improvement']:.4%}")


if __name__ == "__main__":
    main()
