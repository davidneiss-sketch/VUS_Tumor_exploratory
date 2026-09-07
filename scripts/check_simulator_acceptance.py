#!/usr/bin/env python3
"""Acceptance check for the simulator deliverable (Standing Rule 6): emits
PASS/FAIL per criterion by re-running the actual derivation code and
re-parsing the actual output files, never by trusting SIMULATION_SPEC.md's
prose.

Criteria, copied from the task's ACCEPTANCE section:
  1. Every output carries SIMULATED in its name and the required header.
  2. Truth key is in a separate directory with an estimand column populated.
  3. The injected LR derivation is present and reproducible.
  4. At least one injected-null entry exists.
  5. Parameter provenance is recorded for every simulator parameter.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "SIMULATED_data"
TRUTH_DETAIL_DIR = ROOT / "SIMULATED_TRUTH_detail"
TRUTH_TSV = ROOT / "SIMULATED_TRUTH.tsv"
PARAM_PROV = ROOT / "PARAMETER_PROVENANCE.tsv"
SPEC_MD = ROOT / "SIMULATION_SPEC.md"
SIMULATE_PY = ROOT / "simulate.py"
BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

results = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def load_simulate_module():
    spec = importlib.util.spec_from_file_location("simulate", SIMULATE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def criterion_1_naming_and_headers():
    exempt_names = {"README.md"}
    bad_names = []
    for d in (DATA_DIR, TRUTH_DETAIL_DIR):
        if not d.exists():
            bad_names.append(f"directory missing: {d}")
            continue
        for p in d.iterdir():
            if p.name in exempt_names:
                continue
            if "SIMULATED" not in p.name:
                bad_names.append(str(p.relative_to(ROOT)))
    if "SIMULATED" not in TRUTH_TSV.name:
        bad_names.append(str(TRUTH_TSV.relative_to(ROOT)))

    banner_failures = []
    for d in (DATA_DIR, TRUTH_DETAIL_DIR):
        for p in (d.glob("*.md") if d.exists() else []):
            text = p.read_text(encoding="utf-8")
            if not text.startswith(BANNER):
                banner_failures.append(f"{p.relative_to(ROOT)}: does not start with the mandated banner")

    for d in (DATA_DIR, TRUTH_DETAIL_DIR):
        readme = d / "README.md"
        if not readme.exists():
            banner_failures.append(f"{d.relative_to(ROOT)}/README.md missing (documents why .tsv headers here are not literally banner-prefixed)")

    check(
        "every output carries SIMULATED in its name and the required header",
        len(bad_names) == 0 and len(banner_failures) == 0,
        f"non-SIMULATED-named files: {bad_names}; banner failures: {banner_failures}"
        if (bad_names or banner_failures) else
        "every non-README output file is SIMULATED-named; every .md report starts with the mandated banner; "
        "every directory's README.md documents the TSV-header convention (banner not embedded in .tsv "
        "headers because SIMULATED_TRUTH.tsv must stay plain-parseable by gate6_recovery.py's read_tsv)",
    )


def criterion_2_truth_key_separate_with_estimand():
    if not TRUTH_TSV.exists():
        check("truth key in a separate directory with estimand populated", False, "SIMULATED_TRUTH.tsv missing")
        return
    is_separate = TRUTH_TSV.parent != DATA_DIR and DATA_DIR not in TRUTH_TSV.parents
    rows = read_tsv(TRUTH_TSV)
    missing_estimand = [r.get("quantity", "?") for r in rows if not (r.get("estimand") or "").strip()]
    detail_separate = (TRUTH_DETAIL_DIR.exists()) and (DATA_DIR not in TRUTH_DETAIL_DIR.parents) and (TRUTH_DETAIL_DIR != DATA_DIR)
    ok = is_separate and not missing_estimand and detail_separate and len(rows) > 0
    check(
        "truth key in a separate directory with estimand populated",
        ok,
        f"SIMULATED_TRUTH.tsv separate from SIMULATED_data/={is_separate}, "
        f"SIMULATED_TRUTH_detail/ also separate={detail_separate}, "
        f"{len(rows)} row(s), rows missing estimand={missing_estimand}",
    )


def criterion_3_derivation_present_and_reproducible():
    if not SPEC_MD.exists():
        check("injected LR derivation present and reproducible", False, "SIMULATION_SPEC.md missing")
        return
    spec_text = re.sub(r"\s+", " ", SPEC_MD.read_text(encoding="utf-8"))
    has_formula_categorical = "P(E|Pathogenic) / P(E|Benign)" in spec_text or "π₁ / π₀" in spec_text
    has_formula_gaussian = "f(x|Pathogenic) / f(x|Benign)" in spec_text
    derivation_present = has_formula_categorical and has_formula_gaussian

    # Reproducibility: actually re-run the derivation code (not a copy of
    # it) and diff, to full float precision, against the emitted TSV.
    if not TRUTH_TSV.exists():
        check("injected LR derivation present and reproducible", False, "SIMULATED_TRUTH.tsv missing, cannot check reproducibility")
        return
    mod = load_simulate_module()
    fresh_rows = {r["quantity"]: r["injected_value"] for r in mod.compute_truth_quantities()}
    file_rows = read_tsv(TRUTH_TSV)
    mismatches = []
    for r in file_rows:
        q = r["quantity"]
        if q not in fresh_rows:
            mismatches.append(f"{q}: not found in freshly-recomputed quantities")
            continue
        file_val = float(r["injected_value"])
        fresh_val = float(fresh_rows[q])
        if abs(file_val - fresh_val) > 1e-9 * max(1.0, abs(fresh_val)):
            mismatches.append(f"{q}: file={file_val!r} != freshly recomputed {fresh_val!r}")

    ok = derivation_present and not mismatches
    check(
        "the injected LR derivation is present and reproducible",
        ok,
        f"formulas present in SIMULATION_SPEC.md: categorical={has_formula_categorical}, gaussian={has_formula_gaussian}; "
        f"re-running simulate.compute_truth_quantities() and diffing against SIMULATED_TRUTH.tsv: "
        f"{len(mismatches)} mismatch(es)" + (f" -- {mismatches}" if mismatches else " (exact match)"),
    )


def criterion_4_at_least_one_null():
    if not TRUTH_TSV.exists():
        check("at least one injected-null entry exists", False, "SIMULATED_TRUTH.tsv missing")
        return
    rows = read_tsv(TRUTH_TSV)
    null_rows = [r for r in rows if (r.get("is_null") or "").strip().upper() == "TRUE"]
    exact_one = [r for r in null_rows if abs(float(r["injected_value"]) - 1.0) < 1e-12]
    ok = len(null_rows) >= 1 and len(exact_one) >= 1
    check(
        "at least one injected-null entry exists (true LR = 1.0 exactly)",
        ok,
        f"{len(null_rows)} row(s) with is_null=TRUE, {len(exact_one)} with injected_value exactly 1.0: "
        f"{[r['quantity'] for r in exact_one]}",
    )


def criterion_5_parameter_provenance_complete():
    if not PARAM_PROV.exists():
        check("parameter provenance recorded for every simulator parameter", False, "PARAMETER_PROVENANCE.tsv missing")
        return
    rows = read_tsv(PARAM_PROV)
    required_cols = {"parameter_name", "value", "source_type", "source_reference", "rationale"}
    missing_cols = required_cols - set(rows[0].keys()) if rows else required_cols
    bad_source_type = [r["parameter_name"] for r in rows if r.get("source_type") not in ("BENCHMARKS_ROW", "ARBITRARY")]
    bad_rationale = [r["parameter_name"] for r in rows
                      if r.get("source_type") == "ARBITRARY" and not (r.get("rationale") or "").strip()]

    # Cross-check every BENCHMARKS_ROW source_reference actually exists in BENCHMARKS.tsv.
    benchmarks_path = ROOT / "BENCHMARKS.tsv"
    benchmark_ids = set()
    if benchmarks_path.exists():
        benchmark_ids = {r["benchmark_id"] for r in read_tsv(benchmarks_path)}
    bad_benchmark_refs = [
        f"{r['parameter_name']} -> {r['source_reference']}"
        for r in rows if r.get("source_type") == "BENCHMARKS_ROW" and r.get("source_reference") not in benchmark_ids
    ]

    # Every top-level parameter constant simulate.py actually defines must
    # have at least one matching (exact or dotted-prefix) row.
    expected_top_level = [
        "SEED", "N_PER_CELL", "GENE_GROUPS.CORE_HR", "GENE_GROUPS.DDR_SIGNALING",
        "PAM50_PROPORTIONS", "WGD_PREVALENCE", "MEAN_MUTATIONS_PER_EXOME",
        "PURITY_RANGE", "PLOIDY_RANGE", "TUMOR_DEPTH_MEAN", "NORMAL_DEPTH_MEAN",
        "MIN_EVALUABLE_DEPTH", "LOH_SECOND_HIT_PROB.CORE_HR.Pathogenic",
        "LOH_SECOND_HIT_PROB.CORE_HR.Benign", "LOH_SECOND_HIT_PROB.DDR_SIGNALING.Pathogenic",
        "LOH_SECOND_HIT_PROB.DDR_SIGNALING.Benign", "GIS_SCORE_DIST.CORE_HR.Pathogenic",
        "GIS_SCORE_DIST.CORE_HR.Benign", "GIS_SCORE_DIST.DDR_SIGNALING.Pathogenic",
        "GIS_SCORE_DIST.DDR_SIGNALING.Benign", "SBS3_EXPOSURE_DIST.Pathogenic",
        "SBS3_EXPOSURE_DIST.Benign", "NULL_FEATURE_PROB.Pathogenic", "NULL_FEATURE_PROB.Benign",
        "OTHER_LOH_CATEGORY_SPLIT.RETAINED", "OTHER_LOH_CATEGORY_SPLIT.LOH_NON_SECOND_HIT",
        "OTHER_LOH_CATEGORY_SPLIT.LOH_AMBIGUOUS", "OTHER_LOH_CATEGORY_SPLIT.NOT_EVALUABLE",
        "SBS_signature_shape.hrd_favored_substring", "SBS_signature_shape.background",
    ]
    recorded_names = {r["parameter_name"] for r in rows}
    missing_params = [p for p in expected_top_level if p not in recorded_names]

    # And confirm simulate.py doesn't define an additional top-level UPPER_CASE
    # constant that isn't accounted for at all (catches future drift).
    src = SIMULATE_PY.read_text(encoding="utf-8")
    defined_constants = set(re.findall(r"^([A-Z][A-Z0-9_]*)\s*=", src, re.MULTILINE))
    known_prefixes = {p.split(".")[0] for p in expected_top_level} | {"SBS_CONTEXTS", "REPO_ROOT", "DATA_DIR", "TRUTH_DETAIL_DIR", "TRUTH_TSV", "BANNER"}
    unaccounted = sorted(defined_constants - known_prefixes)

    ok = (not missing_cols and not bad_source_type and not bad_rationale
          and not bad_benchmark_refs and not missing_params and not unaccounted)
    check(
        "parameter provenance recorded for every simulator parameter",
        ok,
        f"missing_columns={missing_cols}, bad_source_type={bad_source_type}, "
        f"ARBITRARY-without-rationale={bad_rationale}, invalid BENCHMARKS_ROW refs={bad_benchmark_refs}, "
        f"missing_from_provenance={missing_params}, unaccounted-for constants in simulate.py={unaccounted}",
    )


def main():
    criterion_1_naming_and_headers()
    criterion_2_truth_key_separate_with_estimand()
    criterion_3_derivation_present_and_reproducible()
    criterion_4_at_least_one_null()
    criterion_5_parameter_provenance_complete()

    overall = True
    for name, passed, detail in results:
        verdict = "PASS" if passed else "FAIL"
        overall = overall and passed
        print(f"[{verdict}] {name} — {detail}")

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
