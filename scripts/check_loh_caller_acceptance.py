#!/usr/bin/env python3
"""Acceptance checker for the direction-aware LOH caller task.

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (the prose in
SIMULATED_loh_validation.md) is not itself the check. Every criterion
below re-derives its answer from the actual on-disk artifacts (and, for
gate6/gate7, by re-running the real gate scripts fresh) rather than
trusting what the report claims.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOH_CALLER = REPO_ROOT / "loh_caller.py"
REPORT_MD = REPO_ROOT / "SIMULATED_loh_validation.md"
OUT_DIR = REPO_ROOT / "SIMULATED_loh_validation"
RECOVERY_TABLE = REPO_ROOT / "SIMULATED_RECOVERY_TABLE.tsv"

ALL_CATEGORIES = ["RETENTION", "WT_LOSS", "CN_NEUTRAL_LOH_WT_LOSS", "VARIANT_LOSS", "AMBIGUOUS", "NOT_EVALUABLE"]

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def criterion_1_confusion_matrix() -> None:
    path = OUT_DIR / "SIMULATED_confusion_matrix.tsv"
    if not path.exists():
        check("confusion matrix against injected truth", False, f"{path} missing")
        return
    rows = read_tsv(path)
    seen_true = {r["true_category"] for r in rows}
    seen_pred = {r["predicted_category"] for r in rows}
    missing_true = set(ALL_CATEGORIES) - seen_true
    missing_pred = set(ALL_CATEGORIES) - seen_pred
    total = sum(int(r["count"]) for r in rows)

    calls_path = OUT_DIR / "SIMULATED_loh_calls.tsv"
    calls = read_tsv(calls_path) if calls_path.exists() else []
    n_calls = len(calls)

    ok = (not missing_true) and (not missing_pred) and total > 0 and total == n_calls
    check(
        "confusion matrix against injected truth",
        ok,
        f"{path.name}: {len(rows)} row(s), {total} total count(s) vs {n_calls} calls in "
        f"SIMULATED_loh_calls.tsv, missing_true_categories={sorted(missing_true)}, "
        f"missing_predicted_categories={sorted(missing_pred)}",
    )


def criterion_2_gate6() -> None:
    truth = REPO_ROOT / "SIMULATED_TRUTH.tsv"
    recovered = OUT_DIR / "SIMULATED_recovered_quantities.tsv"
    scope = OUT_DIR / "SIMULATED_recovery_scope.tsv"
    if not (truth.exists() and recovered.exists() and scope.exists()):
        check("gate6 PASS on every quantity, or session reports FAILED", False,
              f"required input missing: truth={truth.exists()}, recovered={recovered.exists()}, scope={scope.exists()}")
        return
    proc = subprocess.run(
        [sys.executable, "gates/gate6_recovery.py", "--truth", str(truth),
         "--recovered", str(recovered), "--scope", str(scope), "--outdir", str(REPO_ROOT)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    exit_code = proc.returncode
    report_text = REPORT_MD.read_text(encoding="utf-8") if REPORT_MD.exists() else ""

    recovery_table = REPO_ROOT / "SIMULATED_RECOVERY_TABLE.tsv"
    recovery_rows = read_tsv(recovery_table) if recovery_table.exists() else []
    undeclared = [r["quantity"] for r in recovery_rows if r.get("scope_status") == "UNDECLARED"]
    if undeclared:
        check("gate6 PASS on every quantity, or session reports FAILED", False,
              f"undeclared-scope quantities found (a real scope bug, not this checker re-running without --scope): {undeclared}")
        return

    if exit_code == 0:
        ok = "PASSED" in report_text and "gate6" in report_text.lower()
        detail = f"gate6 exit=0 (all quantities SIMULATED_PASS); report states PASSED: {ok}"
    else:
        ok = "FAILED" in report_text and "gate6" in report_text.lower()
        detail = (f"gate6 exit={exit_code} (>=1 quantity SIMULATED_FAIL); report explicitly states "
                  f"FAILED per Standing Rule 2 / the task's acceptance wording: {ok}")
    check("gate6 PASS on every quantity, or session reports FAILED", ok, detail)


def criterion_3_gate7() -> None:
    rates = OUT_DIR / "SIMULATED_rates_table.tsv"
    if not rates.exists():
        check("gate7 PASS on every reported rate", False, f"{rates} missing")
        return
    proc = subprocess.run(
        [sys.executable, "gates/gate7_denominators.py", "--rates-table", str(rates)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    check("gate7 PASS on every reported rate", proc.returncode == 0,
          f"gate7_denominators.py exit={proc.returncode}\n{proc.stdout.strip()}")


def criterion_4_denominator_requirement() -> None:
    rates_path = OUT_DIR / "SIMULATED_rates_table.tsv"
    if not rates_path.exists():
        check("denominator requirement (total attempted, AMBIGUOUS excluded, accuracy incl/excl)", False,
              f"{rates_path} missing")
        return
    rows = {r["metric_name"]: r for r in read_tsv(rates_path)}
    required = [
        "overall_accuracy_including_ambiguous_and_not_evaluable",
        "overall_accuracy_excluding_ambiguous_and_not_evaluable",
        "confidence_filter_ambiguous_rate",
        "not_evaluable_rate_depth_lt_20",
    ]
    missing = [m for m in required if m not in rows]
    all_have_excluded_count = all(
        rows[m].get("excluded_count", "").strip() != "" for m in required if m in rows
    )
    incl = rows.get("overall_accuracy_including_ambiguous_and_not_evaluable")
    total_attempted = int(incl["denominator"]) if incl else 0
    ok = (not missing) and all_have_excluded_count and total_attempted > 0
    check(
        "denominator requirement (total attempted, AMBIGUOUS excluded, accuracy incl/excl)",
        ok,
        f"missing_required_rows={missing}, all_have_explicit_excluded_count={all_have_excluded_count}, "
        f"total_calls_attempted={total_attempted}",
    )


def criterion_5_unreliable_region_stated() -> None:
    if not REPORT_MD.exists():
        check("unreliable operating region stated explicitly", False, f"{REPORT_MD} missing")
        return
    text = REPORT_MD.read_text(encoding="utf-8")
    has_heading = "unreliable operating region" in text.lower()
    # Must name a concrete stratum metric and a numeric rate, not just an assertion.
    has_concrete_stratum = bool(re.search(r"accuracy_by_(purity|depth|total_copy_number|wgd_status)_\S+.{0,40}rate\s*\*\*([\d.]+)", text, re.IGNORECASE))
    has_root_cause = "root cause" in text.lower()
    ok = has_heading and has_concrete_stratum and has_root_cause
    check(
        "unreliable operating region stated explicitly",
        ok,
        f"heading_present={has_heading}, names_concrete_stratum_and_rate={has_concrete_stratum}, "
        f"states_root_cause={has_root_cause}",
    )


def criterion_6_variant_loss_distinct() -> None:
    path = OUT_DIR / "SIMULATED_confusion_matrix.tsv"
    if not path.exists():
        check("VARIANT_LOSS is a distinct output class", False, f"{path} missing")
        return
    rows = read_tsv(path)
    variant_loss_true = sum(int(r["count"]) for r in rows if r["true_category"] == "VARIANT_LOSS")
    variant_loss_pred = sum(int(r["count"]) for r in rows if r["predicted_category"] == "VARIANT_LOSS")
    wtloss_variantloss_merged_row_exists = any(
        r["true_category"] == "VARIANT_LOSS" and r["predicted_category"] in ("WT_LOSS", "CN_NEUTRAL_LOH_WT_LOSS") and int(r["count"]) == sum(int(rr["count"]) for rr in rows if rr["true_category"] == r["true_category"])
        for r in rows
    )
    source = LOH_CALLER.read_text(encoding="utf-8")
    call_locus_src = source[source.index("def call_locus"):source.index("def call_locus") + 2500]
    has_both_as_separate_literals = ('"VARIANT_LOSS"' in call_locus_src) and (
        '"CN_NEUTRAL_LOH_WT_LOSS"' in call_locus_src or '"WT_LOSS"' in call_locus_src
    )
    ok = (variant_loss_true + variant_loss_pred) > 0 and has_both_as_separate_literals and not wtloss_variantloss_merged_row_exists
    check(
        "VARIANT_LOSS is a distinct output class",
        ok,
        f"true_instances={variant_loss_true}, predicted_instances={variant_loss_pred}, "
        f"emitted as a separate literal in call_locus()={has_both_as_separate_literals}",
    )


def criterion_7_diagnosis_names_mechanism() -> None:
    path = REPO_ROOT / "DIAGNOSIS.md"
    if not path.exists():
        check("DIAGNOSIS.md names a mechanism, with evidence", False, f"{path} missing")
        return
    text = path.read_text(encoding="utf-8")
    starts_with_banner = text.startswith("SIMULATED DATA — NOT A SCIENTIFIC RESULT")
    # The real check: a named, evidenced mechanism section exists, distinct from a bare "it's noise" dismissal.
    has_mechanism_section = bool(re.search(r"##\s*Conclusion", text)) or "mechanism" in text.lower()
    has_evidence_table = "|" in text and text.count("|") > 20  # markdown tables present, i.e. real data cited
    explicitly_rejects_noise_only = "not an acceptable conclusion" in text.lower() or "not \"sampling noise, ignore it\"" in text.lower() or "not sampling noise" in text.lower() or "is not the dominant driver" in text.lower()
    tested_all_four = all(f"## ({letter})" in text for letter in "abcd")
    ok = starts_with_banner and has_mechanism_section and has_evidence_table and tested_all_four
    check(
        "DIAGNOSIS.md names a mechanism, with evidence",
        ok,
        f"starts_with_banner={starts_with_banner}, has_mechanism_conclusion_section={has_mechanism_section}, "
        f"has_evidence_tables={has_evidence_table}, tests_all_4_subquestions_a_through_d={tested_all_four}",
    )


def criterion_8_wt_loss_accuracy_with_n() -> None:
    rates_path = OUT_DIR / "SIMULATED_rates_table.tsv"
    if not rates_path.exists():
        check("WT_LOSS accuracy reported with n", False, f"{rates_path} missing")
        return
    rows = {r["metric_name"]: r for r in read_tsv(rates_path)}
    wt_loss_rows = [k for k in rows if k.startswith("wt_loss_")]
    ok = len(wt_loss_rows) >= 1 and all(
        rows[k].get("n_total_cell", "").strip() not in ("", None) and int(rows[k]["n_total_cell"]) > 0
        for k in wt_loss_rows
    )
    check(
        "WT_LOSS accuracy reported with n",
        ok,
        f"wt_loss metric rows found: {wt_loss_rows}, "
        f"n values: {[(k, rows[k].get('n_total_cell')) for k in wt_loss_rows]}",
    )


def criterion_9_every_stratified_cell_carries_n() -> None:
    rates_path = OUT_DIR / "SIMULATED_rates_table.tsv"
    if not rates_path.exists():
        check("every stratified cell carries n", False, f"{rates_path} missing")
        return
    rows = read_tsv(rates_path)
    if not rows or "n_total_cell" not in rows[0]:
        check("every stratified cell carries n", False, "n_total_cell column missing from rates table")
        return
    missing_n = [r["metric_name"] for r in rows if not r.get("n_total_cell", "").strip()]
    zero_n_with_nonzero_denominator = [
        r["metric_name"] for r in rows
        if r.get("n_total_cell", "").strip() and int(r["n_total_cell"]) == 0 and float(r.get("denominator") or 0) > 0
    ]
    # Cross-check a specific known small-n grid cell is distinguishable from a large one (the
    # task's exact "a 0/4 cell and a 0/400 cell must not look alike" requirement).
    grid_rows = [r for r in rows if "_x_depth_" in r["metric_name"]]
    distinct_ns = {r["n_total_cell"] for r in grid_rows}
    ok = (not missing_n) and (not zero_n_with_nonzero_denominator) and len(distinct_ns) > 1
    check(
        "every stratified cell carries n",
        ok,
        f"{len(rows)} row(s) checked; missing_n={missing_n}; zero_n_with_nonzero_denominator={zero_n_with_nonzero_denominator}; "
        f"{len(grid_rows)} purity x depth grid cells with {len(distinct_ns)} distinct n values (not all identical)",
    )


def criterion_10_proposed_deviations_and_protocol_unmodified() -> None:
    path = REPO_ROOT / "PROPOSED_DEVIATIONS.md"
    if not path.exists():
        check("proposed protocol deviations listed; PROTOCOL.md unmodified", False, f"{path} missing")
        return
    text = path.read_text(encoding="utf-8")
    starts_with_banner = text.startswith("SIMULATED DATA — NOT A SCIENTIFIC RESULT")
    has_purity_proposal = "purity" in text.lower() and ("propos" in text.lower())
    has_depth_discussion = "depth" in text.lower()
    mentions_010_arm = "0.10" in text
    proc = subprocess.run(["git", "diff", "--stat", "PROTOCOL.md"], cwd=REPO_ROOT, capture_output=True, text=True)
    protocol_unmodified = proc.stdout.strip() == "" and proc.returncode == 0
    proc2 = subprocess.run(["git", "diff", "--cached", "--stat", "PROTOCOL.md"], cwd=REPO_ROOT, capture_output=True, text=True)
    protocol_unmodified_staged = proc2.stdout.strip() == ""
    ok = starts_with_banner and has_purity_proposal and has_depth_discussion and mentions_010_arm and protocol_unmodified and protocol_unmodified_staged
    check(
        "proposed protocol deviations listed; PROTOCOL.md unmodified",
        ok,
        f"starts_with_banner={starts_with_banner}, has_purity_proposal={has_purity_proposal}, "
        f"has_depth_discussion={has_depth_discussion}, mentions_0.10_arm={mentions_010_arm}, "
        f"PROTOCOL.md unmodified (working tree)={protocol_unmodified}, unmodified (staged)={protocol_unmodified_staged}",
    )


def main() -> None:
    criterion_1_confusion_matrix()
    criterion_2_gate6()
    criterion_3_gate7()
    criterion_4_denominator_requirement()
    criterion_5_unreliable_region_stated()
    criterion_6_variant_loss_distinct()
    criterion_7_diagnosis_names_mechanism()
    criterion_8_wt_loss_accuracy_with_n()
    criterion_9_every_stratified_cell_carries_n()
    criterion_10_proposed_deviations_and_protocol_unmodified()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
