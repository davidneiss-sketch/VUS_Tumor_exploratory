SIMULATED DATA — NOT A SCIENTIFIC RESULT

# MIXTURE_FIX_POST_FIX_DIAGNOSTICS.md — shrinkage attribution re-established on the corrected estimand

Per P-AMD-3a's explicit instruction, P-DIAG-1's STEP 1/STEP 3/STEP 4
diagnostics are re-run against the corrected (subtype-blind,
`MIXTURE_FIX.md`) mixture computation. Full data:
`mixture_fix/SIMULATED_LAMBDA_SWEEP_POST_FIX.tsv`,
`mixture_fix/SIMULATED_SEED_VARIATION_POST_FIX.tsv` (+ summary). Scripts:
`mixture_fix_lambda_sweep.py`, `mixture_fix_seed_variation.py`. Neither
script changes lambda selection, the bootstrap replicate count used in
the committed run, or any estimator parameter — same disclosed-reduction
convention as P-DIAG-1 (B_DIAGNOSTIC=500 vs. committed B=2000, 15 seeds
per arm).

## 1. Lambda sweep on the corrected computation

| arm | lambda | mixture LR | relative bias | note |
|---|---|---|---|---|
| CORE_HR | 0.001 (near-unpenalized) | 6.1799 | +6.07% | |
| CORE_HR | 10.0 | 5.5901 | −4.05% | |
| CORE_HR | **30.0** | **4.8230** | **−17.22%** | **CV-selected (lambda.1se)** |
| CORE_HR | 60.0 | 4.1392 | −28.96% | |
| DDR_SIGNALING | 0.001 (near-unpenalized) | 5.9731 | +15.88% | |
| DDR_SIGNALING | 60.0 | 5.0656 | −1.72% | |
| DDR_SIGNALING | **100.0** | **4.6551** | **−9.69%** | **CV-selected (lambda.1se)** |
| DDR_SIGNALING | 200.0 | 3.9538 | −23.29% | |

**The shrinkage curve remains monotonic and well-characterized after the
fix** — bias falls smoothly from a small positive residual near lambda=0
(no longer the old +24.9%/+28.9% application-point-inflated figure;
see `MIXTURE_FIX.md` section 4) through zero, to increasingly negative as
lambda grows. Both CV-selected lambdas sit past their own zero-bias
crossing, same qualitative picture as before the fix, at a **larger**
magnitude — exactly the "gap widens, as expected" finding
`MIXTURE_FIX.md` section 5 reports, now shown as a smooth curve rather
than a single point.

**Independently reproduced**, not merely asserted: the CV-selected-lambda
rows above (−17.22% CORE_HR, −9.69% DDR_SIGNALING) were computed by this
sweep script, refitting on the full population from scratch — and they
match the corrected `production_v2/SIMULATED_RECOVERED.tsv` run's own
relative-bias figures (0.172207 / 0.096884 from
`SIMULATED_RECOVERY_TABLE.tsv`) to within rounding, the same
cross-check `RESIDUAL_DIAGNOSIS.md` performed pre-fix.

## 2. Seed variation on the corrected computation (STEP 1 + STEP 4 re-run)

Same method as P-DIAG-1: 15 independent seeds per arm, B=500 (disclosed
reduction from the committed B=2000), full fixed population
(n=1848/1848, no subsampling — only the bootstrap resampling seed
varies).

| arm | seeds | mean upper bound | SE(upper, B=500) | seeds containing injected |
|---|---|---|---|---|
| CORE_HR | 15 | 5.5013 | 0.0291 | **0 / 15** |
| DDR_SIGNALING | 15 | 5.2691 | 0.0287 | **15 / 15** |

**The post-fix result is, if anything, MORE decisively non-noise than
the pre-fix result was.** CORE_HR's upper bound now ranges from 5.4298 to
5.5442 across all 15 seeds — every single one lands roughly 0.28–0.40
below the injected value 5.8263, an order of magnitude larger than the
seed-to-seed SE (0.0291). The corrected gap (mean upper bound 5.5013 vs.
injected 5.8263 = 0.325) is not "within seed-to-seed variation" by any
reasonable margin — this is the same qualitative conclusion
`RESIDUAL_DIAGNOSIS.md` reached pre-fix (miss is systematic, not a coin
flip), now with a wider, even more unambiguous margin. DDR_SIGNALING's
pass is equally robust post-fix (15/15, same as pre-fix) — the CORRECTED
computation does not change which arm passes and which fails; it only
changes the SIZE of CORE_HR's miss and DDR_SIGNALING's margin, exactly as
`MIXTURE_FIX.md` section 5 predicted ("this widening is the correct,
expected outcome").

Full data: `mixture_fix/SIMULATED_SEED_VARIATION_POST_FIX.tsv`,
`mixture_fix/SIMULATED_SEED_VARIATION_POST_FIX_SUMMARY.tsv`.

## 3. Conclusion

The shrinkage attribution `RESIDUAL_DIAGNOSIS.md` established pre-fix is
**re-established, unchanged in kind, on the corrected computation**: the
CORE_HR containment miss is a real, systematic, reproducible consequence
of ridge shrinkage bias at the CV-selected lambda — now larger, because
`MIXTURE_FIX.md`'s fix removed a separate defect (the application-point
mismatch) that had been partially offsetting it, not because anything new
went wrong. This is the evidentiary basis `PROPOSED_GATE6_AMENDMENT.md`
and `CONSERVATIVE_ASSIGNMENT_ANALYSIS.md` build on.
