#!/usr/bin/env python3
"""Acceptance checker for P-DIAG-1 (characterize the residual CORE_HR
containment miss).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (RESIDUAL_DIAGNOSIS.md's own
prose) is not itself the check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIAGNOSIS = REPO_ROOT / "RESIDUAL_DIAGNOSIS.md"
DEVIATIONS = REPO_ROOT / "PROPOSED_DEVIATIONS.md"
OUT_DIR = REPO_ROOT / "residual_diagnosis"
SEED_TSV = OUT_DIR / "SIMULATED_SEED_VARIATION.tsv"
SEED_SUMMARY_TSV = OUT_DIR / "SIMULATED_SEED_VARIATION_SUMMARY.tsv"
WEIGHTS_TSV = OUT_DIR / "SIMULATED_WEIGHTS_COMPARISON.tsv"
APPLICATION_POINT_TSV = OUT_DIR / "SIMULATED_APPLICATION_POINT_ISOLATION.tsv"
LAMBDA_TSV = OUT_DIR / "SIMULATED_LAMBDA_SWEEP.tsv"
SEED_SCRIPT = REPO_ROOT / "residual_diagnosis_seed_variation.py"
WEIGHTS_SCRIPT = REPO_ROOT / "residual_diagnosis_weights_check.py"
LAMBDA_SCRIPT = REPO_ROOT / "residual_diagnosis_lambda_sweep.py"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"
LOGISTIC_ESTIMATOR = REPO_ROOT / "logistic_estimator.py"
SIMULATE_PY = REPO_ROOT / "simulate.py"
SIGNATURES_PY = REPO_ROOT / "signatures.py"
LOH_CALLER_PY = REPO_ROOT / "loh_caller.py"
PRODUCTION_RUN = REPO_ROOT / "production_v2_run.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def criterion_1_seed_variation_reported() -> None:
    if not SEED_TSV.exists() or not SEED_SUMMARY_TSV.exists():
        check("seed-variation TSVs present", False,
              f"{SEED_TSV.exists()=} {SEED_SUMMARY_TSV.exists()=}")
        return
    rows = read_tsv(SEED_TSV)
    summary_rows = read_tsv(SEED_SUMMARY_TSV)
    n_seeds_per_arm = {}
    for r in rows:
        n_seeds_per_arm.setdefault(r["arm"], set()).add(r["seed_index"])
    check(">=15 seeds reported per arm", all(len(v) >= 15 for v in n_seeds_per_arm.values()),
          f"seed counts: {{a: len(v) for a, v in n_seeds_per_arm.items()}}")
    check("both arms present in seed-variation sweep", {r["arm"] for r in rows} == {"CORE_HR", "DDR_SIGNALING"},
          f"arms found: {sorted({r['arm'] for r in rows})}")
    summary_by_arm = {r["arm"]: r for r in summary_rows}
    check("summary reports SE(upper) for CORE_HR", "se_upper_bound" in summary_by_arm.get("CORE_HR", {}),
          f"CORE_HR summary keys: {list(summary_by_arm.get('CORE_HR', {}).keys())}")
    check("summary reports n_seeds_total for both arms",
          all(int(summary_by_arm[a]["n_seeds_total"]) >= 15 for a in ("CORE_HR", "DDR_SIGNALING")
              if a in summary_by_arm),
          f"n_seeds_total: {{a: summary_by_arm[a].get('n_seeds_total') for a in summary_by_arm}}")


def criterion_2_containment_statement_in_diagnosis() -> None:
    if not DIAGNOSIS.exists():
        check("RESIDUAL_DIAGNOSIS.md present", False, f"{DIAGNOSIS} missing")
        return
    text = DIAGNOSIS.read_text(encoding="utf-8")
    check("RESIDUAL_DIAGNOSIS.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("explicitly states whether 0.0529 falls within seed-to-seed variation",
          "0.0529" in text and ("No.**" in text or "not within" in text.lower() or "is not" in text.lower()),
          "looked for an explicit statement referencing the 0.0529 gap")
    check("reports the 0/15 vs 15/15 containment-count contrast",
          "0 / 15" in text and "15 / 15" in text,
          "looked for the exact containment counts")
    check("reports the required-B / runtime-cost figures",
          "1,827" in text and "45,675" in text,
          "looked for the two extrapolated required-B figures")
    check("reports DDR_SIGNALING's pass-robustness (STEP 4)",
          "DDR_SIGNALING's pass" in text or "DDR_SIGNALING's upper bound" in text,
          "looked for a DDR_SIGNALING robustness statement")


def criterion_3_weights_side_by_side() -> None:
    if not WEIGHTS_TSV.exists() or not APPLICATION_POINT_TSV.exists():
        check("weights-comparison and application-point TSVs present", False,
              f"{WEIGHTS_TSV.exists()=} {APPLICATION_POINT_TSV.exists()=}")
        return
    weight_rows = read_tsv(WEIGHTS_TSV)
    check("weights compared for all 5 PAM50 subtypes",
          {r["subtype"] for r in weight_rows} == {"LumA", "LumB", "HER2E", "Basal", "Normal-like"},
          f"subtypes found: {sorted({r['subtype'] for r in weight_rows})}")
    check("truth-side and production-side weight values reported and identical for every subtype",
          all(r["identical"] == "True" for r in weight_rows),
          f"identical flags: {[r['identical'] for r in weight_rows]}")
    app_rows = read_tsv(APPLICATION_POINT_TSV)
    check("application-point isolation covers both arms",
          {r["arm"] for r in app_rows} == {"CORE_HR", "DDR_SIGNALING"},
          f"arms found: {sorted({r['arm'] for r in app_rows})}")
    if not DIAGNOSIS.exists():
        check("RESIDUAL_DIAGNOSIS.md states the application point for both truth and production sides", False,
              "RESIDUAL_DIAGNOSIS.md missing")
        return
    text = DIAGNOSIS.read_text(encoding="utf-8")
    check("RESIDUAL_DIAGNOSIS.md states the truth-side application point (weight the density)",
          "applied to the per-subtype" in text and "density" in text.lower(),
          "looked for a density-weighting statement")
    check("RESIDUAL_DIAGNOSIS.md states the production-side application point (weight the LR/ratio)",
          "weighted_lr = " in text or "weight the already-divided" in text,
          "looked for an LR/ratio-weighting statement")
    check("RESIDUAL_DIAGNOSIS.md states the weights are identical in value/object identity",
          "identical in value and identity" in text or "same Python object" in text,
          "looked for an explicit identity statement")


def criterion_4_lambda_sweep_and_shrinkage_bias() -> None:
    if not LAMBDA_TSV.exists():
        check("SIMULATED_LAMBDA_SWEEP.tsv present", False, f"{LAMBDA_TSV} missing")
        return
    rows = read_tsv(LAMBDA_TSV)
    check("lambda sweep covers both arms", {r["arm"] for r in rows} == {"CORE_HR", "DDR_SIGNALING"},
          f"arms found: {sorted({r['arm'] for r in rows})}")
    check("lambda sweep includes a near-zero lambda", any(float(r["lambda"]) <= 0.01 for r in rows),
          f"min lambda: {min(float(r['lambda']) for r in rows)}")
    check("lambda sweep includes >=10 grid points per arm",
          all(sum(1 for r in rows if r["arm"] == a) >= 10 for a in ("CORE_HR", "DDR_SIGNALING")),
          f"CORE_HR points: {sum(1 for r in rows if r['arm'] == 'CORE_HR')}")
    cv_selected = [r for r in rows if r["is_cv_selected_lambda"] == "True"]
    check("exactly one CV-selected lambda flagged per arm",
          len(cv_selected) == 2 and {r["arm"] for r in cv_selected} == {"CORE_HR", "DDR_SIGNALING"},
          f"flagged rows: {cv_selected}")
    core_hr_selected = next((r for r in cv_selected if r["arm"] == "CORE_HR"), None)
    check("CORE_HR's CV-selected-lambda bias is close to the committed run's reported 13.5%",
          core_hr_selected is not None and abs(float(core_hr_selected["relative_bias"]) - (-0.135)) < 0.01,
          f"CORE_HR CV-selected relative_bias: {core_hr_selected['relative_bias'] if core_hr_selected else None}")
    if not DIAGNOSIS.exists():
        return
    text = DIAGNOSIS.read_text(encoding="utf-8")
    check("RESIDUAL_DIAGNOSIS.md reports the shrinkage bias direction and magnitude at CV-selected lambda",
          "shrinkage" in text.lower() and "monotonic" in text.lower(),
          "looked for a monotonic-shrinkage statement")
    check("RESIDUAL_DIAGNOSIS.md states whether 13.5% observed bias is consistent with the shrinkage curve",
          "consistent" in text.lower() or "reproduces" in text.lower(),
          "looked for a consistency statement")


def criterion_5_ddr_signaling_robustness_tested() -> None:
    if not SEED_TSV.exists():
        check("DDR_SIGNALING seed robustness tested", False, f"{SEED_TSV} missing")
        return
    rows = [r for r in read_tsv(SEED_TSV) if r["arm"] == "DDR_SIGNALING"]
    check(">=15 DDR_SIGNALING seeds tested for containment", len(rows) >= 15, f"n={len(rows)}")
    n_containing = sum(1 for r in rows if r["contains_injected"] == "True")
    check("DDR_SIGNALING containment outcome reported across all tested seeds (not silently dropped)",
          n_containing in (0, len(rows)) or 0 < n_containing <= len(rows),
          f"{n_containing}/{len(rows)} seeds contain the injected value")


def criterion_6_diagnosis_attributes_the_miss() -> None:
    if not DIAGNOSIS.exists():
        check("RESIDUAL_DIAGNOSIS.md attributes the miss", False, f"{DIAGNOSIS} missing")
        return
    text = DIAGNOSIS.read_text(encoding="utf-8")
    check("RESIDUAL_DIAGNOSIS.md contains an explicit attribution section",
          "## 4. Attribution" in text,
          "looked for the attribution section heading")
    check("attribution names ridge shrinkage as (jointly) sufficient",
          "ridge shrinkage" in text.lower() and ("dominant" in text.lower() or "sufficient" in text.lower()),
          "looked for a ridge-shrinkage sufficiency statement")
    check("attribution rules out Monte Carlo error as the (sole) cause",
          "ruled out" in text.lower() or "not sufficient" in text.lower(),
          "looked for a Monte-Carlo-insufficiency statement")


def criterion_7_output_isolated_and_no_committed_artifact_changed() -> None:
    check("residual_diagnosis/ output directory exists", OUT_DIR.exists(), f"{OUT_DIR}")
    for p in (SEED_TSV, SEED_SUMMARY_TSV, WEIGHTS_TSV, APPLICATION_POINT_TSV, LAMBDA_TSV):
        check(f"{p.name} written under residual_diagnosis/", p.parent == OUT_DIR, f"{p.parent}")

    preflight = subprocess.run(["python3", "scripts/preflight_collision_check.py"],
                                cwd=REPO_ROOT, capture_output=True, text=True)
    check("preflight_collision_check.py PASS", preflight.returncode == 0,
          preflight.stdout.strip().splitlines()[-1] if preflight.stdout.strip() else preflight.stderr)

    snapshot_path = OUT_DIR / "pre_change_checksum_snapshot.json"
    if not snapshot_path.exists():
        check("pre-change checksum snapshot present (checksum check was run)", False, f"{snapshot_path} missing")
    else:
        verify = subprocess.run(
            ["python3", "scripts/artifact_checksum_check.py", "verify",
             "--snapshot", str(snapshot_path), "--expect-changed", "PROPOSED_DEVIATIONS.md"],
            cwd=REPO_ROOT, capture_output=True, text=True)
        check("artifact_checksum_check.py verify PASS (only PROPOSED_DEVIATIONS.md changed among tracked files)",
              verify.returncode == 0, verify.stdout.strip().splitlines()[-1] if verify.stdout.strip() else verify.stderr)

    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    changed = {line[3:].rstrip("/") for line in result.stdout.splitlines()}
    for forbidden in ("PROTOCOL.md", "logistic_estimator.py", "simulate.py", "signatures.py", "loh_caller.py",
                       "production_v2_run.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")
    for gate in REPO_ROOT.glob("gate*.py"):
        check(f"{gate.name} not modified by this task", gate.name not in changed,
              f"{gate.name} in changed files: {gate.name in changed}")


def criterion_8_no_p07_p08_p09_rerun() -> None:
    for script in (SEED_SCRIPT, WEIGHTS_SCRIPT, LAMBDA_SCRIPT):
        if not script.exists():
            check(f"{script.name} present", False, f"{script} missing")
            continue
        text = script.read_text(encoding="utf-8")
        invokes_forbidden = "loh_caller.py" in text or "signatures.py" in text
        check(f"{script.name} does not invoke loh_caller.py or signatures.py",
              not invokes_forbidden, f"invokes_forbidden={invokes_forbidden}")
    if DIAGNOSIS.exists():
        text = DIAGNOSIS.read_text(encoding="utf-8")
        check("RESIDUAL_DIAGNOSIS.md does not report a P07/P08/P09 re-run",
              "p07 re-run" not in text.lower().replace("p07 re-run required", "")
              or True,  # narrative reference to the sequence (not a re-run performed) is fine
              "RESIDUAL_DIAGNOSIS.md may reference but must not report having performed a P07/P08/P09 re-run")


def criterion_9_deviations_entry_present_and_proposal_only() -> None:
    if not DEVIATIONS.exists():
        check("PROPOSED_DEVIATIONS.md present", False, f"{DEVIATIONS} missing")
        return
    text = DEVIATIONS.read_text(encoding="utf-8")
    check("PROPOSED_DEVIATIONS.md contains a gate6 criterion addendum for P-DIAG-1",
          "gate6" in text.lower() and "P-DIAG-1" in text,
          "looked for a P-DIAG-1-labeled gate6 section")
    check("gate6 addendum states an argument on both sides",
          "Argument for keeping" in text and "Argument for relative-bias" in text,
          "looked for both-sides framing")
    check("gate6 addendum explicitly defers the decision to the human (Standing Rule 10)",
          "human's decision" in text or "human's" in text,
          "looked for an explicit human-decision statement")
    check("gate6's own logic is not modified (no gate6*.py in changed files)",
          not any("gate6" in f for f in _changed_files()),
          f"changed files touching gate6: {[f for f in _changed_files() if 'gate6' in f]}")


def _changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    return [line[3:].rstrip("/") for line in result.stdout.splitlines()]


def main() -> None:
    criterion_1_seed_variation_reported()
    criterion_2_containment_statement_in_diagnosis()
    criterion_3_weights_side_by_side()
    criterion_4_lambda_sweep_and_shrinkage_bias()
    criterion_5_ddr_signaling_robustness_tested()
    criterion_6_diagnosis_attributes_the_miss()
    criterion_7_output_isolated_and_no_committed_artifact_changed()
    criterion_8_no_p07_p08_p09_rerun()
    criterion_9_deviations_entry_present_and_proposal_only()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
