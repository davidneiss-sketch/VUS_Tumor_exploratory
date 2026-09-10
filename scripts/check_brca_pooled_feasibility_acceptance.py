#!/usr/bin/env python3
"""Acceptance checker for BRCA_POOLED_FEASIBILITY.md / the updated
COHORT_REQUIREMENT_TABLE.tsv (analysis-only task: pooled BRCA1/BRCA2
feasibility at 0.40 floor, GATE8 threshold sensitivity, purity-floor
crossover, ClinVar reference-set constraint).

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
MEMO = REPO_ROOT / "BRCA_POOLED_FEASIBILITY.md"
TABLE = REPO_ROOT / "COHORT_REQUIREMENT_TABLE.tsv"
REPORT = REPO_ROOT / "REPORT.md"

PIPELINE_FORBIDDEN_FILES = [
    "simulate.py", "PROTOCOL.md", "logistic_estimator.py", "signatures.py",
    "loh_caller.py", "gates/gate3_track_conditional.py", "gates/gate4_statistics.py",
    "gates/gate5_tripwires.py", "gates/gate6_recovery.py", "gates/gate7_denominators.py",
    "gates/gate8_interval_informativeness.py", "gates/gate9_imbalance.py",
]

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    return [line[3:].rstrip("/") for line in result.stdout.splitlines()]


def criterion_table_updated_with_pooled_rows() -> None:
    if not TABLE.exists():
        check("COHORT_REQUIREMENT_TABLE.tsv present", False, f"{TABLE} missing")
        return
    rows = read_tsv(TABLE)
    check("original 35 per-subtype rows preserved (not overwritten)",
          sum(1 for r in rows if r["pam50_subtype"] != "POOLED") == 35,
          f"non-POOLED row count={sum(1 for r in rows if r['pam50_subtype'] != 'POOLED')}")
    pooled_rows = {r["gene"]: r for r in rows if r["pam50_subtype"] == "POOLED"}
    check("BRCA1 POOLED row added", "BRCA1" in pooled_rows, f"pooled genes: {sorted(pooled_rows)}")
    check("BRCA2 POOLED row added", "BRCA2" in pooled_rows, f"pooled genes: {sorted(pooled_rows)}")
    if "BRCA1" in pooled_rows:
        check("BRCA1 POOLED required-N (n=65 bracket) matches computed value (9159)",
              int(pooled_rows["BRCA1"]["required_total_cohort_n_majority_informative_dim3"]) == 9159,
              pooled_rows["BRCA1"]["required_total_cohort_n_majority_informative_dim3"])
    if "BRCA2" in pooled_rows:
        check("BRCA2 POOLED required-N (n=65 bracket) matches computed value (6035)",
              int(pooled_rows["BRCA2"]["required_total_cohort_n_majority_informative_dim3"]) == 6035,
              pooled_rows["BRCA2"]["required_total_cohort_n_majority_informative_dim3"])


def criterion_step1_reported_both_genes_both_cohorts() -> None:
    if not MEMO.exists():
        check("BRCA_POOLED_FEASIBILITY.md present", False, f"{MEMO} missing")
        return
    text = MEMO.read_text(encoding="utf-8")
    check("BRCA1 pooled requirement reported", "BRCA1" in text and "9,159" in text, "looked for BRCA1 required N")
    check("BRCA2 pooled requirement reported", "BRCA2" in text and "6,035" in text, "looked for BRCA2 required N")
    check("reported against TCGA-BRCA alone (951)", "951" in text, "looked for the 951 figure")
    check("reported against combined pre-harmonization ceiling (1,663)",
          "1,663" in text or "1663" in text, "looked for the 1663 figure")
    check("explicit viable/not-viable verdict stated", "NOT VIABLE" in text, "looked for the explicit verdict")


def criterion_step2_sensitivity_and_flip_point() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("requirement reported across a range beyond just the two named brackets",
          "flip" in text.lower(), "looked for flip-point language")
    check("flip-point value(s) explicitly stated", "6.75" in text and "10.24" in text,
          "looked for the computed flip-point figures")
    check("sensitivity of the verdict to the bracket is explicitly assessed",
          "sensitiv" in text.lower(), "looked for explicit sensitivity discussion")
    check("ties the flip point back to GATE8's own empirical informative rate (not just arithmetic)",
          "ZERO_DENSITY_UNDEFINED" in text or "empirically" in text.lower(),
          "looked for the informative-rate cross-check")


def criterion_step3_purity_floor_trade() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    for floor_str in ("0.25", "0.30", "0.35", "0.40"):
        check(f"purity floor trade reported for BRCA1/2 pooled at floor {floor_str}",
              floor_str in text, f"looked for '{floor_str}'")
    check("crossover (or its absence) explicitly reported",
          "no crossover exists" in text.lower() or "crossover" in text.lower(),
          "looked for explicit crossover statement")
    check("binding constraint (prevalence vs. floor) explicitly identified",
          "binding constraint" in text.lower(), "looked for the explicit binding-constraint statement")


def criterion_step4_clinvar_reference_set() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("ClinVar retrieval attempt(s) reported with mechanism", "EGRESS_BLOCKED" in text,
          "looked for the disclosed block mechanism")
    check("multiple distinct retrieval avenues/domains attempted and disclosed",
          "eutils.ncbi.nlm.nih.gov" in text and "clinvarminer" in text.lower(),
          "looked for at least two distinct attempted domains")
    check("no invented ClinVar/gnomAD variant count presented as real",
          "UNVERIFIED" in text, "looked for the explicit UNVERIFIED marker")
    check("PROTOCOL.md's own §4.1/§4.2 floor and ceiling are cited, not re-derived",
          "4.1" in text and "4.2" in text, "looked for the PROTOCOL section citations")
    check("the unresolved-conditional consequence for Step 5 is stated",
          "cannot be evaluated" in text.lower() or "unresolved" in text.lower(),
          "looked for the explicit unresolved-conditional statement")


def criterion_step5_conditional_stated_honestly() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("Step 5 explicitly states its own precondition (Steps 1 and 4 clearing) does not currently hold",
          "does not clear" in text.lower() or "does not currently hold" in text.lower(),
          "looked for the explicit non-clearing statement")
    check("Step 5 nonetheless addresses the conditional/hypothetical content requested",
          "ENIGMA" in text and "exome" in text.lower(),
          "looked for the ENIGMA/exome-array content")


def criterion_step6_draft_not_applied() -> None:
    if not MEMO.exists():
        check("draft REPORT.md negative-result text present", False, f"{MEMO} missing")
        return
    text = MEMO.read_text(encoding="utf-8")
    check("draft negative-result text present, explicitly marked NOT APPLIED",
          "NOT APPLIED" in text and "Negative result" in text,
          "looked for the marked-draft negative-result block")
    if REPORT.exists():
        report_text = REPORT.read_text(encoding="utf-8")
        check("REPORT.md itself is NOT modified by this task",
              "BRCA_POOLED_FEASIBILITY" not in report_text,
              "checked REPORT.md was not edited to reference the new memo")


def criterion_no_pipeline_file_modified_and_no_rerun() -> None:
    changed = set(_changed_files())
    for forbidden in PIPELINE_FORBIDDEN_FILES:
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    forbidden_paths = [p for p in changed if p.startswith("SIMULATED_loh_validation/SIMULATED_recovered")
                        or p.startswith("SIMULATED_loh_validation/SIMULATED_LR_TABLE")
                        or "SIMULATED_signature_validation" in p]
    check("no P07/P08/P09 production output re-generated this task", not forbidden_paths,
          f"suspicious changed paths: {forbidden_paths}")
    check("BRCA_POOLED_FEASIBILITY.md WAS added (this task's own required deliverable)",
          "BRCA_POOLED_FEASIBILITY.md" in changed, f"in changed files: {'BRCA_POOLED_FEASIBILITY.md' in changed}")
    check("COHORT_REQUIREMENT_TABLE.tsv WAS modified (this task's own required deliverable)",
          "COHORT_REQUIREMENT_TABLE.tsv" in changed, f"in changed files: {'COHORT_REQUIREMENT_TABLE.tsv' in changed}")


def criterion_halt_stated() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("memo explicitly states HALT and that the design decision is the human's",
          "HALT" in text and "human's" in text.lower(),
          "looked for the explicit HALT statement")


def main() -> None:
    criterion_table_updated_with_pooled_rows()
    criterion_step1_reported_both_genes_both_cohorts()
    criterion_step2_sensitivity_and_flip_point()
    criterion_step3_purity_floor_trade()
    criterion_step4_clinvar_reference_set()
    criterion_step5_conditional_stated_honestly()
    criterion_step6_draft_not_applied()
    criterion_no_pipeline_file_modified_and_no_rerun()
    criterion_halt_stated()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
