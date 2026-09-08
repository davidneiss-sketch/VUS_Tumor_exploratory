SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_loh_validation.md — direction-aware LOH caller validation

SIMULATED: this report validates `loh_caller.py` against `SIMULATED_TRUTH.tsv` and the SIMULATED tumor/normal data under `SIMULATED_data/`, produced by `simulate.py` (the remediated, v2 simulator). No real patient, tumor, or sequencing data appears anywhere below. No ACMG evidence strength is assigned to anything in this report. This report supersedes the version DIAGNOSIS.md analyzed — see DIAGNOSIS.md for the bias mechanism this revision fixes (BAF corroboration added to `call_locus()`).

**Overall session status: `SIMULATED_PASS`** (gate6 exit=0, gate7 exit=0).
BAF data was available for 11088/11088 loci (0 fell back to the pre-fix 3-hypothesis-only competition).

## 1. Method (updated per DIAGNOSIS.md's fix)

`E[VAF|X] = (rho*X + (1-rho)*1) / (rho*CN_t + (1-rho)*2)` (PROTOCOL.md §5.2). For every variant call with tumor depth >= 20, three canonical hypotheses (`WT_LOST_DIRECTION`, `VARIANT_LOST_DIRECTION`, `RETENTION_DIRECTION`) are scored by exact binomial log-likelihood of the at-risk variant's own reads **plus a Gaussian log-likelihood of the segment's mean mirrored BAF** (new — DIAGNOSIS.md's fix) under each hypothesis's expected mirrored BAF (`0.5` for `RETENTION_DIRECTION` always; `(1-rho)/(rho*CN_t+2(1-rho))` for either loss direction — proven identical between the two loss directions, so this term cannot bias direction calls, only the retention/any-LOH boundary). A uniform prior over the 3 combines these into a posterior (softmax); the call is the argmax hypothesis and the posterior mass is the confidence. Below `CONFIDENCE_THRESHOLD = 0.80`, the call is `AMBIGUOUS`. Depth < 20 loci are `NOT_EVALUABLE` (unchanged, PROTOCOL.md §5.2's own floor).

A `WT_LOST_DIRECTION` win is further split by copy-number mechanism: `CN_NEUTRAL_LOH_WT_LOSS` (total CN equals baseline ploidy) vs bare `WT_LOSS` (a genuine hemizygous deletion, `cn_total=1`, now actually present in the remediated simulator's data — see §3). `VARIANT_LOSS` is never split this way and remains its own, single, distinct output class.

## 2. Confusion matrix (true direction-aware category x predicted category)

| true \ predicted | RETENTION | WT_LOSS | CN_NEUTRAL_LOH_WT_LOSS | VARIANT_LOSS | AMBIGUOUS | NOT_EVALUABLE |
|---|---|---|---|---|---|---|
| RETENTION | 3461 | 0 | 111 | 117 | 205 | 0 |
| WT_LOSS | 0 | 2394 | 0 | 36 | 425 | 0 |
| CN_NEUTRAL_LOH_WT_LOSS | 0 | 0 | 1431 | 10 | 63 | 0 |
| VARIANT_LOSS | 0 | 19 | 5 | 2253 | 270 | 0 |
| AMBIGUOUS | 0 | 51 | 0 | 56 | 37 | 0 |
| NOT_EVALUABLE | 0 | 0 | 0 | 0 | 0 | 144 |

(11088 total variant calls attempted.)

## 3. WT_LOSS accuracy (the primary target — previously unmeasured)

**WT_LOSS sensitivity (excluding AMBIGUOUS/NOT_EVALUABLE): 0.985185 (2394/2430, 425 excluded, n=2855).** **WT_LOSS precision: 0.971591 (2394/2464, n=2464).** This is the first report in this project to measure WT_LOSS accuracy at all — the pre-remediation simulator never generated a true deletion-type WT_LOSS locus (DEFECT 1 of the simulator revision), so this quantity was previously UNCHECKED, not merely untested-and-presumed-fine.

## 4. Inversion rate, both directions, with denominators

**True WT-lost-direction called VARIANT_LOSS (inversion): 0.010553 (46/4359).** **True VARIANT_LOSS called a WT-lost-direction category (inversion): 0.009423 (24/2547).** The pre-remediation report's "zero inversion rate" finding was vacuous: with no true deletion-type WT_LOSS in that run's data, an inversion involving it could never even be evaluated. Both denominators here are real, nonzero counts of true instances (see §3 and the confusion matrix, §2).

## 5. Denominator-explicit accuracy, including/excluding AMBIGUOUS and NOT_EVALUABLE

| metric | numerator | denominator | excluded_count | n (cell) | rate |
|---|---|---|---|---|---|
| overall_accuracy_including_ambiguous_and_not_evaluable | 9720 | 11088 | 0 | 11088 | 0.876623 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable | 9539 | 9944 | 1144 | 11088 | 0.959272 |
| wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable | 2394 | 2430 | 425 | 2855 | 0.985185 |
| wt_loss_precision | 2394 | 2464 | 0 | 2464 | 0.971591 |
| inversion_rate_wt_lost_direction_called_variant_lost | 46 | 4359 | 0 | 4359 | 0.010553 |
| inversion_rate_variant_lost_called_wt_lost_direction | 24 | 2547 | 0 | 2547 | 0.009423 |
| confidence_filter_ambiguous_rate | 1000 | 10944 | 0 | 10944 | 0.091374 |
| not_evaluable_rate_depth_lt_20 | 144 | 11088 | 0 | 11088 | 0.012987 |
| accuracy_by_purity_LOW_0.10_0.35 | 2378 | 2685 | 1010 | 3695 | 0.885661 |
| accuracy_by_purity_MID_0.35_0.65 | 3561 | 3611 | 86 | 3697 | 0.986153 |
| accuracy_by_purity_HIGH_0.65_0.95 | 3600 | 3648 | 48 | 3696 | 0.986842 |
| accuracy_by_depth_BORDERLINE_20_30 | 661 | 743 | 153 | 896 | 0.889637 |
| accuracy_by_depth_MODERATE_30_60 | 3965 | 4138 | 483 | 4621 | 0.958192 |
| accuracy_by_depth_HIGH_60_plus | 4913 | 5063 | 364 | 5427 | 0.970373 |
| accuracy_by_total_copy_number_CN1 | 3804 | 3966 | 704 | 4670 | 0.959153 |
| accuracy_by_total_copy_number_CN2 | 3902 | 4126 | 366 | 4492 | 0.94571 |
| accuracy_by_total_copy_number_CN4 | 1833 | 1852 | 74 | 1926 | 0.989741 |
| accuracy_by_purity_LOW_0.10_0.35_x_depth_BORDERLINE_20_30 | 129 | 153 | 138 | 291 | 0.843137 |
| accuracy_by_purity_LOW_0.10_0.35_x_depth_MODERATE_30_60 | 971 | 1106 | 462 | 1568 | 0.877939 |
| accuracy_by_purity_LOW_0.10_0.35_x_depth_HIGH_60_plus | 1278 | 1426 | 362 | 1788 | 0.896213 |
| accuracy_by_purity_MID_0.35_0.65_x_depth_BORDERLINE_20_30 | 267 | 290 | 15 | 305 | 0.92069 |
| accuracy_by_purity_MID_0.35_0.65_x_depth_MODERATE_30_60 | 1484 | 1509 | 21 | 1530 | 0.983433 |
| accuracy_by_purity_MID_0.35_0.65_x_depth_HIGH_60_plus | 1810 | 1812 | 2 | 1814 | 0.998896 |
| accuracy_by_purity_HIGH_0.65_0.95_x_depth_BORDERLINE_20_30 | 265 | 300 | 0 | 300 | 0.883333 |
| accuracy_by_purity_HIGH_0.65_0.95_x_depth_MODERATE_30_60 | 1510 | 1523 | 0 | 1523 | 0.991464 |
| accuracy_by_purity_HIGH_0.65_0.95_x_depth_HIGH_60_plus | 1825 | 1825 | 0 | 1825 | 1.0 |
| accuracy_by_wgd_status_NON_WGD | 6574 | 6911 | 848 | 7759 | 0.951237 |
| accuracy_by_wgd_status_WGD | 2965 | 3033 | 296 | 3329 | 0.97758 |
| accuracy_by_arm_CORE_HR | 3191 | 3314 | 382 | 3696 | 0.962885 |
| accuracy_by_arm_DDR_SIGNALING | 3159 | 3298 | 398 | 3696 | 0.957853 |
| accuracy_by_arm_NULL_ARM | 3189 | 3332 | 364 | 3696 | 0.957083 |

SIMULATED: of 11088 total calls attempted, `144` were `NOT_EVALUABLE` (depth < 20) and, of the `10944` depth-evaluable loci remaining, `1000` were reclassified `AMBIGUOUS` by the confidence < 0.80 filter (rate = 0.091374). Accuracy **including** those excluded calls = 0.876623 (9720/11088). Accuracy **excluding** them = 0.959272 (9539/9944, 1144 excluded, n=11088).

## 6. The unreliable operating region: purity x depth (investigated, not asserted)

Among strata with n >= 20 (adequately powered — low-n cells are excluded from this specific claim, per §5's flag), the worst-performing purity x depth grid cell is **`accuracy_by_purity_LOW_0.10_0.35_x_depth_BORDERLINE_20_30`** at rate **0.843137** (129/153, n=291).

**Root cause (DIAGNOSIS.md, proven algebraically):** `expected_vaf` is affine in X, so `E[VAF|RETENTION_DIRECTION] = 0.5` exactly for every purity, while `E[VAF|WT_LOST_DIRECTION]` approaches 0.5 as purity -> 0 (`gap(rho) ~ rho*CN_t/4` for small rho) — the separation between retention and either loss direction vanishes proportionally to purity. This is why confidence collapses, and AMBIGUOUS/inversion risk rises, specifically at **low purity** — not at low depth, and not uniformly. BAF corroboration (added this revision) mitigates this (BAF is a lower-variance, independently-measured corroborating signal for the same retention-vs-any-LOH boundary), but does not eliminate the underlying purity-driven signal collapse, which is a property of the VAF model itself, not of any one estimator.

## 7. VARIANT_LOSS is a distinct output class

SIMULATED: `VARIANT_LOSS` appears as its own row and column in the confusion matrix above, distinct from `WT_LOSS`/`CN_NEUTRAL_LOH_WT_LOSS` — 2547 true instances, 2472 predicted instances this run.

## 8. gate6 — recovery against SIMULATED_TRUTH.tsv (16 quantities), scope declared for every one

gate6_recovery.py exit code: **0** (all in-scope quantities SIMULATED_PASS). All 16 `SIMULATED_TRUTH.tsv` quantities are declared in `SIMULATED_recovery_scope.tsv` (0 undeclared this run).

In-scope quantities (2 of 16 — this caller's own deliverable, scored for real):

| quantity | injected | recovered | ci_low | ci_high | status | reason |
|---|---|---|---|---|---|---|
| core_hr_wt_lost_direction_LR | 4.480411981797967 | 4.023547880690738 | 3.6425265229205928 | 4.481621862892165 | SIMULATED_PASS |  |
| ddr_signaling_wt_lost_direction_LR | 2.137348544853484 | 2.0801479654747226 | 1.8868441528620634 | 2.294461213784566 | SIMULATED_PASS |  |

Declared out-of-scope quantities (14 of 16):

| quantity | status | scope_status | reason |
|---|---|---|---|
| core_hr_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| core_hr_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | same reason as core_hr_joint_LR -- requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of core_hr_joint_LR and core_hr_product_of_marginals_LR, both out of scope |
| ddr_signaling_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| ddr_signaling_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | same reason as ddr_signaling_joint_LR -- requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of ddr_signaling_joint_LR and ddr_signaling_product_of_marginals_LR, both out of scope |
| null_arm_full_vector_joint_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM has no marginal-only (LOH-direction-alone) truth quantity to recover against -- only full-feature-vector joint/product/ratio quantities, which require GIS/SBS3 features this caller does not compute |
| null_arm_full_vector_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | same reason as null_arm_full_vector_joint_LR |
| null_arm_full_vector_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of the two null_arm quantities above, both out of scope |
| null_sequencing_depth_bucket_LR | BLOCKED | NOT_IN_SCOPE | an engineered-null depth-bucket feature unrelated to LOH direction; not this caller's estimand |

**Per this task's acceptance wording ("gate6 PASS on every P07 quantity, or FAILED with the cause identified and the remaining gap quantified"): this session reports gate6 as PASSED.** See §9 for the per-quantity cause and gap.

## 9. Post-fix relative bias — cause and remaining gap, quantified

- `core_hr_wt_lost_direction_LR`: injected=4.480411981797967, recovered=4.023547880690738, relative_bias=0.101969, status=SIMULATED_PASS
- `ddr_signaling_wt_lost_direction_LR`: injected=2.137348544853484, recovered=2.0801479654747226, relative_bias=0.026762, status=SIMULATED_PASS

Per DIAGNOSIS.md: the fix targets the purity-dependent retention-vs-LOH confidence collapse (the confirmed mechanism), not the small-n ground-truth-realization variance (a separate, amplifying factor already addressed by the simulator's own n increase, independent of this caller). Any relative bias remaining above should be interpreted against that n increase (11088 total samples, ~1848 per arm-class cell, vs. the 60-sample run DIAGNOSIS.md diagnosed) rather than re-diagnosed as a new, different mechanism.

## 10. gate7 — denominators

gate7_denominators.py exit code: **0** (PASS).

```
=== gate7_denominators ===
[PASS] rates table present — SIMULATED_rates_table.tsv, 31 metric row(s)
[PASS] every row has a positive denominator — all 31 row(s) have a positive denominator
[PASS] every row has an explicit (non-blank) excluded_count — all 31 row(s) carry an explicit excluded_count
[PASS] numerator never exceeds denominator — all 31 row(s) OK
[PASS] reported rate (if present) matches numerator/denominator — all reported rates internally consistent

gate7_denominators OVERALL: PASS
```

## 11. Files

| File | Contents |
|---|---|
| `SIMULATED_loh_validation/SIMULATED_loh_calls.tsv` | one row per variant call: predicted category, confidence, posteriors, true category, BAF-used flag, correctness |
| `SIMULATED_loh_validation/SIMULATED_confusion_matrix.tsv` | true x predicted category counts (long format) |
| `SIMULATED_loh_validation/SIMULATED_rates_table.tsv` | every reported rate with numerator/denominator/excluded_count/n_total_cell/low_n_flag (gate7 input) |
| `SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv` | the 2 recovered LR quantities with bootstrap CIs (gate6 `--recovered` input) |
| `SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv` | scope declaration for all 16 SIMULATED_TRUTH.tsv quantities (gate6 `--scope` input) |
| `SIMULATED_RECOVERY_TABLE.tsv` / `.md` | gate6's own emitted output (repo root), covering all 16 SIMULATED_TRUTH.tsv quantities |
| `DIAGNOSIS.md` | the mechanism analysis this revision fixes |
| `PROPOSED_DEVIATIONS.md` | proposed (not applied) PROTOCOL.md purity/depth floor deviations, per this task's Step 4 |

