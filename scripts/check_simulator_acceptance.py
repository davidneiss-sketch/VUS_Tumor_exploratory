#!/usr/bin/env python3
"""Acceptance checker for the simulator (v2, defect-fix revision).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (SIMULATION_SPEC.md's prose)
is not itself the check. Every criterion re-derives its answer from the
actual on-disk artifacts, importing simulate.py fresh where a live
re-derivation is possible, rather than trusting what a report claims.

Criteria 1-5 are carried over (adapted) from the prior simulator task's
acceptance script. Criteria 6-12 are this revision's task's own
ACCEPTANCE bullets (the four-defect-fix task).

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIMULATE_PY = ROOT / "simulate.py"
SIMULATION_SPEC = ROOT / "SIMULATION_SPEC.md"
PARAMETER_PROVENANCE = ROOT / "PARAMETER_PROVENANCE.tsv"
BENCHMARKS = ROOT / "BENCHMARKS.tsv"
TRUTH_TSV = ROOT / "SIMULATED_TRUTH.tsv"
TRUTH_DETAIL_DIR = ROOT / "SIMULATED_TRUTH_detail"
DATA_DIR = ROOT / "SIMULATED_data"
V1_SCAN_TSV = ROOT / "V1_NUMERIC_SCAN.tsv"
BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"

results = []


def check(name, passed, detail):
    results.append((name, passed, detail))


def read_tsv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_simulate_module():
    spec = importlib.util.spec_from_file_location("simulate_live", SIMULATE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def criterion_1_naming_and_headers():
    problems = []
    if not TRUTH_TSV.exists():
        problems.append("SIMULATED_TRUTH.tsv missing")
    else:
        for p in [TRUTH_TSV] + list((DATA_DIR).rglob("*")) + list(TRUTH_DETAIL_DIR.rglob("*")):
            if p.is_file() and p.name != "README.md" and "SIMULATED" not in p.name and p.suffix != ".tsv" and p.parent != DATA_DIR:
                continue
        for p in list(DATA_DIR.iterdir()) + list(TRUTH_DETAIL_DIR.iterdir()):
            if p.is_file() and p.name != "README.md" and "SIMULATED" not in p.name:
                problems.append(f"{p} does not carry SIMULATED in its name")
        for p in list(DATA_DIR.glob("*.md")):
            text = p.read_text(encoding="utf-8")
            if not text.startswith(BANNER):
                problems.append(f"{p} does not start with the mandated banner")
    check("every non-README output file is SIMULATED-named; every .md report starts with the banner",
          not problems, "; ".join(problems) if problems else "OK")


def criterion_2_truth_key_separate_with_estimand():
    if not TRUTH_TSV.exists():
        check("truth key separate directory, estimand populated for every row", False, "SIMULATED_TRUTH.tsv missing")
        return
    truth_parent_ok = TRUTH_TSV.parent == ROOT
    detail_separate = TRUTH_DETAIL_DIR.exists() and DATA_DIR not in TRUTH_DETAIL_DIR.parents and TRUTH_DETAIL_DIR != DATA_DIR
    rows = read_tsv(TRUTH_TSV)
    missing_estimand = [r["quantity"] for r in rows if not r.get("estimand", "").strip()]
    ok = truth_parent_ok and detail_separate and not missing_estimand
    check("truth key separate directory, estimand populated for every row", ok,
          f"truth_at_repo_root={truth_parent_ok}, TRUTH_detail_separate={detail_separate}, "
          f"{len(rows)} row(s), missing_estimand={missing_estimand}")


def criterion_3_derivation_present_and_reproducible():
    if not SIMULATION_SPEC.exists():
        check("LR derivation present in spec and reproducible", False, "SIMULATION_SPEC.md missing")
        return
    text = SIMULATION_SPEC.read_text(encoding="utf-8")
    norm = re.sub(r"\s+", " ", text)
    has_categorical = "Phi(a+bZ)" in norm or "probit" in norm.lower()
    has_gaussian_marginal = "Gaussian-probit convolution identity" in norm
    has_joint_derivation = "joint_density" in norm and "Simpson" in norm

    mod = load_simulate_module()
    live_rows = mod.compute_truth_quantities()
    live_by_q = {r["quantity"]: r["injected_value"] for r in live_rows}
    persisted_rows = read_tsv(TRUTH_TSV)
    mismatches = []
    for r in persisted_rows:
        q = r["quantity"]
        persisted_val = float(r["injected_value"])
        live_val = live_by_q.get(q)
        if live_val is None:
            mismatches.append(f"{q}: not produced by a live re-import")
            continue
        if persisted_val == 0:
            if abs(live_val) > 1e-9:
                mismatches.append(f"{q}: persisted=0 live={live_val}")
        elif abs(live_val - persisted_val) / abs(persisted_val) > 1e-9:
            mismatches.append(f"{q}: persisted={persisted_val} live={live_val}")

    ok = has_categorical and has_gaussian_marginal and has_joint_derivation and not mismatches
    check("the injected LR derivation is present and reproducible", ok,
          f"categorical_formula_present={has_categorical}, marginal_convolution_identity_present={has_gaussian_marginal}, "
          f"joint_numerical_integration_present={has_joint_derivation}, "
          f"re-running simulate.compute_truth_quantities() vs persisted SIMULATED_TRUTH.tsv: "
          f"{len(mismatches)} mismatch(es){': ' + '; '.join(mismatches) if mismatches else ' (exact match)'}")


def criterion_4_at_least_one_null():
    if not TRUTH_TSV.exists():
        check("at least one injected-null entry exists (true LR = 1.0 exactly)", False, "SIMULATED_TRUTH.tsv missing")
        return
    rows = read_tsv(TRUTH_TSV)
    null_rows = [r for r in rows if r.get("is_null", "").strip().upper() == "TRUE"]
    exact_one_rows = [r for r in null_rows if abs(float(r["injected_value"]) - 1.0) < 1e-9]
    ok = len(null_rows) >= 1 and len(exact_one_rows) >= 1
    check("at least one injected-null entry exists (true LR = 1.0 exactly)", ok,
          f"{len(null_rows)} row(s) with is_null=TRUE, {len(exact_one_rows)} with injected_value exactly 1.0: "
          f"{[r['quantity'] for r in exact_one_rows]}")


def criterion_5_parameter_provenance_complete():
    if not PARAMETER_PROVENANCE.exists():
        check("parameter provenance recorded for every simulator parameter", False, "PARAMETER_PROVENANCE.tsv missing")
        return
    rows = read_tsv(PARAMETER_PROVENANCE)
    required_cols = {"parameter_name", "value", "source_type", "source_reference", "rationale"}
    missing_columns = required_cols - set(rows[0].keys()) if rows else required_cols
    valid_source_types = {"BENCHMARKS_ROW", "ARBITRARY", "PROVIDED_BY_TASK", "INSTALLED_PACKAGE_DATA"}
    bad_source_type = [r["parameter_name"] for r in rows if r["source_type"] not in valid_source_types]
    arbitrary_no_rationale = [r["parameter_name"] for r in rows if r["source_type"] == "ARBITRARY" and not r["rationale"].strip()]

    benchmarks_rows = read_tsv(BENCHMARKS) if BENCHMARKS.exists() else []
    benchmark_ids = {r["benchmark_id"] for r in benchmarks_rows}
    invalid_benchmark_refs = [
        r["parameter_name"] for r in rows
        if r["source_type"] == "BENCHMARKS_ROW" and r["source_reference"] not in benchmark_ids
    ]

    source_text = SIMULATE_PY.read_text(encoding="utf-8")
    top_level_consts = set(re.findall(r"^([A-Z][A-Z0-9_]*)\s*=", source_text, re.MULTILINE))
    structural_exempt = {"REPO_ROOT", "DATA_DIR", "TRUTH_DETAIL_DIR", "TRUTH_TSV", "V1_SCAN_TSV", "BANNER",
                         "GRID_CATEGORIES", "DIRECTION_OF_PROTOCOL_CATEGORY", "SBS_CONTEXTS",
                         "COSMIC_REFERENCE_TSV"}
    provenance_prefixes = {r["parameter_name"].split(".")[0] for r in rows}
    unaccounted = sorted(c for c in top_level_consts if c not in structural_exempt and c not in provenance_prefixes)

    dotted_required = [
        "GENE_GROUPS.CORE_HR", "GENE_GROUPS.DDR_SIGNALING", "GENE_GROUPS.NULL_ARM",
        "Z_MEAN.CORE_HR.Pathogenic", "Z_MEAN.CORE_HR.Benign", "Z_MEAN.DDR_SIGNALING.Pathogenic",
        "Z_MEAN.DDR_SIGNALING.Benign", "Z_MEAN.NULL_ARM.Pathogenic", "Z_MEAN.NULL_ARM.Benign",
        "WT_LOST_LINK.CORE_HR", "WT_LOST_LINK.DDR_SIGNALING", "WT_LOST_LINK.NULL_ARM",
        "GIS_LINK.CORE_HR", "GIS_LINK.DDR_SIGNALING", "GIS_LINK.NULL_ARM",
        "SBS3_LINK.CORE_HR", "SBS3_LINK.DDR_SIGNALING", "SBS3_LINK.NULL_ARM",
        "EVAL_POINT.wt_lost", "EVAL_POINT.gis", "EVAL_POINT.sbs3",
    ]
    provenance_names = {r["parameter_name"] for r in rows}
    missing_from_provenance = [p for p in dotted_required if p not in provenance_names]

    ok = (not missing_columns and not bad_source_type and not arbitrary_no_rationale
          and not invalid_benchmark_refs and not missing_from_provenance and not unaccounted)
    check("parameter provenance recorded for every simulator parameter", ok,
          f"missing_columns={missing_columns}, bad_source_type={bad_source_type}, "
          f"ARBITRARY-without-rationale={arbitrary_no_rationale}, invalid_BENCHMARKS_ROW_refs={invalid_benchmark_refs}, "
          f"missing_from_provenance={missing_from_provenance}, unaccounted_top_level_constants={unaccounted}")


def criterion_6_coverage_grid():
    path = DATA_DIR / "SIMULATED_coverage_report.tsv"
    if not path.exists():
        check("every truth category has minimum instances per purity x depth cell, or is declared out of scope",
              False, f"{path} missing")
        return
    rows = read_tsv(path)
    bad = []
    for r in rows:
        if r["scope_status"] == "OUT_OF_SCOPE":
            if not r["scope_reason"].strip():
                bad.append(f"{r['category']}/{r['arm']}/{r['class']}/{r['purity_bin']}/{r['depth_regime']}: OUT_OF_SCOPE with no reason")
        elif r["scope_status"] == "IN_SCOPE":
            if r["meets_minimum"] != "True":
                bad.append(f"{r['category']}/{r['arm']}/{r['class']}/{r['purity_bin']}/{r['depth_regime']}: "
                            f"count={r['count']} < min_required={r['min_required']}")
        else:
            bad.append(f"unknown scope_status {r['scope_status']!r}")
    check("every truth category has minimum instances per purity x depth cell, or is declared out of scope",
          not bad, f"{len(rows)} cell(s) checked; {len(bad)} problem(s)" + (": " + "; ".join(bad[:10]) if bad else ""))


def criterion_7_deletion_wt_loss():
    path = DATA_DIR / "SIMULATED_variant_calls.tsv"
    if not path.exists():
        check("deletion-type WT_LOSS present with n_t=1, count reported", False, f"{path} missing")
        return
    rows = read_tsv(path)
    wt_loss_rows = [r for r in rows if r["assigned_loh_category"] == "WT_LOSS"]
    wrong_nt = [r for r in wt_loss_rows if int(r["major_cn"]) + int(r["minor_cn"]) != 1]
    ok = len(wt_loss_rows) > 0 and not wrong_nt
    check("deletion-type WT_LOSS present with n_t=1, count reported", ok,
          f"count={len(wt_loss_rows)}, all_with_cn_total=1={not wrong_nt}")


def criterion_8_joint_differs_from_marginal():
    if not TRUTH_TSV.exists():
        check("joint injected LR differs from product of marginals; both persisted; ratio stated", False, "SIMULATED_TRUTH.tsv missing")
        return
    rows = {r["quantity"]: r for r in read_tsv(TRUTH_TSV)}
    problems = []
    for arm in ("core_hr", "ddr_signaling"):
        jkey, pkey, rkey = f"{arm}_joint_LR", f"{arm}_product_of_marginals_LR", f"{arm}_joint_vs_marginal_inflation_ratio"
        if jkey not in rows or pkey not in rows or rkey not in rows:
            problems.append(f"{arm}: missing one of {jkey}/{pkey}/{rkey}")
            continue
        jv, pv, rv = float(rows[jkey]["injected_value"]), float(rows[pkey]["injected_value"]), float(rows[rkey]["injected_value"])
        if abs(jv - pv) / max(abs(pv), 1e-9) < 0.05:
            problems.append(f"{arm}: joint ({jv}) and product-of-marginals ({pv}) differ by less than 5% -- not a meaningful inflation demonstration")
        if abs(rv - jv / pv) > 1e-9:
            problems.append(f"{arm}: stated ratio {rv} does not match joint/product = {jv/pv}")
        if rows[rkey]["estimand"] != "LR_RATIO":
            problems.append(f"{arm}: {rkey} estimand is {rows[rkey]['estimand']!r}, expected LR_RATIO")
    check("joint injected LR differs from product of marginals; both persisted; ratio stated", not problems,
          "; ".join(problems) if problems else
          f"core_hr ratio={rows['core_hr_joint_vs_marginal_inflation_ratio']['injected_value']}, "
          f"ddr_signaling ratio={rows['ddr_signaling_joint_vs_marginal_inflation_ratio']['injected_value']}")


def criterion_9_full_vector_null():
    if not TRUTH_TSV.exists():
        check("full-feature-vector injected-null arm exists with true LR=1.0", False, "SIMULATED_TRUTH.tsv missing")
        return
    rows = {r["quantity"]: r for r in read_tsv(TRUTH_TSV)}
    key = "null_arm_full_vector_joint_LR"
    if key not in rows:
        check("full-feature-vector injected-null arm exists with true LR=1.0", False, f"{key} missing from SIMULATED_TRUTH.tsv")
        return
    v = float(rows[key]["injected_value"])
    is_null = rows[key]["is_null"].strip().upper() == "TRUE"
    ok = abs(v - 1.0) < 1e-9 and is_null
    check("full-feature-vector injected-null arm exists with true LR=1.0", ok,
          f"{key}={v}, is_null={is_null}")


def criterion_10_baf_emitted():
    path = DATA_DIR / "SIMULATED_baf_segments.tsv"
    if not path.exists():
        check("BAF emitted per segment", False, f"{path} missing")
        return
    rows = read_tsv(path)
    required_cols = {"sample_id", "snp_index", "phase", "tumor_ref_reads", "tumor_alt_reads", "mirrored_baf"}
    missing_cols = required_cols - set(rows[0].keys()) if rows else required_cols
    n_samples_with_baf = len({r["sample_id"] for r in rows})
    ok = len(rows) > 0 and not missing_cols
    check("BAF emitted per segment", ok,
          f"{len(rows)} BAF SNP row(s) across {n_samples_with_baf} sample(s), missing_columns={missing_cols}")


def criterion_11_numeric_v1_scan():
    if not V1_SCAN_TSV.exists():
        check("numeric v1 scan executed and reported (not a filename scan)", False, f"{V1_SCAN_TSV} missing")
        return
    rows = read_tsv(V1_SCAN_TSV)
    tiers_present = {r.get("tier", "") for r in rows}
    has_both_tiers = "TIER_1_DESIGN_LEVEL_TRUTH" in tiers_present and "TIER_2_RAW_PER_OBSERVATION" in tiers_present
    tier1_rows = [r for r in rows if r.get("tier") == "TIER_1_DESIGN_LEVEL_TRUTH"]
    tier1_covers_all_figures = len(tier1_rows) == len(load_simulate_module().RETRACTED_V1_FIGURES)
    tier1_any_match = any(r["any_match_found"] == "True" for r in tier1_rows)
    ok = has_both_tiers and tier1_covers_all_figures and not tier1_any_match
    check("numeric v1 scan executed and reported (not a filename scan)", ok,
          f"tiers_present={tiers_present}, tier1_rows={len(tier1_rows)}, tier1_any_match={tier1_any_match}")


def criterion_12_estimand_for_new_quantities():
    if not TRUTH_TSV.exists():
        check("estimand column populated for every new truth quantity", False, "SIMULATED_TRUTH.tsv missing")
        return
    rows = read_tsv(TRUTH_TSV)
    new_quantities = [
        "core_hr_joint_LR", "core_hr_product_of_marginals_LR", "core_hr_joint_vs_marginal_inflation_ratio",
        "ddr_signaling_joint_LR", "ddr_signaling_product_of_marginals_LR", "ddr_signaling_joint_vs_marginal_inflation_ratio",
        "null_arm_full_vector_joint_LR", "null_arm_full_vector_product_of_marginals_LR", "null_arm_full_vector_inflation_ratio",
    ]
    by_q = {r["quantity"]: r for r in rows}
    missing = [q for q in new_quantities if q not in by_q]
    blank_estimand = [q for q in new_quantities if q in by_q and not by_q[q]["estimand"].strip()]
    ok = not missing and not blank_estimand
    check("estimand column populated for every new truth quantity", ok,
          f"missing_quantities={missing}, blank_estimand={blank_estimand}")


def main():
    criterion_1_naming_and_headers()
    criterion_2_truth_key_separate_with_estimand()
    criterion_3_derivation_present_and_reproducible()
    criterion_4_at_least_one_null()
    criterion_5_parameter_provenance_complete()
    criterion_6_coverage_grid()
    criterion_7_deletion_wt_loss()
    criterion_8_joint_differs_from_marginal()
    criterion_9_full_vector_null()
    criterion_10_baf_emitted()
    criterion_11_numeric_v1_scan()
    criterion_12_estimand_for_new_quantities()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
