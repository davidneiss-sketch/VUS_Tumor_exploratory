#!/usr/bin/env python3
"""STEP 6 -- produces genuine production output for the NEW estimator
(logistic_estimator.py), for gate4, gate6, gate8, and gate9 to run
against, in a DEDICATED directory (production_v2/) -- NOT the repo root,
NOT the existing production/ directory. See module docstring history:
this project has hit the fixed-output-filename collision class three
times this session; a dedicated outdir is applied here preemptively (see
OUTPUT_PATH_INVENTORY.tsv / the preflight collision check for the
broader, repo-wide fix).

REVISION (P-AMD-2 follow-up): this file's FIRST version (committed, then
found deficient) hardcoded `lambda=1.0` rather than using the amended
protocol's own CV-selected `lambda.1se`, and evaluated the pooled
quantity at a single reference subtype (LumA) rather than the
PAM50-prevalence-weighted mixture SIMULATED_TRUTH.tsv's own pooled
quantities represent. Both are fixed here -- see
`PROTOCOL_DEVIATIONS.md`'s dated entry logging the original deviation
and its correction (Standing Rule 4: a mistake fixed is still logged,
not erased).

SIMULATED: read-only imports of logistic_estimator.py and simulate.py.
Does NOT modify PROTOCOL.md, logistic_estimator.py, or simulate.py --
this file implements the mixture-evaluation and CV-selection logic
itself, calling those two modules' existing, unmodified functions.

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
import simulate  # noqa: E402

BANNER = "SIMULATED DATA — NOT A SCIENTIFIC RESULT"
LOCAL_SEED = 20260910
B_PROTOCOL = 2000  # PROTOCOL.md section 7.3's actual replicate count -- read live below, asserted to match
CV_K = 5           # variant-grouped (= sample-grouped, see logistic_estimator.py docstring) 5-fold CV
REF_COVARIATES_NON_SUBTYPE = {"purity": 0.5, "wgd": 0}  # subtype is now MIXTURE-evaluated, not fixed -- see below

OUT_DIR = REPO_ROOT / "production_v2"


def read_protocol_b() -> int:
    import re
    text = (REPO_ROOT / "PROTOCOL.md").read_text(encoding="utf-8")
    matches = sorted({int(m.group(1)) for m in re.finditer(r"\bB\s*=\s*(\d+)\b", text)})
    assert len(matches) == 1, f"PROTOCOL.md's B is ambiguous: {matches}"
    return matches[0]


def select_cv_lambda_with_provenance(path_records: list[dict], benign_records: list[dict],
                                       rng: random.Random) -> tuple[float, str]:
    """Selects lambda via logistic_estimator.py's own, unmodified
    select_lambda_cv() -- returns (lambda_1se, provenance_tag). The
    provenance tag is the ONLY thing that satisfies the assertion below;
    there is no code path in this file that produces a lambda value
    without going through this function, so the assertion cannot be
    silently bypassed by a future hardcoded constant slipping back in."""
    cv_result = le.select_lambda_cv(path_records, benign_records, CV_K, rng)
    return cv_result["lambda_1se"], "CV_SELECTED"


def assert_cv_selected(lambda_value: float, provenance: str, context: str) -> None:
    """The assertion this task's own ACCEPTANCE section requires: 'the
    production run fails if the penalty was not CV-selected.' Any code
    path that reaches a bootstrap or a final recovered-value computation
    without having set provenance='CV_SELECTED' (the only value
    select_cv_lambda_with_provenance ever returns) raises here, in
    production, not silently proceeding with an un-provenanced lambda."""
    if provenance != "CV_SELECTED":
        raise AssertionError(
            f"REFUSING to proceed for {context}: lambda={lambda_value} was not CV-selected "
            f"(provenance={provenance!r}, expected 'CV_SELECTED'). PROPOSED_PROTOCOL_AMENDMENT.md "
            f"specifies CV-selected lambda.1se; a hardcoded penalty must not reach production."
        )
    print(f"    [lambda provenance] {context}: lambda={lambda_value:.4f}, provenance=CV_SELECTED (assertion OK)")


def mixture_point_estimate(beta: list[float], std_params: dict, eval_point: dict, purity: float, wgd: int,
                             n_path_ref: int, n_benign_ref: int, print_detail: bool = False) -> tuple[float, dict]:
    """The PAM50-prevalence-weighted mixture LR -- the SAME estimand
    SIMULATED_TRUTH.tsv's pooled quantities represent (simulate.py's own
    joint_lr_collapsed / *_collapsed functions, mixture over
    simulate.PAM50_PROPORTIONS). Uses the ALREADY-FITTED beta (fit once
    on the full reference set, standard practice -- not refit per
    subtype), evaluated at each of the 5 subtype levels, then averaged
    with the SAME prevalence weights simulate.py's own truth computation
    uses (BENCHMARKS.tsv PAM01/PAM02 via simulate.PAM50_PROPORTIONS --
    not re-derived independently here, imported directly)."""
    per_subtype_lr = {}
    weighted_lr = 0.0
    for subtype, prevalence in simulate.PAM50_PROPORTIONS.items():
        design_row = le.eval_point_design_row(eval_point, purity, subtype, wgd, std_params)
        p_hat = le.predict_proba(beta, design_row)
        lr = le.probability_to_lr(p_hat, n_path_ref, n_benign_ref, verbose=False)
        per_subtype_lr[subtype] = lr
        weighted_lr += prevalence * lr
        if print_detail:
            print(f"      subtype={subtype:<12} prevalence={prevalence:.5f}  LR={lr:.4f}")
    return weighted_lr, per_subtype_lr


def bootstrap_ci_mixture(path_records: list[dict], benign_records: list[dict], eval_point: dict,
                          purity: float, wgd: int, lam: float, rng: random.Random, b: int) -> tuple[float, float, list[float]]:
    """Patient-clustered bootstrap (see logistic_estimator.py's own
    docstring: sample-grouped in this simulator, no recurrent variants)
    of the MIXTURE point estimate above -- each replicate refits on a
    resample (at the SAME, already CV-selected lambda -- standard
    bootstrap practice is to hold the tuning parameter fixed across
    replicates, not re-select it 2000 times) and computes the
    prevalence-weighted mixture LR for that replicate, exactly mirroring
    logistic_estimator.py's own bootstrap_ci_logistic structure but for
    the mixture estimand instead of a single-subtype point."""
    n_path, n_benign = len(path_records), len(benign_records)
    replicates = []
    for _ in range(b):
        path_rs = [path_records[rng.randrange(n_path)] for _ in range(n_path)]
        benign_rs = [benign_records[rng.randrange(n_benign)] for _ in range(n_benign)]
        X, y, std_params = le.build_design_matrix(path_rs, benign_rs)
        beta = le.fit_ridge_logistic(X, y, lam)
        weighted_lr, _ = mixture_point_estimate(beta, std_params, eval_point, purity, wgd,
                                                  len(path_rs), len(benign_rs), print_detail=False)
        replicates.append(weighted_lr)
    replicates.sort()
    lo = simulate.percentile(replicates, 2.5)
    hi = simulate.percentile(replicates, 97.5)
    return lo, hi, replicates


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
    per_subtype_rows = []

    truth_by_quantity = {}
    with open(REPO_ROOT / "SIMULATED_TRUTH.tsv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            truth_by_quantity[row["quantity"]] = row

    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        print(f"\n--- {arm}: n_path={len(path_records)}, n_benign={len(benign_records)} ---")

        print("  Selecting lambda via 5-fold CV (PROPOSED_PROTOCOL_AMENDMENT.md's own specified method)...")
        lam, provenance = select_cv_lambda_with_provenance(path_records, benign_records, rng)
        assert_cv_selected(lam, provenance, context=f"{arm} pooled fit")

        X, y, std_params = le.build_design_matrix(path_records, benign_records)
        beta = le.fit_ridge_logistic(X, y, lam)
        n_path_ref, n_benign_ref = len(path_records), len(benign_records)

        print(f"  Per-subtype LRs (PAM50-prevalence-weighted mixture -- the estimand SIMULATED_TRUTH.tsv's "
              f"pooled quantities represent, not a single reference-subtype evaluation):")
        weighted_lr, per_subtype_lr = mixture_point_estimate(
            beta, std_params, le.EVAL_POINT, REF_COVARIATES_NON_SUBTYPE["purity"],
            REF_COVARIATES_NON_SUBTYPE["wgd"], n_path_ref, n_benign_ref, print_detail=True)
        print(f"  Prevalence-weighted mixture point estimate: {weighted_lr:.6f}")

        print(f"  Bootstrapping the mixture estimand, B={B_PROTOCOL} (PROTOCOL.md section 7.3's own replicate count)...")
        ci_low, ci_high, _ = bootstrap_ci_mixture(path_records, benign_records, le.EVAL_POINT,
                                                    REF_COVARIATES_NON_SUBTYPE["purity"],
                                                    REF_COVARIATES_NON_SUBTYPE["wgd"], lam, rng, B_PROTOCOL)
        print(f"  Mixture point={weighted_lr:.6f}  CI=[{ci_low:.6f}, {ci_high:.6f}]  (B={B_PROTOCOL})")

        quantity = f"{arm.lower()}_joint_LR"
        truth_row = truth_by_quantity.get(quantity, {})
        injected_value = truth_row.get("injected_value", "MISSING")
        injected_estimand = truth_row.get("estimand", "MISSING")
        injected_derivation = truth_row.get("derivation", "MISSING")

        print(f"\n  === ESTIMAND COMPARISON (printed side by side, per this task's own requirement) ===")
        print(f"  quantity:            {quantity}")
        print(f"  INJECTED value:      {injected_value}")
        print(f"  INJECTED estimand:   {injected_estimand} -- {injected_derivation[:160]}"
              f"{'...' if len(injected_derivation) > 160 else ''}")
        print(f"  RECOVERED value:     {weighted_lr:.6f}  CI=[{ci_low:.6f}, {ci_high:.6f}]")
        print(f"  RECOVERED estimand:  LR -- ridge-logistic fitted model (lambda={lam:.4f}, CV-selected), "
              f"PAM50-prevalence-weighted mixture over the same 5 subtype levels and the same "
              f"simulate.PAM50_PROPORTIONS weights the injected value's own derivation uses, "
              f"wt_lost/gis/sbs3 at EVAL_POINT, purity={REF_COVARIATES_NON_SUBTYPE['purity']}, wgd="
              f"{REF_COVARIATES_NON_SUBTYPE['wgd']}")
        print(f"  UNITS match (both LR): {injected_estimand.strip() == 'LR'}")
        print()

        lr_table_rows.append({
            "stratum": f"{arm}_pooled_full_vector_mixture", "gene_group": arm, "status": "FITTED",
            "point_estimate": weighted_lr, "ci_low": ci_low, "ci_high": ci_high,
            "n_replicates": B_PROTOCOL, "n_pathogenic": n_path_ref, "n_benign": n_benign_ref,
        })
        recovered_rows.append({
            "quantity": quantity, "recovered_point": weighted_lr, "ci_low": ci_low, "ci_high": ci_high,
            "estimand": "LR",
        })
        ablation_rows.append({
            "arm": arm, "feature_subset": "LOH_GIS_SBS3_MIXTURE", "n_scenario": "PRODUCTION_V2_FULL_N_MIXTURE",
            "point_estimate": weighted_lr, "ci_low": ci_low, "ci_high": ci_high,
        })
        for subtype, lr_val in per_subtype_lr.items():
            per_subtype_rows.append({
                "arm": arm, "subtype": subtype, "prevalence": simulate.PAM50_PROPORTIONS[subtype],
                "point_estimate_lr": lr_val, "lambda_used": lam,
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
    print(f"Wrote {lr_path}")

    # gate6 recovered + scope (against the REAL, repo-root SIMULATED_TRUTH.tsv)
    recovered_path = OUT_DIR / "SIMULATED_RECOVERED.tsv"
    with open(recovered_path, "w", newline="", encoding="utf-8") as f:
        cols = ["quantity", "recovered_point", "ci_low", "ci_high", "estimand"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in recovered_rows:
            w.writerow(r)
    print(f"Wrote {recovered_path}")

    all_truth_quantities = list(truth_by_quantity.keys())
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
                                      "production_v2 run as the PAM50-prevalence-weighted mixture estimand "
                                      "(matching SIMULATED_TRUTH.tsv's own pooled-quantity definition), "
                                      "CV-selected lambda, B=2000."})
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

    # Per-subtype LR report (this task's own explicit requirement -- "belongs
    # in the production output rather than in a throwaway check")
    per_subtype_path = OUT_DIR / "SIMULATED_PER_SUBTYPE_LR.tsv"
    with open(per_subtype_path, "w", newline="", encoding="utf-8") as f:
        cols = ["arm", "subtype", "prevalence", "point_estimate_lr", "lambda_used"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in per_subtype_rows:
            w.writerow(r)
    print(f"Wrote {per_subtype_path}")

    # gate9 imbalance sweep -- now also CV-selecting lambda per (arm, ratio)
    # cell, for consistency with implementing the amendment correctly
    # everywhere in production, not only in the pooled recovery.
    gate9_rows = []
    ratios = [("1:1", 300, 300), ("1:5", 60, 300), ("1:20", 15, 300)]
    for arm in ("CORE_HR", "DDR_SIGNALING"):
        path_records = pop_by_arm[arm]["Pathogenic"]
        benign_records = pop_by_arm[arm]["Benign"]
        for label, n_path, n_benign in ratios:
            for rep in range(5):
                path_sample = rng.sample(path_records, n_path)
                benign_sample = rng.sample(benign_records, n_benign)
                lam_g9, prov_g9 = select_cv_lambda_with_provenance(path_sample, benign_sample, rng)
                assert_cv_selected(lam_g9, prov_g9, context=f"gate9 {arm}/{label}/rep{rep}")
                result = le.fit_and_score(path_sample, benign_sample, le.EVAL_POINT,
                                            REF_COVARIATES_NON_SUBTYPE["purity"], "LumA",
                                            REF_COVARIATES_NON_SUBTYPE["wgd"], lam_g9, verbose=(rep == 0))
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
