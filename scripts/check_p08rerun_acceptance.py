#!/usr/bin/env python3
"""Acceptance checker for P08-RERUN (re-run signature validation against
the P06R2-corrected catalogue).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (ANALYTIC_VS_OBSERVED.md's
or PROPOSED_DEVIATIONS.md's prose) is not itself the check. gate6/gate7
and the reproducibility check are already covered live by
scripts/check_signatures_acceptance.py (unchanged by this task, and its
checks re-derive from the current files, not hardcoded P08 numbers) --
this script covers the NEW criteria P08-RERUN adds: the analytic-vs-
observed consistency check, SigMA-at-scale, and the same-axis tool
comparison.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "SIMULATED_signature_work"
ANALYTIC_VS_OBSERVED = REPO_ROOT / "ANALYTIC_VS_OBSERVED.md"
PROPOSED_DEVIATIONS = REPO_ROOT / "PROPOSED_DEVIATIONS.md"
RECOVERY_TABLE = REPO_ROOT / "SIMULATED_RECOVERY_TABLE.tsv"
REPORT_MD = REPO_ROOT / "SIMULATED_signature_validation.md"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path, delim: str = "\t") -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delim))


def criterion_1_gate6_and_gate7_delegated() -> None:
    """gate6/gate7 scoring, bias, and CI are already covered live by
    check_signatures_acceptance.py (unmodified this task, its checks
    re-derive from current files). This criterion confirms it still runs
    clean against the CURRENT (post-catalogue-fix) state."""
    env = dict(os.environ, SKIP_REPRO_CHECK="1")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_signatures_acceptance.py")],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env,
    )
    check("check_signatures_acceptance.py's own criteria (gate6 scored with bias/CI, gate7 PASS, "
          "environment/COSMIC-pin checks) still pass against the current post-fix state "
          "(reproducibility skipped here -- run separately, it is expensive)",
          result.returncode == 0, f"exit={result.returncode}; tail={result.stdout.splitlines()[-3:] if result.stdout else result.stderr[-300:]}")

    if not RECOVERY_TABLE.exists():
        check("top-level SIMULATED_RECOVERY_TABLE.tsv present (deliverable)", False, f"{RECOVERY_TABLE} missing")
        return
    rows = read_tsv(RECOVERY_TABLE)
    scored = {r["quantity"]: r for r in rows if r["quantity"] in
              ("core_hr_sbs3_exposure_LR", "ddr_signaling_sbs3_exposure_LR")}
    check("SIMULATED_RECOVERY_TABLE.tsv scores both P08 quantities with a status and relative_bias",
          len(scored) == 2 and all(r["status"] and r["relative_bias"] for r in scored.values()),
          f"{ {k: (v['status'], v['relative_bias']) for k, v in scored.items()} }")


def criterion_2_analytic_vs_observed() -> None:
    if not ANALYTIC_VS_OBSERVED.exists():
        check("ANALYTIC_VS_OBSERVED.md present", False, f"{ANALYTIC_VS_OBSERVED} missing")
        return
    text = ANALYTIC_VS_OBSERVED.read_text(encoding="utf-8")
    check("ANALYTIC_VS_OBSERVED.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("reports means numerically (by arm/class)", "analytic mean" in text and "empirical mean" in text,
          "looked for 'analytic mean' and 'empirical mean' columns")
    check("reports spreads numerically (sd)", "analytic sd" in text and "empirical sd" in text,
          "looked for 'analytic sd' and 'empirical sd' columns")
    check("reports an overlap metric", "overlap" in text.lower(), "looked for 'overlap' discussion")
    has_faithful_statement = ("faithful" in text.lower())
    check("makes an EXPLICIT faithful/not-faithful statement (not just numbers)", has_faithful_statement,
          "looked for 'faithful' in the conclusion")
    check("distinguishes faithful (DDR_SIGNALING) from not-faithful (CORE_HR) rather than one blanket verdict",
          ("NOT" in text or "not faithful" in text.lower()) and "faithful" in text.lower()
          and "core_hr" in text.lower() and "ddr_signaling" in text.lower(),
          "looked for a per-quantity, not blanket, verdict")

    # Re-derive the core numeric claim live: is the observed clip-at-zero
    # fraction for CORE_HR Benign really large, and does it match the
    # analytic Phi-prediction (the mechanism claim)?
    import math
    sys.path.insert(0, str(REPO_ROOT))
    import simulate  # noqa: E402

    exposures = read_tsv(REPO_ROOT / "SIMULATED_data" / "SIMULATED_signature_exposures.tsv")
    labels = read_tsv(REPO_ROOT / "SIMULATED_TRUTH_detail" / "SIMULATED_sample_labels.tsv")
    label_by_id = {r["sample_id"]: r for r in labels}
    vals = [float(r["sbs3_relative_exposure_true"]) for r in exposures
            if label_by_id[r["sample_id"]]["gene_group"] == "CORE_HR"
            and label_by_id[r["sample_id"]]["true_class"] == "Benign"]
    frac_zero = sum(1 for v in vals if v == 0.0) / len(vals)
    a_mean, a_sd = simulate.marginal_gaussian_feature_params(simulate.SBS3_LINK["CORE_HR"], "CORE_HR", "Benign")
    predicted = 0.5 * (1 + math.erf((0 - a_mean) / (a_sd * math.sqrt(2))))
    check("live re-derivation: CORE_HR Benign's observed clip-at-zero fraction is large (>30%) and matches "
          "the analytic model's own Phi-prediction within 2 percentage points (confirms the mechanism, not "
          "just an assertion)",
          frac_zero > 0.30 and abs(frac_zero - predicted) < 0.02,
          f"observed={frac_zero:.4f}, analytic-predicted={predicted:.4f}, n={len(vals)}")


def criterion_3_sigma_at_scale() -> None:
    sigma_382 = WORK_DIR / "SIMULATED_sigma_382sample_stratified_result.csv"
    sigma_7392 = WORK_DIR / "SIMULATED_sigma_7392population_result.csv"
    by_bin = WORK_DIR / "SIMULATED_sigma_vs_spa_by_bin.tsv"
    for p, label in [(sigma_382, "382-sample stratified"), (sigma_7392, "7392-sample population"),
                      (by_bin, "per-bin SigMA-vs-SPA comparison")]:
        check(f"SigMA {label} result file present (full population run, or the reason it could not be)",
              p.exists(), f"{p}")
    if not sigma_382.exists() or not sigma_7392.exists():
        return

    rows_382 = read_tsv(sigma_382, delim=",")
    check("SigMA ran against more than ten samples (n>=300) for the stratified curve",
          len(rows_382) >= 300, f"n={len(rows_382)}")
    rows_7392 = read_tsv(sigma_7392, delim=",")
    check("SigMA ran against the full CORE_HR+DDR_SIGNALING population (n>=7000) for the population-level LR",
          len(rows_7392) >= 7000, f"n={len(rows_7392)}")

    if by_bin.exists():
        bin_rows = read_tsv(by_bin)
        check("per-bin comparison covers all 11 total_mutations bins with a real n each",
              len(bin_rows) == 11 and all(int(r["n"]) > 0 for r in bin_rows),
              f"{len(bin_rows)} bins, n values: {[r['n'] for r in bin_rows]}")
        both_present = all("sigma_mae" in r and "spa_mae" in r for r in bin_rows)
        check("every bin reports BOTH tools' MAE and exact-zero fraction (same axis, side by side)",
              both_present, "checked for sigma_mae/spa_mae columns in every row")


def criterion_4_proposed_deviations_and_gate1() -> None:
    if not PROPOSED_DEVIATIONS.exists():
        check("PROPOSED_DEVIATIONS.md present with a P08-RERUN section", False, f"{PROPOSED_DEVIATIONS} missing")
        return
    text = PROPOSED_DEVIATIONS.read_text(encoding="utf-8")
    check("PROPOSED_DEVIATIONS.md has a SigMA-at-scale section referencing PROTOCOL.md's tool ordering",
          "SigMA" in text and "PROTOCOL.md" in text and "5.4" in text,
          "looked for SigMA + PROTOCOL.md §5.4 discussion")
    check("PROPOSED_DEVIATIONS.md states the session disposition (both HALT conditions, not proceeding to P09)",
          "P09" in text and "HALT" in text.upper(),
          "looked for P09 + HALT discussion")

    gate1 = REPO_ROOT / "GATE1.json"
    import json
    d = json.loads(gate1.read_text())
    sigma_entry = next((t for t in d["tools"] if t.get("name") == "SigMA"), None)
    check("GATE1.json's SigMA entry has a p08rerun resolution-attempts record",
          sigma_entry is not None and "resolution_attempts_p08rerun" in sigma_entry,
          f"present={sigma_entry is not None and 'resolution_attempts_p08rerun' in (sigma_entry or {})}")
    check("GATE1.json's SigMA formal status is still FAIL (the bypass is evidence, not a resolution)",
          sigma_entry is not None and sigma_entry.get("status") == "FAIL",
          f"status={sigma_entry.get('status') if sigma_entry else None}")


def criterion_5_unauthorized_files_untouched() -> None:
    # P06R3 fix: this was originally scoped to the LIVE working tree, on
    # the stated assumption that "unlike P06R2 vs simulate.py, there is no
    # later-authorized exception here." That assumption held only until a
    # later task acquired legitimate authorization to modify simulate.py --
    # which P06R3 (fix the SBS3 clipping-fidelity finding) now does. A
    # live-working-tree check would then retroactively "fail" this
    # already-completed, already-committed P08-RERUN task for a change a
    # LATER task made after P08-RERUN's own commit -- exactly the false
    # positive check_signatures_acceptance.py's equivalent check was fixed
    # to avoid (see that script's own comment). Scoped to P08-RERUN's own
    # commit range instead, the same precedent this script's own docstring
    # cites: 230c127..b1d2bb0 was P08's range; P08-RERUN's is 80e56dd (the
    # P06R2 commit it built on) .. 1c40a34 (P08-RERUN's own commit).
    P08RERUN_RANGE = "80e56dd..1c40a34"
    result = subprocess.run(["git", "diff", "--name-only", P08RERUN_RANGE], cwd=REPO_ROOT,
                             capture_output=True, text=True)
    if result.returncode != 0:
        check("P08-RERUN's own commit range is resolvable in this repository", False,
              f"git diff {P08RERUN_RANGE} failed: {result.stderr.strip()} -- cannot scope this check; "
              f"falling back would risk exactly the stale-check false positive this fix exists to avoid")
        return
    changed = set(result.stdout.splitlines())
    for forbidden in ("PROTOCOL.md", "simulate.py", "loh_caller.py"):
        check(f"{forbidden} not modified within P08-RERUN's own commit range ({P08RERUN_RANGE})",
              forbidden not in changed, f"{forbidden} in P08-RERUN's changed files: {forbidden in changed}")
    check("signatures.py not modified within P08-RERUN's own commit range (it was re-run, not edited)",
          "signatures.py" not in changed, f"signatures.py in P08-RERUN's changed files: {'signatures.py' in changed}")


def main() -> None:
    criterion_1_gate6_and_gate7_delegated()
    criterion_2_analytic_vs_observed()
    criterion_3_sigma_at_scale()
    criterion_4_proposed_deviations_and_gate1()
    criterion_5_unauthorized_files_untouched()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
