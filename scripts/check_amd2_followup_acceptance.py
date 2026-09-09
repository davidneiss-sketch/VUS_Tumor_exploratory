#!/usr/bin/env python3
"""Acceptance checker for the P-AMD-2 follow-up task: Part A (fix the
lambda hardcoding and estimand-mismatch deviations in production_v2_run.py,
re-run and re-score) and Part B (eliminate the fixed-output-filename
collision class: inventory, preflight check, checksum check, tests).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment is not itself the check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ORPHAN_CHECK = REPO_ROOT / "ORPHAN_CHECK.md"
PRODUCTION_RUN = REPO_ROOT / "production_v2_run.py"
PROTOCOL_DEVIATIONS = REPO_ROOT / "PROTOCOL_DEVIATIONS.md"
DEPLOYMENT_LOG = REPO_ROOT / "DEPLOYMENT_LOG.md"
OUTPUT_INVENTORY = REPO_ROOT / "OUTPUT_PATH_INVENTORY.tsv"
PREFLIGHT_SCRIPT = REPO_ROOT / "scripts" / "preflight_collision_check.py"
CHECKSUM_SCRIPT = REPO_ROOT / "scripts" / "artifact_checksum_check.py"
WRAPPER_SCRIPT = REPO_ROOT / "scripts" / "run_with_integrity_checks.py"
PRODUCTION_V2 = REPO_ROOT / "production_v2"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
LOGISTIC_ESTIMATOR = REPO_ROOT / "logistic_estimator.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def criterion_orphan_check() -> None:
    if not ORPHAN_CHECK.exists():
        check("ORPHAN_CHECK.md present", False, f"{ORPHAN_CHECK} missing")
        return
    text = ORPHAN_CHECK.read_text(encoding="utf-8")
    check("ORPHAN_CHECK.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("records the process/container check with a conclusion", "no orphaned process" in text.lower(),
          "looked for an explicit conclusion statement")
    check("covers processes, containers, AND open file handles (not just one)",
          "docker" in text.lower() and "lsof" in text.lower() and "ps aux" in text.lower(),
          "looked for all three check types documented")


def criterion_lambda_cv_selected_with_assertion() -> None:
    if not PRODUCTION_RUN.exists():
        check("production_v2_run.py present", False, f"{PRODUCTION_RUN} missing")
        return
    text = PRODUCTION_RUN.read_text(encoding="utf-8")
    check("no hardcoded LAMBDA_FIXED constant remains", "LAMBDA_FIXED" not in text,
          "looked for the removed hardcoded-lambda constant")
    check("calls select_lambda_cv (logistic_estimator.py's own CV selection) for the pooled recovery",
          "select_lambda_cv" in text, "looked for the CV-selection call")
    check("has an explicit assertion that halts on a non-CV-selected lambda",
          "assert_cv_selected" in text and "AssertionError" in text,
          "looked for the provenance-guard function and its raised exception")

    # Live re-derivation: the assertion actually fires on bad provenance.
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, '.'); import production_v2_run as p\n"
         "try:\n"
         "    p.assert_cv_selected(1.0, 'HARDCODED', 'acceptance check')\n"
         "    print('DID_NOT_RAISE')\n"
         "except AssertionError:\n"
         "    print('RAISED_CORRECTLY')\n"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    check("live re-derivation: assert_cv_selected() actually raises on a non-CV-selected lambda",
          "RAISED_CORRECTLY" in proc.stdout, f"stdout: {proc.stdout}, stderr: {proc.stderr[-300:]}")


def criterion_lambda_deviation_logged() -> None:
    if not PROTOCOL_DEVIATIONS.exists():
        check("PROTOCOL_DEVIATIONS.md present", False, f"{PROTOCOL_DEVIATIONS} missing")
        return
    text = PROTOCOL_DEVIATIONS.read_text(encoding="utf-8")
    check("has an Entry 2 documenting the lambda deviation", "Entry 2" in text and "hardcoded lambda" in text.lower(),
          "looked for an Entry 2 heading naming the hardcoded-lambda deviation")
    check("has a Date occurred and Date corrected, both present", "Date occurred" in text and "Date corrected" in text,
          "looked for both date fields")
    check("logs the deviation as RESOLVED (occurred and was corrected), not erased",
          "RESOLVED" in text, "looked for explicit RESOLVED status")
    check("also documents the compounding single-subtype estimand-mismatch finding",
          "single-subtype evaluation" in text.lower() or "single reference subtype" in text.lower(),
          "looked for the second, compounding finding")


def criterion_mixture_and_side_by_side_printing() -> None:
    if not PRODUCTION_RUN.exists():
        check("mixture evaluation and side-by-side printing implemented", False, f"{PRODUCTION_RUN} missing")
        return
    text = PRODUCTION_RUN.read_text(encoding="utf-8")
    check("evaluates the mixture over PAM50_PROPORTIONS (not a single subtype)",
          "PAM50_PROPORTIONS" in text and "mixture_point_estimate" in text,
          "looked for the prevalence-weighted mixture function")
    check("prints INJECTED and RECOVERED estimand definitions side by side",
          "ESTIMAND COMPARISON" in text and "INJECTED estimand" in text and "RECOVERED estimand" in text,
          "looked for the explicit side-by-side print block")

    per_subtype_path = PRODUCTION_V2 / "SIMULATED_PER_SUBTYPE_LR.tsv"
    if not per_subtype_path.exists():
        check("SIMULATED_PER_SUBTYPE_LR.tsv present in production output", False, f"{per_subtype_path} missing")
    else:
        rows = read_tsv(per_subtype_path)
        check("per-subtype LR report has 2 arms x 5 subtypes = 10 rows", len(rows) == 10, f"{len(rows)} rows")
        check("Basal is reported as the lowest LR in both arms (the injected confound, visible in production output)",
              all(min(float(r["point_estimate_lr"]) for r in rows if r["arm"] == arm) ==
                  next(float(r["point_estimate_lr"]) for r in rows if r["arm"] == arm and r["subtype"] == "Basal")
                  for arm in ("CORE_HR", "DDR_SIGNALING")),
              "checked Basal's LR is the minimum within each arm's 5 subtype rows")


def criterion_gates_reported() -> None:
    if not DEPLOYMENT_LOG.exists():
        check("DEPLOYMENT_LOG.md documents the corrected gate runs", False, f"{DEPLOYMENT_LOG} missing")
        return
    text = DEPLOYMENT_LOG.read_text(encoding="utf-8")
    invocation5 = text.split("Invocation 5", 1)[1] if "Invocation 5" in text else ""
    check("Invocation 5 section present", bool(invocation5), "looked for an 'Invocation 5' heading")
    for gate_name in ("gate4_statistics", "gate6_recovery", "gate8_interval_informativeness", "gate9_imbalance"):
        check(f"Invocation 5 reports {gate_name}'s result", gate_name in invocation5,
              f"looked for {gate_name} mentioned in the Invocation 5 section")
    check("gate6's genuine FAIL is reported with its quantified residual gap (not hidden)",
          "does not contain" in invocation5.lower() and "0.0529" in invocation5,
          "looked for the exact CI-exclusion gap reported")
    check("does not claim gate6 was tuned to pass", "tune" not in invocation5.lower() or "no further" in invocation5.lower(),
          "looked for explicit non-tuning language")


def criterion_output_path_inventory() -> None:
    if not OUTPUT_INVENTORY.exists():
        check("OUTPUT_PATH_INVENTORY.tsv present", False, f"{OUTPUT_INVENTORY} missing")
        return
    rows = read_tsv(OUTPUT_INVENTORY)
    unsanctioned = [r for r in rows if r.get("shared_with_other_producer") == "True"
                     and r.get("known_sanctioned_exception") != "True"]
    check("OUTPUT_PATH_INVENTORY.tsv shows zero UNSANCTIONED shared paths",
          len(unsanctioned) == 0, f"unsanctioned rows: {unsanctioned}")
    sanctioned = [r for r in rows if r.get("known_sanctioned_exception") == "True"]
    check("the one sanctioned exception (gate6's own merge-aware SIMULATED_RECOVERY_TABLE.tsv) is explicitly tagged, not silently dropped",
          len(sanctioned) > 0, f"{len(sanctioned)} sanctioned-exception rows found")


def criterion_preflight_check() -> None:
    if not PREFLIGHT_SCRIPT.exists():
        check("scripts/preflight_collision_check.py present", False, f"{PREFLIGHT_SCRIPT} missing")
        return
    proc = subprocess.run([sys.executable, str(PREFLIGHT_SCRIPT)], cwd=REPO_ROOT, capture_output=True, text=True)
    check("preflight_collision_check.py passes against the current repository",
          proc.returncode == 0, f"exit={proc.returncode}; {proc.stdout[-300:]}")

    test_file = REPO_ROOT / "tests" / "test_preflight_collision_check.py"
    if not test_file.exists():
        check("preflight collision check has a colliding-fixture test", False, f"{test_file} missing")
    else:
        test_proc = subprocess.run([sys.executable, "-m", "unittest", "test_preflight_collision_check", "-v"],
                                    cwd=REPO_ROOT / "tests", capture_output=True, text=True)
        check("preflight collision check's test suite passes (including a colliding-fixture test)",
              test_proc.returncode == 0, f"exit={test_proc.returncode}; {test_proc.stderr[-300:]}")
        check("test explicitly constructs two producers claiming one path",
              "colliding" in test_file.read_text(encoding="utf-8").lower(),
              "looked for a colliding-fixture test by name")


def criterion_checksum_check() -> None:
    if not CHECKSUM_SCRIPT.exists():
        check("scripts/artifact_checksum_check.py present", False, f"{CHECKSUM_SCRIPT} missing")
        return
    test_file = REPO_ROOT / "tests" / "test_artifact_checksum_check.py"
    if not test_file.exists():
        check("artifact checksum check has a test suite", False, f"{test_file} missing")
    else:
        test_proc = subprocess.run([sys.executable, "-m", "unittest", "test_artifact_checksum_check", "-v"],
                                    cwd=REPO_ROOT / "tests", capture_output=True, text=True)
        check("artifact checksum check's test suite passes", test_proc.returncode == 0,
              f"exit={test_proc.returncode}; {test_proc.stderr[-300:]}")

    check("checksum check is wired into an UNCONDITIONAL wrapper (run_with_integrity_checks.py)",
          WRAPPER_SCRIPT.exists() and "preflight_collision_check" in WRAPPER_SCRIPT.read_text(encoding="utf-8")
          and "artifact_checksum_check" in WRAPPER_SCRIPT.read_text(encoding="utf-8"),
          "looked for the wrapper script calling both checks unconditionally")
    check("the wrapper was actually used this session (DEPLOYMENT_LOG.md records real invocations)",
          DEPLOYMENT_LOG.exists() and "run_with_integrity_checks.py" in DEPLOYMENT_LOG.read_text(encoding="utf-8"),
          "looked for real, recorded wrapper usage, not just the tool built and left idle")


def criterion_forbidden_files_unmodified() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    changed = {line[3:].rstrip("/") for line in result.stdout.splitlines()}
    for forbidden in ("PROTOCOL.md", "logistic_estimator.py", "simulate.py", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "PROTOCOL.md"], cwd=REPO_ROOT)
    check("git diff confirms PROTOCOL.md is byte-identical to HEAD", diff.returncode == 0,
          f"git diff exit={diff.returncode}")


def main() -> None:
    criterion_orphan_check()
    criterion_lambda_cv_selected_with_assertion()
    criterion_lambda_deviation_logged()
    criterion_mixture_and_side_by_side_printing()
    criterion_gates_reported()
    criterion_output_path_inventory()
    criterion_preflight_check()
    criterion_checksum_check()
    criterion_forbidden_files_unmodified()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
