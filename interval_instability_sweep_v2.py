#!/usr/bin/env python3
"""STEP 5 -- re-run INTERVAL_INSTABILITY.md's sweep (interval_instability_sweep.py)
against the NEW ridge-logistic estimator (logistic_estimator.py), to
characterize the class size below which intervals become gate8-
UNINFORMATIVE, by feature-vector dimension -- mirroring the old sweep's
structure exactly for direct before/after comparability.

SIMULATED: read-only imports of logistic_estimator.py and
gates/gate8_interval_informativeness.py. Does not modify PROTOCOL.md,
simulate.py, stake_ablation.py, logistic_estimator.py, or
interval_instability_sweep.py (the OLD sweep script, left untouched and
still the record of the OLD estimator's behavior).

Method: for each of 2 arms x 3 feature-vector dimensions x the SAME
12 class sizes (n=12 to n=160 per class) INTERVAL_INSTABILITY.md used,
R_REPEATS independent random subsamples are drawn from the existing
synthetic population (without replacement, same methodology as the old
sweep), the NEW estimator is fit and bootstrapped (B_SWEEP replicates),
and each trial's resulting interval is passed through gate8's own,
already-committed informativeness check. Covariates (purity, subtype,
WGD) are read from each drawn sample's own recorded values (NOT held
fixed, unlike the STEP 2 dispositive test) -- this sweep characterizes
REALISTIC production behavior, where covariates vary sample to sample,
not the isolated joint-vs-product question STEP 2 was built to answer.

R_REPEATS and B_SWEEP are REDUCED from the old sweep's own (15, 300) for
tractability across 2 arms x 3 dimensions x 12 n-values in pure-Python
logistic regression -- disclosed explicitly, not silent (Standing Rule
4). The old sweep's own reduction from PROTOCOL's B=2000 to B=300 for
the same tractability reason is the established precedent this follows.
"""
from __future__ import annotations

import csv
import random
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "gates"))
import logistic_estimator as le  # noqa: E402
import gate8_interval_informativeness as g8  # noqa: E402

LOCAL_SEED = 20260910  # ARBITRARY, disclosed, local to this script

N_VALUES = [12, 15, 20, 25, 30, 40, 50, 65, 75, 100, 130, 160]  # identical to the old sweep's grid
R_REPEATS = 8   # reduced from the old sweep's 15, disclosed (Standing Rule 4)
B_SWEEP = 100   # reduced from the old sweep's 300 (itself reduced from PROTOCOL's B=2000), disclosed
LAMBDA_FIXED = 1.0  # fixed moderate ridge strength, same rationale as estimator_joint_vs_product_test_v2.py -- isolates the class-size question from lambda-selection noise across a very large trial count

DIMENSIONS = [
    (1, "SBS3_ONLY", ("sbs3",)),
    (2, "LOH_SBS3", ("wt_lost", "sbs3")),
    (3, "LOH_GIS_SBS3", ("wt_lost", "gis", "sbs3")),
]

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"


def load_population_by_arm() -> dict[str, list[dict]]:
    pop = le.load_population()
    out = {"CORE_HR": {"Pathogenic": [], "Benign": []}, "DDR_SIGNALING": {"Pathogenic": [], "Benign": []}}
    for r in pop:
        out[r["arm"]][r["true_class"]].append(r)
    return out


def project_to_subset(records: list[dict], subset: tuple) -> list[dict]:
    """The NEW estimator's model is always full-covariate (purity,
    subtype, wgd always included, per PROPOSED_PROTOCOL_AMENDMENT.md) --
    'dimension' here means which EVIDENTIARY features are included, with
    the excluded ones held at a FIXED neutral value (0 for wt_lost,
    population-typical values for gis/sbs3) so the design matrix always
    has a column for them but that column carries no information (constant
    within a fit), mirroring the old sweep's per-feature ablation intent
    without requiring a variable-width design matrix."""
    neutral = {"wt_lost": 0, "gis": 30.0, "sbs3": 0.15}
    out = []
    for r in records:
        rr = dict(r)
        for feat in ("wt_lost", "gis", "sbs3"):
            if feat not in subset:
                rr[feat] = neutral[feat]
        out.append(rr)
    return out


def run_one_trial(arm: str, subset: tuple, n: int, all_path: list[dict], all_benign: list[dict],
                   rng: random.Random) -> tuple[str, dict]:
    n_path = min(n, len(all_path))
    n_benign = min(n, len(all_benign))
    path_sub = project_to_subset(rng.sample(all_path, n_path), subset)
    benign_sub = project_to_subset(rng.sample(all_benign, n_benign), subset)
    if n_path + n_benign < 20:
        return "INSUFFICIENT_N", {}

    # Evaluate at each drawn sample's own EVAL_POINT for the in-subset
    # features, but covariates (purity, subtype, wgd) at the FIRST
    # pathogenic sample's own recorded values -- a fixed, disclosed
    # evaluation point per trial (not searched for after seeing results),
    # consistent with EVAL_POINT itself being fixed in advance.
    ref_covariates = path_sub[0]
    eval_point = {k: le.EVAL_POINT[k] if k in subset else path_sub[0][k] for k in ("wt_lost", "gis", "sbs3")}

    try:
        point = le.fit_and_score(path_sub, benign_sub, eval_point, ref_covariates["purity"],
                                  ref_covariates["subtype"], ref_covariates["wgd"], LAMBDA_FIXED,
                                  verbose=False)["lr"]
        ci_low, ci_high, _ = le.bootstrap_ci_logistic(path_sub, benign_sub, eval_point,
                                                        ref_covariates["purity"], ref_covariates["subtype"],
                                                        ref_covariates["wgd"], LAMBDA_FIXED, rng, B_SWEEP)
    except (ZeroDivisionError, ValueError, OverflowError) as e:
        return "ESTIMATOR_ERROR", {"error": str(e)}

    evaluated = g8.evaluate_row(f"{arm}/{n}", point, ci_low, ci_high)
    return evaluated["gate8_status"], {"point": point, "ci_low": ci_low, "ci_high": ci_high}


def main() -> None:
    print(BANNER)
    t_start = time.time()
    pop = load_population_by_arm()
    rng = random.Random(LOCAL_SEED)

    rows = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        all_path = pop[arm]["Pathogenic"]
        all_benign = pop[arm]["Benign"]
        for dim, label, subset in DIMENSIONS:
            for n in N_VALUES:
                statuses = []
                for _ in range(R_REPEATS):
                    status, _ = run_one_trial(arm, subset, n, all_path, all_benign, rng)
                    statuses.append(status)
                n_uninformative = sum(1 for s in statuses if s == "UNINFORMATIVE")
                n_estimator_error = sum(1 for s in statuses if s == "ESTIMATOR_ERROR")
                n_informative = sum(1 for s in statuses if s == "INFORMATIVE")
                n_insufficient = sum(1 for s in statuses if s == "INSUFFICIENT_N")
                not_usable_fraction = (n_uninformative + n_estimator_error) / R_REPEATS
                rows.append({
                    "arm": arm, "dimension": dim, "feature_subset": label, "n_per_class": n,
                    "r_repeats": R_REPEATS, "n_uninformative": n_uninformative,
                    "n_estimator_error": n_estimator_error, "n_informative": n_informative,
                    "n_insufficient": n_insufficient, "not_usable_fraction": round(not_usable_fraction, 4),
                })
                print(f"{arm}\t{label}\tn={n}\tUNINFORMATIVE={n_uninformative}/{R_REPEATS}\t"
                      f"ESTIMATOR_ERROR={n_estimator_error}/{R_REPEATS}\t"
                      f"elapsed={time.time()-t_start:.1f}s")

    out_path = REPO_ROOT / "SIMULATED_INTERVAL_INSTABILITY_SWEEP_V2.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "dimension", "feature_subset", "n_per_class", "r_repeats", "n_uninformative",
                "n_estimator_error", "n_informative", "n_insufficient", "not_usable_fraction"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(rows)} rows) in {time.time()-t_start:.1f}s total")


if __name__ == "__main__":
    main()
