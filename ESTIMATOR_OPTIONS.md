SIMULATED DATA — NOT A SCIENTIFIC RESULT

# ESTIMATOR_OPTIONS.md — proposed paths forward, not a decision

SIMULATED: per Standing Rule 10, this document PROPOSES options. It does
not choose one, and no pipeline, estimator, or protocol file is modified
by it. `ESTIMATOR_SPECIFICATION_AUDIT.md` established that PROTOCOL.md's
estimator, as specified and as implemented, is a product of per-feature
marginal LRs under a conditional-independence assumption — not a joint
density model — and that `*_joint_LR` / `*_joint_vs_marginal_inflation_ratio`
truth quantities are structurally unreachable by it, at any n, by any
amount of tuning. This document lays out four ways the study could
respond. **HALT after this document — the choice is the human's.**

For every option: "P07/P08 survival" asks whether `loh_caller.py`'s and
`signatures.py`'s own already-committed gate6 scoring survives the option
unchanged. Both currently score only single-feature MARGINAL LR
quantities (`loh_caller.py`'s `RECOVERY_SCOPE`:
`core_hr_wt_lost_direction_LR`, `ddr_signaling_wt_lost_direction_LR`;
`signatures.py`'s gate6 targets: `core_hr_sbs3_exposure_LR`,
`ddr_signaling_sbs3_exposure_LR`) — **neither has ever evaluated the joint
feature vector at all.** Any option that changes only the joint-COMBINATION
step (all four below do) leaves these two files' own scored quantities
untouched by construction, independent of which option is chosen — this
column is not a discriminator between the four options; it is confirmed
here once, for all four, so the four writeups below need not repeat it as
if it varied.

## Option A — keep the current estimator; amend PROTOCOL.md to describe it accurately; restate what P09 can validate

**Requires.** No code change to `stake_ablation.py` or any estimator
implementation. A `PROTOCOL.md` §7.1 wording amendment (proposed only,
not applied here) making explicit what §7.1 already implies but does not
say outright: the "joint feature vector" LR is an independence-assuming
PRODUCT of marginals, and the correlation diagnostic §7.1 already
requires is reported for information, not used to correct the LR. A
restated P09 recovery scope, naming `*_product_of_marginals_LR`,
per-feature marginal LR quantities, and `NULL_ARM` quantities as
in-scope, and `*_joint_LR` / `*_joint_vs_marginal_inflation_ratio`
explicitly out of scope for this estimator.

**Cost.** Cheapest option by a wide margin — zero re-implementation,
zero new numerical-stability risk, zero new n-dependence to characterize.
The cost is not engineering effort but scope: the study would then have
no true joint model anywhere in its own pipeline. The naive-multiplication
warning PROTOCOL.md §7.1's own correlation-diagnostic language exists to
flag for *external* users of a reported LR applies, unaddressed, to this
pipeline's own primary joint-vector estimator.

**Downstream impact.** P09 is not blocked, only narrowed: it validates
recovery of the marginal and product-of-marginals quantities (a
real, well-posed comparison — STEP 2 of `ESTIMATOR_SPECIFICATION_AUDIT.md`
shows the estimator DOES converge to the product value). `*_joint_LR`
and its inflation-ratio quantities remain in `SIMULATED_TRUTH.tsv` as
documented, un-validatable truth about the simulator's own generative
correlation structure — useful for STEP 3's confounding demonstrations
and future estimator comparisons, not as this estimator's own target.

**Evidence that would favor it.** No further evidence is needed beyond
`ESTIMATOR_SPECIFICATION_AUDIT.md`'s own findings — this is the
null-change option, favored if the study accepts a marginals-and-product
scope for its primary estimator and prioritizes zero re-implementation
risk over closing the joint-density gap.

**P07/P08 survival.** Survives unchanged (see the shared note above) —
trivially, since nothing changes.

## Option B — true multivariate density ratio (joint KDE or an adaptive/k-NN density estimator over the full feature space)

**Requires.** Replacing `joint_lr_for_subset`'s per-feature loop with a
genuine multivariate density estimate — e.g. a product-kernel or
full-covariance-bandwidth multivariate Gaussian KDE, fit jointly on the
Pathogenic and Benign reference sets in the full (up to 3-D) feature
space, evaluated at `EVAL_POINT` as a single joint density (not a product
of three 1-D densities). Categorical (`wt_lost`) and continuous (`gis`,
`sbs3`) features would need a genuine mixed-type joint density
construction (e.g. a conditional decomposition, `f(gis, sbs3 | wt_lost)`
times `P(wt_lost)`, itself estimated jointly for the continuous pair) —
non-trivial relative to the current per-feature independence
factorization.

**Cost / degradation at small n.** Handles correlation directly by
construction — this option, and only this option among the four, would
let `*_joint_LR` become a legitimate P09 recovery target. It also
degrades fastest of the four at small n: the current, easier, per-feature
1-D KDE already shows real instability (`INTERVAL_INSTABILITY.md`,
`ESTIMATOR_SPECIFICATION_AUDIT.md` STEP 4) well into n=160/class for
SBS3 alone — a genuine 2-D or 3-D joint KDE thins its effective sample
density with every added dimension (the classic curse-of-dimensionality
effect `INTERVAL_INSTABILITY.md` Headline finding 4 notes the CURRENT
estimator is specifically *not* subject to, precisely because it factors
into 1-D pieces). **This project's own `interval_instability_sweep.py`
machinery (read-only reusable, unmodified) is the right tool to
characterize the n at which a true joint estimator becomes usable, but
that sweep has not been run for this option — reported here as a gap,
not filled by this task** (STEP 5 of this task's own instructions
specifies, not implements, options). What existing evidence already
shows: the realistic Track B class sizes this project has derived
(`SIMULATION_SPEC.md` §6: CORE_HR 55/75, DDR_SIGNALING 25/35;
PALB2/RAD51C/RAD51D in the low tens per this task's own framing) sit
inside or below the range where even the CURRENT, less-demanding
per-feature KDE is unstable — there is no evidence in this project that a
strictly harder multivariate version would do better at those n, and
every mechanistic reason (STEP 4's bandwidth/dimensionality argument) to
expect it would do worse.

**Evidence that would favor it.** A future, not-yet-run sweep
(`interval_instability_sweep.py`-style) showing a true multivariate
estimator's own UNINFORMATIVE/UNDEFINED rate at Track B-realistic n is
acceptable — currently unevidenced, and the existing single-feature sweep
argues against it being favorable without such a demonstration.

**P07/P08 survival.** Survives unchanged (shared note above).

## Option C — penalized logistic regression with the prior-odds correction (the original brief's specification)

**Requires.** Replacing the per-feature-product joint-LR step with a
regularized (ridge/L2 or elastic-net) logistic regression fit on the
reference sets across the feature subset, converted to a likelihood
ratio via a prior-odds correction (`LR = posterior odds / prior odds`,
using the reference-set class proportions as the prior) — this is
precisely the conversion step this task's own text identifies as "what
broke v2." This task did not find, in this repository, any
already-committed "class-imbalance test" file or artifact by that name
(searched for `class.imbalance`, `prior.odds`, `prior_odds` case-insensitive
across all tracked files; the only hit was `PROTOCOL.md`'s own §7 prose on
LRs vs. odds ratios, not a test). Per Standing Rule 3, this is reported
as UNVERIFIED rather than assumed: **if such a test exists outside this
repository's tracked history, or under a different name, it should be
named and pointed to before this option is pursued** — this task does not
invent a reference to one.

**Cost.** Handles correlation (regression coefficients absorb
correlated-feature structure jointly, unlike the current product) and
covariates, and — being parametric rather than a nonparametric density
estimate — should tolerate small n meaningfully better than Option B's
multivariate KDE (a fixed, small parameter count vs. an entire joint
density surface to estimate). The cost is reintroducing the exact
prior-odds conversion mechanism this task's own framing flags as having
broken this project before, with no in-repository regression test found
to catch a recurrence — building or locating that safeguard would be a
prerequisite, not an afterthought, if this option is pursued.

**Evidence that would favor it.** The original brief's own specification
naming penalized logistic regression is itself evidence, if that brief is
judged the more authoritative source than PROTOCOL.md §7.1's current
text — a judgment call for the human, not resolvable from this
repository's code alone. Favored if the prior-odds conversion can be
re-validated cleanly (a class-imbalance regression test built or located
first).

**P07/P08 survival.** Survives unchanged (shared note above) — but is the
option most likely, of the four, to newly require exactly the kind of
regression test named above, since it is the one reintroducing the
conversion step implicated in a past failure.

## Option D — low-dimensional parametric joint model (e.g. a Gaussian copula over the three features)

**Requires.** Fitting a copula: transform each feature's value to a
uniform or standard-normal score via its own already-estimated marginal
CDF (the existing per-feature KDE/Jeffreys marginals, unchanged), estimate
a correlation matrix among the transformed scores from each reference
class, then combine via the copula density formula (for a Gaussian
copula: a closed-form adjustment to the product of marginals, using only
the pairwise correlations, not a full joint density surface).

**Cost / middle ground.** Handles correlation via a genuinely
low-dimensional summary — for 3 features, only 3 pairwise correlations,
not an entire 2-D/3-D density surface (Option B) — so it should degrade
more gracefully than Option B at small n while still closing (not
merely restating) the joint-vs-product gap Option A leaves open. It adds
a distributional assumption that must be stated and checked: the copula
FAMILY (Gaussian, in the simplest case) is itself a modeling choice, not
a nonparametric fact. This is checkable, not merely assertable, against
this project's own simulator: `simulate.py`'s generative correlation
structure for the continuous features (`gis`, `sbs3`) is analytically
Gaussian-linked through the shared latent `Z` (`GIS = c + d*Z + Normal`,
`SBS3 = c + d*Z + Normal`, clipped) — so a Gaussian copula is a
defensibly well-matched, though still explicitly disclosed, assumption
*for this simulator specifically*. Whether that match extends to real
tumor data is a separate, unresolved question this simulator cannot
answer either way.

**Evidence that would favor it.** A demonstration (not yet performed by
this task) that a Gaussian copula fit to this simulator's own reference
sets reproduces `simulate.py`'s known analytic joint density reasonably
well — a cheap, well-posed check given the simulator's own Z-linked
construction, and a natural first follow-up if this option is pursued.
Favored as the pragmatic middle path if a disclosed, checkable
lower-dimensional correlation assumption is judged acceptable in exchange
for materially better small-n behavior than Option B.

**P07/P08 survival.** Survives unchanged (shared note above).

## Summary table

| option | closes the joint-vs-product gap? | small-n behavior vs. current | new assumption to disclose | P07/P08 survival |
|---|---|---|---|---|
| A. Keep + amend PROTOCOL.md | No — restates scope instead | Unchanged (no re-implementation) | None new | Unchanged |
| B. True multivariate density | Yes | Worse (curse of dimensionality; unevidenced at Track B n) | None new (still nonparametric) | Unchanged |
| C. Penalized logistic regression + prior-odds | Yes | Likely better than B (parametric); untested here | Prior-odds conversion re-risked; no in-repo regression test found | Unchanged |
| D. Gaussian copula | Yes | Likely better than B (3 correlations, not a full surface) | Copula family (checkable against this simulator specifically) | Unchanged |

No option is chosen here. Standing Rule 10.
