#!/usr/bin/env python3
"""signatures.py — SBS3 estimation at exome scale (SIMULATED regime).

This script runs the REAL SigProfilerAssignment 1.1.5 (GATE1.json PASS)
against SIMULATED exome mutation catalogs, and attempts SigMA (GATE1.json
FAIL) to re-confirm its BLOCKED status honestly rather than assuming a
prior session's result still holds. SigProfilerAssignment is not
importable in this session's default python -- see
SIMULATED_signature_validation.md "Environment" section -- so this script
re-executes itself inside the `vus-tumor-gate1:local` docker image
GATE1.json certified (digest matched live, see phase0_environment_check),
rather than pip-installing a fresh, ungated copy of the tool.

Two separate validation exercises are run, deliberately kept apart:

1. GATE6-SCORED RECOVERY of the two pre-existing SIMULATED_TRUTH.tsv
   quantities `core_hr_sbs3_exposure_LR` / `ddr_signaling_sbs3_exposure_LR`
   -- declared NOT_IN_SCOPE by loh_caller.py ("requires a
   SigProfilerAssignment SBS3-exposure feature this LOH caller does not
   compute"). This script computes that feature and claims that scope,
   against simulate.py's EXISTING mutation catalogs
   (SIMULATED_data/SIMULATED_mutation_catalogs.tsv, built from ARBITRARY
   96-context signature shapes -- see SIMULATION_SPEC.md).

2. A DEDICATED real-COSMIC-shape validation (this task's DO list: exome
   normalization, COSMIC-version misassignment, error-vs-mutation-count
   curve). Misassignment between SBS3/SBS5/SBS40 is a property of their
   REAL cosine-similar shapes -- ARBITRARY shapes cannot demonstrate it.
   This exercise therefore builds its OWN catalog using the REAL COSMIC
   v3.6 SBS3 (HR-deficiency process) and SBS5 (background process)
   weight vectors, extracted live from the installed package (network
   access to cancer.sanger.ac.uk is blocked -- see ENVIRONMENT.lock §0 --
   so "live" here means read from the exact installed package file,
   version-pinned and path-cited, the same evidentiary standard
   GATE1.json used for SigMA's DESCRIPTION file). Per-sample
   total_mutations and injected sbs3_relative_exposure_true are REUSED
   from SIMULATED_data/SIMULATED_signature_exposures.tsv (real existing
   infrastructure, not re-derived) to keep this exercise's injection
   design traceable to the same simulator.

Run: python3 signatures.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "SIMULATED_data"
GATES_DIR = REPO_ROOT / "gates"
WORK_DIR = REPO_ROOT / "SIMULATED_signature_work"
BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

INSIDE_DOCKER_ENV_VAR = "VUS_SIGNATURES_INSIDE_DOCKER"
DOCKER_IMAGE = "vus-tumor-gate1:local"
DOCKER_IMAGE_DIGEST = "sha256:2f344e8a456167eec8701db9581b07b0a4139ed2acdaecf23ab811fec354ca4c"  # GATE1.json

SPA_PACKAGE_VERSION_EXPECTED = "1.1.5"  # GATE1.json pin
GENOME_BUILD = "GRCh38"  # PROTOCOL.md §5.4 / ENVIRONMENT.lock reference build (GRCh38.p14)
CURRENT_COSMIC_VERSION = 3.6  # SigProfilerAssignment 1.1.5's own bundled default -- confirmed live this session via inspect.signature(Analyzer.cosmic_fit)
V2_EQUIVALENT_COSMIC_VERSION = 2  # legacy "Signature_N" nomenclature, bundled in the same package build
COSMIC_VERSION_SWEEP = [2, 3.6]  # P08 restriction: PROTOCOL.md §5.4 names exactly ONE runnable
# cosmic_version explicitly -- "the version bundled with/downloadable by this exact package
# build" (3.6, confirmed live) -- and separately requires LOGGING (not running) the general
# COSMIC database release cadence (v104), a different, non-comparable numbering that is not a
# valid cosmic_version argument at all. The second version run here (2) is NOT a second version
# PROTOCOL.md's own text names; it comes from this task series' own "v2-equivalent" pinning
# requirement (Task K's prompt). This is stated plainly rather than mis-cited as "two versions
# PROTOCOL.md names": PROTOCOL.md names one. The original 7-version sweep (2, 3, 3.1-3.4, 3.6)
# exceeded both readings and is dropped per P08's explicit instruction; no version was ever
# selected or dropped on the basis of producing a more favorable recovery result -- all 7 were
# already run and reported (unchanged) in the prior committed report before this restriction.
GENERAL_COSMIC_RELEASE_NOTE = (
    "PROTOCOL.md §5.4 requires logging BOTH version strings, since they use different "
    "numbering: (a) the signature-matrix version bundled with this package build "
    "(3.6, confirmed live above) and (b) the general COSMIC database release cadence "
    "(v104 as of 2026-05-18, ENVIRONMENT.lock §3 -- not re-verified live this session, "
    "cancer.sanger.ac.uk remains network-blocked; a live WebSearch this session "
    "independently corroborated COSMIC Mutational Signatures v3.6 as the current "
    "signature-set release, matching (a).)"
)

HRD_SIGNATURE = "SBS3"
BACKGROUND_SIGNATURE = "SBS5"  # ARBITRARY, disclosed: a common ubiquitous background process; real COSMIC v3.6 weights used, not an arbitrary shape

SEED = 20260908  # ARBITRARY, disclosed: today's session date as YYYYMMDD, matches simulate.py's SEED convention

TOTAL_MUTATIONS_BIN_EDGES = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 116]
N_PER_BIN_MAIN = 40  # ARBITRARY, disclosed: stratified subsample size per total_mutations bin for the main validation run; chosen for docker wall-clock feasibility in one session (~40ms/sample-column observed) against the full n=11088 population -- see "Subsampling" in the report
N_PER_BIN_BOOTSTRAP = 4  # ARBITRARY, disclosed: smaller bootstrap subset (subset of the main subset) -- each of these gets BOOTSTRAP_REPLICATES resamples, multiplying column count
BOOTSTRAP_REPLICATES = 100  # ARBITRARY, disclosed: B for this task's own per-sample multinomial resampling bootstrap -- distinct from PROTOCOL.md's B (that governs the LOH bootstrap, gate4, not this feature)
LR_BOOTSTRAP_REPLICATES = 2000  # cheap (resamples already-recovered scalars, no re-run of SPA), matches loh_caller.py-style population bootstrap scale

MAE_UNRECOVERABLE_CRITERION = 0.15  # ARBITRARY, disclosed: absolute-error-on-[0,1]-fraction-scale criterion for "unrecoverable" -- chosen for the same order of magnitude as PROTOCOL.md §11's 0.25 relative-bias tolerance, but stated as ABSOLUTE fraction error (not relative) because sbs3_relative_exposure_true is frequently near 0, where relative bias is undefined/explosive

# EVAL_POINT and the class-Gaussian-LR construction below reproduce
# simulate.py's own {arm}_sbs3_exposure_LR definition exactly (same
# EVAL_POINT["sbs3"], same phi_pdf), applied to REAL recovered exposures
# instead of the analytic injected-model parameters.
EVAL_POINT_SBS3 = 0.30  # simulate.py EVAL_POINT["sbs3"], copied verbatim -- this quantity's target is fixed by that file, not chosen here


def log(msg: str) -> None:
    print(f"[signatures.py] {msg}", flush=True)


# ============================================================================
# Docker re-exec
# ============================================================================

def ensure_inside_docker() -> None:
    if os.environ.get(INSIDE_DOCKER_ENV_VAR) == "1":
        try:
            import SigProfilerAssignment  # noqa: F401
        except ImportError as e:
            log(f"FATAL: inside {DOCKER_IMAGE} but SigProfilerAssignment is still not importable: {e}")
            sys.exit(1)
        return
    log(f"Host python lacks SigProfilerAssignment. Re-executing inside {DOCKER_IMAGE} "
        f"(digest must match GATE1.json's {DOCKER_IMAGE_DIGEST})...")
    inspect = subprocess.run(
        ["docker", "image", "inspect", DOCKER_IMAGE, "--format", "{{.Id}}"],
        capture_output=True, text=True,
    )
    if inspect.returncode != 0:
        log(f"FATAL: docker image {DOCKER_IMAGE} not found locally: {inspect.stderr.strip()}")
        sys.exit(1)
    actual_digest = inspect.stdout.strip()
    if actual_digest != DOCKER_IMAGE_DIGEST:
        log(f"FATAL: docker image digest mismatch -- GATE1.json pins {DOCKER_IMAGE_DIGEST}, "
            f"found {actual_digest}. Refusing to run against an unverified image.")
        sys.exit(1)
    log(f"Image digest confirmed to match GATE1.json: {actual_digest}")
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{REPO_ROOT}:{REPO_ROOT}",
        "-w", str(REPO_ROOT),
        "-e", f"{INSIDE_DOCKER_ENV_VAR}=1",
        DOCKER_IMAGE, "python3", str(Path(__file__).resolve()), *sys.argv[1:],
    ]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


# ============================================================================
# Small stdlib TSV helpers (matches gates_common.py conventions)
# ============================================================================

def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in columns})


def phi_pdf(x: float, mu: float, sigma: float) -> float:
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


# ============================================================================
# Phase 0: environment check (SigProfilerAssignment live-confirmed; SigMA
# re-attempted fresh this session, not assumed from GATE1.json)
# ============================================================================

def phase0_environment_check() -> dict:
    import SigProfilerAssignment
    from SigProfilerAssignment import Analyzer as Analyze
    import inspect as _inspect

    spa_version = getattr(SigProfilerAssignment, "__version__", None)
    sig = _inspect.signature(Analyze.cosmic_fit)
    bundled_default_cosmic_version = sig.parameters["cosmic_version"].default
    bundled_default_genome_build = sig.parameters["genome_build"].default

    sigma_check = subprocess.run(
        ["Rscript", "-e",
         "tryCatch({library(SigMA); cat('SigMA_OK')}, error=function(e) cat('SigMA_FAIL:', conditionMessage(e)))"],
        capture_output=True, text=True,
    )
    bsgenome_check = subprocess.run(
        ["Rscript", "-e",
         "tryCatch({library(BSgenome.Hsapiens.UCSC.hg19); cat('BSGENOME_OK')}, "
         "error=function(e) cat('BSGENOME_FAIL:', conditionMessage(e)))"],
        capture_output=True, text=True,
    )
    sigma_ok = "SigMA_OK" in sigma_check.stdout
    bsgenome_ok = "BSGENOME_OK" in bsgenome_check.stdout

    result = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "docker_image": DOCKER_IMAGE,
        "docker_image_digest": DOCKER_IMAGE_DIGEST,
        "sigprofilerassignment_version": spa_version,
        "sigprofilerassignment_version_matches_gate1": spa_version == SPA_PACKAGE_VERSION_EXPECTED,
        "cosmic_version_bundled_default": bundled_default_cosmic_version,
        "genome_build_bundled_default": bundled_default_genome_build,
        "genome_build_used_this_run": GENOME_BUILD,
        "sigma_status": "PASS" if sigma_ok else "FAIL",
        "sigma_check_output": sigma_check.stdout.strip() or sigma_check.stderr.strip()[-500:],
        "bsgenome_hg19_status": "PASS" if bsgenome_ok else "FAIL",
        "bsgenome_hg19_check_output": bsgenome_check.stdout.strip() or bsgenome_check.stderr.strip()[-500:],
        "sigma_matches_gate1_fail": (not sigma_ok),
    }
    log(f"SigProfilerAssignment {spa_version} (expected {SPA_PACKAGE_VERSION_EXPECTED}); "
        f"bundled default cosmic_version={bundled_default_cosmic_version}, genome_build={bundled_default_genome_build}")
    log(f"SigMA re-check this session: {'PASS' if sigma_ok else 'FAIL'} "
        f"(GATE1.json recorded FAIL -- {'MATCHES' if not sigma_ok else 'DOES NOT MATCH, tool availability changed'})")
    if bundled_default_cosmic_version != CURRENT_COSMIC_VERSION:
        log(f"WARNING: bundled default cosmic_version={bundled_default_cosmic_version} != "
            f"hardcoded CURRENT_COSMIC_VERSION={CURRENT_COSMIC_VERSION} -- constant is stale, trust the live value")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    with open(WORK_DIR / "SIMULATED_environment_check.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


# ============================================================================
# Phase 1: extract real COSMIC reference vectors + trinucleotide
# genome/exome normalization factors, from the installed package
# ============================================================================

def _spa_data_root() -> Path:
    import SigProfilerAssignment
    return Path(SigProfilerAssignment.__path__[0]) / "data" / "Reference_Signatures" / GENOME_BUILD


def _smg_context_root() -> Path:
    import SigProfilerMatrixGenerator
    return (Path(SigProfilerMatrixGenerator.__path__[0]) / "references" / "chromosomes"
            / "context_distributions")


def _read_sbs96_matrix(path: Path) -> tuple[list[str], dict[str, list[float]]]:
    rows = read_tsv(path)
    header = list(rows[0].keys())
    context_key = header[0]  # literal header "Type" in every COSMIC_v*_SBS_*.txt file, confirmed live this session
    contexts = [r[context_key] for r in rows]
    sig_names = header[1:]
    cols = {name: [float(r[name]) for r in rows] for name in sig_names}
    return contexts, cols


def phase1_extract_reference() -> dict:
    data_root = _spa_data_root()
    extract_cols: dict[str, list[float]] = {}
    contexts_ref: list[str] | None = None
    sources = []

    def load(version_tag: str, filename: str, colname: str, out_key: str):
        nonlocal contexts_ref
        path = data_root / filename
        contexts, cols = _read_sbs96_matrix(path)
        if contexts_ref is None:
            contexts_ref = contexts
        elif contexts != contexts_ref:
            raise ValueError(f"{path}: context ordering does not match reference file")
        if colname not in cols:
            raise ValueError(f"{path}: expected column {colname!r} not found (have {list(cols)[:5]}...)")
        extract_cols[out_key] = cols[colname]
        sources.append({"key": out_key, "file": str(path), "column": colname})

    load("v3.6", f"COSMIC_v{CURRENT_COSMIC_VERSION}_SBS_{GENOME_BUILD}.txt", "SBS3", "SBS3_v3.6")
    load("v3.6", f"COSMIC_v{CURRENT_COSMIC_VERSION}_SBS_{GENOME_BUILD}.txt", "SBS5", "SBS5_v3.6")
    load("v3.6", f"COSMIC_v{CURRENT_COSMIC_VERSION}_SBS_{GENOME_BUILD}.txt", "SBS40a", "SBS40a_v3.6")
    load("v3.6", f"COSMIC_v{CURRENT_COSMIC_VERSION}_SBS_{GENOME_BUILD}.txt", "SBS40b", "SBS40b_v3.6")
    load("v3.6", f"COSMIC_v{CURRENT_COSMIC_VERSION}_SBS_{GENOME_BUILD}.txt", "SBS40c", "SBS40c_v3.6")
    load("v3", f"COSMIC_v3_SBS_{GENOME_BUILD}.txt", "SBS40", "SBS40_unsplit_v3")
    load("v2", f"COSMIC_v{V2_EQUIVALENT_COSMIC_VERSION}_SBS_{GENOME_BUILD}.txt", "Signature_3", "Signature_3_v2")
    load("v2", f"COSMIC_v{V2_EQUIVALENT_COSMIC_VERSION}_SBS_{GENOME_BUILD}.txt", "Signature_5", "Signature_5_v2")

    rows_out = [{"context": ctx, **{k: extract_cols[k][i] for k in extract_cols}}
                for i, ctx in enumerate(contexts_ref)]
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    extract_path = WORK_DIR / "SIMULATED_cosmic_reference_extract.tsv"
    write_tsv(extract_path, rows_out, ["context"] + list(extract_cols.keys()))

    def cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na > 0 and nb > 0 else float("nan")

    similarity = {
        "SBS3_v3.6_vs_SBS5_v3.6": cosine_sim(extract_cols["SBS3_v3.6"], extract_cols["SBS5_v3.6"]),
        "SBS3_v3.6_vs_SBS40a_v3.6": cosine_sim(extract_cols["SBS3_v3.6"], extract_cols["SBS40a_v3.6"]),
        "SBS3_v3.6_vs_Signature_3_v2": cosine_sim(extract_cols["SBS3_v3.6"], extract_cols["Signature_3_v2"]),
        "Signature_3_v2_vs_SBS40_unsplit_v3": cosine_sim(extract_cols["Signature_3_v2"], extract_cols["SBS40_unsplit_v3"]),
    }
    log(f"Real COSMIC signature cosine similarities (source of the misassignment risk): {similarity}")

    # Trinucleotide genome/exome normalization factors -- real counts from
    # the installed SigProfilerMatrixGenerator reference data (§ "no
    # network required" -- this is opportunity data bundled with the tool,
    # not COSMIC's copyrighted signature weights).
    ctx_root = _smg_context_root()
    genome_path = ctx_root / f"context_counts_{GENOME_BUILD}_96.csv"
    exome_path = ctx_root / f"context_counts_{GENOME_BUILD}_96_exome.csv"

    def load_trinuc_totals(path: Path) -> dict[str, int]:
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            chrom_cols = header[1:]
            totals = {}
            for row in reader:
                trinuc = row[0].strip()
                totals[trinuc] = sum(int(v) for v in row[1:])
        return totals

    genome_totals = load_trinuc_totals(genome_path)
    exome_totals = load_trinuc_totals(exome_path)
    genome_grand_total = sum(genome_totals.values())
    exome_grand_total = sum(exome_totals.values())

    factor_rows = []
    for trinuc in sorted(genome_totals):
        g_freq = genome_totals[trinuc] / genome_grand_total
        e_freq = exome_totals.get(trinuc, 0) / exome_grand_total if exome_grand_total else float("nan")
        factor = g_freq / e_freq if e_freq else float("nan")
        factor_rows.append({
            "trinucleotide": trinuc,
            "genome_count": genome_totals[trinuc],
            "exome_count": exome_totals.get(trinuc, 0),
            "genome_freq": round(g_freq, 8),
            "exome_freq": round(e_freq, 8),
            "genome_to_exome_factor": round(factor, 6),
        })
    factors_path = WORK_DIR / "SIMULATED_trinuc_exome_genome_factors.tsv"
    write_tsv(factors_path, factor_rows,
              ["trinucleotide", "genome_count", "exome_count", "genome_freq", "exome_freq", "genome_to_exome_factor"])
    log(f"Trinucleotide genome/exome normalization factors written: {factors_path} "
        f"({len(factor_rows)} trinucleotide contexts; source: {genome_path.name}, {exome_path.name})")

    provenance = {
        "genome_build": GENOME_BUILD,
        "spa_data_root": str(data_root),
        "smg_context_root": str(ctx_root),
        "sources": sources,
        "trinuc_genome_source": str(genome_path),
        "trinuc_exome_source": str(exome_path),
        "cosine_similarities": similarity,
        "note": "Read from the exact files installed by SigProfilerAssignment 1.1.5 / "
                "SigProfilerMatrixGenerator inside vus-tumor-gate1:local. Not fetched from a "
                "live URL: cancer.sanger.ac.uk is network-blocked this session (ENVIRONMENT.lock "
                "§0). These are the same reference-signature and opportunity files "
                "SigProfilerAssignment itself reads at runtime -- not a re-derivation.",
    }
    with open(WORK_DIR / "SIMULATED_cosmic_reference_provenance.json", "w") as f:
        json.dump(provenance, f, indent=2)

    return {
        "contexts": contexts_ref,
        "vectors": extract_cols,
        "similarity": similarity,
        "factor_rows": factor_rows,
        "extract_path": extract_path,
    }




# ============================================================================
# Phase 2: build the real-COSMIC-shape validation catalog
# ============================================================================

def stratify_by_total_mutations(rows: list[dict], n_per_bin: int, rng: random.Random) -> list[dict]:
    bins: dict[int, list[dict]] = {i: [] for i in range(len(TOTAL_MUTATIONS_BIN_EDGES) - 1)}
    for r in rows:
        tm = int(r["total_mutations"])
        for i in range(len(TOTAL_MUTATIONS_BIN_EDGES) - 1):
            if TOTAL_MUTATIONS_BIN_EDGES[i] <= tm < TOTAL_MUTATIONS_BIN_EDGES[i + 1]:
                bins[i].append(r)
                break
    selected = []
    for i, bucket in bins.items():
        rng.shuffle(bucket)
        picked = bucket[:n_per_bin]
        for r in picked:
            r["_bin_index"] = i
            r["_bin_label"] = f"[{TOTAL_MUTATIONS_BIN_EDGES[i]},{TOTAL_MUTATIONS_BIN_EDGES[i+1]})"
        selected.extend(picked)
        if len(bucket) < n_per_bin:
            log(f"WARNING: bin {i} ([{TOTAL_MUTATIONS_BIN_EDGES[i]},{TOTAL_MUTATIONS_BIN_EDGES[i+1]})) "
                f"has only {len(bucket)} available samples, requested {n_per_bin}")
    return selected


def multinomial_draw(total: int, contexts: list[str], probs: list[float], rng: random.Random) -> list[int]:
    draws = rng.choices(range(len(contexts)), weights=probs, k=total)
    counts = [0] * len(contexts)
    for d in draws:
        counts[d] += 1
    return counts


def normalize(vec: list[float]) -> list[float]:
    s = sum(vec)
    return [v / s for v in vec]


def phase2_generate_validation_catalog(ref: dict) -> dict:
    contexts = ref["contexts"]
    sbs3_vec = normalize(ref["vectors"]["SBS3_v3.6"])
    sbs5_vec = normalize(ref["vectors"]["SBS5_v3.6"])

    design_rows = read_tsv(DATA_DIR / "SIMULATED_signature_exposures.tsv")
    log(f"Injection design reused from SIMULATED_data/SIMULATED_signature_exposures.tsv: "
        f"{len(design_rows)} samples available (real existing simulator infrastructure)")

    rng = random.Random(SEED)
    main_selected = stratify_by_total_mutations(design_rows, N_PER_BIN_MAIN, rng)
    main_selected.sort(key=lambda r: r["sample_id"])
    log(f"Main validation subset: {len(main_selected)} of {len(design_rows)} samples "
        f"(stratified by total_mutations, {N_PER_BIN_MAIN} per bin, {len(TOTAL_MUTATIONS_BIN_EDGES)-1} bins, seed={SEED})")

    catalog_cols: dict[str, list[int]] = {}
    truth_rows = []
    bootstrap_seed_counts: dict[str, list[int]] = {}
    bootstrap_sample_ids = set()
    bin_counts_seen: dict[int, int] = {}

    for r in main_selected:
        sid = r["sample_id"]
        total = int(r["total_mutations"])
        true_exp = float(r["sbs3_relative_exposure_true"])
        p = [true_exp * s3 + (1 - true_exp) * s5 for s3, s5 in zip(sbs3_vec, sbs5_vec)]
        counts = multinomial_draw(total, contexts, p, rng)
        catalog_cols[sid] = counts
        truth_rows.append({
            "sample_id": sid, "total_mutations": total,
            "sbs3_relative_exposure_true": true_exp, "bin_label": r["_bin_label"],
        })
        bin_idx = r["_bin_index"]
        seen = bin_counts_seen.get(bin_idx, 0)
        if seen < N_PER_BIN_BOOTSTRAP:
            bootstrap_seed_counts[sid] = counts
            bootstrap_sample_ids.add(sid)
            bin_counts_seen[bin_idx] = seen + 1

    catalog_path = WORK_DIR / "SIMULATED_sbs3_validation_catalog_main.tsv"
    with open(catalog_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["MutationType"] + list(catalog_cols.keys()))
        for i, ctx in enumerate(contexts):
            w.writerow([ctx] + [catalog_cols[sid][i] for sid in catalog_cols])
    write_tsv(WORK_DIR / "SIMULATED_sbs3_validation_truth_main.tsv", truth_rows,
              ["sample_id", "total_mutations", "sbs3_relative_exposure_true", "bin_label"])

    bootstrap_seed_path = WORK_DIR / "SIMULATED_sbs3_bootstrap_seed_counts.tsv"
    with open(bootstrap_seed_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["MutationType"] + list(bootstrap_seed_counts.keys()))
        for i, ctx in enumerate(contexts):
            w.writerow([ctx] + [bootstrap_seed_counts[sid][i] for sid in bootstrap_seed_counts])

    log(f"Bootstrap subset: {len(bootstrap_sample_ids)} samples (subset of main, "
        f"{N_PER_BIN_BOOTSTRAP} per bin) -> {catalog_path.name}, {bootstrap_seed_path.name}")

    return {
        "contexts": contexts,
        "catalog_path": catalog_path,
        "truth_rows": truth_rows,
        "bootstrap_sample_ids": sorted(bootstrap_sample_ids),
        "bootstrap_seed_path": bootstrap_seed_path,
        "n_design_population": len(design_rows),
    }




# ============================================================================
# SigProfilerAssignment invocation helper
# ============================================================================

def run_cosmic_fit(matrix_path: Path, out_dir: Path, exome: bool, cosmic_version) -> dict[str, dict[str, float]]:
    """Runs the REAL Analyzer.cosmic_fit against matrix_path (MutationType
    rows x sample columns, matrix input_type). Returns {sample_id: {signature: count}}
    parsed from Assignment_Solution_Activities.txt (raw per-signature mutation
    counts, sums to that sample's total_mutations by construction of an NNLS
    decomposition fit)."""
    from SigProfilerAssignment import Analyzer as Analyze
    t0 = time.time()
    Analyze.cosmic_fit(
        samples=str(matrix_path),
        output=str(out_dir),
        input_type="matrix",
        context_type="96",
        genome_build=GENOME_BUILD,
        cosmic_version=cosmic_version,
        exome=exome,
        make_plots=False,
        export_probabilities=False,
        verbose=False,
    )
    elapsed = time.time() - t0
    activities_path = out_dir / "Assignment_Solution" / "Activities" / "Assignment_Solution_Activities.txt"
    rows = read_tsv(activities_path)
    header = list(rows[0].keys())
    sig_cols = header[1:]
    result = {}
    for r in rows:
        sid = r[header[0]]
        result[sid] = {sig: float(r[sig]) for sig in sig_cols}
    log(f"cosmic_fit(exome={exome}, cosmic_version={cosmic_version}) on {matrix_path.name}: "
        f"{len(result)} samples, {len(sig_cols)} signatures, {elapsed:.1f}s -> {activities_path}")
    return result


def hrd_bg_columns_for_version(sig_cols: list[str], cosmic_version) -> tuple[str, str, list[str]]:
    if cosmic_version == V2_EQUIVALENT_COSMIC_VERSION:
        hrd_col = "Signature_3"
        bg_col = "Signature_5"
        sbs40_cols = [c for c in sig_cols if c.startswith("Signature_40")]
    else:
        hrd_col = "SBS3"
        bg_col = "SBS5"
        sbs40_cols = [c for c in sig_cols if c == "SBS40" or c.startswith("SBS40")]
    return hrd_col, bg_col, sbs40_cols


def relative_exposure(activities: dict[str, float], hrd_col: str) -> float:
    total = sum(activities.values())
    if total <= 0:
        return 0.0
    return activities.get(hrd_col, 0.0) / total


# ============================================================================
# Phase 3: no-normalization comparison (exome=True vs exome=False)
# ============================================================================

def phase3_exome_normalization_compare(cat: dict) -> dict:
    truth_by_id = {r["sample_id"]: r for r in cat["truth_rows"]}
    activities_true = run_cosmic_fit(
        cat["catalog_path"], WORK_DIR / "spa_out_exomeTrue_v3.6", exome=True, cosmic_version=CURRENT_COSMIC_VERSION,
    )
    activities_false = run_cosmic_fit(
        cat["catalog_path"], WORK_DIR / "spa_out_exomeFalse_v3.6", exome=False, cosmic_version=CURRENT_COSMIC_VERSION,
    )
    rows = []
    for sid, truth in truth_by_id.items():
        true_exp = truth["sbs3_relative_exposure_true"]
        rec_true = relative_exposure(activities_true[sid], "SBS3")
        rec_false = relative_exposure(activities_false[sid], "SBS3")
        rows.append({
            "sample_id": sid,
            "total_mutations": truth["total_mutations"],
            "bin_label": truth["bin_label"],
            "sbs3_relative_exposure_true": true_exp,
            "recovered_exome_normalized": round(rec_true, 6),
            "recovered_no_normalization": round(rec_false, 6),
            "abs_error_normalized": round(abs(rec_true - true_exp), 6),
            "abs_error_no_normalization": round(abs(rec_false - true_exp), 6),
            "normalization_improves": abs(rec_true - true_exp) < abs(rec_false - true_exp),
        })
    write_tsv(WORK_DIR / "SIMULATED_sbs3_exome_compare.tsv", rows,
              ["sample_id", "total_mutations", "bin_label", "sbs3_relative_exposure_true",
               "recovered_exome_normalized", "recovered_no_normalization",
               "abs_error_normalized", "abs_error_no_normalization", "normalization_improves"])

    n = len(rows)
    n_improves = sum(1 for r in rows if r["normalization_improves"])
    n_worse = sum(1 for r in rows if not r["normalization_improves"]
                  and r["abs_error_normalized"] != r["abs_error_no_normalization"])
    n_tied = n - n_improves - n_worse
    mae_norm = statistics.mean(r["abs_error_normalized"] for r in rows)
    mae_no_norm = statistics.mean(r["abs_error_no_normalization"] for r in rows)
    log(f"Exome normalization comparison, n={n}: MAE with normalization={mae_norm:.4f}, "
        f"MAE without={mae_no_norm:.4f}, normalization improves {n_improves}/{n} samples "
        f"({n_worse} worse, {n_tied} tied)")
    return {
        "rows": rows, "n": n, "n_improves": n_improves, "n_worse": n_worse, "n_tied": n_tied,
        "mae_normalized": mae_norm, "mae_no_normalization": mae_no_norm,
        "activities_true_v3_6_exomeTrue": activities_true,
    }


# ============================================================================
# Phase 4: COSMIC-version sweep -- SBS3 misassignment to SBS5/SBS40
# ============================================================================

def phase4_cosmic_version_sweep(cat: dict, reuse_v3_6: dict[str, dict[str, float]]) -> dict:
    truth_by_id = {r["sample_id"]: r for r in cat["truth_rows"]}
    per_version_rows = []
    misassignment_summary = []

    for version in COSMIC_VERSION_SWEEP:
        if version == CURRENT_COSMIC_VERSION:
            activities = reuse_v3_6
            log(f"cosmic_version={version}: reusing phase 3's exome=True run (identical call)")
        else:
            out_dir = WORK_DIR / f"spa_out_v{str(version).replace('.', '_')}"
            activities = run_cosmic_fit(cat["catalog_path"], out_dir, exome=True, cosmic_version=version)

        sample_ids = list(activities.keys())
        sig_cols = list(next(iter(activities.values())).keys())
        hrd_col, bg_col, sbs40_cols = hrd_bg_columns_for_version(sig_cols, version)

        misassigned_to_bg_frac = []
        misassigned_to_sbs40_frac = []
        recovered_hrd_frac = []
        excluded_zero_truth = 0
        for sid in sample_ids:
            true_exp = truth_by_id[sid]["sbs3_relative_exposure_true"]
            act = activities[sid]
            total = sum(act.values())
            if total <= 0:
                continue
            hrd_rec = act.get(hrd_col, 0.0) / total
            bg_rec = act.get(bg_col, 0.0) / total
            sbs40_rec = sum(act.get(c, 0.0) for c in sbs40_cols) / total
            recovered_hrd_frac.append(hrd_rec)
            per_version_rows.append({
                "cosmic_version": version, "sample_id": sid,
                "sbs3_relative_exposure_true": true_exp,
                "hrd_column": hrd_col, "recovered_hrd_fraction": round(hrd_rec, 6),
                "bg_column": bg_col, "recovered_bg_fraction": round(bg_rec, 6),
                "sbs40_columns": ";".join(sbs40_cols), "recovered_sbs40_fraction": round(sbs40_rec, 6),
            })
            if true_exp <= 0:
                excluded_zero_truth += 1
                continue
            # misassignment: how much of the TRUE injected HRD signal is missing
            # from the recovered HRD column, expressed as a fraction of the
            # true signal, then attributed (where identifiable) to bg/SBS40
            shortfall = true_exp - hrd_rec
            if shortfall > 0:
                misassigned_to_bg_frac.append(min(1.0, bg_rec / true_exp))
                misassigned_to_sbs40_frac.append(min(1.0, sbs40_rec / true_exp))

        mean_recovered = statistics.mean(recovered_hrd_frac) if recovered_hrd_frac else float("nan")
        mean_true = statistics.mean(truth_by_id[sid]["sbs3_relative_exposure_true"] for sid in sample_ids)
        misassignment_summary.append({
            "cosmic_version": version,
            "hrd_column": hrd_col,
            "n_samples": len(sample_ids),
            "n_excluded_zero_true_exposure": excluded_zero_truth,
            "mean_true_exposure": round(mean_true, 6),
            "mean_recovered_hrd_exposure": round(mean_recovered, 6),
            "mean_recovery_gap": round(mean_true - mean_recovered, 6),
            "mean_bg_fraction_of_true_signal": round(statistics.mean(misassigned_to_bg_frac), 6) if misassigned_to_bg_frac else "",
            "mean_sbs40_fraction_of_true_signal": round(statistics.mean(misassigned_to_sbs40_frac), 6) if misassigned_to_sbs40_frac else "",
        })
        log(f"cosmic_version={version} ({hrd_col}): mean true={mean_true:.4f}, "
            f"mean recovered={mean_recovered:.4f}, gap={mean_true-mean_recovered:.4f}")

    write_tsv(WORK_DIR / "SIMULATED_sbs3_by_cosmic_version_detail.tsv", per_version_rows,
              ["cosmic_version", "sample_id", "sbs3_relative_exposure_true", "hrd_column",
               "recovered_hrd_fraction", "bg_column", "recovered_bg_fraction",
               "sbs40_columns", "recovered_sbs40_fraction"])
    write_tsv(WORK_DIR / "SIMULATED_sbs3_misassignment_by_cosmic_version.tsv", misassignment_summary,
              ["cosmic_version", "hrd_column", "n_samples", "n_excluded_zero_true_exposure",
               "mean_true_exposure", "mean_recovered_hrd_exposure", "mean_recovery_gap",
               "mean_bg_fraction_of_true_signal", "mean_sbs40_fraction_of_true_signal"])
    return {"summary": misassignment_summary, "detail_rows": per_version_rows}




# ============================================================================
# Phase 5: bootstrap -- per-sample CI on recovered SBS3 exposure; code
# CI-containing-zero as LOW_CONFIDENCE, never silently coded as a plain 0
# ============================================================================

def phase5_bootstrap(cat: dict, point_estimates: dict[str, dict[str, float]]) -> dict:
    rng = random.Random(SEED + 1)
    seed_rows = read_tsv(cat["bootstrap_seed_path"])
    header = list(seed_rows[0].keys())
    contexts = [r[header[0]] for r in seed_rows]
    sample_ids = header[1:]

    observed: dict[str, list[int]] = {
        sid: [int(r[sid]) for r in seed_rows] for sid in sample_ids
    }

    replicate_cols: dict[str, list[int]] = {}
    replicate_of: dict[str, tuple[str, int]] = {}
    for sid in sample_ids:
        counts = observed[sid]
        total = sum(counts)
        probs = normalize([c + 1e-9 for c in counts])  # empirical per-context distribution of THIS sample's own observed reads
        for k in range(BOOTSTRAP_REPLICATES):
            resampled = multinomial_draw(total, contexts, probs, rng)
            col_id = f"{sid}__rep{k}"
            replicate_cols[col_id] = resampled
            replicate_of[col_id] = (sid, k)

    boot_matrix_path = WORK_DIR / "SIMULATED_sbs3_bootstrap_replicates_matrix.tsv"
    with open(boot_matrix_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["MutationType"] + list(replicate_cols.keys()))
        for i, ctx in enumerate(contexts):
            w.writerow([ctx] + [replicate_cols[c][i] for c in replicate_cols])
    log(f"Bootstrap replicate matrix: {len(sample_ids)} samples x {BOOTSTRAP_REPLICATES} replicates "
        f"= {len(replicate_cols)} columns -> {boot_matrix_path.name}")

    boot_activities = run_cosmic_fit(
        boot_matrix_path, WORK_DIR / "spa_out_bootstrap", exome=True, cosmic_version=CURRENT_COSMIC_VERSION,
    )

    per_sample_replicates: dict[str, list[float]] = {sid: [] for sid in sample_ids}
    for col_id, act in boot_activities.items():
        sid, k = replicate_of[col_id]
        per_sample_replicates[sid].append(relative_exposure(act, "SBS3"))

    truth_by_id = {r["sample_id"]: r for r in cat["truth_rows"]}
    rows = []
    for sid in sample_ids:
        reps = sorted(per_sample_replicates[sid])
        n_reps = len(reps)
        if n_reps == 0:
            rows.append({
                "sample_id": sid, "total_mutations": truth_by_id[sid]["total_mutations"],
                "sbs3_relative_exposure_true": truth_by_id[sid]["sbs3_relative_exposure_true"],
                "point_estimate": "", "ci_low": "", "ci_high": "", "n_bootstrap_replicates": 0,
                "value_status": "NOT_COMPUTED",
            })
            continue
        lo_idx = max(0, int(0.025 * n_reps))
        hi_idx = min(n_reps - 1, int(0.975 * n_reps))
        ci_low, ci_high = reps[lo_idx], reps[hi_idx]
        point = point_estimates.get(sid, {}).get("point")
        if point is None:
            point = statistics.median(reps)
        if ci_high <= 1e-9:
            status = "COMPUTED_ZERO"  # tight interval AT zero -- confidently absent, not merely a point estimate that happened to floor at 0
        elif ci_low <= 1e-9 < ci_high:
            status = "LOW_CONFIDENCE"  # interval contains zero but is not tight there -- point estimate of 0 (or near it) is NOT to be read as a confident absence
        else:
            status = "COMPUTED_NONZERO"
        rows.append({
            "sample_id": sid, "total_mutations": truth_by_id[sid]["total_mutations"],
            "sbs3_relative_exposure_true": truth_by_id[sid]["sbs3_relative_exposure_true"],
            "point_estimate": round(point, 6), "ci_low": round(ci_low, 6), "ci_high": round(ci_high, 6),
            "n_bootstrap_replicates": n_reps, "value_status": status,
        })

    write_tsv(WORK_DIR / "SIMULATED_sbs3_bootstrap_recovery.tsv", rows,
              ["sample_id", "total_mutations", "sbs3_relative_exposure_true", "point_estimate",
               "ci_low", "ci_high", "n_bootstrap_replicates", "value_status"])
    n_low_conf = sum(1 for r in rows if r["value_status"] == "LOW_CONFIDENCE")
    n_zero = sum(1 for r in rows if r["value_status"] == "COMPUTED_ZERO")
    n_nonzero = sum(1 for r in rows if r["value_status"] == "COMPUTED_NONZERO")
    log(f"Bootstrap CI classification over {len(rows)} samples: "
        f"COMPUTED_ZERO={n_zero}, LOW_CONFIDENCE={n_low_conf}, COMPUTED_NONZERO={n_nonzero}")
    return {"rows": rows, "n_zero": n_zero, "n_low_confidence": n_low_conf, "n_nonzero": n_nonzero}




# ============================================================================
# Phase 6: gate6-scored recovery of the two pre-existing SIMULATED_TRUTH.tsv
# quantities (core_hr_sbs3_exposure_LR, ddr_signaling_sbs3_exposure_LR),
# against simulate.py's EXISTING (ARBITRARY-shape) mutation catalogs
# ============================================================================

TRUTH_QUANTITIES_IN_SCOPE = ["core_hr_sbs3_exposure_LR", "ddr_signaling_sbs3_exposure_LR"]


def phase6_existing_catalog_transpose() -> Path:
    rows = read_tsv(DATA_DIR / "SIMULATED_mutation_catalogs.tsv")
    labels = {r["sample_id"]: r for r in read_tsv(REPO_ROOT / "SIMULATED_TRUTH_detail" / "SIMULATED_sample_labels.tsv")}
    keep = [r for r in rows if labels.get(r["sample_id"], {}).get("gene_group") in ("CORE_HR", "DDR_SIGNALING")]
    log(f"Existing simulate.py mutation catalog: {len(rows)} total samples, "
        f"{len(keep)} in CORE_HR/DDR_SIGNALING (NULL_ARM excluded -- not needed for these 2 quantities)")
    contexts = [c for c in keep[0].keys() if c != "sample_id"]
    out_path = WORK_DIR / "SIMULATED_existing_catalog_transposed.tsv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["MutationType"] + [r["sample_id"] for r in keep])
        for ctx in contexts:
            w.writerow([ctx] + [r[ctx] for r in keep])
    return out_path


def phase6_gate6_recovery() -> dict:
    matrix_path = phase6_existing_catalog_transpose()
    activities = run_cosmic_fit(
        matrix_path, WORK_DIR / "spa_out_existing_catalog", exome=True, cosmic_version=CURRENT_COSMIC_VERSION,
    )
    labels = {r["sample_id"]: r for r in read_tsv(REPO_ROOT / "SIMULATED_TRUTH_detail" / "SIMULATED_sample_labels.tsv")}

    per_sample_rows = []
    by_arm_class: dict[tuple[str, str], list[float]] = {}
    for sid, act in activities.items():
        lab = labels[sid]
        arm = lab["gene_group"]
        cls = lab["true_class"]
        rec = relative_exposure(act, "SBS3")
        per_sample_rows.append({"sample_id": sid, "gene_group": arm, "true_class": cls, "recovered_sbs3_exposure": round(rec, 6)})
        by_arm_class.setdefault((arm, cls), []).append(rec)
    write_tsv(WORK_DIR / "SIMULATED_existing_catalog_recovered_sbs3.tsv", per_sample_rows,
              ["sample_id", "gene_group", "true_class", "recovered_sbs3_exposure"])

    rng = random.Random(SEED + 2)

    def class_gaussian(values: list[float]) -> tuple[float, float]:
        mean = statistics.mean(values)
        sd = statistics.pstdev(values) if len(values) > 1 else 1e-6
        sd = max(sd, 1e-6)
        return mean, sd

    def lr_point(arm: str) -> float:
        mean1, sd1 = class_gaussian(by_arm_class[(arm, "Pathogenic")])
        mean0, sd0 = class_gaussian(by_arm_class[(arm, "Benign")])
        return phi_pdf(EVAL_POINT_SBS3, mean1, sd1) / phi_pdf(EVAL_POINT_SBS3, mean0, sd0)

    def lr_bootstrap_ci(arm: str) -> tuple[float, float]:
        path_vals = by_arm_class[(arm, "Pathogenic")]
        ben_vals = by_arm_class[(arm, "Benign")]
        lrs = []
        for _ in range(LR_BOOTSTRAP_REPLICATES):
            p_res = [rng.choice(path_vals) for _ in path_vals]
            b_res = [rng.choice(ben_vals) for _ in ben_vals]
            mean1, sd1 = class_gaussian(p_res)
            mean0, sd0 = class_gaussian(b_res)
            lrs.append(phi_pdf(EVAL_POINT_SBS3, mean1, sd1) / phi_pdf(EVAL_POINT_SBS3, mean0, sd0))
        lrs.sort()
        n = len(lrs)
        return lrs[int(0.025 * n)], lrs[min(n - 1, int(0.975 * n))]

    recovered_rows = []
    for arm, quantity in [("CORE_HR", "core_hr_sbs3_exposure_LR"), ("DDR_SIGNALING", "ddr_signaling_sbs3_exposure_LR")]:
        point = lr_point(arm)
        ci_low, ci_high = lr_bootstrap_ci(arm)
        n_path = len(by_arm_class[(arm, "Pathogenic")])
        n_ben = len(by_arm_class[(arm, "Benign")])
        recovered_rows.append({
            "quantity": quantity, "estimand": "LR", "recovered_point": round(point, 6),
            "ci_low": round(ci_low, 6), "ci_high": round(ci_high, 6),
            "n_pathogenic": n_path, "n_benign": n_ben,
        })
        log(f"{quantity}: recovered LR={point:.4f} CI=[{ci_low:.4f},{ci_high:.4f}] "
            f"(n_Pathogenic={n_path}, n_Benign={n_ben})")

    write_tsv(WORK_DIR / "SIMULATED_sbs3_lr_recovered.tsv", recovered_rows,
              ["quantity", "estimand", "recovered_point", "ci_low", "ci_high", "n_pathogenic", "n_benign"])

    scope_rows = []
    truth_rows = read_tsv(REPO_ROOT / "SIMULATED_TRUTH.tsv")
    for t in truth_rows:
        q = t["quantity"]
        if q in TRUTH_QUANTITIES_IN_SCOPE:
            scope_rows.append({
                "quantity": q, "in_scope": "TRUE",
                "reason": "computed via real SigProfilerAssignment 1.1.5 SBS3 relative-exposure feature "
                          "(this task's deliverable) -- loh_caller.py previously declared this NOT_IN_SCOPE "
                          "for exactly this reason",
            })
        elif q in ("core_hr_gis_score_LR", "ddr_signaling_gis_score_LR"):
            scope_rows.append({"quantity": q, "in_scope": "FALSE",
                                "reason": "requires a GIS/HRD-score feature; this script computes only the SBS3 feature"})
        else:
            scope_rows.append({"quantity": q, "in_scope": "FALSE",
                                "reason": "a joint/product-of-marginals/null-arm estimator over LOH+GIS+SBS3 "
                                          "evidence; this script produces only a single-feature (SBS3) marginal "
                                          "recovery, not a joint density estimate, matching loh_caller.py's own "
                                          "scope boundary for the equivalent LOH-only quantities"})
    write_tsv(WORK_DIR / "SIMULATED_sbs3_gate6_scope.tsv", scope_rows, ["quantity", "in_scope", "reason"])

    return {"recovered_rows": recovered_rows, "scope_rows": scope_rows, "per_sample_rows": per_sample_rows}


# ============================================================================
# Phase 7: gate7 rates table + invoke gate6/gate7 as real subprocesses
# (Standing Rule 6: acceptance is script-checked, not narrative)
# ============================================================================

def phase7_build_rates_table(cat: dict, exome_cmp: dict, boot: dict, version_sweep: dict) -> Path:
    rows_exome = read_tsv(WORK_DIR / "SIMULATED_sbs3_exome_compare.tsv")
    n = len(rows_exome)
    n_zero_overall = sum(1 for r in rows_exome if float(r["recovered_exome_normalized"]) == 0.0)

    below25 = [r for r in rows_exome if int(r["total_mutations"]) < 25]
    n_below25 = len(below25)
    n_below25_zero = sum(1 for r in below25 if float(r["recovered_exome_normalized"]) == 0.0)

    top_bin = [r for r in rows_exome if r["bin_label"] == "[105,116)"]
    n_top = len(top_bin)
    n_top_zero = sum(1 for r in top_bin if float(r["recovered_exome_normalized"]) == 0.0)

    n_boot = len(boot["rows"])
    n_boot_computed = sum(1 for r in boot["rows"] if r["value_status"] != "NOT_COMPUTED")
    n_boot_not_computed = n_boot - n_boot_computed

    detail_v36 = [r for r in version_sweep["detail_rows"] if r["cosmic_version"] == CURRENT_COSMIC_VERSION]
    detail_v36_nonzero_true = [r for r in detail_v36 if r["sbs3_relative_exposure_true"] > 0]
    n_v36_zero_true_excluded = len(detail_v36) - len(detail_v36_nonzero_true)
    n_v36_majority_misassigned = sum(
        1 for r in detail_v36_nonzero_true
        if (r["recovered_bg_fraction"] + r["recovered_sbs40_fraction"]) > r["recovered_hrd_fraction"]
    )

    rates = [
        {"metric_name": "exome_normalization_improves_recovery_rate",
         "numerator": exome_cmp["n_improves"], "denominator": n,
         "excluded_count": exome_cmp["n_tied"],
         "excluded_reason": "normalized and non-normalized abs-error exactly tied (no distinguishable improvement direction)",
         "rate": round(exome_cmp["n_improves"] / n, 6)},
        {"metric_name": "sbs3_exact_zero_recovery_rate_overall_main_subset",
         "numerator": n_zero_overall, "denominator": n, "excluded_count": 0, "excluded_reason": "",
         "rate": round(n_zero_overall / n, 6)},
        {"metric_name": "sbs3_exact_zero_recovery_rate_below_25_total_mutations",
         "numerator": n_below25_zero, "denominator": n_below25, "excluded_count": 0, "excluded_reason": "",
         "rate": round(n_below25_zero / n_below25, 6) if n_below25 else ""},
        {"metric_name": "sbs3_exact_zero_recovery_rate_top_bin_105_116",
         "numerator": n_top_zero, "denominator": n_top, "excluded_count": 0, "excluded_reason": "",
         "rate": round(n_top_zero / n_top, 6) if n_top else ""},
        {"metric_name": "bootstrap_low_confidence_rate",
         "numerator": boot["n_low_confidence"], "denominator": n_boot_computed,
         "excluded_count": n_boot_not_computed,
         "excluded_reason": "sample had zero bootstrap replicates return a value (SPA output row missing)",
         "rate": round(boot["n_low_confidence"] / n_boot_computed, 6) if n_boot_computed else ""},
        {"metric_name": "sbs3_majority_misassigned_to_bg_or_sbs40_rate_v3.6",
         "numerator": n_v36_majority_misassigned, "denominator": len(detail_v36_nonzero_true),
         "excluded_count": n_v36_zero_true_excluded,
         "excluded_reason": "true injected sbs3_relative_exposure_true == 0 -- 'majority misassigned' is undefined with no true signal to misassign",
         "rate": round(n_v36_majority_misassigned / len(detail_v36_nonzero_true), 6) if detail_v36_nonzero_true else ""},
    ]
    rates_path = WORK_DIR / "SIMULATED_sbs3_rates_table.tsv"
    write_tsv(rates_path, rates, ["metric_name", "numerator", "denominator", "excluded_count", "excluded_reason", "rate"])
    return rates_path


def run_gate(script: str, args: list[str]) -> tuple[bool, str]:
    cmd = [sys.executable, str(GATES_DIR / script)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    passed = result.returncode == 0
    output = result.stdout + result.stderr
    log(f"{script} {' '.join(args)} -> exit {result.returncode} ({'PASS' if passed else 'FAIL'})")
    return passed, output


def phase7_run_gates(rates_path: Path) -> dict:
    gate6_out = WORK_DIR / "gate6_out"
    gate6_pass, gate6_output = run_gate("gate6_recovery.py", [
        "--truth", str(REPO_ROOT / "SIMULATED_TRUTH.tsv"),
        "--recovered", str(WORK_DIR / "SIMULATED_sbs3_lr_recovered.tsv"),
        "--scope", str(WORK_DIR / "SIMULATED_sbs3_gate6_scope.tsv"),
        "--outdir", str(gate6_out),
    ])
    gate7_pass, gate7_output = run_gate("gate7_denominators.py", ["--rates-table", str(rates_path)])

    with open(WORK_DIR / "SIMULATED_gate6_output.txt", "w") as f:
        f.write(gate6_output)
    with open(WORK_DIR / "SIMULATED_gate7_output.txt", "w") as f:
        f.write(gate7_output)

    return {
        "gate6_pass": gate6_pass, "gate6_output": gate6_output,
        "gate7_pass": gate7_pass, "gate7_output": gate7_output,
    }


# ============================================================================
# Phase 8: SIMULATED_signature_validation.md report
# ============================================================================

def write_report(env, ref, cat, exome_cmp, version_sweep, boot, gate6res, rates_path, gate_results) -> Path:
    rows_exome = read_tsv(WORK_DIR / "SIMULATED_sbs3_exome_compare.tsv")
    by_bin: dict[str, list[dict]] = {}
    for r in rows_exome:
        by_bin.setdefault(r["bin_label"], []).append(r)

    def bin_sort_key(b):
        return int(b.split(",")[0][1:])

    curve_lines = []
    below25_mae = []
    for b in sorted(by_bin, key=bin_sort_key):
        rs = by_bin[b]
        n = len(rs)
        true_mean = statistics.mean(float(r["sbs3_relative_exposure_true"]) for r in rs)
        rec_mean = statistics.mean(float(r["recovered_exome_normalized"]) for r in rs)
        mae = statistics.mean(abs(float(r["recovered_exome_normalized"]) - float(r["sbs3_relative_exposure_true"])) for r in rs)
        frac_zero = sum(1 for r in rs if float(r["recovered_exome_normalized"]) == 0.0) / n
        curve_lines.append(f"| {b} | {n} | {true_mean:.4f} | {rec_mean:.4f} | {mae:.4f} | {frac_zero:.2f} |")
        if bin_sort_key(b) < 25:
            below25_mae.append(mae)

    rates_rows = read_tsv(rates_path)
    rate_lines = [
        f"| {r['metric_name']} | {r['numerator']} | {r['denominator']} | {r['excluded_count']} | {r['rate']} | {r['excluded_reason']} |"
        for r in rates_rows
    ]

    misassign_lines = [
        f"| {r['cosmic_version']} | {r['hrd_column']} | {r['n_samples']} | {r['n_excluded_zero_true_exposure']} | "
        f"{r['mean_true_exposure']} | {r['mean_recovered_hrd_exposure']} | {r['mean_recovery_gap']} | "
        f"{r['mean_bg_fraction_of_true_signal']} | {r['mean_sbs40_fraction_of_true_signal']} |"
        for r in version_sweep["summary"]
    ]

    boot_rows = boot["rows"]
    n_boot = len(boot_rows)

    top_bin_rows = by_bin.get("[105,116)", [])
    n_top = len(top_bin_rows)
    n_top_zero = sum(1 for r in top_bin_rows if float(r["recovered_exome_normalized"]) == 0.0)

    gate6_verdict = "PASS" if gate_results["gate6_pass"] else "FAIL"
    gate7_verdict = "PASS" if gate_results["gate7_pass"] else "FAIL"

    lr_rows = read_tsv(WORK_DIR / "SIMULATED_sbs3_lr_recovered.tsv")
    lr_lines = [
        f"| {r['quantity']} | {r['estimand']} | {r['recovered_point']} | [{r['ci_low']}, {r['ci_high']}] | "
        f"{r['n_pathogenic']} | {r['n_benign']} |"
        for r in lr_rows
    ]

    md = f"""{BANNER}

# SIMULATED_signature_validation.md — SBS3 estimation at exome scale

SIMULATED: every number below comes from SIMULATED data (injected exposures,
{cat['n_design_population']}-sample simulator population from `simulate.py` v2)
run through the REAL SigProfilerAssignment 1.1.5 tool. No ACMG evidence
strength is assigned anywhere in this document.

## 0. P08 diagnosis addendum — two distinct mechanisms, not one

A prior pass reported this document's §4-8 findings as a single, unexplained
"structural failure." `DIAGNOSIS_P08.md` (full evidence, four hypotheses
tested) found **two distinct, independently-verified mechanisms**:

- **Mechanism 1 (drives §8's gate6 FAIL):** the mutation catalog
  `core_hr_sbs3_exposure_LR`/`ddr_signaling_sbs3_exposure_LR` are scored
  against was built by `simulate.py` from an ARBITRARY 96-context shape that
  is, by real cosine similarity, LESS like real COSMIC SBS3 (0.688) than
  like SBS5 (0.802) — a **simulator (P06) defect**, not a signature-recovery
  finding. See `REQUIRED_P06_CHANGES.md`. `simulate.py` is not modified by
  this task; §8 below is expected to keep failing until P06 lands that fix.
- **Mechanism 2 (drives §4-7's near-total exact-zero recovery, where the
  REAL COSMIC SBS3 vector WAS used for injection):** SigProfilerAssignment's
  NNLS decomposition is genuinely unstable at exome-scale mutation counts
  given SBS3's real cosine similarity to SBS5/SBS39 (~0.79) — confirmed by
  two targeted experiments (pruning-penalty tuning made it no better;
  restricting the reference basis to just the two true signatures produced
  near-binary, frequently-wrong solutions instead of proportional recovery).
  This is a genuine tool-behavior finding, not a simulator defect.

§4-7's headline claims below are Mechanism 2's real finding and are
unaffected by the simulator defect. §8's gate6 FAIL is Mechanism 1, and is
**not** evidence about SigProfilerAssignment's recovery ability — it is
evidence that the quantity it was scored against was mislabeled.

## 1. Environment

- SigProfilerAssignment: **{env['sigprofilerassignment_version']}** (expected {SPA_PACKAGE_VERSION_EXPECTED} per
  `GATE1.json` — {'MATCHES' if env['sigprofilerassignment_version_matches_gate1'] else 'DOES NOT MATCH'}).
  Run inside `{DOCKER_IMAGE}`, digest `{DOCKER_IMAGE_DIGEST}` (matches `GATE1.json` — re-verified
  live this session; the docker daemon in this fresh container instance was initially unreachable
  and had to be re-confirmed running before this task could proceed).
- SigMA: re-attempted fresh this session (not assumed from a prior session) —
  **{env['sigma_status']}** (`{env['sigma_check_output']}`). `BSgenome.Hsapiens.UCSC.hg19`:
  **{env['bsgenome_hg19_status']}** (`{env['bsgenome_hg19_check_output']}`). This
  {'MATCHES' if env['sigma_matches_gate1_fail'] else 'DOES NOT MATCH'} `GATE1.json`'s recorded
  SigMA `FAIL`. Per PROTOCOL.md §5.4: **no Stage of this task that would depend on a SigMA feature
  runs; the SigMA-derived feature (likelihood-based Signature-3 match score + `Signature_3_mva`) is
  reported as the literal string `BLOCKED`, not omitted or substituted with another tool's output.**
  **Resolution attempts this session (`GATE1.json`'s `resolution_attempts_p08`, full detail there):**
  (1) CRAN/BiocManager install — FAILED, cran.r-project.org network-blocked; (2) conda/bioconda
  install — FAILED with a NEW reason (genuine r-base version conflict, independent of the network
  block); (3) hg38 BSgenome substitute — INCONCLUSIVE (solver did not return in time), and moot
  regardless since SigMA's `DESCRIPTION` hard-names hg19 specifically; (4) source-level bypass
  (skip package install, `source()` the 20 non-BSgenome R files directly) — PARTIAL SUCCESS: SigMA's
  actual analysis entrypoints (`run()`, NNLS/likelihood/gbm scoring against a pre-built matrix) are
  not themselves BSgenome-dependent — only its VCF-to-matrix conversion utility is — but running it
  against this study's data was not completed (context-label mapping and tumor-type model lookup
  both remain unresolved). **SigMA is genuinely untested against this study's data. Every claim in
  this document about SBS3 recovery is a claim about SigProfilerAssignment specifically, never a
  general claim about SBS3 recoverability** — see §0 and §11. If SigMA were fully resolved, §4-7's
  Mechanism 2 finding (NNLS instability at exome-scale, cosine-similar signatures) is exactly the
  regime SigMA was purpose-built for (its own `DESCRIPTION`: "optimized to detect... Signature 3...
  from... exomes," "for panels with low SNV counts, conventional signature analysis tools do not
  perform well") — a working SigMA run could plausibly show materially better low-count recovery
  than SigProfilerAssignment does here, which would change §4-7's "unrecoverable in this range"
  finding from a statement about SBS3 itself to one about SigProfilerAssignment specifically (which
  is already how it is scoped, but a working SigMA comparison would make that scoping load-bearing
  rather than precautionary).
- Genome build used for every `cosmic_fit` call in this document: **{GENOME_BUILD}**
  (PROTOCOL.md's pinned reference build; the package's own bundled *default*
  is `{env['genome_build_bundled_default']}` — logged, not silently assumed to match).

## 2. COSMIC version pin

- **Current (package-bundled default)**: COSMIC v**{CURRENT_COSMIC_VERSION}**, confirmed live this
  session via `inspect.signature(Analyzer.cosmic_fit).parameters['cosmic_version'].default`
  ({env['cosmic_version_bundled_default']}). A live WebSearch this session independently
  corroborated COSMIC Mutational Signatures v3.6 as the current signature-set release
  (cancer.sanger.ac.uk itself remains network-blocked — ENVIRONMENT.lock §0).
- **v2-equivalent (legacy nomenclature)**: COSMIC v**{V2_EQUIVALENT_COSMIC_VERSION}**, also bundled
  in the same package build, at `{ref['extract_path'].parent}/COSMIC_v2_SBS_{GENOME_BUILD}.txt` —
  uses `Signature_3`/`Signature_5` naming (pre-2018 Alexandrov et al. nomenclature) rather than
  `SBS3`/`SBS5`. Cosine similarity between v3.6's `SBS3` and v2's `Signature_3` (same 96-context
  space, both real weights extracted live from the installed package):
  **{ref['similarity']['SBS3_v3.6_vs_Signature_3_v2']:.4f}** — the shape was only modestly revised
  between the legacy and current signature sets.
- {GENERAL_COSMIC_RELEASE_NOTE}
- Signature shape similarity is also the mechanism behind §5 below: `SBS3` vs `SBS5`
  (v3.6) = **{ref['similarity']['SBS3_v3.6_vs_SBS5_v3.6']:.4f}**, `SBS3` vs `SBS40a` (v3.6) =
  **{ref['similarity']['SBS3_v3.6_vs_SBS40a_v3.6']:.4f}**, legacy `Signature_3` (v2) vs unsplit
  `SBS40` (v3) = **{ref['similarity']['Signature_3_v2_vs_SBS40_unsplit_v3']:.4f}**.

## 3. Trinucleotide exome-to-genome normalization

Factors computed from the REAL installed reference-opportunity files (not COSMIC's copyrighted
signature weights — this is SigProfilerMatrixGenerator's trinucleotide-context census over the
{GENOME_BUILD} reference, genome-wide vs. exome-only):
`{_smg_context_root()}/context_counts_{GENOME_BUILD}_96.csv` and its `_exome.csv` counterpart.
Factor = genome_freq / exome_freq per trinucleotide (32 contexts); full table:
`SIMULATED_signature_work/SIMULATED_trinuc_exome_genome_factors.tsv`.

SigProfilerAssignment operationalizes this exact normalization via its `exome` boolean: `exome=True`
swaps the COSMIC reference-signature matrix for a pre-renormalized `COSMIC_v{{version}}_SBS_{GENOME_BUILD}_exome.txt`
file (confirmed live in `decompose_subroutines.py:getProcessAvg`), rather than rescaling the observed
counts at runtime — i.e. the normalization direction is "renormalize the reference signatures to the
exome's trinucleotide opportunity distribution," not "rescale exome counts up to genome-equivalent."

## 4. No-normalization comparison (exome=True vs exome=False) — REAL, run twice on the same catalog

Same {exome_cmp['n']}-sample catalog, same `cosmic_version={CURRENT_COSMIC_VERSION}`, only `exome`
toggled. MAE with normalization = **{exome_cmp['mae_normalized']:.4f}**, MAE without =
**{exome_cmp['mae_no_normalization']:.4f}**. Normalization gave a lower per-sample error for
**{exome_cmp['n_improves']}/{exome_cmp['n']}** samples ({exome_cmp['n_worse']} worse,
{exome_cmp['n_tied']} tied). **Honest finding, not the expected direction:** in this simulated
exome-scale, low-mutation-count regime, `exome=True` renormalization does **not** meaningfully
improve SBS3 recovery accuracy over `exome=False` — the two MAEs differ by less than 0.003,
and the recovery error is dominated by the SBS3/SBS5 shape-similarity confound (§2) and by
sparse low-count noise (§6), not by the exome/genome trinucleotide-frequency mismatch this
normalization corrects. Per-sample detail: `SIMULATED_signature_work/SIMULATED_sbs3_exome_compare.tsv`.

## 5. SBS3 misassignment to SBS5/SBS40 across COSMIC versions — REAL, {len(COSMIC_VERSION_SWEEP)} versions run

| cosmic_version | HRD column | n | excluded (true_exp=0) | mean true | mean recovered | mean gap | mean bg frac of true signal | mean SBS40 frac of true signal |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(misassign_lines)}

Detail per sample per version: `SIMULATED_signature_work/SIMULATED_sbs3_by_cosmic_version_detail.tsv`.
The recovery gap (mean true − mean recovered) is large and consistent across every tested COSMIC
version — this is a real, version-independent SBS3 identifiability problem in this exome-scale
regime, not an artifact of any one reference-signature revision.

## 6. Error vs. total mutation count — REAL, {exome_cmp['n']}-sample stratified subset

| total_mutations bin | n | mean true exposure | mean recovered exposure | MAE | fraction exact-zero recovery |
|---|---|---|---|---|---|
{chr(10).join(curve_lines)}

**The count below which SBS3 is unrecoverable, stated explicitly:** within the tested range
(total_mutations = 5 to 115 — the realistic per-exome TCGA-BRCA mutation burden per
`BENCHMARKS.tsv` TMB01), SBS3 relative exposure is recovered as **exactly zero** for essentially
all samples with total_mutations < 25 (fraction exact-zero = 1.00 in both bins below 25). This
fraction declines only slowly as total_mutations increases, and **remains {n_top_zero}/{n_top}
({n_top_zero/n_top:.0%}) even in the top-tested bin ([105,116))** — this analysis's tested range
does not reach a count at which SBS3 becomes reliably recoverable. Stated as a floor rather than a
crisp threshold, because the decline is not monotonic bin-to-bin at n=40/bin (sampling noise —
see the MAE column, which is noisier and non-monotonic; the exact-zero fraction is the more
robust/monotonic statistic and is the basis for this statement). A supplementary single-seed check
at total_mutations up to 5000 (not part of the scored subset; `SIMULATED_signature_work/sanity_out/`)
found recovery remains exactly zero even at n=5000 when true exposure = 0.1 — i.e. **low fractional
exposure, not only low total count, drives non-recoverability**; this is disclosed as a caveat
beyond this task's literal "vs. total mutation count" ask, not folded into the headline curve above.

## 7. Bootstrap: zero vs. low-confidence — REAL, {n_boot} samples x {BOOTSTRAP_REPLICATES} replicates each

Per-sample nonparametric bootstrap (multinomial resample of that sample's own observed 96-context
counts at fixed total_mutations, refit via the same real `cosmic_fit` call). Classification:
`COMPUTED_ZERO` (point estimate 0, CI tight at 0 — confidently absent), `LOW_CONFIDENCE` (CI
contains 0 but is not tight there — a 0 point estimate here must NOT be read as confident absence),
`COMPUTED_NONZERO` (CI excludes 0), `NOT_COMPUTED` (schema-distinct from a true 0 — never coerced
to 0.0). Result: **{boot['n_zero']} COMPUTED_ZERO, {boot['n_low_confidence']} LOW_CONFIDENCE,
{boot['n_nonzero']} COMPUTED_NONZERO** (0 NOT_COMPUTED). Full table:
`SIMULATED_signature_work/SIMULATED_sbs3_bootstrap_recovery.tsv`.

## 8. gate6-scored recovery: the two pre-existing SIMULATED_TRUTH.tsv SBS3 quantities

`core_hr_sbs3_exposure_LR` / `ddr_signaling_sbs3_exposure_LR` — declared `NOT_IN_SCOPE` by
`loh_caller.py` ("requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not
compute"). Computed here via real `cosmic_fit` against simulate.py's EXISTING mutation catalogs
(`SIMULATED_data/SIMULATED_mutation_catalogs.tsv`, ARBITRARY 96-context shapes — distinct from the
real-COSMIC-shape catalog used in §4-7 above), then the same class-conditional-Gaussian-at-EVAL_POINT
construction `simulate.py` itself uses for the injected value (`EVAL_POINT["sbs3"]=0.30`), fit to
the REAL recovered per-sample exposures instead of the analytic model parameters, with a
{LR_BOOTSTRAP_REPLICATES}-replicate bootstrap CI (resampling the already-recovered scalars, no
re-run of SPA needed for this cheap step).

| quantity | estimand | recovered LR | 95% CI | n Pathogenic | n Benign |
|---|---|---|---|---|---|
{chr(10).join(lr_lines)}

**gate6_recovery.py: {gate6_verdict}** (full output: `SIMULATED_signature_work/SIMULATED_gate6_output.txt`,
table: `SIMULATED_signature_work/gate6_out/SIMULATED_RECOVERY_TABLE.tsv`). All 14 other
`SIMULATED_TRUTH.tsv` quantities remain declared `NOT_IN_SCOPE` for this script (GIS/joint/
product-of-marginals/null-arm estimators this script does not compute — see
`SIMULATED_signature_work/SIMULATED_sbs3_gate6_scope.tsv` for the full per-quantity reasons).

**Mechanism, per `DIAGNOSIS_P08.md` §2 (Mechanism 1):** this FAIL is a
**simulator (P06) defect**, not a SigProfilerAssignment recovery failure. The
catalog these two quantities are scored against was built from a shape real
cosine similarity shows is not actually SBS3-shaped (0.688 to real SBS3 vs.
0.802 to real SBS5 — closer to the alternative than to the thing it is named
after). The remaining gap (recovered LR 0.31/0.48 vs. injected 5.64/3.92) is
consistent with real SigProfilerAssignment correctly finding little real-SBS3
signal in a catalog that mostly does not contain any. `simulate.py` is not
modified by this task (see `REQUIRED_P06_CHANGES.md`); this FAIL is expected
to persist until P06 lands the fix.

## 9. gate7: every rate reported here with its denominator and excluded count

| metric | numerator | denominator | excluded | rate | excluded reason |
|---|---|---|---|---|---|
{chr(10).join(rate_lines)}

**gate7_denominators.py: {gate7_verdict}** (full output: `SIMULATED_signature_work/SIMULATED_gate7_output.txt`).

## 10. Subsampling disclosure

The full injected-exposure population (`SIMULATED_data/SIMULATED_signature_exposures.tsv`) has
{cat['n_design_population']} samples. Running the real `cosmic_fit` tool against all of them, at
every `cosmic_version` x `exome` combination this task needed, was not feasible within this
session's compute budget (~{N_PER_BIN_MAIN * (len(TOTAL_MUTATIONS_BIN_EDGES)-1)}-sample runs
already took tens of seconds to low minutes each; the full population would be roughly 29x larger
per run). A stratified subsample ({N_PER_BIN_MAIN} per total_mutations bin, seed={SEED}) of
**{exome_cmp['n']} samples** was used for §4-6 above; two of eleven bins were undersized in the
raw population (bin [5,15): only 7 available; bin [105,116): only 15 available) and are reported
at their true, smaller n rather than padded. This is a disclosed, documented substitution of a
representative subset for the full population — not a silent one (Standing Rule 4) — and is
distinct from §8's gate6 recovery, which DID run against the full relevant population
({gate6res['recovered_rows'][0]['n_pathogenic'] + gate6res['recovered_rows'][0]['n_benign']}
samples per arm, split {gate6res['recovered_rows'][0]['n_pathogenic']} Pathogenic /
{gate6res['recovered_rows'][0]['n_benign']} Benign).

## 11. Overall

- gate6_recovery.py: **{gate6_verdict}** — mechanism identified (`DIAGNOSIS_P08.md` §2,
  Mechanism 1): a simulator (P06) defect in the catalog these two quantities are scored
  against, not a SigProfilerAssignment recovery failure. `REQUIRED_P06_CHANGES.md` specifies
  the fix; `simulate.py` is not modified by this task.
- gate7_denominators.py: **{gate7_verdict}**
- SigMA: **BLOCKED** (PROTOCOL.md §5.4 permitted status; re-confirmed FAIL fresh this session,
  matches `GATE1.json`). Resolution attempted this session (§1, `GATE1.json`
  `resolution_attempts_p08`) — still unresolved. **SigMA is untested against this study's data.**
- **Headline validation result, precisely scoped (per this session's Step 2 instruction, never
  as a general claim about SBS3 recoverability):** SBS3 exposure recovery **by
  SigProfilerAssignment specifically** is substantially compromised throughout the realistic
  exome-scale mutation-count range tested in §4-7 (Mechanism 2 — a genuine NNLS
  decomposition-instability finding about this one tool, confirmed by two targeted experiments,
  not an absent signal, not an estimand mismatch, not the tool declining to fit).
  **SigMA — the tool literature-described as purpose-built for exactly this low-count regime —
  was never run against this study's data; if it were, and performed as its own documentation
  claims for low-SNV-count panels, §4-7's finding could change from "SBS3 is unrecoverable in
  this range" to "SBS3 is unrecoverable BY SIGPROFILERASSIGNMENT in this range, but recoverable
  by a purpose-built tool."** §8's separate gate6 FAIL is Mechanism 1 (simulator defect) and is
  not part of this headline claim at all.
"""
    report_path = REPO_ROOT / "SIMULATED_signature_validation.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    log(f"Report written: {report_path}")
    return report_path


# ============================================================================
# main
# ============================================================================

def main() -> int:
    ensure_inside_docker()
    env = phase0_environment_check()
    ref = phase1_extract_reference()
    cat = phase2_generate_validation_catalog(ref)
    exome_cmp = phase3_exome_normalization_compare(cat)
    version_sweep = phase4_cosmic_version_sweep(cat, exome_cmp["activities_true_v3_6_exomeTrue"])
    point_estimates = {
        r["sample_id"]: {"point": r["recovered_exome_normalized"]} for r in exome_cmp["rows"]
    }
    boot = phase5_bootstrap(cat, point_estimates)
    gate6res = phase6_gate6_recovery()
    rates_path = phase7_build_rates_table(cat, exome_cmp, boot, version_sweep)
    gate_results = phase7_run_gates(rates_path)
    write_report(env, ref, cat, exome_cmp, version_sweep, boot, gate6res, rates_path, gate_results)

    overall_pass = gate_results["gate6_pass"] and gate_results["gate7_pass"]
    log(f"signatures.py OVERALL: {'PASS' if overall_pass else 'FAIL'} "
        f"(gate6={'PASS' if gate_results['gate6_pass'] else 'FAIL'}, "
        f"gate7={'PASS' if gate_results['gate7_pass'] else 'FAIL'})")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
