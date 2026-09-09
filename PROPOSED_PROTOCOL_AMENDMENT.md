SIMULATED DATA — NOT A SCIENTIFIC RESULT

# PROPOSED_PROTOCOL_AMENDMENT.md — replacement text for PROTOCOL.md §7.1

SIMULATED: this document PROPOSES exact replacement text for PROTOCOL.md
section 7.1 ("Model"). **`PROTOCOL.md` itself is not modified by this
document or this task.** No ACMG evidence strength is assigned anywhere
below. Per Standing Rule 10, this is a proposal for human review — see
`PROTOCOL_DEVIATIONS.md` for the deviation record and `REPORT.md` for
where this surfaces prominently, and HALT: nothing in this repository's
pipeline, gate, or estimator code implements any of the text below.

## Why this text exists

`ESTIMATOR_SPECIFICATION_AUDIT.md` (prior task, this session) proved from
the code, then proved numerically (a two-dataset test constructed so that
only a true joint estimator could pass it), that PROTOCOL.md's current
§7.1 specifies and `stake_ablation.py` correctly implements a **product
of per-feature marginal likelihood ratios under a conditional-independence
assumption** — not a joint density model. The three evidentiary features
(WT_LOST direction, GIS score, SBS3 exposure) are three readouts of one
underlying event (HR-deficiency, represented in this project's own
simulator by a single shared latent variable) — the independence
assumption is known false by the project's own design, and multiplying
correlated likelihood ratios is exactly the failure mode the original
brief this project started from named as the error reviewers look for
first. The decision has been made, on this evidence, to replace the
estimator with penalized logistic regression, as that original brief
specified. This document drafts that replacement; it does not implement
it.

---

## REPLACEMENT TEXT FOR PROTOCOL.md §7.1

*(The following is the complete proposed replacement for the existing
§7.1 "Model" subsection — from its opening line through the end of the
subsection, immediately before §7.2 "Cross-validation," which is
unchanged — see "What is carried over unchanged" below.)*

> ### 7.1 Model
>
> The LR is estimated as a **class-conditional likelihood ratio** via
> **L2-penalized (ridge) logistic regression** fit jointly on the full
> feature vector, with purity, PAM50 subtype, and WGD status as
> covariates — not a per-feature product under a conditional-independence
> assumption.
>
> **Feature vector and covariates.** The model is fit on:
>
> - **Evidentiary features** (the quantities the LR is evidence about):
>   `wt_lost` (binary: 1 if the called second-hit direction is
>   WT-lost, else 0), `gis` (continuous: genomic instability score),
>   `sbs3` (continuous: SigProfilerAssignment SBS3 relative exposure).
> - **Covariates** (adjusted for, not themselves evidence of
>   pathogenicity): `purity` (continuous, tumor purity estimate),
>   `pam50_subtype` (categorical, 5 levels — LumA, LumB, HER2-enriched,
>   Basal-like, Normal-like; reference-coded against LumA as the
>   reference level, 4 indicator terms), `wgd` (binary: whole-genome-
>   doubling status).
>
> **Model form.** Let `X` denote the full predictor vector (3 evidentiary
> features + purity + 4 subtype indicators + WGD = 9 terms) for one
> observation. The model estimates
>
> `p_hat(X) = sigmoid(beta_0 + beta . X)`
>
> as the fitted probability of Pathogenic class membership, where
> `beta_0` and the coefficient vector `beta` are fit by L2-penalized
> (ridge) logistic regression on the reference set — **no L1/lasso
> term, and no interaction or polynomial terms beyond the linear terms
> listed above**, unless a future amendment adds and justifies them (see
> "Assumptions" below for what this restricts).
>
> **Penalty and its selection.** The penalty is **ridge (L2)**:
> `minimize [negative log-likelihood + lambda * ||beta||^2]` (the
> intercept `beta_0` is not penalized). Ridge, not lasso or elastic net,
> is specified because every one of the 9 terms above is retained by
> design (none is a candidate for exclusion via sparsity) and because
> ridge is the more stable choice at the small reference-set sizes this
> project's own realistic-n figures (`SIMULATION_SPEC.md` §6) describe —
> lasso's coefficient instability at small n is a known risk this project
> has no evidence it can tolerate, and elastic net's second tuning
> parameter is not justified by any feature-selection need here. This
> choice is ARBITRARY-but-standard, disclosed in `PARAMETER_PROVENANCE.tsv`-
> style provenance if and when this amendment is implemented, not asserted
> as uniquely correct.
>
> `lambda`'s strength is selected via the SAME variant-grouped 5-fold
> cross-validation specified in §7.2 (carried over unchanged, see below),
> using the mean held-out-fold binomial deviance (negative log-likelihood)
> as the selection criterion — the `lambda` value within one standard
> error of the minimum deviance across folds (`lambda`.1se`, the standard,
> more-conservative-than-`lambda.min` convention) is selected, to
> reduce the chance of the fold-level noise inherent to overlapping small
> reference sets driving the choice.
>
> **Conversion from predicted probability to likelihood ratio — the
> exact arithmetic.** This is the step identified as having broken a
> prior version of this project's pipeline ("v2"); it is written out in
> full here, not left to implementation.
>
> Let `n_path_ref` and `n_benign_ref` be the number of Pathogenic and
> Benign observations in the reference set the model is FIT on (the same
> reference set `p_hat` is evaluated against). Fitting a logistic
> regression on a case-control-style reference set (not a random
> population sample) is a well-established statistical equivalence
> (Prentice & Pyke 1979): the fitted SLOPE coefficients `beta` are
> consistent for the same slopes a prospective/cohort-sampled logistic
> regression would estimate, but the fitted INTERCEPT `beta_0` absorbs
> the reference set's own class balance, `log(n_path_ref / n_benign_ref)`,
> as an ADDITIVE offset relative to the population intercept. Consequently
> `p_hat(X) / (1 - p_hat(X))` is the model's POSTERIOR odds of
> pathogenicity **under the reference set's own, arbitrary class
> balance as an implicit prior**, not a likelihood ratio.
>
> The likelihood ratio is recovered by dividing that posterior odds by
> the SAME implicit prior odds the fit imposed:
>
> ```
> LR(X) = [ p_hat(X) / (1 - p_hat(X)) ]  /  [ n_path_ref / n_benign_ref ]
>       = [ p_hat(X) / (1 - p_hat(X)) ]  *  [ n_benign_ref / n_path_ref ]
> ```
>
> **Worked numeric example** (illustrative values, not a project figure):
> if `n_path_ref = 60`, `n_benign_ref = 240` (a 1:4 reference-set ratio,
> NOT the true population prevalence of pathogenic variants), and the
> fitted model returns `p_hat(X) = 0.90` for one evaluated feature
> vector `X`: posterior odds `= 0.90 / 0.10 = 9.0`; reference-set prior
> odds `= 60 / 240 = 0.25`; `LR(X) = 9.0 / 0.25 = 36.0`.
>
> **This formula is valid ONLY if the model fit itself applies no
> additional class-balance correction** — no `class_weight="balanced"`
> argument, no oversampling/undersampling of either class, no explicit
> prior/offset term supplied to the fitting routine. **This protocol
> specifies: fit the plain, unweighted, unresampled logistic regression
> on the reference set exactly as assembled, and apply the single
> division above.** If any class-balance correction is EVER applied
> during fitting, the arithmetic above must be replaced with one that
> accounts for it explicitly (dividing out whatever prior the correction
> imposed instead of `n_path_ref / n_benign_ref`) — applying BOTH a
> fit-time correction and the post-hoc division above double-corrects and
> silently produces a wrong LR. This exact failure mode — an unstated or
> undocumented fit-time class-balance adjustment combined with a
> post-hoc prior-odds division that assumes there wasn't one — is named
> here as the specific, concrete mechanism this task's own text
> attributes to "what broke v2." See STEP 4 (`ESTIMATOR_SPECIFICATION_AUDIT.md`'s
> companion risk statement, `PROPOSED_PROTOCOL_AMENDMENT.md`'s own STEP 4
> section below) for the test that must catch a recurrence.
>
> **Calibration.** On each of the 5 variant-grouped cross-validation
> folds (§7.2, unchanged), the model fit on the other 4 folds is
> evaluated on the held-out fold's predicted probabilities `p_hat`
> (BEFORE the prior-odds conversion above — calibration concerns the
> probability estimate itself, not the converted LR). Diagnostics
> reported for every fold, pooled across all 5 folds' held-out
> predictions:
>
> - A **reliability curve** (predicted-probability decile bins on the
>   x-axis, observed empirical fraction Pathogenic within each bin on
>   the y-axis, both reported with their bin's `n` per Standing Rule 5),
>   compared against the diagonal.
> - **Brier score** (mean squared error of `p_hat` against the true
>   binary class label, pooled across held-out folds).
> - **Expected Calibration Error (ECE)**, the n-weighted mean absolute
>   deviation of each decile bin's observed fraction from its mean
>   predicted probability.
>
> **Calibration is diagnostic only at this stage — it does NOT feed back
> into the prior-odds conversion above.** Applying a calibration
> correction (e.g. Platt scaling or isotonic regression) on top of the
> prior-odds division would be a second, compounding correction of
> exactly the kind the "no double-correcting" warning above exists to
> prevent; if the calibration diagnostics show material miscalibration,
> that is reported as a finding requiring a future, separately
> pre-registered amendment, not silently absorbed into this one.
>
> **Assumptions this model makes, stated explicitly (§7.1 previously left
> its own assumption — conditional independence — implicit until this
> project's own audit surfaced it; this replacement does not repeat that
> omission):**
>
> 1. **Log-linearity**: the log-odds of pathogenicity is a LINEAR
>    function of the listed features and covariates, with no interaction
>    or higher-order terms unless a future amendment adds and justifies
>    them. See STEP 4 below for how this is checked, and for the two
>    concrete respects in which this project's own generative model is
>    known to depart from it (WT_LOST's probit link; SBS3's clip-boundary
>    point mass).
> 2. **No unmodeled confounders**: purity, subtype, and WGD are the
>    complete covariate set adjusted for; any other systematic source of
>    feature variation not listed here (e.g. sequencing batch,
>    depth-regime-driven noise beyond what purity/WGD capture) is
>    unadjusted and would bias the fitted coefficients if it correlates
>    with both class and a feature.
> 3. **Correct reference-set class-balance bookkeeping**: the prior-odds
>    conversion above is exact only if `n_path_ref` / `n_benign_ref` are
>    the TRUE counts the model was fit on, with no fit-time reweighting —
>    see the conversion arithmetic's own warning above.
> 4. **Ridge's implicit prior does not bias the operating point**: an L2
>    penalty is equivalent to placing an independent, zero-mean Gaussian
>    prior on each coefficient — this shrinks all coefficients toward 0
>    (toward LR=1, no evidence) by an amount governed by `lambda`. This
>    is a real, disclosed bias-variance trade-off, not a free correction;
>    its magnitude is checked via the calibration diagnostics above and
>    via comparing `lambda.1se`'s shrinkage against `lambda.min`'s.
> 5. **Fixed EVAL_POINT / fixed feature transformation**: as in the
>    current §7.1, no feature is transformed (log, rank, etc.) before
>    entering the model unless a future amendment specifies and justifies
>    a transformation — the model is linear in the RAW feature scale
>    named above.

## What is carried over UNCHANGED

- **§7.2 Cross-validation** (variant-grouped k-fold, k=5, stratified to
  ±5 percentage points of the full-set Pathogenic:Benign ratio) — reused
  both for `lambda` selection (above) and for the calibration diagnostics
  (above). No change to its own text is proposed.
- **§7.3 Patient-clustered bootstrap** (nonparametric cluster bootstrap
  at the patient level, B=2000, percentile 95% CI) — reused unchanged,
  applied to the NEW estimator's `LR(X)` output in place of the current
  estimator's output. This is a substitution of estimand (what is being
  bootstrapped), not a change to the resampling method itself.

No other section of PROTOCOL.md is proposed for change by this document.

---

## STEP 4 — risks

### Risk 1: the prior-odds conversion is the v2 failure mode

**Named mechanism** (above): a fit-time class-balance correction
(`class_weight="balanced"`, resampling, or an explicit prior/offset) left
undocumented or unaccounted for, combined with the post-hoc
`n_path_ref / n_benign_ref` division specified above, double-corrects
and produces a silently wrong LR — too large if the fit under-corrected
relative to what the post-hoc division assumes, too small (or reversed in
extreme cases) if it over-corrected.

**The test that catches it, and what it must show.** Before this
amendment is implemented, a dedicated regression test must exist —
searched for and NOT found under this repository's tracked history (this
task's own prior audit, `ESTIMATOR_OPTIONS.md`, already reported this
search and its UNVERIFIED result for a "class-imbalance test" by that
name; the same gap applies here and is not re-asserted as resolved) — and
must be written as part of implementing this amendment, not assumed to
already exist. The test: construct a reference set with a KNOWN, injected
class imbalance different from the population prior (e.g. 1:4
Pathogenic:Benign when the true simulator prevalence is 1:1, mirroring
this document's own worked example), fit the model exactly as specified
(no `class_weight`, no resampling), apply the conversion formula above,
and confirm the resulting `LR(X)` is **invariant to the reference set's
class balance** — i.e., re-running the same test with a 1:1 reference set
of the same underlying feature distributions must recover the SAME
`LR(X)` at the same evaluation point, within Monte Carlo noise, as the
1:4 reference set did. **If the two reference-set-balance conditions
produce systematically different `LR(X)` values at the same evaluation
point, the conversion is broken and this amendment must not be
implemented until it is fixed** — this is exactly the invariance property
a correct prior-odds conversion guarantees and an uncorrected or
double-corrected one violates.

### Risk 2: log-linearity is an assumption the previous model did not make

The current (product-of-marginals) estimator makes no linearity
assumption at all in the raw feature values — its own instability is a
KDE/bandwidth problem (`ESTIMATOR_SPECIFICATION_AUDIT.md` STEP 4), not a
functional-form assumption. The replacement's log-linear form is new, and
two concrete, already-known respects in which this project's own
generative model departs from it:

- **WT_LOST's probit link**: `P(WT_LOST | Z) = Phi(a + b*Z)` is a probit,
  not logit, function of the shared latent `Z` — a logistic model that
  includes `wt_lost` as one linear predictor term does not exactly
  reproduce the TRUE joint likelihood ratio's dependence on `wt_lost`
  jointly with `gis`/`sbs3`, only a first-order log-linear approximation
  to it.
- **SBS3's clip boundary**: `sbs3` is clipped to `[SBS3_CLIP_LO,
  SBS3_CLIP_HI]` (`simulate.py`), producing a point mass at each boundary
  the log-linear model's smooth functional form cannot represent exactly.

**How this will be checked.** `estimator_joint_vs_product_test.py`
(prior task, this session) already established the pattern: construct
data from `simulate.py`'s own known generative model (which provides an
exact analytic true joint LR via `simulate.joint_lr`/`joint_density`, no
estimation needed for the "truth" side of the comparison), fit the
proposed logistic-regression estimator on samples drawn from it, and
compare the fitted model's `LR(X)` against the analytic true joint LR at
`EVAL_POINT`, across a range of n. **This must be reported as an
approximation-error curve (fitted LR vs. true LR, by n), not a single
pass/fail** — STEP 3's reachability classification below treats the
joint-LR quantities as STRUCTURALLY reachable under this amendment (the
estimator's factorization can represent correlation at all, unlike the
current one, which cannot represent it under any circumstance), which is
a distinct claim from the model recovering the exact true joint LR at
every n — log-linearity's adequacy, not just the amendment's structural
capacity, is what this check quantifies.

### Risk 3: quantities whose INTERPRETATION changes under the new estimator

- **`*_product_of_marginals_LR`** quantities do not disappear (the
  per-feature marginal KDE/Jeffreys machinery is retained unchanged,
  precisely so `loh_caller.py`/`signatures.py` keep their existing
  targets — see `REACHABILITY_TABLE.tsv`), but their ROLE changes: under
  the current estimator, `product_of_marginals_LR` is (once
  `ESTIMATOR_SPECIFICATION_AUDIT.md`'s finding is accounted for) what the
  estimator's own "joint LR" output actually equals — it is the primary
  reported quantity, mislabeled. Under the amendment, it becomes a
  **secondary, diagnostic** quantity — reported alongside the new,
  primary `joint_LR` specifically so the divergence between them (the
  `*_joint_vs_marginal_inflation_ratio`) remains visible, exactly
  reversing which of the two is "the estimator's real output" and which
  is "the diagnostic contrast."
- **`*_joint_vs_marginal_inflation_ratio`** changes from a
  simulator-truth-only quantity (computable analytically from
  `simulate.py`, but never independently verifiable against any
  estimator output, since the estimator could not independently estimate
  its numerator) to a quantity BOTH sides of which are now independently,
  empirically estimated — its interpretation shifts from "a property of
  the simulator's design" to "a property this study can now actually
  measure and validate."
- **NULL_ARM quantities** do not change interpretation — true LR ≡ 1.0
  under either estimator, for the same reason under both (identical
  class-conditional distributions), so nothing about what these
  quantities mean or how they are checked changes.

---

*(End of document. See `REACHABILITY_TABLE.tsv` for STEP 3's
quantity-by-quantity classification and `PROTOCOL_DEVIATIONS.md` for the
deviation record.)*
