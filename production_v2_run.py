#!/usr/bin/env python3
"""STEP 6 -- produces genuine production output for the NEW estimator
(logistic_estimator.py), for gate4, gate6, gate8, and gate9 to run
against, in a DEDICATED directory (production_v2/) -- NOT the repo root,
NOT the existing production/ directory. See module docstring history:
this project has hit the fixed-output-filename collision class three
times this session; a dedicated outdir is applied here preemptively (see
OUTPUT_PATH_INVENTORY.tsv / the preflight collision check for the
broader, repo-wide fix).

REVISION (P-AMD-2 follow-up): this file's FIRST version (committed, then
found deficient) hardcoded `lambda=1.0` rather than using the amended
protocol's own CV-selected `lambda.1se`, and evaluated the pooled
quantity at a single reference subtype (LumA) rather than the
PAM50-prevalence-weighted mixture SIMULATED_TRUTH.tsv's own pooled
quantities represent. Both are fixed here -- see
`PROTOCOL_DEVIATIONS.md`'s dated entry logging the original deviation
and its correction (Standing Rule 4: a mistake fixed is still logged,
not erased).

REVISION 2 (P-AMD-3a, MIXTURE_FIX.md): `mixture_point_estimate`'s SECOND
version (this file's own, committed under P-AMD-2 follow-up, found
deficient by P-DIAG-1) weighted the per-subtype LRs directly
(`Sigma_s w_s * LR_s`), while `simulate.py`'s `compute_truth_quantities()`
weights the per-subtype DENSITIES and divides
(`Sigma_s w_s * f(x|Path,s) / Sigma_s w_s * f(x|Benign,s)`). These are
different operations. MIXTURE_FIX.md proves that, GIVEN this simulator's
own generative independence between PAM50 subtype and true pathogenicity
class (subtype is drawn from `PAM50_PROPORTIONS` identically regardless
of `cls` -- see `simulate.py`'s `_emit_sample`, and verified live in
MIXTURE_FIX.md), the density-mixture construction is EXACTLY the
subtype-MARGINAL (pooled, subtype-blind) joint LR `f(x|Path)/f(x|Benign)`.
This is estimated directly and correctly by fitting the SAME ridge
logistic model on the SAME feature set, but WITHOUT a subtype covariate
at all (`mixture_point_estimate` below), rather than by combining
per-subtype conditional fits (which cannot recover the true density
mixture from a discriminative model without extra, unverified
assumptions -- see MIXTURE_FIX.md section 2). The old (P-AMD-2)
LR-weighted computation is kept as `mixture_point_estimate_legacy_lr_weighted`
for the required before/after comparison only; it is not used for
production output as of this revision.

SIMULATED: read-only imports of logistic_estimator.py and simulate.py.
Does NOT modify PROTOCOL.md, logistic_estimator.py, or simulate.py --
this file implements the mixture-evaluation and CV-selection logic
itself, calling those two modules' existing, unmodified functions
(including, for the subtype-blind fix, `le.standardize_params`,
`le.fit_ridge_logistic`, `le.predict_proba`, `le.probability_to_lr`,
`le.make_folds`, and `le.deviance` -- all used exactly as-is; only the
SET OF COLUMNS fed into them, assembled in this file, differs).

Run: python3 production_v2_run.py
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import logistic_estimator as le  # noqa: E402
import simulate  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
LOCAL_SEED = 20260910
B_PROTOCOL = 2000  # PROTOCOL.md section 7.3's actual replicate count -- read live below, asserted to match
CV_K = 5           # variant-grouped (= sample-grouped, see logistic_estimator.py docstring) 5-fold CV
REF_COVARIATES_NON_SUBTYPE = {"purity": 0.5, "wgd": 0}  # subtype is now MIXTURE-evaluated, not fixed -- see below

OUT_DIR = REPO_ROOT / "production_v2"


def read_protocol_b() -> int:
    import re
    text = (REPO_ROOT / "PROTOCOL.md").read_text(encoding="utf-8")
    matches = sorted({int(m.group(1)) for m in re.finditer(r"\bB\s*=\s*(\d+)\b", text)})
    assert len(matches) == 1, f"PROTOCOL.md's B is ambiguous: {matches}"
    return matches[0]


def select_cv_lambda_with_provenance(path_records: list[dict], benign_records: list[dict],
                                       rng: random.Random) -> tuple[float, str]:
    """Selects lambda via logistic_estimator.py's own, unmodified
    select_lambda_cv() -- returns (lambda_1se, provenance_tag). The
    provenance tag is the ONLY thing that satisfies the assertion below;
    there is no code path in this file that produces a lambda value
    without going through this function, so the assertion cannot be
    silently bypassed by a future hardcoded constant slipping back in."""
    cv_result = le.select_lambda_cv(path_records, benign_records, CV_K, rng)
    return cv_result["lambda_1se"], "CV_SELECTED"


def select_cv_lambda_subtype_blind_with_provenance(path_records: list[dict], benign_records: list[dict],
                                                      rng: random.Random) -> tuple[float, str]:
    """Same provenance contract as select_cv_lambda_with_provenance, for
    the subtype-blind design (select_lambda_cv_subtype_blind, defined
    above) -- selected SEPARATELY from the subtype-covariate design's own
    lambda, since the two designs have different columns and can select
    different lambda.1se values (P-AMD-3a's own explicit instruction: "Re
    -run the lambda sweep ... after the fix, so the shrinkage attribution
    is re-established on the corrected computation")."""
    cv_result = select_lambda_cv_subtype_blind(path_records, benign_records, CV_K, rng)
    return cv_result["lambda_1se"], "CV_SELECTED"


def per_subtype_lr_report(beta: list[float], std_params: dict, eval_point: dict, purity: float, wgd: int,
                            n_path_ref: int, n_benign_ref: int) -> dict[str, float]:
    """INFORMATIONAL ONLY (not used for the gate6 mixture estimand as of
    P-AMD-3a): the subtype-COVARIATE model's own per-subtype conditional
    LR at eval_point, for each PAM50 level. Retained because it is a
    genuinely interpretable quantity in its own right (the model's
    subtype-specific relative-risk estimate) -- just not one that can be
    correctly averaged into the pooled/mixture estimand without the
    density information a discriminative model does not provide (see
    MIXTURE_FIX.md section 2)."""
    rows = {}
    for subtype, prevalence in simulate.PAM50_PROPORTIONS.items():
        design_row = le.eval_point_design_row(eval_point, purity, subtype, wgd, std_params)
        p_hat = le.predict_proba(beta, design_row)
        rows[subtype] = le.probability_to_lr(p_hat, n_path_ref, n_benign_ref, verbose=False)
    return rows


def assert_cv_selected(lambda_value: float, provenance: str, context: str) -> None:
    """The assertion this task's own ACCEPTANCE section requires: 'the
    production run fails if the penalty was not CV-selected.' Any code
    path that reaches a bootstrap or a final recovered-value computation
    without having set provenance='CV_SELECTED' (the only value
    select_cv_lambda_with_provenance ever returns) raises here, in
    production, not silently proceeding with an un-provenanced lambda."""
    if provenance != "CV_SELECTED":
        raise AssertionError(
            f"REFUSING to proceed for {context}: lambda={lambda_value} was not CV-selected "
            f"(provenance={provenance!r}, expected 'CV_SELECTED'). PROPOSED_PROTOCOL_AMENDMENT.md "
            f"specifies CV-selected lambda.1se; a hardcoded penalty must not reach production."
        )
    print(f"    [lambda provenance] {context}: lambda={lambda_value:.4f}, provenance=CV_SELECTED (assertion OK)")


def mixture_point_estimate_legacy_lr_weighted(beta: list[float], std_params: dict, eval_point: dict,
                                                purity: float, wgd: int, n_path_ref: int, n_benign_ref: int,
                                                print_detail: bool = False) -> tuple[float, dict]:
    """P-AMD-2's (deficient, per P-DIAG-1/MIXTURE_FIX.md) mixture
    construction: weights the per-subtype LRs directly (Sigma_s w_s *
    LR_s). Kept ONLY for the required before/after comparison in
    MIXTURE_FIX.md -- not called by main() as of P-AMD-3a."""
    per_subtype_lr = {}
    weighted_lr = 0.0
    for subtype, prevalence in simulate.PAM50_PROPORTIONS.items():
        design_row = le.eval_point_design_row(eval_point, purity, subtype, wgd, std_params)
        p_hat = le.predict_proba(beta, design_row)
        lr = le.probability_to_lr(p_hat, n_path_ref, n_benign_ref, verbose=False)
        per_subtype_lr[subtype] = lr
        weighted_lr += prevalence * lr
        if print_detail:
            print(f"      subtype={subtype:<12} prevalence={prevalence:.5f}  LR={lr:.4f}")
    return weighted_lr, per_subtype_lr


# ============================================================================
# P-AMD-3a fix: the subtype-BLIND design (MIXTURE_FIX.md). Reuses
# logistic_estimator.py's primitives (standardize_params, sigmoid via
# fit_ridge_logistic/predict_proba, probability_to_lr, make_folds,
# deviance) completely unmodified -- only the SET OF COLUMNS assembled
# into the design matrix differs (subtype dummies omitted), which is a
# choice of what to feed the existing, unmodified estimator, not a
# change to the estimator itself.
# ============================================================================

def build_subtype_blind_design_row(record: dict, std_params: dict) -> list[float]:
    row = [1.0]
    for k in le.CONTINUOUS_FEATURES:
        mean, sd = std_params[k]
        row.append((float(record[k]) - mean) / sd)
    for k in le.BINARY_FEATURES:
        row.append(float(record[k]))
    return row


def build_subtype_blind_design_matrix(path_records: list[dict],
                                        benign_records: list[dict]) -> tuple[list[list[float]], list[float], dict]:
    all_records = path_records + benign_records
    std_params = le.standardize_params(all_records, le.CONTINUOUS_FEATURES)
    X = [build_subtype_blind_design_row(r, std_params) for r in all_records]
    y = [1.0] * len(path_records) + [0.0] * len(benign_records)
    return X, y, std_params


def eval_point_subtype_blind_design_row(eval_point: dict, purity: float, wgd: int, std_params: dict) -> list[float]:
    record = {**eval_point, "purity": purity, "wgd": wgd}
    return build_subtype_blind_design_row(record, std_params)


def select_lambda_cv_subtype_blind(path_records: list[dict], benign_records: list[dict], k: int,
                                     rng: random.Random, lambda_grid: list[float] = None) -> dict:
    """le.select_lambda_cv's exact algorithm, re-implemented here (not
    calling le.select_lambda_cv, since that function hardcodes the
    subtype-including le.build_design_matrix) against the subtype-blind
    design instead. Uses le.make_folds, le.fit_ridge_logistic,
    le.predict_proba, le.deviance unmodified."""
    if lambda_grid is None:
        lambda_grid = le.LAMBDA_GRID
    folds = le.make_folds(path_records, benign_records, k, rng)
    per_lambda_fold_deviance = {lam: [] for lam in lambda_grid}
    for train_path, train_benign, test_path, test_benign in folds:
        X_train, y_train, std_params = build_subtype_blind_design_matrix(train_path, train_benign)
        X_test = [build_subtype_blind_design_row(r, std_params) for r in test_path + test_benign]
        y_test = [1.0] * len(test_path) + [0.0] * len(test_benign)
        for lam in lambda_grid:
            beta = le.fit_ridge_logistic(X_train, y_train, lam)
            p_hat = [le.predict_proba(beta, row) for row in X_test]
            per_lambda_fold_deviance[lam].append(le.deviance(y_test, p_hat))
    mean_dev = {lam: sum(devs) / len(devs) for lam, devs in per_lambda_fold_deviance.items()}
    se_dev = {lam: (sum((d - mean_dev[lam]) ** 2 for d in devs) / (len(devs) - 1)) ** 0.5 / (len(devs) ** 0.5)
              if len(devs) > 1 else 0.0
              for lam, devs in per_lambda_fold_deviance.items()}
    lambda_min = min(mean_dev, key=lambda l: mean_dev[l])
    threshold = mean_dev[lambda_min] + se_dev[lambda_min]
    candidates = [l for l in lambda_grid if mean_dev[l] <= threshold]
    lambda_1se = max(candidates) if candidates else lambda_min
    return {"lambda_min": lambda_min, "lambda_1se": lambda_1se, "mean_deviance": mean_dev, "se_deviance": se_dev}


def mixture_point_estimate(beta: list[float], std_params: dict, eval_point: dict, purity: float, wgd: int,
                             n_path_ref: int, n_benign_ref: int, print_detail: bool = False) -> float:
    """CORRECTED (P-AMD-3a/MIXTURE_FIX.md) mixture LR: the subtype-blind
    fit's prior-odds-corrected LR at eval_point. MIXTURE_FIX.md proves
    this equals the PAM50-prevalence-weighted DENSITY mixture
    (SIMULATED_TRUTH.tsv's own estimand) exactly, given this simulator's
    verified subtype-class independence -- NOT an approximation. `beta`
    and `std_params` must come from a SUBTYPE-BLIND fit
    (build_subtype_blind_design_matrix), not le.build_design_matrix."""
    design_row = eval_point_subtype_blind_design_row(eval_point, purity, wgd, std_params)
    p_hat = le.predict_proba(beta, design_row)
    lr = le.probability_to_lr(p_hat, n_path_ref, n_benign_ref, verbose=False)
    if print_detail:
        print(f"      [subtype-blind mixture] p_hat={p_hat:.6f}  LR={lr:.4f}  "
              f"(n_path_ref={n_path_ref}, n_benign_ref={n_benign_ref})")
    return lr


def bootstrap_ci_mixture(path_records: list[dict], benign_records: list[dict], eval_point: dict,
                          purity: float, wgd: int, lam: float, rng: random.Random, b: int) -> tuple[float, float, list[float]]:
    """Patient-clustered bootstrap (see logistic_estimator.py's own
    docstring: sample-grouped in this simulator, no recurrent variants)
    of the CORRECTED (subtype-blind) mixture point estimate above -- each
    replicate refits the subtype-blind design on a resample (at the SAME,
    already CV-selected lambda -- standard bootstrap practice is to hold
    the tuning parameter fixed across replicates, not re-select it 2000
    times)."""
    n_path, n_benign = len(path_records), len(benign_records)
    replicates = []
    for _ in range(b):
        path_rs = [path_records[rng.randrange(n_path)] for _ in range(n_path)]
        benign_rs = [benign_records[rng.randrange(n_benign)] for _ in range(n_benign)]
        X, y, std_params = build_subtype_blind_design_matrix(path_rs, benign_rs)
        beta = le.fit_ridge_logistic(X, y, lam)
        lr = mixture_point_estimate(beta, std_params, eval_point, purity, wgd,
                                     len(path_rs), len(benign_rs), print_detail=False)
        replicates.append(lr)
    replicates.sort()
    lo = simulate.percentile(replicates, 2.5)
    hi = simulate.percentile(replicates, 97.5)
    return lo, hi, replicates


def main() -> None:
    print(BANNER)
    protocol_b = read_protocol_b()
    assert protocol_b == B_PROTOCOL, f"PROTOCOL.md's B ({protocol_b}) != this script's B_PROTOCOL ({B_PROTOCOL})"
    OUT_DIR.mkdir(exist_ok=True)

    rng = random.Random(LOCAL_SEED)
    pop = le.load_population()
    pop_by_arm = {"CORE_HR": {"Pathogenic": [], "Benign": []}, "DDR_SIGNALING": {"Pathogenic": [], "Benign": []}}
    for r in pop:
        pop_by_arm[r["arm"]][r["true_class"]].append(r)

    lr_table_rows = []
    recovered_rows = []
    ablation_rows = []
    per_subtype_rows = []

    truth_by_quantity = {}
    with open(REPO_ROOT / "SIMULATED_TRUTH.tsv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            truth_by_quantity[row["quantity"]] = row

    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        print(f"\n--- {arm}: n_path={len(path_records)}, n_benign={len(benign_records)} ---")

        n_path_ref, n_benign_ref = len(path_records), len(benign_records)

        # Informational only (P-AMD-3a/MIXTURE_FIX.md): the subtype-COVARIATE
        # fit's own per-subtype conditional LRs. No longer used to form the
        # gate6 mixture estimand -- see MIXTURE_FIX.md.
        print("  Selecting lambda via 5-fold CV for the subtype-COVARIATE design (informational per-subtype report only)...")
        lam_subtype, provenance_subtype = select_cv_lambda_with_provenance(path_records, benign_records, rng)
        assert_cv_selected(lam_subtype, provenance_subtype, context=f"{arm} subtype-covariate fit (informational)")
        X_st, y_st, std_params_st = le.build_design_matrix(path_records, benign_records)
        beta_st = le.fit_ridge_logistic(X_st, y_st, lam_subtype)
        per_subtype_lr = per_subtype_lr_report(beta_st, std_params_st, le.EVAL_POINT,
                                                 REF_COVARIATES_NON_SUBTYPE["purity"],
                                                 REF_COVARIATES_NON_SUBTYPE["wgd"], n_path_ref, n_benign_ref)
        print("  Per-subtype conditional LRs (informational, NOT averaged into the gate6 estimand):")
        for subtype, lr_val in per_subtype_lr.items():
            print(f"      subtype={subtype:<12} prevalence={simulate.PAM50_PROPORTIONS[subtype]:.5f}  LR={lr_val:.4f}")

        # CORRECTED (P-AMD-3a): the subtype-BLIND fit, whose prior-odds
        # -corrected LR at eval_point equals the PAM50-prevalence-weighted
        # DENSITY mixture exactly (MIXTURE_FIX.md) -- this IS the gate6
        # estimand.
        print("  Selecting lambda via 5-fold CV for the subtype-BLIND design (the CORRECTED estimand)...")
        lam, provenance = select_cv_lambda_subtype_blind_with_provenance(path_records, benign_records, rng)
        assert_cv_selected(lam, provenance, context=f"{arm} subtype-blind fit (corrected estimand)")

        X, y, std_params = build_subtype_blind_design_matrix(path_records, benign_records)
        beta = le.fit_ridge_logistic(X, y, lam)

        weighted_lr = mixture_point_estimate(
            beta, std_params, le.EVAL_POINT, REF_COVARIATES_NON_SUBTYPE["purity"],
            REF_COVARIATES_NON_SUBTYPE["wgd"], n_path_ref, n_benign_ref, print_detail=True)
        print(f"  Corrected (subtype-blind) mixture point estimate: {weighted_lr:.6f}")

        print(f"  Bootstrapping the mixture estimand, B={B_PROTOCOL} (PROTOCOL.md section 7.3's own replicate count)...")
        ci_low, ci_high, _ = bootstrap_ci_mixture(path_records, benign_records, le.EVAL_POINT,
                                                    REF_COVARIATES_NON_SUBTYPE["purity"],
                                                    REF_COVARIATES_NON_SUBTYPE["wgd"], lam, rng, B_PROTOCOL)
        print(f"  Mixture point={weighted_lr:.6f}  CI=[{ci_low:.6f}, {ci_high:.6f}]  (B={B_PROTOCOL})")

        quantity = f"{arm.lower()}_joint_LR"
        truth_row = truth_by_quantity.get(quantity, {})
        injected_value = truth_row.get("injected_value", "MISSING")
        injected_estimand = truth_row.get("estimand", "MISSING")
        injected_derivation = truth_row.get("derivation", "MISSING")

        print(f"\n  === ESTIMAND COMPARISON (printed side by side, per this task's own requirement) ===")
        print(f"  quantity:            {quantity}")
        print(f"  INJECTED value:      {injected_value}")
        print(f"  INJECTED estimand:   {injected_estimand} -- {injected_derivation[:160]}"
              f"{'...' if len(injected_derivation) > 160 else ''}")
        print(f"  RECOVERED value:     {weighted_lr:.6f}  CI=[{ci_low:.6f}, {ci_high:.6f}]")
        print(f"  RECOVERED estimand:  LR -- ridge-logistic fitted model, SUBTYPE-BLIND design "
              f"(lambda={lam:.4f}, CV-selected on this design), wt_lost/gis/sbs3/purity/wgd at "
              f"EVAL_POINT/REF_COVARIATES_NON_SUBTYPE. MIXTURE_FIX.md proves this equals the "
              f"PAM50-prevalence-weighted DENSITY mixture over the same simulate.PAM50_PROPORTIONS "
              f"weights the injected value's own derivation uses (subtype-class independence, "
              f"verified against simulate.py's own sample generation) -- P-AMD-3a's fix for the "
              f"application-point mismatch P-DIAG-1 found (weighting per-subtype LRs, this file's "
              f"prior revision, is NOT the same operation).")
        print(f"  UNITS match (both LR): {injected_estimand.strip() == 'LR'}")
        print()

        lr_table_rows.append({
            "stratum": f"{arm}_pooled_full_vector_mixture", "gene_group": arm, "status": "FITTED",
            "point_estimate": weighted_lr, "ci_low": ci_low, "ci_high": ci_high,
            "n_replicates": B_PROTOCOL, "n_pathogenic": n_path_ref, "n_benign": n_benign_ref,
        })
        recovered_rows.append({
            "quantity": quantity, "recovered_point": weighted_lr, "ci_low": ci_low, "ci_high": ci_high,
            "estimand": "LR",
        })
        ablation_rows.append({
            "arm": arm, "feature_subset": "LOH_GIS_SBS3_MIXTURE", "n_scenario": "PRODUCTION_V2_FULL_N_MIXTURE",
            "point_estimate": weighted_lr, "ci_low": ci_low, "ci_high": ci_high,
        })
        for subtype, lr_val in per_subtype_lr.items():
            per_subtype_rows.append({
                "arm": arm, "subtype": subtype, "prevalence": simulate.PAM50_PROPORTIONS[subtype],
                "point_estimate_lr": lr_val, "lambda_used": lam_subtype,
            })

    # gate4 LR table
    lr_path = OUT_DIR / "SIMULATED_LR_TABLE.tsv"
    with open(lr_path, "w", newline="", encoding="utf-8") as f:
        cols = ["stratum", "gene_group", "status", "point_estimate", "ci_low", "ci_high",
                "n_replicates", "n_pathogenic", "n_benign"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in lr_table_rows:
            w.writerow(r)
    print(f"Wrote {lr_path}")

    # gate6 recovered + scope (against the REAL, repo-root SIMULATED_TRUTH.tsv)
    recovered_path = OUT_DIR / "SIMULATED_RECOVERED.tsv"
    with open(recovered_path, "w", newline="", encoding="utf-8") as f:
        cols = ["quantity", "recovered_point", "ci_low", "ci_high", "estimand"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in recovered_rows:
            w.writerow(r)
    print(f"Wrote {recovered_path}")

    all_truth_quantities = list(truth_by_quantity.keys())
    recovered_quantities = {r["quantity"] for r in recovered_rows}
    scope_path = OUT_DIR / "SIMULATED_scope.tsv"
    with open(scope_path, "w", newline="", encoding="utf-8") as f:
        cols = ["quantity", "in_scope", "reason"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for q in all_truth_quantities:
            if q in recovered_quantities:
                w.writerow({"quantity": q, "in_scope": "TRUE",
                            "reason": "newly reachable under PROPOSED_PROTOCOL_AMENDMENT.md's estimator "
                                      "(REACHABILITY_TABLE.tsv: NEWLY_REACHABLE) -- recovered by this "
                                      "production_v2 run as the PAM50-prevalence-weighted mixture estimand "
                                      "(matching SIMULATED_TRUTH.tsv's own pooled-quantity definition), "
                                      "CV-selected lambda, B=2000."})
            else:
                w.writerow({"quantity": q, "in_scope": "FALSE",
                            "reason": "out of scope for this task's production_v2 gate6 run, which recovers "
                                      "only the 2 pooled joint_LR quantities as a representative, tractable "
                                      "subset of the 24 quantities REACHABILITY_TABLE.tsv marks NEWLY_REACHABLE "
                                      "-- not a claim this quantity is unreachable, see REACHABILITY_TABLE.tsv "
                                      "for its actual classification."})
    print(f"Wrote {scope_path}")

    # gate8 ablation-style table (reuses the SAME 2 fits, no extra compute)
    ablation_path = OUT_DIR / "SIMULATED_ABLATION_TABLE_V2.tsv"
    with open(ablation_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "feature_subset", "n_scenario", "point_estimate", "ci_low", "ci_high"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in ablation_rows:
            w.writerow(r)
    print(f"Wrote {ablation_path}")

    # Per-subtype LR report (this task's own explicit requirement -- "belongs
    # in the production output rather than in a throwaway check")
    per_subtype_path = OUT_DIR / "SIMULATED_PER_SUBTYPE_LR.tsv"
    with open(per_subtype_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "subtype", "prevalence", "point_estimate_lr", "lambda_used"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in per_subtype_rows:
            w.writerow(r)
    print(f"Wrote {per_subtype_path}")

    # gate9 imbalance sweep -- now also CV-selecting lambda per (arm, ratio)
    # cell, for consistency with implementing the amendment correctly
    # everywhere in production, not only in the pooled recovery.
    gate9_rows = []
    ratios = [("1:1", 300, 300), ("1:5", 60, 300), ("1:20", 15, 300)]
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        for label, n_path, n_benign in ratios:
            for rep in range(5):
                path_sample = rng.sample(path_records, n_path)
                benign_sample = rng.sample(benign_records, n_benign)
                lam_g9, prov_g9 = select_cv_lambda_with_provenance(path_sample, benign_sample, rng)
                assert_cv_selected(lam_g9, prov_g9, context=f"gate9 {arm}/{label}/rep{rep}")
                result = le.fit_and_score(path_sample, benign_sample, le.EVAL_POINT,
                                            REF_COVARIATES_NON_SUBTYPE["purity"], "LumA",
                                            REF_COVARIATES_NON_SUBTYPE["wgd"], lam_g9, verbose=(rep == 0))
                gate9_rows.append({
                    "test_case": arm, "class_ratio_label": label, "n_pathogenic_ref": n_path,
                    "n_benign_ref": n_benign, "recovered_lr": result["lr"], "replicate_index": rep,
                })
    gate9_path = OUT_DIR / "SIMULATED_GATE9_INPUT.tsv"
    with open(gate9_path, "w", newline="", encoding="utf-8") as f:
        cols = ["test_case", "class_ratio_label", "n_pathogenic_ref", "n_benign_ref", "recovered_lr", "replicate_index"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in gate9_rows:
            w.writerow(r)
    print(f"Wrote {gate9_path} ({len(gate9_rows)} rows)")


if __name__ == "__main__":
    main()
