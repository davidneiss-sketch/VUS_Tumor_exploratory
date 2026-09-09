#!/usr/bin/env python3
"""P-DIAG-1 STEP 3 -- quantify the ridge shrinkage bias by refitting at a
range of lambda (including near-zero) on the FULL, fixed population (no
resampling -- this is a deterministic point-estimate-vs-lambda curve, not
a bootstrap), and reporting the recovered mixture LR as a function of
lambda against the injected value.

SIMULATED: read-only imports of logistic_estimator.py and simulate.py.
Does NOT modify PROTOCOL.md, logistic_estimator.py, or simulate.py, and
does NOT change lambda SELECTION anywhere in production_v2_run.py or
logistic_estimator.py -- this is a diagnostic sweep only, written to its
own directory (residual_diagnosis/), never touching any committed
artifact. Per this task's own DO-NOT clause: this quantifies the known
shrinkage property: it does not license switching to an unpenalized fit.

Run: python3 residual_diagnosis_lambda_sweep.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import logistic_estimator as le  # noqa: E402
import simulate  # noqa: E402
import production_v2_run as prod  # noqa: E402 -- read-only import of mixture_point_estimate

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
OUT_DIR = REPO_ROOT / "residual_diagnosis"

# Wide grid including near-zero (an unpenalized fit is lambda->0), well
# below and well above the CV-selected values (30.0 CORE_HR, 100.0
# DDR_SIGNALING) -- ARBITRARY grid choice, disclosed, not a change to
# lambda SELECTION (select_lambda_cv is not called or altered here).
LAMBDA_GRID = [0.001, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 60.0, 100.0, 200.0, 500.0, 1000.0]
CV_SELECTED_LAMBDA = {"CORE_HR": 30.0, "DDR_SIGNALING": 100.0}
REF_COVARIATES = {"purity": 0.5, "wgd": 0}


def main() -> None:
    print(BANNER)
    OUT_DIR.mkdir(exist_ok=True)

    pop = le.load_population()
    pop_by_arm = {"CORE_HR": {"Pathogenic": [], "Benign": []}, "DDR_SIGNALING": {"Pathogenic": [], "Benign": []}}
    for r in pop:
        pop_by_arm[r["arm"]][r["true_class"]].append(r)

    truth_by_quantity = {}
    with open(REPO_ROOT / "SIMULATED_TRUTH.tsv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            truth_by_quantity[row["quantity"]] = row

    rows = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        n_path_ref, n_benign_ref = len(path_records), len(benign_records)
        injected = float(truth_by_quantity[f"{arm.lower()}_joint_LR"]["injected_value"])

        X, y, std_params = le.build_design_matrix(path_records, benign_records)
        print(f"\n--- {arm} (injected={injected:.6f}) ---")
        for lam in LAMBDA_GRID:
            beta = le.fit_ridge_logistic(X, y, lam)
            weighted_lr, per_subtype = prod.mixture_point_estimate(
                beta, std_params, le.EVAL_POINT, REF_COVARIATES["purity"], REF_COVARIATES["wgd"],
                n_path_ref, n_benign_ref, print_detail=False)
            rel_bias = (weighted_lr - injected) / injected
            is_cv_selected = abs(lam - CV_SELECTED_LAMBDA[arm]) < 1e-9
            marker = "  <-- CV-selected lambda.1se" if is_cv_selected else ""
            print(f"  lambda={lam:8.3f}  mixture_LR={weighted_lr:10.4f}  relative_bias={rel_bias:+8.2%}{marker}")
            rows.append({
                "arm": arm, "lambda": lam, "mixture_lr": weighted_lr, "injected_value": injected,
                "relative_bias": rel_bias, "is_cv_selected_lambda": is_cv_selected,
            })

    out_path = OUT_DIR / "SIMULATED_LAMBDA_SWEEP.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "lambda", "mixture_lr", "injected_value", "relative_bias", "is_cv_selected_lambda"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
