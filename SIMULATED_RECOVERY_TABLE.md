SIMULATED DATA — NOT A SCIENTIFIC RESULT

# Stage 2 recovery table

SIMULATED: recovered quantities vs their pre-specified injected targets, and the declared scope of every quantity in SIMULATED_TRUTH.tsv. Status values are SIMULATED_PASS / SIMULATED_FAIL / BLOCKED only, per Standing Rule 1.

| quantity | injected | recovered | ci_low | ci_high | estimand (truth/recovered) | relative_bias | status | scope | reason |
|---|---|---|---|---|---|---|---|---|---|
| core_hr_wt_lost_direction_LR | 4.480411981797967 | 4.023547880690738 | 3.6425265229205928 | 4.481621862892165 | LR/LR | 0.101969 | SIMULATED_PASS | IN_SCOPE |  |
| core_hr_gis_score_LR | 3.6622471084686548 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_sbs3_exposure_LR | 5.644994542233774 | 435.24222 | 61.315827 | 14426.858662 | LR/LR | 76.102328 | SIMULATED_FAIL | IN_SCOPE | CI [61.315827, 14426.858662] does not contain injected value 5.644994542233774 — FAILED per Standing Rule 2; relative bias 76.1023 exceeds tolerance 0.25 |
| core_hr_joint_LR | 7.243192150573085 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| core_hr_product_of_marginals_LR | 92.6251919795419 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | same reason as core_hr_joint_LR -- requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| core_hr_joint_vs_marginal_inflation_ratio | 0.07819894345992705 |  |  |  | LR_RATIO/ |  | BLOCKED | NOT_IN_SCOPE | downstream of core_hr_joint_LR and core_hr_product_of_marginals_LR, both out of scope |
| ddr_signaling_wt_lost_direction_LR | 2.137348544853484 | 2.0801479654747226 | 1.8868441528620634 | 2.294461213784566 | LR/LR | 0.026762 | SIMULATED_PASS | IN_SCOPE |  |
| ddr_signaling_gis_score_LR | 2.7235909709691692 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_sbs3_exposure_LR | 3.9157230519927206 | 112.01845 | 11.588999 | 7897.461071 | LR/LR | 27.607347 | SIMULATED_FAIL | IN_SCOPE | CI [11.588999, 7897.461071] does not contain injected value 3.9157230519927206 — FAILED per Standing Rule 2; relative bias 27.6073 exceeds tolerance 0.25 |
| ddr_signaling_joint_LR | 6.204176316151221 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | a joint estimator over LOH+GIS+SBS3 evidence; this caller produces only a single-feature (LOH-direction) marginal recovery, not a joint density estimate |
| ddr_signaling_product_of_marginals_LR | 22.794454498384997 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | same reason as ddr_signaling_joint_LR -- requires GIS/SBS3 features this caller does not compute, in addition to a product-of-marginals estimator this caller does not implement |
| ddr_signaling_joint_vs_marginal_inflation_ratio | 0.2721791967687049 |  |  |  | LR_RATIO/ |  | BLOCKED | NOT_IN_SCOPE | downstream of ddr_signaling_joint_LR and ddr_signaling_product_of_marginals_LR, both out of scope |
| null_arm_full_vector_joint_LR | 1.0 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | NULL_ARM has no marginal-only (LOH-direction-alone) truth quantity to recover against -- only full-feature-vector joint/product/ratio quantities, which require GIS/SBS3 features this caller does not compute |
| null_arm_full_vector_product_of_marginals_LR | 1.0 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | same reason as null_arm_full_vector_joint_LR |
| null_arm_full_vector_inflation_ratio | 1.0 |  |  |  | LR_RATIO/ |  | BLOCKED | NOT_IN_SCOPE | downstream of the two null_arm quantities above, both out of scope |
| null_sequencing_depth_bucket_LR | 1.0 |  |  |  | LR/ |  | BLOCKED | NOT_IN_SCOPE | an engineered-null depth-bucket feature unrelated to LOH direction; not this caller's estimand |
