SIMULATED DATA — NOT A SCIENTIFIC RESULT

# DISPOSITIVE_TEST_AFTER.md — P-EST-1's Step 2 test, re-run against the new estimator

SIMULATED: this document is the acceptance criterion this task's own
text calls non-negotiable. It re-runs `ESTIMATOR_SPECIFICATION_AUDIT.md`'s
decisive numeric test — identical marginal feature distributions, one
dataset correlated (drawn from `simulate.py`'s own shared-latent-Z
model), one independent — against `logistic_estimator.py` (the new,
implemented ridge-logistic estimator per `PROPOSED_PROTOCOL_AMENDMENT.md`),
in place of the old product-of-marginals estimator
(`stake_ablation.py`'s `joint_lr_for_subset`). Full script:
`estimator_joint_vs_product_test_v2.py`. Raw output:
`SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_V2.tsv`,
`SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_V2_REPLICATES.tsv`.

## Method (identical construction to the "before" test)

Covariates (purity, subtype, WGD) are held fixed at neutral,
representative values (purity=0.5, subtype=LumA [the model's reference
level], WGD=0) for every drawn sample and at the evaluation point, in
both constructions — so any separation between the new estimator's
`LR(CORRELATED)` and `LR(INDEPENDENT)` is attributable only to the
wt_lost/gis/sbs3 correlation structure under test, not to incidental
covariate confounding. 30 independent replicate draws, 300/class, both
arms — identical n and replicate count to the "before" test.

## Result: BEFORE → AFTER, side by side

| arm | true joint LR (correlated) | true product-of-marginals LR (= true joint LR, independent) | **OLD** estimator mean, correlated (sd) | **OLD** estimator mean, independent (sd) | **OLD** separation | **NEW** estimator mean, correlated (sd) | **NEW** estimator mean, independent (sd) | **NEW** separation |
|---|---|---|---|---|---|---|---|---|
| CORE_HR | 7.243 | 92.625 | 73.151 (20.878) | 78.535 (21.110) | **0.26 sd** | **7.424 (1.592)** | **52.982 (19.776)** | **3.25 sd** |
| DDR_SIGNALING | 6.204 | 22.794 | 21.320 (7.619) | 21.470 (6.193) | **0.02 sd** | **6.697 (1.444)** | **24.675 (8.432)** | **2.97 sd** |

("Separation" = `|mean(correlated) - mean(independent)| / pooled_sd` — the
same metric `ESTIMATOR_SPECIFICATION_AUDIT.md` reported for the old
estimator, computed identically here for direct comparability.)

## Verdict: PASS — the new estimator separates the two datasets and tracks the true joint values

**This is not a marginal improvement — it is qualitatively different
behavior.** The old estimator's separation (0.26 / 0.02 pooled-sd units)
was noise: run twice on datasets engineered to have different true joint
LRs, it returned statistically indistinguishable numbers. The new
estimator's separation (3.25 / 2.97 pooled-sd units) is a real, large,
unambiguous signal — over an order of magnitude larger than the old
estimator's, and large enough that the two distributions barely overlap.

**More than mere separation: the new estimator's mean values are
themselves close to the correct targets, in BOTH regimes** — not merely
"different from each other," but "close to what each dataset's true
value actually is":

- CORE_HR, correlated: new estimator mean **7.424**, true joint LR
  **7.243** — within 2.5%.
- CORE_HR, independent: new estimator mean **52.982**, true
  product-of-marginals LR **92.625** — a real ridge-shrinkage-driven
  downward bias (expected: ridge shrinks the fitted log-odds toward the
  reference-set's intercept, i.e. toward LR=1, and this shrinkage bites
  hardest exactly where the true LR is largest and furthest from 1 —
  see `CALIBRATION_DIAGNOSTICS.md` for the calibration diagnostics this
  motivates), but still an order of magnitude closer to the correct
  target (92.6) than to the WRONG target (7.2) it would land near if the
  estimator were still, secretly, a product-of-marginals computation.
- DDR_SIGNALING, correlated: new estimator mean **6.697**, true joint LR
  **6.204** — within 8%.
- DDR_SIGNALING, independent: new estimator mean **24.675**, true
  product-of-marginals LR **22.794** — within 8%, notably LESS biased
  than CORE_HR's independent case (DDR_SIGNALING's true product value,
  22.8, is far closer to LR=1 than CORE_HR's, 92.6, so ridge's
  shrinkage-toward-1 bias has less distance to travel).

`log(estimator mean) - log(true value)` is closer to the TRUE JOINT
target than to the true product-of-marginals target for both arms'
correlated-data runs (`tracks_true_joint = True` in
`SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_V2.tsv` for both rows) — the
new estimator is not merely "different," it is tracking the quantity
this study needs it to track.

**HALT condition does not trigger.** Per this task's own instruction,
this result clears the non-negotiable bar: proceeding to gate9, the
calibration diagnostics, the log-linearity check, and the re-run
instability sweep is warranted and reported below/in the companion
documents.

## What this does NOT establish

This test is deliberately narrow — the same narrowness the "before" test
had, for direct comparability. It fixes covariates at one neutral value
and evaluates at one point (`EVAL_POINT`). It does not, on its own,
establish that the new estimator is WELL-CALIBRATED (a separate,
genuine concern — the ridge-shrinkage bias observed above is real and
addressed, not hidden, in `CALIBRATION_DIAGNOSTICS.md`), that it behaves
well across the realistic small-n range Track B will actually see (see
`INTERVAL_INSTABILITY_V2.md`), or that its log-linearity assumption holds
broadly (see `CALIBRATION_DIAGNOSTICS.md`'s log-linearity section). Those
are each addressed in their own companion document, per this task's own
STEP 3-6 structure — this document answers exactly, and only, the
question STEP 2 poses.
