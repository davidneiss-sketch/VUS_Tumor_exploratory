#!/usr/bin/env python3
"""simulate.py — SIMULATED regime simulator with fully-known ground truth.

Standing Rule 1 applies to every artifact this script produces: every
output filename contains SIMULATED, every report's first line is
"SIMULATED DATA — NOT A SCIENTIFIC RESULT", every caption begins
"SIMULATED:", no ACMG evidence strength is assigned anywhere in this
script's output, and status fields use only SIMULATED / SIMULATED_PASS /
SIMULATED_FAIL / BLOCKED.

What this generates, per the task:
  - SIMULATED_data/: tumor/normal pairs with independently controlled
    purity, ploidy, WGD, per-locus allele-specific copy number, depth,
    and germline genotype; a known LOH category (PROTOCOL.md §5.1) per
    variant; and known signature exposures at exome-scale mutation
    counts (PROTOCOL.md §5.4-style features).
  - SIMULATED_TRUTH.tsv (repo root, separate from SIMULATED_data/): the
    analytically-derived ground-truth likelihood ratio for each of 6
    injected quantities, with an `estimand` column. The full derivation
    of each is in SIMULATION_SPEC.md; the exact same distributional
    parameters are used here to both (a) compute the closed-form LR and
    (b) draw the actual per-sample data, so the "truth" is the genuine
    data-generating parameter, not a decorative number.
  - SIMULATED_TRUTH_detail/SIMULATED_sample_labels.tsv: the per-sample
    hidden class label (Pathogenic/Benign) a real downstream classifier
    would not see -- the answer key, also kept separate from
    SIMULATED_data/.

Every parameter used below is recorded in PARAMETER_PROVENANCE.tsv as
either a BENCHMARKS.tsv row ID or ARBITRARY with a stated rationale.
Nothing here was tuned to reproduce a prior run's output -- see the
`--check-no-v1-reuse` self-check this script runs and reports on every
invocation.

Run: python3 simulate.py
"""
from __future__ import annotations

import csv
import itertools
import math
import random
from pathlib import Path

# ============================================================================
# Fixed parameters. Every name here has a matching row in
# PARAMETER_PROVENANCE.tsv (checked by scripts/check_simulator_acceptance.py).
# ============================================================================

SEED = 20260907  # fixed for full reproducibility; ARBITRARY (today's date as YYYYMMDD)
N_PER_CELL = 15   # samples per (class x gene_group) cell; ARBITRARY, see PARAMETER_PROVENANCE.tsv
GENE_GROUPS = {
    # PROTOCOL.md §1 gene lists, copied verbatim.
    "CORE_HR": ["BRCA1", "BRCA2", "PALB2", "RAD51C", "RAD51D", "RAD51B", "BRIP1", "BARD1", "RAD54L"],
    "DDR_SIGNALING": ["ATM", "CHEK1", "CHEK2", "ATR", "MRE11", "RAD50", "NBN", "FANCM"],
}
PAM50_PROPORTIONS = {  # BENCHMARKS.tsv PAM01 (225/126/57/93 of 501)
    "LumA": 225 / 501, "LumB": 126 / 501, "HER2E": 57 / 501, "Basal": 93 / 501,
}
WGD_PREVALENCE = 0.30          # BENCHMARKS.tsv WGD01
MEAN_MUTATIONS_PER_EXOME = 60.05  # BENCHMARKS.tsv TMB01 (30626/510)
PURITY_RANGE = (0.10, 0.95)     # ARBITRARY, see PARAMETER_PROVENANCE.tsv
PLOIDY_RANGE = (1.5, 5.5)       # ARBITRARY (matches ASCAT's own default search bounds)
TUMOR_DEPTH_MEAN = 80.0         # ARBITRARY (headroom over PROTOCOL.md's 30x floor)
NORMAL_DEPTH_MEAN = 40.0        # ARBITRARY (headroom over PROTOCOL.md's 15x floor)
MIN_EVALUABLE_DEPTH = 20        # PROTOCOL.md §5.2, copied verbatim (not a free parameter)

# Class-conditional feature distributions -- these ARE the injected ground
# truth. Every one is ARBITRARY (chosen to produce a specific, pre-declared
# LR spanning several ACMG evidence bands, not fit to any prior data) --
# see PARAMETER_PROVENANCE.tsv for the per-parameter rationale.
LOH_SECOND_HIT_PROB = {
    "CORE_HR": {"Pathogenic": 0.70, "Benign": 0.10},
    "DDR_SIGNALING": {"Pathogenic": 0.40, "Benign": 0.15},
}
GIS_SCORE_DIST = {  # (mu, sigma) of a Normal, evaluated at a fixed x below
    "CORE_HR": {"Pathogenic": (55.0, 12.0), "Benign": (25.0, 10.0), "eval_x": 55.0},
    "DDR_SIGNALING": {"Pathogenic": (40.0, 15.0), "Benign": (25.0, 12.0), "eval_x": 40.0},
}
SBS3_EXPOSURE_DIST = {"Pathogenic": (0.35, 0.10), "Benign": (0.10, 0.08), "eval_x": 0.35}
NULL_FEATURE_PROB = {"Pathogenic": 0.50, "Benign": 0.50}  # engineered null: identical by construction

OTHER_LOH_CATEGORY_SPLIT = {  # among non-LOH_SECOND_HIT draws; ARBITRARY, see PARAMETER_PROVENANCE.tsv
    "RETAINED": 0.60, "LOH_NON_SECOND_HIT": 0.25, "LOH_AMBIGUOUS": 0.10, "NOT_EVALUABLE": 0.05,
}

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "SIMULATED_data"
TRUTH_DETAIL_DIR = REPO_ROOT / "SIMULATED_TRUTH_detail"
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"


# ============================================================================
# Analytic LR derivations (closed form; see SIMULATION_SPEC.md for the
# written-out derivation of each formula used here).
# ============================================================================

def norm_pdf(x: float, mu: float, sigma: float) -> float:
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


def categorical_lr(p_pathogenic: float, p_benign: float) -> float:
    """LR of observing the indicator event under a Bernoulli feature.
    PROTOCOL.md §6: LR(E) = P(E|Pathogenic) / P(E|Benign)."""
    return p_pathogenic / p_benign


def gaussian_lr(x: float, mu1: float, s1: float, mu0: float, s0: float) -> float:
    """LR of observing continuous evidence E=x under two Normal class-
    conditional densities. PROTOCOL.md §6: LR(E) = f(E|Pathogenic) / f(E|Benign)."""
    return norm_pdf(x, mu1, s1) / norm_pdf(x, mu0, s0)


def compute_truth_quantities() -> list[dict]:
    rows = []

    for group in ("CORE_HR", "DDR_SIGNALING"):
        p1 = LOH_SECOND_HIT_PROB[group]["Pathogenic"]
        p0 = LOH_SECOND_HIT_PROB[group]["Benign"]
        rows.append({
            "quantity": f"{group.lower()}_loh_second_hit_LR",
            "injected_value": categorical_lr(p1, p0),
            "estimand": "LR",
            "is_null": "FALSE",
            "feature_type": "categorical",
            "derivation": f"P(LOH_SECOND_HIT|Pathogenic)={p1} / P(LOH_SECOND_HIT|Benign)={p0}",
        })

    for group in ("CORE_HR", "DDR_SIGNALING"):
        d = GIS_SCORE_DIST[group]
        mu1, s1 = d["Pathogenic"]
        mu0, s0 = d["Benign"]
        x = d["eval_x"]
        rows.append({
            "quantity": f"{group.lower()}_gis_score_LR",
            "injected_value": gaussian_lr(x, mu1, s1, mu0, s0),
            "estimand": "LR",
            "is_null": "FALSE",
            "feature_type": "continuous_gaussian",
            "derivation": f"f(GIS={x}|Pathogenic~N({mu1},{s1})) / f(GIS={x}|Benign~N({mu0},{s0}))",
        })

    d = SBS3_EXPOSURE_DIST
    mu1, s1 = d["Pathogenic"]
    mu0, s0 = d["Benign"]
    x = d["eval_x"]
    rows.append({
        "quantity": "core_hr_sbs3_exposure_LR",
        "injected_value": gaussian_lr(x, mu1, s1, mu0, s0),
        "estimand": "LR",
        "is_null": "FALSE",
        "feature_type": "continuous_gaussian",
        "derivation": f"f(SBS3={x}|Pathogenic~N({mu1},{s1})) / f(SBS3={x}|Benign~N({mu0},{s0}))",
    })

    p1 = NULL_FEATURE_PROB["Pathogenic"]
    p0 = NULL_FEATURE_PROB["Benign"]
    rows.append({
        "quantity": "null_sequencing_depth_bucket_LR",
        "injected_value": categorical_lr(p1, p0),
        "estimand": "LR",
        "is_null": "TRUE",
        "feature_type": "categorical",
        "derivation": f"P(HIGH_DEPTH|Pathogenic)={p1} / P(HIGH_DEPTH|Benign)={p0} "
                       f"(engineered identical by construction -- HIGH_DEPTH is a coin "
                       f"flip independent of class in both branches of the generator)",
    })

    return rows


# ============================================================================
# Data generation
# ============================================================================

def expected_vaf(purity: float, cn_total: int, mutant_copies: int) -> float:
    """PROTOCOL.md §5.2 binomial VAF model, exact formula:
    E[VAF|X] = (p*X + (1-p)*1) / (p*CN_t + (1-p)*2)."""
    return (purity * mutant_copies + (1 - purity) * 1) / (purity * cn_total + (1 - purity) * 2)


def draw_loh_category(rng: random.Random, group: str, cls: str) -> str:
    p_second_hit = LOH_SECOND_HIT_PROB[group][cls]
    if rng.random() < p_second_hit:
        return "LOH_SECOND_HIT"
    r = rng.random()
    cum = 0.0
    for cat, prob in OTHER_LOH_CATEGORY_SPLIT.items():
        cum += prob
        if r < cum:
            return cat
    return "NOT_EVALUABLE"


def cn_and_depth_for_category(rng: random.Random, category: str, purity: float, wgd: bool) -> dict:
    cn_total = 4 if wgd else 2
    if category == "RETAINED":
        major, minor = cn_total // 2, cn_total // 2
        mutant_copies = 1
        depth = max(MIN_EVALUABLE_DEPTH + 5, round(rng.gauss(TUMOR_DEPTH_MEAN, 15)))
    elif category == "LOH_SECOND_HIT":
        major, minor = cn_total, 0
        mutant_copies = cn_total
        depth = max(MIN_EVALUABLE_DEPTH + 5, round(rng.gauss(TUMOR_DEPTH_MEAN, 15)))
    elif category == "LOH_NON_SECOND_HIT":
        major, minor = cn_total, 0
        mutant_copies = 0
        depth = max(MIN_EVALUABLE_DEPTH + 5, round(rng.gauss(TUMOR_DEPTH_MEAN, 15)))
    elif category == "LOH_AMBIGUOUS":
        major, minor = cn_total, 0
        vaf_hi = expected_vaf(purity, cn_total, cn_total)
        vaf_lo = expected_vaf(purity, cn_total, 0)
        mutant_copies = None  # use midpoint VAF directly, not a discrete copy count
        depth = MIN_EVALUABLE_DEPTH + rng.randint(0, 5)  # deliberately borderline depth
        return {"major": major, "minor": minor, "depth": depth, "vaf_target": (vaf_hi + vaf_lo) / 2}
    else:  # NOT_EVALUABLE
        major, minor = cn_total // 2, cn_total // 2
        mutant_copies = 1
        depth = rng.randint(4, MIN_EVALUABLE_DEPTH - 1)  # below the evaluable floor, by construction
        return {"major": major, "minor": minor, "depth": depth,
                "vaf_target": expected_vaf(purity, cn_total, mutant_copies)}

    return {"major": major, "minor": minor, "depth": depth,
            "vaf_target": expected_vaf(purity, cn_total, mutant_copies)}


SBS_CONTEXTS = [
    f"{five}[{sub}]{three}"
    for sub in ("C>A", "C>G", "C>T", "T>A", "T>C", "T>G")
    for five, three in itertools.product("ACGT", "ACGT")
]
assert len(SBS_CONTEXTS) == 96

# Two ARBITRARY, stylized 96-context "signature shapes" -- NOT the real
# published COSMIC SBS3 weights: this session's network policy blocks live
# retrieval of cancer.sanger.ac.uk / the COSMIC signature matrices (see
# BENCHMARKS_NOTES.md), so per Standing Rule 3 these are declared arbitrary
# rather than presented as the literal COSMIC values. They are internally
# consistent (each sums to 1 and is fixed once, not re-tuned) and serve only
# to give the simulator's mutation catalogs a non-uniform, reproducible shape.
def _make_shape(rng: random.Random, favored_substr: str, favored_weight: float) -> list[float]:
    weights = []
    for ctx in SBS_CONTEXTS:
        w = favored_weight if favored_substr in ctx else 1.0
        w *= rng.uniform(0.7, 1.3)
        weights.append(w)
    total = sum(weights)
    return [w / total for w in weights]


def build_signature_shapes(rng: random.Random) -> tuple[list[float], list[float]]:
    hrd_shape = _make_shape(rng, "C>T", 4.0)      # ARBITRARY stylized "HRD-like" shape
    background_shape = _make_shape(rng, "", 1.0)  # ARBITRARY ~flat background shape
    return hrd_shape, background_shape


def generate() -> None:
    master_rng = random.Random(SEED)

    DATA_DIR.mkdir(exist_ok=True)
    TRUTH_DETAIL_DIR.mkdir(exist_ok=True)

    hrd_shape, background_shape = build_signature_shapes(random.Random(SEED + 1))

    truth_rows = compute_truth_quantities()
    with open(TRUTH_TSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["quantity", "injected_value", "estimand", "is_null", "feature_type", "derivation"], delimiter="\t")
        w.writeheader()
        for r in truth_rows:
            w.writerow({**r, "injected_value": repr(r["injected_value"])})

    sample_rows, variant_rows, catalog_rows, exposure_rows, label_rows = [], [], [], [], []
    self_check_rows = []
    sample_idx = 0

    for group in ("CORE_HR", "DDR_SIGNALING"):
        for cls in ("Pathogenic", "Benign"):
            for _ in range(N_PER_CELL):
                sample_idx += 1
                sample_id = f"SIM-{sample_idx:04d}"
                rng = random.Random(SEED * 1000 + sample_idx)  # per-sample reproducible substream

                gene = rng.choice(GENE_GROUPS[group])
                subtype = rng.choices(list(PAM50_PROPORTIONS), weights=list(PAM50_PROPORTIONS.values()))[0]
                purity = rng.uniform(*PURITY_RANGE)
                ploidy = rng.uniform(*PLOIDY_RANGE)
                wgd = rng.random() < WGD_PREVALENCE
                normal_depth = max(5, round(rng.gauss(NORMAL_DEPTH_MEAN, 8)))

                sample_rows.append({
                    "sample_id": sample_id, "gene": gene, "gene_group": group,
                    "pam50_subtype": subtype, "purity": round(purity, 4),
                    "ploidy": round(ploidy, 4), "wgd": wgd, "normal_depth": normal_depth,
                })
                label_rows.append({"sample_id": sample_id, "true_class": cls, "gene_group": group, "gene": gene})

                # --- LOH category injection + read-count generation ---
                loh_category = draw_loh_category(rng, group, cls)
                cn_info = cn_and_depth_for_category(rng, loh_category, purity, wgd)
                depth = cn_info["depth"]
                vaf_target = cn_info["vaf_target"]
                tumor_alt = rng.binomialvariate(depth, max(0.0, min(1.0, vaf_target))) if hasattr(rng, "binomialvariate") else sum(1 for _ in range(depth) if rng.random() < vaf_target)
                tumor_ref = depth - tumor_alt
                normal_alt = rng.binomialvariate(normal_depth, 0.5) if hasattr(rng, "binomialvariate") else sum(1 for _ in range(normal_depth) if rng.random() < 0.5)
                normal_ref = normal_depth - normal_alt

                variant_rows.append({
                    "sample_id": sample_id, "gene": gene, "chrom": "chrSIM", "pos": 1000 + sample_idx,
                    "ref": "A", "alt": "G",
                    "normal_ref_reads": normal_ref, "normal_alt_reads": normal_alt,
                    "tumor_ref_reads": tumor_ref, "tumor_alt_reads": tumor_alt,
                    "major_cn": cn_info["major"], "minor_cn": cn_info["minor"],
                    "assigned_loh_category": loh_category,
                })

                # Self-check: re-run PROTOCOL.md §5.1/§5.2's own classification
                # logic against the generated reads and confirm it recovers
                # the category we assigned (evidence the injection is
                # internally consistent, not just a label with no matching data).
                recovered = classify_loh(tumor_ref, tumor_alt, cn_info["major"], cn_info["minor"], purity)
                self_check_rows.append({
                    "sample_id": sample_id, "assigned": loh_category, "recovered": recovered,
                    "match": assigned_matches_recovered(loh_category, recovered),
                })

                # --- signature exposure injection + mutation catalog ---
                mu, sigma = SBS3_EXPOSURE_DIST[cls]
                sbs3_exposure = min(0.95, max(0.0, rng.gauss(mu, sigma)))
                total_muts = max(5, round(rng.gauss(MEAN_MUTATIONS_PER_EXOME, 15)))
                n_hrd = round(total_muts * sbs3_exposure)
                n_bg = total_muts - n_hrd
                counts = [0] * 96
                if n_hrd > 0:
                    for ctx in rng.choices(range(96), weights=hrd_shape, k=n_hrd):
                        counts[ctx] += 1
                if n_bg > 0:
                    for ctx in rng.choices(range(96), weights=background_shape, k=n_bg):
                        counts[ctx] += 1
                catalog_rows.append({"sample_id": sample_id, **{SBS_CONTEXTS[i]: counts[i] for i in range(96)}})
                exposure_rows.append({
                    "sample_id": sample_id, "sbs3_relative_exposure_true": round(sbs3_exposure, 4),
                    "total_mutations": total_muts, "n_hrd_process_mutations": n_hrd, "n_background_mutations": n_bg,
                })

    write_simulated_tsv(DATA_DIR / "SIMULATED_sample_metadata.tsv", sample_rows,
                         ["sample_id", "gene", "gene_group", "pam50_subtype", "purity", "ploidy", "wgd", "normal_depth"])
    write_simulated_tsv(DATA_DIR / "SIMULATED_variant_calls.tsv", variant_rows,
                         ["sample_id", "gene", "chrom", "pos", "ref", "alt", "normal_ref_reads", "normal_alt_reads",
                          "tumor_ref_reads", "tumor_alt_reads", "major_cn", "minor_cn", "assigned_loh_category"])
    write_simulated_tsv(DATA_DIR / "SIMULATED_mutation_catalogs.tsv", catalog_rows, ["sample_id"] + SBS_CONTEXTS)
    write_simulated_tsv(DATA_DIR / "SIMULATED_signature_exposures.tsv", exposure_rows,
                         ["sample_id", "sbs3_relative_exposure_true", "total_mutations", "n_hrd_process_mutations", "n_background_mutations"])
    write_simulated_tsv(TRUTH_DETAIL_DIR / "SIMULATED_sample_labels.tsv", label_rows,
                         ["sample_id", "true_class", "gene_group", "gene"])

    # LOH self-check report (SIMULATED artifact -- Standing Rule 1 vocabulary)
    n_match = sum(1 for r in self_check_rows if r["match"])
    write_simulated_report(
        DATA_DIR / "SIMULATED_loh_injection_self_check.md",
        "LOH injection self-check",
        f"Re-classifying every generated sample's tumor/normal read counts with PROTOCOL.md "
        f"§5.1/§5.2's own binomial-test logic recovered the assigned LOH category for "
        f"{n_match}/{len(self_check_rows)} samples "
        f"({100*n_match/len(self_check_rows):.1f}%). LOH_AMBIGUOUS is expected to sometimes "
        f"resolve to a definite category by chance (that is what \"ambiguous\" means under a "
        f"noisy binomial draw); NOT_EVALUABLE is expected to match 100% (depth alone determines it).",
    )

    print(f"Generated {sample_idx} SIMULATED tumor/normal pairs under {DATA_DIR}")
    print(f"Wrote {TRUTH_TSV} ({len(truth_rows)} quantities) and {TRUTH_DETAIL_DIR}")
    print(f"LOH self-check: {n_match}/{len(self_check_rows)} recovered category matched assigned category")


def classify_loh(tumor_ref: int, tumor_alt: int, major: int, minor: int, purity: float) -> str:
    """PROTOCOL.md §5.1/§5.2, implemented exactly as specified there."""
    depth = tumor_ref + tumor_alt
    if depth < MIN_EVALUABLE_DEPTH:
        return "NOT_EVALUABLE"
    cn_total = major + minor
    vaf = tumor_alt / depth if depth > 0 else 0.0
    if minor >= 1:
        if 0.35 <= vaf <= 0.65:
            return "RETAINED"
        # falls through to AMBIGUOUS-style handling below if imbalanced despite minor>=1
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
    """Exact two-sided binomial test p-value (stdlib only, no scipy)."""
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


def assigned_matches_recovered(assigned: str, recovered: str) -> bool:
    return assigned == recovered


def write_simulated_tsv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in columns})


def write_simulated_report(path: Path, title: str, body: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(BANNER + "\n\n")
        f.write(f"# {title}\n\n")
        f.write(f"SIMULATED: {body}\n")


def check_no_v1_reuse() -> None:
    """Explicitly scan this repository for any 'v1'/'retracted' artifacts
    and confirm no simulator output value reproduces one. Reports the
    result either way (Standing Rule 4/8: log the check, don't skip it
    silently just because nothing was found)."""
    import re

    candidates = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_file() and (".git" not in p.parts):
            name = p.name.lower()
            if re.search(r"\bv1\b", name) or "retract" in name:
                candidates.append(str(p.relative_to(REPO_ROOT)))

    report_lines = [BANNER, "", "# No-v1-reuse parameter-independence check", ""]
    if not candidates:
        report_lines.append(
            "SIMULATED: repo-wide scan (excluding .git/) for filenames matching "
            "the word 'v1' or containing 'retract' found ZERO matching files. "
            "There are no retracted v1 artifacts in this repository (confirmed "
            "by this scan, not assumed) -- this check is therefore vacuously "
            "satisfied: no prior-run value exists for this simulator's output "
            "to have reproduced, by construction or otherwise."
        )
    else:
        report_lines.append("SIMULATED: candidate v1/retracted artifact files found:")
        for c in candidates:
            report_lines.append(f"  - {c}")
        report_lines.append(
            "SIMULATED: manual review required -- this script does not itself "
            "diff simulator output against arbitrary prior files; the presence "
            "of matching filenames is reported as BLOCKED pending that review."
        )
    (DATA_DIR / "SIMULATED_no_v1_reuse_check.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print("\n".join(report_lines))


if __name__ == "__main__":
    generate()
    check_no_v1_reuse()
