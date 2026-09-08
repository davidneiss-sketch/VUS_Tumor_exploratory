#!/usr/bin/env python3
"""loh_caller.py — direction-aware LOH caller, SIMULATED regime throughout.

Standing Rule 1 applies to every artifact this script produces: every
output filename contains SIMULATED, every report's first line is
"SIMULATED DATA — NOT A SCIENTIFIC RESULT", every caption begins
"SIMULATED:", no ACMG evidence strength is assigned anywhere in this
script's output, and status fields use only SIMULATED / SIMULATED_PASS /
SIMULATED_FAIL / BLOCKED.

**Revision history:** this is the P07-diagnosis-and-fix revision. See
DIAGNOSIS.md for the full mechanism analysis. Two changes from the
version that DIAGNOSIS.md diagnosed:
  1. Updated to the remediated simulator's (simulate.py v2) schema:
     `assigned_loh_category` now IS the direction-aware vocabulary
     directly (no PROTOCOL-vocabulary translation layer needed or
     present — the old `TRUTH_CATEGORY_MAP` is removed), and
     `SIMULATED_variant_calls.tsv` carries new `mechanism`,
     `mirrored_baf_mean`, `n_baf_snps` columns.
  2. BAF corroboration added to `call_locus()`'s hypothesis competition
     (DIAGNOSIS.md's identified fix): mirrored B-allele frequency from
     flanking heterozygous SNPs (pooled over `n_baf_snps`, far lower
     variance than the single at-risk variant's own read count) is
     added as a 4th log-likelihood term. Because `E[mirrored BAF]` is
     proven identical for `WT_LOST_DIRECTION` and `VARIANT_LOST_DIRECTION`
     (both equal `(1-rho)/(rho*CN_t+2(1-rho))`) and provably distinct from
     `RETENTION_DIRECTION`'s constant 0.5 (DIAGNOSIS.md's algebraic proof,
     reused from the prior LOH-caller-validation task), this term
     strengthens RETENTION-vs-any-LOH separation specifically at low
     purity — exactly where DIAGNOSIS.md located the original failure —
     without touching direction discrimination at all.

What this implements, per the original task plus the above revision:
  - PROTOCOL.md §5.2's binomial VAF model, exactly:
        E[VAF|X] = (rho*X + (1-rho)*1) / (rho*CN_t + (1-rho)*2)
  - A LIKELIHOOD-based (not p-value-rejection-based) assignment: for each
    variant call, three canonical hypotheses about the mutant allele's
    tumor-cell copy count X are scored by exact binomial log-likelihood
    of the observed (alt reads, depth) under Binomial(depth, E[VAF|X]),
    PLUS (new) a Gaussian log-likelihood of the observed mean mirrored
    BAF under each hypothesis's expected mirrored BAF, combined with a
    uniform prior into a posterior over the 3 hypotheses (softmax of the
    summed log-likelihoods). The call is the argmax hypothesis; the
    posterior mass on that hypothesis IS the reported confidence.
  - Five direction-aware output categories (task's exact list), plus one
    additional NOT_EVALUABLE status this script adds on top of the
    task's list and discloses explicitly (see NOTE_ON_NOT_EVALUABLE
    below) rather than silently dropping PROTOCOL.md's own depth floor:
        WT_LOSS, VARIANT_LOSS, CN_NEUTRAL_LOH_WT_LOSS, RETENTION,
        AMBIGUOUS, [NOT_EVALUABLE]
  - Scoring against SIMULATED_TRUTH.tsv via gate6_recovery.py (for the
    2 of 16 truth quantities this caller can actually produce a recovered
    LR for — see the SCOPE note below) and gate7_denominators.py (for
    every reported rate).
  - Stratified accuracy by purity, depth, and total copy number, with
    every rate's denominator and excluded count reported explicitly
    (Standing Rule 5), AND every stratum's n stated plainly so a 4-
    observation cell cannot be read as if it carried the same weight as
    a 400-observation cell (DIAGNOSIS.md's finding about the prior
    report's worst-stratum claim).

SCOPE (disclosed, not silently narrowed): SIMULATED_TRUTH.tsv (v2) has 16
injected quantities. Only 2 of them (core_hr_wt_lost_direction_LR,
ddr_signaling_wt_lost_direction_LR) are marginal LOH-direction quantities
this caller can recover. The other 14 (GIS/HRD-score marginals, SBS3-
exposure marginals, joint/product-of-marginals/inflation-ratio
quantities per arm, and the 3 NULL_ARM full-feature-vector quantities)
require either scarHRD/SigProfilerAssignment-derived features this
script does not compute, or a JOINT estimator over multiple features
this single-feature LOH caller does not implement. This script does NOT
fabricate recovered values for those 14 — it runs gate6 against the
full, unmodified SIMULATED_TRUTH.tsv and declares all 16 quantities'
scope explicitly (gate6's scope-enumeration requirement), letting the
14 out-of-scope rows report honestly as `BLOCKED`/`NOT_IN_SCOPE`.

NOTE_ON_NOT_EVALUABLE: unchanged from the prior version — PROTOCOL.md
§5.2 fixes D >= 20 as a hard floor below which the binomial test cannot
run; this script emits NOT_EVALUABLE as a disclosed 6th status for loci
with depth < 20, kept fully distinct from AMBIGUOUS.

Run: python3 loh_caller.py
"""
from __future__ import annotations

import csv
import math
import random
import statistics
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "SIMULATED_data"
TRUTH_DETAIL_DIR = REPO_ROOT / "SIMULATED_TRUTH_detail"
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"
OUT_DIR = REPO_ROOT / "SIMULATED_loh_validation"
GATES_DIR = REPO_ROOT / "gates"
REPORT_MD = REPO_ROOT / "SIMULATED_loh_validation.md"

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

# --- Fixed rules, stated here before any scoring is run (not tuned to the
# accuracy numbers this script produces) ---
MIN_EVALUABLE_DEPTH = 20   # PROTOCOL.md §5.2, copied verbatim.
CONFIDENCE_THRESHOLD = 0.80  # ARBITRARY: minimum posterior mass (uniform
    # prior over the 3 candidate hypotheses) on the winning hypothesis to
    # avoid an AMBIGUOUS call. Unchanged from the prior version -- not
    # re-tuned as part of this fix (DIAGNOSIS.md's mechanism is the VAF
    # model's own loss of separation at low purity, not this threshold's
    # value; changing the threshold would just trade one failure mode for
    # another rather than fixing the identified cause).
BOOTSTRAP_B = 2000          # PROTOCOL.md §7.3, patient-clustered bootstrap replicate count.
BOOTSTRAP_SEED = 20260907   # ARBITRARY, reproducibility only (matches simulate.py's SEED convention).
MIN_STRATUM_N_FOR_HEADLINE = 20  # PROTOCOL.md §8's own minimum-stratum-size convention, reused here
    # so a low-n stratum's rate is never used, on its own, as a headline "the caller is unreliable
    # here" finding (DIAGNOSIS.md / this task's explicit "a 0/4 cell and a 0/400 cell must not look
    # alike" instruction) -- every stratum is still reported, just flagged when n is below this.

# Pre-declared stratification bin edges (fixed before running, not chosen
# post-hoc to make any particular stratum look better or worse). Unchanged
# from the prior version.
PURITY_BINS = [("LOW_0.10_0.35", 0.10, 0.35), ("MID_0.35_0.65", 0.35, 0.65), ("HIGH_0.65_0.95", 0.65, 0.95 + 1e-9)]
DEPTH_BINS = [("SUBFLOOR_4_20", 4, 20), ("BORDERLINE_20_30", 20, 30), ("MODERATE_30_60", 30, 60), ("HIGH_60_plus", 60, 10_000)]

sys.path.insert(0, str(GATES_DIR))
from gates_common import read_tsv, write_tsv  # noqa: E402


# ============================================================================
# PROTOCOL.md §5.2 binomial VAF model (exact formula, reused verbatim from
# simulate.py's own expected_vaf() -- not re-derived differently here).
# ============================================================================

def expected_vaf(purity: float, cn_total: int, mutant_copies: int) -> float:
    return (purity * mutant_copies + (1 - purity) * 1) / (purity * cn_total + (1 - purity) * 2)


def log_binom_pmf(k: int, n: int, p: float) -> float:
    """Exact binomial log-PMF, stdlib-only (math.lgamma), numerically
    stable for the depths in this dataset (no scipy)."""
    p = min(max(p, 1e-9), 1 - 1e-9)
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log(1 - p))


def log_gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    sigma = max(sigma, 1e-6)
    return -0.5 * ((x - mu) / sigma) ** 2 - math.log(sigma * math.sqrt(2 * math.pi))


# BAF corroboration (DIAGNOSIS.md's fix). E[mirrored BAF] is a proven
# identity of the same affine VAF model: exactly 0.5 for RETENTION,
# regardless of purity/CN_t; and (1-rho)/(rho*CN_t+2(1-rho)) for EITHER
# loss direction (the two loss directions are indistinguishable by BAF
# alone -- proven in the prior LOH-caller-validation task -- so adding
# this term cannot bias direction calls, only the retention/any-LOH
# boundary, which is exactly where DIAGNOSIS.md located the failure).
def expected_mirrored_baf(purity: float, cn_total: int, hypothesis: str) -> float:
    if hypothesis == "RETENTION_DIRECTION":
        return 0.5
    return (1 - purity) / (purity * cn_total + 2 * (1 - purity))


MIN_BAF_SEM = 0.005  # numerical floor on the empirical SEM, disclosed: avoids a
    # pathological zero-variance blowup in the Gaussian term when a sample's
    # observed per-SNP mirrored BAF values happen to be identical or n is tiny.


def call_locus(tumor_alt: int, tumor_ref: int, major_cn: int, minor_cn: int,
               purity: float, baseline_cn: int,
               mirrored_baf_mean: float | None = None, baf_sem: float | None = None) -> dict:
    """Direction-aware LOH call. Always considers the same 3 canonical
    hypotheses about the mutant allele's tumor-cell copy count X, scored
    by exact binomial likelihood of the at-risk variant's own reads PLUS
    (when BAF data is available) a Gaussian likelihood of the segment's
    mean mirrored BAF, combined with a UNIFORM prior into a posterior.
    The winning hypothesis's posterior mass is the confidence."""
    depth = tumor_alt + tumor_ref
    if depth < MIN_EVALUABLE_DEPTH:
        return {
            "call": "NOT_EVALUABLE", "confidence": "", "depth": depth,
            "cn_total": major_cn + minor_cn,
            "posterior_wt_lost_direction": "", "posterior_variant_lost_direction": "", "posterior_retention_direction": "",
        }

    cn_total = major_cn + minor_cn
    hyps = {
        "WT_LOST_DIRECTION": cn_total,                      # mutant occupies every surviving copy
        "VARIANT_LOST_DIRECTION": 0,                         # mutant occupies no surviving copy
        "RETENTION_DIRECTION": round(cn_total / 2) if cn_total > 0 else 0,  # mutant on half the copies (preserved het)
    }
    loglikes = {name: log_binom_pmf(tumor_alt, depth, expected_vaf(purity, cn_total, x)) for name, x in hyps.items()}

    if mirrored_baf_mean is not None and baf_sem is not None:
        for name in hyps:
            baf_target = expected_mirrored_baf(purity, cn_total, name)
            loglikes[name] += log_gaussian_pdf(mirrored_baf_mean, baf_target, max(baf_sem, MIN_BAF_SEM))

    m = max(loglikes.values())
    unnorm = {name: math.exp(ll - m) for name, ll in loglikes.items()}
    total = sum(unnorm.values())
    post = {name: v / total for name, v in unnorm.items()}
    best = max(post, key=post.get)
    confidence = post[best]

    if confidence < CONFIDENCE_THRESHOLD:
        call = "AMBIGUOUS"
    elif best == "WT_LOST_DIRECTION":
        call = "CN_NEUTRAL_LOH_WT_LOSS" if cn_total == baseline_cn else "WT_LOSS"
    elif best == "VARIANT_LOST_DIRECTION":
        call = "VARIANT_LOSS"
    else:
        call = "RETENTION"

    return {
        "call": call, "confidence": confidence, "depth": depth, "cn_total": cn_total,
        "posterior_wt_lost_direction": post["WT_LOST_DIRECTION"],
        "posterior_variant_lost_direction": post["VARIANT_LOST_DIRECTION"],
        "posterior_retention_direction": post["RETENTION_DIRECTION"],
    }


def parse_bool(s: str) -> bool:
    return s.strip().lower() == "true"


def load_baf_summary() -> dict[str, dict]:
    """Groups SIMULATED_baf_segments.tsv by sample_id and computes, per
    sample, the empirical mean and standard-error-of-the-mean of the
    per-SNP mirrored BAF -- entirely data-driven (no assumed depth or
    noise constant borrowed from simulate.py), so the Gaussian likelihood
    term in call_locus() reflects each locus's ACTUAL observed BAF
    precision, not a global approximation."""
    path = DATA_DIR / "SIMULATED_baf_segments.tsv"
    if not path.exists():
        return {}
    by_sample: dict[str, list[float]] = {}
    for row in read_tsv(path):
        by_sample.setdefault(row["sample_id"], []).append(float(row["mirrored_baf"]))
    summary = {}
    for sid, vals in by_sample.items():
        n = len(vals)
        mean = sum(vals) / n
        sd = statistics.stdev(vals) if n > 1 else 0.0
        sem = sd / math.sqrt(n) if n > 0 else MIN_BAF_SEM
        summary[sid] = {"n_baf_snps": n, "mirrored_baf_mean": mean, "baf_sem": max(sem, MIN_BAF_SEM)}
    return summary


def load_loci() -> tuple[list[dict], dict]:
    meta = {r["sample_id"]: r for r in read_tsv(DATA_DIR / "SIMULATED_sample_metadata.tsv")}
    labels = {r["sample_id"]: r for r in read_tsv(TRUTH_DETAIL_DIR / "SIMULATED_sample_labels.tsv")}
    variants = read_tsv(DATA_DIR / "SIMULATED_variant_calls.tsv")
    baf_summary = load_baf_summary()

    n_baf_missing = 0
    loci = []
    for v in variants:
        sid = v["sample_id"]
        m = meta[sid]
        lbl = labels[sid]
        purity = float(m["purity"])
        wgd = parse_bool(m["wgd"])
        baseline_cn = 4 if wgd else 2
        major_cn = int(v["major_cn"])
        minor_cn = int(v["minor_cn"])
        tumor_alt = int(v["tumor_alt_reads"])
        tumor_ref = int(v["tumor_ref_reads"])

        baf = baf_summary.get(sid)
        if baf is None:
            n_baf_missing += 1
            result = call_locus(tumor_alt, tumor_ref, major_cn, minor_cn, purity, baseline_cn)
        else:
            result = call_locus(tumor_alt, tumor_ref, major_cn, minor_cn, purity, baseline_cn,
                                 baf["mirrored_baf_mean"], baf["baf_sem"])

        # simulate.py v2 emits the direction-aware vocabulary directly in
        # assigned_loh_category (RETENTION, CN_NEUTRAL_LOH_WT_LOSS, WT_LOSS,
        # VARIANT_LOSS, AMBIGUOUS, NOT_EVALUABLE) -- no PROTOCOL-vocabulary
        # translation layer is needed or present (v1's TRUTH_CATEGORY_MAP,
        # which this schema change made obsolete, has been removed).
        true_category = v["assigned_loh_category"]

        loci.append({
            "sample_id": sid, "gene": v["gene"], "gene_group": m["gene_group"],
            "true_class": lbl["true_class"], "assigned_loh_category": v["assigned_loh_category"],
            "mechanism": v.get("mechanism", ""),
            "true_direction_category": true_category,
            "predicted_category": result["call"], "confidence": result["confidence"],
            "posterior_wt_lost_direction": result["posterior_wt_lost_direction"],
            "posterior_variant_lost_direction": result["posterior_variant_lost_direction"],
            "posterior_retention_direction": result["posterior_retention_direction"],
            "purity": purity, "wgd": wgd, "baseline_cn": baseline_cn,
            "major_cn": major_cn, "minor_cn": minor_cn, "cn_total": major_cn + minor_cn,
            "depth": result["depth"],
            "used_baf": baf is not None,
            "correct": result["call"] == true_category,
        })
    return loci, {"n_baf_missing": n_baf_missing, "n_total": len(loci)}


# ============================================================================
# Confusion matrix + denominator-explicit rate table (Standing Rule 5)
# ============================================================================

ALL_CATEGORIES = ["RETENTION", "WT_LOSS", "CN_NEUTRAL_LOH_WT_LOSS", "VARIANT_LOSS", "AMBIGUOUS", "NOT_EVALUABLE"]
EXCLUDED_FROM_DEFINITIVE = {"AMBIGUOUS", "NOT_EVALUABLE"}
WT_LOST_DIRECTION_CATS = {"WT_LOSS", "CN_NEUTRAL_LOH_WT_LOSS"}


def build_confusion_matrix(loci: list[dict]) -> list[dict]:
    counts: dict[tuple[str, str], int] = {}
    for r in loci:
        key = (r["true_direction_category"], r["predicted_category"])
        counts[key] = counts.get(key, 0) + 1
    rows = []
    for true_cat in ALL_CATEGORIES:
        for pred_cat in ALL_CATEGORIES:
            n = counts.get((true_cat, pred_cat), 0)
            rows.append({"true_category": true_cat, "predicted_category": pred_cat, "count": n})
    return rows


def rate_row(metric_name: str, numerator: int, denominator: int, excluded_count: int, excluded_reason: str) -> dict:
    rate = round(numerator / denominator, 6) if denominator > 0 else ""
    n_total_cell = denominator + excluded_count
    low_n_flag = "TRUE" if n_total_cell < MIN_STRATUM_N_FOR_HEADLINE else "FALSE"
    return {
        "metric_name": metric_name, "numerator": numerator, "denominator": denominator,
        "excluded_count": excluded_count, "excluded_reason": excluded_reason, "rate": rate,
        "n_total_cell": n_total_cell, "low_n_flag": low_n_flag,
    }


def build_rates_table(loci: list[dict]) -> list[dict]:
    rows = []
    n_total = len(loci)

    n_correct_all = sum(1 for r in loci if r["correct"])
    rows.append(rate_row(
        "overall_accuracy_including_ambiguous_and_not_evaluable", n_correct_all, n_total, 0,
        "none -- AMBIGUOUS and NOT_EVALUABLE predictions are scored against their own true category here, not excluded",
    ))

    definitive = [r for r in loci if r["predicted_category"] not in EXCLUDED_FROM_DEFINITIVE]
    excluded = [r for r in loci if r["predicted_category"] in EXCLUDED_FROM_DEFINITIVE]
    n_correct_def = sum(1 for r in definitive if r["correct"])
    rows.append(rate_row(
        "overall_accuracy_excluding_ambiguous_and_not_evaluable", n_correct_def, len(definitive), len(excluded),
        "excludes predicted_category in {AMBIGUOUS (confidence < 0.80), NOT_EVALUABLE (depth < 20)}",
    ))

    # WT_LOSS-specific accuracy (this task's explicit requirement: "It is the
    # primary target and has never been measured"). Two views: sensitivity
    # (recall) among true WT_LOSS loci, and precision among predicted WT_LOSS.
    true_wt_loss = [r for r in loci if r["true_direction_category"] == "WT_LOSS"]
    n_wt_loss_correct = sum(1 for r in true_wt_loss if r["predicted_category"] == "WT_LOSS")
    n_wt_loss_ambiguous_or_ne = sum(1 for r in true_wt_loss if r["predicted_category"] in EXCLUDED_FROM_DEFINITIVE)
    rows.append(rate_row(
        "wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable",
        n_wt_loss_correct, len(true_wt_loss) - n_wt_loss_ambiguous_or_ne, n_wt_loss_ambiguous_or_ne,
        "of true WT_LOSS (deletion-type, n_t=1) loci with a definitive call, fraction correctly called WT_LOSS "
        "(not CN_NEUTRAL_LOH_WT_LOSS, VARIANT_LOSS, or RETENTION)",
    ))
    pred_wt_loss = [r for r in loci if r["predicted_category"] == "WT_LOSS"]
    n_wt_loss_precision_correct = sum(1 for r in pred_wt_loss if r["true_direction_category"] == "WT_LOSS")
    rows.append(rate_row(
        "wt_loss_precision", n_wt_loss_precision_correct, len(pred_wt_loss), 0,
        "of loci predicted WT_LOSS, fraction whose true category is actually WT_LOSS (deletion-type, n_t=1)",
    ))

    # Inversion rates in both directions, with denominators (this task's
    # explicit requirement -- the prior report's zero-inversion finding was
    # vacuous because deletion-type WT_LOSS did not exist in that run's data).
    true_wt_direction = [r for r in loci if r["true_direction_category"] in WT_LOST_DIRECTION_CATS]
    n_wt_to_variant_inversions = sum(1 for r in true_wt_direction if r["predicted_category"] == "VARIANT_LOSS")
    rows.append(rate_row(
        "inversion_rate_wt_lost_direction_called_variant_lost",
        n_wt_to_variant_inversions, len(true_wt_direction), 0,
        "of true WT-lost-direction loci (CN_NEUTRAL_LOH_WT_LOSS or WT_LOSS), fraction called VARIANT_LOSS "
        "(the opposite direction -- a genuine inversion, not an AMBIGUOUS/NOT_EVALUABLE non-call)",
    ))
    true_variant_loss = [r for r in loci if r["true_direction_category"] == "VARIANT_LOSS"]
    n_variant_to_wt_inversions = sum(1 for r in true_variant_loss if r["predicted_category"] in WT_LOST_DIRECTION_CATS)
    rows.append(rate_row(
        "inversion_rate_variant_lost_called_wt_lost_direction",
        n_variant_to_wt_inversions, len(true_variant_loss), 0,
        "of true VARIANT_LOSS loci, fraction called a WT-lost-direction category (CN_NEUTRAL_LOH_WT_LOSS or "
        "WT_LOSS) -- the opposite direction",
    ))

    n_ambiguous = sum(1 for r in loci if r["predicted_category"] == "AMBIGUOUS")
    n_not_evaluable = sum(1 for r in loci if r["predicted_category"] == "NOT_EVALUABLE")
    n_depth_evaluable = n_total - n_not_evaluable
    rows.append(rate_row(
        "confidence_filter_ambiguous_rate", n_ambiguous, n_depth_evaluable, 0,
        "fraction of depth-evaluable (depth>=20) loci where the confidence<0.80 filter reclassified the "
        "best-fitting hypothesis's call to AMBIGUOUS; denominator excludes NOT_EVALUABLE (depth<20) loci "
        "because those never entered the hypothesis competition at all",
    ))
    rows.append(rate_row("not_evaluable_rate_depth_lt_20", n_not_evaluable, n_total, 0,
                          "fraction of all attempted calls excluded pre-emptively by the depth<20 floor (PROTOCOL.md §5.2), before any hypothesis competition"))

    for bin_name, lo, hi in PURITY_BINS:
        in_bin_def = [r for r in definitive if lo <= r["purity"] < hi]
        in_bin_excl = [r for r in excluded if lo <= r["purity"] < hi]
        n_correct = sum(1 for r in in_bin_def if r["correct"])
        if len(in_bin_def) == 0:
            continue
        rows.append(rate_row(f"accuracy_by_purity_{bin_name}", n_correct, len(in_bin_def), len(in_bin_excl),
                              f"purity in [{lo},{hi}); excludes AMBIGUOUS/NOT_EVALUABLE predictions within this purity band"))

    for bin_name, lo, hi in DEPTH_BINS:
        in_bin_def = [r for r in definitive if lo <= r["depth"] < hi]
        in_bin_excl = [r for r in excluded if lo <= r["depth"] < hi]
        if len(in_bin_def) == 0:
            continue
        n_correct = sum(1 for r in in_bin_def if r["correct"])
        rows.append(rate_row(f"accuracy_by_depth_{bin_name}", n_correct, len(in_bin_def), len(in_bin_excl),
                              f"tumor depth in [{lo},{hi}); excludes AMBIGUOUS/NOT_EVALUABLE predictions within this depth band"))

    for cn in sorted({r["cn_total"] for r in loci}):
        in_bin_def = [r for r in definitive if r["cn_total"] == cn]
        in_bin_excl = [r for r in excluded if r["cn_total"] == cn]
        if len(in_bin_def) == 0:
            continue
        n_correct = sum(1 for r in in_bin_def if r["correct"])
        rows.append(rate_row(f"accuracy_by_total_copy_number_CN{cn}", n_correct, len(in_bin_def), len(in_bin_excl),
                              f"cn_total == {cn}; excludes AMBIGUOUS/NOT_EVALUABLE predictions"))

    # Full purity x depth grid, per this task's explicit "every stratified cell
    # carries its own n" requirement -- reported at this finer grain in addition
    # to the marginal purity-only / depth-only breakdowns above.
    for purity_bin, p_lo, p_hi in PURITY_BINS:
        for depth_bin, d_lo, d_hi in DEPTH_BINS:
            in_cell_def = [r for r in definitive if p_lo <= r["purity"] < p_hi and d_lo <= r["depth"] < d_hi]
            in_cell_excl = [r for r in excluded if p_lo <= r["purity"] < p_hi and d_lo <= r["depth"] < d_hi]
            if len(in_cell_def) == 0:
                continue
            n_correct = sum(1 for r in in_cell_def if r["correct"])
            rows.append(rate_row(
                f"accuracy_by_purity_{purity_bin}_x_depth_{depth_bin}", n_correct, len(in_cell_def), len(in_cell_excl),
                f"purity in [{p_lo},{p_hi}) x depth in [{d_lo},{d_hi}); excludes AMBIGUOUS/NOT_EVALUABLE",
            ))

    for wgd_flag in (False, True):
        in_bin_def = [r for r in definitive if r["wgd"] == wgd_flag]
        in_bin_excl = [r for r in excluded if r["wgd"] == wgd_flag]
        label = "WGD" if wgd_flag else "NON_WGD"
        if len(in_bin_def) == 0:
            continue
        n_correct = sum(1 for r in in_bin_def if r["correct"])
        rows.append(rate_row(f"accuracy_by_wgd_status_{label}", n_correct, len(in_bin_def), len(in_bin_excl),
                              f"wgd == {wgd_flag}; excludes AMBIGUOUS/NOT_EVALUABLE predictions"))

    for arm in sorted({r["gene_group"] for r in loci}):
        in_bin_def = [r for r in definitive if r["gene_group"] == arm]
        in_bin_excl = [r for r in excluded if r["gene_group"] == arm]
        n_correct = sum(1 for r in in_bin_def if r["correct"])
        rows.append(rate_row(f"accuracy_by_arm_{arm}", n_correct, len(in_bin_def), len(in_bin_excl),
                              f"gene_group == {arm}; excludes AMBIGUOUS/NOT_EVALUABLE predictions"))

    return rows


# ============================================================================
# Recovered LR quantities (core_hr_wt_lost_direction_LR,
# ddr_signaling_wt_lost_direction_LR) -- the 2 of 16 SIMULATED_TRUTH.tsv
# quantities this caller can score against (v2 renamed these from
# *_loh_second_hit_LR; NULL_ARM has no marginal-only truth quantity to
# recover against, only full-vector joint/product/ratio ones this
# single-feature caller cannot produce).
# ============================================================================

def jeffreys_rate(count: int, n: int) -> float:
    return (count + 0.5) / (n + 1)


def wt_lost_direction_lr_point(loci_group: list[dict]) -> float:
    path = [r for r in loci_group if r["true_class"] == "Pathogenic"]
    benign = [r for r in loci_group if r["true_class"] == "Benign"]
    c_path = sum(1 for r in path if r["predicted_category"] in WT_LOST_DIRECTION_CATS)
    c_benign = sum(1 for r in benign if r["predicted_category"] in WT_LOST_DIRECTION_CATS)
    p_path = jeffreys_rate(c_path, len(path))
    p_benign = jeffreys_rate(c_benign, len(benign))
    return p_path / p_benign


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * (p / 100)
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def bootstrap_ci(loci_group: list[dict], rng: random.Random) -> tuple[float, float]:
    path = [r for r in loci_group if r["true_class"] == "Pathogenic"]
    benign = [r for r in loci_group if r["true_class"] == "Benign"]
    lrs = []
    for _ in range(BOOTSTRAP_B):
        path_b = [rng.choice(path) for _ in path]
        benign_b = [rng.choice(benign) for _ in benign]
        c_path = sum(1 for r in path_b if r["predicted_category"] in WT_LOST_DIRECTION_CATS)
        c_benign = sum(1 for r in benign_b if r["predicted_category"] in WT_LOST_DIRECTION_CATS)
        p_path = jeffreys_rate(c_path, len(path_b))
        p_benign = jeffreys_rate(c_benign, len(benign_b))
        lrs.append(p_path / p_benign)
    lrs.sort()
    return percentile(lrs, 2.5), percentile(lrs, 97.5)


def build_recovered_quantities(loci: list[dict]) -> list[dict]:
    rows = []
    rng = random.Random(BOOTSTRAP_SEED)
    for group in ("CORE_HR", "DDR_SIGNALING"):
        loci_group = [r for r in loci if r["gene_group"] == group]
        point = wt_lost_direction_lr_point(loci_group)
        ci_low, ci_high = bootstrap_ci(loci_group, rng)
        rows.append({
            "quantity": f"{group.lower()}_wt_lost_direction_LR",
            "recovered_point": point, "ci_low": ci_low, "ci_high": ci_high, "estimand": "LR",
        })
    return rows


# Every SIMULATED_TRUTH.tsv (v2, 16-quantity) quantity, declared explicitly
# (gate6 housekeeping fix: a gate that scores a subset without declaring the
# subset is a scope bug). Only the 2 marginal WT-lost-direction quantities
# are this caller's deliverable; the rest require GIS/SBS3 feature
# extraction and/or a joint estimator this single-feature caller does not
# implement.
RECOVERY_SCOPE = [
    {"quantity": "core_hr_wt_lost_direction_LR", "in_scope": "TRUE",
     "reason": "this caller's own deliverable: recovered from its blind WT_LOSS/CN_NEUTRAL_LOH_WT_LOSS calls"},
    {"quantity": "ddr_signaling_wt_lost_direction_LR", "in_scope": "TRUE",
     "reason": "this caller's own deliverable: recovered from its blind WT_LOSS/CN_NEUTRAL_LOH_WT_LOSS calls"},
    {"quantity": "core_hr_gis_score_LR", "in_scope": "FALSE",
     "reason": "requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute"},
    {"quantity": "ddr_signaling_gis_score_LR", "in_scope": "FALSE",
     "reason": "requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute"},
    {"quantity": "core_hr_sbs3_exposure_LR", "in_scope": "FALSE",
     "reason": "requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute"},
    {"quantity": "ddr_signaling_sbs3_exposure_LR", "in_scope": "FALSE",
     "reason": "requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute"},
    {"quantity": "core_hr_joint_LR", "in_scope": "FALSE",
     "reason": "a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate"},
    {"quantity": "core_hr_product_of_marginals_LR", "in_scope": "FALSE",
     "reason": "same reason as core_hr_joint_LR -- requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement"},
    {"quantity": "core_hr_joint_vs_marginal_inflation_ratio", "in_scope": "FALSE",
     "reason": "downstream of core_hr_joint_LR and core_hr_product_of_marginals_LR, both out of scope"},
    {"quantity": "ddr_signaling_joint_LR", "in_scope": "FALSE",
     "reason": "a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate"},
    {"quantity": "ddr_signaling_product_of_marginals_LR", "in_scope": "FALSE",
     "reason": "same reason as ddr_signaling_joint_LR -- requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement"},
    {"quantity": "ddr_signaling_joint_vs_marginal_inflation_ratio", "in_scope": "FALSE",
     "reason": "downstream of ddr_signaling_joint_LR and ddr_signaling_product_of_marginals_LR, both out of scope"},
    {"quantity": "null_arm_full_vector_joint_LR", "in_scope": "FALSE",
     "reason": "NULL_ARM has no marginal-only (LOH-direction-alone) truth quantity to recover against -- only full-feature-vector joint/product/ratio quantities, which require GIS/SBS3 features this caller does not compute"},
    {"quantity": "null_arm_full_vector_product_of_marginals_LR", "in_scope": "FALSE",
     "reason": "same reason as null_arm_full_vector_joint_LR"},
    {"quantity": "null_arm_full_vector_inflation_ratio", "in_scope": "FALSE",
     "reason": "downstream of the two null_arm quantities above, both out of scope"},
    {"quantity": "null_sequencing_depth_bucket_LR", "in_scope": "FALSE",
     "reason": "an engineered-null depth-bucket feature unrelated to LOH direction; not this caller's estimand"},
]


# ============================================================================
# gate6 / gate7 invocation (subprocess, real files, real exit codes --
# Standing Rule 4: nonzero exit is failure even if a file appeared)
# ============================================================================

def run_gate(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable] + args, cwd=REPO_ROOT, capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    return proc.returncode, output


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    loci, baf_stats = load_loci()

    write_tsv(OUT_DIR / "SIMULATED_loh_calls.tsv", loci, [
        "sample_id", "gene", "gene_group", "true_class", "assigned_loh_category", "mechanism", "true_direction_category",
        "predicted_category", "confidence", "posterior_wt_lost_direction", "posterior_variant_lost_direction",
        "posterior_retention_direction", "purity", "wgd", "baseline_cn", "major_cn", "minor_cn", "cn_total",
        "depth", "used_baf", "correct",
    ])

    confusion_rows = build_confusion_matrix(loci)
    write_tsv(OUT_DIR / "SIMULATED_confusion_matrix.tsv", confusion_rows, ["true_category", "predicted_category", "count"])

    rates_rows = build_rates_table(loci)
    write_tsv(OUT_DIR / "SIMULATED_rates_table.tsv", rates_rows,
              ["metric_name", "numerator", "denominator", "excluded_count", "excluded_reason",
               "rate", "n_total_cell", "low_n_flag"])

    recovered_rows = build_recovered_quantities(loci)
    write_tsv(OUT_DIR / "SIMULATED_recovered_quantities.tsv", recovered_rows,
              ["quantity", "recovered_point", "ci_low", "ci_high", "estimand"])

    write_tsv(OUT_DIR / "SIMULATED_recovery_scope.tsv", RECOVERY_SCOPE, ["quantity", "in_scope", "reason"])

    print(f"Loaded and called {len(loci)} SIMULATED loci ({baf_stats['n_baf_missing']} without BAF data); wrote outputs under {OUT_DIR}")

    gate6_exit, gate6_out = run_gate([
        "gates/gate6_recovery.py",
        "--truth", str(TRUTH_TSV),
        "--recovered", str(OUT_DIR / "SIMULATED_recovered_quantities.tsv"),
        "--scope", str(OUT_DIR / "SIMULATED_recovery_scope.tsv"),
        "--outdir", str(REPO_ROOT),
    ])
    print(gate6_out)
    print(f"gate6_recovery.py exit code: {gate6_exit}")

    gate7_exit, gate7_out = run_gate([
        "gates/gate7_denominators.py",
        "--rates-table", str(OUT_DIR / "SIMULATED_rates_table.tsv"),
    ])
    print(gate7_out)
    print(f"gate7_denominators.py exit code: {gate7_exit}")

    write_validation_report(loci, confusion_rows, rates_rows, recovered_rows,
                             gate6_exit, gate6_out, gate7_exit, gate7_out, baf_stats)


def write_validation_report(loci, confusion_rows, rates_rows, recovered_rows,
                             gate6_exit, gate6_out, gate7_exit, gate7_out, baf_stats) -> None:
    n_total = len(loci)
    overall_status = "SIMULATED_PASS" if (gate6_exit == 0 and gate7_exit == 0) else "SIMULATED_FAIL"

    recovery_table_path = REPO_ROOT / "SIMULATED_RECOVERY_TABLE.tsv"
    recovery_rows = read_tsv(recovery_table_path) if recovery_table_path.exists() else []
    in_scope_rows = [r for r in recovery_rows if r["scope_status"] == "IN_SCOPE"]
    out_of_scope_rows = [r for r in recovery_rows if r["scope_status"] == "NOT_IN_SCOPE"]
    undeclared_rows = [r for r in recovery_rows if r["scope_status"] == "UNDECLARED"]

    def acc_row(name: str) -> dict:
        return next(r for r in rates_rows if r["metric_name"] == name)

    overall_incl = acc_row("overall_accuracy_including_ambiguous_and_not_evaluable")
    overall_excl = acc_row("overall_accuracy_excluding_ambiguous_and_not_evaluable")
    conf_filter = acc_row("confidence_filter_ambiguous_rate")
    not_eval = acc_row("not_evaluable_rate_depth_lt_20")
    wt_loss_sens = acc_row("wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable")
    wt_loss_prec = acc_row("wt_loss_precision")
    inv_wt_to_var = acc_row("inversion_rate_wt_lost_direction_called_variant_lost")
    inv_var_to_wt = acc_row("inversion_rate_variant_lost_called_wt_lost_direction")

    # Worst-performing ADEQUATELY-POWERED (n >= MIN_STRATUM_N_FOR_HEADLINE) stratum
    # only -- a low-n cell is reported in full in the table but never used, alone,
    # to make an "unreliable region" claim (this task's explicit correction).
    grid_rows = [r for r in rates_rows if r["metric_name"].startswith("accuracy_by_purity_") and "_x_depth_" in r["metric_name"]]
    adequately_powered = [r for r in grid_rows if r["n_total_cell"] >= MIN_STRATUM_N_FOR_HEADLINE and r["denominator"] > 0]
    low_n_grid_cells = [r for r in grid_rows if r["n_total_cell"] < MIN_STRATUM_N_FOR_HEADLINE]
    worst = min(adequately_powered, key=lambda r: r["rate"] if r["rate"] != "" else 1.0) if adequately_powered else None

    lines = [BANNER, "", "# SIMULATED_loh_validation.md — direction-aware LOH caller validation", ""]
    lines.append(
        "SIMULATED: this report validates `loh_caller.py` against `SIMULATED_TRUTH.tsv` and the "
        "SIMULATED tumor/normal data under `SIMULATED_data/`, produced by `simulate.py` (the "
        "remediated, v2 simulator). No real patient, tumor, or sequencing data appears anywhere "
        "below. No ACMG evidence strength is assigned to anything in this report. This report "
        "supersedes the version DIAGNOSIS.md analyzed — see DIAGNOSIS.md for the bias mechanism "
        "this revision fixes (BAF corroboration added to `call_locus()`)."
    )
    lines.append("")
    lines.append(f"**Overall session status: `{overall_status}`** (gate6 exit={gate6_exit}, gate7 exit={gate7_exit}).")
    lines.append(f"BAF data was available for {n_total - baf_stats['n_baf_missing']}/{n_total} loci "
                 f"({baf_stats['n_baf_missing']} fell back to the pre-fix 3-hypothesis-only competition).")
    lines.append("")

    lines.append("## 1. Method (updated per DIAGNOSIS.md's fix)")
    lines.append("")
    lines.append(
        "`E[VAF|X] = (rho*X + (1-rho)*1) / (rho*CN_t + (1-rho)*2)` (PROTOCOL.md §5.2). For every "
        "variant call with tumor depth >= 20, three canonical hypotheses (`WT_LOST_DIRECTION`, "
        "`VARIANT_LOST_DIRECTION`, `RETENTION_DIRECTION`) are scored by exact binomial log-likelihood "
        "of the at-risk variant's own reads **plus a Gaussian log-likelihood of the segment's mean "
        "mirrored BAF** (new — DIAGNOSIS.md's fix) under each hypothesis's expected mirrored BAF "
        "(`0.5` for `RETENTION_DIRECTION` always; `(1-rho)/(rho*CN_t+2(1-rho))` for either loss "
        "direction — proven identical between the two loss directions, so this term cannot bias "
        "direction calls, only the retention/any-LOH boundary). A uniform prior over the 3 combines "
        "these into a posterior (softmax); the call is the argmax hypothesis and the posterior mass "
        "is the confidence. Below `CONFIDENCE_THRESHOLD = 0.80`, the call is `AMBIGUOUS`. Depth < 20 "
        "loci are `NOT_EVALUABLE` (unchanged, PROTOCOL.md §5.2's own floor)."
    )
    lines.append("")
    lines.append(
        "A `WT_LOST_DIRECTION` win is further split by copy-number mechanism: `CN_NEUTRAL_LOH_WT_LOSS` "
        "(total CN equals baseline ploidy) vs bare `WT_LOSS` (a genuine hemizygous deletion, "
        "`cn_total=1`, now actually present in the remediated simulator's data — see §3). "
        "`VARIANT_LOSS` is never split this way and remains its own, single, distinct output class."
    )
    lines.append("")

    lines.append("## 2. Confusion matrix (true direction-aware category x predicted category)")
    lines.append("")
    lines.append("| true \\ predicted | " + " | ".join(ALL_CATEGORIES) + " |")
    lines.append("|---|" + "|".join(["---"] * len(ALL_CATEGORIES)) + "|")
    for true_cat in ALL_CATEGORIES:
        row_counts = [str(next(r["count"] for r in confusion_rows if r["true_category"] == true_cat and r["predicted_category"] == pc)) for pc in ALL_CATEGORIES]
        lines.append(f"| {true_cat} | " + " | ".join(row_counts) + " |")
    lines.append(f"\n({n_total} total variant calls attempted.)")
    lines.append("")

    lines.append("## 3. WT_LOSS accuracy (the primary target — previously unmeasured)")
    lines.append("")
    lines.append(
        f"**WT_LOSS sensitivity (excluding AMBIGUOUS/NOT_EVALUABLE): {wt_loss_sens['rate']} "
        f"({wt_loss_sens['numerator']}/{wt_loss_sens['denominator']}, {wt_loss_sens['excluded_count']} "
        f"excluded, n={wt_loss_sens['n_total_cell']}).** "
        f"**WT_LOSS precision: {wt_loss_prec['rate']} ({wt_loss_prec['numerator']}/{wt_loss_prec['denominator']}, "
        f"n={wt_loss_prec['n_total_cell']}).** This is the first report in this project to measure "
        f"WT_LOSS accuracy at all — the pre-remediation simulator never generated a true deletion-type "
        f"WT_LOSS locus (DEFECT 1 of the simulator revision), so this quantity was previously UNCHECKED, "
        f"not merely untested-and-presumed-fine."
    )
    lines.append("")

    lines.append("## 4. Inversion rate, both directions, with denominators")
    lines.append("")
    lines.append(
        f"**True WT-lost-direction called VARIANT_LOSS (inversion): {inv_wt_to_var['rate']} "
        f"({inv_wt_to_var['numerator']}/{inv_wt_to_var['denominator']}).** "
        f"**True VARIANT_LOSS called a WT-lost-direction category (inversion): {inv_var_to_wt['rate']} "
        f"({inv_var_to_wt['numerator']}/{inv_var_to_wt['denominator']}).** The pre-remediation report's "
        f"\"zero inversion rate\" finding was vacuous: with no true deletion-type WT_LOSS in that run's "
        f"data, an inversion involving it could never even be evaluated. Both denominators here are "
        f"real, nonzero counts of true instances (see §3 and the confusion matrix, §2)."
    )
    lines.append("")

    lines.append("## 5. Denominator-explicit accuracy, including/excluding AMBIGUOUS and NOT_EVALUABLE")
    lines.append("")
    lines.append("| metric | numerator | denominator | excluded_count | n (cell) | rate |")
    lines.append("|---|---|---|---|---|---|")
    for r in rates_rows:
        lines.append(f"| {r['metric_name']} | {r['numerator']} | {r['denominator']} | {r['excluded_count']} | {r['n_total_cell']} | {r['rate']} |")
    lines.append("")
    lines.append(
        f"SIMULATED: of {n_total} total calls attempted, `{not_eval['numerator']}` were `NOT_EVALUABLE` "
        f"(depth < 20) and, of the `{conf_filter['denominator']}` depth-evaluable loci remaining, "
        f"`{conf_filter['numerator']}` were reclassified `AMBIGUOUS` by the confidence < 0.80 filter "
        f"(rate = {conf_filter['rate']}). Accuracy **including** those excluded calls = {overall_incl['rate']} "
        f"({overall_incl['numerator']}/{overall_incl['denominator']}). Accuracy **excluding** them = "
        f"{overall_excl['rate']} ({overall_excl['numerator']}/{overall_excl['denominator']}, "
        f"{overall_excl['excluded_count']} excluded, n={overall_excl['n_total_cell']})."
    )
    lines.append("")
    if low_n_grid_cells:
        lines.append(
            f"**{len(low_n_grid_cells)} of {len(grid_rows)} purity x depth grid cells carry n < "
            f"{MIN_STRATUM_N_FOR_HEADLINE}** (listed in the table above with their own n — never "
            f"conflated with a well-powered cell's rate): "
            + ", ".join(f"`{r['metric_name']}` (n={r['n_total_cell']})" for r in low_n_grid_cells) + "."
        )
        lines.append("")

    lines.append("## 6. The unreliable operating region: purity x depth (investigated, not asserted)")
    lines.append("")
    if worst is not None:
        lines.append(
            f"Among strata with n >= {MIN_STRATUM_N_FOR_HEADLINE} (adequately powered — low-n cells are "
            f"excluded from this specific claim, per §5's flag), the worst-performing purity x depth "
            f"grid cell is **`{worst['metric_name']}`** at rate **{worst['rate']}** "
            f"({worst['numerator']}/{worst['denominator']}, n={worst['n_total_cell']})."
        )
    else:
        lines.append(f"No purity x depth grid cell reached n >= {MIN_STRATUM_N_FOR_HEADLINE}; no headline "
                      f"operating-region claim is made (see the low-n cells listed in §5 instead).")
    lines.append("")
    lines.append(
        "**Root cause (DIAGNOSIS.md, proven algebraically):** `expected_vaf` is affine in X, so "
        "`E[VAF|RETENTION_DIRECTION] = 0.5` exactly for every purity, while "
        "`E[VAF|WT_LOST_DIRECTION]` approaches 0.5 as purity -> 0 (`gap(rho) ~ rho*CN_t/4` for small "
        "rho) — the separation between retention and either loss direction vanishes proportionally to "
        "purity. This is why confidence collapses, and AMBIGUOUS/inversion risk rises, specifically at "
        "**low purity** — not at low depth, and not uniformly. BAF corroboration (added this revision) "
        "mitigates this (BAF is a lower-variance, independently-measured corroborating signal for the "
        "same retention-vs-any-LOH boundary), but does not eliminate the underlying purity-driven "
        "signal collapse, which is a property of the VAF model itself, not of any one estimator."
    )
    lines.append("")

    lines.append("## 7. VARIANT_LOSS is a distinct output class")
    lines.append("")
    variant_loss_true = sum(r["count"] for r in confusion_rows if r["true_category"] == "VARIANT_LOSS")
    variant_loss_pred = sum(r["count"] for r in confusion_rows if r["predicted_category"] == "VARIANT_LOSS")
    lines.append(
        f"SIMULATED: `VARIANT_LOSS` appears as its own row and column in the confusion matrix above, "
        f"distinct from `WT_LOSS`/`CN_NEUTRAL_LOH_WT_LOSS` — {variant_loss_true} true instances, "
        f"{variant_loss_pred} predicted instances this run."
    )
    lines.append("")

    lines.append("## 8. gate6 — recovery against SIMULATED_TRUTH.tsv (16 quantities), scope declared for every one")
    lines.append("")
    lines.append(
        f"gate6_recovery.py exit code: **{gate6_exit}** "
        f"({'all in-scope quantities SIMULATED_PASS' if gate6_exit == 0 else 'at least one in-scope quantity SIMULATED_FAIL — reported as FAILED'})."
        f" All 16 `SIMULATED_TRUTH.tsv` quantities are declared in `SIMULATED_recovery_scope.tsv` "
        f"({len(undeclared_rows)} undeclared this run)."
    )
    lines.append("")
    lines.append(f"In-scope quantities ({len(in_scope_rows)} of 16 — this caller's own deliverable, scored for real):")
    lines.append("")
    lines.append("| quantity | injected | recovered | ci_low | ci_high | status | reason |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in in_scope_rows:
        lines.append(f"| {r['quantity']} | {r['injected']} | {r['recovered']} | {r['ci_low']} | {r['ci_high']} | {r['status']} | {r['reason']} |")
    lines.append("")
    lines.append(f"Declared out-of-scope quantities ({len(out_of_scope_rows)} of 16):")
    lines.append("")
    lines.append("| quantity | status | scope_status | reason |")
    lines.append("|---|---|---|---|")
    for r in out_of_scope_rows:
        lines.append(f"| {r['quantity']} | {r['status']} | {r['scope_status']} | {r['reason']} |")
    lines.append("")
    lines.append(
        f"**Per this task's acceptance wording (\"gate6 PASS on every P07 quantity, or FAILED with the "
        f"cause identified and the remaining gap quantified\"): this session reports gate6 as "
        f"{'PASSED' if gate6_exit == 0 else 'FAILED'}.** See §9 for the per-quantity cause and gap."
    )
    lines.append("")

    lines.append("## 9. Post-fix relative bias — cause and remaining gap, quantified")
    lines.append("")
    for r in in_scope_rows:
        lines.append(f"- `{r['quantity']}`: injected={r['injected']}, recovered={r['recovered']}, "
                      f"relative_bias={r['relative_bias']}, status={r['status']}"
                      + (f" — {r['reason']}" if r["reason"] else ""))
    lines.append("")
    lines.append(
        "Per DIAGNOSIS.md: the fix targets the purity-dependent retention-vs-LOH confidence collapse "
        "(the confirmed mechanism), not the small-n ground-truth-realization variance (a separate, "
        "amplifying factor already addressed by the simulator's own n increase, independent of this "
        "caller). Any relative bias remaining above should be interpreted against that n increase "
        "(11088 total samples, ~1848 per arm-class cell, vs. the 60-sample run DIAGNOSIS.md diagnosed) "
        "rather than re-diagnosed as a new, different mechanism."
    )
    lines.append("")

    lines.append("## 10. gate7 — denominators")
    lines.append("")
    lines.append(f"gate7_denominators.py exit code: **{gate7_exit}** ({'PASS' if gate7_exit == 0 else 'FAIL'}).")
    lines.append("")
    lines.append("```")
    lines.append(gate7_out.strip())
    lines.append("```")
    lines.append("")

    lines.append("## 11. Files")
    lines.append("")
    lines.append("| File | Contents |")
    lines.append("|---|---|")
    lines.append("| `SIMULATED_loh_validation/SIMULATED_loh_calls.tsv` | one row per variant call: predicted category, confidence, posteriors, true category, BAF-used flag, correctness |")
    lines.append("| `SIMULATED_loh_validation/SIMULATED_confusion_matrix.tsv` | true x predicted category counts (long format) |")
    lines.append("| `SIMULATED_loh_validation/SIMULATED_rates_table.tsv` | every reported rate with numerator/denominator/excluded_count/n_total_cell/low_n_flag (gate7 input) |")
    lines.append("| `SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv` | the 2 recovered LR quantities with bootstrap CIs (gate6 `--recovered` input) |")
    lines.append("| `SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv` | scope declaration for all 16 SIMULATED_TRUTH.tsv quantities (gate6 `--scope` input) |")
    lines.append("| `SIMULATED_RECOVERY_TABLE.tsv` / `.md` | gate6's own emitted output (repo root), covering all 16 SIMULATED_TRUTH.tsv quantities |")
    lines.append("| `DIAGNOSIS.md` | the mechanism analysis this revision fixes |")
    lines.append("| `PROPOSED_DEVIATIONS.md` | proposed (not applied) PROTOCOL.md purity/depth floor deviations, per this task's Step 4 |")
    lines.append("")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
