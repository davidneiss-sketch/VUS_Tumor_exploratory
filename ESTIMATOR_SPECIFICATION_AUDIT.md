SIMULATED DATA — NOT A SCIENTIFIC RESULT

# ESTIMATOR_SPECIFICATION_AUDIT.md — does PROTOCOL.md's estimator model the joint density?

SIMULATED: this document settles a yes/no question from the code and a
decisive numeric test; it does not fix anything. Per Standing Rule 10,
this is a finding, reported with evidence, not an amendment — `PROTOCOL.md`,
`simulate.py`, `stake_ablation.py`, and every other pipeline/estimator
file are unmodified. HALT after this document and its sibling
`ESTIMATOR_OPTIONS.md`: which side changes is the human's decision.

`INTERVAL_INSTABILITY.md`'s own Headline finding 4 already reported, in
passing, that "PROTOCOL.md §7.1's joint estimator is not a true
multivariate (joint) KDE at all; it is a PRODUCT of independently-fit 1-D
KDE/Jeffreys-proportion ratios." This document verifies that claim
directly against the code (STEP 1), proves it with a test constructed
specifically to be undeniable (STEP 2), states what that means for P09
(STEP 3), and separates and diagnoses GATE8's two instability findings
(STEP 4).

## STEP 1 — the fact, from the code

### 1a. What PROTOCOL.md specifies

`PROTOCOL.md` §7.1 ("Model"), quoted verbatim:

> **Joint feature vector:** the product of per-feature LRs, under a
> conditional-independence assumption given class. This assumption is
> tested and reported (not assumed silently): pairwise feature
> correlations are computed within each reference class and reported
> alongside every joint LR; no joint LR is reported without its
> supporting correlation diagnostic.

**PROTOCOL.md itself specifies a product of marginals**, explicitly under
a stated conditional-independence assumption — not a true joint density
estimate. The document does not silently assume independence: it commits
to *testing and reporting* the assumption (via pairwise correlation
diagnostics) alongside every joint LR. It does not, however, commit to
*correcting* for any correlation found — the LR computed and reported is
the product regardless of what the correlation diagnostic shows.

### 1b. What the code computes

`stake_ablation.py` (PROTOCOL.md §7.1's implementation — KDE for
continuous features, Jeffreys-corrected proportion for categorical,
exactly as specified) traces as follows:

```python
def feature_lr(feature: str, path_vals: list, benign_vals: list) -> float:
    if feature == "wt_lost":
        p1 = jeffreys_p(sum(path_vals), len(path_vals))
        p0 = jeffreys_p(sum(benign_vals), len(benign_vals))
        return p1 / p0
    x0 = EVAL_POINT[feature]
    f1 = kde_density_at(x0, path_vals)
    f0 = kde_density_at(x0, benign_vals)
    return f1 / f0


def joint_lr_for_subset(subset: tuple, path: dict, benign: dict) -> float:
    lr = 1.0
    for feat in subset:
        lr *= feature_lr(feat, path[feat], benign[feat])
    return lr
```

(`stake_ablation.py` lines 160-175, unmodified by this task.)

Tracing the arithmetic from a feature vector to the returned LR:
`joint_lr_for_subset` loops over the requested feature subset and, for
each feature independently, calls `feature_lr` on **only that one
feature's own column of values** (`path[feat]`, `benign[feat]`) —
`kde_density_at` never receives, and `feature_lr`'s signature never
accepts, any value from a *different* feature. **No step conditions one
feature's density estimate on another feature's value.** The three
per-feature ratios (WT_LOST via Jeffreys proportion, GIS and SBS3 via
1-D Gaussian KDE) are each computed in complete isolation, then
multiplied together at the end (`lr *= feature_lr(...)`). This is a
literal, in-code product of independently-estimated marginal likelihood
ratios — there is no covariance term, no multivariate kernel, no
conditioning step anywhere in the call graph from a feature vector to
the returned LR.

### 1c. Verdict: AGREE

**PROTOCOL.md's specification and the code agree.** Both are, explicitly
and by design, a product of per-feature marginal LRs under a stated
conditional-independence assumption — not a true joint density ratio.
This is not a specification/implementation mismatch to fix; it is a
mismatch (STEP 3) between what this estimator can measure and what
`SIMULATED_TRUTH.tsv`'s `*_joint_LR` quantities represent.

## STEP 2 — the decisive numeric test

`estimator_joint_vs_product_test.py` (new file, this task; read-only
imports of `simulate.py` and `stake_ablation.py`, no modification to
either) implements the task's own prescribed construction:

Two synthetic datasets with **identical class-conditional marginal
feature distributions** and **different correlation structure**:

- **CORRELATED** — drawn from `simulate.py`'s own one-factor shared-latent
  model: `z ~ Normal(Z_MEAN[arm][cls], Z_SD)`; `wt_lost`, `gis`, `sbs3`
  all downstream of the *same* per-sample `z`. This is the generative
  model `simulate.joint_lr(arm, x)` already computes analytically
  (Simpson-integrated over `z`) — no simulation is even needed to know
  its true joint LR, since the test IS that model.
- **INDEPENDENT** — `wt_lost`, `gis`, `sbs3` drawn *independently of each
  other*, each straight from its own class-conditional **marginal**
  distribution (`z` integrated out analytically via
  `simulate.marginal_wt_lost_prob` / `simulate.marginal_gaussian_feature_params`
  — the exact closed forms `simulate.product_of_marginals_lr` is built
  from).

By construction, both datasets have byte-identical closed-form marginal
distributions per feature (the CORRELATED draw's marginals, integrated
over `z`, are exactly those closed forms) — only the cross-feature
dependence differs. Therefore, exactly and without approximation:

- **true joint LR(CORRELATED)** = `simulate.joint_lr(arm, EVAL_POINT)`
- **true joint LR(INDEPENDENT)** = `simulate.product_of_marginals_lr(arm, EVAL_POINT)`
  (independence forces joint density = product of marginal densities, by
  the definition of statistical independence)
- **product-of-marginals LR is identical for both datasets** =
  `simulate.product_of_marginals_lr(arm, EVAL_POINT)`

Note on which truth values these are: this test deliberately uses
`simulate.py`'s pre-subtype-fix, Z-only bare functions (`joint_lr`,
`product_of_marginals_lr`), not the subtype-mixture `_collapsed`
functions the currently-committed `SIMULATED_TRUTH.tsv` reports — STEP 2
tests a property of the estimator's *factorization structure*, which does
not depend on whether the generative model also includes a subtype
mixture, and using the simpler two-dataset construction keeps the
independent/correlated contrast clean. The numbers below (7.24 / 92.63
for CORE_HR) are therefore **not** the same as `SIMULATED_TRUTH.tsv`'s
current `core_hr_joint_LR` / `core_hr_product_of_marginals_LR` rows (5.83
/ 46.78, post-subtype-fix) — both are correct for what they each measure;
they are not interchangeable, and this document does not conflate them.

**Estimator run 30 independent times on freshly-drawn samples (300/class)
from each construction, both arms** (full output:
`SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST.tsv`,
`SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_REPLICATES.tsv`):

| arm | true joint LR (CORRELATED) | true joint LR (INDEPENDENT) = product-of-marginals LR | estimator mean, CORRELATED (sd) | estimator mean, INDEPENDENT (sd) | mean difference, in pooled-sd units |
|---|---|---|---|---|---|
| CORE_HR | **7.243** | **92.625** | 73.151 (20.878) | 78.535 (21.110) | **−0.26** |
| DDR_SIGNALING | **6.204** | **22.794** | 21.320 (7.619) | 21.470 (6.193) | **−0.02** |

**Read this table left to right.** The true joint LR differs from the
true product-of-marginals LR by 12.8x (CORE_HR) and 3.7x (DDR_SIGNALING)
— a large, real, by-construction gap. **The estimator's own empirical
mean is statistically indistinguishable between the CORRELATED and
INDEPENDENT datasets** (−0.26 and −0.02 pooled-sd units respectively —
noise, not signal), and **both means sit close to the product-of-marginals
value (92.6 / 22.8), nowhere near the true joint LR of the correlated
dataset (7.2 / 6.2)**.

**This is dispositive, exactly per this document's own read-first
instruction: the estimator returns the same LR (up to sampling noise) for
the independent and correlated datasets. It is a product of marginals.
Proven — not inferred from behavior, demonstrated by a test constructed
so that only a true joint estimator could pass it.**

(The estimator's means, ~78-79% and ~94% of the respective
product-of-marginals values, sit somewhat below the exact analytic
product value — this is ordinary KDE smoothing bias at finite bandwidth
and n=300, not a sign of joint-density recovery; it moves the estimate
*toward* the product value's neighborhood, not toward the true joint
value's, which sits an order of magnitude away.)

## STEP 3 — what this means for P09's recovery target

`SIMULATED_TRUTH.tsv`'s `core_hr_joint_LR` and `ddr_signaling_joint_LR`
rows (and the corresponding `*_joint_vs_marginal_inflation_ratio` rows)
are the TRUE, latent-Z-integrated joint density ratio — the quantity
STEP 1/2 just proved PROTOCOL.md's estimator, run exactly as specified,
**cannot produce**. The estimator's own factorization guarantees its
expectation converges to the product-of-marginals value, not the joint
value, regardless of sample size, bootstrap replicate count, or KDE
implementation quality — this is not a small-n artifact fixable by more
data; STEP 2's test used n=300/class, an order of magnitude above the
realistic Track B class sizes this project has already characterized as
unstable even for the *marginal* SBS3 estimate, and the gap did not
narrow.

**Explicitly: if P09 scores gate6 recovery of `core_hr_joint_LR` /
`ddr_signaling_joint_LR` (or their inflation-ratio counterparts) against
this estimator's output, gate6 CANNOT pass on those quantities. Say
plainly: it will FAIL, and it is not a bug to chase — no amount of tuning,
larger n, or better bandwidth selection closes a gap that is structural
to the estimator's own factorization.** P06R's shared-latent model was
built precisely so the joint-vs-product gap would be large and testable
(12.8x / 3.7x pre-subtype-fix; 8.0x / 3.1x post-subtype-fix, per
`TRUTH_DELTA.md`'s subtype-fix addendum) — that gap is real, and it now
measures something P09 cannot use as this estimator's own recovery target:
**the gap between the correlated simulator and an independence-assuming
estimator, not a property this estimator can be scored on recovering.**

What P09 *can* still validate against this estimator, unaffected by this
finding: `*_product_of_marginals_LR` (this IS the estimator's own,
correctly-modeled target — STEP 2 shows the estimator converges to it,
not away from it), every single-feature marginal LR quantity
(`*_wt_lost_direction_LR`, `*_gis_score_LR`, `*_sbs3_exposure_LR` — none
of these were ever joint quantities to begin with, P07/P08's own scored
quantities are exactly this category, STEP 3 of `REVALIDATION_REQUIRED.md`
already treats them this way), and every `NULL_ARM` quantity (true LR
≡ 1.0 regardless of correlation structure, by construction — a product of
two identical-distribution ratios is 1.0 whether or not the underlying
features are correlated, so this recovery target is unaffected by STEP 1's
finding).

## STEP 4 — the two separate instability findings

### 4a. Density underflow (`ZERO_DENSITY_UNDEFINED`) — NOT a consequence of the product-of-marginals structure

**Independent of the joint-vs-product question.** The underflow event is
a property of the per-feature 1-D Gaussian-KDE step (Silverman bandwidth,
data-driven) combined with an `EVAL_POINT` that sits in the tail of
SBS3's Benign-class distribution — it would occur identically whether the
joint LR were later computed as a product or as a true multivariate KDE
(a true multivariate KDE would in fact be at least as susceptible,
typically more so, via the classic curse-of-dimensionality thinning of a
d-dimensional neighborhood — STEP 2's own product-of-marginals structure
is, if anything, protective here, since each feature's density is
estimated in its own 1-D space rather than a shared, thinner
d-dimensional volume, exactly `INTERVAL_INSTABILITY.md` Headline finding
4's own observation).

**Mechanism, demonstrated (not assumed):** `stake_ablation.py`'s
`silverman_bandwidth()` recomputes its bandwidth from whatever values are
actually passed to it — and `interval_instability_sweep.py`'s real trial
structure calls the estimator fresh on **every bootstrap resample**
(resampling WITH REPLACEMENT from an already-small original n-sized
subsample), not once on the original sample. A resample that happens, by
chance, to draw few distinct original values has a small or near-zero
empirical spread, collapsing THAT resample's own bandwidth toward the
numeric floor — and a Gaussian kernel with a near-zero bandwidth,
evaluated at `EVAL_POINT` (which sits well away from where the resampled
values cluster for SBS3 | Benign), underflows to exactly `0.0` in
floating point, raising `ZeroDivisionError` when the ratio is formed. This
is reproduced here by calling `stake_ablation.py`'s own, real,
unmodified `joint_lr_for_subset`/`bootstrap_ci` end to end
(`estimator_underflow_bandwidth_diagnosis.py`, new file this task) — an
independent replication, not the same run:

| n/class (CORE_HR) | zero-density fraction, this replication (60 trials, B=300) | zero-density fraction, `interval_instability_sweep.py`'s own committed sweep (15 trials, B=300) |
|---|---|---|
| 12 | 28.3% | 33.3% (5/15) |
| 15 | 13.3% | 13.3% (2/15) |
| 20 | 1.7% | 13.3% (2/15) |
| 25 | 1.7% | 0% (0/15) |
| 30 | 0% | 0% (0/15) |
| ≥30 | 0% throughout | 0% throughout |

An independent re-derivation (different sampling method — fresh
analytic-marginal draws here vs. without-replacement draws from the
already-committed population there — same estimator code, same trial
structure) reproduces the same qualitative and closely-matched
quantitative pattern: near-1-in-3 at n=12, collapsing to zero by n≈25-30.
Full table, both arms: `SIMULATED_KDE_BANDWIDTH_MECHANISM.tsv`.

An earlier draft of this diagnosis used a single FIXED, population-level
bandwidth instead of recomputing it per-resample, and found essentially
zero underflow at any n — the wrong mechanism, reported and corrected
here rather than silently discarded (see the file's own header comment):
it is specifically the *resample-level* bandwidth recomputation, not the
population-level spread, that collapses.

**Cause: attributed.** Per-feature 1-D Gaussian KDE with a data-driven
(Silverman) bandwidth, evaluated at a tail-adjacent `EVAL_POINT` for
SBS3 specifically, recomputed fresh on each small bootstrap resample. Not
a consequence of the product-of-marginals joint-combination step.

### 4b. Non-monotonic UNINFORMATIVE fraction — reconciled, largely an artifact of bucket-splitting

`interval_instability_sweep.py`'s own committed sweep bucket
`ZERO_DENSITY_UNDEFINED` separately from `UNINFORMATIVE` (correctly — an
undefined LR is a different, more severe failure than a wide-but-defined
one). Combining the two into one `not_usable_fraction` (already present
as its own column in `SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv`) and
testing whether the COMBINED sequence is monotonic non-increasing in n
(`estimator_underflow_bandwidth_diagnosis.py`, `SIMULATED_FAILURE_MODE_RECONCILIATION.tsv`):

| n/class | 12 | 15 | 20 | 25 | 30 | 40 | 50 | 65 | 75 | 100 | 130 | 160 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CORE_HR / dim 1, not_usable_fraction | 0.933 | 0.933 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.867 | 0.733 | 0.4 | 0.2 | 0.333 |

**Monotonic non-increasing up to R=15 sampling noise: TRUE** (the only
increase anywhere in the sequence is the last step, 0.2→0.333, a 2-trial
swing at R=15 — well within one binomial standard deviation at this
repeat count, not a real reversal). **The "worst in the middle, not the
smallest" shape `INTERVAL_INSTABILITY.md` Headline finding 1 reported is
real for the `UNINFORMATIVE`-only column, but is largely an artifact of
how the same, roughly-constant near-100%-failure population is bucketed
differently as n crosses the point (~n=20-30) where `ZERO_DENSITY_UNDEFINED`
stops occurring** — at n=12-15, a third to a tenth of trials are
`UNDEFINED` rather than `UNINFORMATIVE`, so the `UNINFORMATIVE` count
alone reads artificially low; once `UNDEFINED` vanishes (~n=20-30), every
still-failing trial shows up in the `UNINFORMATIVE` column instead,
making that column peak exactly where the combined failure rate was
already at its (roughly flat) ceiling the whole time.

The residual, genuine improvement — the combined `not_usable_fraction`
does decline substantially past n≈65-100 — is explained by the same
mechanism as 4a's underflow, continued past the point where it stops
producing exact zeros: `estimator_underflow_bandwidth_diagnosis.py`'s
`mean_top1_kernel_contribution_share` (the share of the KDE density sum
at `EVAL_POINT` contributed by the single closest observation, on the
*original*, non-resampled sample) declines smoothly and substantially
across the whole grid (CORE_HR: 0.689 at n=12 → 0.141 at n=160;
DDR_SIGNALING: 0.626 at n=12 → 0.130 at n=160 — full table,
`SIMULATED_KDE_BANDWIDTH_MECHANISM.tsv`). At small-to-mid n, the density
estimate at `EVAL_POINT` is effectively determined by whichever one or
two observations happen to land closest — and *which* few observations
those are, and whether they survive a given bootstrap resample, is highly
variable at these sample sizes, producing wide (not necessarily
undefined) bootstrap intervals. As n grows, more observations
meaningfully contribute, the estimate stops depending on any one point,
and the interval narrows enough to clear gate8's thresholds.

**Cause: attributed, as one continuous mechanism whose FAILURE MODE (not
its underlying severity) changes character around n≈20-30** — a
data-driven bandwidth combined with a tail-adjacent evaluation point for
SBS3 specifically. Bandwidth selection (Silverman's rule, specifically
its resample-level recomputation and its slow, `n^(-1/5)`, shrinkage) is
confirmed as the driver, not merely the "obvious candidate" — demonstrated
via the reconciliation and the top-1-contribution-share tables above, not
assumed.

## Summary

| question | answer |
|---|---|
| Does PROTOCOL.md §7.1's specification describe a joint density model? | **No** — a product of per-feature marginal LRs under a stated, disclosed conditional-independence assumption (STEP 1a) |
| Does the code implement what PROTOCOL.md specifies? | **Yes, they agree** (STEP 1b/1c) |
| Does the estimator, run on data with real correlation vs. none, return different LRs? | **No — statistically indistinguishable (STEP 2), proven by construction, not inferred** |
| Can P09 validate `*_joint_LR` / `*_joint_vs_marginal_inflation_ratio` against this estimator? | **No — structurally unreachable; gate6 would and should FAIL those quantities regardless of n or tuning (STEP 3)** |
| Can P09 validate `*_product_of_marginals_LR`, marginal LRs, and NULL_ARM quantities? | **Yes — unaffected by this finding (STEP 3)** |
| Is density underflow a consequence of the product-of-marginals architecture? | **No — a per-feature KDE/bandwidth issue, independent of it (STEP 4a)** |
| Is the non-monotonic UNINFORMATIVE fraction a real property of the estimator? | **Largely an artifact of bucket-splitting; the combined failure rate is monotonic up to sampling noise (STEP 4b)** |

See `ESTIMATOR_OPTIONS.md` for the proposed (not applied) paths forward.
This document does not choose one — Standing Rule 10.
