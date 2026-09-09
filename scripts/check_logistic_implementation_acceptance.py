#!/usr/bin/env python3
"""Acceptance checker for the logistic-regression estimator
implementation task (per the approved PROPOSED_PROTOCOL_AMENDMENT.md).

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
ESTIMATOR = REPO_ROOT / "logistic_estimator.py"
GATE9 = REPO_ROOT / "gates" / "gate9_imbalance.py"
TEST_GATE9 = REPO_ROOT / "tests" / "test_gate9.py"
DISPOSITIVE = REPO_ROOT / "DISPOSITIVE_TEST_AFTER.md"
CALIBRATION = REPO_ROOT / "CALIBRATION_DIAGNOSTICS.md"
INSTABILITY_V2 = REPO_ROOT / "INTERVAL_INSTABILITY_V2.md"
STEP2_V2_TSV = REPO_ROOT / "SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_V2.tsv"
PRODUCTION_V2 = REPO_ROOT / "production_v2"
DEPLOYMENT_LOG = REPO_ROOT / "DEPLOYMENT_LOG.md"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path, delim: str = "\t") -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delim))


def criterion_1_dispositive_test() -> None:
    if not DISPOSITIVE.exists() or not STEP2_V2_TSV.exists():
        check("Step 2 dispositive test re-run and reported", False,
              f"DISPOSITIVE_TEST_AFTER.md exists={DISPOSITIVE.exists()}, "
              f"SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_V2.tsv exists={STEP2_V2_TSV.exists()}")
        return
    text = DISPOSITIVE.read_text(encoding="utf-8")
    check("DISPOSITIVE_TEST_AFTER.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("reports before (OLD estimator) and after (NEW estimator) in the same table",
          "0.26" in text and "0.02" in text and "3.25" in text and "2.97" in text,
          "looked for both old and new separation figures reproduced")

    rows = read_tsv(STEP2_V2_TSV)
    check("both arms present in the re-run", {r["arm"] for r in rows} == {"CORE_HR", "DDR_SIGNALING"},
          f"arms: {[r['arm'] for r in rows]}")

    all_separated = True
    all_track_joint = True
    detail_parts = []
    for r in rows:
        sep = float(r["separation_pooled_sd_units"])
        tracks = r["tracks_true_joint"].strip().upper() == "TRUE"
        all_separated = all_separated and sep >= 1.0
        all_track_joint = all_track_joint and tracks
        detail_parts.append(f"{r['arm']}: separation={sep:.3f}, tracks_true_joint={tracks}")
    check("NEW estimator separates the two datasets by >= 1.0 pooled-sd units (non-negotiable acceptance bar)",
          all_separated, "; ".join(detail_parts))
    check("NEW estimator's correlated-data mean tracks the TRUE JOINT value (not the product-of-marginals value)",
          all_track_joint, "; ".join(detail_parts))


def criterion_2_prior_odds_printed() -> None:
    if not ESTIMATOR.exists():
        check("prior-odds correction printed per fit", False, f"{ESTIMATOR} missing")
        return
    text = ESTIMATOR.read_text(encoding="utf-8")
    check("prior_odds_correction() prints the correction applied",
          "prior-odds correction" in text and "print(" in text.split("def prior_odds_correction")[1][:600],
          "looked for a print statement inside prior_odds_correction()")
    check("probability_to_lr() calls the printing correction function (not a silent duplicate)",
          "correction = prior_odds_correction(" in text,
          "looked for probability_to_lr() calling prior_odds_correction()")

    # Live re-derivation: run a real fit and confirm the correction is
    # actually printed to stdout, not merely present in source but unused.
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, '.'); import logistic_estimator as le; "
         "pop = le.load_population(); "
         "path = [r for r in pop if r['arm']=='CORE_HR' and r['true_class']=='Pathogenic'][:50]; "
         "benign = [r for r in pop if r['arm']=='CORE_HR' and r['true_class']=='Benign'][:50]; "
         "le.fit_and_score(path, benign, le.EVAL_POINT, 0.5, 'LumA', 0, 1.0, verbose=True)"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    check("live re-derivation: a real fit actually prints the prior-odds correction to stdout",
          "prior-odds correction" in proc.stdout and "correction multiplier" in proc.stdout,
          f"stdout tail: {proc.stdout[-300:]}" if proc.returncode == 0 else f"fit failed: {proc.stderr[-500:]}")


def criterion_3_gate9() -> None:
    if not GATE9.exists():
        check("gates/gate9_imbalance.py present", False, f"{GATE9} missing")
        return
    text = GATE9.read_text(encoding="utf-8")
    check("gate9 checks class ratios spanning at least 1:1, 1:5, 1:20", all(r in text for r in ("1:1", "1:5", "1:20")),
          "looked for all 3 required ratio labels")
    check("gate9 has a pre-specified, documented tolerance", "TOLERANCE_MAX_RATIO" in text,
          "looked for a named tolerance constant")

    if not TEST_GATE9.exists():
        check("tests/test_gate9.py present", False, f"{TEST_GATE9} missing")
    else:
        proc = subprocess.run([sys.executable, "-m", "unittest", "test_gate9", "-v"],
                               cwd=REPO_ROOT / "tests", capture_output=True, text=True)
        check("tests/test_gate9.py passes (passing fixture + deliberately-broken fixture)", proc.returncode == 0,
              f"exit={proc.returncode}; stderr tail: {proc.stderr[-400:]}")
        check("test_gate9.py includes a deliberately-broken (uncorrected-conversion) fixture test",
              "uncorrected_prior_odds_conversion" in TEST_GATE9.read_text(encoding="utf-8"),
              "looked for the specific broken-fixture test name")

    gate9_good = REPO_ROOT / "tests" / "fixtures" / "gate9_good" / "table.tsv"
    gate9_bad = REPO_ROOT / "tests" / "fixtures" / "gate9_bad" / "table.tsv"
    check("gate9 good and bad fixtures both present", gate9_good.exists() and gate9_bad.exists(),
          f"good={gate9_good.exists()}, bad={gate9_bad.exists()}")


def criterion_4_calibration_reported() -> None:
    if not CALIBRATION.exists():
        check("CALIBRATION_DIAGNOSTICS.md present", False, f"{CALIBRATION} missing")
        return
    text = CALIBRATION.read_text(encoding="utf-8")
    check("starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("reports a reliability curve (binned, with n per bin)", "observed fraction" in text.lower()
          and "mean predicted" in text.lower(), "looked for reliability curve table")
    check("reports Brier score for both arms", text.count("Brier") >= 2, "looked for Brier score mentions")
    check("reports ECE", "ECE" in text, "looked for expected calibration error")


def criterion_5_loglinearity_checked() -> None:
    if not CALIBRATION.exists():
        check("log-linearity checked and reported", False, f"{CALIBRATION} missing")
        return
    text = CALIBRATION.read_text(encoding="utf-8")
    check("log-linearity residual-grid check present (comparison against true analytic model)",
          "residual" in text.lower() and "simulate.joint_lr" in text,
          "looked for the residual-grid-vs-analytic-truth check")
    check("log-linearity nested-model (interaction/spline) comparison present",
          "nested" in text.lower() and ("interaction" in text.lower() or "spline" in text.lower()),
          "looked for the nested-model comparison")
    check("draws an explicit conclusion about whether log-linearity holds (not left ambiguous)",
          "not rejected" in text.lower() or "rejected" in text.lower(),
          "looked for an explicit accept/reject statement")


def criterion_6_instability_sweep_by_dimension() -> None:
    if not INSTABILITY_V2.exists():
        check("INTERVAL_INSTABILITY_V2.md present", False, f"{INSTABILITY_V2} missing")
        return
    text = INSTABILITY_V2.read_text(encoding="utf-8")
    check("starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("reports results broken out by feature-vector dimension", "dimension" in text.lower()
          and "SBS3_ONLY" in text and "LOH_GIS_SBS3" in text, "looked for dimension-broken-out results")
    check("reports the density-underflow finding (gone or not) explicitly",
          "n_estimator_error" in text or "underflow" in text.lower(), "looked for the underflow finding")

    sweep_tsv = REPO_ROOT / "SIMULATED_INTERVAL_INSTABILITY_SWEEP_V2.tsv"
    if sweep_tsv.exists():
        rows = read_tsv(sweep_tsv)
        check("sweep data covers both arms x 3 dimensions x the full n-grid",
              len(rows) == 72, f"{len(rows)} rows (expected 72 = 2 arms x 3 dims x 12 n-values)")
        total_errors = sum(int(r["n_estimator_error"]) for r in rows)
        check("live re-derivation: zero estimator errors across the whole sweep (density-underflow is gone)",
              total_errors == 0, f"total n_estimator_error across all rows: {total_errors}")
    else:
        check("SIMULATED_INTERVAL_INSTABILITY_SWEEP_V2.tsv present", False, f"{sweep_tsv} missing")


def criterion_7_gates_run_against_production() -> None:
    if not PRODUCTION_V2.exists():
        check("production_v2/ directory present with new estimator's production output", False,
              f"{PRODUCTION_V2} missing")
        return
    required_files = ["SIMULATED_LR_TABLE.tsv", "SIMULATED_RECOVERED.tsv", "SIMULATED_scope.tsv",
                       "SIMULATED_ABLATION_TABLE_V2.tsv", "SIMULATED_GATE9_INPUT.tsv"]
    missing = [f for f in required_files if not (PRODUCTION_V2 / f).exists()]
    check("all production_v2 output files present", len(missing) == 0, f"missing: {missing}")

    if not DEPLOYMENT_LOG.exists():
        check("DEPLOYMENT_LOG.md documents gate4/gate6/gate8/gate9 runs against production_v2 output", False,
              f"{DEPLOYMENT_LOG} missing")
        return
    text = DEPLOYMENT_LOG.read_text(encoding="utf-8")
    for gate_name in ("gate4_statistics", "gate6_recovery", "gate8_interval_informativeness", "gate9_imbalance"):
        check(f"DEPLOYMENT_LOG.md documents a {gate_name} run against production_v2 output",
              gate_name in text and "production_v2" in text,
              f"looked for {gate_name} mentioned alongside production_v2")
    check("declares gate6's scope explicitly includes the newly-reachable joint quantities",
          "NEWLY_REACHABLE" in text or "newly reachable" in text.lower(),
          "looked for explicit scope declaration language")


def criterion_8_protocol_unmodified() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    changed = {line[3:].rstrip("/") for line in result.stdout.splitlines()}
    check("PROTOCOL.md not modified by this task", "PROTOCOL.md" not in changed,
          f"PROTOCOL.md in changed files: {'PROTOCOL.md' in changed}")
    diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "PROTOCOL.md"], cwd=REPO_ROOT)
    check("git diff confirms PROTOCOL.md is byte-identical to HEAD", diff.returncode == 0,
          f"git diff exit={diff.returncode}")
    for forbidden in ("simulate.py", "stake_ablation.py", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified by this task (not re-run/edited)", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")


def main() -> None:
    criterion_1_dispositive_test()
    criterion_2_prior_odds_printed()
    criterion_3_gate9()
    criterion_4_calibration_reported()
    criterion_5_loglinearity_checked()
    criterion_6_instability_sweep_by_dimension()
    criterion_7_gates_run_against_production()
    criterion_8_protocol_unmodified()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
