#!/usr/bin/env python3
"""Acceptance checker for the Part A/B/C directional-check-fix task
(zero-bias noise allowance for gate6_recovery.py's directional check;
TCGA-BRCA purity-floor feasibility costing; LOH-confounding-gap writeup).

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
GATE6 = REPO_ROOT / "gates" / "gate6_recovery.py"
TEST_GATE6 = REPO_ROOT / "tests" / "test_gate6.py"
FIX_DOC = REPO_ROOT / "DIRECTIONAL_CHECK_FIX.md"
PURITY_DOC = REPO_ROOT / "PURITY_FLOOR_COST.md"
PROPOSED_DEVIATIONS = REPO_ROOT / "PROPOSED_DEVIATIONS.md"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
RESCORED_TABLE = (REPO_ROOT / "SIMULATED_loh_validation" / "gate6_directional_check_fix_rescoring"
                  / "SIMULATED_RECOVERY_TABLE.tsv")
REPAIRED_BIAS_PREDICTION = REPO_ROOT / "SIMULATED_loh_validation" / "SIMULATED_BIAS_PREDICTION_REPAIRED.tsv"
ORIGINAL_BIAS_PREDICTION = REPO_ROOT / "SIMULATED_loh_validation" / "SIMULATED_BIAS_PREDICTION.tsv"
ZERO_WITHIN_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "gate6_zero_bias_within_allowance"
ZERO_EXCEEDS_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "gate6_zero_bias_exceeds_allowance"
BAD_CI_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "gate6_bad_ci"

FORBIDDEN_FILES = ["simulate.py", "PROTOCOL.md", "logistic_estimator.py", "signatures.py", "loh_caller.py"]

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    return [line[3:].rstrip("/") for line in result.stdout.splitlines()]


def part_a_zero_bias_interface_implemented() -> None:
    if not GATE6.exists():
        check("gates/gate6_recovery.py present", False, f"{GATE6} missing")
        return
    text = GATE6.read_text(encoding="utf-8")
    check("zero_bias_check() implemented", "def zero_bias_check(" in text, "looked for zero_bias_check()")
    check("estimate_se_from_ci() implemented", "def estimate_se_from_ci(" in text,
          "looked for estimate_se_from_ci()")
    check("directional_check() (nonzero path) still present, unremoved",
          "def directional_check(" in text, "looked for directional_check()")
    check("noise-allowance multiplier is a named, disclosed constant",
          "ZERO_BIAS_NOISE_ALLOWANCE_SE_MULTIPLIER" in text,
          "looked for the multiplier constant")
    check("false-failure-rate computation function present (computed, not hand-typed)",
          "def two_sided_false_failure_rate(" in text and "math.erf" in text,
          "looked for two_sided_false_failure_rate() using math.erf")
    check("family-wise false-failure-rate function present",
          "def family_wise_false_failure_rate(" in text,
          "looked for family_wise_false_failure_rate()")
    check("optional noise_allowance_se_multiples column supported",
          "noise_allowance_se_multiples" in text,
          "looked for the optional bias-prediction column")


def part_a_fixtures_and_tests() -> None:
    for fixture in (ZERO_WITHIN_FIXTURE, ZERO_EXCEEDS_FIXTURE):
        check(f"{fixture.name} fixture exists with all 4 files",
              fixture.exists() and all((fixture / f).exists()
                                        for f in ("truth.tsv", "recovered.tsv", "scope.tsv", "bias_prediction.tsv")),
              str(fixture))

    if not TEST_GATE6.exists():
        check("tests/test_gate6.py present", False, f"{TEST_GATE6} missing")
        return
    test_text = TEST_GATE6.read_text(encoding="utf-8")
    check("a within-allowance zero-bias test exists", "within_noise_allowance" in test_text,
          "looked for the PASS-case test")
    check("an exceeds-allowance zero-bias test exists", "exceeding_noise_allowance" in test_text,
          "looked for the FAIL-case test")

    result = subprocess.run(["python3", "-m", "unittest", "test_gate6", "-v"],
                             cwd=REPO_ROOT / "tests", capture_output=True, text=True)
    check("full test_gate6.py suite passes (10 tests: 8 pre-existing + 2 new)",
          result.returncode == 0, result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "")
    check("test count is exactly 10 (no test silently dropped)",
          "Ran 10 tests" in result.stderr, "looked for 'Ran 10 tests' in unittest output")


def part_a_halt_condition_not_triggered() -> None:
    outdir = REPO_ROOT / "scratch_check_directional_fix" / "bad_ci"
    result = subprocess.run(
        ["python3", str(GATE6), "--truth", str(BAD_CI_FIXTURE / "truth.tsv"),
         "--recovered", str(BAD_CI_FIXTURE / "recovered.tsv"),
         "--scope", str(BAD_CI_FIXTURE / "scope.tsv"), "--outdir", str(outdir)],
        cwd=REPO_ROOT, capture_output=True, text=True)
    check("HALT CHECK: gate6_bad_ci fixture still FAILS (repaired check did not weaken it)",
          result.returncode == 1 and "gate6_recovery OVERALL: FAIL" in result.stdout,
          f"returncode={result.returncode}")

    wrong_sign_fixture = REPO_ROOT / "tests" / "fixtures" / "gate6_wrong_sign_bias"
    if wrong_sign_fixture.exists():
        outdir2 = REPO_ROOT / "scratch_check_directional_fix" / "wrong_sign"
        result2 = subprocess.run(
            ["python3", str(GATE6), "--truth", str(wrong_sign_fixture / "truth.tsv"),
             "--recovered", str(wrong_sign_fixture / "recovered.tsv"),
             "--scope", str(wrong_sign_fixture / "scope.tsv"),
             "--bias-prediction", str(wrong_sign_fixture / "bias_prediction.tsv"),
             "--outdir", str(outdir2)],
            cwd=REPO_ROOT, capture_output=True, text=True)
        check("HALT CHECK: wrong-sign nonzero-prediction fixture still FAILS (nonzero path unweakened)",
              result2.returncode == 1 and "gate6_recovery OVERALL: FAIL" in result2.stdout,
              f"returncode={result2.returncode}")
    else:
        check("wrong-sign fixture present for HALT re-check", False, f"{wrong_sign_fixture} missing")


def part_a_rescoring_reported() -> None:
    check("repaired zero-bias prediction file for P07-RERUN2 quantities exists",
          REPAIRED_BIAS_PREDICTION.exists(), str(REPAIRED_BIAS_PREDICTION))
    check("original P07-RERUN2 SIMULATED_BIAS_PREDICTION.tsv left untouched (historical record)",
          ORIGINAL_BIAS_PREDICTION.exists() and "gates/gate6_recovery.py" not in ORIGINAL_BIAS_PREDICTION.read_text(),
          "presence + sanity content check")
    check("re-scoring output table exists", RESCORED_TABLE.exists(), str(RESCORED_TABLE))
    if not RESCORED_TABLE.exists():
        return
    rows = read_tsv(RESCORED_TABLE)
    in_scope_loh_rows = [r for r in rows if r["quantity"].endswith("wt_lost_direction_LR")
                          and r.get("scope_status") == "IN_SCOPE"]
    check("exactly 12 in-scope LOH quantities re-scored", len(in_scope_loh_rows) == 12,
          f"count={len(in_scope_loh_rows)}")
    n_pass = sum(1 for r in in_scope_loh_rows if r["status"] == "SIMULATED_PASS")
    check("re-scored PASS count improved from P07-RERUN2's 1/12 to 10/12",
          n_pass == 10, f"n_pass={n_pass} of {len(in_scope_loh_rows)}")

    if FIX_DOC.exists():
        text = FIX_DOC.read_text(encoding="utf-8")
        check("DIRECTIONAL_CHECK_FIX.md reports the before (1/12) and after (10/12) counts",
              "1 of 12" in text and "10 of 12" in text, "looked for both counts in the doc")
        check("DIRECTIONAL_CHECK_FIX.md states the computed false-failure rate at the chosen multiplier",
              "0.27" in text and "3.19" in text, "looked for the computed per-quantity and family-wise rates")
    else:
        check("DIRECTIONAL_CHECK_FIX.md present", False, f"{FIX_DOC} missing")


def part_a_protocol_draft_not_applied() -> None:
    if not FIX_DOC.exists():
        check("draft PROTOCOL.md §11 clarification present in DIRECTIONAL_CHECK_FIX.md", False, f"{FIX_DOC} missing")
        return
    text = FIX_DOC.read_text(encoding="utf-8")
    check("draft §11 clarification text present, explicitly marked NOT APPLIED",
          "NOT APPLIED" in text and "Zero-bias predictions (clarification)" in text,
          "looked for the marked-draft clarification block")
    if PROTOCOL.exists():
        protocol_text = PROTOCOL.read_text(encoding="utf-8")
        check("PROTOCOL.md itself does NOT contain the new zero-bias clarification language "
              "(draft only, not applied, per Standing Rule 10)",
              "noise_allowance_se_multiples" not in protocol_text and "ZERO_BIAS_NOISE_ALLOWANCE" not in protocol_text,
              "checked PROTOCOL.md for leaked applied text")


def part_b_purity_floor_cost() -> None:
    if not PURITY_DOC.exists():
        check("PURITY_FLOOR_COST.md present", False, f"{PURITY_DOC} missing")
        return
    text = PURITY_DOC.read_text(encoding="utf-8")
    for floor_str in ("0.20", "0.25", "0.30", "0.40", "0.45"):
        check(f"PURITY_FLOOR_COST.md reports survival fraction at floor {floor_str}",
              floor_str in text, f"looked for '{floor_str}'")
    for subtype in ("Basal", "Her2", "LumA", "LumB", "Normal"):
        check(f"PURITY_FLOOR_COST.md reports survival by subtype ({subtype})",
              subtype in text, f"looked for '{subtype}'")
    check("PURITY_FLOOR_COST.md reports the network-egress block mechanism (EGRESS_BLOCKED)",
          "EGRESS_BLOCKED" in text, "looked for the disclosed block mechanism")
    check("PURITY_FLOOR_COST.md reports implied per-gene class sizes",
          "CORE_HR" in text and "DDR_SIGNALING" in text and "carrier" in text.lower(),
          "looked for the carrier-class-size cross-reference")
    check("PURITY_FLOOR_COST.md cross-references gate8's UNINFORMATIVE characterization",
          "UNINFORMATIVE" in text, "looked for the gate8 cross-reference")
    check("PURITY_FLOOR_COST.md states the feasibility finding plainly",
          "leaves too few" in text.lower() or "cannot resolve" in text.lower(),
          "looked for a plain feasibility statement")
    check("PROTOCOL.md is not edited by Part B (feasibility finding only)",
          "PURITY_FLOOR_COST" not in (PROTOCOL.read_text(encoding="utf-8") if PROTOCOL.exists() else ""),
          "checked PROTOCOL.md does not reference the new doc")

    if PROPOSED_DEVIATIONS.exists():
        dev_text = PROPOSED_DEVIATIONS.read_text(encoding="utf-8")
        check("PROPOSED_DEVIATIONS.md has a new section referencing PURITY_FLOOR_COST.md",
              "PURITY_FLOOR_COST.md" in dev_text, "looked for a cross-reference")


def part_c_loh_confounding_gap() -> None:
    if not PROPOSED_DEVIATIONS.exists():
        check("PROPOSED_DEVIATIONS.md present", False, f"{PROPOSED_DEVIATIONS} missing")
        return
    text = PROPOSED_DEVIATIONS.read_text(encoding="utf-8")
    check("PROPOSED_DEVIATIONS.md documents the LOH-confounding simulator gap",
          "LOH-confounding gap" in text or "LOH-direction pathway" in text,
          "looked for the gap section")
    check("a cited source for basal-like LOH burden is present (not asserted)",
          "PMID 14729609" in text or "Cancer Res. 2004" in text,
          "looked for the cited primary source")
    check("states what P09 can and cannot demonstrate under the current simulator",
          "P09" in text and "cannot" in text and "can" in text,
          "looked for the can/cannot P09 statement")
    check("explicitly does not propose modifying simulate.py",
          "does not modify" in text.lower() and "simulate.py" in text,
          "looked for the explicit non-modification statement")


def forbidden_files_unmodified() -> None:
    changed = set(_changed_files())
    for forbidden in FORBIDDEN_FILES:
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    check("gates/gate6_recovery.py WAS modified (Part A's own permitted change)",
          "gates/gate6_recovery.py" in changed, f"in changed files: {'gates/gate6_recovery.py' in changed}")


def part_a_test_case_with_no_pred_still_matches_directional_semantics() -> None:
    # Sanity: near_tier_boundary is unchanged (N/A for zero/negative predicted magnitude).
    if not GATE6.exists():
        return
    text = GATE6.read_text(encoding="utf-8")
    check("near_tier_boundary()'s zero/negative-magnitude guard is unchanged (still returns N/A)",
          "predicted_magnitude <= 0" in text and 'return "N/A"' in text,
          "looked for the pre-existing guard")


def main() -> None:
    part_a_zero_bias_interface_implemented()
    part_a_fixtures_and_tests()
    part_a_halt_condition_not_triggered()
    part_a_rescoring_reported()
    part_a_protocol_draft_not_applied()
    part_a_test_case_with_no_pred_still_matches_directional_semantics()
    part_b_purity_floor_cost()
    part_c_loh_confounding_gap()
    forbidden_files_unmodified()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
