SIMULATED DATA — NOT A SCIENTIFIC RESULT

# CONFIRM_TIER_DIRECTIONALITY_RESULT.md — P-AMD-3b Part D directionality confirmation

SIMULATED: verifies every tier movement identified by the estimator's known shrinkage bias is conservative (recovered ACMG tier <= true tier), per this task's own explicit HALT condition. Compares the tier PROTOCOL.md §9's OddsPath thresholds would assign to the INJECTED (true) value against the tier assigned to the RECOVERED CI lower bound, for every pathogenic-direction quantity with a declared bias-prediction entry.

| quantity | injected | true_tier | true_points | recovered_point | ci_low | recovered_tier | recovered_points | verdict |
|---|---|---|---|---|---|---|---|---|
| core_hr_joint_LR | 5.826333 | PATHOGENIC_MODERATE | 2 | 4.822998 | 4.279654 | PATHOGENIC_SUPPORTING | 1 | CONSERVATIVE |
| ddr_signaling_joint_LR | 5.154487 | PATHOGENIC_MODERATE | 2 | 4.655099 | 4.144367 | PATHOGENIC_SUPPORTING | 1 | CONSERVATIVE |

**OVERALL: ALL MOVEMENTS CONSERVATIVE**
