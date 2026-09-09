#!/usr/bin/env python3
"""logistic_estimator.py -- implementation of PROPOSED_PROTOCOL_AMENDMENT.md's
replacement for PROTOCOL.md section 7.1: L2-penalized (ridge) logistic
regression on the full feature vector (wt_lost, gis, sbs3), with purity,
PAM50 subtype, and WGD as covariates, converted to a likelihood ratio by
dividing out the reference set's own class-balance-implied prior odds.

SIMULATED: this file is the estimator PROPOSED_PROTOCOL_AMENDMENT.md's
own §7.1 replacement text describes -- it does not modify PROTOCOL.md
(still §7.1's OLD text) or any other file. It is a new estimator
implementation, run per this task's own instruction, not applied to
PROTOCOL.md itself.

No numpy/sklearn/scipy is available in this environment (confirmed this
session) -- every numerical routine below (the linear solver, the IRLS
ridge-logistic fit, the bootstrap, the cross-validation) is pure
Python/stdlib. Benchmarked at n=1800/class, p=10 predictors: ~0.06s per
fit, so B=2000 (PROTOCOL.md section 7.3's actual replicate count) is
tractable for a small number of production strata; wider sweeps
(instability characterization, calibration folds) use a smaller,
disclosed B for tractability across many trials, per this project's own
established convention (Standing Rule 4: disclosed, not silent).

Design decisions not specified word-for-word in PROPOSED_PROTOCOL_AMENDMENT.md,
made here and disclosed (none of them touch the amendment's own specified
arithmetic -- the penalty, its selection, and the prior-odds conversion
are implemented exactly as that document specifies):
  - Continuous features (gis, sbs3, purity) are standardized (z-scored
    using the FITTING reference set's own mean/sd, recomputed fresh for
    every fit -- no leakage across CV folds or bootstrap replicates) before
    entering the ridge penalty, so the penalty does not unevenly shrink
    features on very different raw scales (GIS ~0-100 vs SBS3/purity
    ~0-1). Binary predictors (wt_lost, wgd, subtype indicators) are left
    on their natural {0,1} scale. This is a standard, disclosed
    implementation necessity for ridge regression, not a change to the
    amendment's own specified model form (the model is still linear in
    the named features; standardization is a reparameterization of the
    SAME linear model, not an added nonlinearity).
  - "Variant-grouped" cross-validation/bootstrap: this simulator injects
    no recurrent variants (verified this task: 11088/11088
    (chrom,pos,ref,alt) tuples in SIMULATED_variant_calls.tsv are unique)
    -- every sample_id is its own distinct variant/patient, so
    variant-grouped k-fold and patient-clustered bootstrap both reduce
    mechanically to ordinary sample-grouped resampling in this dataset.
    Disclosed here rather than silently implementing an unused grouping
    layer.
"""
from __future__ import annotations

import csv
import math
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import simulate  # noqa: E402 -- read-only import: phi_pdf, Phi, EVAL_POINT, etc.

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

EVAL_POINT = {"wt_lost": 1, "gis": 42.0, "sbs3": 0.30}  # identical to simulate.py's / stake_ablation.py's

SUBTYPE_LEVELS = ["LumA", "LumB", "HER2E", "Basal", "Normal-like"]  # LumA is the reference level
SUBTYPE_REFERENCE = "LumA"

# Evidentiary features + covariates, per PROPOSED_PROTOCOL_AMENDMENT.md.
CONTINUOUS_FEATURES = ["gis", "sbs3", "purity"]  # standardized
BINARY_FEATURES = ["wt_lost", "wgd"]  # left on {0,1} scale
# 4 subtype indicator terms (LumA is the reference, omitted).
SUBTYPE_INDICATOR_LEVELS = [s for s in SUBTYPE_LEVELS if s != SUBTYPE_REFERENCE]

ALL_TERM_NAMES = ["intercept"] + CONTINUOUS_FEATURES + BINARY_FEATURES + \
                  [f"subtype_{s.replace('-', '_')}" for s in SUBTYPE_INDICATOR_LEVELS]

# Ridge strength grid searched by cross-validation (log-spaced, ARBITRARY,
# disclosed -- PROPOSED_PROTOCOL_AMENDMENT.md specifies lambda.1se
# SELECTION via CV deviance; it does not specify the search grid itself).
LAMBDA_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]


# ============================================================================
# Pure-Python linear algebra (no numpy available)
# ============================================================================

def solve_linear_system(A: list[list[float]], b: list[float]) -> list[float]:
    """Gauss-Jordan elimination with partial pivoting. A is p x p, b is
    length p. Returns x such that A x = b."""
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot_val = aug[col][col]
        if abs(pivot_val) < 1e-12:
            pivot_val = 1e-12 if pivot_val >= 0 else -1e-12
        for j in range(col, n + 1):
            aug[col][j] /= pivot_val
        for r in range(n):
            if r != col:
                factor = aug[r][col]
                if factor != 0.0:
                    for j in range(col, n + 1):
                        aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


# ============================================================================
# Design matrix construction
# ============================================================================

def standardize_params(rows: list[dict], keys: list[str]) -> dict[str, tuple[float, float]]:
    params = {}
    n = len(rows)
    for k in keys:
        vals = [float(r[k]) for r in rows]
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n if n > 1 else 1.0
        sd = math.sqrt(var) if var > 1e-12 else 1.0
        params[k] = (mean, sd)
    return params


def build_design_row(record: dict, std_params: dict[str, tuple[float, float]]) -> list[float]:
    row = [1.0]  # intercept
    for k in CONTINUOUS_FEATURES:
        mean, sd = std_params[k]
        row.append((float(record[k]) - mean) / sd)
    for k in BINARY_FEATURES:
        row.append(float(record[k]))
    subtype = record["subtype"]
    for level in SUBTYPE_INDICATOR_LEVELS:
        row.append(1.0 if subtype == level else 0.0)
    return row


def build_design_matrix(path_records: list[dict], benign_records: list[dict]) -> tuple[list[list[float]], list[float], dict]:
    """Builds X, y for a fit, and returns the standardization params
    (computed FRESH from this fitting set's own continuous features --
    no leakage across CV folds/bootstrap replicates)."""
    all_records = path_records + benign_records
    std_params = standardize_params(all_records, CONTINUOUS_FEATURES)
    X = [build_design_row(r, std_params) for r in all_records]
    y = [1.0] * len(path_records) + [0.0] * len(benign_records)
    return X, y, std_params


def eval_point_design_row(eval_point: dict, purity: float, subtype: str, wgd: bool,
                           std_params: dict) -> list[float]:
    record = {**eval_point, "purity": purity, "subtype": subtype, "wgd": wgd}
    return build_design_row(record, std_params)


# ============================================================================
# Ridge-penalized logistic regression (IRLS / penalized Newton-Raphson)
# ============================================================================

def fit_ridge_logistic(X: list[list[float]], y: list[float], lam: float,
                        max_iter: int = 50, tol: float = 1e-8) -> list[float]:
    """Fits beta (length p, beta[0] = intercept, UNPENALIZED) by penalized
    IRLS: maximize log-likelihood - lam/2 * ||beta[1:]||^2. Standard
    Newton-Raphson update: beta_new = beta_old + (X'WX + Lambda)^-1
    (X'(y-p) - Lambda*beta_old), W = diag(p_i(1-p_i)), Lambda = lam on
    the diagonal for all but the intercept term."""
    n = len(X)
    p = len(X[0])
    beta = [0.0] * p
    for _ in range(max_iter):
        preds = [sigmoid(sum(b * x for b, x in zip(beta, row))) for row in X]
        grad = [0.0] * p
        XtWX = [[0.0] * p for _ in range(p)]
        for i in range(n):
            pi = preds[i]
            w = max(pi * (1.0 - pi), 1e-10)
            resid = y[i] - pi
            xi = X[i]
            for a in range(p):
                if xi[a] != 0.0:
                    grad[a] += xi[a] * resid
                    wxa = w * xi[a]
                    row_a = XtWX[a]
                    for b in range(a, p):
                        row_a[b] += wxa * xi[b]
        for a in range(p):
            for b in range(a + 1, p):
                XtWX[b][a] = XtWX[a][b]
        for a in range(1, p):  # intercept (index 0) is unpenalized
            grad[a] -= lam * beta[a]
            XtWX[a][a] += lam
        delta = solve_linear_system(XtWX, grad)
        beta = [beta[i] + delta[i] for i in range(p)]
        if max(abs(d) for d in delta) < tol:
            break
    return beta


def predict_proba(beta: list[float], design_row: list[float]) -> float:
    return sigmoid(sum(b * x for b, x in zip(beta, design_row)))


# ============================================================================
# Prior-odds conversion (PROPOSED_PROTOCOL_AMENDMENT.md's exact arithmetic)
# ============================================================================

def prior_odds_correction(n_path_ref: int, n_benign_ref: int, verbose: bool = True) -> float:
    """Returns the multiplier n_benign_ref/n_path_ref -- LR(X) =
    posterior_odds(X) * this multiplier. Prints the correction applied
    (this task's STEP 1: "Print the correction applied for every fit, so
    it is visible rather than buried")."""
    prior_odds = n_path_ref / n_benign_ref
    correction = n_benign_ref / n_path_ref
    if verbose:
        print(f"    [prior-odds correction] n_path_ref={n_path_ref}, n_benign_ref={n_benign_ref}, "
              f"reference-set prior odds={prior_odds:.6f}, correction multiplier={correction:.6f}")
    return correction


def probability_to_lr(p_hat: float, n_path_ref: int, n_benign_ref: int, verbose: bool = True) -> float:
    posterior_odds = p_hat / (1.0 - p_hat) if p_hat < 1.0 else float("inf")
    correction = prior_odds_correction(n_path_ref, n_benign_ref, verbose=verbose)
    return posterior_odds * correction


# ============================================================================
# The estimator's own joint-LR entry point (mirrors stake_ablation.py's
# joint_lr_for_subset signature/spirit, but computes a GENUINE joint LR
# via logistic regression, not a per-feature product).
# ============================================================================

def fit_and_score(path_records: list[dict], benign_records: list[dict], eval_point: dict,
                   purity: float, subtype: str, wgd: bool, lam: float, verbose: bool = True) -> dict:
    """Fits the ridge logistic model on path_records+benign_records and
    returns the LR at eval_point (with the given covariate values),
    printing the prior-odds correction applied."""
    X, y, std_params = build_design_matrix(path_records, benign_records)
    beta = fit_ridge_logistic(X, y, lam)
    design_row = eval_point_design_row(eval_point, purity, subtype, wgd, std_params)
    p_hat = predict_proba(beta, design_row)
    lr = probability_to_lr(p_hat, len(path_records), len(benign_records), verbose=verbose)
    return {"lr": lr, "p_hat": p_hat, "beta": beta, "std_params": std_params,
            "n_path_ref": len(path_records), "n_benign_ref": len(benign_records)}


def bootstrap_ci_logistic(path_records: list[dict], benign_records: list[dict], eval_point: dict,
                           purity: float, subtype: str, wgd: bool, lam: float,
                           rng: random.Random, b: int, verbose_first: bool = False) -> tuple[float, float, list[float]]:
    """Patient-clustered bootstrap at the given replicate count B. This
    simulator injects no recurrent variants (see module docstring) --
    'patient-clustered' reduces to ordinary per-class resampling with
    replacement, matching stake_ablation.py's own bootstrap_ci exactly in
    structure, with the ridge-logistic fit substituted for the
    product-of-marginals point estimate."""
    n_path, n_benign = len(path_records), len(benign_records)
    replicates = []
    for i in range(b):
        path_rs = [path_records[rng.randrange(n_path)] for _ in range(n_path)]
        benign_rs = [benign_records[rng.randrange(n_benign)] for _ in range(n_benign)]
        result = fit_and_score(path_rs, benign_rs, eval_point, purity, subtype, wgd, lam,
                                verbose=(verbose_first and i == 0))
        replicates.append(result["lr"])
    replicates.sort()
    lo = simulate.percentile(replicates, 2.5)
    hi = simulate.percentile(replicates, 97.5)
    return lo, hi, replicates


# ============================================================================
# Variant-grouped (= sample-grouped, per module docstring) k-fold CV,
# stratified to preserve class ratio -- for lambda selection and
# calibration diagnostics.
# ============================================================================

def make_folds(path_records: list[dict], benign_records: list[dict], k: int,
                rng: random.Random) -> list[tuple[list[dict], list[dict], list[dict], list[dict]]]:
    """Returns k (train_path, train_benign, test_path, test_benign) tuples,
    stratified so each fold's class ratio matches the full-set ratio."""
    path_shuffled = path_records[:]
    benign_shuffled = benign_records[:]
    rng.shuffle(path_shuffled)
    rng.shuffle(benign_shuffled)
    path_folds = [path_shuffled[i::k] for i in range(k)]
    benign_folds = [benign_shuffled[i::k] for i in range(k)]
    folds = []
    for i in range(k):
        test_path, test_benign = path_folds[i], benign_folds[i]
        train_path = [r for j, f in enumerate(path_folds) if j != i for r in f]
        train_benign = [r for j, f in enumerate(benign_folds) if j != i for r in f]
        folds.append((train_path, train_benign, test_path, test_benign))
    return folds


def deviance(y: list[float], p_hat: list[float]) -> float:
    total = 0.0
    for yi, pi in zip(y, p_hat):
        pi_clamped = min(max(pi, 1e-10), 1 - 1e-10)
        total += -(yi * math.log(pi_clamped) + (1 - yi) * math.log(1 - pi_clamped))
    return 2.0 * total


def select_lambda_cv(path_records: list[dict], benign_records: list[dict], k: int,
                      rng: random.Random, lambda_grid: list[float] = None) -> dict:
    """Selects lambda via k-fold CV mean held-out deviance -- returns
    lambda.min AND lambda.1se (the standard, more conservative choice
    PROPOSED_PROTOCOL_AMENDMENT.md specifies is what's actually used)."""
    if lambda_grid is None:
        lambda_grid = LAMBDA_GRID
    folds = make_folds(path_records, benign_records, k, rng)
    per_lambda_fold_deviance = {lam: [] for lam in lambda_grid}
    for train_path, train_benign, test_path, test_benign in folds:
        X_train, y_train, std_params = build_design_matrix(train_path, train_benign)
        X_test = [build_design_row(r, std_params) for r in test_path + test_benign]
        y_test = [1.0] * len(test_path) + [0.0] * len(test_benign)
        for lam in lambda_grid:
            beta = fit_ridge_logistic(X_train, y_train, lam)
            p_hat = [predict_proba(beta, row) for row in X_test]
            per_lambda_fold_deviance[lam].append(deviance(y_test, p_hat))
    mean_dev = {lam: sum(devs) / len(devs) for lam, devs in per_lambda_fold_deviance.items()}
    se_dev = {lam: (sum((d - mean_dev[lam]) ** 2 for d in devs) / (len(devs) - 1)) ** 0.5 / (len(devs) ** 0.5)
              if len(devs) > 1 else 0.0
              for lam, devs in per_lambda_fold_deviance.items()}
    lambda_min = min(mean_dev, key=lambda l: mean_dev[l])
    threshold = mean_dev[lambda_min] + se_dev[lambda_min]
    # lambda.1se: the LARGEST lambda (most regularization) within one SE
    # of the minimum -- standard glmnet convention.
    candidates = [l for l in lambda_grid if mean_dev[l] <= threshold]
    lambda_1se = max(candidates) if candidates else lambda_min
    return {"lambda_min": lambda_min, "lambda_1se": lambda_1se, "mean_deviance": mean_dev, "se_deviance": se_dev}


def load_population() -> list[dict]:
    """Loads the committed synthetic population with wt_lost, gis, sbs3,
    purity, subtype, and wgd -- the full feature+covariate set
    PROPOSED_PROTOCOL_AMENDMENT.md's replacement model requires. Extends
    stake_ablation.py's own load_population() (which does not load purity
    or wgd) rather than modifying that file."""
    def read_tsv(path):
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter="\t"))
    labels = read_tsv(REPO_ROOT / "SIMULATED_TRUTH_detail" / "SIMULATED_sample_labels.tsv")
    samples = read_tsv(REPO_ROOT / "SIMULATED_data" / "SIMULATED_sample_metadata.tsv")
    exposures = read_tsv(REPO_ROOT / "SIMULATED_data" / "SIMULATED_signature_exposures.tsv")
    sample_by_id = {r["sample_id"]: r for r in samples}
    exposure_by_id = {r["sample_id"]: r for r in exposures}
    pop = []
    for lab in labels:
        sid = lab["sample_id"]
        if lab["gene_group"] not in ("CORE_HR", "DDR_SIGNALING"):
            continue
        s = sample_by_id[sid]
        e = exposure_by_id[sid]
        pop.append({
            "sample_id": sid,
            "arm": lab["gene_group"],
            "true_class": lab["true_class"],
            "subtype": s["pam50_subtype"],
            "wt_lost": 1 if lab["hidden_direction"] == "WT_LOST" else 0,
            "gis": float(s["gis_score"]),
            "sbs3": float(e["sbs3_relative_exposure_true"]),
            "purity": float(s["purity"]),
            "wgd": 1 if s["wgd"] == "True" else 0,
        })
    return pop


def calibration_diagnostics(path_records: list[dict], benign_records: list[dict], lam: float, k: int,
                             rng: random.Random) -> dict:
    """5-fold (variant-grouped = sample-grouped) held-out predicted
    probabilities, pooled, for reliability curve / Brier score / ECE --
    computed on p_hat BEFORE the prior-odds conversion, per
    PROPOSED_PROTOCOL_AMENDMENT.md's own text."""
    folds = make_folds(path_records, benign_records, k, rng)
    all_p_hat, all_y = [], []
    for train_path, train_benign, test_path, test_benign in folds:
        X_train, y_train, std_params = build_design_matrix(train_path, train_benign)
        beta = fit_ridge_logistic(X_train, y_train, lam)
        X_test = [build_design_row(r, std_params) for r in test_path + test_benign]
        y_test = [1.0] * len(test_path) + [0.0] * len(test_benign)
        p_hat = [predict_proba(beta, row) for row in X_test]
        all_p_hat.extend(p_hat)
        all_y.extend(y_test)

    brier = sum((p - y) ** 2 for p, y in zip(all_p_hat, all_y)) / len(all_y)

    n_bins = 10
    bins = [[] for _ in range(n_bins)]
    for p, y in zip(all_p_hat, all_y):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, y))
    bin_rows = []
    ece = 0.0
    for i, b in enumerate(bins):
        if not b:
            bin_rows.append({"bin": f"[{i/n_bins:.1f},{(i+1)/n_bins:.1f})", "n": 0,
                              "mean_predicted": None, "observed_fraction": None})
            continue
        mean_pred = sum(p for p, _ in b) / len(b)
        obs_frac = sum(y for _, y in b) / len(b)
        bin_rows.append({"bin": f"[{i/n_bins:.1f},{(i+1)/n_bins:.1f})", "n": len(b),
                          "mean_predicted": mean_pred, "observed_fraction": obs_frac})
        ece += (len(b) / len(all_y)) * abs(obs_frac - mean_pred)

    return {"brier_score": brier, "ece": ece, "n_held_out": len(all_y), "bins": bin_rows}
