#!/usr/bin/env python3
"""STEP 2 of the logistic-regression-implementation task -- re-run
P-EST-1's exact dispositive test (estimator_joint_vs_product_test.py)
against the NEW ridge-logistic estimator (logistic_estimator.py), for a
direct, apples-to-apples before/after comparison. This is the acceptance
criterion that governs whether the rest of this task proceeds
(HALT condition: if the new estimator does not separate the two
datasets, report FAILED and stop -- do not proceed to gate9, the
instability sweep, or anything else).

SIMULATED: read-only imports of simulate.py (data-generating functions,
analytic true-LR functions) and logistic_estimator.py (the new
estimator). Does not modify PROTOCOL.md, simulate.py, stake_ablation.py,
or logistic_estimator.py.

Method -- IDENTICAL data construction to estimator_joint_vs_product_test.py,
so the OLD and NEW estimator's numbers sit in the same table for direct
comparison:

  CORRELATED   -- wt_lost, gis, sbs3 drawn from simulate.py's own
                  shared-latent-Z model (same function,
                  draw_correlated_class, copied here for a
                  self-contained script per this project's own
                  convention -- see estimator_joint_vs_product_test.py's
                  own docstring for the identical construction).
  INDEPENDENT  -- wt_lost, gis, sbs3 drawn independently, each from its
                  own class-conditional MARGINAL distribution.

Covariates (purity, subtype, wgd) are held FIXED at neutral,
representative values for every drawn sample AND at the evaluation point,
in both constructions -- so any difference between the new estimator's
LR(CORRELATED) and LR(INDEPENDENT) can only be attributable to the
wt_lost/gis/sbs3 correlation structure the test is designed to isolate,
not to incidental covariate confounding. (purity=0.5, subtype=LumA
[the model's reference level], wgd=0 -- ARBITRARY, disclosed, chosen as
uninformative "average" values, not tuned to produce any particular
result.)

Run: python3 estimator_joint_vs_product_test_v2.py
"""
from __future__ import annotations

import csv
import random
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import simulate  # noqa: E402
import logistic_estimator as le  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

LOCAL_SEED = 20260910  # ARBITRARY, disclosed, local to this script; distinct from every other script's seed this session

N_PER_CLASS = 300
N_REPLICATES = 30
BOOTSTRAP_B = 300  # reduced from PROTOCOL's B=2000 for this per-replicate sweep's tractability, disclosed (Standing Rule 4)
LAMBDA_FIXED = 1.0  # a fixed, moderate ridge strength for this test -- CV-selected lambda is used in the production/CALIBRATION_DIAGNOSTICS.md runs; fixing it here isolates the joint-vs-product question from lambda-selection noise across only 30 replicates x 2 constructions x 2 arms
ARMS = ("CORE_HR", "DDR_SIGNALING")

FIXED_COVARIATES = {"purity": 0.5, "subtype": "LumA", "wgd": 0}


def draw_correlated_class(arm: str, cls: str, n: int, rng: random.Random) -> list[dict]:
    """Identical construction to estimator_joint_vs_product_test.py's
    function of the same name -- shared-latent-Z generative draw."""
    wt_link = simulate.WT_LOST_LINK[arm]
    gis_link = simulate.GIS_LINK[arm]
    sbs3_link = simulate.SBS3_LINK[arm]
    muZ = simulate.Z_MEAN[arm][cls]
    records = []
    for _ in range(n):
        z = rng.gauss(muZ, simulate.Z_SD)
        wt_lost = 1 if rng.random() < simulate.Phi(wt_link["a"] + wt_link["b"] * z) else 0
        gis = gis_link["c"] + gis_link["d"] * z + rng.gauss(0, gis_link["sigma"])
        raw = sbs3_link["c"] + sbs3_link["d"] * z + rng.gauss(0, sbs3_link["sigma"])
        sbs3 = min(simulate.SBS3_CLIP_HI, max(simulate.SBS3_CLIP_LO, raw))
        records.append({"wt_lost": wt_lost, "gis": gis, "sbs3": sbs3, **FIXED_COVARIATES})
    return records


def draw_independent_class(arm: str, cls: str, n: int, rng: random.Random) -> list[dict]:
    """Identical construction to estimator_joint_vs_product_test.py's
    function of the same name -- independent marginal draws."""
    p_wt = simulate.marginal_wt_lost_prob(arm, cls)
    gis_mean, gis_sd = simulate.marginal_gaussian_feature_params(simulate.GIS_LINK[arm], arm, cls)
    sbs3_mean, sbs3_sd = simulate.marginal_gaussian_feature_params(simulate.SBS3_LINK[arm], arm, cls)
    records = []
    for _ in range(n):
        wt_lost = 1 if rng.random() < p_wt else 0
        gis = rng.gauss(gis_mean, gis_sd)
        sbs3 = min(simulate.SBS3_CLIP_HI, max(simulate.SBS3_CLIP_LO, rng.gauss(sbs3_mean, sbs3_sd)))
        records.append({"wt_lost": wt_lost, "gis": gis, "sbs3": sbs3, **FIXED_COVARIATES})
    return records


def new_estimator_point_estimate(path: list[dict], benign: list[dict], verbose: bool = False) -> float:
    result = le.fit_and_score(path, benign, le.EVAL_POINT, FIXED_COVARIATES["purity"],
                               FIXED_COVARIATES["subtype"], FIXED_COVARIATES["wgd"], LAMBDA_FIXED,
                               verbose=verbose)
    return result["lr"]


def run_arm(arm: str, rng: random.Random) -> dict:
    true_joint_correlated = simulate.joint_lr(arm, le.EVAL_POINT)
    true_joint_independent = simulate.product_of_marginals_lr(arm, le.EVAL_POINT)
    product_of_marginals = simulate.product_of_marginals_lr(arm, le.EVAL_POINT)

    corr_estimates, indep_estimates = [], []
    corr_path = corr_benign = indep_path = indep_benign = None
    for i in range(N_REPLICATES):
        corr_path = draw_correlated_class(arm, "Pathogenic", N_PER_CLASS, rng)
        corr_benign = draw_correlated_class(arm, "Benign", N_PER_CLASS, rng)
        indep_path = draw_independent_class(arm, "Pathogenic", N_PER_CLASS, rng)
        indep_benign = draw_independent_class(arm, "Benign", N_PER_CLASS, rng)
        corr_estimates.append(new_estimator_point_estimate(corr_path, corr_benign, verbose=(i == 0)))
        indep_estimates.append(new_estimator_point_estimate(indep_path, indep_benign, verbose=(i == 0)))

    ci_corr_lo, ci_corr_hi, _ = le.bootstrap_ci_logistic(
        corr_path, corr_benign, le.EVAL_POINT, FIXED_COVARIATES["purity"], FIXED_COVARIATES["subtype"],
        FIXED_COVARIATES["wgd"], LAMBDA_FIXED, rng, BOOTSTRAP_B)
    ci_indep_lo, ci_indep_hi, _ = le.bootstrap_ci_logistic(
        indep_path, indep_benign, le.EVAL_POINT, FIXED_COVARIATES["purity"], FIXED_COVARIATES["subtype"],
        FIXED_COVARIATES["wgd"], LAMBDA_FIXED, rng, BOOTSTRAP_B)

    return {
        "arm": arm,
        "true_joint_lr_correlated": true_joint_correlated,
        "true_joint_lr_independent": true_joint_independent,
        "product_of_marginals_lr_both_datasets": product_of_marginals,
        "new_estimator_mean_correlated": statistics.mean(corr_estimates),
        "new_estimator_sd_correlated": statistics.stdev(corr_estimates),
        "new_estimator_mean_independent": statistics.mean(indep_estimates),
        "new_estimator_sd_independent": statistics.stdev(indep_estimates),
        "new_estimator_ci_correlated": (ci_corr_lo, ci_corr_hi),
        "new_estimator_ci_independent": (ci_indep_lo, ci_indep_hi),
        "n_replicates": N_REPLICATES, "n_per_class": N_PER_CLASS, "bootstrap_b": BOOTSTRAP_B,
        "corr_estimates": corr_estimates, "indep_estimates": indep_estimates,
    }


def main() -> None:
    print(BANNER)
    rng = random.Random(LOCAL_SEED)
    results = [run_arm(arm, rng) for arm in ARMS]

    columns = ["arm", "true_joint_lr_correlated", "true_joint_lr_independent",
               "product_of_marginals_lr_both_datasets",
               "new_estimator_mean_correlated", "new_estimator_sd_correlated",
               "new_estimator_mean_independent", "new_estimator_sd_independent",
               "new_estimator_ci_correlated_lo", "new_estimator_ci_correlated_hi",
               "new_estimator_ci_independent_lo", "new_estimator_ci_independent_hi",
               "separation_pooled_sd_units", "tracks_true_joint",
               "n_replicates", "n_per_class", "bootstrap_b"]
    out_path = REPO_ROOT / "SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_V2.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for r in results:
            mean_diff = r["new_estimator_mean_correlated"] - r["new_estimator_mean_independent"]
            pooled_sd = ((r["new_estimator_sd_correlated"] ** 2 + r["new_estimator_sd_independent"] ** 2) / 2) ** 0.5
            separation = abs(mean_diff) / pooled_sd if pooled_sd > 0 else float("inf")
            # "Tracks the true joint values": the new estimator's mean on
            # CORRELATED data should sit closer (in log-space, since LRs
            # are naturally multiplicative) to the true joint LR than to
            # the true product-of-marginals LR.
            import math as _m
            log_est = _m.log(r["new_estimator_mean_correlated"])
            log_true_joint = _m.log(r["true_joint_lr_correlated"])
            log_true_product = _m.log(r["product_of_marginals_lr_both_datasets"])
            tracks_joint = abs(log_est - log_true_joint) < abs(log_est - log_true_product)
            w.writerow({
                "arm": r["arm"],
                "true_joint_lr_correlated": r["true_joint_lr_correlated"],
                "true_joint_lr_independent": r["true_joint_lr_independent"],
                "product_of_marginals_lr_both_datasets": r["product_of_marginals_lr_both_datasets"],
                "new_estimator_mean_correlated": r["new_estimator_mean_correlated"],
                "new_estimator_sd_correlated": r["new_estimator_sd_correlated"],
                "new_estimator_mean_independent": r["new_estimator_mean_independent"],
                "new_estimator_sd_independent": r["new_estimator_sd_independent"],
                "new_estimator_ci_correlated_lo": r["new_estimator_ci_correlated"][0],
                "new_estimator_ci_correlated_hi": r["new_estimator_ci_correlated"][1],
                "new_estimator_ci_independent_lo": r["new_estimator_ci_independent"][0],
                "new_estimator_ci_independent_hi": r["new_estimator_ci_independent"][1],
                "separation_pooled_sd_units": separation,
                "tracks_true_joint": tracks_joint,
                "n_replicates": r["n_replicates"], "n_per_class": r["n_per_class"], "bootstrap_b": r["bootstrap_b"],
            })
            r["separation_pooled_sd_units"] = separation
            r["tracks_true_joint"] = tracks_joint
    print(f"Wrote {out_path} ({len(results)} rows)")

    raw_path = REPO_ROOT / "SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_V2_REPLICATES.tsv"
    with open(raw_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["arm", "replicate_index", "construction", "new_estimator_point_estimate"])
        for r in results:
            for i, v in enumerate(r["corr_estimates"]):
                w.writerow([r["arm"], i, "CORRELATED", v])
            for i, v in enumerate(r["indep_estimates"]):
                w.writerow([r["arm"], i, "INDEPENDENT", v])
    print(f"Wrote {raw_path}")

    print()
    all_pass = True
    for r in results:
        print(f"--- {r['arm']} ---")
        print(f"  true joint LR (CORRELATED)     = {r['true_joint_lr_correlated']:.6f}")
        print(f"  true joint LR (INDEPENDENT) = product-of-marginals LR = {r['true_joint_lr_independent']:.6f}")
        print(f"  NEW estimator mean, CORRELATED:  {r['new_estimator_mean_correlated']:.6f}  "
              f"(sd={r['new_estimator_sd_correlated']:.6f})")
        print(f"  NEW estimator mean, INDEPENDENT: {r['new_estimator_mean_independent']:.6f}  "
              f"(sd={r['new_estimator_sd_independent']:.6f})")
        print(f"  separation = {r['separation_pooled_sd_units']:.3f} pooled-sd units")
        print(f"  tracks true joint (not product-of-marginals): {r['tracks_true_joint']}")
        if r["separation_pooled_sd_units"] < 1.0 or not r["tracks_true_joint"]:
            all_pass = False
        print()
    print(f"DISPOSITIVE TEST: {'PASS -- new estimator separates the datasets and tracks the joint values' if all_pass else 'FAILED'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
