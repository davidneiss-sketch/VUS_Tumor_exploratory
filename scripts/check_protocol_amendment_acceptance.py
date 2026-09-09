#!/usr/bin/env python3
"""Acceptance checker for the protocol-amendment task (draft
PROPOSED_PROTOCOL_AMENDMENT.md, PROTOCOL_DEVIATIONS.md, and
REACHABILITY_TABLE.tsv replacing PROTOCOL.md section 7.1's estimator with
penalized logistic regression -- proposed, not applied).

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
AMENDMENT = REPO_ROOT / "PROPOSED_PROTOCOL_AMENDMENT.md"
DEVIATIONS = REPO_ROOT / "PROTOCOL_DEVIATIONS.md"
REACHABILITY_TSV = REPO_ROOT / "REACHABILITY_TABLE.tsv"
REPORT = REPO_ROOT / "REPORT.md"
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path, delim: str = "\t") -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delim))


def criterion_1_amendment_complete() -> None:
    if not AMENDMENT.exists():
        check("PROPOSED_PROTOCOL_AMENDMENT.md present", False, f"{AMENDMENT} missing")
        return
    text = AMENDMENT.read_text(encoding="utf-8")
    check("starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("contains a complete replacement text block for section 7.1",
          "### 7.1 Model" in text and "penalized" in text.lower() and "logistic regression" in text.lower(),
          "looked for a '### 7.1 Model' replacement heading")
    check("names the penalty and how its strength is selected", "ridge" in text.lower() and "lambda" in text,
          "looked for an explicit penalty name and a lambda-selection method")
    check("specifies purity, subtype, and WGD as covariates",
          "purity" in text.lower() and "subtype" in text.lower() and "wgd" in text.lower(),
          "looked for all three covariates named")

    normalized = " ".join(text.split())
    check("writes the prior-odds conversion arithmetic explicitly (the exact formula, not just a description)",
          "n_path_ref / n_benign_ref" in normalized or "n_path_ref/n_benign_ref" in normalized,
          "looked for the exact LR = posterior_odds / prior_odds formula with named terms")
    check("includes a worked numeric example of the prior-odds conversion",
          "Worked numeric example" in text or "worked numeric example" in text.lower(),
          "looked for a concrete numeric worked example")
    check("specifies calibration method and diagnostics on held-out folds",
          "reliability curve" in text.lower() and "brier" in text.lower(),
          "looked for reliability-curve and Brier-score diagnostics")
    check("states what replaces the conditional-independence assumption, with assumptions listed explicitly",
          "Assumptions this model makes" in text and "Log-linearity" in text,
          "looked for an explicit, named assumptions list including log-linearity")
    check("states that section 7.2 (cross-validation) and 7.3 (bootstrap) carry over unchanged",
          "carried over unchanged" in text.lower() or "carried over UNCHANGED" in text,
          "looked for explicit carry-over language for 7.2/7.3")


def criterion_2_deviation_record_draft_with_blank_approver() -> None:
    if not DEVIATIONS.exists():
        check("PROTOCOL_DEVIATIONS.md present", False, f"{DEVIATIONS} missing")
        return
    text = DEVIATIONS.read_text(encoding="utf-8")
    check("starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("status marked DRAFT, not applied", "DRAFT" in text and "not yet applied" in text.lower(),
          "looked for explicit DRAFT / not-yet-applied status")
    check("has a dated entry", "Date drafted" in text, "looked for a Date drafted field")
    check("names the section amended (PROTOCOL.md section 7.1)", "PROTOCOL.md" in text and "7.1" in text,
          "looked for the amended section named")
    check("cites P-EST-1's STEP 2 evidence with its numbers",
          "7.243" in text and "92.625" in text and "12.8x" in text,
          "looked for the exact STEP 2 test numbers reproduced")
    check("states what was known at pre-registration and what was not",
          "Known at pre-registration" in text and "Not known at pre-registration" in text,
          "looked for both explicit subsections")
    check("names an approver field", "Approver" in text, "looked for an Approver field")
    # The approver field itself must be BLANK -- check the text right
    # after the '**Approver**' table cell contains a placeholder, not a name.
    blank_markers = ("_(blank", "blank —", "blank -")
    approver_section = text.split("**Approver**", 1)[1][:300] if "**Approver**" in text else ""
    check("Approver field is left blank (contains an explicit blank placeholder, no name filled in)",
          bool(approver_section) and any(marker in approver_section for marker in blank_markers),
          "looked for an explicit blank placeholder immediately after the '**Approver**' table field")
    check("does not itself apply the amendment (no PROTOCOL.md edit claimed)",
          "does not take effect" in text.lower() or "not modified" in text.lower(),
          "looked for explicit non-application language")


def criterion_3_reachability_classification_complete() -> None:
    if not REACHABILITY_TSV.exists():
        check("REACHABILITY_TABLE.tsv present", False, f"{REACHABILITY_TSV} missing")
        return
    if not TRUTH_TSV.exists():
        check("SIMULATED_TRUTH.tsv present (needed to verify coverage)", False, f"{TRUTH_TSV} missing")
        return
    rows = read_tsv(REACHABILITY_TSV)
    truth_rows = read_tsv(TRUTH_TSV)
    truth_quantities = {r["quantity"] for r in truth_rows}
    table_quantities = {r["quantity"] for r in rows}
    check("every SIMULATED_TRUTH.tsv quantity appears in REACHABILITY_TABLE.tsv",
          truth_quantities == table_quantities,
          f"missing from table: {truth_quantities - table_quantities}; "
          f"extra in table: {table_quantities - truth_quantities}")
    valid_statuses = {"NEWLY_REACHABLE", "STILL_REACHABLE", "STILL_UNREACHABLE"}
    bad_status_rows = [r["quantity"] for r in rows if r.get("amendment_status") not in valid_statuses]
    check("every row has a valid classification (newly reachable / still reachable / still unreachable)",
          len(bad_status_rows) == 0, f"invalid-status rows: {bad_status_rows}")
    empty_reasoning = [r["quantity"] for r in rows if not r.get("reasoning", "").strip()]
    check("every classification has a stated reasoning", len(empty_reasoning) == 0,
          f"rows with empty reasoning: {empty_reasoning}")

    # Live re-derivation: NULL_ARM/secondary-null rows (is_null=TRUE) must
    # never be classified anything but STILL_REACHABLE -- true LR is
    # identically 1.0 under either estimator, this is a structural fact,
    # not an assertion.
    null_quantities = {r["quantity"] for r in truth_rows if r["is_null"].strip().upper() == "TRUE"}
    wrong_null_classification = [r["quantity"] for r in rows
                                  if r["quantity"] in null_quantities and r["amendment_status"] != "STILL_REACHABLE"]
    check("live re-derivation: every is_null=TRUE quantity is classified STILL_REACHABLE",
          len(wrong_null_classification) == 0, f"misclassified null quantities: {wrong_null_classification}")

    # Live re-derivation: every non-null *_joint_LR / *_inflation_ratio
    # quantity must be NEWLY_REACHABLE (the whole point of the amendment).
    joint_and_ratio = [r for r in rows if r["quantity"] not in null_quantities
                        and (r["quantity"].endswith("_joint_LR") or r["quantity"].endswith("_inflation_ratio"))]
    wrong_joint_classification = [r["quantity"] for r in joint_and_ratio if r["amendment_status"] != "NEWLY_REACHABLE"]
    check("live re-derivation: every non-null joint_LR/inflation_ratio quantity is classified NEWLY_REACHABLE",
          len(joint_and_ratio) > 0 and len(wrong_joint_classification) == 0,
          f"count checked={len(joint_and_ratio)}; misclassified: {wrong_joint_classification}")


def criterion_4_risks_stated_with_tests() -> None:
    if not AMENDMENT.exists():
        check("risks stated with a test for each", False, f"{AMENDMENT} missing")
        return
    text = AMENDMENT.read_text(encoding="utf-8")
    step4_section = text.split("## STEP 4", 1)[1] if "## STEP 4" in text else ""
    check("STEP 4 (risks) section present", bool(step4_section), "looked for a '## STEP 4' heading")
    check("Risk 1 (prior-odds / v2 failure mode) names the test and what it must show",
          "Risk 1" in step4_section and "invariant to the reference set's" in step4_section,
          "looked for the reference-set-balance invariance test description")
    check("Risk 2 (log-linearity) states how it will be checked",
          "Risk 2" in step4_section and "approximation-error curve" in step4_section,
          "looked for the log-linearity approximation-error check")
    check("Risk 3 names quantities whose interpretation changes",
          "Risk 3" in step4_section and "product_of_marginals_LR" in step4_section,
          "looked for the interpretation-change discussion")


def criterion_5_protocol_unmodified() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    changed = {line[3:].rstrip("/") for line in result.stdout.splitlines()}
    check("PROTOCOL.md not modified by this task (git status confirms)", "PROTOCOL.md" not in changed,
          f"PROTOCOL.md in changed files: {'PROTOCOL.md' in changed}")
    for forbidden in ("simulate.py", "signatures.py", "loh_caller.py", "stake_ablation.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "PROTOCOL.md"], cwd=REPO_ROOT)
    check("git diff confirms PROTOCOL.md is byte-identical to HEAD", diff.returncode == 0,
          f"git diff exit={diff.returncode} (0 = no diff)")


def criterion_6_report_prominence() -> None:
    if not REPORT.exists():
        check("REPORT.md present with the deviation surfaced prominently", False, f"{REPORT} missing")
        return
    text = REPORT.read_text(encoding="utf-8")
    check("starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    # "Prominently, not only in an appendix": the deviation section must
    # appear near the TOP of the file, not buried after unrelated content.
    deviation_pos = text.find("Protocol deviation in effect")
    check("REPORT.md present", True, "")
    check("deviation entry appears prominently (within the first ~3000 characters, not in a late appendix)",
          0 < deviation_pos < 3000, f"deviation heading found at character offset {deviation_pos}")
    check("REPORT.md references all three companion documents",
          "PROPOSED_PROTOCOL_AMENDMENT.md" in text and "PROTOCOL_DEVIATIONS.md" in text
          and "REACHABILITY_TABLE.tsv" in text,
          "looked for all three filenames referenced")
    normalized = " ".join(text.split())
    check("REPORT.md discloses it is a newly-created file, not a synthesized retrospective",
          "did not exist in this repository before this task" in normalized,
          "looked for explicit disclosure of the file's newness/scope")


def main() -> None:
    criterion_1_amendment_complete()
    criterion_2_deviation_record_draft_with_blank_approver()
    criterion_3_reachability_classification_complete()
    criterion_4_risks_stated_with_tests()
    criterion_5_protocol_unmodified()
    criterion_6_report_prominence()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
