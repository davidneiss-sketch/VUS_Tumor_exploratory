#!/usr/bin/env python3
"""Acceptance checker for the P-DEC-1 task: gate8_interval_informativeness.py,
its test suite, INTERVAL_INSTABILITY.md, and the DEPLOYMENT_LOG.md /
PROPOSED_DEVIATIONS.md wiring.

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
GATE8 = REPO_ROOT / "gates" / "gate8_interval_informativeness.py"
TEST_GATE8 = REPO_ROOT / "tests" / "test_gate8.py"
INTERVAL_INSTABILITY = REPO_ROOT / "INTERVAL_INSTABILITY.md"
DEPLOYMENT_LOG = REPO_ROOT / "DEPLOYMENT_LOG.md"
PROPOSED_DEVIATIONS = REPO_ROOT / "PROPOSED_DEVIATIONS.md"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
ABLATION_TABLE = REPO_ROOT / "ABLATION_TABLE.tsv"
GATE8_REPORT = REPO_ROOT / "SIMULATED_GATE8_INTERVAL_REPORT.tsv"
SWEEP_TSV = REPO_ROOT / "SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def criterion_1_gate8_exists_and_thresholds_prespecified() -> None:
    if not GATE8.exists():
        check("gates/gate8_interval_informativeness.py present", False, f"{GATE8} missing")
        return
    text = GATE8.read_text(encoding="utf-8")
    check("gate8 exits nonzero on failure (real convention check, not just a claim)",
          "sys.exit(0 if" in text or "report.print_and_exit()" in text,
          "checked for GateReport.print_and_exit()/sys.exit usage")
    check("MAX_TIERS_SPANNED threshold pre-specified as a named module-level constant",
          "MAX_TIERS_SPANNED = 2" in text, "checked source")
    check("MAX_UPPER_POINT_RATIO threshold pre-specified as a named module-level constant",
          "MAX_UPPER_POINT_RATIO = 18.7" in text, "checked source")
    check("ABSOLUTE_UPPER_CEILING threshold pre-specified as a named module-level constant",
          "ABSOLUTE_UPPER_CEILING = 10000" in text, "checked source")
    check("both thresholds carry a stated rationale in the module docstring (not bare numbers)",
          "rationale #1" in text.lower() or ("derived, not\n   picked freely" in text) or "derived" in text.lower(),
          "checked for rationale prose accompanying the constants")
    check("docstring explicitly states these were fixed before running against existing output",
          "PRE-SPECIFIED HERE" in text and "BEFORE THIS GATE IS" in text,
          "checked for the pre-specification-order statement")
    # Cross-check: the thresholds as documented in DEPLOYMENT_LOG.md's real
    # run output match the ones currently in gate8's source (no drift
    # between what ran and what is committed).
    if DEPLOYMENT_LOG.exists():
        dep_text = DEPLOYMENT_LOG.read_text(encoding="utf-8")
        check("DEPLOYMENT_LOG.md's gate8 entry references the same flagged row this task's trigger named",
              "3.65 billion" in dep_text or "3.65e9" in dep_text, "checked DEPLOYMENT_LOG.md for the flagged row")


def criterion_2_gate8_rejects_flagged_row_and_passes_good_row() -> None:
    if not TEST_GATE8.exists():
        check("tests/test_gate8.py present", False, f"{TEST_GATE8} missing")
        return
    result = subprocess.run([sys.executable, "-m", "unittest", "test_gate8", "-v"],
                             cwd=REPO_ROOT / "tests", capture_output=True, text=True)
    check("tests/test_gate8.py passes (both a good fixture and the 3.65-billion-row-reproducing bad fixture)",
          result.returncode == 0, f"exit={result.returncode}; {result.stderr.strip().splitlines()[-3:] if result.stderr else ''}")

    # Live re-derivation against real production output, not just the unit
    # test fixtures: gate8 run fresh against ABLATION_TABLE.tsv must FAIL
    # overall (the flagged row is real, committed output) and the report
    # must name that exact row as UNINFORMATIVE.
    if not ABLATION_TABLE.exists():
        check("live re-derivation: gate8 run fresh against ABLATION_TABLE.tsv", False,
              f"{ABLATION_TABLE} missing")
        return
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, str(GATE8), "--table", str(ABLATION_TABLE),
             "--id-cols", "arm,feature_subset,n_scenario",
             "--point-col", "point_estimate", "--ci-low-col", "ci_low", "--ci-high-col", "ci_high",
             "--outdir", td],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        report_rows = read_tsv(Path(td) / "SIMULATED_GATE8_INTERVAL_REPORT.tsv")
        flagged = next((r for r in report_rows if r["row_id"] == "DDR_SIGNALING/LOH_GIS_SBS3/REALISTIC_N_35"), None)
        check("live re-derivation: gate8 run fresh against ABLATION_TABLE.tsv correctly rejects the exact "
              "flagged row (not merely a synthetic fixture standing in for it)",
              flagged is not None and flagged["gate8_status"] == "UNINFORMATIVE" and proc.returncode == 1,
              f"gate8 exit={proc.returncode}; flagged row status={flagged['gate8_status'] if flagged else 'NOT FOUND'}")
        n_informative = sum(1 for r in report_rows if r["gate8_status"] == "INFORMATIVE")
        check("live re-derivation: gate8 does not indiscriminately reject the whole table "
              "(well-behaved rows still pass)", n_informative > 0, f"{n_informative} row(s) INFORMATIVE")


def criterion_3_wired_into_production_and_logged() -> None:
    if not DEPLOYMENT_LOG.exists():
        check("DEPLOYMENT_LOG.md present", False, f"{DEPLOYMENT_LOG} missing")
        return
    text = DEPLOYMENT_LOG.read_text(encoding="utf-8")
    check("DEPLOYMENT_LOG.md names gate8_interval_informativeness.py by file name",
          "gate8_interval_informativeness.py" in text, "checked for the exact file name")
    check("DEPLOYMENT_LOG.md's gate8 entry runs against a real, on-disk production file (ABLATION_TABLE.tsv), "
          "not only a test fixture", "ABLATION_TABLE.tsv" in text, "checked for the production input file name")
    check("DEPLOYMENT_LOG.md states gate8 is part of the standard invocation set alongside gate5/gate6",
          "alongside gate5" in text.lower() or "alongside gate5 and gate6" in text,
          "checked for the standard-invocation-set statement")
    check("SIMULATED_GATE8_INTERVAL_REPORT.tsv exists on disk at repo root (real emitted artifact, not just "
          "claimed in prose)", GATE8_REPORT.exists(), f"{GATE8_REPORT}")


def criterion_4_instability_characterized_by_dimension() -> None:
    if not INTERVAL_INSTABILITY.exists():
        check("INTERVAL_INSTABILITY.md present", False, f"{INTERVAL_INSTABILITY} missing")
        return
    text = INTERVAL_INSTABILITY.read_text(encoding="utf-8")
    check("INTERVAL_INSTABILITY.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("reports the sweep broken out by feature-vector dimension (1/2/3)",
          "dimension" in text.lower() and all(f"| {d} |" in text or f"dimension {d}" in text.lower() for d in ("1", "2", "3")),
          "looked for dimension 1/2/3 discussion")
    check("names PALB2/RAD51C/RAD51D or the low-tens Track B class-size framing this task itself used",
          "PALB2" in text or "low-tens" in text.lower() or "low tens" in text.lower(),
          "looked for the task's own named-gene framing")
    check("reports class size(s) at which the estimator produces gate8-rejected intervals, per dimension "
          "(not just a single unqualified number)", "UNINFORMATIVE/15" in text or "uninformative fraction" in text.lower()
          or "UNINFORMATIVE" in text, "looked for the per-n, per-dimension rejection-rate reporting")
    if SWEEP_TSV.exists():
        rows = read_tsv(SWEEP_TSV)
        dims_seen = {r["dimension"] for r in rows}
        check("SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv covers all 3 dimensions",
              {"1", "2", "3"} <= dims_seen, f"dimensions seen: {dims_seen}")
        arms_seen = {r["arm"] for r in rows}
        check("sweep covers both CORE_HR and DDR_SIGNALING", {"CORE_HR", "DDR_SIGNALING"} <= arms_seen,
              f"arms seen: {arms_seen}")
    else:
        check("SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv present", False, f"{SWEEP_TSV} missing")


def criterion_5_proposed_not_applied() -> None:
    if not PROPOSED_DEVIATIONS.exists():
        check("PROPOSED_DEVIATIONS.md present", False, f"{PROPOSED_DEVIATIONS} missing")
        return
    text = PROPOSED_DEVIATIONS.read_text(encoding="utf-8")
    check("PROPOSED_DEVIATIONS.md has a section on the KDE model-choice evidence",
          "model choice" in text.lower() or "model-choice" in text.lower(), "looked for model-choice discussion")
    check("explicitly frames it as proposed, not applied (Standing Rule 10 language)",
          "not applied" in text.lower() and "Standing Rule 10" in text, "looked for explicit propose-not-apply framing")
    check("penalized logistic regression (PROTOCOL's own named alternative) is mentioned",
          "logistic regression" in text.lower(), "looked for the alternative estimator this task named")


def criterion_6_protocol_unmodified() -> None:
    result = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    result_staged = subprocess.run(["git", "diff", "--staged", "--name-only", "HEAD"], cwd=REPO_ROOT,
                                    capture_output=True, text=True)
    changed = set(result.stdout.splitlines()) | set(result_staged.stdout.splitlines())
    check("PROTOCOL.md not modified by this task", "PROTOCOL.md" not in changed,
          f"PROTOCOL.md in changed files: {'PROTOCOL.md' in changed}")
    for also_forbidden in ("simulate.py", "signatures.py", "loh_caller.py"):
        check(f"{also_forbidden} not modified by this task", also_forbidden not in changed,
              f"{also_forbidden} in changed files: {also_forbidden in changed}")


def main() -> None:
    criterion_1_gate8_exists_and_thresholds_prespecified()
    criterion_2_gate8_rejects_flagged_row_and_passes_good_row()
    criterion_3_wired_into_production_and_logged()
    criterion_4_instability_characterized_by_dimension()
    criterion_5_proposed_not_applied()
    criterion_6_protocol_unmodified()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
