#!/usr/bin/env python3
"""Acceptance checker for P-EST-1 (does PROTOCOL.md's estimator model the
joint density, or is it a product of marginals?).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (ESTIMATOR_SPECIFICATION_AUDIT.md's,
ESTIMATOR_OPTIONS.md's prose) is not itself the check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT = REPO_ROOT / "ESTIMATOR_SPECIFICATION_AUDIT.md"
OPTIONS = REPO_ROOT / "ESTIMATOR_OPTIONS.md"
STEP2_TSV = REPO_ROOT / "SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST.tsv"
STEP2_SCRIPT = REPO_ROOT / "estimator_joint_vs_product_test.py"
STEP4_RECONCILIATION_TSV = REPO_ROOT / "SIMULATED_FAILURE_MODE_RECONCILIATION.tsv"
STEP4_BANDWIDTH_TSV = REPO_ROOT / "SIMULATED_KDE_BANDWIDTH_MECHANISM.tsv"
STEP4_SCRIPT = REPO_ROOT / "estimator_underflow_bandwidth_diagnosis.py"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
SIMULATE_PY = REPO_ROOT / "simulate.py"
SIGNATURES_PY = REPO_ROOT / "signatures.py"
LOH_CALLER_PY = REPO_ROOT / "loh_caller.py"
STAKE_ABLATION_PY = REPO_ROOT / "stake_ablation.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path, delim: str = "\t") -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delim))


def criterion_1_spec_vs_code_quoted() -> None:
    if not AUDIT.exists():
        check("ESTIMATOR_SPECIFICATION_AUDIT.md present", False, f"{AUDIT} missing")
        return
    text = AUDIT.read_text(encoding="utf-8")
    check("ESTIMATOR_SPECIFICATION_AUDIT.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("quotes PROTOCOL.md's model specification verbatim",
          "the product of per-feature LRs, under a" in text and "conditional-independence assumption" in text,
          "looked for PROTOCOL.md section 7.1's exact 'product of per-feature LRs' wording")
    # Confirm the quoted passage is ACTUALLY in PROTOCOL.md, not fabricated.
    protocol_text = PROTOCOL.read_text(encoding="utf-8") if PROTOCOL.exists() else ""
    check("the quoted PROTOCOL.md passage is verified against the live PROTOCOL.md file (not fabricated)",
          "the product of per-feature LRs, under a" in protocol_text,
          "searched PROTOCOL.md itself for the same exact wording")
    check("traces the code's arithmetic (quotes joint_lr_for_subset / feature_lr)",
          "joint_lr_for_subset" in text and "feature_lr" in text and "lr *= feature_lr" in text,
          "looked for the actual stake_ablation.py source quoted, not paraphrased")
    check("states an explicit agree/disagree verdict", "AGREE" in text.upper(),
          "looked for an explicit verdict")


def criterion_2_step2_test_present_and_run() -> None:
    if not STEP2_SCRIPT.exists():
        check("estimator_joint_vs_product_test.py present", False, f"{STEP2_SCRIPT} missing")
        return
    if not STEP2_TSV.exists():
        check("SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST.tsv present (test was run)", False,
              f"{STEP2_TSV} missing")
        return
    rows = read_tsv(STEP2_TSV)
    check("step 2 test covers both arms", {r["arm"] for r in rows} == {"CORE_HR", "DDR_SIGNALING"},
          f"arms found: {[r['arm'] for r in rows]}")
    required_cols = {"true_joint_lr_correlated", "true_joint_lr_independent",
                      "product_of_marginals_lr_both_datasets", "estimator_mean_correlated",
                      "estimator_mean_independent"}
    check("reports both true joint LRs, product-of-marginals value, and both estimator means",
          rows and required_cols.issubset(rows[0].keys()), f"columns: {list(rows[0].keys()) if rows else []}")

    # Live re-derivation: the true joint LR (correlated) really is far from
    # the true joint LR (independent) = product-of-marginals -- otherwise
    # this would not be a meaningful test construction at all.
    all_ok = True
    detail_parts = []
    for r in rows:
        true_joint = float(r["true_joint_lr_correlated"])
        product = float(r["product_of_marginals_lr_both_datasets"])
        ratio = true_joint / product
        gap_is_material = ratio < 0.5 or ratio > 2.0
        all_ok = all_ok and gap_is_material
        detail_parts.append(f"{r['arm']}: true_joint/product={ratio:.4f}")
    check("true joint LR (correlated) differs materially from product-of-marginals LR by construction",
          all_ok, "; ".join(detail_parts))

    # The dispositive comparison: is the estimator's mean on CORRELATED
    # samples statistically indistinguishable from its mean on INDEPENDENT
    # samples (product-of-marginals structure), or does it track the true
    # joint LR instead (true joint-density structure)?
    all_indistinguishable = True
    detail_parts = []
    for r in rows:
        mean_corr = float(r["estimator_mean_correlated"])
        mean_indep = float(r["estimator_mean_independent"])
        sd_corr = float(r["estimator_sd_correlated"])
        sd_indep = float(r["estimator_sd_independent"])
        pooled_sd = ((sd_corr ** 2 + sd_indep ** 2) / 2) ** 0.5
        z = abs(mean_corr - mean_indep) / pooled_sd if pooled_sd > 0 else float("inf")
        indistinguishable = z < 1.0  # well within noise
        all_indistinguishable = all_indistinguishable and indistinguishable
        detail_parts.append(f"{r['arm']}: |mean_corr-mean_indep|/pooled_sd={z:.3f}")
    check("estimator's mean is statistically indistinguishable between CORRELATED and INDEPENDENT "
          "datasets (dispositive: confirms product-of-marginals, not joint-density, behavior)",
          all_indistinguishable, "; ".join(detail_parts))


def criterion_3_p09_target_meaning_stated() -> None:
    if not AUDIT.exists():
        check("states what P09's recovery target means under the finding", False, f"{AUDIT} missing")
        return
    text = AUDIT.read_text(encoding="utf-8")
    step3_section = (text.split("## STEP 3", 1)[1].split("## STEP 4", 1)[0]
                      if "## STEP 3" in text and "## STEP 4" in text else "")
    check("STEP 3 section present and states gate6 cannot pass on the joint quantity",
          "cannot pass" in step3_section.lower() or "CANNOT pass" in step3_section,
          "looked for explicit 'cannot pass' language in the STEP 3 section")
    check("STEP 3 names which quantities remain validatable (product-of-marginals, marginals, NULL_ARM)",
          "product_of_marginals_LR" in step3_section and "NULL_ARM" in step3_section,
          "looked for the in-scope quantities named explicitly")
    check("STEP 3 explains the ratio is a simulator-vs-estimator gap, not an estimator-recoverable property",
          "gap between the correlated simulator and an independence-assuming" in text,
          "looked for the exact reinterpretation language")


def criterion_4_underflow_and_nonmonotonicity_attributed() -> None:
    if not AUDIT.exists() or not STEP4_RECONCILIATION_TSV.exists() or not STEP4_BANDWIDTH_TSV.exists():
        check("underflow and non-monotonicity findings present with supporting data", False,
              f"audit={AUDIT.exists()}, reconciliation={STEP4_RECONCILIATION_TSV.exists()}, "
              f"bandwidth={STEP4_BANDWIDTH_TSV.exists()}")
        return
    text = AUDIT.read_text(encoding="utf-8")
    step4_section = text.split("## STEP 4", 1)[1] if "## STEP 4" in text else ""
    check("4a (underflow) has an explicit cause attributed", "Cause: attributed" in step4_section,
          "looked for an explicit 'Cause: attributed' statement in 4a")
    check("4b (non-monotonicity) has an explicit cause attributed",
          step4_section.count("Cause: attributed") >= 2,
          "looked for a second 'Cause: attributed' statement in 4b")
    normalized = " ".join(text.split())  # collapse newlines/whitespace so wrapped phrases still match
    check("4a is demonstrated by reproducing the phenomenon with stake_ablation.py's real functions "
          "(not just re-implemented)", "own, real, unmodified" in normalized,
          "looked for explicit use of the real, unmodified estimator functions")

    recon_rows = read_tsv(STEP4_RECONCILIATION_TSV)
    core_hr_dim1 = [r for r in recon_rows if r["arm"] == "CORE_HR" and r["dimension"] == "1"]
    check("failure-mode reconciliation table has CORE_HR dimension-1 rows matching the sweep's n grid",
          len(core_hr_dim1) == 12, f"{len(core_hr_dim1)} rows found (expected 12)")
    monotonic_flags = [r["combined_sequence_monotonic_up_to_noise"] for r in core_hr_dim1]
    check("reconciliation confirms (or explicitly refutes) monotonicity of the combined failure rate",
          all(f in ("True", "False") for f in monotonic_flags) and len(set(monotonic_flags)) == 1,
          f"flags: {set(monotonic_flags)}")

    bw_rows = read_tsv(STEP4_BANDWIDTH_TSV)
    check("bandwidth mechanism table covers both arms across the full n grid",
          {r["arm"] for r in bw_rows} == {"CORE_HR", "DDR_SIGNALING"} and len(bw_rows) == 24,
          f"arms: {set(r['arm'] for r in bw_rows)}, rows: {len(bw_rows)}")
    core_hr_bw = sorted((r for r in bw_rows if r["arm"] == "CORE_HR"), key=lambda r: int(r["n_per_class"]))
    top1_shares = [float(r["mean_top1_kernel_contribution_share_original_sample"]) for r in core_hr_bw]
    is_declining = all(top1_shares[i] >= top1_shares[i + 1] - 0.05 for i in range(len(top1_shares) - 1))
    check("mean top-1 kernel contribution share declines with n (demonstrates the bandwidth mechanism, "
          "not asserted)", is_declining and top1_shares[0] > top1_shares[-1],
          f"n=12 share={top1_shares[0]:.4f}, n=160 share={top1_shares[-1]:.4f}")


def criterion_5_estimator_options_covers_four_paths() -> None:
    if not OPTIONS.exists():
        check("ESTIMATOR_OPTIONS.md present", False, f"{OPTIONS} missing")
        return
    text = OPTIONS.read_text(encoding="utf-8")
    check("ESTIMATOR_OPTIONS.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("does not itself choose an option (Standing Rule 10)",
          "No option is chosen here" in text, "looked for explicit non-choice statement")

    for label, keyword in [
        ("A (keep + amend PROTOCOL.md)", "Option A"),
        ("B (true multivariate density)", "Option B"),
        ("C (penalized logistic regression)", "Option C"),
        ("D (Gaussian copula)", "Option D"),
    ]:
        section = text.split(keyword, 1)[1].split("## Option", 1)[0] if keyword in text else ""
        check(f"Option {label} present with cost, downstream impact, and evidence discussion",
              bool(section) and "Requires" in section and ("Cost" in section) and "P07/P08 survival" in section,
              f"looked for {keyword}'s own Requires/Cost/P07-P08-survival subsections")

    check("states whether P07/P08 survive for each option", text.count("P07/P08 survival") >= 4,
          f"found {text.count('P07/P08 survival')} occurrences (expected >= 4, one per option)")
    check("does not invent an unverified 'class-imbalance test' reference (Standing Rule 3)",
          "UNVERIFIED" in text or "did not find" in text.lower(),
          "looked for an explicit UNVERIFIED/not-found disclosure for the class-imbalance test claim")


def criterion_6_no_pipeline_file_modified() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    changed = {line[3:].rstrip("/") for line in result.stdout.splitlines()}
    for forbidden in ("PROTOCOL.md", "simulate.py", "signatures.py", "loh_caller.py", "stake_ablation.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    # gate8's repo-root report and the recovery table are the two known
    # multi-producer collision points from earlier tasks in this session --
    # confirm this task's own scripts did not clobber either.
    for collision_risk in ("SIMULATED_GATE8_INTERVAL_REPORT.tsv", "SIMULATED_RECOVERY_TABLE.tsv",
                            "SIMULATED_RECOVERY_TABLE.md"):
        check(f"{collision_risk} not modified by this task (no fixed-output-filename collision)",
              collision_risk not in changed, f"{collision_risk} in changed files: {collision_risk in changed}")


def criterion_7_no_p07_p08_p09_rerun() -> None:
    # Static check: this task's own new scripts must not invoke
    # loh_caller.py, signatures.py, or any P09 pipeline script.
    for script in (STEP2_SCRIPT, STEP4_SCRIPT):
        if not script.exists():
            check(f"{script.name} does not invoke P07/P08/P09 pipeline scripts", False, f"{script} missing")
            continue
        text = script.read_text(encoding="utf-8")
        invokes_forbidden = any(name in text for name in
                                 ("loh_caller.py", "signatures.py", "subprocess.run"))
        # subprocess.run alone is not disqualifying (this repo's OTHER
        # checkers use it) -- only flag if it targets a forbidden script by name.
        invokes_forbidden = "loh_caller.py" in text or "signatures.py" in text
        check(f"{script.name} does not invoke loh_caller.py or signatures.py",
              not invokes_forbidden, f"invokes_forbidden={invokes_forbidden}")


def main() -> None:
    criterion_1_spec_vs_code_quoted()
    criterion_2_step2_test_present_and_run()
    criterion_3_p09_target_meaning_stated()
    criterion_4_underflow_and_nonmonotonicity_attributed()
    criterion_5_estimator_options_covers_four_paths()
    criterion_6_no_pipeline_file_modified()
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
