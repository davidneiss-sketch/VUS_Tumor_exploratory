#!/usr/bin/env python3
"""P-EST-1 STEP 4 -- diagnose (not assume) the mechanism behind GATE8's
two instability findings: (a) density underflow to exactly 0.0 at very
small n, and (b) a non-monotonic UNINFORMATIVE fraction, worst in the
middle of the tested n range rather than at the smallest n.

SIMULATED: read-only re-analysis of the already-committed
`SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv` (finding (b)'s reconciliation
needs no new sampling) plus new, local sampling that calls
`stake_ablation.py`'s own, unmodified `joint_lr_for_subset` /
`bootstrap_ci` / `kde_density_at` / `silverman_bandwidth` functions
directly (read-only import, exactly as `interval_instability_sweep.py`
itself does) to demonstrate finding (a)'s mechanism concretely. Does not
modify or re-run `simulate.py`, `stake_ablation.py`,
`interval_instability_sweep.py`, or `PROTOCOL.md`.

An earlier draft of this file's Part 2 re-implemented the KDE sum with a
single FIXED, population-level bandwidth and found essentially zero
underflow at any n -- which turned out to be the wrong mechanism, not
evidence that underflow doesn't happen: `silverman_bandwidth()` recomputes
its bandwidth from whatever values are actually PASSED IN, and
`interval_instability_sweep.py`'s real trial structure calls it fresh on
EVERY bootstrap resample (a resample WITH REPLACEMENT from an already-
small original subsample), not once on the original sample. A resample
that happens, by chance, to draw few distinct original values has a small
or even ~0 empirical spread, collapsing that resample's OWN bandwidth
toward the floor -- and a Gaussian kernel with a near-zero bandwidth,
evaluated at EVAL_POINT (which sits several tenths away from where the
resampled points actually cluster), underflows outright. This version
calls `stake_ablation.py`'s real functions end to end so the actual
mechanism is exercised, not a simplified stand-in for it -- the earlier,
wrong-mechanism draft is disclosed here rather than silently discarded.

Run: python3 estimator_underflow_bandwidth_diagnosis.py
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import simulate  # noqa: E402 -- read-only import
import stake_ablation as sa  # noqa: E402 -- read-only import (joint_lr_for_subset, bootstrap_ci, kde_density_at, silverman_bandwidth)

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
LOCAL_SEED = 20260909  # same as estimator_joint_vs_product_test.py's, disclosed, not simulate.py's own SEED

N_GRID = [12, 15, 20, 25, 30, 40, 50, 65, 75, 100, 130, 160]  # identical to interval_instability_sweep.py's grid
# Reduced from interval_instability_sweep.py's own R_REPEATS=15 / B=300 (that
# script's actual, already-committed numbers remain the reported ground
# truth in SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv) up to a still-tractable
# size for a second, independent replication of the same phenomenon here,
# using the real estimator functions end-to-end -- disclosed, not silent
# (Standing Rule 4).
N_OUTER_TRIALS = 60
B_BOOTSTRAP = 300  # matches interval_instability_sweep.py's B_SWEEP exactly


def part1_reconcile_failure_buckets() -> list[dict]:
    """Combine gate8's two separately-bucketed failure categories
    (UNINFORMATIVE and ZERO_DENSITY_UNDEFINED) back into one
    'not_usable_fraction' per (arm, dimension, n) cell, already present as
    its own column in the committed sweep -- and test whether that
    COMBINED sequence is monotonic non-increasing in n. If it is (up to
    sampling noise at R=15 repeats), the apparent 'non-monotonicity' in
    the UNINFORMATIVE-only column is an artifact of splitting one
    underlying failure population into two buckets whose boundary itself
    moves with n, not a genuine worse-in-the-middle property of the
    estimator's recoverability."""
    sweep_path = REPO_ROOT / "SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv"
    with open(sweep_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    rows_by_key: dict[tuple, list[dict]] = {}
    for r in rows:
        key = (r["arm"], r["dimension"], r["feature_subset"])
        rows_by_key.setdefault(key, []).append(r)

    out = []
    for key, group in rows_by_key.items():
        group.sort(key=lambda r: int(r["n_per_class"]))
        fractions = [float(r["not_usable_fraction"]) for r in group]
        # "Monotonic up to sampling noise": non-increasing, OR any increase
        # is <= 2/15 (R=15 repeats; a 2-trial swing at p~0.2-0.3 is well
        # inside one binomial standard deviation, sqrt(15*p*(1-p)) ~ 1.5-1.8).
        max_increase = 0.0
        for i in range(1, len(fractions)):
            max_increase = max(max_increase, fractions[i] - fractions[i - 1])
        r_repeats = int(group[0]["r_repeats"])
        noise_tolerance = 2.0 / r_repeats
        monotonic_up_to_noise = max_increase <= noise_tolerance
        for r, frac in zip(group, fractions):
            out.append({
                "arm": key[0], "dimension": key[1], "feature_subset": key[2],
                "n_per_class": r["n_per_class"], "r_repeats": r["r_repeats"],
                "n_uninformative": r["n_uninformative"], "n_zero_density_undefined": r["n_zero_density_undefined"],
                "n_informative": r["n_informative"], "not_usable_fraction": frac,
                "max_increase_in_sequence": round(max_increase, 4),
                "noise_tolerance_2_of_r": round(noise_tolerance, 4),
                "combined_sequence_monotonic_up_to_noise": monotonic_up_to_noise,
            })
    return out


def draw_class_sample(arm: str, cls: str, n: int, rng: random.Random) -> dict:
    """n independent draws from the class-conditional MARGINAL
    distributions (Z integrated out), for wt_lost and sbs3 only -- the two
    fields stake_ablation.bootstrap_ci/pool_features require. Identical
    marginal-draw mechanism to estimator_joint_vs_product_test.py's
    draw_independent_class, restricted to the fields this diagnosis uses."""
    p_wt = simulate.marginal_wt_lost_prob(arm, cls)
    mean, sd = simulate.marginal_gaussian_feature_params(simulate.SBS3_LINK[arm], arm, cls)
    return {
        "wt_lost": [1 if rng.random() < p_wt else 0 for _ in range(n)],
        "sbs3": [min(simulate.SBS3_CLIP_HI, max(simulate.SBS3_CLIP_LO, rng.gauss(mean, sd))) for _ in range(n)],
    }


def part2_bandwidth_mechanism(rng: random.Random) -> list[dict]:
    """For the {sbs3} subset (INTERVAL_INSTABILITY.md's dimension 1,
    isolating the specific feature at issue), in each arm: report (a) the
    fraction of independent trials in which stake_ablation.py's own,
    real, unmodified bootstrap_ci() raises ZeroDivisionError -- the SAME
    event interval_instability_sweep.py counts as ZERO_DENSITY_UNDEFINED,
    reproduced here by calling that exact function, not a re-implementation
    -- and (b) on the ORIGINAL (pre-bootstrap) sample only, what share of
    the KDE density sum at EVAL_POINT the single closest observation
    contributes, using stake_ablation.silverman_bandwidth's own bandwidth
    for that sample. A top-1 share near 1.0 means the estimate is
    effectively determined by whichever one observation happens to land
    closest -- and a BOOTSTRAP RESAMPLE that, by chance of sampling with
    replacement from a small original set, happens not to include that one
    close point (or to include mostly repeats of a single far point,
    collapsing that resample's own re-estimated bandwidth toward the
    floor) is the literal mechanism behind (a)."""
    out = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        mean, sd = simulate.marginal_gaussian_feature_params(simulate.SBS3_LINK[arm], arm, "Benign")
        x0 = simulate.EVAL_POINT["sbs3"]
        for n in N_GRID:
            undefined_trials = 0
            top1_shares = []
            for _ in range(N_OUTER_TRIALS):
                path = draw_class_sample(arm, "Pathogenic", n, rng)
                benign = draw_class_sample(arm, "Benign", n, rng)
                h = sa.silverman_bandwidth(benign["sbs3"])
                kernel_terms = [simulate.phi_pdf(x0, v, h) for v in benign["sbs3"]]
                total = sum(kernel_terms)
                if total > 0.0:
                    top1_shares.append(max(kernel_terms) / total)
                try:
                    sa.joint_lr_for_subset(("sbs3",), path, benign)
                    sa.bootstrap_ci(("sbs3",), path, benign, rng, B_BOOTSTRAP)
                except ZeroDivisionError:
                    undefined_trials += 1
            mean_top1_share = sum(top1_shares) / len(top1_shares) if top1_shares else float("nan")
            out.append({
                "arm": arm, "n_per_class": n,
                "eval_point_sbs3": x0, "benign_marginal_mean": round(mean, 4),
                "zero_density_fraction_of_trials": round(undefined_trials / N_OUTER_TRIALS, 4),
                "mean_top1_kernel_contribution_share_original_sample": (
                    round(mean_top1_share, 4) if mean_top1_share == mean_top1_share else "NaN_all_zero"),
                "n_outer_trials": N_OUTER_TRIALS, "b_bootstrap_per_trial": B_BOOTSTRAP,
            })
    return out


def main() -> None:
    print(BANNER)
    rng = random.Random(LOCAL_SEED)

    reconciliation = part1_reconcile_failure_buckets()
    recon_path = REPO_ROOT / "SIMULATED_FAILURE_MODE_RECONCILIATION.tsv"
    with open(recon_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "dimension", "feature_subset", "n_per_class", "r_repeats", "n_uninformative",
                "n_zero_density_undefined", "n_informative", "not_usable_fraction", "max_increase_in_sequence",
                "noise_tolerance_2_of_r", "combined_sequence_monotonic_up_to_noise"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in reconciliation:
            w.writerow(r)
    print(f"Wrote {recon_path} ({len(reconciliation)} rows)")

    mechanism = part2_bandwidth_mechanism(rng)
    mech_path = REPO_ROOT / "SIMULATED_KDE_BANDWIDTH_MECHANISM.tsv"
    with open(mech_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "n_per_class", "eval_point_sbs3", "benign_marginal_mean",
                "zero_density_fraction_of_trials", "mean_top1_kernel_contribution_share_original_sample",
                "n_outer_trials", "b_bootstrap_per_trial"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in mechanism:
            w.writerow(r)
    print(f"Wrote {mech_path} ({len(mechanism)} rows)")

    print()
    print("Part 1 -- CORE_HR / dimension 1 (SBS3_ONLY) reconciled sequence:")
    for r in reconciliation:
        if r["arm"] == "CORE_HR" and r["dimension"] == "1":
            print(f"  n={r['n_per_class']:>4}  not_usable_fraction={r['not_usable_fraction']}")
    core_hr_dim1_monotonic = next(r["combined_sequence_monotonic_up_to_noise"] for r in reconciliation
                                   if r["arm"] == "CORE_HR" and r["dimension"] == "1")
    print(f"  monotonic non-increasing up to sampling noise: {core_hr_dim1_monotonic}")
    print()
    print("Part 2 -- SBS3 | Benign, real stake_ablation.py functions, CORE_HR:")
    for r in mechanism:
        if r["arm"] == "CORE_HR":
            print(f"  n={r['n_per_class']:>4}  zero_density_frac={r['zero_density_fraction_of_trials']:>6}  "
                  f"mean_top1_share={r['mean_top1_kernel_contribution_share_original_sample']}")
    print()
    print("Part 2 -- SBS3 | Benign, real stake_ablation.py functions, DDR_SIGNALING:")
    for r in mechanism:
        if r["arm"] == "DDR_SIGNALING":
            print(f"  n={r['n_per_class']:>4}  zero_density_frac={r['zero_density_fraction_of_trials']:>6}  "
                  f"mean_top1_share={r['mean_top1_kernel_contribution_share_original_sample']}")


if __name__ == "__main__":
    main()
