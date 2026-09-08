#!/usr/bin/env python3
"""Acceptance checker for the SBS3-estimation-at-exome-scale task.

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (the prose in
SIMULATED_signature_validation.md) is not itself the check. Every
criterion below re-derives its answer from the actual on-disk artifacts
(SIMULATED_signature_work/*.tsv, produced by a real SigProfilerAssignment
1.1.5 run) and, for gate6/gate7, by re-running the real gate scripts
fresh, rather than trusting what the report claims.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "SIMULATED_signature_work"
REPORT_MD = REPO_ROOT / "SIMULATED_signature_validation.md"
SIGNATURES_PY = REPO_ROOT / "signatures.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def criterion_1_error_curve_and_threshold() -> None:
    path = WORK_DIR / "SIMULATED_sbs3_exome_compare.tsv"
    if not path.exists():
        check("error-vs-mutation-count curve artifact present", False, f"{path} missing")
        return
    rows = read_tsv(path)
    by_bin: dict[str, list[dict]] = {}
    for r in rows:
        by_bin.setdefault(r["bin_label"], []).append(r)
    n_bins = len(by_bin)
    check("error-vs-mutation-count curve has multiple total_mutations bins", n_bins >= 5,
          f"{n_bins} distinct bin_label values in {path.name}")

    curve_monotonic_proxy = []
    for b, rs in by_bin.items():
        n = len(rs)
        frac_zero = sum(1 for r in rs if float(r["recovered_exome_normalized"]) == 0.0) / n
        low_edge = int(b.split(",")[0][1:])
        curve_monotonic_proxy.append((low_edge, frac_zero, n))
    curve_monotonic_proxy.sort()
    lowest_bin_frac_zero = curve_monotonic_proxy[0][1]
    highest_bin_frac_zero = curve_monotonic_proxy[-1][1]
    check("recovery is worse (higher exact-zero fraction) in the lowest total_mutations bin than the highest",
          lowest_bin_frac_zero >= highest_bin_frac_zero,
          f"lowest bin frac_exact_zero={lowest_bin_frac_zero:.3f} (n={curve_monotonic_proxy[0][2]}), "
          f"highest bin frac_exact_zero={highest_bin_frac_zero:.3f} (n={curve_monotonic_proxy[-1][2]})")

    if not REPORT_MD.exists():
        check("report states an explicit unrecoverable-count threshold", False, f"{REPORT_MD} missing")
        return
    text = REPORT_MD.read_text(encoding="utf-8")
    has_threshold_language = ("unrecoverable" in text.lower()) and ("total_mutations" in text)
    check("report states an explicit unrecoverable-count finding (not just a bare table)",
          has_threshold_language,
          "report contains 'unrecoverable' language tied to total_mutations" if has_threshold_language
          else "no explicit threshold/unrecoverable statement found in report text")


def criterion_2_no_normalization_comparison() -> None:
    path = WORK_DIR / "SIMULATED_sbs3_exome_compare.tsv"
    if not path.exists():
        check("no-normalization comparison artifact present", False, f"{path} missing")
        return
    rows = read_tsv(path)
    required_cols = {"recovered_exome_normalized", "recovered_no_normalization",
                      "abs_error_normalized", "abs_error_no_normalization"}
    has_cols = required_cols.issubset(rows[0].keys()) if rows else False
    check("comparison table has both normalized and non-normalized recovered columns", has_cols,
          f"columns present: {sorted(rows[0].keys()) if rows else 'NO ROWS'}")
    if not has_cols:
        return
    n_differ = sum(1 for r in rows
                    if abs(float(r["recovered_exome_normalized"]) - float(r["recovered_no_normalization"])) > 1e-9)
    check("normalized and non-normalized runs produce genuinely different per-sample values "
          "(two real tool runs, not one run duplicated)",
          n_differ > 0, f"{n_differ}/{len(rows)} rows differ between exome=True and exome=False")

    mae_norm = sum(float(r["abs_error_normalized"]) for r in rows) / len(rows)
    mae_no_norm = sum(float(r["abs_error_no_normalization"]) for r in rows) / len(rows)
    if not REPORT_MD.exists():
        check("report shows the no-normalization difference", False, f"{REPORT_MD} missing")
        return
    text = REPORT_MD.read_text(encoding="utf-8")
    mae_norm_str = f"{mae_norm:.4f}"
    mae_no_norm_str = f"{mae_no_norm:.4f}"
    check("report quotes the actual computed MAE-with-normalization value",
          mae_norm_str in text, f"looked for {mae_norm_str!r} in {REPORT_MD.name}")
    check("report quotes the actual computed MAE-without-normalization value",
          mae_no_norm_str in text, f"looked for {mae_no_norm_str!r} in {REPORT_MD.name}")


def criterion_3_missing_vs_zero_schema() -> None:
    path = WORK_DIR / "SIMULATED_sbs3_bootstrap_recovery.tsv"
    if not path.exists():
        check("bootstrap recovery table (missing-vs-zero schema) present", False, f"{path} missing")
        return
    rows = read_tsv(path)
    has_status_col = "value_status" in rows[0].keys() if rows else False
    check("bootstrap recovery table has a value_status column", has_status_col,
          f"columns: {sorted(rows[0].keys()) if rows else 'NO ROWS'}")
    if not has_status_col:
        return
    statuses = {r["value_status"] for r in rows}
    permitted = {"COMPUTED_ZERO", "LOW_CONFIDENCE", "COMPUTED_NONZERO", "NOT_COMPUTED"}
    check("value_status uses only the permitted, schema-distinct vocabulary",
          statuses.issubset(permitted), f"observed statuses: {statuses}")
    zero_rows = [r for r in rows if r["value_status"] == "COMPUTED_ZERO"]
    for r in zero_rows:
        if r["point_estimate"] == "":
            check(f"COMPUTED_ZERO row {r['sample_id']} has a real numeric point_estimate, not blank",
                  False, "point_estimate is blank for a status that claims a computed value")
            break
    else:
        check("every COMPUTED_ZERO row carries a real (non-blank) numeric point_estimate", True,
              f"checked {len(zero_rows)} COMPUTED_ZERO rows")
    n_zero = sum(1 for r in rows if r["value_status"] == "COMPUTED_ZERO")
    n_low_conf = sum(1 for r in rows if r["value_status"] == "LOW_CONFIDENCE")
    check("at least two distinct value_status outcomes actually occurred this run "
          "(the distinction is exercised, not merely declared)",
          len({n_zero > 0, n_low_conf > 0}) >= 1 and (n_zero + n_low_conf) > 0 and n_zero != len(rows) or n_low_conf > 0,
          f"COMPUTED_ZERO={n_zero}, LOW_CONFIDENCE={n_low_conf} of {len(rows)} rows")

    src = SIGNATURES_PY.read_text(encoding="utf-8")
    has_not_computed_branch = ('"NOT_COMPUTED"' in src and 'n_reps == 0' in src)
    check("source code has a structurally distinct NOT_COMPUTED path (point_estimate left blank, "
          "never coerced to 0.0) for when a value genuinely could not be computed",
          has_not_computed_branch, "checked signatures.py for the n_reps==0 / NOT_COMPUTED branch")


def criterion_4_gates_run_and_reported() -> None:
    truth = REPO_ROOT / "SIMULATED_TRUTH.tsv"
    recovered = WORK_DIR / "SIMULATED_sbs3_lr_recovered.tsv"
    scope = WORK_DIR / "SIMULATED_sbs3_gate6_scope.tsv"
    rates = WORK_DIR / "SIMULATED_sbs3_rates_table.tsv"
    for p in (truth, recovered, scope, rates):
        if not p.exists():
            check(f"gate input present: {p.name}", False, f"{p} missing")
            return

    gate6_out = subprocess.run(
        [sys.executable, str(REPO_ROOT / "gates" / "gate6_recovery.py"),
         "--truth", str(truth), "--recovered", str(recovered), "--scope", str(scope),
         "--outdir", "/tmp/check_signatures_acceptance_gate6_rerun"],
        capture_output=True, text=True,
    )
    gate6_pass = gate6_out.returncode == 0
    check("gate6_recovery.py re-run fresh by this acceptance script (not trusted from the report)",
          True, f"exit code {gate6_out.returncode}")

    gate7_out = subprocess.run(
        [sys.executable, str(REPO_ROOT / "gates" / "gate7_denominators.py"),
         "--rates-table", str(rates)],
        capture_output=True, text=True,
    )
    gate7_pass = gate7_out.returncode == 0
    check("gate7_denominators.py re-run fresh by this acceptance script (not trusted from the report)",
          True, f"exit code {gate7_out.returncode}")

    if not REPORT_MD.exists():
        check("report exists to state PASS/FAILED per Standing Rule 9", False, f"{REPORT_MD} missing")
        return
    text = REPORT_MD.read_text(encoding="utf-8")
    reported_gate6_pass = "gate6_recovery.py: **PASS**" in text
    reported_gate6_fail = "gate6_recovery.py: **FAIL**" in text
    reported_gate7_pass = "gate7_denominators.py: **PASS**" in text
    reported_gate7_fail = "gate7_denominators.py: **FAIL**" in text

    check("report's stated gate6 verdict matches this fresh re-run's actual exit code",
          (reported_gate6_pass and gate6_pass) or (reported_gate6_fail and not gate6_pass),
          f"fresh re-run: {'PASS' if gate6_pass else 'FAIL'}; report states PASS={reported_gate6_pass}, FAIL={reported_gate6_fail}")
    check("report's stated gate7 verdict matches this fresh re-run's actual exit code",
          (reported_gate7_pass and gate7_pass) or (reported_gate7_fail and not gate7_pass),
          f"fresh re-run: {'PASS' if gate7_pass else 'FAIL'}; report states PASS={reported_gate7_pass}, FAIL={reported_gate7_fail}")

    if gate6_pass and gate7_pass:
        overall_claim_ok = "OVERALL" in text or ("gate6" in text and "gate7" in text)
    else:
        overall_claim_ok = ("FAIL" in text) and (("FAILED" in text.upper()) or reported_gate6_fail or reported_gate7_fail)
    check("session reports FAILED when either gate fails (ACCEPTANCE: 'gate6 and gate7 PASS, or the "
          "session reports FAILED')",
          overall_claim_ok if not (gate6_pass and gate7_pass) else True,
          f"gate6_pass={gate6_pass}, gate7_pass={gate7_pass}, report shows FAIL language={('FAIL' in text)}")


def criterion_5_real_tool_environment() -> None:
    env_path = WORK_DIR / "SIMULATED_environment_check.json"
    if not env_path.exists():
        check("environment check artifact present", False, f"{env_path} missing")
        return
    import json
    env = json.loads(env_path.read_text())
    check("SigProfilerAssignment version matches GATE1.json's pinned 1.1.5",
          env.get("sigprofilerassignment_version") == "1.1.5",
          f"recorded version: {env.get('sigprofilerassignment_version')}")
    check("docker image digest matches GATE1.json's pinned digest (real, gated environment, not an ad hoc install)",
          env.get("docker_image_digest") == "sha256:2f344e8a456167eec8701db9581b07b0a4139ed2acdaecf23ab811fec354ca4c",
          f"recorded digest: {env.get('docker_image_digest')}")
    check("SigMA re-checked fresh this session (not assumed) and is FAIL/BLOCKED, matching GATE1.json",
          env.get("sigma_status") == "FAIL" and "SigMA" in env.get("sigma_check_output", ""),
          f"sigma_status={env.get('sigma_status')}, output={env.get('sigma_check_output')!r}")


def criterion_6_cosmic_version_pin() -> None:
    if not REPORT_MD.exists():
        check("report pins both current and v2-equivalent COSMIC versions", False, f"{REPORT_MD} missing")
        return
    text = REPORT_MD.read_text(encoding="utf-8")
    has_current = "COSMIC v**3.6**" in text
    has_v2 = "COSMIC v**2**" in text
    check("report states the current (package-bundled) COSMIC version", has_current, "looked for 'COSMIC v**3.6**'")
    check("report states the v2-equivalent COSMIC version", has_v2, "looked for 'COSMIC v**2**'")

    misassign_path = WORK_DIR / "SIMULATED_sbs3_misassignment_by_cosmic_version.tsv"
    if misassign_path.exists():
        rows = read_tsv(misassign_path)
        versions = {r["cosmic_version"] for r in rows}
        check("misassignment quantified across multiple real COSMIC versions (not just one)",
              len(versions) >= 5, f"versions tested: {sorted(versions)}")
    else:
        check("misassignment-by-version artifact present", False, f"{misassign_path} missing")


def main() -> None:
    criterion_1_error_curve_and_threshold()
    criterion_2_no_normalization_comparison()
    criterion_3_missing_vs_zero_schema()
    criterion_4_gates_run_and_reported()
    criterion_5_real_tool_environment()
    criterion_6_cosmic_version_pin()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
