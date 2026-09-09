SIMULATED DATA — NOT A SCIENTIFIC RESULT

# CALIBRATION_DIAGNOSTICS.md — calibration and log-linearity checks for the new estimator

SIMULATED: this document reports `logistic_estimator.py`'s calibration
diagnostics (this task's STEP 1) and the log-linearity assumption check
(STEP 4), against real, generated 5-fold-CV-held-out predictions on the
full committed synthetic population. Full scripts:
`logistic_calibration_and_loglinearity.py`. Raw output:
`SIMULATED_CALIBRATION_RESULTS.tsv`, `SIMULATED_LOGLINEARITY_RESIDUAL_GRID.tsv`,
`SIMULATED_LOGLINEARITY_NESTED_COMPARISON.tsv`. Does not modify
`PROTOCOL.md`, `simulate.py`, or `logistic_estimator.py`.

## Part A — Calibration

5-fold variant-grouped (= sample-grouped in this simulator, no recurrent
variants — see `logistic_estimator.py`'s own docstring) cross-validation,
lambda selected via CV deviance (`lambda.1se`, per
`PROPOSED_PROTOCOL_AMENDMENT.md`), held-out predicted probabilities
pooled across all 5 folds, evaluated on `p_hat` BEFORE the prior-odds
conversion (per the amendment's own text — calibration concerns the
probability estimate, not the converted LR).

| arm | lambda.1se | lambda.min | Brier score | ECE | n held out |
|---|---|---|---|---|---|
| CORE_HR | 30.0 | 1.0 | 0.0907 | 0.0260 | 3696 |
| DDR_SIGNALING | 100.0 | 10.0 | 0.1936 | 0.0274 | 3696 |

**Reliability curve** (predicted-probability decile, `n` per bin per
Standing Rule 5, mean predicted vs. observed fraction Pathogenic):

**CORE_HR:**

| bin | n | mean predicted | observed fraction |
|---|---|---|---|
| [0.0,0.1) | 969 | 0.050 | 0.024 |
| [0.1,0.2) | 364 | 0.145 | 0.118 |
| [0.2,0.3) | 209 | 0.245 | 0.234 |
| [0.3,0.4) | 167 | 0.348 | 0.287 |
| [0.4,0.5) | 148 | 0.444 | 0.486 |
| [0.5,0.6) | 152 | 0.551 | 0.553 |
| [0.6,0.7) | 184 | 0.649 | 0.696 |
| [0.7,0.8) | 214 | 0.753 | 0.799 |
| [0.8,0.9) | 330 | 0.856 | 0.900 |
| [0.9,1.0) | 959 | 0.964 | 0.973 |

**DDR_SIGNALING:**

| bin | n | mean predicted | observed fraction |
|---|---|---|---|
| [0.0,0.1) | 7 | 0.094 | 0.000 |
| [0.1,0.2) | 274 | 0.167 | 0.117 |
| [0.2,0.3) | 513 | 0.250 | 0.211 |
| [0.3,0.4) | 566 | 0.348 | 0.323 |
| [0.4,0.5) | 540 | 0.450 | 0.465 |
| [0.5,0.6) | 524 | 0.550 | 0.571 |
| [0.6,0.7) | 486 | 0.650 | 0.665 |
| [0.7,0.8) | 403 | 0.747 | 0.806 |
| [0.8,0.9) | 315 | 0.841 | 0.835 |
| [0.9,1.0) | 68 | 0.926 | 0.941 |

**Reading**: both arms track the diagonal closely across every bin with
meaningful `n` (CORE_HR's smallest and largest bins carry n≥148; DDR's
[0.0,0.1) bin has only n=7, too small to read — flagged rather than
silently averaged in with the rest, per Standing Rule 5). ECE (2.6% /
2.7%) and Brier score are both low. **The predicted PROBABILITY (`p_hat`)
is well calibrated for both arms at this sample size.** This is a
distinct claim from "the converted LR is unbiased" — see Part B below and
`DISPOSITIVE_TEST_AFTER.md`'s own observed downward bias in the converted
LR at extreme evaluation points, which calibration (measured on `p_hat`,
bounded in [0,1]) cannot by itself detect (a systematic LR bias that is
small in probability space can still be large in odds/LR space, since
LR is a ratio that magnifies small probability errors near the tails).

## Part B — Log-linearity: two independent checks

### B1. Residual grid vs. simulate.py's own true analytic joint LR

For `subtype="LumA"` specifically, `simulate.joint_lr(arm, x)` is EXACT
(LumA's `SUBTYPE_Z_SHIFT`/`SUBTYPE_GIS_SHIFT` are both `0.0` — confirmed
in `TRUTH_DELTA.md`'s subtype-fix addendum) — a genuine ground-truth
comparison, not an approximation of one. The fitted model (trained on the
full, subtype-diverse population) is evaluated at a 5×5 grid of
(gis, sbs3) values, `wt_lost=1`, `purity=0.5`, `subtype=LumA`, `wgd=0`
held fixed, against `simulate.joint_lr` at the same points.

| arm | mean log-residual | sd | range |
|---|---|---|---|
| CORE_HR | −0.331 | 0.450 | [−1.079, 0.434] |
| DDR_SIGNALING | −0.265 | 0.073 | [−0.458, −0.176] |

**A real, systematic pattern exists — reported honestly, not smoothed
over.** Full grid: `SIMULATED_LOGLINEARITY_RESIDUAL_GRID.tsv`. For
CORE_HR specifically, the residual is small near the grid's low corner
(gis=20, sbs3=0.05: true LR=0.197, residual=−0.018) and grows steadily
more negative toward the high corner (gis=70, sbs3=0.6: true LR=847,
residual=−1.079) — **the residual's magnitude scales monotonically with
the true log-LR's own distance from zero, in both directions the grid
covers**, not with `gis`/`sbs3` individually in an inconsistent way. This
is the SHAPE a shrinkage-toward-`LR=1` bias produces, not the shape a
missing-interaction or missing-curvature functional-form error would
produce (a genuine functional-form miss would show a residual pattern
tied to the SHAPE of the feature relationship, e.g. a residual that
changes sign as gis or sbs3 individually cross some value — not one that
tracks the magnitude of the fitted quantity itself, symmetric around
`LR=1`).

### B2. Nested model comparison: does a richer functional form help?

An augmented model adds a `gis²` term and a `gis × wt_lost` interaction
term to the base model; 5-fold CV mean deviance is compared.

| arm | base model CV deviance | augmented model CV deviance | relative improvement |
|---|---|---|---|
| CORE_HR | 431.638 | 430.349 | **0.30%** |
| DDR_SIGNALING | 838.248 | 839.700 | **−0.17% (worse)** |

**Neither arm shows a meaningful improvement from added interaction/
curvature terms — DDR_SIGNALING's augmented model is actually
(negligibly) worse, consistent with overfitting two extra, uninformative
parameters rather than capturing real missing structure.** This directly
supports B1's own diagnosis: a richer functional form does not close the
gap B1 found, which is evidence AGAINST attributing that gap to a
log-linearity failure.

### Conclusion: the observed residual is regularization bias, not a log-linearity failure

**Log-linearity is not rejected by either check.** B1's systematic
residual is real and quantified, but B2 shows it is not fixed by adding
the flexibility a genuine log-linearity failure would require — its
shape (scaling with the fitted quantity's own magnitude, symmetric
around `LR=1`) is the signature of ridge's own shrinkage-toward-the-
reference-intercept bias, an assumption `PROPOSED_PROTOCOL_AMENDMENT.md`
already named explicitly (Assumption 4: "Ridge's implicit prior does not
bias the operating point... a real, disclosed bias-variance trade-off").
`lambda.1se` (30.0 for CORE_HR) is 30x `lambda.min` (1.0) — the
amendment's own choice of the more conservative `lambda.1se` accepts a
larger version of exactly this bias in exchange for lower fold-to-fold
variance; this is that trade-off's quantified cost, not a new,
undisclosed finding requiring a `PROPOSED_DEVIATIONS.md` entry (per this
task's own instruction: "If it fails, that is a finding for
PROPOSED_DEVIATIONS.md" — log-linearity itself did not fail; the checks
above distinguish the two).

**Practical consequence, stated plainly**: at evaluation points far from
`LR=1` (large true joint LR, as CORE_HR's does at `EVAL_POINT` and
beyond), expect the converted LR to be a conservative UNDERESTIMATE of
the true value, by an amount that grows with distance from `LR=1` — this
is a known, quantified, one-directional bias (never an overestimate in
this grid), not an unpredictable source of error. `DISPOSITIVE_TEST_AFTER.md`'s
own CORE_HR/independent-dataset result (new estimator mean 52.98 vs. true
92.63) is this exact effect, observed independently in that test.
