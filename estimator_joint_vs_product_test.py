#!/usr/bin/env python3
"""P-EST-1 STEP 2 -- decisive numeric test of whether PROTOCOL.md section
7.1's estimator, as implemented in `stake_ablation.py`, models the joint
density or merely multiplies per-feature marginal likelihood ratios.

SIMULATED: this file does not modify `simulate.py`, `stake_ablation.py`,
`PROTOCOL.md`, or any pipeline file -- it imports `simulate`'s math
helpers and `stake_ablation`'s estimator functions read-only (exactly as
`stake_ablation.py` itself imports `simulate` read-only), and generates
its own new synthetic datasets local to this test.

Method (exactly the task's STEP 2 instruction):
Construct two synthetic datasets with IDENTICAL class-conditional MARGINAL
feature distributions and DIFFERENT correlation structure:

  CORRELATED   -- drawn from simulate.py's own one-factor shared-latent
                  model (Z drives wt_lost, gis, sbs3 jointly, exactly the
                  mechanism DEFECT 3/P06R built and the subtype fix
                  extended). This is the model the simulator's "true
                  joint LR" (`simulate.joint_lr`) already describes
                  analytically.
  INDEPENDENT  -- wt_lost, gis, sbs3 drawn INDEPENDENTLY of each other,
                  each from its own class-conditional MARGINAL
                  distribution (Z integrated out) -- the exact
                  distributions `simulate.marginal_wt_lost_prob` /
                  `simulate.marginal_gaussian_feature_params` already
                  describe analytically, and that `product_of_marginals_lr`
                  is built from.

By construction, both datasets have the SAME per-feature marginal
distributions (same closed-form mean/sd/probability, since the CORRELATED
draw's per-feature marginals are Z-integrated to exactly those same
closed forms). Only the CROSS-feature dependence differs. Therefore:

  - true joint LR(CORRELATED)  = simulate.joint_lr(arm, EVAL_POINT)
      (the analytic Z-integrated joint density ratio -- exact, no
      simulation needed, since this IS the generative model)
  - true joint LR(INDEPENDENT) = simulate.product_of_marginals_lr(arm, EVAL_POINT)
      (independence forces joint density = product of marginal densities,
      by definition of statistical independence -- exact, not an
      approximation)
  - product-of-marginals LR is IDENTICAL for both datasets by
      construction (same marginals) = simulate.product_of_marginals_lr(arm, EVAL_POINT)

If PROTOCOL.md's estimator (as implemented in stake_ablation.py) models
the TRUE joint density, its empirical point estimate on samples drawn
from CORRELATED should track true joint LR(CORRELATED) -- diverging from
its estimate on INDEPENDENT samples by roughly the same margin the
analytic joint-vs-product ratio predicts.
If it is actually a product of marginals, its empirical point estimate on
CORRELATED and INDEPENDENT samples should be statistically
indistinguishable from each other, and both close to
product_of_marginals_lr(arm, EVAL_POINT) -- NOT to true joint LR(CORRELATED).

Run: python3 estimator_joint_vs_product_test.py
"""
from __future__ import annotations

import csv
import random
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import simulate  # noqa: E402 -- read-only import
import stake_ablation  # noqa: E402 -- read-only import (feature_lr, joint_lr_for_subset, bootstrap_ci, EVAL_POINT)

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

# ARBITRARY, disclosed: a seed local to THIS test file, distinct from
# simulate.py's own SEED and from stake_ablation.py's LOCAL_SEED -- this
# test neither reads nor writes either of those modules' RNG state.
LOCAL_SEED = 20260909

N_PER_CLASS = 300          # per class, per dataset -- large enough for KDE to stabilize (see INTERVAL_INSTABILITY.md)
N_REPLICATES = 30          # independent replicate datasets, to report mean/sd, not a single lucky/unlucky draw
BOOTSTRAP_B = 500          # PROTOCOL.md specifies B=2000; reduced for tractability across 2 arms x 2 constructions x 30 replicates, disclosed per Standing Rule 4 (same disclosed reduction stake_ablation.py itself uses at large n)
SUBSET = ("wt_lost", "gis", "sbs3")
ARMS = ("CORE_HR", "DDR_SIGNALING")


def draw_correlated_class(arm: str, cls: str, n: int, rng: random.Random) -> dict:
    """Draw n samples from simulate.py's own shared-latent-Z generative
    model -- wt_lost, gis, sbs3 all downstream of the SAME per-sample Z,
    exactly the mechanism simulate.joint_lr / simulate.joint_density
    describe analytically. Uses only simulate.py's module-level link
    constants (Z_MEAN, WT_LOST_LINK, GIS_LINK, SBS3_LINK, Z_SD,
    SBS3_CLIP_LO/HI) and math helpers (Phi) -- no call into simulate.py's
    own RNG-consuming generate()/_emit_sample(), no file I/O, no state
    shared with the committed SIMULATED_* population."""
    wt_link = simulate.WT_LOST_LINK[arm]
    gis_link = simulate.GIS_LINK[arm]
    sbs3_link = simulate.SBS3_LINK[arm]
    muZ = simulate.Z_MEAN[arm][cls]
    wt_lost, gis, sbs3 = [], [], []
    for _ in range(n):
        z = rng.gauss(muZ, simulate.Z_SD)
        wt_lost.append(1 if rng.random() < simulate.Phi(wt_link["a"] + wt_link["b"] * z) else 0)
        gis.append(gis_link["c"] + gis_link["d"] * z + rng.gauss(0, gis_link["sigma"]))
        raw = sbs3_link["c"] + sbs3_link["d"] * z + rng.gauss(0, sbs3_link["sigma"])
        sbs3.append(min(simulate.SBS3_CLIP_HI, max(simulate.SBS3_CLIP_LO, raw)))
    return {"wt_lost": wt_lost, "gis": gis, "sbs3": sbs3}


def draw_independent_class(arm: str, cls: str, n: int, rng: random.Random) -> dict:
    """Draw n samples with wt_lost, gis, sbs3 drawn INDEPENDENTLY of each
    other and of any per-sample latent variable -- each straight from its
    own class-conditional MARGINAL distribution (Z integrated out
    analytically, via simulate.py's own closed-form marginal functions).
    These are, by construction, the SAME marginal distributions the
    CORRELATED draw above has once Z is integrated out -- only the joint
    (cross-feature) structure differs; there is no shared per-sample
    value linking the three draws below."""
    p_wt = simulate.marginal_wt_lost_prob(arm, cls)
    gis_mean, gis_sd = simulate.marginal_gaussian_feature_params(simulate.GIS_LINK[arm], arm, cls)
    sbs3_mean, sbs3_sd = simulate.marginal_gaussian_feature_params(simulate.SBS3_LINK[arm], arm, cls)
    wt_lost = [1 if rng.random() < p_wt else 0 for _ in range(n)]
    gis = [rng.gauss(gis_mean, gis_sd) for _ in range(n)]
    sbs3 = [min(simulate.SBS3_CLIP_HI, max(simulate.SBS3_CLIP_LO, rng.gauss(sbs3_mean, sbs3_sd))) for _ in range(n)]
    return {"wt_lost": wt_lost, "gis": gis, "sbs3": sbs3}


def estimator_point_estimate(path: dict, benign: dict) -> float:
    """The actual PROTOCOL.md 7.1 estimator (stake_ablation.py's own,
    unmodified implementation), on the given samples."""
    return stake_ablation.joint_lr_for_subset(SUBSET, path, benign)


def run_arm(arm: str, rng: random.Random) -> dict:
    true_joint_correlated = simulate.joint_lr(arm, stake_ablation.EVAL_POINT)
    true_joint_independent = simulate.product_of_marginals_lr(arm, stake_ablation.EVAL_POINT)
    product_of_marginals = simulate.product_of_marginals_lr(arm, stake_ablation.EVAL_POINT)

    corr_estimates, indep_estimates = [], []
    for _ in range(N_REPLICATES):
        corr_path = draw_correlated_class(arm, "Pathogenic", N_PER_CLASS, rng)
        corr_benign = draw_correlated_class(arm, "Benign", N_PER_CLASS, rng)
        indep_path = draw_independent_class(arm, "Pathogenic", N_PER_CLASS, rng)
        indep_benign = draw_independent_class(arm, "Benign", N_PER_CLASS, rng)
        corr_estimates.append(estimator_point_estimate(corr_path, corr_benign))
        indep_estimates.append(estimator_point_estimate(indep_path, indep_benign))

    # One bootstrap CI per construction, from ONE representative replicate
    # draw (the last one above), using stake_ablation.py's own unmodified
    # bootstrap_ci -- reported for context, not as the primary comparison
    # (the primary comparison is the replicate-mean/sd above, which does
    # not depend on any one draw's luck).
    ci_corr_lo, ci_corr_hi, _ = stake_ablation.bootstrap_ci(SUBSET, corr_path, corr_benign, rng, BOOTSTRAP_B)
    ci_indep_lo, ci_indep_hi, _ = stake_ablation.bootstrap_ci(SUBSET, indep_path, indep_benign, rng, BOOTSTRAP_B)

    return {
        "arm": arm,
        "true_joint_lr_correlated": true_joint_correlated,
        "true_joint_lr_independent": true_joint_independent,
        "product_of_marginals_lr_both_datasets": product_of_marginals,
        "joint_vs_product_ratio_correlated": true_joint_correlated / product_of_marginals,
        "estimator_mean_correlated": statistics.mean(corr_estimates),
        "estimator_sd_correlated": statistics.stdev(corr_estimates),
        "estimator_mean_independent": statistics.mean(indep_estimates),
        "estimator_sd_independent": statistics.stdev(indep_estimates),
        "estimator_ci_correlated": (ci_corr_lo, ci_corr_hi),
        "estimator_ci_independent": (ci_indep_lo, ci_indep_hi),
        "n_replicates": N_REPLICATES,
        "n_per_class": N_PER_CLASS,
        "bootstrap_b": BOOTSTRAP_B,
        "corr_estimates": corr_estimates,
        "indep_estimates": indep_estimates,
    }


def main() -> None:
    print(BANNER)
    rng = random.Random(LOCAL_SEED)
    results = [run_arm(arm, rng) for arm in ARMS]

    columns = ["arm", "true_joint_lr_correlated", "true_joint_lr_independent",
               "product_of_marginals_lr_both_datasets", "joint_vs_product_ratio_correlated",
               "estimator_mean_correlated", "estimator_sd_correlated",
               "estimator_mean_independent", "estimator_sd_independent",
               "estimator_ci_correlated_lo", "estimator_ci_correlated_hi",
               "estimator_ci_independent_lo", "estimator_ci_independent_hi",
               "n_replicates", "n_per_class", "bootstrap_b"]
    out_path = REPO_ROOT / "SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for r in results:
            w.writerow({
                "arm": r["arm"],
                "true_joint_lr_correlated": r["true_joint_lr_correlated"],
                "true_joint_lr_independent": r["true_joint_lr_independent"],
                "product_of_marginals_lr_both_datasets": r["product_of_marginals_lr_both_datasets"],
                "joint_vs_product_ratio_correlated": r["joint_vs_product_ratio_correlated"],
                "estimator_mean_correlated": r["estimator_mean_correlated"],
                "estimator_sd_correlated": r["estimator_sd_correlated"],
                "estimator_mean_independent": r["estimator_mean_independent"],
                "estimator_sd_independent": r["estimator_sd_independent"],
                "estimator_ci_correlated_lo": r["estimator_ci_correlated"][0],
                "estimator_ci_correlated_hi": r["estimator_ci_correlated"][1],
                "estimator_ci_independent_lo": r["estimator_ci_independent"][0],
                "estimator_ci_independent_hi": r["estimator_ci_independent"][1],
                "n_replicates": r["n_replicates"],
                "n_per_class": r["n_per_class"],
                "bootstrap_b": r["bootstrap_b"],
            })
    print(f"Wrote {out_path} ({len(results)} rows)")

    # Per-replicate raw estimates, for anyone who wants to re-derive the
    # mean/sd/CI above rather than trust this script's own arithmetic.
    raw_path = REPO_ROOT / "SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_REPLICATES.tsv"
    with open(raw_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["arm", "replicate_index", "construction", "estimator_point_estimate"])
        for r in results:
            for i, v in enumerate(r["corr_estimates"]):
                w.writerow([r["arm"], i, "CORRELATED", v])
            for i, v in enumerate(r["indep_estimates"]):
                w.writerow([r["arm"], i, "INDEPENDENT", v])
    print(f"Wrote {raw_path}")

    print()
    for r in results:
        print(f"--- {r['arm']} ---")
        print(f"  true joint LR, CORRELATED dataset  (simulate.joint_lr)              = {r['true_joint_lr_correlated']:.6f}")
        print(f"  true joint LR, INDEPENDENT dataset (= product_of_marginals_lr)      = {r['true_joint_lr_independent']:.6f}")
        print(f"  product_of_marginals_lr (identical for both datasets by construction) = {r['product_of_marginals_lr_both_datasets']:.6f}")
        print(f"  joint-vs-product ratio (CORRELATED)                                 = {r['joint_vs_product_ratio_correlated']:.6f}")
        print(f"  estimator on CORRELATED samples:  mean={r['estimator_mean_correlated']:.6f}  sd={r['estimator_sd_correlated']:.6f}  "
              f"(n={r['n_replicates']} replicate draws, {r['n_per_class']}/class)")
        print(f"  estimator on INDEPENDENT samples: mean={r['estimator_mean_independent']:.6f}  sd={r['estimator_sd_independent']:.6f}")
        print(f"  one-draw bootstrap CI, CORRELATED  : [{r['estimator_ci_correlated'][0]:.4f}, {r['estimator_ci_correlated'][1]:.4f}]")
        print(f"  one-draw bootstrap CI, INDEPENDENT : [{r['estimator_ci_independent'][0]:.4f}, {r['estimator_ci_independent'][1]:.4f}]")
        mean_diff = r["estimator_mean_correlated"] - r["estimator_mean_independent"]
        pooled_sd = ((r["estimator_sd_correlated"] ** 2 + r["estimator_sd_independent"] ** 2) / 2) ** 0.5
        print(f"  estimator mean(CORRELATED) - mean(INDEPENDENT) = {mean_diff:.6f}  "
              f"(~{mean_diff / pooled_sd:.2f} pooled-sd units)" if pooled_sd > 0 else "")
        print()


if __name__ == "__main__":
    main()
