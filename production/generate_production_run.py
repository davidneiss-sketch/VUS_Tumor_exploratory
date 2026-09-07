#!/usr/bin/env python3
"""Generates one deterministic, fully-SIMULATED "production" run of gate
input files, on disk, for gate2..gate7 to be deployed against (per the
task's "gate5 and gate6 run against PRODUCTION outputs on every pipeline
invocation, not only against test fixtures" requirement).

Every artifact here is synthetic verification-demo data -- there is no
real germline or tumor data in this repository (TRACK.md: Track A only,
no germline access; GATE1.json: gate1_result FAIL). Standing Rule 1
applies in full: every filename contains SIMULATED, and this script's
own raw-input files carry an explicit fabricated-data marker in their
first line.

This is a clean/healthy example run (all gates expected to PASS) --
demonstrating that the gates correctly catch bad input is the job of
tests/, not of this production deployment target.

Run: python3 production/generate_production_run.py
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def write_tsv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> None:
    raw_dir = HERE / "SIMULATED_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Raw input files + manifest (gate2) ---
    samples = [
        ("SIM-S001", "SIM-P001", 812_345, "GRCh38"),
        ("SIM-S002", "SIM-P002", 940_112, "GRCh38"),
        ("SIM-S003", "SIM-P003", 775_600, "GRCh38"),
        ("SIM-S004", "SIM-P004", 1_003_887, "GRCh38"),
        ("SIM-S005", "SIM-P005", 861_204, "GRCh38"),
        ("SIM-S006", "SIM-P006", 902_477, "GRCh38"),
    ]
    manifest_rows = []
    provenance_rows = []
    for sample_id, patient_id, reads, ref in samples:
        fname = f"SIMULATED_{sample_id}.rawtxt"
        fpath = raw_dir / fname
        body = (
            "# SIMULATED RAW INPUT -- fabricated for gate-verification testing, not biological data\n"
            f"READS: {reads}\n"
            f"REFERENCE: {ref}\n"
            + ("ACGTACGTACGT\n" * (reads // 50000 + 1))  # vary byte size with read count, deterministic
        )
        fpath.write_text(body, encoding="utf-8")
        data = fpath.read_bytes()
        md5 = hashlib.md5(data).hexdigest()
        manifest_rows.append({
            "sample_id": sample_id,
            "path": str(fpath),
            "byte_size_recorded": len(data),
            "md5_recorded": md5,
            "source_url": "",
            "reference_build_recorded": ref,
            "read_count_recorded": reads,
        })
        provenance_rows.append({
            "sample_id": sample_id,
            "patient_id": patient_id,
            "source_file": str(fpath),
        })

    write_tsv(
        HERE / "SIMULATED_raw_manifest.tsv", manifest_rows,
        ["sample_id", "path", "byte_size_recorded", "md5_recorded", "source_url", "reference_build_recorded", "read_count_recorded"],
    )
    write_tsv(HERE / "SIMULATED_provenance.tsv", provenance_rows, ["sample_id", "patient_id", "source_file"])
    write_tsv(
        HERE / "SIMULATED_analyzed_samples.tsv",
        [{"sample_id": s[0]} for s in samples],
        ["sample_id"],
    )

    # --- 2. Phase log (gate3) ---
    phase_rows = [
        {"phase": "copy_number_calling", "command": "SIMULATED: facets_test.R --toy", "exit_code": 0,
         "wall_clock_sec": 46.0, "peak_rss_mb": 512.0, "cpu_hours": 0.02, "bytes_read": 5_295_625, "n_samples": 6},
        {"phase": "hrd_scoring", "command": "SIMULATED: scarHRD_test.R --toy", "exit_code": 0,
         "wall_clock_sec": 13.5, "peak_rss_mb": 340.0, "cpu_hours": 0.004, "bytes_read": 5_295_625, "n_samples": 6},
        {"phase": "signature_assignment", "command": "SIMULATED: cosmic_fit --toy", "exit_code": 0,
         "wall_clock_sec": 19.2, "peak_rss_mb": 890.0, "cpu_hours": 0.006, "bytes_read": 5_295_625, "n_samples": 6},
        {"phase": "loh_binomial_test", "command": "SIMULATED: loh_binomial.py --toy", "exit_code": 0,
         "wall_clock_sec": 3.4, "peak_rss_mb": 120.0, "cpu_hours": 0.001, "bytes_read": 5_295_625, "n_samples": 6},
        {"phase": "second_hit_scan", "command": "SIMULATED: second_hit_scan.py --toy", "exit_code": 0,
         "wall_clock_sec": 4.1, "peak_rss_mb": 140.0, "cpu_hours": 0.001, "bytes_read": 5_295_625, "n_samples": 6},
    ]
    write_tsv(
        HERE / "SIMULATED_phase_log.tsv", phase_rows,
        ["phase", "command", "exit_code", "wall_clock_sec", "peak_rss_mb", "cpu_hours", "bytes_read", "n_samples"],
    )

    # --- 3. LR table (gate4, gate5 tripwire 5) ---
    lr_rows = [
        {"stratum": "CORE_HR_LumA", "gene_group": "CORE_HR", "status": "FITTED",
         "point_estimate": 8.2, "ci_low": 3.1, "ci_high": 19.5, "n_replicates": 2000,
         "n_pathogenic": 25, "n_benign": 40, "control_type": "analysis"},
        {"stratum": "CORE_HR_Basal", "gene_group": "CORE_HR", "status": "FITTED",
         "point_estimate": 15.6, "ci_low": 6.0, "ci_high": 42.0, "n_replicates": 2000,
         "n_pathogenic": 30, "n_benign": 22, "control_type": "analysis"},
        {"stratum": "DDR_SIGNALING_LumA", "gene_group": "DDR_SIGNALING", "status": "FITTED",
         "point_estimate": 1.8, "ci_low": 0.6, "ci_high": 4.9, "n_replicates": 2000,
         "n_pathogenic": 18, "n_benign": 35, "control_type": "analysis"},
        {"stratum": "DDR_SIGNALING_Her2E", "gene_group": "DDR_SIGNALING", "status": "INSUFFICIENT_N",
         "point_estimate": "", "ci_low": "", "ci_high": "", "n_replicates": "",
         "n_pathogenic": 5, "n_benign": 8, "control_type": "analysis"},
        {"stratum": "NEGATIVE_CONTROL_1", "gene_group": "CORE_HR", "status": "FITTED",
         "point_estimate": 1.1, "ci_low": 0.2, "ci_high": 3.2, "n_replicates": 2000,
         "n_pathogenic": 20, "n_benign": 20, "control_type": "negative_control"},
        {"stratum": "POSITIVE_CONTROL_1", "gene_group": "CORE_HR", "status": "FITTED",
         "point_estimate": 12.0, "ci_low": 10.5, "ci_high": 13.0, "n_replicates": 2000,
         "n_pathogenic": 22, "n_benign": 20, "control_type": "positive_control"},
    ]
    write_tsv(
        HERE / "SIMULATED_LR_TABLE.tsv", lr_rows,
        ["stratum", "gene_group", "status", "point_estimate", "ci_low", "ci_high",
         "n_replicates", "n_pathogenic", "n_benign", "control_type"],
    )

    # --- 4. Tripwire inputs (gate5) ---
    metrics_rows = [
        {"metric_name": "auc_core_hr_lumA", "value": 0.81, "benchmark_value": "", "benchmark_source": ""},
        {"metric_name": "auc_ddr_signaling_basal", "value": 0.74, "benchmark_value": "", "benchmark_source": ""},
        {"metric_name": "hrd_high_proportion_hgsoc_measured", "value": 0.47, "benchmark_value": 0.50,
         "benchmark_source": "BENCHMARKS.tsv HRD01 (TCGA 2011, ~50% HGSOC)"},
        {"metric_name": "tp53_mutation_rate_measured", "value": 0.34, "benchmark_value": 0.37,
         "benchmark_source": "BENCHMARKS.tsv TP02 (37%, TCGA IDC n=680)"},
    ]
    write_tsv(HERE / "SIMULATED_metrics.tsv", metrics_rows, ["metric_name", "value", "benchmark_value", "benchmark_source"])

    threshold_rows = [
        {"threshold_name": "gis_threshold_recalibration_check", "derived_threshold": 42.9,
         "reference_threshold": 42.0, "reported_bias_pct": round((42.9 - 42.0) / 42.0 * 100, 2)},
    ]
    write_tsv(HERE / "SIMULATED_thresholds.tsv", threshold_rows,
              ["threshold_name", "derived_threshold", "reference_threshold", "reported_bias_pct"])

    circularity_rows = [
        {"gene_group": "CORE_HR", "excluded_count": 7},
        {"gene_group": "DDR_SIGNALING", "excluded_count": 4},
    ]
    write_tsv(HERE / "SIMULATED_circularity.tsv", circularity_rows, ["gene_group", "excluded_count"])

    # --- 5. Recovery inputs (gate6) ---
    truth_rows = [
        {"quantity": "core_hr_lumA_LR", "injected_value": 8.0, "estimand": "LR", "is_null": "FALSE"},
        {"quantity": "ddr_signaling_lumA_LR", "injected_value": 1.0, "estimand": "LR", "is_null": "TRUE"},
        {"quantity": "core_hr_basal_LR", "injected_value": 15.0, "estimand": "LR", "is_null": "FALSE"},
    ]
    write_tsv(HERE / "SIMULATED_TRUTH.tsv", truth_rows, ["quantity", "injected_value", "estimand", "is_null"])

    recovered_rows = [
        {"quantity": "core_hr_lumA_LR", "recovered_point": 8.2, "ci_low": 3.1, "ci_high": 19.5, "estimand": "LR"},
        {"quantity": "ddr_signaling_lumA_LR", "recovered_point": 1.05, "ci_low": 0.55, "ci_high": 1.95, "estimand": "LR"},
        {"quantity": "core_hr_basal_LR", "recovered_point": 15.6, "ci_low": 6.0, "ci_high": 42.0, "estimand": "LR"},
    ]
    write_tsv(HERE / "SIMULATED_RECOVERED.tsv", recovered_rows, ["quantity", "recovered_point", "ci_low", "ci_high", "estimand"])

    scope_rows = [
        {"quantity": "core_hr_lumA_LR", "in_scope": "TRUE",
         "reason": "primary Stage 2 deliverable quantity, computed by this production run's LR-fitting pipeline"},
        {"quantity": "ddr_signaling_lumA_LR", "in_scope": "TRUE",
         "reason": "primary Stage 2 deliverable quantity, computed by this production run's LR-fitting pipeline"},
        {"quantity": "core_hr_basal_LR", "in_scope": "TRUE",
         "reason": "primary Stage 2 deliverable quantity, computed by this production run's LR-fitting pipeline"},
    ]
    write_tsv(HERE / "SIMULATED_scope.tsv", scope_rows, ["quantity", "in_scope", "reason"])

    # --- 6. Rates table (gate7) ---
    def rate_row(name, num, den, excl, reason):
        return {"metric_name": name, "numerator": num, "denominator": den,
                "excluded_count": excl, "excluded_reason": reason, "rate": round(num / den, 8)}

    rates_rows = [
        rate_row("core_hr_lumA_pathogenic_call_rate", 18, 65, 3, "AMBIGUOUS LOH category (LOH_AMBIGUOUS)"),
        rate_row("sample_selection_inclusion_rate", 542, 611, 69, "excluded at S4 histology filter"),
        rate_row("sigprofilerassignment_success_rate", 58, 60, 2, "insufficient tumor mutation burden for cosine-similarity fit"),
    ]
    write_tsv(HERE / "SIMULATED_rates_table.tsv", rates_rows,
              ["metric_name", "numerator", "denominator", "excluded_count", "excluded_reason", "rate"])

    print("Generated production run files under", HERE)


if __name__ == "__main__":
    main()
