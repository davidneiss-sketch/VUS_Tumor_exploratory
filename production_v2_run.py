#!/usr/bin/env python3
"""STEP 6 -- produces genuine production output for the NEW estimator
(logistic_estimator.py), for gate4, gate6, and gate8 to run against, in
a DEDICATED directory (production_v2/) -- NOT the repo root, NOT the
existing production/ directory (that holds the OLD estimator's own
clean, already-committed example; gate6_recovery.py's own
SIMULATED_RECOVERY_TABLE.tsv has no merge-awareness protection against a
DIFFERENT script writing to the SAME outdir with a different scope --
this project has hit that exact collision twice this session already,
each time fixed by using a dedicated outdir instead. Same fix applied
here, before any collision, not after).

SIMULATED: read-only imports of logistic_estimator.py. Does not modify
PROTOCOL.md, simulate.py, or logistic_estimator.py. Fits at
PROTOCOL.md's own B=2000 replicate count (feasible here: ~0.06s/fit at
n=1848/class, benchmarked this session, so B=2000 costs roughly 2
minutes per stratum) -- this is the genuine protocol replicate count,
not a reduced one, for these 2 production strata specifically (unlike
the wider sweeps this task also runs, which do disclose a reduction).

Run: python3 production_v2_run.py
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
import logistic_estimator as le  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
LOCAL_SEED = 20260910
B_PROTOCOL = 2000  # PROTOCOL.md section 7.3's actual replicate count -- read live below, asserted to match
LAMBDA_FIXED = 1.0  # a fixed, moderate ridge strength for this production run (CV-selection is demonstrated separately in CALIBRATION_DIAGNOSTICS.md; fixing it here keeps this run's cost bounded to 2 strata x B=2000, not 2 strata x 5 folds x 9 lambdas x B=2000)
REF_COVARIATES = {"purity": 0.5, "subtype": "LumA", "wgd": 0}

OUT_DIR = REPO_ROOT / "production_v2"


def read_protocol_b() -> int:
    import re
    text = (REPO_ROOT / "PROTOCOL.md").read_text(encoding="utf-8")
    matches = sorted({int(m.group(1)) for m in re.finditer(r"\bB\s*=\s*(\d+)\b", text)})
    assert len(matches) == 1, f"PROTOCOL.md's B is ambiguous: {matches}"
    return matches[0]


def main() -> None:
    print(BANNER)
    protocol_b = read_protocol_b()
    assert protocol_b == B_PROTOCOL, f"PROTOCOL.md's B ({protocol_b}) != this script's B_PROTOCOL ({B_PROTOCOL})"
    OUT_DIR.mkdir(exist_ok=True)

    rng = random.Random(LOCAL_SEED)
    pop = le.load_population()
    pop_by_arm = {"CORE_HR": {"Pathogenic": [], "Benign": []}, "DDR_SIGNALING": {"Pathogenic": [], "Benign": []}}
    for r in pop:
        pop_by_arm[r["arm"]][r["true_class"]].append(r)

    lr_table_rows = []
    recovered_rows = []
    ablation_rows = []

    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        print(f"\n--- Fitting {arm}, n_path={len(path_records)}, n_benign={len(benign_records)}, B={B_PROTOCOL} ---")
        point_result = le.fit_and_score(path_records, benign_records, le.EVAL_POINT,
                                          REF_COVARIATES["purity"], REF_COVARIATES["subtype"],
                                          REF_COVARIATES["wgd"], LAMBDA_FIXED, verbose=True)
        point = point_result["lr"]
        ci_low, ci_high, _ = le.bootstrap_ci_logistic(path_records, benign_records, le.EVAL_POINT,
                                                        REF_COVARIATES["purity"], REF_COVARIATES["subtype"],
                                                        REF_COVARIATES["wgd"], LAMBDA_FIXED, rng, B_PROTOCOL,
                                                        verbose_first=False)
        print(f"  point={point:.6f}  CI=[{ci_low:.6f}, {ci_high:.6f}]  (B={B_PROTOCOL} bootstrap replicates, "
              f"identical prior-odds correction n_path_ref={len(path_records)}/n_benign_ref={len(benign_records)} "
              f"applied to every replicate since resample size is fixed)")

        lr_table_rows.append({
            "stratum": f"{arm}_pooled_full_vector", "gene_group": arm, "status": "FITTED",
            "point_estimate": point, "ci_low": ci_low, "ci_high": ci_high,
            "n_replicates": B_PROTOCOL, "n_pathogenic": len(path_records), "n_benign": len(benign_records),
        })

        quantity = f"{arm.lower()}_joint_LR"
        recovered_rows.append({
            "quantity": quantity, "recovered_point": point, "ci_low": ci_low, "ci_high": ci_high,
            "estimand": "LR",
        })

        ablation_rows.append({
            "arm": arm, "feature_subset": "LOH_GIS_SBS3", "n_scenario": "PRODUCTION_V2_FULL_N",
            "point_estimate": point, "ci_low": ci_low, "ci_high": ci_high,
        })

    # gate4 LR table
    lr_path = OUT_DIR / "SIMULATED_LR_TABLE.tsv"
    with open(lr_path, "w", newline="", encoding="utf-8") as f:
        cols = ["stratum", "gene_group", "status", "point_estimate", "ci_low", "ci_high",
                "n_replicates", "n_pathogenic", "n_benign"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in lr_table_rows:
            w.writerow(r)
    print(f"\nWrote {lr_path}")

    # gate6 recovered + scope (against the REAL, repo-root SIMULATED_TRUTH.tsv)
    recovered_path = OUT_DIR / "SIMULATED_RECOVERED.tsv"
    with open(recovered_path, "w", newline="", encoding="utf-8") as f:
        cols = ["quantity", "recovered_point", "ci_low", "ci_high", "estimand"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in recovered_rows:
            w.writerow(r)
    print(f"Wrote {recovered_path}")

    with open(REPO_ROOT / "SIMULATED_TRUTH.tsv", newline="", encoding="utf-8") as f:
        all_truth_quantities = [row["quantity"] for row in csv.DictReader(f, delimiter="\t")]
    recovered_quantities = {r["quantity"] for r in recovered_rows}
    scope_path = OUT_DIR / "SIMULATED_scope.tsv"
    with open(scope_path, "w", newline="", encoding="utf-8") as f:
        cols = ["quantity", "in_scope", "reason"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for q in all_truth_quantities:
            if q in recovered_quantities:
                w.writerow({"quantity": q, "in_scope": "TRUE",
                            "reason": "newly reachable under PROPOSED_PROTOCOL_AMENDMENT.md's estimator "
                                      "(REACHABILITY_TABLE.tsv: NEWLY_REACHABLE) -- recovered by this "
                                      "production_v2 run, pooled full feature vector, B=2000."})
            else:
                w.writerow({"quantity": q, "in_scope": "FALSE",
                            "reason": "out of scope for this task's production_v2 gate6 run, which recovers "
                                      "only the 2 pooled joint_LR quantities as a representative, tractable "
                                      "subset of the 24 quantities REACHABILITY_TABLE.tsv marks NEWLY_REACHABLE "
                                      "-- not a claim this quantity is unreachable, see REACHABILITY_TABLE.tsv "
                                      "for its actual classification."})
    print(f"Wrote {scope_path}")

    # gate8 ablation-style table (reuses the SAME 2 fits, no extra compute)
    ablation_path = OUT_DIR / "SIMULATED_ABLATION_TABLE_V2.tsv"
    with open(ablation_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "feature_subset", "n_scenario", "point_estimate", "ci_low", "ci_high"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in ablation_rows:
            w.writerow(r)
    print(f"Wrote {ablation_path}")

    # gate9 imbalance sweep (cheap -- point estimates only, no B=2000 bootstrap needed)
    gate9_rows = []
    ratios = [("1:1", 300, 300), ("1:5", 60, 300), ("1:20", 15, 300)]
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        for label, n_path, n_benign in ratios:
            for rep in range(5):
                path_sample = rng.sample(path_records, n_path)
                benign_sample = rng.sample(benign_records, n_benign)
                result = le.fit_and_score(path_sample, benign_sample, le.EVAL_POINT,
                                            REF_COVARIATES["purity"], REF_COVARIATES["subtype"],
                                            REF_COVARIATES["wgd"], LAMBDA_FIXED, verbose=(rep == 0))
                gate9_rows.append({
                    "test_case": arm, "class_ratio_label": label, "n_pathogenic_ref": n_path,
                    "n_benign_ref": n_benign, "recovered_lr": result["lr"], "replicate_index": rep,
                })
    gate9_path = OUT_DIR / "SIMULATED_GATE9_INPUT.tsv"
    with open(gate9_path, "w", newline="", encoding="utf-8") as f:
        cols = ["test_case", "class_ratio_label", "n_pathogenic_ref", "n_benign_ref", "recovered_lr", "replicate_index"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in gate9_rows:
            w.writerow(r)
    print(f"Wrote {gate9_path} ({len(gate9_rows)} rows)")


if __name__ == "__main__":
    main()
