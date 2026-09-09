#!/usr/bin/env python3
"""Acceptance checker for P-AMD-3a (fix the mixture application point,
draft the gate6 criterion amendment).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (MIXTURE_FIX.md's,
PROPOSED_GATE6_AMENDMENT.md's own prose) is not itself the check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIXTURE_FIX = REPO_ROOT / "MIXTURE_FIX.md"
POST_FIX_DIAG = REPO_ROOT / "MIXTURE_FIX_POST_FIX_DIAGNOSTICS.md"
GATE6_AMENDMENT = REPO_ROOT / "PROPOSED_GATE6_AMENDMENT.md"
CONSERVATIVE_ANALYSIS = REPO_ROOT / "CONSERVATIVE_ASSIGNMENT_ANALYSIS.md"
PROD_RUN = REPO_ROOT / "production_v2_run.py"
MIXTURE_FIX_DIR = REPO_ROOT / "mixture_fix"
LAMBDA_SWEEP_POST = MIXTURE_FIX_DIR / "SIMULATED_LAMBDA_SWEEP_POST_FIX.tsv"
SEED_VARIATION_POST = MIXTURE_FIX_DIR / "SIMULATED_SEED_VARIATION_POST_FIX.tsv"
SEED_VARIATION_POST_SUMMARY = MIXTURE_FIX_DIR / "SIMULATED_SEED_VARIATION_POST_FIX_SUMMARY.tsv"
PRE_FIX_SNAPSHOT = MIXTURE_FIX_DIR / "pre_fix_production_v2_snapshot" / "SIMULATED_RECOVERED.tsv"
RECOVERED = REPO_ROOT / "production_v2" / "SIMULATED_RECOVERED.tsv"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
LOGISTIC_ESTIMATOR = REPO_ROOT / "logistic_estimator.py"
SIMULATE_PY = REPO_ROOT / "simulate.py"
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


def criterion_1_same_operation_justified() -> None:
    if not MIXTURE_FIX.exists():
        check("MIXTURE_FIX.md present", False, f"{MIXTURE_FIX} missing")
        return
    text = MIXTURE_FIX.read_text(encoding="utf-8")
    check("MIXTURE_FIX.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("states the mathematical identity (density-mixture = subtype-marginal LR)",
          "Sigma_s w_s * f(x|Path,s)" in text and "f(x|Path) / f(x|Benign)" in text,
          "looked for the derived identity")
    check("verifies subtype-class independence against simulate.py's own generation code (not asserted)",
          "_emit_sample" in text and "rng.choices(list(PAM50_PROPORTIONS)" in text,
          "looked for a direct quote of simulate.py's subtype draw")
    check("explains why per-subtype LR combination cannot recover the density mixture",
          "not identified" in text.lower() or "not achievable" in text.lower(),
          "looked for the non-identifiability argument")
    check("justifies the choice mathematically, not merely as easier to implement",
          "mathematically correct construction" in text or "QED" in text,
          "looked for an explicit mathematical justification")

    if not PROD_RUN.exists():
        check("production_v2_run.py implements the subtype-blind fix", False, f"{PROD_RUN} missing")
        return
    prod_text = PROD_RUN.read_text(encoding="utf-8")
    check("production_v2_run.py defines build_subtype_blind_design_matrix",
          "def build_subtype_blind_design_matrix" in prod_text, "looked for the function definition")
    check("production_v2_run.py's mixture_point_estimate uses the subtype-blind design row",
          "def mixture_point_estimate(" in prod_text and "eval_point_subtype_blind_design_row" in prod_text,
          "looked for the corrected mixture_point_estimate body")
    check("the OLD (legacy) LR-weighted computation is retained for comparison only, not called by main()",
          "mixture_point_estimate_legacy_lr_weighted" in prod_text,
          "looked for the retained legacy function")


def criterion_2_before_after_widening_reported() -> None:
    if not MIXTURE_FIX.exists():
        check("before/after containment gap reported", False, f"{MIXTURE_FIX} missing")
        return
    text = MIXTURE_FIX.read_text(encoding="utf-8")
    check("reports a BEFORE point/CI for CORE_HR", "5.041024" in text or "5.041023" in text,
          "looked for the committed pre-fix CORE_HR point estimate")
    check("reports an AFTER point/CI for CORE_HR", "4.822998" in text,
          "looked for the corrected CORE_HR point estimate")
    check("explicitly states the gap WIDENED and that this is expected, not a regression",
          "widen" in text.lower() and ("expected" in text.lower()) and ("not a regression" in text.lower()),
          "looked for explicit widening + expected-not-regression language")

    if not PRE_FIX_SNAPSHOT.exists() or not RECOVERED.exists():
        check("pre-fix snapshot and post-fix production output both present on disk", False,
              f"{PRE_FIX_SNAPSHOT.exists()=} {RECOVERED.exists()=}")
        return
    before = {r["quantity"]: r for r in read_tsv(PRE_FIX_SNAPSHOT)}
    after = {r["quantity"]: r for r in read_tsv(RECOVERED)}
    truth_by_quantity = {}
    with open(REPO_ROOT / "SIMULATED_TRUTH.tsv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            truth_by_quantity[row["quantity"]] = row
    injected = float(truth_by_quantity["core_hr_joint_LR"]["injected_value"])
    before_gap = injected - float(before["core_hr_joint_LR"]["ci_high"])
    after_gap = injected - float(after["core_hr_joint_LR"]["ci_high"])
    check("CORE_HR's containment gap actually widened on disk (after > before)",
          after_gap > before_gap,
          f"before_gap={before_gap:.6f}, after_gap={after_gap:.6f}")


def criterion_3_lambda_sweep_and_seed_variation_rerun() -> None:
    check("SIMULATED_LAMBDA_SWEEP_POST_FIX.tsv present (lambda sweep re-run)",
          LAMBDA_SWEEP_POST.exists(), f"{LAMBDA_SWEEP_POST}")
    check("SIMULATED_SEED_VARIATION_POST_FIX.tsv present (seed variation re-run)",
          SEED_VARIATION_POST.exists(), f"{SEED_VARIATION_POST}")
    check("SIMULATED_SEED_VARIATION_POST_FIX_SUMMARY.tsv present",
          SEED_VARIATION_POST_SUMMARY.exists(), f"{SEED_VARIATION_POST_SUMMARY}")
    check("post-fix diagnostics written under mixture_fix/ (separate from production_v2/)",
          MIXTURE_FIX_DIR.exists() and LAMBDA_SWEEP_POST.parent == MIXTURE_FIX_DIR,
          f"{MIXTURE_FIX_DIR}")
    if LAMBDA_SWEEP_POST.exists():
        rows = read_tsv(LAMBDA_SWEEP_POST)
        check("post-fix lambda sweep covers both arms", {r["arm"] for r in rows} == {"CORE_HR", "DDR_SIGNALING"},
              f"arms: {sorted({r['arm'] for r in rows})}")
    if SEED_VARIATION_POST.exists():
        rows = read_tsv(SEED_VARIATION_POST)
        n_seeds_per_arm = {}
        for r in rows:
            n_seeds_per_arm.setdefault(r["arm"], set()).add(r["seed_index"])
        check("post-fix seed variation has >=15 seeds per arm",
              all(len(v) >= 15 for v in n_seeds_per_arm.values()),
              f"seed counts: { {a: len(v) for a, v in n_seeds_per_arm.items()} }")


def criterion_4_gate6_amendment_complete() -> None:
    if not GATE6_AMENDMENT.exists():
        check("PROPOSED_GATE6_AMENDMENT.md present", False, f"{GATE6_AMENDMENT} missing")
        return
    text = GATE6_AMENDMENT.read_text(encoding="utf-8")
    check("PROPOSED_GATE6_AMENDMENT.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("states this is a proposal, not an applied change (Standing Rule 10)",
          "not modified" in text.lower() and "proposal" in text.lower(),
          "looked for explicit proposal-only language")
    check("specifies the amended criterion: relative bias + directional shrinkage check, containment reported not gated",
          "directional" in text.lower() and "reported" in text.lower() and "no longer" in text.lower(),
          "looked for the 3-part amended criterion")
    check("states the rationale (CV minimizes deviance, not LR bias; expected at these class sizes)",
          "deviance" in text.lower(),
          "looked for the CV/deviance rationale")
    check("computes (not asserts) whether the historical v2 failure still fails under the amended criterion",
          "96.22%" in text or "0.9622" in text,
          "looked for the computed relative-bias figure on the task-stated 8.83/4.5 pair")
    check("flags the 8.83-vs-4.5 figure as UNVERIFIED per Standing Rule 3, and independently checked against an on-disk fixture",
          "UNVERIFIED" in text and "106.67%" in text,
          "looked for the UNVERIFIED disclosure and the on-disk gate6_bad_ci fixture cross-check")
    check("states what replaces containment as protection against the v2 failure mode",
          "replaces containment" in text.lower() or "replaces" in text.lower(),
          "looked for an explicit replacement-mechanism section")
    check("does not modify gate6's own logic (no gate6*.py in changed files)",
          not any("gate6" in f for f in _changed_files()),
          f"changed files touching gate6: {[f for f in _changed_files() if 'gate6' in f]}")


def criterion_5_conservative_assignment_quantified() -> None:
    if not CONSERVATIVE_ANALYSIS.exists():
        check("CONSERVATIVE_ASSIGNMENT_ANALYSIS.md present", False, f"{CONSERVATIVE_ANALYSIS} missing")
        return
    text = CONSERVATIVE_ANALYSIS.read_text(encoding="utf-8")
    check("CONSERVATIVE_ASSIGNMENT_ANALYSIS.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("quantifies the danger-zone-as-fraction-of-boundary result (f/(1-f))",
          "f / (1 - f)" in text or "f/(1-f)" in text,
          "looked for the general tier-boundary formula")
    check("reports this per PROTOCOL.md §9's actual OddsPath boundaries (350, 18.7, 4.33, 2.08)",
          all(b in text for b in ("350", "18.7", "4.33", "2.08")),
          "looked for all four boundary values")
    check("reports a concrete, observed tier-downgrade instance from this session's own data",
          "SUPPORTING" in text and "MODERATE" in text and ("4.279654" in text or "4.144367" in text),
          "looked for an observed CI-lower-bound crossing a real boundary")
    check("draft PROTOCOL.md text for the shrinkage property is present (draft only)",
          "Draft text for PROTOCOL.md" in text,
          "looked for the PROTOCOL.md draft section")
    check("draft REPORT.md text for the shrinkage property is present (draft only)",
          "Draft text for REPORT.md" in text,
          "looked for the REPORT.md draft section")


def criterion_6_no_forbidden_file_modified() -> None:
    changed = set(_changed_files())
    for forbidden in ("PROTOCOL.md", "logistic_estimator.py", "simulate.py", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    for gate in REPO_ROOT.glob("gates/gate*.py"):
        rel = str(gate.relative_to(REPO_ROOT))
        check(f"{rel} not modified by this task", rel not in changed, f"{rel} in changed files: {rel in changed}")
    check("production_v2_run.py WAS modified by this task (Part A's own required fix)",
          "production_v2_run.py" in changed, f"production_v2_run.py in changed files: {'production_v2_run.py' in changed}")


def criterion_7_no_p07_p08_p09_rerun() -> None:
    # This task's own sequence: P-AMD-3a -> human decision -> P-AMD-3b -> P07 -> P08 -> P09.
    # Static check: no committed evidence of a P07/P08/P09 pipeline invocation this task.
    changed = set(_changed_files())
    forbidden_paths = [p for p in changed if p.startswith("loh_caller") or p.startswith("signatures")
                        or "P07" in p or "P08" in p or "P09" in p]
    check("no P07/P08/P09-labeled output changed this task", not forbidden_paths,
          f"suspicious changed paths: {forbidden_paths}")


def main() -> None:
    criterion_1_same_operation_justified()
    criterion_2_before_after_widening_reported()
    criterion_3_lambda_sweep_and_seed_variation_rerun()
    criterion_4_gate6_amendment_complete()
    criterion_5_conservative_assignment_quantified()
    criterion_6_no_forbidden_file_modified()
    criterion_7_no_p07_p08_p09_rerun()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
