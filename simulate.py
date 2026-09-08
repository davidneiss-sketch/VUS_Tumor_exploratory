#!/usr/bin/env python3
"""simulate.py (v2) — SIMULATED regime simulator with fully-known ground
truth. This is a structural revision of the original simulator, fixing
four defects found in a review of that version (see SIMULATION_SPEC.md
§0 for the full defect list and the fix applied for each):

  DEFECT 1 — bare, deletion-type WT_LOSS (n_t=1, wild-type allele
    deleted, variant retained) and deletion-type VARIANT_LOSS (n_t=1,
    variant deleted, wild-type retained) are now genuinely generated,
    across a purity x depth grid, not just copy-neutral LOH.
  DEFECT 2 — LOH_AMBIGUOUS no longer uses a VAF-midpoint construction
    (which was analytically IDENTICAL to the RETENTION hypothesis'
    target, an unresolvable degeneracy of the single-variant binomial
    model). It now uses a real hidden-direction target VAF at low
    (but evaluable) depth, and this script emits per-segment B-allele
    frequencies from flanking heterozygous SNPs, which independently
    confirm LOH state (m=0 vs m>=1) regardless of the single at-risk
    variant's own read noise.
  DEFECT 3 — LOH-direction, GIS/HRD score, and SBS3 exposure are now
    generated from a single shared latent HR-deficiency variable Z per
    sample (a one-factor model), so they are genuinely correlated given
    class. The injected joint LR is computed from the true joint
    density (1D numerical integration over Z), and recorded alongside
    the naive product-of-marginals LR and their ratio.
  DEFECT 4 — a full-feature-vector null arm (NULL_ARM, a DDR-signaling-
    analogue: same gene list and link structure as DDR_SIGNALING, but
    with the class-conditional Z distribution made IDENTICAL between
    Pathogenic and Benign) is added, whose true joint LR is exactly 1.0
    for every possible evidence vector, not just at one evaluation
    point. The old engineered-null depth-bucket quantity is kept as a
    secondary null.

Also per this revision's task: n is raised substantially (see
SIMULATION_SPEC.md §6 for the justification against real Track B class
sizes), and the old filename-only "no v1 reuse" check is replaced with a
NUMERIC scan of every emitted value against the retracted v1 figures.

Run: python3 simulate.py
"""
from __future__ import annotations

import csv
import itertools
import math
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "SIMULATED_data"
TRUTH_DETAIL_DIR = REPO_ROOT / "SIMULATED_TRUTH_detail"
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"
V1_SCAN_TSV = REPO_ROOT / "V1_NUMERIC_SCAN.tsv"

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

SEED = 20260907  # fixed for full reproducibility; ARBITRARY (today's date as YYYYMMDD)

GENE_GROUPS = {
    # PROTOCOL.md §1 gene lists, copied verbatim.
    "CORE_HR": ["BRCA1", "BRCA2", "PALB2", "RAD51C", "RAD51D", "RAD51B", "BRIP1", "BARD1", "RAD54L"],
    "DDR_SIGNALING": ["ATM", "CHEK1", "CHEK2", "ATR", "MRE11", "RAD50", "NBN", "FANCM"],
    # NULL_ARM is a "DDR-signaling-analogue": the SAME gene list and link
    # structure as DDR_SIGNALING (see *_LINK dicts below), differing only
    # in that its class-conditional Z distribution is made identical
    # between Pathogenic and Benign (Z_MEAN), which is what forces its
    # true joint LR to be exactly 1.0 -- see DEFECT 4.
    "NULL_ARM": ["ATM", "CHEK1", "CHEK2", "ATR", "MRE11", "RAD50", "NBN", "FANCM"],
}
# SUBTYPE_MODEL.md §4: BENCHMARKS.tsv PAM01 (225/126/57/93 of 501, TCGA
# Nature 2012) has no Normal-like figure (PAM01's own notes: "Excludes a
# small Normal-like group not captured in this search"). A second,
# separately WebSearch-sourced citation from the SAME paper ("only eight
# normal-like and eight claudin-low tumours" of 525 profiled) supplies
# Normal-like ~ 8/525 -- a different denominator than PAM01's 501-tumor
# subset, combined here explicitly (not a single clean source; see
# SUBTYPE_MODEL.md §4 for the full citation and the egress-block caveat).
# The other 4 proportions are renormalized to preserve their original
# 225:126:57:93 ratio while leaving room for Normal-like.
_NORMAL_LIKE_PROPORTION = 8 / 525
_PAM01_RAW = {"LumA": 225, "LumB": 126, "HER2E": 57, "Basal": 93}  # of 501, BENCHMARKS.tsv PAM01
_PAM01_TOTAL = sum(_PAM01_RAW.values())
PAM50_PROPORTIONS = {
    **{k: (v / _PAM01_TOTAL) * (1 - _NORMAL_LIKE_PROPORTION) for k, v in _PAM01_RAW.items()},
    "Normal-like": _NORMAL_LIKE_PROPORTION,
}

# SUBTYPE_MODEL.md §1/§2: the confounder PROTOCOL.md's subtype
# stratification exists to handle -- basal-like tumors carry elevated
# baseline genomic instability irrespective of germline HR-deficiency
# status. Applied identically to BOTH classes within a subtype (never
# class-dependent), so it shifts each subtype's BASELINE without touching
# the Pathogenic-vs-Benign SEPARATION Z_MEAN already encodes -- a genuine
# confound, not a second hidden class signal. Only Basal is nonzero;
# every other subtype (including the newly-added Normal-like) is 0.0.
# Magnitudes are ARBITRARY (qualitative existence of the effect is cited
# in SUBTYPE_MODEL.md §2; the size is a disclosed simulator design choice,
# same status as GIS_LINK's own c/d/sigma).
SUBTYPE_Z_SHIFT = {"LumA": 0.0, "LumB": 0.0, "HER2E": 0.0, "Basal": 0.4, "Normal-like": 0.0}
SUBTYPE_GIS_SHIFT = {"LumA": 0.0, "LumB": 0.0, "HER2E": 0.0, "Basal": 10.0, "Normal-like": 0.0}
# SBS3 and WT_LOST direction get NO separate direct subtype term --
# SUBTYPE_MODEL.md §3: no citable literature basis found in this
# session's (egress-restricted) search for an independent-of-Z subtype
# effect on either. Both still inherit a small effect via SUBTYPE_Z_SHIFT
# (since both are downstream of Z).
WGD_PREVALENCE = 0.30          # BENCHMARKS.tsv WGD01
MEAN_MUTATIONS_PER_EXOME = 60.05  # BENCHMARKS.tsv TMB01 (30626/510)
MIN_EVALUABLE_DEPTH = 20        # PROTOCOL.md §5.2, copied verbatim (not a free parameter)
NORMAL_DEPTH_MEAN = 40.0        # ARBITRARY, unchanged from v1
PLOIDY_RANGE = (1.5, 5.5)       # ARBITRARY (matches ASCAT's own default search bounds), unchanged from v1

# --- Purity x depth coverage grid (DEFECT 1) ---
# Bin edges are pre-declared, fixed before generation, not chosen post-hoc.
PURITY_BINS = [("LOW", 0.10, 0.35), ("MID", 0.35, 0.65), ("HIGH", 0.65, 0.95)]
DEPTH_BINS = [("LOW", 25, 45), ("MID", 45, 75), ("HIGH", 75, 120)]  # evaluable-depth grid only (>= floor)
GRID_CATEGORIES = ["RETENTION", "CN_NEUTRAL_LOH_WT_LOSS", "WT_LOSS", "VARIANT_LOSS"]
MIN_PER_CELL_GRID = 5    # minimum instances required per (category, purity_bin, depth_bin, arm, class) cell
DRAWS_PER_GRID_CELL = 200  # raw draws per (purity_bin, depth_bin, arm, class) cell; see SIMULATION_SPEC.md §6

# AMBIGUOUS and NOT_EVALUABLE are defined by construction outside the
# evaluable-depth grid (AMBIGUOUS: near-floor depth; NOT_EVALUABLE:
# below-floor depth) -- every grid cell for these two categories is
# therefore explicitly declared OUT_OF_SCOPE (see coverage report), and
# they get their own, separate, purity-only allocation instead.
AMBIGUOUS_DEPTH_RANGE = (20, 35)      # near the evaluable floor, deliberately low-power
NOT_EVALUABLE_DEPTH_RANGE = (4, 19)   # below the evaluable floor, by construction
MIN_PER_CELL_SIDE_ARM = 8             # instances per (purity_bin, arm, class) for AMBIGUOUS / NOT_EVALUABLE

# --- One-factor shared-latent model (DEFECT 3 / DEFECT 4) ---
# Z ~ Normal(Z_MEAN[arm][class], 1) per sample, shared across all 3
# features below. NULL_ARM's Z_MEAN is IDENTICAL between classes --
# the entire mechanism of DEFECT 4's exact null.
Z_SD = 1.0
Z_MEAN = {
    "CORE_HR": {"Pathogenic": 1.5, "Benign": -1.0},
    "DDR_SIGNALING": {"Pathogenic": 0.8, "Benign": -0.5},
    "NULL_ARM": {"Pathogenic": 0.0, "Benign": 0.0},  # identical -> exact null, see DEFECT 4
}
# P(WT_LOST_DIRECTION | Z) = Phi(a + b*Z) -- probit link.
WT_LOST_LINK = {
    "CORE_HR": {"a": -0.3, "b": 1.0},
    "DDR_SIGNALING": {"a": -0.5, "b": 0.7},
    "NULL_ARM": {"a": -0.5, "b": 0.7},  # same link as DDR_SIGNALING ("analogue")
}
# GIS = c + d*Z + Normal(0, sigma)
GIS_LINK = {
    "CORE_HR": {"c": 30.0, "d": 12.0, "sigma": 8.0},
    "DDR_SIGNALING": {"c": 25.0, "d": 8.0, "sigma": 10.0},
    "NULL_ARM": {"c": 25.0, "d": 8.0, "sigma": 10.0},
}
# SBS3 = c + d*Z + Normal(0, sigma), clipped to [SBS3_CLIP_LO, SBS3_CLIP_HI].
# Named here (not left as inline magic numbers) so the analytic clipped-
# density function below (sbs3_clipped_density) and the generative draw in
# _emit_sample() cannot drift apart -- see P06R3 FIDELITY_AUDIT.md.
SBS3_CLIP_LO = 0.0
SBS3_CLIP_HI = 0.95
SBS3_LINK = {
    "CORE_HR": {"c": 0.15, "d": 0.12, "sigma": 0.08},
    "DDR_SIGNALING": {"c": 0.12, "d": 0.08, "sigma": 0.08},
    "NULL_ARM": {"c": 0.12, "d": 0.08, "sigma": 0.08},
}
# Given NOT WT-lost-direction: split between RETENTION and VARIANT_LOSS.
# Given WT-lost OR variant-lost direction: split between COPY_NEUTRAL and
# DELETION mechanism. Both ARBITRARY, disclosed; DELETION is weighted
# higher than 50% because large-scale copy-number loss is the more
# commonly reported real-world second-hit mechanism (also gives the
# deletion-type categories DEFECT 1 requires more representation).
NOT_WT_LOST_SPLIT = {"RETENTION": 0.6, "VARIANT_LOSS": 0.4}
MECHANISM_SPLIT_DELETION_PROB = 0.65

# Fixed evaluation point for the joint / marginal / inflation-ratio
# quantities -- chosen in advance, not searched for after seeing data.
# gis=42 ties directly to BENCHMARKS.tsv HRD03's real GIS-positive
# threshold rather than an arbitrary round number.
EVAL_POINT = {"wt_lost": 1, "gis": 42.0, "sbs3": 0.30}

# --- BAF channel (DEFECT 2) ---
N_BAF_SNPS = 15          # ARBITRARY, disclosed: flanking heterozygous SNPs pooled per segment
BAF_SNP_DEPTH_MEAN = 60.0  # ARBITRARY, disclosed: representative per-SNP depth away from the at-risk variant
NORMAL_BAF_DEPTH_MEAN = 40.0

# --- Retracted v1 figures (numeric scan, replaces the old filename-only check) ---
RETRACTED_V1_FIGURES = [-3.54, 34.0, 0.9598, 0.9976, 15.13, 4.45, 0.99, 80.0, 91.7]
V1_SCAN_REL_TOL = 1e-3
V1_SCAN_ABS_TOL = 1e-6


# ============================================================================
# Math helpers (stdlib only)
# ============================================================================

def phi_pdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


def Phi(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def simpson_integrate(f, lo: float, hi: float, n: int) -> float:
    """Composite Simpson's rule, n even. Stdlib only."""
    if n % 2 == 1:
        n += 1
    h = (hi - lo) / n
    total = f(lo) + f(hi)
    for i in range(1, n):
        x = lo + i * h
        total += (4 if i % 2 == 1 else 2) * f(x)
    return total * h / 3


def expected_vaf(purity: float, cn_total: int, mutant_copies: int) -> float:
    """PROTOCOL.md §5.2 binomial VAF model, exact formula:
    E[VAF|X] = (p*X + (1-p)*1) / (p*CN_t + (1-p)*2)."""
    return (purity * mutant_copies + (1 - purity) * 1) / (purity * cn_total + (1 - purity) * 2)


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * (p / 100)
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


# ============================================================================
# Latent-model marginal / joint / product-of-marginals LR (DEFECT 3 / 4)
# ============================================================================

def marginal_wt_lost_prob(arm: str, cls: str) -> float:
    """P(WT_LOST_DIRECTION | class), integrating out Z ~ Normal(muZ, 1).
    Exact closed form (the Gaussian-probit convolution identity):
    E_Z[Phi(a+bZ)] = Phi( (a + b*muZ) / sqrt(1 + b^2 * Var(Z)) )."""
    link = WT_LOST_LINK[arm]
    muZ = Z_MEAN[arm][cls]
    return Phi((link["a"] + link["b"] * muZ) / math.sqrt(1 + link["b"] ** 2 * Z_SD ** 2))


def marginal_gaussian_feature_params(link: dict, arm: str, cls: str) -> tuple[float, float]:
    muZ = Z_MEAN[arm][cls]
    mean = link["c"] + link["d"] * muZ
    sd = math.sqrt((link["d"] ** 2) * (Z_SD ** 2) + link["sigma"] ** 2)
    return mean, sd


def sbs3_clipped_density(x: float, mean: float, sd: float) -> tuple[float, str]:
    """P06R3: the analytic density of the CLIPPED SBS3 marginal (or of the
    conditional-on-Z distribution, at whichever mean/sd is passed in), the
    quantity _emit_sample() actually draws --
    sbs3 = min(SBS3_CLIP_HI, max(SBS3_CLIP_LO, raw)), raw ~ Normal(mean, sd).

    Clipping is a MEASURE-PRESERVING IDENTITY MAP on the open interval
    (SBS3_CLIP_LO, SBS3_CLIP_HI): for any [a, b) strictly inside that
    interval, P(clip(raw) in [a, b)) == P(raw in [a, b)) exactly, because
    clip(v) == v there. So the continuous density on the interior is
    UNCHANGED by clipping -- phi_pdf(x, mean, sd) is already the exact
    density there, not an approximation. Only the two boundary points
    x == SBS3_CLIP_LO and x == SBS3_CLIP_HI carry additional discrete point
    mass (P(raw <= lo) and P(raw >= hi) respectively), which a plain
    continuous-density evaluation cannot represent and which a caller must
    not silently divide as if it were a Lebesgue density. See
    FIDELITY_AUDIT.md for the derivation and the empirical (exact-CDF,
    binomial z-test) confirmation against the real generated data.

    Returns (value, kind); kind is "density" on the interior or
    "point_mass" at a boundary, so a caller cannot conflate the two without
    the tuple unpacking telling it which one it got."""
    if x <= SBS3_CLIP_LO:
        return Phi((SBS3_CLIP_LO - mean) / sd), "point_mass"
    if x >= SBS3_CLIP_HI:
        return 1.0 - Phi((SBS3_CLIP_HI - mean) / sd), "point_mass"
    return phi_pdf(x, mean, sd), "density"


def sbs3_clipped_lr(x_sbs3: float, mean1: float, sd1: float, mean0: float, sd0: float) -> float:
    """LR of the CLIPPED SBS3 marginal at x_sbs3 between two class-
    conditional Normal(mean, sd) raw distributions. Requires both classes'
    evaluation to be the SAME kind (both interior densities, or both
    boundary point masses) -- a density-over-point-mass ratio is not a
    meaningful likelihood ratio, so this raises rather than silently
    returning a nonsense number if that ever happens (it does not at the
    current EVAL_POINT: see FIDELITY_AUDIT.md)."""
    v1, kind1 = sbs3_clipped_density(x_sbs3, mean1, sd1)
    v0, kind0 = sbs3_clipped_density(x_sbs3, mean0, sd0)
    if kind1 != kind0:
        raise ValueError(f"sbs3_clipped_lr: mismatched evaluation kinds at x={x_sbs3} "
                          f"({kind1} vs {kind0}) -- LR undefined between a density and a point mass")
    return v1 / v0


def product_of_marginals_lr(arm: str, x: dict) -> float:
    p1 = marginal_wt_lost_prob(arm, "Pathogenic")
    p0 = marginal_wt_lost_prob(arm, "Benign")
    lr_wt = (p1 if x["wt_lost"] == 1 else (1 - p1)) / (p0 if x["wt_lost"] == 1 else (1 - p0))

    gis_mean1, gis_sd1 = marginal_gaussian_feature_params(GIS_LINK[arm], arm, "Pathogenic")
    gis_mean0, gis_sd0 = marginal_gaussian_feature_params(GIS_LINK[arm], arm, "Benign")
    lr_gis = phi_pdf(x["gis"], gis_mean1, gis_sd1) / phi_pdf(x["gis"], gis_mean0, gis_sd0)

    sbs3_mean1, sbs3_sd1 = marginal_gaussian_feature_params(SBS3_LINK[arm], arm, "Pathogenic")
    sbs3_mean0, sbs3_sd0 = marginal_gaussian_feature_params(SBS3_LINK[arm], arm, "Benign")
    lr_sbs3 = sbs3_clipped_lr(x["sbs3"], sbs3_mean1, sbs3_sd1, sbs3_mean0, sbs3_sd0)

    return lr_wt * lr_gis * lr_sbs3


def joint_density(arm: str, cls: str, x: dict, z_lo: float = -8.0, z_hi: float = 8.0, n_steps: int = 4000) -> float:
    """The TRUE joint density of (wt_lost, gis, sbs3) given class,
    integrating out the shared latent Z -- 1D numerical integration
    (Simpson's rule), not a product of marginals. The sbs3 term uses
    sbs3_clipped_density (P06R3) against the CONDITIONAL-ON-Z mean/sd
    (c + d*z, sigma), since the same clip-is-identity-on-the-interior
    argument applies pointwise for every fixed z, not only to the
    Z-marginalized distribution."""
    wt_link = WT_LOST_LINK[arm]
    gis_link = GIS_LINK[arm]
    sbs3_link = SBS3_LINK[arm]
    muZ = Z_MEAN[arm][cls]

    def integrand(z: float) -> float:
        p_wt = Phi(wt_link["a"] + wt_link["b"] * z)
        wt_term = p_wt if x["wt_lost"] == 1 else (1 - p_wt)
        gis_term = phi_pdf(x["gis"], gis_link["c"] + gis_link["d"] * z, gis_link["sigma"])
        sbs3_term, _kind = sbs3_clipped_density(x["sbs3"], sbs3_link["c"] + sbs3_link["d"] * z, sbs3_link["sigma"])
        z_term = phi_pdf(z, muZ, Z_SD)
        return wt_term * gis_term * sbs3_term * z_term

    return simpson_integrate(integrand, z_lo, z_hi, n_steps)


def joint_lr(arm: str, x: dict) -> float:
    return joint_density(arm, "Pathogenic", x) / joint_density(arm, "Benign", x)


def normalization_self_check(arm: str, cls: str, n_steps: int = 4000) -> float:
    """Self-check: integrating the joint density over both wt_lost outcomes
    and over gis/sbs3 (via their own marginal normalization, since for
    fixed wt_lost the gis/sbs3 x Z integrand is a proper density in Z
    only up to the point-evaluation of gis/sbs3 -- so instead check that
    P(wt_lost=1|class) + P(wt_lost=0|class), each obtained by integrating
    Phi/[1-Phi] x Z-density over Z alone, sums to 1.0."""
    wt_link = WT_LOST_LINK[arm]
    muZ = Z_MEAN[arm][cls]
    p1 = simpson_integrate(lambda z: Phi(wt_link["a"] + wt_link["b"] * z) * phi_pdf(z, muZ, Z_SD), -8, 8, n_steps)
    p0 = simpson_integrate(lambda z: (1 - Phi(wt_link["a"] + wt_link["b"] * z)) * phi_pdf(z, muZ, Z_SD), -8, 8, n_steps)
    return p1 + p0


# ============================================================================
# Subtype-conditional and subtype-collapsed truth quantities (subtype fix).
#
# The functions above (marginal_wt_lost_prob, marginal_gaussian_feature_params,
# joint_density, joint_lr, product_of_marginals_lr) are UNCHANGED -- they
# still compute the Z-only-integrated marginal/joint at a single (arm, cls)
# pair, with no subtype term. They are kept exactly as they were (not
# repurposed) so stake_ablation.py's existing `true_reference_lr()` call
# sites keep meaning exactly what they always meant -- the model's Z-only
# view, evaluated with no subtype weighting. They are NOT what
# compute_truth_quantities() below uses for the pooled/"AFTER" quantities
# any more, since a bare Z-only marginal is no longer the correct pooled
# truth once subtype genuinely shifts each stratum's baseline (see
# SUBTYPE_MODEL.md and TRUTH_DELTA.md's own note on this).
#
# New below: SUBTYPE-CONDITIONAL versions (evaluated within one named
# subtype stratum) and SUBTYPE-COLLAPSED versions (the correct pooled/
# marginal quantity once subtype is a real mixture component -- a
# prevalence-weighted MIXTURE, not a single Gaussian, so "collapsed" is
# never simply "bare functions with subtype ignored").
# ============================================================================

def marginal_wt_lost_prob_subtype(arm: str, cls: str, subtype: str) -> float:
    """Same Gaussian-probit convolution identity as marginal_wt_lost_prob,
    with Z's mean shifted by SUBTYPE_Z_SHIFT[subtype] (Z's spread, Z_SD,
    is unchanged by subtype -- SUBTYPE_MODEL.md §1)."""
    link = WT_LOST_LINK[arm]
    muZ = Z_MEAN[arm][cls] + SUBTYPE_Z_SHIFT[subtype]
    return Phi((link["a"] + link["b"] * muZ) / math.sqrt(1 + link["b"] ** 2 * Z_SD ** 2))


def marginal_gaussian_feature_params_subtype(link: dict, arm: str, cls: str, subtype: str,
                                              direct_shift: float = 0.0) -> tuple[float, float]:
    """Same closed form as marginal_gaussian_feature_params, with Z's mean
    shifted by SUBTYPE_Z_SHIFT[subtype] and an optional additional
    DIRECT shift on the feature itself (GIS only -- SUBTYPE_MODEL.md §2;
    SBS3 always passes direct_shift=0.0, per §3)."""
    muZ = Z_MEAN[arm][cls] + SUBTYPE_Z_SHIFT[subtype]
    mean = link["c"] + link["d"] * muZ + direct_shift
    sd = math.sqrt((link["d"] ** 2) * (Z_SD ** 2) + link["sigma"] ** 2)
    return mean, sd


def product_of_marginals_lr_subtype(arm: str, subtype: str, x: dict) -> float:
    p1 = marginal_wt_lost_prob_subtype(arm, "Pathogenic", subtype)
    p0 = marginal_wt_lost_prob_subtype(arm, "Benign", subtype)
    lr_wt = (p1 if x["wt_lost"] == 1 else (1 - p1)) / (p0 if x["wt_lost"] == 1 else (1 - p0))

    gis_mean1, gis_sd1 = marginal_gaussian_feature_params_subtype(GIS_LINK[arm], arm, "Pathogenic", subtype,
                                                                    SUBTYPE_GIS_SHIFT[subtype])
    gis_mean0, gis_sd0 = marginal_gaussian_feature_params_subtype(GIS_LINK[arm], arm, "Benign", subtype,
                                                                    SUBTYPE_GIS_SHIFT[subtype])
    lr_gis = phi_pdf(x["gis"], gis_mean1, gis_sd1) / phi_pdf(x["gis"], gis_mean0, gis_sd0)

    sbs3_mean1, sbs3_sd1 = marginal_gaussian_feature_params_subtype(SBS3_LINK[arm], arm, "Pathogenic", subtype)
    sbs3_mean0, sbs3_sd0 = marginal_gaussian_feature_params_subtype(SBS3_LINK[arm], arm, "Benign", subtype)
    lr_sbs3 = sbs3_clipped_lr(x["sbs3"], sbs3_mean1, sbs3_sd1, sbs3_mean0, sbs3_sd0)

    return lr_wt * lr_gis * lr_sbs3


def joint_density_subtype(arm: str, cls: str, subtype: str, x: dict,
                           z_lo: float = -8.0, z_hi: float = 8.0, n_steps: int = 4000) -> float:
    """Same 1D Simpson's-rule Z-integral as joint_density, with Z's mean
    shifted by SUBTYPE_Z_SHIFT[subtype] and GIS's conditional-on-Z mean
    additionally shifted by SUBTYPE_GIS_SHIFT[subtype]."""
    wt_link = WT_LOST_LINK[arm]
    gis_link = GIS_LINK[arm]
    sbs3_link = SBS3_LINK[arm]
    muZ = Z_MEAN[arm][cls] + SUBTYPE_Z_SHIFT[subtype]
    gis_shift = SUBTYPE_GIS_SHIFT[subtype]

    def integrand(z: float) -> float:
        p_wt = Phi(wt_link["a"] + wt_link["b"] * z)
        wt_term = p_wt if x["wt_lost"] == 1 else (1 - p_wt)
        gis_term = phi_pdf(x["gis"], gis_link["c"] + gis_link["d"] * z + gis_shift, gis_link["sigma"])
        sbs3_term, _kind = sbs3_clipped_density(x["sbs3"], sbs3_link["c"] + sbs3_link["d"] * z, sbs3_link["sigma"])
        z_term = phi_pdf(z, muZ, Z_SD)
        return wt_term * gis_term * sbs3_term * z_term

    return simpson_integrate(integrand, z_lo, z_hi, n_steps)


def joint_lr_subtype(arm: str, subtype: str, x: dict) -> float:
    return joint_density_subtype(arm, "Pathogenic", subtype, x) / joint_density_subtype(arm, "Benign", subtype, x)


# --- Subtype-collapsed (pooled/marginal) quantities: the CORRECT "AFTER"
# replacement for the pre-subtype-model 16 quantities. Subtype is now a
# genuine mixture component, so "collapsed" means a prevalence-weighted
# MIXTURE over subtype, never simply re-using the bare (no-subtype)
# functions above. ---

def marginal_wt_lost_prob_collapsed(arm: str, cls: str) -> float:
    """Exact by the law of total probability (WT_LOST is a probability,
    so its subtype-marginal IS the prevalence-weighted average of its
    per-subtype conditional probabilities -- no approximation)."""
    return sum(PAM50_PROPORTIONS[st] * marginal_wt_lost_prob_subtype(arm, cls, st) for st in PAM50_PROPORTIONS)


def gaussian_density_collapsed(x0: float, link: dict, arm: str, cls: str, direct_shift_dict: dict) -> float:
    """Mixture density at x0: sum over subtype of prevalence-weighted
    per-subtype Gaussian densities. Exact (a Gaussian MIXTURE's density at
    a point is exactly this weighted sum -- not itself Gaussian, and not
    approximable by phi_pdf(x0, mixture_mean, mixture_sd))."""
    return sum(
        PAM50_PROPORTIONS[st] * phi_pdf(x0, *marginal_gaussian_feature_params_subtype(
            link, arm, cls, st, direct_shift_dict.get(st, 0.0)))
        for st in PAM50_PROPORTIONS
    )


def sbs3_density_collapsed(x0: float, arm: str, cls: str) -> tuple[float, set[str]]:
    """Same mixture-of-densities logic as gaussian_density_collapsed, but
    through sbs3_clipped_density (P06R3) per subtype component, since SBS3
    is clipped. Returns (value, {kinds seen}) -- the caller should assert
    kinds == {"density"} before treating the result as an ordinary LR
    numerator/denominator; a mix of "density" and "point_mass" components
    would mean x0 sits interior for some subtypes and at the boundary for
    others, which this project's current EVAL_POINT never triggers but
    which must not be silently mishandled if a future EVAL_POINT does."""
    total = 0.0
    kinds: set[str] = set()
    for st, w in PAM50_PROPORTIONS.items():
        mean, sd = marginal_gaussian_feature_params_subtype(SBS3_LINK[arm], arm, cls, st)
        val, kind = sbs3_clipped_density(x0, mean, sd)
        total += w * val
        kinds.add(kind)
    return total, kinds


def joint_density_collapsed(arm: str, cls: str, x: dict) -> float:
    return sum(PAM50_PROPORTIONS[st] * joint_density_subtype(arm, cls, st, x) for st in PAM50_PROPORTIONS)


def joint_lr_collapsed(arm: str, x: dict) -> float:
    return joint_density_collapsed(arm, "Pathogenic", x) / joint_density_collapsed(arm, "Benign", x)


def product_of_marginals_lr_collapsed(arm: str, x: dict) -> float:
    """The 'naive' estimator's target under the subtype-aware model: blind
    to BOTH the shared-Z correlation (product, not joint) AND to subtype
    (each per-feature density is the prevalence-weighted mixture, not a
    per-subtype-stratified fit) -- exactly what a pipeline that has never
    heard of subtype stratification would compute."""
    p1 = marginal_wt_lost_prob_collapsed(arm, "Pathogenic")
    p0 = marginal_wt_lost_prob_collapsed(arm, "Benign")
    lr_wt = (p1 if x["wt_lost"] == 1 else (1 - p1)) / (p0 if x["wt_lost"] == 1 else (1 - p0))

    gis1 = gaussian_density_collapsed(x["gis"], GIS_LINK[arm], arm, "Pathogenic", SUBTYPE_GIS_SHIFT)
    gis0 = gaussian_density_collapsed(x["gis"], GIS_LINK[arm], arm, "Benign", SUBTYPE_GIS_SHIFT)
    lr_gis = gis1 / gis0

    sbs3_1, kinds1 = sbs3_density_collapsed(x["sbs3"], arm, "Pathogenic")
    sbs3_0, kinds0 = sbs3_density_collapsed(x["sbs3"], arm, "Benign")
    if kinds1 != {"density"} or kinds0 != {"density"}:
        raise ValueError(f"product_of_marginals_lr_collapsed: sbs3 mixture components are not uniformly "
                          f"'density' kind (Pathogenic kinds={kinds1}, Benign kinds={kinds0}) -- EVAL_POINT "
                          f"sbs3 is no longer interior for every subtype; a mixture LR is undefined here "
                          f"without a boundary-aware generalization this project does not yet have")
    lr_sbs3 = sbs3_1 / sbs3_0

    return lr_wt * lr_gis * lr_sbs3


def _pooled_quantity_rows(arm: str) -> list[dict]:
    """The pre-existing 16-quantity structure's 6-quantity block per
    (CORE_HR, DDR_SIGNALING) arm, now correctly re-derived as the subtype-
    COLLAPSED (prevalence-weighted mixture over all 5 subtypes) quantity --
    the subtype fix's "AFTER" value for each. See TRUTH_DELTA.md for the
    before/after comparison and why these move only slightly."""
    rows = []
    p1 = marginal_wt_lost_prob_collapsed(arm, "Pathogenic")
    p0 = marginal_wt_lost_prob_collapsed(arm, "Benign")
    rows.append({
        "quantity": f"{arm.lower()}_wt_lost_direction_LR", "injected_value": p1 / p0,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "categorical",
        "derivation": f"subtype fix: P(WT_LOST_DIRECTION|Pathogenic)={p1:.6f} / P(...|Benign)={p0:.6f}, each "
                       f"the PAM50-prevalence-weighted average of the per-subtype Gaussian-probit-convolution "
                       f"probability (marginal_wt_lost_prob_subtype) -- exact by the law of total probability, "
                       f"not an approximation.",
    })

    x_gis = EVAL_POINT["gis"]
    gis1 = gaussian_density_collapsed(x_gis, GIS_LINK[arm], arm, "Pathogenic", SUBTYPE_GIS_SHIFT)
    gis0 = gaussian_density_collapsed(x_gis, GIS_LINK[arm], arm, "Benign", SUBTYPE_GIS_SHIFT)
    rows.append({
        "quantity": f"{arm.lower()}_gis_score_LR", "injected_value": gis1 / gis0,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "continuous_gaussian_mixture_marginal",
        "derivation": f"subtype fix: f(GIS={x_gis}|Pathogenic)={gis1:.6f} / f(GIS={x_gis}|Benign)={gis0:.6f}, "
                       f"each a PAM50-prevalence-weighted MIXTURE of 5 per-subtype Gaussian densities "
                       f"(gaussian_density_collapsed), not a single Gaussian -- Basal's SUBTYPE_GIS_SHIFT/"
                       f"SUBTYPE_Z_SHIFT genuinely shift that component's mean relative to the other 4, so "
                       f"the true marginal is a real mixture, computed exactly (Simpson/closed-form, no MC).",
    })

    x_sbs3 = EVAL_POINT["sbs3"]
    sbs3_1, kinds1 = sbs3_density_collapsed(x_sbs3, arm, "Pathogenic")
    sbs3_0, kinds0 = sbs3_density_collapsed(x_sbs3, arm, "Benign")
    rows.append({
        "quantity": f"{arm.lower()}_sbs3_exposure_LR", "injected_value": sbs3_1 / sbs3_0,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "continuous_gaussian_mixture_marginal",
        "derivation": f"subtype fix: f_clipped(SBS3={x_sbs3}|Pathogenic)={sbs3_1:.6f} (component kinds "
                       f"{kinds1}) / f_clipped(SBS3={x_sbs3}|Benign)={sbs3_0:.6f} (component kinds {kinds0}), "
                       f"each a PAM50-prevalence-weighted mixture of 5 per-subtype clipped densities "
                       f"(sbs3_density_collapsed, P06R3's clip-is-identity-on-the-interior argument applied "
                       f"per component); SBS3 carries no direct subtype term (SUBTYPE_MODEL.md §3), only the "
                       f"small Z-mediated shift, so this moves only slightly from the pre-subtype-fix value.",
    })

    jlr = joint_lr_collapsed(arm, EVAL_POINT)
    plr = product_of_marginals_lr_collapsed(arm, EVAL_POINT)
    rows.append({
        "quantity": f"{arm.lower()}_joint_LR", "injected_value": jlr,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "joint_latent_model",
        "derivation": f"subtype fix: joint_density_collapsed(x*|Pathogenic)/joint_density_collapsed(x*|Benign) "
                       f"at x*={EVAL_POINT} -- each joint_density_collapsed is a PAM50-prevalence-weighted sum "
                       f"of 5 per-subtype joint_density_subtype values, each itself a 1D Simpson's-rule "
                       f"integral over Z within that subtype stratum. Correctly accounts for BOTH the shared-Z "
                       f"correlation (DEFECT 3) AND the subtype mixture (this fix) -- NOT a product of "
                       f"marginals, and NOT subtype-blind.",
    })
    rows.append({
        "quantity": f"{arm.lower()}_product_of_marginals_LR", "injected_value": plr,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "product_of_marginals",
        "derivation": f"subtype fix: naive product of the 3 subtype-collapsed marginal per-feature LRs above, "
                       f"evaluated at the SAME x*={EVAL_POINT} -- the quantity an estimator that is BOTH "
                       f"conditional-independence-assuming (ignores shared-Z) AND subtype-blind (never "
                       f"stratifies by PAM50 subtype) would recover -- the fully naive baseline this fix's "
                       f"joint-vs-marginal ratio below is measured against.",
    })
    rows.append({
        "quantity": f"{arm.lower()}_joint_vs_marginal_inflation_ratio", "injected_value": jlr / plr,
        "estimand": "LR_RATIO", "is_null": "FALSE", "feature_type": "diagnostic_ratio",
        "derivation": f"{arm.lower()}_joint_LR / {arm.lower()}_product_of_marginals_LR -- P09's known "
                       f"inflation target; != 1.0 both because the 3 features share latent Z (DEFECT 3) and "
                       f"because the naive denominator ignores the subtype mixture this fix adds.",
    })
    return rows


def _subtype_quantity_rows(arm: str, subtype: str) -> list[dict]:
    """Per-subtype-stratum version of the same 6-quantity block, so gate6
    can score stratified recovery (this task's own explicit requirement)."""
    rows = []
    prefix = f"{arm.lower()}_{subtype.lower().replace('-', '_')}"
    p1 = marginal_wt_lost_prob_subtype(arm, "Pathogenic", subtype)
    p0 = marginal_wt_lost_prob_subtype(arm, "Benign", subtype)
    rows.append({
        "quantity": f"{prefix}_wt_lost_direction_LR", "injected_value": p1 / p0,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "categorical_subtype_stratum",
        "derivation": f"P(WT_LOST_DIRECTION|Pathogenic,{subtype})={p1:.6f} / P(...|Benign,{subtype})={p0:.6f}, "
                       f"Gaussian-probit convolution with Z's mean shifted by SUBTYPE_Z_SHIFT[{subtype}]="
                       f"{SUBTYPE_Z_SHIFT[subtype]}.",
    })

    x_gis = EVAL_POINT["gis"]
    gis_mean1, gis_sd1 = marginal_gaussian_feature_params_subtype(GIS_LINK[arm], arm, "Pathogenic", subtype,
                                                                    SUBTYPE_GIS_SHIFT[subtype])
    gis_mean0, gis_sd0 = marginal_gaussian_feature_params_subtype(GIS_LINK[arm], arm, "Benign", subtype,
                                                                    SUBTYPE_GIS_SHIFT[subtype])
    rows.append({
        "quantity": f"{prefix}_gis_score_LR",
        "injected_value": phi_pdf(x_gis, gis_mean1, gis_sd1) / phi_pdf(x_gis, gis_mean0, gis_sd0),
        "estimand": "LR", "is_null": "FALSE", "feature_type": "continuous_gaussian_subtype_stratum",
        "derivation": f"f(GIS={x_gis}|Pathogenic,{subtype}~N({gis_mean1:.4f},{gis_sd1:.4f})) / "
                       f"f(GIS={x_gis}|Benign,{subtype}~N({gis_mean0:.4f},{gis_sd0:.4f})); SUBTYPE_GIS_SHIFT"
                       f"[{subtype}]={SUBTYPE_GIS_SHIFT[subtype]}, SUBTYPE_Z_SHIFT[{subtype}]="
                       f"{SUBTYPE_Z_SHIFT[subtype]}.",
    })

    x_sbs3 = EVAL_POINT["sbs3"]
    sbs3_mean1, sbs3_sd1 = marginal_gaussian_feature_params_subtype(SBS3_LINK[arm], arm, "Pathogenic", subtype)
    sbs3_mean0, sbs3_sd0 = marginal_gaussian_feature_params_subtype(SBS3_LINK[arm], arm, "Benign", subtype)
    sbs3_dens1, sbs3_kind1 = sbs3_clipped_density(x_sbs3, sbs3_mean1, sbs3_sd1)
    sbs3_dens0, sbs3_kind0 = sbs3_clipped_density(x_sbs3, sbs3_mean0, sbs3_sd0)
    rows.append({
        "quantity": f"{prefix}_sbs3_exposure_LR", "injected_value": sbs3_dens1 / sbs3_dens0,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "continuous_gaussian_subtype_stratum",
        "derivation": f"f_clipped(SBS3={x_sbs3}|Pathogenic,{subtype}~N({sbs3_mean1:.4f},{sbs3_sd1:.4f}))="
                       f"{sbs3_dens1:.6f} ({sbs3_kind1}) / f_clipped(SBS3={x_sbs3}|Benign,{subtype}~N("
                       f"{sbs3_mean0:.4f},{sbs3_sd0:.4f}))={sbs3_dens0:.6f} ({sbs3_kind0}); SBS3 has no direct "
                       f"subtype term (SUBTYPE_MODEL.md §3), only SUBTYPE_Z_SHIFT[{subtype}]="
                       f"{SUBTYPE_Z_SHIFT[subtype]}.",
    })

    jlr = joint_lr_subtype(arm, subtype, EVAL_POINT)
    plr = product_of_marginals_lr_subtype(arm, subtype, EVAL_POINT)
    rows.append({
        "quantity": f"{prefix}_joint_LR", "injected_value": jlr,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "joint_latent_model_subtype_stratum",
        "derivation": f"joint_density_subtype(x*|Pathogenic,{subtype})/joint_density_subtype(x*|Benign,"
                       f"{subtype}) at x*={EVAL_POINT}, 1D Simpson's-rule integral over Z within this subtype "
                       f"stratum only.",
    })
    rows.append({
        "quantity": f"{prefix}_product_of_marginals_LR", "injected_value": plr,
        "estimand": "LR", "is_null": "FALSE", "feature_type": "product_of_marginals_subtype_stratum",
        "derivation": f"naive product of the 3 per-feature LRs above, within this subtype stratum only -- "
                       f"the quantity a conditional-independence-assuming estimator would recover if it "
                       f"stratified by subtype but still ignored the shared-Z correlation.",
    })
    rows.append({
        "quantity": f"{prefix}_joint_vs_marginal_inflation_ratio", "injected_value": jlr / plr,
        "estimand": "LR_RATIO", "is_null": "FALSE", "feature_type": "diagnostic_ratio_subtype_stratum",
        "derivation": f"{prefix}_joint_LR / {prefix}_product_of_marginals_LR, within this subtype stratum.",
    })
    return rows


def _null_arm_pooled_rows() -> list[dict]:
    jlr_null = joint_lr_collapsed("NULL_ARM", EVAL_POINT)
    plr_null = product_of_marginals_lr_collapsed("NULL_ARM", EVAL_POINT)
    return [
        {
            "quantity": "null_arm_full_vector_joint_LR", "injected_value": jlr_null,
            "estimand": "LR", "is_null": "TRUE", "feature_type": "joint_latent_model",
            "derivation": "NULL_ARM's Z_MEAN is identical (0.0) for Pathogenic and Benign, and SUBTYPE_Z_SHIFT/"
                          "SUBTYPE_GIS_SHIFT are applied IDENTICALLY to both classes within every subtype "
                          "(never class-dependent) -- so f(x|Pathogenic)===f(x|Benign) as full mixture "
                          "distributions still holds exactly under the subtype fix, joint_LR(x)===1.0 for "
                          "EVERY evidence vector x, at every subtype stratum and pooled. Verified numerically "
                          "at EVAL_POINT, pooled across subtype.",
        },
        {
            "quantity": "null_arm_full_vector_product_of_marginals_LR", "injected_value": plr_null,
            "estimand": "LR", "is_null": "TRUE", "feature_type": "product_of_marginals",
            "derivation": "Each marginal (subtype-collapsed mixture included) of two identical distributions "
                          "is itself identical, so the naive product-of-marginals LR is also exactly 1.0 here, "
                          "pooled across subtype -- the subtype fix does not disturb DEFECT 4's null.",
        },
        {
            "quantity": "null_arm_full_vector_inflation_ratio", "injected_value": jlr_null / plr_null,
            "estimand": "LR_RATIO", "is_null": "TRUE", "feature_type": "diagnostic_ratio",
            "derivation": "joint/product ratio for the null arm, pooled across subtype; == 1.0 exactly since "
                          "both quantities above are each exactly 1.0 by construction.",
        },
    ]


def _null_arm_subtype_rows(subtype: str) -> list[dict]:
    prefix = f"null_arm_{subtype.lower().replace('-', '_')}"
    jlr_null = joint_lr_subtype("NULL_ARM", subtype, EVAL_POINT)
    plr_null = product_of_marginals_lr_subtype("NULL_ARM", subtype, EVAL_POINT)
    return [
        {
            "quantity": f"{prefix}_full_vector_joint_LR", "injected_value": jlr_null,
            "estimand": "LR", "is_null": "TRUE", "feature_type": "joint_latent_model_subtype_stratum",
            "derivation": f"NULL_ARM within {subtype} only: SUBTYPE_Z_SHIFT[{subtype}] and "
                           f"SUBTYPE_GIS_SHIFT[{subtype}] are applied identically to Pathogenic and Benign "
                           f"(both already share Z_MEAN=0.0), so f(x|Pathogenic,{subtype})===f(x|Benign,"
                           f"{subtype}) exactly -- joint_LR===1.0 within this stratum too, re-proven per "
                           f"STEP 2's explicit requirement, not merely assumed to carry over from the pooled "
                           f"proof above.",
        },
        {
            "quantity": f"{prefix}_full_vector_product_of_marginals_LR", "injected_value": plr_null,
            "estimand": "LR", "is_null": "TRUE", "feature_type": "product_of_marginals_subtype_stratum",
            "derivation": f"Each per-feature marginal within {subtype}, for two identical (Pathogenic===Benign) "
                           f"distributions, is itself identical -- product-of-marginals LR===1.0 exactly, "
                           f"within this stratum.",
        },
        {
            "quantity": f"{prefix}_full_vector_inflation_ratio", "injected_value": jlr_null / plr_null,
            "estimand": "LR_RATIO", "is_null": "TRUE", "feature_type": "diagnostic_ratio_subtype_stratum",
            "derivation": f"joint/product ratio for NULL_ARM within {subtype} only; == 1.0 exactly.",
        },
    ]


def compute_truth_quantities() -> list[dict]:
    rows = []

    for arm in ("CORE_HR", "DDR_SIGNALING"):
        rows.extend(_pooled_quantity_rows(arm))
        for subtype in PAM50_PROPORTIONS:
            rows.extend(_subtype_quantity_rows(arm, subtype))

    # NULL_ARM: DEFECT 4's full-feature-vector null, pooled and per subtype
    # (see _null_arm_pooled_rows/_null_arm_subtype_rows docstrings for why
    # the subtype fix cannot disturb the exact-1.0 property).
    rows.extend(_null_arm_pooled_rows())
    for subtype in PAM50_PROPORTIONS:
        rows.extend(_null_arm_subtype_rows(subtype))

    # Secondary null, kept from v1 per the task's explicit instruction.
    p1 = p0 = 0.50
    rows.append({
        "quantity": "null_sequencing_depth_bucket_LR", "injected_value": p1 / p0,
        "estimand": "LR", "is_null": "TRUE", "feature_type": "categorical",
        "derivation": f"P(HIGH_DEPTH|Pathogenic)={p1} / P(HIGH_DEPTH|Benign)={p0} (engineered identical by "
                       f"construction -- HIGH_DEPTH is a coin flip independent of class in both branches of "
                       f"the generator). Kept as a SECONDARY null per this revision's task -- the PRIMARY "
                       f"null test is now null_arm_full_vector_joint_LR above, a full-feature-vector null, "
                       f"which is the case a prior version's regression got wrong.",
    })

    return rows


# ============================================================================
# PROTOCOL.md §5.1/§5.2 classification logic (self-check only, unchanged
# mechanics from v1 -- this is PROTOCOL's OWN model, not this simulator's).
# ============================================================================

def classify_loh(tumor_ref: int, tumor_alt: int, major: int, minor: int, purity: float) -> str:
    depth = tumor_ref + tumor_alt
    if depth < MIN_EVALUABLE_DEPTH:
        return "NOT_EVALUABLE"
    cn_total = major + minor
    vaf = tumor_alt / depth if depth > 0 else 0.0
    if minor >= 1:
        if 0.35 <= vaf <= 0.65:
            return "RETAINED"
    vaf_mutant_retained = expected_vaf(purity, cn_total, major)
    vaf_wt_retained = expected_vaf(purity, cn_total, 0)
    p_mutant = binom_two_sided_pvalue(tumor_alt, depth, vaf_mutant_retained)
    p_wt = binom_two_sided_pvalue(tumor_alt, depth, vaf_wt_retained)
    mutant_not_rejected = p_mutant >= 0.05
    wt_not_rejected = p_wt >= 0.05
    if minor >= 1:
        return "LOH_AMBIGUOUS" if (mutant_not_rejected or wt_not_rejected) else "RETAINED"
    if mutant_not_rejected and not wt_not_rejected:
        return "LOH_SECOND_HIT"
    if wt_not_rejected and not mutant_not_rejected:
        return "LOH_NON_SECOND_HIT"
    return "LOH_AMBIGUOUS"


def binom_two_sided_pvalue(k: int, n: int, p: float) -> float:
    if n == 0:
        return 1.0
    p = min(max(p, 1e-9), 1 - 1e-9)

    def pmf(i: int) -> float:
        return math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))

    p_obs = pmf(k)
    total = 0.0
    for i in range(n + 1):
        pi = pmf(i)
        if pi <= p_obs * (1 + 1e-9):
            total += pi
    return min(1.0, total)


DIRECTION_OF_PROTOCOL_CATEGORY = {
    # classify_loh only recovers DIRECTION (PROTOCOL.md's own model has no
    # concept of copy-neutral vs deletion mechanism) -- this collapses this
    # simulator's mechanism-aware assigned category down to the same
    # direction-only vocabulary for a fair self-check comparison.
    "RETENTION": "RETAINED",
    "CN_NEUTRAL_LOH_WT_LOSS": "LOH_SECOND_HIT",
    "WT_LOSS": "LOH_SECOND_HIT",
    "VARIANT_LOSS": "LOH_NON_SECOND_HIT",
    "AMBIGUOUS": "LOH_AMBIGUOUS",
    "NOT_EVALUABLE": "NOT_EVALUABLE",
}


# ============================================================================
# Per-locus data generation
# ============================================================================

def binomial_draw(rng: random.Random, n: int, p: float) -> int:
    p = min(max(p, 0.0), 1.0)
    if hasattr(rng, "binomialvariate"):
        return rng.binomialvariate(n, p)
    return sum(1 for _ in range(n) if rng.random() < p)


def draw_category_and_mechanism(rng: random.Random, arm: str, z: float) -> tuple[str, str, str]:
    link = WT_LOST_LINK[arm]
    p_wt_lost = Phi(link["a"] + link["b"] * z)
    if rng.random() < p_wt_lost:
        direction = "WT_LOST"
        mechanism = "DELETION" if rng.random() < MECHANISM_SPLIT_DELETION_PROB else "COPY_NEUTRAL"
        category = "WT_LOSS" if mechanism == "DELETION" else "CN_NEUTRAL_LOH_WT_LOSS"
    else:
        direction = "NOT_WT_LOST"
        if rng.random() < NOT_WT_LOST_SPLIT["RETENTION"]:
            category, mechanism = "RETENTION", "NA"
        else:
            mechanism = "DELETION" if rng.random() < MECHANISM_SPLIT_DELETION_PROB else "COPY_NEUTRAL"
            category = "VARIANT_LOSS"
    return category, mechanism, direction


def cn_for_category(category: str, mechanism: str, baseline_cn: int, hidden_direction: str = "") -> tuple[int, int, int]:
    """Returns (major, minor, mutant_copies)."""
    if category == "RETENTION":
        half = baseline_cn // 2
        return half, half, half
    if category == "CN_NEUTRAL_LOH_WT_LOSS":
        return baseline_cn, 0, baseline_cn
    if category == "WT_LOSS":
        return 1, 0, 1
    if category == "VARIANT_LOSS":
        major = 1 if mechanism == "DELETION" else baseline_cn
        return major, 0, 0
    if category == "AMBIGUOUS":
        # DEFECT 2: deletion-type (cn_total=1) so BAF cleanly shows m=0
        # (real LOH), while the DIRECTION is left genuinely underpowered
        # by low depth alone (see generate()), not by a rigged VAF target.
        mutant_copies = 1 if hidden_direction == "WT_LOST" else 0
        return 1, 0, mutant_copies
    if category == "NOT_EVALUABLE":
        half = baseline_cn // 2
        return half, half, half
    raise ValueError(category)


def generate_baf_snps(rng: random.Random, purity: float, cn_total: int, major: int, minor: int,
                       n_snps: int, sample_id: str) -> list[dict]:
    """DEFECT 2: B-allele frequencies for flanking heterozygous SNPs on the
    same segment. Each SNP's phase (whether its own alt allele sits on the
    major or minor copy) is independent and unknown a priori (50/50) --
    this is what makes real BAF tracks show two symmetric bands for an
    imbalanced segment, collapsing to one band for a balanced segment.
    Mirroring (min(vaf,1-vaf)) removes the phase ambiguity, revealing the
    true |allelic imbalance| regardless of which physical allele is 'alt'."""
    rows = []
    for i in range(n_snps):
        phase = "major" if rng.random() < 0.5 else "minor"
        mutant_copies_snp = major if phase == "major" else minor
        depth = max(10, round(rng.gauss(BAF_SNP_DEPTH_MEAN, 12)))
        normal_depth = max(10, round(rng.gauss(NORMAL_BAF_DEPTH_MEAN, 8)))
        vaf_target = expected_vaf(purity, cn_total, mutant_copies_snp)
        tumor_alt = binomial_draw(rng, depth, vaf_target)
        tumor_ref = depth - tumor_alt
        normal_alt = binomial_draw(rng, normal_depth, 0.5)
        normal_ref = normal_depth - normal_alt
        observed_vaf = tumor_alt / depth if depth > 0 else 0.0
        rows.append({
            "sample_id": sample_id, "snp_index": i, "phase": phase,
            "normal_ref_reads": normal_ref, "normal_alt_reads": normal_alt,
            "tumor_ref_reads": tumor_ref, "tumor_alt_reads": tumor_alt,
            "mirrored_baf": min(observed_vaf, 1 - observed_vaf),
        })
    return rows


# ============================================================================
# Mutation catalog / SBS3-like signature exposure (mechanics unchanged from
# v1; the exposure value itself now comes from the shared-latent model)
# ============================================================================

SBS_CONTEXTS = [
    f"{five}[{sub}]{three}"
    for sub in ("C>A", "C>G", "C>T", "T>A", "T>C", "T>G")
    for five, three in itertools.product("ACGT", "ACGT")
]
assert len(SBS_CONTEXTS) == 96

# P06R2: hrd_shape/background_shape were previously an ARBITRARY, stylized
# C>T-favored construction (v1/v2's _make_shape) never checked for
# resemblance to real COSMIC SBS3. P08 found it was, by real cosine
# similarity, LESS like SBS3 (0.688) than like SBS5 (0.802) -- the
# recovery target this whole feature is named after was never actually
# injected. Fixed here: hrd_shape/background_shape are now the REAL COSMIC
# v3.6 SBS3/SBS5 weight vectors, read from a committed reference file
# extracted live from the installed, gate-verified SigProfilerAssignment
# package (see SIMULATED_data/COSMIC_SBS3_SBS5_v3.6_reference_PROVENANCE.md
# for exact source/digest). No randomization, no hand-tuning: this file's
# SBS3/SBS5 columns are used exactly as COSMIC defines them.
COSMIC_REFERENCE_TSV = REPO_ROOT / "COSMIC_SBS3_SBS5_v3.6_reference.tsv"  # real reference DATA, not a
# simulated output -- lives at repo root (like BENCHMARKS.tsv/PROTOCOL.md), not under SIMULATED_data/,
# so Standing Rule 1's "every output filename carries SIMULATED" rule (about synthetic/simulated
# INPUTS, which this file is not) is not misapplied to it.

# Floors/bands for the acceptance assertion (REQUIRED_P06_CHANGES.md /
# P06R2's task text: "cited, not chosen to pass"). Both numbers ARE the
# real COSMIC v3.6 values themselves (there is no independent literature
# "realistic band" beyond COSMIC's own reference matrix -- that census IS
# the authority on what real cosine similarity between these two
# signatures is). COSINE_SIM_TO_REAL_SBS3_FLOOR is checked by
# scripts/check_p06r2_acceptance.py (a fresh live docker-side extraction
# vs. this committed reference file -- the meaningful version of that
# check, since hrd_shape is trivially identical to itself); the band below
# IS checked at runtime in build_signature_shapes(), since it compares two
# vectors already loaded from this same file to each other.
COSINE_SIM_TO_REAL_SBS3_FLOOR = 0.999  # hrd_shape IS real SBS3; floor allows only float round-trip noise
COSINE_SIM_TO_REAL_SBS5_BAND = (0.78, 0.81)  # real COSMIC v3.6 SBS3-vs-SBS5 = 0.7928 (computed from this file)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0 and nb > 0 else float("nan")


def build_signature_shapes() -> tuple[list[float], list[float]]:
    with open(COSMIC_REFERENCE_TSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    sbs3_by_ctx = {r["Type"]: float(r["SBS3"]) for r in rows}
    sbs5_by_ctx = {r["Type"]: float(r["SBS5"]) for r in rows}
    if set(sbs3_by_ctx) != set(SBS_CONTEXTS):
        raise ValueError(f"{COSMIC_REFERENCE_TSV} context labels do not match SBS_CONTEXTS exactly")
    hrd_shape_raw = [sbs3_by_ctx[c] for c in SBS_CONTEXTS]
    background_shape_raw = [sbs5_by_ctx[c] for c in SBS_CONTEXTS]
    hrd_total = sum(hrd_shape_raw)
    bg_total = sum(background_shape_raw)
    hrd_shape = [w / hrd_total for w in hrd_shape_raw]
    background_shape = [w / bg_total for w in background_shape_raw]

    # This file-internal check catches loading/normalization bugs (wrong
    # column, wrong context order, a corrupted committed file) -- it cannot
    # by itself prove the committed file's SBS3 column really IS live COSMIC
    # data (that requires comparing against a fresh docker-side extraction,
    # which simulate.py does not depend on at runtime; see
    # scripts/check_p06r2_acceptance.py, which does exactly that live
    # re-extraction and diffs it against this same committed file).
    sim_to_sbs5 = cosine_similarity(hrd_shape, background_shape)
    if not (COSINE_SIM_TO_REAL_SBS5_BAND[0] <= sim_to_sbs5 <= COSINE_SIM_TO_REAL_SBS5_BAND[1]):
        raise ValueError(f"hrd_shape-vs-background_shape cosine similarity ({sim_to_sbs5:.6f}) is outside the "
                          f"realistic band {COSINE_SIM_TO_REAL_SBS5_BAND} -- either the shapes are wrong, or the "
                          f"target has become unrealistically easy/hard to separate")
    return hrd_shape, background_shape


# ============================================================================
# Main generation loop
# ============================================================================

def _emit_sample(state: dict, arm: str, cls: str, purity_bin: str, p_lo: float, p_hi: float,
                  depth_regime: str, d_lo: float, d_hi: float, forced_category: str | None,
                  hrd_shape: list[float], background_shape: list[float]) -> None:
    state["sample_idx"] += 1
    sample_idx = state["sample_idx"]
    sample_id = f"SIM-{sample_idx:05d}"
    rng = random.Random(SEED * 1000 + sample_idx)  # per-sample reproducible substream

    purity = rng.uniform(p_lo, p_hi)
    depth = round(rng.uniform(d_lo, d_hi))

    gene = rng.choice(GENE_GROUPS[arm])
    subtype = rng.choices(list(PAM50_PROPORTIONS), weights=list(PAM50_PROPORTIONS.values()))[0]
    ploidy = rng.uniform(*PLOIDY_RANGE)
    wgd = rng.random() < WGD_PREVALENCE
    baseline_cn = 4 if wgd else 2
    normal_depth = max(5, round(rng.gauss(NORMAL_DEPTH_MEAN, 8)))

    # Subtype fix: SUBTYPE_Z_SHIFT applied identically regardless of cls
    # (SUBTYPE_MODEL.md §1) -- a genuine confound, not a second class signal.
    z = rng.gauss(Z_MEAN[arm][cls] + SUBTYPE_Z_SHIFT[subtype], Z_SD)

    hidden_direction = ""
    if forced_category is None:
        category, mechanism, direction = draw_category_and_mechanism(rng, arm, z)
    elif forced_category == "AMBIGUOUS":
        hidden_direction = "WT_LOST" if rng.random() < 0.5 else "NOT_WT_LOST"
        category, mechanism, direction = "AMBIGUOUS", "DELETION", hidden_direction
    else:  # NOT_EVALUABLE
        category, mechanism, direction = "NOT_EVALUABLE", "NA", "NOT_EVALUABLE"

    major, minor, mutant_copies = cn_for_category(category, mechanism, baseline_cn, hidden_direction)
    cn_total = major + minor

    tumor_alt = binomial_draw(rng, depth, expected_vaf(purity, cn_total, mutant_copies))
    tumor_ref = depth - tumor_alt
    normal_alt = binomial_draw(rng, normal_depth, 0.5)
    normal_ref = normal_depth - normal_alt

    # Subtype fix: SUBTYPE_GIS_SHIFT is the explicit, literature-cited direct
    # channel (SUBTYPE_MODEL.md §2), on top of whatever GIS inherits via z.
    gis = GIS_LINK[arm]["c"] + GIS_LINK[arm]["d"] * z + SUBTYPE_GIS_SHIFT[subtype] + rng.gauss(0, GIS_LINK[arm]["sigma"])
    sbs3 = min(SBS3_CLIP_HI, max(SBS3_CLIP_LO, SBS3_LINK[arm]["c"] + SBS3_LINK[arm]["d"] * z + rng.gauss(0, SBS3_LINK[arm]["sigma"])))

    state["sample_rows"].append({
        "sample_id": sample_id, "gene": gene, "gene_group": arm, "pam50_subtype": subtype,
        "purity": round(purity, 4), "ploidy": round(ploidy, 4), "wgd": wgd, "normal_depth": normal_depth,
        "purity_bin": purity_bin, "depth_regime": depth_regime, "gis_score": round(gis, 4),
    })
    state["label_rows"].append({
        "sample_id": sample_id, "true_class": cls, "gene_group": arm, "gene": gene,
        "z_latent": round(z, 6), "hidden_direction": hidden_direction or direction,
    })

    baf = generate_baf_snps(rng, purity, cn_total, major, minor, N_BAF_SNPS, sample_id)
    state["baf_rows_all"].extend(baf)
    mean_mirrored = sum(r["mirrored_baf"] for r in baf) / len(baf)

    state["variant_rows"].append({
        "sample_id": sample_id, "gene": gene, "chrom": "chrSIM", "pos": 1000 + sample_idx,
        "ref": "A", "alt": "G",
        "normal_ref_reads": normal_ref, "normal_alt_reads": normal_alt,
        "tumor_ref_reads": tumor_ref, "tumor_alt_reads": tumor_alt,
        "major_cn": major, "minor_cn": minor,
        "assigned_loh_category": category, "mechanism": mechanism,
        "mirrored_baf_mean": round(mean_mirrored, 6), "n_baf_snps": len(baf),
    })

    recovered = classify_loh(tumor_ref, tumor_alt, major, minor, purity)
    expected_direction_label = DIRECTION_OF_PROTOCOL_CATEGORY[category]
    state["self_check_rows"].append({
        "sample_id": sample_id, "assigned": category, "recovered": recovered,
        "match": recovered == expected_direction_label,
    })

    total_muts = max(5, round(rng.gauss(MEAN_MUTATIONS_PER_EXOME, 15)))
    n_hrd = round(total_muts * sbs3)
    n_bg = total_muts - n_hrd
    counts = [0] * 96
    if n_hrd > 0:
        for ctx in rng.choices(range(96), weights=hrd_shape, k=n_hrd):
            counts[ctx] += 1
    if n_bg > 0:
        for ctx in rng.choices(range(96), weights=background_shape, k=n_bg):
            counts[ctx] += 1
    state["catalog_rows"].append({"sample_id": sample_id, **{SBS_CONTEXTS[i]: counts[i] for i in range(96)}})
    state["exposure_rows"].append({
        "sample_id": sample_id, "sbs3_relative_exposure_true": round(sbs3, 4),
        "total_mutations": total_muts, "n_hrd_process_mutations": n_hrd, "n_background_mutations": n_bg,
    })

    key = (category, arm, cls, purity_bin, depth_regime)
    state["coverage_counts"][key] = state["coverage_counts"].get(key, 0) + 1


def build_coverage_report(coverage_counts: dict) -> list[dict]:
    """Every (category, arm, class, purity_bin, depth_regime) cell in the
    grid, either with its actual count or an explicit OUT_OF_SCOPE
    declaration + reason -- never a silently-blank cell (Standing Rule 4)."""
    rows = []
    depth_regimes_in_grid = [b[0] for b in DEPTH_BINS]
    all_depth_labels = depth_regimes_in_grid + ["AMBIGUOUS_REGIME", "NOT_EVALUABLE_REGIME"]
    all_categories = GRID_CATEGORIES + ["AMBIGUOUS", "NOT_EVALUABLE"]

    for arm in GENE_GROUPS:
        for cls in ("Pathogenic", "Benign"):
            for category in all_categories:
                for purity_bin, _, _ in PURITY_BINS:
                    for depth_label in all_depth_labels:
                        count = coverage_counts.get((category, arm, cls, purity_bin, depth_label), 0)
                        in_scope = (
                            (category in GRID_CATEGORIES and depth_label in depth_regimes_in_grid) or
                            (category == "AMBIGUOUS" and depth_label == "AMBIGUOUS_REGIME") or
                            (category == "NOT_EVALUABLE" and depth_label == "NOT_EVALUABLE_REGIME")
                        )
                        min_required = MIN_PER_CELL_GRID if category in GRID_CATEGORIES else MIN_PER_CELL_SIDE_ARM
                        if not in_scope:
                            rows.append({
                                "category": category, "arm": arm, "class": cls, "purity_bin": purity_bin,
                                "depth_regime": depth_label, "count": count, "min_required": "",
                                "meets_minimum": "", "scope_status": "OUT_OF_SCOPE",
                                "scope_reason": (
                                    f"{category} is defined only in its own depth regime by construction "
                                    f"(AMBIGUOUS: near-floor depth {AMBIGUOUS_DEPTH_RANGE}; NOT_EVALUABLE: "
                                    f"sub-floor depth {NOT_EVALUABLE_DEPTH_RANGE}); it has no representation "
                                    f"in the evaluable-depth grid bins by design, not by omission"
                                ) if category in ("AMBIGUOUS", "NOT_EVALUABLE") else (
                                    f"{category} is one of the 4 evaluable-depth grid categories and is not "
                                    f"generated in the {depth_label} side-arm regime, which is reserved for "
                                    f"AMBIGUOUS/NOT_EVALUABLE by construction"
                                ),
                            })
                        else:
                            rows.append({
                                "category": category, "arm": arm, "class": cls, "purity_bin": purity_bin,
                                "depth_regime": depth_label, "count": count, "min_required": min_required,
                                "meets_minimum": count >= min_required, "scope_status": "IN_SCOPE",
                                "scope_reason": "",
                            })
    return rows


def generate() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    TRUTH_DETAIL_DIR.mkdir(exist_ok=True)

    hrd_shape, background_shape = build_signature_shapes()

    truth_rows = compute_truth_quantities()
    write_simulated_tsv(TRUTH_TSV, truth_rows,
                         ["quantity", "injected_value", "estimand", "is_null", "feature_type", "derivation"],
                         float_repr_cols=["injected_value"])

    state = {
        "sample_idx": 0, "sample_rows": [], "variant_rows": [], "catalog_rows": [], "exposure_rows": [],
        "label_rows": [], "baf_rows_all": [], "self_check_rows": [], "coverage_counts": {},
    }

    for arm in GENE_GROUPS:
        for cls in ("Pathogenic", "Benign"):
            for purity_bin, p_lo, p_hi in PURITY_BINS:
                for depth_bin, d_lo, d_hi in DEPTH_BINS:
                    for _ in range(DRAWS_PER_GRID_CELL):
                        _emit_sample(state, arm, cls, purity_bin, p_lo, p_hi, depth_bin, d_lo, d_hi,
                                     None, hrd_shape, background_shape)
                for _ in range(MIN_PER_CELL_SIDE_ARM):
                    _emit_sample(state, arm, cls, purity_bin, p_lo, p_hi, "AMBIGUOUS_REGIME",
                                 *AMBIGUOUS_DEPTH_RANGE, "AMBIGUOUS", hrd_shape, background_shape)
                for _ in range(MIN_PER_CELL_SIDE_ARM):
                    _emit_sample(state, arm, cls, purity_bin, p_lo, p_hi, "NOT_EVALUABLE_REGIME",
                                 *NOT_EVALUABLE_DEPTH_RANGE, "NOT_EVALUABLE", hrd_shape, background_shape)

    write_simulated_tsv(DATA_DIR / "SIMULATED_sample_metadata.tsv", state["sample_rows"],
                         ["sample_id", "gene", "gene_group", "pam50_subtype", "purity", "ploidy", "wgd",
                          "normal_depth", "purity_bin", "depth_regime", "gis_score"])
    write_simulated_tsv(DATA_DIR / "SIMULATED_variant_calls.tsv", state["variant_rows"],
                         ["sample_id", "gene", "chrom", "pos", "ref", "alt", "normal_ref_reads", "normal_alt_reads",
                          "tumor_ref_reads", "tumor_alt_reads", "major_cn", "minor_cn", "assigned_loh_category",
                          "mechanism", "mirrored_baf_mean", "n_baf_snps"])
    write_simulated_tsv(DATA_DIR / "SIMULATED_baf_segments.tsv", state["baf_rows_all"],
                         ["sample_id", "snp_index", "phase", "normal_ref_reads", "normal_alt_reads",
                          "tumor_ref_reads", "tumor_alt_reads", "mirrored_baf"])
    write_simulated_tsv(DATA_DIR / "SIMULATED_mutation_catalogs.tsv", state["catalog_rows"], ["sample_id"] + SBS_CONTEXTS)
    write_simulated_tsv(DATA_DIR / "SIMULATED_signature_exposures.tsv", state["exposure_rows"],
                         ["sample_id", "sbs3_relative_exposure_true", "total_mutations", "n_hrd_process_mutations", "n_background_mutations"])
    write_simulated_tsv(TRUTH_DETAIL_DIR / "SIMULATED_sample_labels.tsv", state["label_rows"],
                         ["sample_id", "true_class", "gene_group", "gene", "z_latent", "hidden_direction"])

    coverage_rows = build_coverage_report(state["coverage_counts"])
    write_simulated_tsv(DATA_DIR / "SIMULATED_coverage_report.tsv", coverage_rows,
                         ["category", "arm", "class", "purity_bin", "depth_regime", "count", "min_required",
                          "meets_minimum", "scope_status", "scope_reason"])

    n_match = sum(1 for r in state["self_check_rows"] if r["match"])
    n_check = len(state["self_check_rows"])
    write_simulated_report(
        DATA_DIR / "SIMULATED_loh_injection_self_check.md",
        "LOH injection self-check",
        f"Re-classifying every generated sample's tumor/normal read counts with PROTOCOL.md "
        f"§5.1/§5.2's own binomial-test logic (direction only -- PROTOCOL's model has no concept "
        f"of copy-neutral vs deletion mechanism, so CN_NEUTRAL_LOH_WT_LOSS and WT_LOSS are both "
        f"collapsed to LOH_SECOND_HIT for this comparison) recovered the expected direction label "
        f"for {n_match}/{n_check} samples ({100*n_match/n_check:.1f}%). AMBIGUOUS is expected to "
        f"sometimes resolve to a definite direction by chance at its deliberately low, near-floor "
        f"depth (that is what \"ambiguous\" means under a noisy binomial draw); NOT_EVALUABLE is "
        f"expected to match 100% (depth alone determines it).",
    )

    check_no_v1_reuse_numeric(state, truth_rows)

    n_underfilled = sum(1 for r in coverage_rows if r["scope_status"] == "IN_SCOPE" and r["meets_minimum"] is False)
    print(f"Generated {state['sample_idx']} SIMULATED tumor/normal pairs under {DATA_DIR}")
    print(f"Wrote {TRUTH_TSV} ({len(truth_rows)} quantities) and {TRUTH_DETAIL_DIR}")
    print(f"LOH self-check: {n_match}/{n_check} recovered direction matched assigned direction")
    print(f"Coverage report: {len(coverage_rows)} cells, {n_underfilled} IN_SCOPE cell(s) below minimum")
    return state


def write_simulated_tsv(path: Path, rows: list[dict], columns: list[str], float_repr_cols: list[str] | None = None) -> None:
    float_repr_cols = float_repr_cols or []
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for row in rows:
            out = {}
            for c in columns:
                v = row.get(c, "")
                if c in float_repr_cols and isinstance(v, float):
                    v = repr(v)
                out[c] = v
            w.writerow(out)


def write_simulated_report(path: Path, title: str, body: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(BANNER + "\n\n")
        f.write(f"# {title}\n\n")
        f.write(f"SIMULATED: {body}\n")


# ============================================================================
# Numeric v1 scan (replaces the old filename-only check; Standing Rule 3/4:
# the rule is about VALUES, not filenames, so this scans every emitted
# numeric value against the retracted v1 figures at a stated tolerance).
# ============================================================================

def _iter_numeric_cells(rows: list[dict], source_name: str):
    for i, row in enumerate(rows):
        for col, val in row.items():
            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue
            yield source_name, i, col, fval


# TIER_1 is the set of values this check actually cares about: the
# simulator's own asserted DESIGN-LEVEL/ground-truth numbers. A match here
# would be the real, serious "reproduced a retracted figure" finding.
# TIER_2 is every raw per-sample/per-observation value (depths, read
# counts, per-SNP BAFs, ...) -- at n=8388 samples x ~15 BAF SNPs each,
# some of these are EXPECTED to land within tolerance of any given target
# purely by chance, and INTEGER-valued fields (depths, read counts) will
# exactly equal an integer-valued target (34.0, 80.0) at a predictable
# base rate purely from quantization, not from reuse. Both tiers are
# reported in full (Standing Rule 4: never omit a real match), but only
# TIER_1 is treated as evidence bearing on Standing Rule 3.
def check_no_v1_reuse_numeric(state: dict, truth_rows: list[dict]) -> None:
    tier2_sources = [
        (state["sample_rows"], "SIMULATED_sample_metadata.tsv"),
        (state["variant_rows"], "SIMULATED_variant_calls.tsv"),
        (state["exposure_rows"], "SIMULATED_signature_exposures.tsv"),
        (state["baf_rows_all"], "SIMULATED_baf_segments.tsv"),
    ]
    tier1_source = (truth_rows, "SIMULATED_TRUTH.tsv (injected_value column only)")

    def scan_one_tier(sources, restrict_col: str | None) -> list[dict]:
        rows = []
        for v1_value in RETRACTED_V1_FIGURES:
            matches = []
            scanned = 0
            for src_rows, source_name in sources:
                for _src, row_idx, col, fval in _iter_numeric_cells(src_rows, source_name):
                    if restrict_col is not None and col != restrict_col:
                        continue
                    scanned += 1
                    if math.isclose(fval, v1_value, rel_tol=V1_SCAN_REL_TOL, abs_tol=V1_SCAN_ABS_TOL):
                        matches.append(f"{source_name}:row{row_idx}:{col}={fval}")
            rows.append({
                "v1_figure": v1_value, "tolerance_rel": V1_SCAN_REL_TOL, "tolerance_abs": V1_SCAN_ABS_TOL,
                "values_scanned_count": scanned, "any_match_found": bool(matches),
                "matching_locations": "; ".join(matches[:20]) + (f" ... ({len(matches)} total)" if len(matches) > 20 else ""),
            })
        return rows

    tier1_rows = [{**r, "tier": "TIER_1_DESIGN_LEVEL_TRUTH"} for r in scan_one_tier([tier1_source], "injected_value")]
    tier2_rows = [{**r, "tier": "TIER_2_RAW_PER_OBSERVATION"} for r in scan_one_tier(tier2_sources, None)]

    write_simulated_tsv(V1_SCAN_TSV, tier1_rows + tier2_rows,
                         ["tier", "v1_figure", "tolerance_rel", "tolerance_abs", "values_scanned_count",
                          "any_match_found", "matching_locations"])

    tier1_any_match = any(r["any_match_found"] for r in tier1_rows)
    tier2_any_match = any(r["any_match_found"] for r in tier2_rows)
    tier2_scanned_total = sum(r["values_scanned_count"] for r in tier2_rows) // len(RETRACTED_V1_FIGURES)
    tier2_matched_figures = [r["v1_figure"] for r in tier2_rows if r["any_match_found"]]

    report_lines = [BANNER, "", "# Numeric v1-reuse scan (replaces the old filename-only check)", ""]
    report_lines.append(
        f"SIMULATED: this is a scan of VALUES, not filenames -- Standing Rule 3's concern is a "
        f"reproduced NUMBER, and a filename scan (this simulator's v1 approach) cannot detect that at all."
    )
    report_lines.append("")
    report_lines.append(
        f"**Tier 1 (the check that actually matters): every SIMULATED_TRUTH.tsv `injected_value` "
        f"({len(truth_rows)} design-level quantities this simulator asserts as ground truth) scanned "
        f"against all {len(RETRACTED_V1_FIGURES)} retracted v1 figures "
        f"({RETRACTED_V1_FIGURES}) at rel_tol={V1_SCAN_REL_TOL}, abs_tol={V1_SCAN_ABS_TOL}: "
        f"**{'MATCH FOUND' if tier1_any_match else 'ZERO matches'}**. "
        + ("Manual review required before these design-level quantities can be trusted as independent "
           "of the retracted v1 artifacts." if tier1_any_match else
           "None of this simulator's 16 injected ground-truth quantities coincide with a retracted v1 "
           "figure within the stated tolerance.")
    )
    report_lines.append("")
    report_lines.append(
        f"**Tier 2 (context, not itself evidence of reuse): {tier2_scanned_total} raw per-sample/per-"
        f"observation numeric values** (depths, read counts, per-SNP BAFs, purity/ploidy/GIS draws) were "
        f"also scanned against the same 9 figures. "
        + (f"Matches were found for figure(s) {tier2_matched_figures} -- see V1_NUMERIC_SCAN.tsv for exact "
           f"locations. **These are expected, not evidence of reuse**: at n={state['sample_idx']} samples "
           f"(~{tier2_scanned_total} numeric values scanned per figure), (a) INTEGER-valued fields like "
           f"`normal_depth` and read counts will exactly equal an integer-valued target (e.g. 34.0, 80.0) "
           f"at a predictable base rate purely from quantization -- this is arithmetic coincidence, not "
           f"reproduction of a retracted figure's SCIENTIFIC CONTENT; (b) continuous fields (gis_score, "
           f"ploidy) drawn from a wide distribution will occasionally land within a {V1_SCAN_REL_TOL:.1%} "
           f"relative tolerance of any fixed target purely by chance when this many values are scanned. "
           f"No design-level parameter was tuned to produce any of these per-observation coincidences; "
           f"they are logged in full per Standing Rule 4, not filtered out, but are not what this check "
           f"is protecting against -- Tier 1 is."
           if tier2_any_match else "ZERO matches found.")
    )
    (DATA_DIR / "SIMULATED_no_v1_reuse_check.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"V1 numeric scan -- Tier 1 (design-level truth): {'MATCH FOUND' if tier1_any_match else 'no matches'}; "
          f"Tier 2 (raw per-observation, {tier2_scanned_total} values/figure): "
          f"{'matches found (expected, see report)' if tier2_any_match else 'no matches'}")


if __name__ == "__main__":
    generate()
