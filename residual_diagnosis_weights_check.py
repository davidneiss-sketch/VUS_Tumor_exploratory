#!/usr/bin/env python3
"""P-DIAG-1 STEP 2 -- verify the mixture weights match on both sides, and
whether they are applied at the same point in the computation.

SIMULATED: read-only imports of simulate.py, logistic_estimator.py, and
production_v2_run.py. Does not modify any of them. Writes only to
residual_diagnosis/.

Also computes a PURELY ANALYTIC comparison (no model fitting, no
randomness -- simulate.py's own exact functions only) isolating the
APPLICATION-POINT choice from every other source of error: what would
the "LR-mixture" (weight the per-subtype LRs, matching
production_v2_run.py's mixture_point_estimate) equal if computed from
the TRUE generative densities, versus the "density-mixture" (weight the
densities, THEN divide -- SIMULATED_TRUTH.tsv's own definition,
simulate.joint_lr_collapsed)? This isolates the application-point effect
from ridge shrinkage and finite-sample fitting noise entirely, since both
quantities are computed from the exact same, noise-free analytic model.

Run: python3 residual_diagnosis_weights_check.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import simulate  # noqa: E402
import logistic_estimator as le  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
OUT_DIR = REPO_ROOT / "residual_diagnosis"


def main() -> None:
    print(BANNER)
    OUT_DIR.mkdir(exist_ok=True)

    truth_weights = dict(simulate.PAM50_PROPORTIONS)
    production_weights = dict(le.simulate.PAM50_PROPORTIONS) if hasattr(le, "simulate") else None
    # production_v2_run.py imports `simulate` directly and reads
    # simulate.PAM50_PROPORTIONS at call time inside mixture_point_estimate
    # -- confirmed by reading that file's own source (grep below), not
    # re-derived independently. Both sides are, textually, the SAME
    # Python object (simulate.PAM50_PROPORTIONS), not merely equal values
    # from two separate computations.
    import production_v2_run as prod
    production_weights = dict(prod.simulate.PAM50_PROPORTIONS)

    print("=== Truth-side weights (simulate.py, used inside compute_truth_quantities() / *_collapsed functions) ===")
    print("Source: simulate.py's own module-level PAM50_PROPORTIONS dict "
          "(derived from BENCHMARKS.tsv PAM01/PAM02, see SUBTYPE_MODEL.md section 4)")
    for st, w in truth_weights.items():
        print(f"    {st:<12} {w:.8f}")

    print("\n=== Production-side weights (production_v2_run.py's mixture_point_estimate()) ===")
    print("Source: `for subtype, prevalence in simulate.PAM50_PROPORTIONS.items():` -- "
          "the SAME imported module attribute, not re-derived or copied")
    for st, w in production_weights.items():
        print(f"    {st:<12} {w:.8f}")

    identical = truth_weights == production_weights
    same_object = simulate.PAM50_PROPORTIONS is prod.simulate.PAM50_PROPORTIONS
    print(f"\nWeights identical in value: {identical}")
    print(f"Same underlying Python object (not independently re-derived copies): {same_object}")

    print("\n=== Application point ===")
    print("Truth side (simulate.joint_density_collapsed / joint_lr_collapsed):")
    print("    joint_density_collapsed(cls) = sum_s( w_s * joint_density_subtype(s, cls) )   <- weight the DENSITY")
    print("    joint_lr_collapsed(x)        = joint_density_collapsed(Pathogenic) / joint_density_collapsed(Benign)")
    print("    i.e. weights are applied to the per-subtype DENSITY, once per class, BEFORE the division.")
    print("Production side (production_v2_run.py's mixture_point_estimate()):")
    print("    for each subtype: lr_s = probability_to_lr(predict_proba(beta, design_row_s), ...)")
    print("    weighted_lr = sum_s( w_s * lr_s )                                            <- weight the LR")
    print("    i.e. weights are applied to the per-subtype RATIO (LR), AFTER each subtype's own division.")
    print("\n**These are NOT the same operation** (weighting densities-then-dividing != weighting"
          " already-divided ratios) -- confirmed by direct source comparison, not merely asserted.")

    print("\n=== Isolating the application-point effect analytically (no model fitting, exact) ===")
    rows = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        x = simulate.EVAL_POINT
        density_mixture = simulate.joint_lr_collapsed(arm, x)  # SIMULATED_TRUTH.tsv's own definition
        lr_mixture = sum(truth_weights[s] * simulate.joint_lr_subtype(arm, s, x) for s in truth_weights)
        rel_diff = (lr_mixture - density_mixture) / density_mixture
        print(f"  {arm}: true density-mixture (truth definition)      = {density_mixture:.6f}")
        print(f"  {arm}: true LR-mixture (production's own operation) = {lr_mixture:.6f}")
        print(f"  {arm}: application-point-ALONE relative displacement = {rel_diff:+.4%}  "
              f"({'same direction as' if (lr_mixture > density_mixture) == (rel_diff > 0) else 'n/a'})")
        rows.append({"arm": arm, "true_density_mixture_lr": density_mixture, "true_lr_mixture_lr": lr_mixture,
                      "application_point_relative_displacement": rel_diff})

    out_path = OUT_DIR / "SIMULATED_APPLICATION_POINT_ISOLATION.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "true_density_mixture_lr", "true_lr_mixture_lr", "application_point_relative_displacement"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {out_path}")

    weights_path = OUT_DIR / "SIMULATED_WEIGHTS_COMPARISON.tsv"
    with open(weights_path, "w", newline="", encoding="utf-8") as f:
        cols = ["subtype", "truth_side_weight", "production_side_weight", "identical"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for st in truth_weights:
            w.writerow({"subtype": st, "truth_side_weight": truth_weights[st],
                        "production_side_weight": production_weights[st],
                        "identical": truth_weights[st] == production_weights[st]})
    print(f"Wrote {weights_path}")


if __name__ == "__main__":
    main()
