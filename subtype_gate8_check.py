#!/usr/bin/env python3
"""subtype_gate8_check.py -- subtype fix STEP 5: run gate8 against the new,
subtype-stratified truth. The subtype-stratified quantities have smaller
per-stratum n than the pooled ones this project has scored before -- this
reports which strata gate8 marks UNINFORMATIVE, as a finding about what
the study can resolve, not something to tune away (per this task's own
instruction).

Reuses stake_ablation.py's PROTOCOL.md §7.1 estimator (Gaussian KDE +
Jeffreys-corrected proportion + product-of-marginals) and
gate8_interval_informativeness.py's own informativeness check, both
read-only imports -- does not modify either file, or simulate.py/
signatures.py/loh_caller.py/PROTOCOL.md.

Run: python3 subtype_gate8_check.py
"""
from __future__ import annotations

import csv
import random
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "gates"))
import stake_ablation as sa  # noqa: E402
import simulate  # noqa: E402

LOCAL_SEED = 20260909
B_REPLICATES = 2000  # PROTOCOL.md §7.3, full spec -- per-stratum n is small enough this is cheap

SUBTYPES = list(simulate.PAM50_PROPORTIONS)


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_population_with_subtype() -> list[dict]:
    labels = read_tsv(REPO_ROOT / "SIMULATED_TRUTH_detail" / "SIMULATED_sample_labels.tsv")
    samples = read_tsv(REPO_ROOT / "SIMULATED_data" / "SIMULATED_sample_metadata.tsv")
    exposures = read_tsv(REPO_ROOT / "SIMULATED_data" / "SIMULATED_signature_exposures.tsv")
    sample_by_id = {r["sample_id"]: r for r in samples}
    exposure_by_id = {r["sample_id"]: r for r in exposures}
    pop = []
    for lab in labels:
        sid = lab["sample_id"]
        if lab["gene_group"] not in ("CORE_HR", "DDR_SIGNALING"):
            continue
        s = sample_by_id[sid]
        e = exposure_by_id[sid]
        pop.append({
            "sample_id": sid, "arm": lab["gene_group"], "true_class": lab["true_class"],
            "subtype": s["pam50_subtype"],
            "wt_lost": 1 if lab["hidden_direction"] == "WT_LOST" else 0,
            "gis": float(s["gis_score"]), "sbs3": float(e["sbs3_relative_exposure_true"]),
        })
    return pop


def main() -> None:
    pop = load_population_with_subtype()
    rng = random.Random(LOCAL_SEED)
    subset = ("wt_lost", "gis", "sbs3")

    rows = []
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        for subtype in SUBTYPES:
            path_records = [r for r in pop if r["arm"] == arm and r["true_class"] == "Pathogenic" and r["subtype"] == subtype]
            benign_records = [r for r in pop if r["arm"] == arm and r["true_class"] == "Benign" and r["subtype"] == subtype]
            n_path, n_benign = len(path_records), len(benign_records)
            n_total = n_path + n_benign
            row_id = f"{arm}/{subtype}"
            if n_total < 20:
                rows.append({"row_id": row_id, "arm": arm, "subtype": subtype, "n_pathogenic": n_path,
                             "n_benign": n_benign, "n_total": n_total, "point_estimate": "", "ci_low": "",
                             "ci_high": "", "true_reference_joint_LR": round(simulate.joint_lr_subtype(arm, subtype, simulate.EVAL_POINT), 6)})
                print(f"{row_id}: n_total={n_total} < 20 -> INSUFFICIENT_N (no interval computed)")
                continue
            path = sa.pool_features(path_records)
            benign = sa.pool_features(benign_records)
            point = sa.joint_lr_for_subset(subset, path, benign)
            ci_low, ci_high, _ = sa.bootstrap_ci(subset, path, benign, rng, B_REPLICATES)
            true_ref = simulate.joint_lr_subtype(arm, subtype, simulate.EVAL_POINT)
            rows.append({"row_id": row_id, "arm": arm, "subtype": subtype, "n_pathogenic": n_path,
                         "n_benign": n_benign, "n_total": n_total, "point_estimate": round(point, 6),
                         "ci_low": round(ci_low, 6), "ci_high": round(ci_high, 6),
                         "true_reference_joint_LR": round(true_ref, 6)})
            print(f"{row_id}: n_path={n_path} n_benign={n_benign} point={point:.4f} CI=[{ci_low:.4f},{ci_high:.4f}] "
                  f"true_ref={true_ref:.4f}")

    out_path = REPO_ROOT / "SIMULATED_SUBTYPE_STRATUM_ESTIMATES.tsv"
    columns = ["row_id", "arm", "subtype", "n_pathogenic", "n_benign", "n_total", "point_estimate",
               "ci_low", "ci_high", "true_reference_joint_LR"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(rows)} rows)")

    # A DEDICATED outdir, not REPO_ROOT: gate8_interval_informativeness.py
    # writes an unconditional, fixed-name SIMULATED_GATE8_INTERVAL_REPORT.tsv
    # (no merge-awareness, unlike gate6_recovery.py post-P06R3) -- running it
    # again at the repo root would silently clobber the STAKE task's own,
    # already-committed gate8 report (ABLATION_TABLE.tsv-derived), exactly
    # the multi-producer-collision class of bug P06R3's REVERSION_DIAGNOSIS.md
    # diagnosed for gate6's repo-root SIMULATED_RECOVERY_TABLE.tsv. Confirmed
    # by reproducing it once during this task's own development (git-restored
    # before commit) -- not a hypothetical concern.
    gate8_outdir = REPO_ROOT / "SIMULATED_subtype_gate8_out"
    gate8 = REPO_ROOT / "gates" / "gate8_interval_informativeness.py"
    proc = subprocess.run(
        [sys.executable, str(gate8), "--table", str(out_path), "--id-cols", "row_id",
         "--point-col", "point_estimate", "--ci-low-col", "ci_low", "--ci-high-col", "ci_high",
         "--outdir", str(gate8_outdir)],
        cwd=REPO_ROOT,
    )
    print(f"\ngate8_interval_informativeness.py exit code: {proc.returncode} (report: {gate8_outdir}/SIMULATED_GATE8_INTERVAL_REPORT.tsv)")


if __name__ == "__main__":
    main()
