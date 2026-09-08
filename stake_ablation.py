#!/usr/bin/env python3
"""stake_ablation.py -- P06R3-STAKE task: how much does the gate6 SBS3 FAIL
actually matter?

Implements PROTOCOL.md's OWN pre-registered estimator (Section 7.1: KDE for
continuous features, Jeffreys-corrected empirical proportion for categorical
features, joint LR = product of per-feature LRs under conditional
independence -- NOT the simulator's true latent-integrated joint density,
since that is not what any real estimator under this protocol computes) on
the ALREADY-GENERATED synthetic population (SIMULATED_data/,
SIMULATED_TRUTH_detail/), for four feature subsets, at synthetic n and at
realistic (BENCHMARKS.tsv-derived) n, stratified by PAM50 subtype.

Does NOT modify simulate.py, signatures.py, loh_caller.py, or PROTOCOL.md --
imports simulate.py's math helpers (phi_pdf, Phi) and existing analytic
functions read-only, for the "true" reference values used only as context.

Run: python3 stake_ablation.py
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

# ARBITRARY, disclosed: a bootstrap/subsample seed local to THIS script, not
# simulate.py's SEED (that file is not modified or re-run by this script).
LOCAL_SEED = 20260908

EVAL_POINT = {"wt_lost": 1, "gis": 42.0, "sbs3": 0.30}  # identical to simulate.py's EVAL_POINT (copied, not imported, so this file has no runtime dependency on simulate.py's module-level state beyond the pure functions used below)

# PROTOCOL.md §11: B=2000, percentile bootstrap. Used in full at realistic-n
# scenarios (cheap: n<150/class). At full synthetic n (~1848/class) B is
# reduced to 500 for tractability in pure-Python/stdlib-only KDE (no numpy
# in this environment) -- disclosed explicitly in every row where it
# applies, per Standing Rule 4 (never substitute silently).
B_FULL_PROTOCOL = 2000
B_REDUCED_LARGE_N = 500
LARGE_N_THRESHOLD = 300  # combined class size above which B is reduced

FEATURE_SUBSETS = [
    ("LOH_GIS_SBS3", ("wt_lost", "gis", "sbs3")),
    ("LOH_GIS", ("wt_lost", "gis")),
    ("LOH_SBS3", ("wt_lost", "sbs3")),
    ("GIS_SBS3", ("gis", "sbs3")),
]

PAM50_SUBTYPES = ["LumA", "LumB", "HER2E", "Basal", "Normal-like"]

# BENCHMARKS.tsv BRCA_PREV01 (Yost et al. 2019) / DDR_PREV01 (Couch et al.
# 2017), extrapolated to a ~1097-patient TCGA-BRCA-scale cohort -- the SAME
# arithmetic and citations SIMULATION_SPEC.md §6 already used and disclosed
# (not re-derived here, reused verbatim). Benign-class realistic n has NO
# published citation in BENCHMARKS.tsv -- set equal to the pathogenic-class
# n as a disclosed, UNCITED simplifying assumption (Standing Rule 3: this is
# NOT a retrieved value, it is an assumption, stated as such everywhere it
# is used).
REALISTIC_N = {
    "CORE_HR": [55, 75],          # SIMULATION_SPEC.md §6, from BRCA_PREV01
    "DDR_SIGNALING": [25, 35],    # SIMULATION_SPEC.md §6, from DDR_PREV01
}
REALISTIC_N_SOURCE = ("Pathogenic-class n from SIMULATION_SPEC.md §6 (BENCHMARKS.tsv BRCA_PREV01/DDR_PREV01, "
                       "extrapolated to a ~1097-patient TCGA-BRCA-scale cohort). Benign-class n is NOT a "
                       "published figure -- set equal to the pathogenic n as a disclosed, uncited assumption.")

ACMG_THRESHOLDS = [  # PROTOCOL.md §9, copied verbatim
    (350, float("inf"), "PATHOGENIC_VERY_STRONG", 8),
    (18.7, 350, "PATHOGENIC_STRONG", 4),
    (4.33, 18.7, "PATHOGENIC_MODERATE", 2),
    (2.08, 4.33, "PATHOGENIC_SUPPORTING", 1),
]


def acmg_tier(ci_low: float, ci_high: float) -> tuple[str, int]:
    """PROTOCOL.md §9, evaluated on the CI LOWER bound for pathogenic-
    direction evidence (this ablation's EVAL_POINT is evidence-positive:
    wt_lost=1, gis=42 (HRD03's positive threshold), sbs3=0.30 (>injected
    Benign means) -- consistently the pathogenicity-supporting side)."""
    for lo, hi, label, pts in ACMG_THRESHOLDS:
        if hi >= ci_low > lo:
            return label, pts
    if ci_low <= 2.08 and ci_high >= 0.48:
        return "NO_EVIDENCE", 0
    if 0.053 <= ci_high < 0.48:
        return "BENIGN_SUPPORTING", 1
    if ci_high < 0.053:
        return "BENIGN_STRONG", 4
    # Shouldn't happen given the table is exhaustive, but never fail silently.
    return "UNCLASSIFIED_GAP_IN_TABLE", -1


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_population() -> list[dict]:
    labels = read_tsv(REPO_ROOT / "SIMULATED_TRUTH_detail" / "SIMULATED_sample_labels.tsv")
    samples = read_tsv(REPO_ROOT / "SIMULATED_data" / "SIMULATED_sample_metadata.tsv")
    exposures = read_tsv(REPO_ROOT / "SIMULATED_data" / "SIMULATED_signature_exposures.tsv")
    sample_by_id = {r["sample_id"]: r for r in samples}
    exposure_by_id = {r["sample_id"]: r for r in exposures}
    pop = []
    for lab in labels:
        sid = lab["sample_id"]
        if lab["gene_group"] not in ("CORE_HR", "DDR_SIGNALING"):
            continue  # NULL_ARM is not part of this ablation (PROTOCOL's actual gene groups only)
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
        })
    return pop


# ============================================================================
# PROTOCOL.md §7.1 estimator: Gaussian KDE (continuous) + Jeffreys-corrected
# empirical proportion (categorical) + product-of-marginals joint LR.
# ============================================================================

def silverman_bandwidth(values: list[float]) -> float:
    """Silverman's rule of thumb -- PROTOCOL.md §7.1 specifies Gaussian KDE
    but does not specify a bandwidth rule; this is a standard, disclosed
    ARBITRARY choice (not itself a protocol-specified parameter)."""
    n = len(values)
    if n < 2:
        return 1.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    sd = math.sqrt(var) if var > 0 else 1e-6
    h = 1.06 * sd * (n ** (-1 / 5))
    return h if h > 1e-6 else 1e-6


def kde_density_at(x0: float, values: list[float]) -> float:
    h = silverman_bandwidth(values)
    n = len(values)
    return sum(simulate.phi_pdf(x0, v, h) for v in values) / n


def jeffreys_p(n_positive: int, n_total: int) -> float:
    """Jeffreys +0.5 continuity correction, PROTOCOL.md §7.1."""
    return (n_positive + 0.5) / (n_total + 1)


def feature_lr(feature: str, path_vals: list, benign_vals: list) -> float:
    if feature == "wt_lost":
        p1 = jeffreys_p(sum(path_vals), len(path_vals))
        p0 = jeffreys_p(sum(benign_vals), len(benign_vals))
        return p1 / p0  # EVAL_POINT["wt_lost"] == 1
    x0 = EVAL_POINT[feature]
    f1 = kde_density_at(x0, path_vals)
    f0 = kde_density_at(x0, benign_vals)
    return f1 / f0


def joint_lr_for_subset(subset: tuple, path: dict, benign: dict) -> float:
    lr = 1.0
    for feat in subset:
        lr *= feature_lr(feat, path[feat], benign[feat])
    return lr


def bootstrap_ci(subset: tuple, path: dict, benign: dict, rng: random.Random, b: int) -> tuple[float, float, list]:
    n_path, n_benign = len(path["wt_lost"]), len(benign["wt_lost"])
    replicates = []
    for _ in range(b):
        path_idx = [rng.randrange(n_path) for _ in range(n_path)]
        benign_idx = [rng.randrange(n_benign) for _ in range(n_benign)]
        path_rs = {feat: [path[feat][i] for i in path_idx] for feat in subset}
        benign_rs = {feat: [benign[feat][i] for i in benign_idx] for feat in subset}
        replicates.append(joint_lr_for_subset(subset, path_rs, benign_rs))
    replicates.sort()
    lo = simulate.percentile(replicates, 2.5)
    hi = simulate.percentile(replicates, 97.5)
    return lo, hi, replicates


def true_reference_lr(arm: str, subset: tuple) -> float:
    """The analytically injected marginal LR, product-restricted to this
    subset, computed from simulate.py's OWN (unmodified) functions -- for
    context only (this ablation's estimator is PROTOCOL's KDE/Jeffreys
    estimator, not this analytic value; reported alongside as a sanity
    reference, not as the ACCEPTANCE-scored quantity)."""
    lr = 1.0
    if "wt_lost" in subset:
        p1 = simulate.marginal_wt_lost_prob(arm, "Pathogenic")
        p0 = simulate.marginal_wt_lost_prob(arm, "Benign")
        lr *= p1 / p0
    if "gis" in subset:
        m1, s1 = simulate.marginal_gaussian_feature_params(simulate.GIS_LINK[arm], arm, "Pathogenic")
        m0, s0 = simulate.marginal_gaussian_feature_params(simulate.GIS_LINK[arm], arm, "Benign")
        lr *= simulate.phi_pdf(EVAL_POINT["gis"], m1, s1) / simulate.phi_pdf(EVAL_POINT["gis"], m0, s0)
    if "sbs3" in subset:
        m1, s1 = simulate.marginal_gaussian_feature_params(simulate.SBS3_LINK[arm], arm, "Pathogenic")
        m0, s0 = simulate.marginal_gaussian_feature_params(simulate.SBS3_LINK[arm], arm, "Benign")
        d1, _ = simulate.sbs3_clipped_density(EVAL_POINT["sbs3"], m1, s1)
        d0, _ = simulate.sbs3_clipped_density(EVAL_POINT["sbs3"], m0, s0)
        lr *= d1 / d0
    return lr


def pool_features(records: list[dict]) -> dict:
    return {
        "wt_lost": [r["wt_lost"] for r in records],
        "gis": [r["gis"] for r in records],
        "sbs3": [r["sbs3"] for r in records],
    }


def run_one(arm: str, subset_name: str, subset: tuple, path_records: list, benign_records: list,
            n_scenario: str, rng: random.Random) -> dict:
    n_path, n_benign = len(path_records), len(benign_records)
    n_total = n_path + n_benign
    if n_total < 20:
        return {
            "arm": arm, "feature_subset": subset_name, "n_scenario": n_scenario,
            "n_pathogenic": n_path, "n_benign": n_benign, "n_total": n_total,
            "point_estimate": "", "ci_low": "", "ci_high": "", "b_replicates": "",
            "true_reference_lr": round(true_reference_lr(arm, subset), 6),
            "acmg_tier": "INSUFFICIENT_N", "acmg_points": "",
        }
    path = pool_features(path_records)
    benign = pool_features(benign_records)
    point = joint_lr_for_subset(subset, path, benign)
    b = B_REDUCED_LARGE_N if n_total > LARGE_N_THRESHOLD else B_FULL_PROTOCOL
    ci_low, ci_high, _ = bootstrap_ci(subset, path, benign, rng, b)
    tier, pts = acmg_tier(ci_low, ci_high)
    return {
        "arm": arm, "feature_subset": subset_name, "n_scenario": n_scenario,
        "n_pathogenic": n_path, "n_benign": n_benign, "n_total": n_total,
        "point_estimate": round(point, 6), "ci_low": round(ci_low, 6), "ci_high": round(ci_high, 6),
        "b_replicates": b,
        "true_reference_lr": round(true_reference_lr(arm, subset), 6),
        "acmg_tier": tier, "acmg_points": pts,
    }


def main() -> None:
    pop = load_population()
    rng = random.Random(LOCAL_SEED)

    rows = []

    # ---- STEP 1: full synthetic n, gene-group level (no subtype split) ----
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = [r for r in pop if r["arm"] == arm and r["true_class"] == "Pathogenic"]
        benign_records = [r for r in pop if r["arm"] == arm and r["true_class"] == "Benign"]
        for subset_name, subset in FEATURE_SUBSETS:
            rows.append(run_one(arm, subset_name, subset, path_records, benign_records,
                                 "SYNTHETIC_FULL_N", rng))

    # ---- STEP 2: realistic n, gene-group level (no subtype split) ----
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        all_path = [r for r in pop if r["arm"] == arm and r["true_class"] == "Pathogenic"]
        all_benign = [r for r in pop if r["arm"] == arm and r["true_class"] == "Benign"]
        for n_target in REALISTIC_N[arm]:
            n_path = min(n_target, len(all_path))
            n_benign = min(n_target, len(all_benign))  # disclosed assumption: benign n = pathogenic n target
            path_sub = rng.sample(all_path, n_path)
            benign_sub = rng.sample(all_benign, n_benign)
            for subset_name, subset in FEATURE_SUBSETS:
                rows.append(run_one(arm, subset_name, subset, path_sub, benign_sub,
                                     f"REALISTIC_N_{n_target}", rng))

    # ---- STEP 3: subtype-stratified, at SYNTHETIC n (realistic n is
    # covered analytically in STAKE_ANALYSIS.md -- computing every
    # subtype x realistic-n cell numerically is redundant once §2's own
    # per-arm realistic n already clears/fails the n>=20 combined-class
    # floor, since splitting that same small n further across 5 subtypes
    # can only shrink each cell). ----
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        for subtype in PAM50_SUBTYPES:
            path_records = [r for r in pop if r["arm"] == arm and r["true_class"] == "Pathogenic" and r["subtype"] == subtype]
            benign_records = [r for r in pop if r["arm"] == arm and r["true_class"] == "Benign" and r["subtype"] == subtype]
            for subset_name, subset in FEATURE_SUBSETS:
                rows.append(run_one(arm, subset_name, subset, path_records, benign_records,
                                     f"SYNTHETIC_SUBTYPE_{subtype}", rng))

    columns = ["arm", "feature_subset", "n_scenario", "n_pathogenic", "n_benign", "n_total",
               "point_estimate", "ci_low", "ci_high", "b_replicates", "true_reference_lr",
               "acmg_tier", "acmg_points"]
    out_path = REPO_ROOT / "ABLATION_TABLE.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
