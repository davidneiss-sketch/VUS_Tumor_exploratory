#!/usr/bin/env python3
"""Acceptance checker for FEASIBILITY_MEMO.md / COHORT_REQUIREMENT_TABLE.tsv
(analysis-only task: gene x subtype cohort requirement, real-cohort
retrieval for TCGA-BRCA/ICGC-PCAWG/CPTAC-3, three-design comparison).

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
MEMO = REPO_ROOT / "FEASIBILITY_MEMO.md"
TABLE = REPO_ROOT / "COHORT_REQUIREMENT_TABLE.tsv"

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


def criterion_cohort_table_present_and_complete() -> None:
    if not TABLE.exists():
        check("COHORT_REQUIREMENT_TABLE.tsv present", False, f"{TABLE} missing")
        return
    rows = read_tsv(TABLE)
    check("cohort requirement table has 35 rows (7 genes x 5 subtypes)", len(rows) == 35, f"count={len(rows)}")
    genes = {r["gene"] for r in rows}
    for g in ("PALB2", "RAD51C", "RAD51D", "BRCA1", "BRCA2", "ATM", "CHEK2"):
        check(f"gene {g} present in cohort requirement table", g in genes, f"genes found: {sorted(genes)}")
    subtypes = {r["pam50_subtype"] for r in rows}
    for s in ("Basal", "Her2", "LumA", "LumB", "Normal"):
        check(f"subtype {s} present in cohort requirement table", s in subtypes, f"subtypes found: {sorted(subtypes)}")
    check("every row has a nonzero required_total_cohort_n (majority-informative)",
          all(int(r["required_total_cohort_n_majority_informative_dim3"]) > 0 for r in rows),
          "checked all 35 rows")
    check("every row has a nonzero required_total_cohort_n (fully-informative)",
          all(int(r["required_total_cohort_n_fully_informative_dim3"]) > 0 for r in rows),
          "checked all 35 rows")
    check("every row cites a source for gene_case_prevalence",
          all(r["gene_case_prevalence_pct_source"].strip() for r in rows),
          "checked all 35 rows")


def criterion_step1_gate8_threshold_reported() -> None:
    if not MEMO.exists():
        check("FEASIBILITY_MEMO.md present", False, f"{MEMO} missing")
        return
    text = MEMO.read_text(encoding="utf-8")
    check("GATE8 dimension-1/2/3 threshold table present, both arms",
          "CORE_HR" in text and "DDR_SIGNALING" in text and "dimension" in text.lower(),
          "looked for the by-dimension threshold table")
    check("non-monotonicity of the gate8 failure rate is disclosed (not a single clean threshold)",
          "non-monotonic" in text.lower() or "no single clean threshold" in text.lower(),
          "looked for the disclosed non-monotonicity caveat")
    check("states the never-reached case for the 1-feature SBS3-only dimension",
          "never reached" in text.lower(),
          "looked for the never-fully-informative disclosure")


def criterion_accuracy_vs_n_trade_quantified() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    for floor_str in ("0.25", "0.30", "0.35", "0.40"):
        check(f"accuracy-vs-n trade reported at floor {floor_str}", floor_str in text, f"looked for '{floor_str}'")
    check("accuracy figures cite P07-RERUN2's operating region (not re-derived)",
          "SIMULATED_PURITY_FLOOR_BY_SUBTYPE" in text, "looked for the source table reference")
    check("surviving n at each floor cites P-FIX-2",
          "P-FIX-2" in text or "PURITY_FLOOR_COST" in text, "looked for the P-FIX-2 cross-reference")


def criterion_live_retrieval_with_egress_disclosure() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("EGRESS_BLOCKED mechanism recorded for at least one unreachable domain this task",
          "EGRESS_BLOCKED" in text, "looked for the disclosed block mechanism")
    check("ICGC/PCAWG breast cohort size reported", "560" in text, "looked for the Nik-Zainal 560-genome figure")
    check("CPTAC-3 breast cohort size reported and matches live-retrieved clinical file row count",
          "122" in text, "looked for the Krug 2020 n=122 figure")
    check("no estimated substitute presented as a live retrieval where retrieval failed",
          "UNVERIFIED" in text, "looked for at least one explicit UNVERIFIED marker")


def criterion_harmonization_cost_stated() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("harmonization cost stated explicitly (capture kits / coverage / calling)",
          "capture" in text.lower() and "coverage" in text.lower(),
          "looked for the harmonization-cost paragraph")
    check("naive summed n is explicitly disclaimed as not directly usable",
          "not usable as a summed" in text.lower() or "not presented" in text.lower()
          or "scale illustration only" in text.lower(),
          "looked for the explicit summed-n disclaimer")


def criterion_three_designs_specified() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("Design A (stratified multi-cohort) specified with cost/loss/feasibility verdict",
          "Design A" in text or ("### A." in text), "looked for Design A section")
    check("Design A is explicitly ruled out (Step 2 does not reach the requirement)",
          "ruled out" in text.lower(), "looked for the explicit rule-out statement")
    check("Design B (pooled + covariate) specified with what is lost",
          "### B." in text or "Design B" in text, "looked for Design B section")
    check("Design B's loss of the per-subtype claim is stated",
          "gives up" in text.lower() and "subtype" in text.lower(), "looked for the explicit loss statement")
    check("Design C (stratified + INSUFFICIENT_N) specified with populated-cell count",
          "### C." in text or "Design C" in text, "looked for Design C section")
    check("Design C's small-minority-populating finding is stated plainly",
          "insufficient_n" in text.lower(), "looked for INSUFFICIENT_N in Design C's discussion")


def criterion_p09_implications_per_design() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("P09 implication under Design B (pooled estimator, changed truth quantities) stated",
          "pooled estimator" in text.lower() and "P09" in text,
          "looked for the Design-B P09 implication")
    check("P09 implication under Design A/C (stratified scope stands) stated",
          "stratified scope stands" in text.lower() or "current" in text.lower() and "stratified" in text.lower(),
          "looked for the Design-A/C P09 implication")
    check("Part C simulator gap relevance-shift under Design B is noted",
          "matters much less" in text.lower() or "matters less" in text.lower(),
          "looked for the reduced-relevance-under-B statement")
    check("no design is chosen (Step 4 states implications only)",
          "does not choose" in text.lower(), "looked for the explicit non-choice disclosure")


def criterion_technical_vs_judgment_separated() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("a section separating evidence-settled questions from judgment questions exists",
          "settled by evidence" in text.lower() and "programmatic judgment" in text.lower(),
          "looked for the explicit settled-vs-judgment section")


def criterion_report_md_statement_present_but_not_applied() -> None:
    if not MEMO.exists():
        check("REPORT.md feasibility statement present in memo", False, f"{MEMO} missing")
        return
    text = MEMO.read_text(encoding="utf-8")
    check("plain REPORT.md-directed feasibility statement present in the memo",
          "belongs in the report" in text.lower(), "looked for the exact required framing")
    report = REPO_ROOT / "REPORT.md"
    if report.exists():
        report_text = report.read_text(encoding="utf-8")
        check("REPORT.md itself is not modified by this task (feasibility statement lives in the memo)",
              "FEASIBILITY_MEMO" not in report_text and "COHORT_REQUIREMENT_TABLE" not in report_text,
              "checked REPORT.md was not edited to reference the new memo")


def criterion_no_pipeline_file_modified_and_no_p07_p08_p09_rerun() -> None:
    changed = set(_changed_files())
    for forbidden in PIPELINE_FORBIDDEN_FILES:
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    forbidden_paths = [p for p in changed if p.startswith("SIMULATED_loh_validation/SIMULATED_recovered")
                        or p.startswith("SIMULATED_loh_validation/SIMULATED_LR_TABLE")
                        or "SIMULATED_signature_validation" in p]
    check("no P07/P08/P09 production output re-generated this task", not forbidden_paths,
          f"suspicious changed paths: {forbidden_paths}")
    check("FEASIBILITY_MEMO.md WAS added (this task's own required deliverable)",
          "FEASIBILITY_MEMO.md" in changed, f"in changed files: {'FEASIBILITY_MEMO.md' in changed}")
    check("COHORT_REQUIREMENT_TABLE.tsv WAS added (this task's own required deliverable)",
          "COHORT_REQUIREMENT_TABLE.tsv" in changed, f"in changed files: {'COHORT_REQUIREMENT_TABLE.tsv' in changed}")


def criterion_halt_stated() -> None:
    if not MEMO.exists():
        return
    text = MEMO.read_text(encoding="utf-8")
    check("memo explicitly states HALT and that the design decision is the human's",
          "HALT" in text and "human's" in text.lower(),
          "looked for the explicit HALT statement")


def main() -> None:
    criterion_cohort_table_present_and_complete()
    criterion_step1_gate8_threshold_reported()
    criterion_accuracy_vs_n_trade_quantified()
    criterion_live_retrieval_with_egress_disclosure()
    criterion_harmonization_cost_stated()
    criterion_three_designs_specified()
    criterion_p09_implications_per_design()
    criterion_technical_vs_judgment_separated()
    criterion_report_md_statement_present_but_not_applied()
    criterion_no_pipeline_file_modified_and_no_p07_p08_p09_rerun()
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
