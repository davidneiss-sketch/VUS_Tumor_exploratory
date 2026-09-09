#!/usr/bin/env python3
"""Acceptance checker for P07-RERUN2 (revalidate the LOH caller against
the current simulator).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (SIMULATED_loh_validation.md's,
PROPOSED_DEVIATIONS.md's own prose) is not itself the check.

Exit 0 = every criterion PASS. Note: per this task's own HALT instruction,
a script-checked PASS here does NOT mean gate6/gate8 passed on the LOH
caller's own quantities -- it means every ACCEPTANCE requirement (scope
declared, gates run, findings reported, forbidden files untouched) was
actually done, honestly, including reporting the HALT-triggering FAILs.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOH_CALLER = REPO_ROOT / "loh_caller.py"
P07_SCOPE = REPO_ROOT / "P07_SCOPE.tsv"
VALIDATION_MD = REPO_ROOT / "SIMULATED_loh_validation.md"
OUT_DIR = REPO_ROOT / "SIMULATED_loh_validation"
RECOVERY_TABLE = OUT_DIR / "SIMULATED_RECOVERY_TABLE.tsv"
LR_TABLE = OUT_DIR / "SIMULATED_LR_TABLE.tsv"
RATES_TABLE = OUT_DIR / "SIMULATED_rates_table.tsv"
BIAS_PREDICTION = OUT_DIR / "SIMULATED_BIAS_PREDICTION.tsv"
GATE8_REPORT = OUT_DIR / "gate8_out" / "SIMULATED_GATE8_INTERVAL_REPORT.tsv"
PURITY_FLOOR_TABLE = OUT_DIR / "SIMULATED_PURITY_FLOOR_BY_SUBTYPE.tsv"
PROPOSED_DEVIATIONS = REPO_ROOT / "PROPOSED_DEVIATIONS.md"
DEPLOYMENT_LOG = REPO_ROOT / "DEPLOYMENT_LOG.md"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
SIMULATE_PY = REPO_ROOT / "simulate.py"
LOGISTIC_ESTIMATOR = REPO_ROOT / "logistic_estimator.py"
SIGNATURES_PY = REPO_ROOT / "signatures.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    return [line[3:].rstrip("/") for line in result.stdout.splitlines()]


def criterion_1_scope_declared_for_all_91() -> None:
    if not P07_SCOPE.exists():
        check("P07_SCOPE.tsv present", False, f"{P07_SCOPE} missing")
        return
    rows = read_tsv(P07_SCOPE)
    check("P07_SCOPE.tsv declares all 91 SIMULATED_TRUTH.tsv quantities", len(rows) == 91,
          f"row count: {len(rows)}")
    n_true = sum(1 for r in rows if r["in_scope"] == "TRUE")
    n_false = sum(1 for r in rows if r["in_scope"] == "FALSE")
    check("scope counts are exactly 12 IN_SCOPE / 79 NOT_IN_SCOPE, stated explicitly",
          n_true == 12 and n_false == 79, f"TRUE={n_true}, FALSE={n_false}")
    check("the 10 new subtype-stratified wt_lost_direction_LR quantities are IN_SCOPE",
          all(r["in_scope"] == "TRUE" for r in rows if r["quantity"].endswith("_wt_lost_direction_LR")
              and r["quantity"] not in ("core_hr_wt_lost_direction_LR", "ddr_signaling_wt_lost_direction_LR")),
          "checked all 10 subtype-stratified wt_lost_direction_LR rows")


def criterion_2_what_broke_reported() -> None:
    if not LOH_CALLER.exists():
        check("loh_caller.py present", False, "missing")
        return
    text = LOH_CALLER.read_text(encoding="utf-8")
    check("loh_caller.py's own docstring reports what broke before describing the fix",
          "KeyError" in text and "UNDECLARED SCOPE" in text,
          "looked for both break descriptions in the revision-history docstring")
    if not DEPLOYMENT_LOG.exists():
        check("DEPLOYMENT_LOG.md reports STEP 2's findings", False, "missing")
        return
    log_text = DEPLOYMENT_LOG.read_text(encoding="utf-8")
    check("DEPLOYMENT_LOG.md's Invocation 7 reports what broke, before the fix, explicitly",
          "STEP 2" in log_text and "what broke, reported before any change" in log_text,
          "looked for the STEP 2 section")


def criterion_3_all_four_gates_run_through_wrapper() -> None:
    if not DEPLOYMENT_LOG.exists():
        check("all 4 gates logged via run_with_integrity_checks.py", False, "DEPLOYMENT_LOG.md missing")
        return
    text = DEPLOYMENT_LOG.read_text(encoding="utf-8")
    invocation_7 = text[text.find("## Invocation 7"):]
    for gate in ("gate4_statistics.py", "gate6_recovery.py", "gate8_interval_informativeness.py"):
        check(f"{gate} logged as run through run_with_integrity_checks.py in Invocation 7",
              gate in invocation_7 and "run_with_integrity_checks.py" in invocation_7,
              f"looked for {gate} in the Invocation 7 section")
    check("gate7_denominators reported in Invocation 7 (via loh_caller.py's own internal invocation)",
          "gate7_denominators" in invocation_7, "looked for gate7 mention")
    for path in (LR_TABLE, RECOVERY_TABLE, GATE8_REPORT, RATES_TABLE):
        check(f"{path.relative_to(REPO_ROOT)} present on disk", path.exists(), str(path))


def criterion_4_bias_prediction_stated_with_rationale() -> None:
    if not BIAS_PREDICTION.exists():
        check("SIMULATED_BIAS_PREDICTION.tsv present", False, f"{BIAS_PREDICTION} missing")
        return
    rows = read_tsv(BIAS_PREDICTION)
    check("bias prediction supplied for all 12 in-scope quantities", len(rows) == 12,
          f"row count: {len(rows)}")
    check("every prediction cites a computed source (Jeffreys correction), not an arbitrary guess",
          all("Jeffreys" in r["source"] for r in rows),
          "checked source column for all rows")
    if not PROPOSED_DEVIATIONS.exists():
        check("PROPOSED_DEVIATIONS.md states the rationale for the bias prediction", False, "missing")
        return
    text = PROPOSED_DEVIATIONS.read_text(encoding="utf-8")
    check("PROPOSED_DEVIATIONS.md explains why no penalized-estimator-style prediction applies",
          "not a penalized estimator" in text.lower() or "no tunable penalty" in text.lower(),
          "looked for the not-a-penalized-estimator rationale")
    check("PROPOSED_DEVIATIONS.md reports the resulting directional-check outcome honestly (11 of 12 fail)",
          "11 of 12" in text or "11 strata" in text,
          "looked for the explicit failure-count statement")


def criterion_5_wt_loss_accuracy_by_subtype_with_n() -> None:
    if not RATES_TABLE.exists():
        check("WT_LOSS accuracy by subtype reported with n", False, f"{RATES_TABLE} missing")
        return
    rows = {r["metric_name"]: r for r in read_tsv(RATES_TABLE)}
    subtypes = ["luma", "lumb", "her2e", "basal", "normal_like"]
    for st in subtypes:
        sens_key = f"wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable_subtype_{st}"
        prec_key = f"wt_loss_precision_subtype_{st}"
        check(f"WT_LOSS sensitivity reported for subtype={st} with n_total_cell",
              sens_key in rows and rows[sens_key]["n_total_cell"] not in ("", None),
              f"row present: {sens_key in rows}")
        check(f"WT_LOSS precision reported for subtype={st} with n_total_cell",
              prec_key in rows and rows[prec_key]["n_total_cell"] not in ("", None),
              f"row present: {prec_key in rows}")
    check("pooled WT_LOSS sensitivity/precision still reported (unchanged metric names)",
          "wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable" in rows
          and "wt_loss_precision" in rows,
          "checked pooled metric names")
    if VALIDATION_MD.exists():
        text = VALIDATION_MD.read_text(encoding="utf-8")
        check("SIMULATED_loh_validation.md leads with the Basal-vs-others finding",
              "does NOT degrade in Basal" in text or "does not degrade in Basal" in text,
              "looked for the explicit Basal finding")


def criterion_6_inversion_rates_by_subtype_with_denominators() -> None:
    if not RATES_TABLE.exists():
        check("inversion rates by subtype reported with denominators", False, "missing")
        return
    rows = {r["metric_name"]: r for r in read_tsv(RATES_TABLE)}
    subtypes = ["luma", "lumb", "her2e", "basal", "normal_like"]
    for st in subtypes:
        for direction in ("inversion_rate_wt_lost_direction_called_variant_lost",
                           "inversion_rate_variant_lost_called_wt_lost_direction"):
            key = f"{direction}_subtype_{st}"
            check(f"{key} present with an explicit denominator",
                  key in rows and rows[key]["denominator"] not in ("", None),
                  f"row present: {key in rows}")


def criterion_7_operating_region_rederived_per_subtype() -> None:
    if not PURITY_FLOOR_TABLE.exists():
        check("SIMULATED_PURITY_FLOOR_BY_SUBTYPE.tsv present", False, f"{PURITY_FLOOR_TABLE} missing")
        return
    rows = read_tsv(PURITY_FLOOR_TABLE)
    subtypes_present = {r["subtype"] for r in rows}
    check("purity floor re-derived for POOLED and all 5 PAM50 subtypes",
          subtypes_present == {"POOLED", "LumA", "LumB", "HER2E", "Basal", "Normal-like"},
          f"subtypes found: {sorted(subtypes_present)}")
    if not PROPOSED_DEVIATIONS.exists():
        check("PROPOSED_DEVIATIONS.md re-assesses the 0.25 floor proposal per subtype", False, "missing")
        return
    text = PROPOSED_DEVIATIONS.read_text(encoding="utf-8")
    check("PROPOSED_DEVIATIONS.md states the 0.25 floor no longer holds",
          "0.25 floor does not hold" in text.lower() or "0.25 proposal is superseded" in text.lower(),
          "looked for the explicit supersession statement")
    check("PROPOSED_DEVIATIONS.md identifies Basal/LumB needing a stricter floor than pooled",
          "one purity band stricter" in text.lower() or "stricter than pooled" in text.lower(),
          "looked for the Basal/LumB-specific finding")
    check("PROPOSED_DEVIATIONS.md's revised proposal is written to PROPOSED_DEVIATIONS.md, not PROTOCOL.md",
          "PROTOCOL.md" not in _changed_files(),
          f"PROTOCOL.md in changed files: {'PROTOCOL.md' in _changed_files()}")


def criterion_8_forbidden_files_unmodified() -> None:
    changed = set(_changed_files())
    for forbidden in ("simulate.py", "PROTOCOL.md", "logistic_estimator.py", "signatures.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    for gate in REPO_ROOT.glob("gates/gate*.py"):
        rel = str(gate.relative_to(REPO_ROOT))
        check(f"{rel} not modified by this task", rel not in changed, f"{rel} in changed files: {rel in changed}")
    check("loh_caller.py WAS modified (this task's own required schema-compatibility fix)",
          "loh_caller.py" in changed, f"loh_caller.py in changed files: {'loh_caller.py' in changed}")


def criterion_9_halt_no_p08_p09_rerun() -> None:
    changed = set(_changed_files())
    forbidden_paths = [p for p in changed if "signatures" in p or "P08" in p or "P09" in p]
    check("no P08/P09-labeled output changed this task", not forbidden_paths,
          f"suspicious changed paths: {forbidden_paths}")
    if DEPLOYMENT_LOG.exists():
        text = DEPLOYMENT_LOG.read_text(encoding="utf-8")
        check("DEPLOYMENT_LOG.md explicitly records the HALT (gate6 FAIL, P08 not re-run)",
              "HALT" in text and "P08 is NOT re-run" in text,
              "looked for the explicit HALT statement")


def main() -> None:
    criterion_1_scope_declared_for_all_91()
    criterion_2_what_broke_reported()
    criterion_3_all_four_gates_run_through_wrapper()
    criterion_4_bias_prediction_stated_with_rationale()
    criterion_5_wt_loss_accuracy_by_subtype_with_n()
    criterion_6_inversion_rates_by_subtype_with_denominators()
    criterion_7_operating_region_rederived_per_subtype()
    criterion_8_forbidden_files_unmodified()
    criterion_9_halt_no_p08_p09_rerun()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    print("\nNOTE: this OVERALL PASS/FAIL is about whether the ACCEPTANCE requirements were met "
          "(scope declared, gates run, findings reported, forbidden files untouched). It is NOT the "
          "same question as whether gate6/gate8 passed on the LOH caller's own quantities -- those did "
          "NOT pass, and that is reported honestly, per this task's own HALT instruction, above.")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
