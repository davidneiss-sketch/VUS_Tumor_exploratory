#!/usr/bin/env python3
"""Acceptance check for the gate2..gate7 verification machinery
(Standing Rule 6): emits PASS/FAIL per criterion by actually re-running
the gates and the test suite, never by trusting what TRIPWIRE_EVIDENCE.md
or DEPLOYMENT_LOG.md merely claims happened.

Criteria, copied from the task's ACCEPTANCE section:
  1. Every gate has a passing and a failing test, with failure output shown.
  2. gate4 rejects a table with a CI excluding its estimate.
  3. gate5 flags an AUC of 0.998 and an exact benchmark match.
  4. gate6 rejects a recovered CI of [7.47, 11.25] against an injected 4.5,
     and rejects an OR-vs-LR comparison.
  5. The run log shows gate5 and gate6 evaluated against named production
     files.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATES = ROOT / "gates"
FIXTURES = ROOT / "tests" / "fixtures"
PRODUCTION = ROOT / "production"

results = []


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=60)


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def criterion_1_every_gate_has_pass_and_fail_test():
    r = run([sys.executable, "tests/run_all_tests.py"])
    combined = r.stdout + r.stderr
    ok = r.returncode == 0
    test_names = re.findall(r"test_(\S+) \(test_gate(\d)\.", combined)
    per_gate = {}
    for name, gate_num in test_names:
        per_gate.setdefault(gate_num, set()).add(name)
    missing = []
    for gate_num in ["2", "3", "4", "5", "6", "7"]:
        names = per_gate.get(gate_num, set())
        has_pass_test = any("good" in n or "passes" in n for n in names)
        has_fail_test = any("bad" in n for n in names)
        if not (has_pass_test and has_fail_test):
            missing.append(f"gate{gate_num}: pass_test={has_pass_test}, fail_test={has_fail_test}, tests_seen={sorted(names)}")
    check(
        "every gate has a passing and a failing test; full suite passes",
        ok and not missing,
        (f"test suite exit={r.returncode}; " + ("; ".join(missing) if missing else "every gate2..gate7 has >=1 good-fixture and >=1 bad-fixture test")),
    )


def criterion_2_gate4_rejects_ci_excluding_estimate():
    r = run([sys.executable, "gates/gate4_statistics.py", "--lr-table",
             str(FIXTURES / "gate4_bad" / "lr_table.tsv")])
    ok = r.returncode == 1 and "does not contain point estimate" in r.stdout
    check(
        "gate4 rejects a table with a CI excluding its estimate",
        ok,
        f"exit={r.returncode}; " + ("found the expected rejection message" if ok else r.stdout + r.stderr),
    )


def criterion_3_gate5_flags_auc_and_exact_match():
    d = FIXTURES / "gate5_bad"
    r = run([sys.executable, "gates/gate5_tripwires.py",
             "--metrics", str(d / "metrics.tsv"), "--thresholds", str(d / "thresholds.tsv"),
             "--circularity", str(d / "circularity.tsv"), "--lr-table", str(d / "lr_table.tsv")])
    flags_auc = "0.998" in r.stdout and "ceiling" in r.stdout
    flags_exact_match = "exact_match_metric" in r.stdout and "0.000% apart" in r.stdout
    ok = r.returncode == 1 and flags_auc and flags_exact_match
    check(
        "gate5 flags an AUC of 0.998 and an exact benchmark match",
        ok,
        f"exit={r.returncode}, flags_auc={flags_auc}, flags_exact_match={flags_exact_match}",
    )


def criterion_4_gate6_rejects_ci_and_or_vs_lr():
    d1 = FIXTURES / "gate6_bad_ci"
    r1 = run([sys.executable, "gates/gate6_recovery.py",
              "--truth", str(d1 / "truth.tsv"), "--recovered", str(d1 / "recovered.tsv"),
              "--scope", str(d1 / "scope.tsv"),
              "--outdir", "/tmp/check_gates_acceptance_ci_out"])
    ci_ok = r1.returncode == 1 and "[7.47, 11.25]" in r1.stdout and "4.5" in r1.stdout

    d2 = FIXTURES / "gate6_bad_estimand"
    r2 = run([sys.executable, "gates/gate6_recovery.py",
              "--truth", str(d2 / "truth.tsv"), "--recovered", str(d2 / "recovered.tsv"),
              "--scope", str(d2 / "scope.tsv"),
              "--outdir", "/tmp/check_gates_acceptance_estimand_out"])
    or_lr_ok = r2.returncode == 1 and "MISMATCH" in r2.stdout and "truth=LR, recovered=OR" in r2.stdout

    check(
        "gate6 rejects CI [7.47, 11.25] vs injected 4.5, and rejects an OR-vs-LR comparison",
        ci_ok and or_lr_ok,
        f"ci_case: exit={r1.returncode}, ok={ci_ok}; estimand_case: exit={r2.returncode}, ok={or_lr_ok}",
    )


def criterion_5_gate5_gate6_ran_against_named_production_files():
    dep_log = ROOT / "DEPLOYMENT_LOG.md"
    if not dep_log.exists():
        check("DEPLOYMENT_LOG.md shows gate5/gate6 evaluated against named production files", False, "DEPLOYMENT_LOG.md missing")
        return
    text = dep_log.read_text()

    # The log must name the actual production files (not just say "production data").
    required_names = [
        "SIMULATED_metrics.tsv", "SIMULATED_thresholds.tsv", "SIMULATED_circularity.tsv",
        "SIMULATED_TRUTH.tsv", "SIMULATED_RECOVERED.tsv", "SIMULATED_LR_TABLE.tsv",
    ]
    missing_names = [n for n in required_names if n not in text]

    # And it must show a PASS/exit-0 result for gate5 and gate6 specifically.
    gate5_section = re.search(r"### gate5_tripwires\.py.*?(?=\n### |\Z)", text, re.DOTALL)
    gate6_section = re.search(r"### gate6_recovery\.py.*?(?=\n### |\Z)", text, re.DOTALL)
    gate5_documented = bool(gate5_section and "EXIT_CODE=0" in gate5_section.group(0))
    gate6_documented = bool(gate6_section and "EXIT_CODE=0" in gate6_section.group(0))

    # Live re-check: production files must actually exist and gate5/gate6 must
    # actually pass against them right now, not just as a historical claim.
    live_ok = True
    live_detail = []
    if PRODUCTION.exists():
        r5 = run([sys.executable, "gates/gate5_tripwires.py",
                  "--metrics", str(PRODUCTION / "SIMULATED_metrics.tsv"),
                  "--thresholds", str(PRODUCTION / "SIMULATED_thresholds.tsv"),
                  "--circularity", str(PRODUCTION / "SIMULATED_circularity.tsv"),
                  "--lr-table", str(PRODUCTION / "SIMULATED_LR_TABLE.tsv")])
        r6 = run([sys.executable, "gates/gate6_recovery.py",
                  "--truth", str(PRODUCTION / "SIMULATED_TRUTH.tsv"),
                  "--recovered", str(PRODUCTION / "SIMULATED_RECOVERED.tsv"),
                  "--scope", str(PRODUCTION / "SIMULATED_scope.tsv"),
                  "--outdir", str(PRODUCTION)])
        live_ok = r5.returncode == 0 and r6.returncode == 0
        live_detail.append(f"live re-run: gate5 exit={r5.returncode}, gate6 exit={r6.returncode}")
    else:
        live_ok = False
        live_detail.append("production/ directory missing — cannot live-verify")

    ok = not missing_names and gate5_documented and gate6_documented and live_ok
    check(
        "DEPLOYMENT_LOG.md shows gate5/gate6 evaluated against named production files",
        ok,
        f"missing_file_names={missing_names}, gate5_documented={gate5_documented}, "
        f"gate6_documented={gate6_documented}; {'; '.join(live_detail)}",
    )


def main():
    criterion_1_every_gate_has_pass_and_fail_test()
    criterion_2_gate4_rejects_ci_excluding_estimate()
    criterion_3_gate5_flags_auc_and_exact_match()
    criterion_4_gate6_rejects_ci_and_or_vs_lr()
    criterion_5_gate5_gate6_ran_against_named_production_files()

    overall = True
    for name, passed, detail in results:
        verdict = "PASS" if passed else "FAIL"
        overall = overall and passed
        print(f"[{verdict}] {name} — {detail}")

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
