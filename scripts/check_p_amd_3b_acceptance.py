#!/usr/bin/env python3
"""Acceptance checker for P-AMD-3b (apply the gate6 criterion amendment).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (PROTOCOL_DEVIATIONS.md's,
REPORT.md's own prose) is not itself the check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE6 = REPO_ROOT / "gates" / "gate6_recovery.py"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
PROTOCOL_DEVIATIONS = REPO_ROOT / "PROTOCOL_DEVIATIONS.md"
REPORT = REPO_ROOT / "REPORT.md"
CONSERVATIVE_ANALYSIS = REPO_ROOT / "CONSERVATIVE_ASSIGNMENT_ANALYSIS.md"
CONFIRM_DIRECTIONALITY_SCRIPT = REPO_ROOT / "scripts" / "confirm_tier_directionality.py"
CONFIRM_DIRECTIONALITY_RESULT = REPO_ROOT / "CONFIRM_TIER_DIRECTIONALITY_RESULT.md"
BIAS_PREDICTION = REPO_ROOT / "production_v2" / "SIMULATED_BIAS_PREDICTION.tsv"
RECOVERY_TABLE = REPO_ROOT / "production_v2" / "SIMULATED_RECOVERY_TABLE.tsv"
TEST_GATE6 = REPO_ROOT / "tests" / "test_gate6.py"
LOGISTIC_ESTIMATOR = REPO_ROOT / "logistic_estimator.py"
SIMULATE_PY = REPO_ROOT / "simulate.py"
SIGNATURES_PY = REPO_ROOT / "signatures.py"
LOH_CALLER_PY = REPO_ROOT / "loh_caller.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    return [line[3:].rstrip("/") for line in result.stdout.splitlines()]


def criterion_1_amended_gate6_fails_bad_ci_fixture() -> None:
    d = REPO_ROOT / "tests" / "fixtures" / "gate6_bad_ci"
    outdir = REPO_ROOT / "scratch_check_amd3b" / "bad_ci"
    result = subprocess.run(
        ["python3", str(GATE6), "--truth", str(d / "truth.tsv"), "--recovered", str(d / "recovered.tsv"),
         "--scope", str(d / "scope.tsv"), "--outdir", str(outdir)],
        cwd=REPO_ROOT, capture_output=True, text=True)
    check("amended gate6 STILL FAILS the on-disk gate6_bad_ci fixture (HALT condition if not)",
          result.returncode == 1 and "gate6_recovery OVERALL: FAIL" in result.stdout,
          f"returncode={result.returncode}")
    check("the failure is on relative bias, not containment (containment now informational)",
          "relative bias 1.0667 exceeds tolerance" in result.stdout,
          "looked for the relative-bias failure reason")
    check("containment is still computed and reported for this fixture",
          "does NOT contain injected value 4.5" in result.stdout,
          "looked for the informational containment line")


def criterion_2_directional_check_implemented_and_tested() -> None:
    if not GATE6.exists():
        check("gate6_recovery.py present", False, f"{GATE6} missing")
        return
    text = GATE6.read_text(encoding="utf-8")
    check("directional_check function implemented", "def directional_check(" in text,
          "looked for directional_check()")
    check("--bias-prediction CLI argument added", "--bias-prediction" in text,
          "looked for the new argparse option")
    check("MAGNITUDE_SLACK_FACTOR disclosed as a named constant", "MAGNITUDE_SLACK_FACTOR" in text,
          "looked for the disclosed slack constant")

    if not TEST_GATE6.exists():
        check("tests/test_gate6.py present", False, f"{TEST_GATE6} missing")
        return
    test_text = TEST_GATE6.read_text(encoding="utf-8")
    check("a wrong-sign fixture test exists", "wrong_sign" in test_text.lower(),
          "looked for a wrong-sign test")
    wrong_sign_fixture = REPO_ROOT / "tests" / "fixtures" / "gate6_wrong_sign_bias"
    check("gate6_wrong_sign_bias fixture exists with a bias_prediction.tsv",
          (wrong_sign_fixture / "bias_prediction.tsv").exists(),
          f"{wrong_sign_fixture}")
    result = subprocess.run(["python3", "-m", "unittest", "test_gate6", "-v"],
                             cwd=REPO_ROOT / "tests", capture_output=True, text=True)
    check("full test_gate6.py suite passes (includes the wrong-sign and correct-sign fixtures)",
          result.returncode == 0, result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "")


def criterion_3_containment_reported_not_gating() -> None:
    if not RECOVERY_TABLE.exists():
        check("production_v2/SIMULATED_RECOVERY_TABLE.tsv present", False, f"{RECOVERY_TABLE} missing")
        return
    rows = read_tsv(RECOVERY_TABLE)
    scored_rows = [r for r in rows if r["quantity"] in ("core_hr_joint_LR", "ddr_signaling_joint_LR")]
    check("both production quantities have a populated ci_contains_injected column",
          all(r.get("ci_contains_injected") in ("True", "False") for r in scored_rows),
          f"values: {[r.get('ci_contains_injected') for r in scored_rows]}")
    core_hr_row = next((r for r in scored_rows if r["quantity"] == "core_hr_joint_LR"), None)
    check("CORE_HR's ci_contains_injected is False (CI does not contain injected) YET status is SIMULATED_PASS "
          "(containment does not gate)",
          core_hr_row is not None and core_hr_row["ci_contains_injected"] == "False"
          and core_hr_row["status"] == "SIMULATED_PASS",
          f"core_hr row: {core_hr_row}")


def criterion_4_protocol_and_deviations_and_report_updated() -> None:
    if not PROTOCOL.exists():
        check("PROTOCOL.md present", False, "missing")
        return
    text = PROTOCOL.read_text(encoding="utf-8")
    check("PROTOCOL.md §11 marks the amendment APPLIED", "AMENDED" in text and "APPLIED" in text,
          "looked for APPLIED status language in §11")
    check("PROTOCOL.md states containment is no longer a hard pass/fail condition",
          "no longer a hard" in text.lower() or "no longer required as a hard" in text.lower(),
          "looked for explicit containment-downgrade language")
    check("PROTOCOL.md discloses the conservative-bias property",
          "conservative bias" in text.lower() or "understate" in text.lower(),
          "looked for the shrinkage-property disclosure")
    check("PROTOCOL.md discloses §7.1 is NOT amended by this entry (Entry 1 remains separate/draft)",
          "Entry 1" in text and "DRAFT" in text,
          "looked for the Entry-1-separation note")

    if not PROTOCOL_DEVIATIONS.exists():
        check("PROTOCOL_DEVIATIONS.md present", False, "missing")
        return
    dev_text = PROTOCOL_DEVIATIONS.read_text(encoding="utf-8")
    check("PROTOCOL_DEVIATIONS.md has an Entry 3 with Status APPLIED", "Entry 3" in dev_text and "APPLIED" in dev_text,
          "looked for Entry 3 / APPLIED")
    check("Entry 3's Approver field is completed (not blank)",
          "Approver** | davidneiss@unicauca.edu.co" in dev_text or "Approver | davidneiss@unicauca.edu.co" in dev_text,
          "looked for a completed Approver field")
    check("Entry 3 has a Date approved / Date applied field",
          "Date approved" in dev_text and "Date applied" in dev_text,
          "looked for date fields")
    check("Entry 1's own Approver section remains blank (untouched, unapplied)",
          "blank — for human completion. Entry 1" in dev_text,
          "looked for the still-blank Entry 1 approver note")

    if not REPORT.exists():
        check("REPORT.md present", False, "missing")
        return
    report_text = REPORT.read_text(encoding="utf-8")
    check("REPORT.md's Entry 3 deviation section appears BEFORE (more prominent than) the Entry 1 draft section",
          report_text.find("APPLIED") != -1 and report_text.find("APPLIED") < report_text.find("draft"),
          "checked relative ordering")
    check("REPORT.md discloses the conservative-bias finding with the realized downgrade",
          "one-tier downgrade" in report_text.lower() or "one tier" in report_text.lower(),
          "looked for the tier-downgrade disclosure")


def criterion_5_near_tier_boundary_column_standing() -> None:
    if not RECOVERY_TABLE.exists():
        check("near_tier_boundary column present", False, f"{RECOVERY_TABLE} missing")
        return
    rows = read_tsv(RECOVERY_TABLE)
    scored_rows = [r for r in rows if r["quantity"] in ("core_hr_joint_LR", "ddr_signaling_joint_LR")]
    check("near_tier_boundary column populated for both production quantities",
          all(r.get("near_tier_boundary") in ("TRUE", "FALSE", "AT_RISK", "REALIZED_DOWNGRADE", "N/A")
              for r in scored_rows) and len(scored_rows) == 2,
          f"values: {[r.get('near_tier_boundary') for r in scored_rows]}")
    check("both production quantities flag REALIZED_DOWNGRADE (concrete, not hypothetical)",
          all(r.get("near_tier_boundary") == "REALIZED_DOWNGRADE" for r in scored_rows),
          f"values: {[r.get('near_tier_boundary') for r in scored_rows]}")
    if not BIAS_PREDICTION.exists():
        check("production_v2/SIMULATED_BIAS_PREDICTION.tsv present (standing input, not one-time)",
              False, f"{BIAS_PREDICTION} missing")
    else:
        check("production_v2/SIMULATED_BIAS_PREDICTION.tsv present (standing input, not one-time)",
              True, str(BIAS_PREDICTION))


def criterion_6_directionality_confirmed_conservative() -> None:
    if not CONFIRM_DIRECTIONALITY_SCRIPT.exists():
        check("scripts/confirm_tier_directionality.py present", False, f"{CONFIRM_DIRECTIONALITY_SCRIPT} missing")
        return
    result = subprocess.run(["python3", str(CONFIRM_DIRECTIONALITY_SCRIPT)], cwd=REPO_ROOT,
                             capture_output=True, text=True)
    check("confirm_tier_directionality.py exits 0 (all movements conservative; HALT condition if not)",
          result.returncode == 0, f"returncode={result.returncode}, stdout tail: {result.stdout[-300:]}")
    check("confirm_tier_directionality.py reports ALL MOVEMENTS CONSERVATIVE",
          "ALL MOVEMENTS CONSERVATIVE" in result.stdout,
          "looked for the explicit verdict")
    check("CONFIRM_TIER_DIRECTIONALITY_RESULT.md written", CONFIRM_DIRECTIONALITY_RESULT.exists(),
          f"{CONFIRM_DIRECTIONALITY_RESULT}")


def criterion_7_all_quantities_rescored_gates_run_through_wrapper() -> None:
    if not RECOVERY_TABLE.exists():
        check("all 91 truth quantities re-scored under amended criterion", False, f"{RECOVERY_TABLE} missing")
        return
    rows = read_tsv(RECOVERY_TABLE)
    check("all 91 truth quantities appear in the re-scored recovery table",
          len(rows) == 91, f"row count: {len(rows)}")
    check("both in-scope quantities are SIMULATED_PASS under the amended criterion",
          all(r["status"] == "SIMULATED_PASS" for r in rows if r["quantity"] in
              ("core_hr_joint_LR", "ddr_signaling_joint_LR")),
          f"statuses: { {r['quantity']: r['status'] for r in rows if r['quantity'] in ('core_hr_joint_LR', 'ddr_signaling_joint_LR')} }")

    deployment_log = (REPO_ROOT / "DEPLOYMENT_LOG.md").read_text(encoding="utf-8")
    check("DEPLOYMENT_LOG.md logs gate4/gate6/gate8/gate9 all run through run_with_integrity_checks.py this invocation",
          "Invocation 6" in deployment_log and deployment_log.count("run_with_integrity_checks.py") >= 8,
          "looked for Invocation 6 and >=8 wrapper invocations logged total")


def criterion_8_estimator_and_simulator_unmodified() -> None:
    changed = set(_changed_files())
    for forbidden in ("logistic_estimator.py", "simulate.py", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    check("gates/gate6_recovery.py WAS modified (this task's own required change)",
          "gates/gate6_recovery.py" in changed, f"in changed files: {'gates/gate6_recovery.py' in changed}")
    check("PROTOCOL.md WAS modified (this task's own required change)",
          "PROTOCOL.md" in changed, f"in changed files: {'PROTOCOL.md' in changed}")


def criterion_9_no_p07_p08_p09_rerun() -> None:
    changed = set(_changed_files())
    forbidden_paths = [p for p in changed if p.startswith("loh_caller") or p.startswith("signatures")
                        or "P07" in p or "P08" in p or "P09" in p]
    check("no P07/P08/P09-labeled output changed this task", not forbidden_paths,
          f"suspicious changed paths: {forbidden_paths}")


def main() -> None:
    criterion_1_amended_gate6_fails_bad_ci_fixture()
    criterion_2_directional_check_implemented_and_tested()
    criterion_3_containment_reported_not_gating()
    criterion_4_protocol_and_deviations_and_report_updated()
    criterion_5_near_tier_boundary_column_standing()
    criterion_6_directionality_confirmed_conservative()
    criterion_7_all_quantities_rescored_gates_run_through_wrapper()
    criterion_8_estimator_and_simulator_unmodified()
    criterion_9_no_p07_p08_p09_rerun()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
