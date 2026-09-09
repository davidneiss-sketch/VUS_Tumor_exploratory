SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_loh_validation.md — direction-aware LOH caller validation

SIMULATED: this report validates `loh_caller.py` against `SIMULATED_TRUTH.tsv` and the SIMULATED tumor/normal data under `SIMULATED_data/`, produced by `simulate.py` (the remediated, v2 simulator). No real patient, tumor, or sequencing data appears anywhere below. No ACMG evidence strength is assigned to anything in this report. This report supersedes the version DIAGNOSIS.md analyzed — see DIAGNOSIS.md for the bias mechanism this revision fixes (BAF corroboration added to `call_locus()`).

**Overall session status: `SIMULATED_FAIL`** (gate6 exit=1, gate7 exit=0).
BAF data was available for 11088/11088 loci (0 fell back to the pre-fix 3-hypothesis-only competition).

## 1. Method (updated per DIAGNOSIS.md's fix)

`E[VAF|X] = (rho*X + (1-rho)*1) / (rho*CN_t + (1-rho)*2)` (PROTOCOL.md §5.2). For every variant call with tumor depth >= 20, three canonical hypotheses (`WT_LOST_DIRECTION`, `VARIANT_LOST_DIRECTION`, `RETENTION_DIRECTION`) are scored by exact binomial log-likelihood of the at-risk variant's own reads **plus a Gaussian log-likelihood of the segment's mean mirrored BAF** (new — DIAGNOSIS.md's fix) under each hypothesis's expected mirrored BAF (`0.5` for `RETENTION_DIRECTION` always; `(1-rho)/(rho*CN_t+2(1-rho))` for either loss direction — proven identical between the two loss directions, so this term cannot bias direction calls, only the retention/any-LOH boundary). A uniform prior over the 3 combines these into a posterior (softmax); the call is the argmax hypothesis and the posterior mass is the confidence. Below `CONFIDENCE_THRESHOLD = 0.80`, the call is `AMBIGUOUS`. Depth < 20 loci are `NOT_EVALUABLE` (unchanged, PROTOCOL.md §5.2's own floor).

A `WT_LOST_DIRECTION` win is further split by copy-number mechanism: `CN_NEUTRAL_LOH_WT_LOSS` (total CN equals baseline ploidy) vs bare `WT_LOSS` (a genuine hemizygous deletion, `cn_total=1`, now actually present in the remediated simulator's data — see §3). `VARIANT_LOSS` is never split this way and remains its own, single, distinct output class.

## 2. Confusion matrix (true direction-aware category x predicted category)

| true \ predicted | RETENTION | WT_LOSS | CN_NEUTRAL_LOH_WT_LOSS | VARIANT_LOSS | AMBIGUOUS | NOT_EVALUABLE |
|---|---|---|---|---|---|---|
| RETENTION | 3361 | 0 | 110 | 116 | 199 | 0 |
| WT_LOSS | 0 | 2492 | 0 | 37 | 439 | 0 |
| CN_NEUTRAL_LOH_WT_LOSS | 0 | 0 | 1491 | 11 | 66 | 0 |
| VARIANT_LOSS | 0 | 18 | 5 | 2195 | 260 | 0 |
| AMBIGUOUS | 0 | 51 | 0 | 56 | 37 | 0 |
| NOT_EVALUABLE | 0 | 0 | 0 | 0 | 0 | 144 |

(11088 total variant calls attempted.)

## 3. WT_LOSS accuracy (the primary target — previously unmeasured)

**WT_LOSS sensitivity (excluding AMBIGUOUS/NOT_EVALUABLE): 0.98537 (2492/2529, 439 excluded, n=2968).** **WT_LOSS precision: 0.973057 (2492/2561, n=2561).** This is the first report in this project to measure WT_LOSS accuracy at all — the pre-remediation simulator never generated a true deletion-type WT_LOSS locus (DEFECT 1 of the simulator revision), so this quantity was previously UNCHECKED, not merely untested-and-presumed-fine.

## 3.5. WT_LOSS accuracy and inversion rate BY PAM50 SUBTYPE (P07-RERUN2)

**Read first, per this task's own framing:** P06R4 wired `pam50_subtype` into the latent HR-deficiency variable AND into GIS directly, giving Basal an elevated baseline instability independent of true class -- the confounder this stratification exists to detect. This caller never reads `pam50_subtype` when calling an individual locus (`call_locus()` sees only VAF/BAF/CN evidence) -- it is completely subtype-blind by construction.

| subtype | WT_LOSS sensitivity | n (sens.) | WT_LOSS precision | n (prec.) | inversion: WT-dir called VARIANT_LOSS | inversion: VARIANT_LOSS called WT-dir |
|---|---|---|---|---|---|---|
| LumA | 0.985849 | 1242 | 0.972998 | 1074 | 0.008971 (17/1895) | 0.006768 (8/1182) |
| LumB | 0.989865 | 695 | 0.970199 | 604 | 0.008451 (9/1065) | 0.01209 (7/579) |
| HER2E | 0.976589 | 351 | 0.976589 | 299 | 0.017682 (9/509) | 0.007519 (2/266) |
| Basal | 0.983577 | 641 | 0.976449 | 552 | 0.013026 (13/998) | 0.014599 (6/411) |
| Normal-like | 1.0 | 39 | 0.9375 | 32 | 0.0 (0/69) | 0.0 (0/40) |

**Finding: WT_LOSS accuracy does NOT degrade in Basal.** Basal sensitivity (0.983577, n=641) is indistinguishable from every other subtype and from the pooled figure (0.98537, n=2968) -- all subtypes fall in the same 0.977-1.0 sensitivity band (Normal-like's small n aside). Per this task's own framing: **since accuracy holds uniformly across subtypes for a subtype-blind caller, the confounder P06R4 introduced is not reaching the LOH/WT_LOSS-direction feature this caller consumes.** It must be reaching GIS instead (a direct, disclosed channel per `SUBTYPE_MODEL.md`) -- worth knowing before any future task builds a joint model over both LOH and GIS evidence: the confounder is real and present in this study, but this specific feature does not carry it. Normal-like's own recovered-LR bias (unlike its accuracy) IS visibly larger than the other subtypes' (see gate6 in section 8) -- but that is an n=63/55 small-sample-variance story on the LR point estimate, not an accuracy degradation; the per-call sensitivity/precision numbers above are stable at n=30-32 in Normal-like too.

## 4. Inversion rate, both directions, with denominators

**True WT-lost-direction called VARIANT_LOSS (inversion): 0.010582 (48/4536).** **True VARIANT_LOSS called a WT-lost-direction category (inversion): 0.009282 (23/2478).** The pre-remediation report's "zero inversion rate" finding was vacuous: with no true deletion-type WT_LOSS in that run's data, an inversion involving it could never even be evaluated. Both denominators here are real, nonzero counts of true instances (see §3 and the confusion matrix, §2).

## 5. Denominator-explicit accuracy, including/excluding AMBIGUOUS and NOT_EVALUABLE

| metric | numerator | denominator | excluded_count | n (cell) | rate |
|---|---|---|---|---|---|
| overall_accuracy_including_ambiguous_and_not_evaluable | 9720 | 11088 | 0 | 11088 | 0.876623 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable | 9539 | 9943 | 1145 | 11088 | 0.959368 |
| wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable | 2492 | 2529 | 439 | 2968 | 0.98537 |
| wt_loss_precision | 2492 | 2561 | 0 | 2561 | 0.973057 |
| inversion_rate_wt_lost_direction_called_variant_lost | 48 | 4536 | 0 | 4536 | 0.010582 |
| inversion_rate_variant_lost_called_wt_lost_direction | 23 | 2478 | 0 | 2478 | 0.009282 |
| overall_accuracy_including_ambiguous_and_not_evaluable_subtype_luma | 4299 | 4878 | 0 | 4878 | 0.881304 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable_subtype_luma | 4218 | 4396 | 482 | 4878 | 0.959509 |
| wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable_subtype_luma | 1045 | 1060 | 182 | 1242 | 0.985849 |
| wt_loss_precision_subtype_luma | 1045 | 1074 | 0 | 1074 | 0.972998 |
| inversion_rate_wt_lost_direction_called_variant_lost_subtype_luma | 17 | 1895 | 0 | 1895 | 0.008971 |
| inversion_rate_variant_lost_called_wt_lost_direction_subtype_luma | 8 | 1182 | 0 | 1182 | 0.006768 |
| overall_accuracy_including_ambiguous_and_not_evaluable_subtype_lumb | 2340 | 2675 | 0 | 2675 | 0.874766 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable_subtype_lumb | 2288 | 2380 | 295 | 2675 | 0.961345 |
| wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable_subtype_lumb | 586 | 592 | 103 | 695 | 0.989865 |
| wt_loss_precision_subtype_lumb | 586 | 604 | 0 | 604 | 0.970199 |
| inversion_rate_wt_lost_direction_called_variant_lost_subtype_lumb | 9 | 1065 | 0 | 1065 | 0.008451 |
| inversion_rate_variant_lost_called_wt_lost_direction_subtype_lumb | 7 | 579 | 0 | 579 | 0.01209 |
| overall_accuracy_including_ambiguous_and_not_evaluable_subtype_her2e | 1080 | 1257 | 0 | 1257 | 0.859189 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable_subtype_her2e | 1061 | 1115 | 142 | 1257 | 0.95157 |
| wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable_subtype_her2e | 292 | 299 | 52 | 351 | 0.976589 |
| wt_loss_precision_subtype_her2e | 292 | 299 | 0 | 299 | 0.976589 |
| inversion_rate_wt_lost_direction_called_variant_lost_subtype_her2e | 9 | 509 | 0 | 509 | 0.017682 |
| inversion_rate_variant_lost_called_wt_lost_direction_subtype_her2e | 2 | 266 | 0 | 266 | 0.007519 |
| overall_accuracy_including_ambiguous_and_not_evaluable_subtype_basal | 1851 | 2105 | 0 | 2105 | 0.879335 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable_subtype_basal | 1826 | 1900 | 205 | 2105 | 0.961053 |
| wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable_subtype_basal | 539 | 548 | 93 | 641 | 0.983577 |
| wt_loss_precision_subtype_basal | 539 | 552 | 0 | 552 | 0.976449 |
| inversion_rate_wt_lost_direction_called_variant_lost_subtype_basal | 13 | 998 | 0 | 998 | 0.013026 |
| inversion_rate_variant_lost_called_wt_lost_direction_subtype_basal | 6 | 411 | 0 | 411 | 0.014599 |
| overall_accuracy_including_ambiguous_and_not_evaluable_subtype_normal_like | 150 | 173 | 0 | 173 | 0.867052 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable_subtype_normal_like | 146 | 152 | 21 | 173 | 0.960526 |
| wt_loss_sensitivity_excluding_ambiguous_and_not_evaluable_subtype_normal_like | 30 | 30 | 9 | 39 | 1.0 |
| wt_loss_precision_subtype_normal_like | 30 | 32 | 0 | 32 | 0.9375 |
| inversion_rate_wt_lost_direction_called_variant_lost_subtype_normal_like | 0 | 69 | 0 | 69 | 0.0 |
| inversion_rate_variant_lost_called_wt_lost_direction_subtype_normal_like | 0 | 40 | 0 | 40 | 0.0 |
| confidence_filter_ambiguous_rate | 1001 | 10944 | 0 | 10944 | 0.091466 |
| not_evaluable_rate_depth_lt_20 | 144 | 11088 | 0 | 11088 | 0.012987 |
| accuracy_by_purity_LOW_0.10_0.35 | 2380 | 2686 | 1009 | 3695 | 0.886076 |
| accuracy_by_purity_MID_0.35_0.65 | 3559 | 3609 | 88 | 3697 | 0.986146 |
| accuracy_by_purity_HIGH_0.65_0.95 | 3600 | 3648 | 48 | 3696 | 0.986842 |
| accuracy_by_depth_BORDERLINE_20_30 | 662 | 744 | 152 | 896 | 0.889785 |
| accuracy_by_depth_MODERATE_30_60 | 3962 | 4136 | 485 | 4621 | 0.95793 |
| accuracy_by_depth_HIGH_60_plus | 4915 | 5063 | 364 | 5427 | 0.970768 |
| accuracy_by_total_copy_number_CN1 | 3871 | 4033 | 710 | 4743 | 0.959831 |
| accuracy_by_total_copy_number_CN2 | 3859 | 4082 | 361 | 4443 | 0.94537 |
| accuracy_by_total_copy_number_CN4 | 1809 | 1828 | 74 | 1902 | 0.989606 |
| accuracy_by_purity_LOW_0.10_0.35_x_depth_BORDERLINE_20_30 | 131 | 155 | 136 | 291 | 0.845161 |
| accuracy_by_purity_LOW_0.10_0.35_x_depth_MODERATE_30_60 | 969 | 1105 | 463 | 1568 | 0.876923 |
| accuracy_by_purity_LOW_0.10_0.35_x_depth_HIGH_60_plus | 1280 | 1426 | 362 | 1788 | 0.897616 |
| accuracy_by_purity_MID_0.35_0.65_x_depth_BORDERLINE_20_30 | 266 | 289 | 16 | 305 | 0.920415 |
| accuracy_by_purity_MID_0.35_0.65_x_depth_MODERATE_30_60 | 1483 | 1508 | 22 | 1530 | 0.983422 |
| accuracy_by_purity_MID_0.35_0.65_x_depth_HIGH_60_plus | 1810 | 1812 | 2 | 1814 | 0.998896 |
| accuracy_by_purity_HIGH_0.65_0.95_x_depth_BORDERLINE_20_30 | 265 | 300 | 0 | 300 | 0.883333 |
| accuracy_by_purity_HIGH_0.65_0.95_x_depth_MODERATE_30_60 | 1510 | 1523 | 0 | 1523 | 0.991464 |
| accuracy_by_purity_HIGH_0.65_0.95_x_depth_HIGH_60_plus | 1825 | 1825 | 0 | 1825 | 1.0 |
| accuracy_by_wgd_status_NON_WGD | 6573 | 6909 | 850 | 7759 | 0.951368 |
| accuracy_by_wgd_status_WGD | 2966 | 3034 | 295 | 3329 | 0.977587 |
| accuracy_by_arm_CORE_HR | 3190 | 3312 | 384 | 3696 | 0.963164 |
| accuracy_by_arm_DDR_SIGNALING | 3160 | 3299 | 397 | 3696 | 0.957866 |
| accuracy_by_arm_NULL_ARM | 3189 | 3332 | 364 | 3696 | 0.957083 |

SIMULATED: of 11088 total calls attempted, `144` were `NOT_EVALUABLE` (depth < 20) and, of the `10944` depth-evaluable loci remaining, `1001` were reclassified `AMBIGUOUS` by the confidence < 0.80 filter (rate = 0.091466). Accuracy **including** those excluded calls = 0.876623 (9720/11088). Accuracy **excluding** them = 0.959368 (9539/9943, 1145 excluded, n=11088).

## 6. The unreliable operating region: purity x depth (investigated, not asserted)

Among strata with n >= 20 (adequately powered — low-n cells are excluded from this specific claim, per §5's flag), the worst-performing purity x depth grid cell is **`accuracy_by_purity_LOW_0.10_0.35_x_depth_BORDERLINE_20_30`** at rate **0.845161** (131/155, n=291).

**Root cause (DIAGNOSIS.md, proven algebraically):** `expected_vaf` is affine in X, so `E[VAF|RETENTION_DIRECTION] = 0.5` exactly for every purity, while `E[VAF|WT_LOST_DIRECTION]` approaches 0.5 as purity -> 0 (`gap(rho) ~ rho*CN_t/4` for small rho) — the separation between retention and either loss direction vanishes proportionally to purity. This is why confidence collapses, and AMBIGUOUS/inversion risk rises, specifically at **low purity** — not at low depth, and not uniformly. BAF corroboration (added this revision) mitigates this (BAF is a lower-variance, independently-measured corroborating signal for the same retention-vs-any-LOH boundary), but does not eliminate the underlying purity-driven signal collapse, which is a property of the VAF model itself, not of any one estimator.

## 7. VARIANT_LOSS is a distinct output class

SIMULATED: `VARIANT_LOSS` appears as its own row and column in the confusion matrix above, distinct from `WT_LOSS`/`CN_NEUTRAL_LOH_WT_LOSS` — 2478 true instances, 2415 predicted instances this run.

## 8. gate6 — recovery against SIMULATED_TRUTH.tsv (91 quantities), scope declared for every one

gate6_recovery.py exit code: **1** (at least one in-scope quantity SIMULATED_FAIL — reported as FAILED). All 91 `SIMULATED_TRUTH.tsv` quantities are declared in `SIMULATED_recovery_scope.tsv` (0 undeclared this run).

**Note on this run's own gate6 invocation (above): it does not pass `--bias-prediction`.** The directional shrinkage-bias check (PROTOCOL_DEVIATIONS.md Entry 3) is therefore SKIPPED here, and this run's own PASS/FAIL reflects relative-bias tolerance alone. A SEPARATE, external invocation of gate6 WITH a stated, computed bias prediction (per this task's own Step 3 requirement) is logged in `DEPLOYMENT_LOG.md` and `PROPOSED_DEVIATIONS.md` — see those for the fuller picture, including the directional-check results.

In-scope quantities (12 of 91 — this caller's own deliverable, scored for real):

| quantity | injected | recovered | ci_low | ci_high | status | reason |
|---|---|---|---|---|---|---|
| core_hr_wt_lost_direction_LR | 4.194289038463922 | 3.682788051209104 | 3.349254813432772 | 4.0967671122771625 | SIMULATED_PASS |  |
| core_hr_luma_wt_lost_direction_LR | 4.480411981797967 | 3.636351495726496 | 3.1374385869137718 | 4.2382500345734195 | SIMULATED_PASS |  |
| core_hr_lumb_wt_lost_direction_LR | 4.480411981797967 | 4.126982944812691 | 3.367223707475515 | 5.243833294797868 | SIMULATED_PASS |  |
| core_hr_her2e_wt_lost_direction_LR | 4.480411981797967 | 4.1722985752111965 | 3.174115590169767 | 5.760370697263901 | SIMULATED_PASS |  |
| core_hr_basal_wt_lost_direction_LR | 3.321335081019411 | 3.095501183898974 | 2.564224520248104 | 3.7992575420972985 | SIMULATED_PASS |  |
| core_hr_normal_like_wt_lost_direction_LR | 4.480411981797967 | 5.72972972972973 | 2.774774774774775 | 38.5945945945946 | SIMULATED_FAIL | relative bias 0.2788 exceeds tolerance 0.25 |
| ddr_signaling_wt_lost_direction_LR | 2.0841779761089585 | 2.040650406504065 | 1.8621577444722093 | 2.2448196006868937 | SIMULATED_PASS |  |
| ddr_signaling_luma_wt_lost_direction_LR | 2.137348544853484 | 1.9693396226415094 | 1.699942555088856 | 2.302851392160343 | SIMULATED_PASS |  |
| ddr_signaling_lumb_wt_lost_direction_LR | 2.137348544853484 | 2.367200281147372 | 1.9504303170630173 | 2.9498769376194116 | SIMULATED_PASS |  |
| ddr_signaling_her2e_wt_lost_direction_LR | 2.137348544853484 | 2.007919400187441 | 1.541825821237586 | 2.7224288075560796 | SIMULATED_PASS |  |
| ddr_signaling_basal_wt_lost_direction_LR | 1.903747064591609 | 1.849190189111138 | 1.5500226662482128 | 2.2677410708511263 | SIMULATED_PASS |  |
| ddr_signaling_normal_like_wt_lost_direction_LR | 2.137348544853484 | 2.0495867768595044 | 1.018181818181818 | 6.545454545454546 | SIMULATED_PASS |  |

Declared out-of-scope quantities (79 of 91):

| quantity | status | scope_status | reason |
|---|---|---|---|
| core_hr_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| core_hr_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| core_hr_luma_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_luma_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| core_hr_luma_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_luma_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_luma_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| core_hr_lumb_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_lumb_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| core_hr_lumb_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_lumb_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_lumb_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| core_hr_her2e_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_her2e_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| core_hr_her2e_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_her2e_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_her2e_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| core_hr_basal_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_basal_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| core_hr_basal_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_basal_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_basal_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| core_hr_normal_like_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_normal_like_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| core_hr_normal_like_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_normal_like_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_normal_like_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| ddr_signaling_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| ddr_signaling_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| ddr_signaling_luma_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_luma_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| ddr_signaling_luma_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_luma_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_luma_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| ddr_signaling_lumb_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_lumb_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| ddr_signaling_lumb_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_lumb_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_lumb_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| ddr_signaling_her2e_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_her2e_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| ddr_signaling_her2e_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_her2e_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_her2e_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| ddr_signaling_basal_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_basal_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| ddr_signaling_basal_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_basal_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_basal_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| ddr_signaling_normal_like_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_normal_like_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| ddr_signaling_normal_like_joint_LR | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_normal_like_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_normal_like_joint_vs_marginal_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of a joint_LR/product_of_marginals_LR pair, both out of scope for this caller |
| null_arm_full_vector_joint_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_full_vector_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_full_vector_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of the NULL_ARM full_vector_joint_LR/product_of_marginals_LR pair, both out of scope |
| null_arm_luma_full_vector_joint_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_luma_full_vector_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_luma_full_vector_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of the NULL_ARM full_vector_joint_LR/product_of_marginals_LR pair, both out of scope |
| null_arm_lumb_full_vector_joint_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_lumb_full_vector_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_lumb_full_vector_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of the NULL_ARM full_vector_joint_LR/product_of_marginals_LR pair, both out of scope |
| null_arm_her2e_full_vector_joint_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_her2e_full_vector_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_her2e_full_vector_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of the NULL_ARM full_vector_joint_LR/product_of_marginals_LR pair, both out of scope |
| null_arm_basal_full_vector_joint_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_basal_full_vector_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_basal_full_vector_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of the NULL_ARM full_vector_joint_LR/product_of_marginals_LR pair, both out of scope |
| null_arm_normal_like_full_vector_joint_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_normal_like_full_vector_product_of_marginals_LR | BLOCKED | NOT_IN_SCOPE | NULL_ARM full-feature-vector quantity requiring GIS/SBS3 features this LOH caller does not compute |
| null_arm_normal_like_full_vector_inflation_ratio | BLOCKED | NOT_IN_SCOPE | downstream of the NULL_ARM full_vector_joint_LR/product_of_marginals_LR pair, both out of scope |
| null_sequencing_depth_bucket_LR | BLOCKED | NOT_IN_SCOPE | an engineered-null depth-bucket feature unrelated to LOH direction; not this caller's estimand |

**Per this task's acceptance wording ("gate6 PASS on every P07 quantity, or FAILED with the cause identified and the remaining gap quantified"): this session reports gate6 as FAILED.** See §9 for the per-quantity cause and gap.

## 9. Post-fix relative bias — cause and remaining gap, quantified

- `core_hr_wt_lost_direction_LR`: injected=4.194289038463922, recovered=3.682788051209104, relative_bias=0.121952, status=SIMULATED_PASS
- `core_hr_luma_wt_lost_direction_LR`: injected=4.480411981797967, recovered=3.636351495726496, relative_bias=0.188389, status=SIMULATED_PASS
- `core_hr_lumb_wt_lost_direction_LR`: injected=4.480411981797967, recovered=4.126982944812691, relative_bias=0.078883, status=SIMULATED_PASS
- `core_hr_her2e_wt_lost_direction_LR`: injected=4.480411981797967, recovered=4.1722985752111965, relative_bias=0.068769, status=SIMULATED_PASS
- `core_hr_basal_wt_lost_direction_LR`: injected=3.321335081019411, recovered=3.095501183898974, relative_bias=0.067995, status=SIMULATED_PASS
- `core_hr_normal_like_wt_lost_direction_LR`: injected=4.480411981797967, recovered=5.72972972972973, relative_bias=0.27884, status=SIMULATED_FAIL — relative bias 0.2788 exceeds tolerance 0.25
- `ddr_signaling_wt_lost_direction_LR`: injected=2.0841779761089585, recovered=2.040650406504065, relative_bias=0.020885, status=SIMULATED_PASS
- `ddr_signaling_luma_wt_lost_direction_LR`: injected=2.137348544853484, recovered=1.9693396226415094, relative_bias=0.078606, status=SIMULATED_PASS
- `ddr_signaling_lumb_wt_lost_direction_LR`: injected=2.137348544853484, recovered=2.367200281147372, relative_bias=0.107541, status=SIMULATED_PASS
- `ddr_signaling_her2e_wt_lost_direction_LR`: injected=2.137348544853484, recovered=2.007919400187441, relative_bias=0.060556, status=SIMULATED_PASS
- `ddr_signaling_basal_wt_lost_direction_LR`: injected=1.903747064591609, recovered=1.849190189111138, relative_bias=0.028658, status=SIMULATED_PASS
- `ddr_signaling_normal_like_wt_lost_direction_LR`: injected=2.137348544853484, recovered=2.0495867768595044, relative_bias=0.041061, status=SIMULATED_PASS

Per DIAGNOSIS.md: the fix targets the purity-dependent retention-vs-LOH confidence collapse (the confirmed mechanism), not the small-n ground-truth-realization variance (a separate, amplifying factor already addressed by the simulator's own n increase, independent of this caller). Any relative bias remaining above should be interpreted against that n increase (11088 total samples, ~1848 per arm-class cell, vs. the 60-sample run DIAGNOSIS.md diagnosed) rather than re-diagnosed as a new, different mechanism.

## 10. gate7 — denominators

gate7_denominators.py exit code: **0** (PASS).

```
=== gate7_denominators ===
[PASS] rates table present — SIMULATED_rates_table.tsv, 61 metric row(s)
[PASS] every row has a positive denominator — all 61 row(s) have a positive denominator
[PASS] every row has an explicit (non-blank) excluded_count — all 61 row(s) carry an explicit excluded_count
[PASS] numerator never exceeds denominator — all 61 row(s) OK
[PASS] reported rate (if present) matches numerator/denominator — all reported rates internally consistent

gate7_denominators OVERALL: PASS
```

## 11. Files

| File | Contents |
|---|---|
| `SIMULATED_loh_validation/SIMULATED_loh_calls.tsv` | one row per variant call: predicted category, confidence, posteriors, true category, BAF-used flag, correctness |
| `SIMULATED_loh_validation/SIMULATED_confusion_matrix.tsv` | true x predicted category counts (long format) |
| `SIMULATED_loh_validation/SIMULATED_rates_table.tsv` | every reported rate with numerator/denominator/excluded_count/n_total_cell/low_n_flag (gate7 input) |
| `SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv` | the 12 recovered wt_lost_direction_LR quantities (pooled + 5 subtypes x 2 arms) with bootstrap CIs (gate6 `--recovered` input) |
| `SIMULATED_loh_validation/SIMULATED_LR_TABLE.tsv` | the same 12 (+ any INSUFFICIENT_N) strata in gate4's own schema (stratum/status/n_pathogenic/n_benign/n_replicates) |
| `SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv` | scope declaration for all 91 SIMULATED_TRUTH.tsv quantities (gate6 `--scope` input) |
| `P07_SCOPE.tsv` (repo root) | the same scope declaration, standalone deliverable |
| `SIMULATED_loh_validation/SIMULATED_RECOVERY_TABLE.tsv` / `.md` | gate6's own emitted output (this caller's own directory), covering all 91 SIMULATED_TRUTH.tsv quantities |
| `SIMULATED_loh_validation/SIMULATED_BIAS_PREDICTION.tsv` | this task's Step 3 bias prediction (Jeffreys-correction-only magnitude), supplied to the EXTERNAL gate6 invocation logged in DEPLOYMENT_LOG.md |
| `SIMULATED_loh_validation/SIMULATED_PURITY_FLOOR_BY_SUBTYPE.tsv` | Step 5's re-derived purity operating region, pooled and per PAM50 subtype |
| `DIAGNOSIS.md` | the mechanism analysis the original P07 revision fixed |
| `PROPOSED_DEVIATIONS.md` | proposed (not applied) PROTOCOL.md purity/depth floor deviations, including this task's revised, per-subtype floor (supersedes the original section 1 proposal) |

