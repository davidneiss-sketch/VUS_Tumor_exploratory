SIMULATED DATA — NOT A SCIENTIFIC RESULT

# MIXTURE_FIX.md — P-AMD-3a Part A: fixing the mixture application point

This is a real defect, fixed regardless of any gate6 criterion decision
(that decision is Part B, drafted separately in
`PROPOSED_GATE6_AMENDMENT.md`, not applied). `RESIDUAL_DIAGNOSIS.md`
(P-DIAG-1) found: production weights per-subtype LRs
(`Sigma_s w_s * LR_s`); `simulate.py`'s `compute_truth_quantities()`
weights per-subtype densities and then divides
(`[Sigma_s w_s * f(x|Path,s)] / [Sigma_s w_s * f(x|Benign,s)]`). These are
different operations, confirmed to differ by +6.1% (CORE_HR) / +9.3%
(DDR_SIGNALING) in isolation, computed purely analytically from
`simulate.py`'s own exact generative functions. That this currently
offsets (rather than compounds) the separate ridge-shrinkage bias is
luck of the sign, not a property of the construction — the sign depends
on subtype composition and effect-size heterogeneity across subtypes,
which will differ on real Track B data.

## 1. Which operation is correct, and why

The task's own instruction: *"Weighting densities then dividing is the
mathematically correct construction of a pooled likelihood ratio over
strata; weighting LRs is not, and the choice should be justified on that
basis rather than on which one is easier to change."* This section
proves that claim for this specific model, rather than asserting it.

**Claim:** given this simulator's own generative structure, the
density-mixture construction

```
Sigma_s w_s * f(x|Path,s)  /  Sigma_s w_s * f(x|Benign,s)      (density-mixture, "correct")
```

is **exactly equal** to the subtype-marginal (pooled, subtype-blind)
joint likelihood ratio `f(x|Path) / f(x|Benign)` — i.e., the LR you would
estimate by fitting a model on `x` alone, with subtype **not** included
as a covariate at all.

**Proof.** By the law of total probability, for any class `c` (Path or
Benign):

```
f(x|c) = Sigma_s  P(subtype=s | c)  *  f(x|c, subtype=s)
```

This holds for ANY joint distribution of `(X, subtype, class)` — it is
just conditioning on subtype and summing out. If `w_s = PAM50_PROPORTIONS[s]`
equals `P(subtype=s | Path)` **and** equals `P(subtype=s | Benign)` — i.e.
subtype is marginally independent of true pathogenicity class — then
substituting `w_s` for `P(subtype=s|c)` in the identity above gives,
for both classes simultaneously:

```
f(x|Path)   = Sigma_s w_s * f(x|Path, s)
f(x|Benign) = Sigma_s w_s * f(x|Benign, s)
```

Dividing: `f(x|Path)/f(x|Benign) = [Sigma_s w_s f(x|Path,s)] / [Sigma_s w_s f(x|Benign,s)]`
— exactly the density-mixture construction. QED, **conditional on the
independence assumption**.

**The independence assumption is verified, not assumed, for this
simulator.** `simulate.py`'s `_emit_sample()` (the sample generator) draws:

```python
subtype = rng.choices(list(PAM50_PROPORTIONS), weights=list(PAM50_PROPORTIONS.values()))[0]
```

BEFORE `cls` (`Pathogenic`/`Benign`) enters any downstream computation,
and this draw does not depend on `cls` in any way — the SAME
`PAM50_PROPORTIONS` weights are used regardless of which class the
calling loop is currently generating. `cls` only enters later, via
`Z_MEAN[arm][cls]` in the latent-variable draw
(`z = rng.gauss(Z_MEAN[arm][cls] + SUBTYPE_Z_SHIFT[subtype], Z_SD)`) —
subtype shifts `z`'s mean **additively and identically regardless of
class** (a confound on the observed features, not a channel by which
class affects subtype assignment). This confirms, by direct inspection
of the generative code (not inference from downstream statistics):
`P(subtype=s | Pathogenic) = P(subtype=s | Benign) = PAM50_PROPORTIONS[s]`
exactly, for every subtype `s`, by construction.

**Consequence for the fix.** The density-mixture target
`f(x|Path)/f(x|Benign)` should therefore be estimated **directly**, by
fitting a ridge logistic model on the pooled population with subtype
**omitted** from the design (no subtype dummy columns), rather than by
combining five separate per-subtype-conditional fits. This is not merely
"easier" — Section 2 shows the per-subtype-combination route is not
achievable at all without an additional, unverifiable assumption, while
the subtype-blind fit recovers the target directly and exactly (up to
ordinary finite-sample/model-form error, quantified in Section 5).

## 2. Why per-subtype LR values cannot be correctly recombined into the density mixture

A natural first instinct (the one this codebase's prior revision used)
is: fit the model WITH subtype as a covariate (informative, potentially
more efficient per-subtype), get per-subtype LRs `LR_s(x) = f(x|Path,s)/f(x|Benign,s)`,
then combine them into the density mixture some other, correct way.
This does not work, for a reason specific to what a **discriminative**
model can identify:

`predict_proba` estimates `P(Path | x, subtype=s)`, from which (via the
prior-odds correction) only the **ratio** `LR_s(x)` is identifiable per
subtype. The density-mixture combination needs

```
Sigma_s w_s * f(x|Path,s)  /  Sigma_s w_s * f(x|Benign,s)
= [weighted average of LR_s(x), weighted by  w_s * f(x|Benign,s)]
```

— which requires `f(x|Benign,s)` **individually**, comparable in scale
across subtypes, not just the per-subtype ratio `LR_s(x)`. A
discriminative model conditioned on `x` and `subtype` is invariant to
rescaling the covariate-marginal density `g_s(x) = f(x,subtype=s)`
(pooled over class) at any fixed `(x,s)` — multiplying `g_s(x)` by any
positive constant leaves `P(Path|x,s)` unchanged, since it appears
identically in both the numerator and denominator of the class-posterior.
This means `g_s(x)`, and hence `f(x|Benign,s)` on a scale comparable
across `s`, is **not identified** by a discriminative fit at all,
regardless of sample size — this is a structural property of
discriminative models, not a fixable implementation gap. (This point was
first raised, not yet acted on, in `RESIDUAL_DIAGNOSIS.md` section 2.)

The subtype-blind fit sidesteps this entirely: it never needs
`f(x|Benign,s)` individually, because Section 1's identity shows the
TARGET itself, once you substitute the independence assumption, no
longer depends on any subtype-specific density at all — only on the
pooled `f(x|Path)`/`f(x|Benign)`, which a subtype-blind discriminative
fit on the pooled population estimates directly, using the SAME
prior-odds-correction logic already implemented, unmodified, in
`logistic_estimator.py`'s `probability_to_lr`.

## 3. Implementation

`production_v2_run.py` (not "the estimator" — its own module docstring
states it implements "the mixture-evaluation and CV-selection logic
itself, calling [`logistic_estimator.py` and `simulate.py`'s] existing,
unmodified functions"; this fix stays inside that boundary):

- `build_subtype_blind_design_row` / `build_subtype_blind_design_matrix` /
  `eval_point_subtype_blind_design_row`: the SAME feature set
  (`le.CONTINUOUS_FEATURES` + `le.BINARY_FEATURES`, standardized via
  `le.standardize_params`, unmodified), with the subtype-dummy columns
  omitted.
- `select_lambda_cv_subtype_blind`: `le.select_lambda_cv`'s exact
  algorithm, re-implemented against this design (`le.select_lambda_cv`
  itself cannot be reused unmodified, since it hardcodes
  `le.build_design_matrix`'s subtype-including design internally) —
  reuses `le.make_folds`, `le.fit_ridge_logistic`, `le.predict_proba`,
  `le.deviance` exactly as-is.
- `mixture_point_estimate`: now the subtype-blind fit's
  prior-odds-corrected LR at `EVAL_POINT` — this **is** the estimand
  proven equal to the density mixture in Section 1, not an
  approximation.
- `bootstrap_ci_mixture`: unchanged in structure (patient-clustered =
  sample-grouped bootstrap, per `logistic_estimator.py`'s own docstring),
  refits the subtype-blind design per replicate.
- `mixture_point_estimate_legacy_lr_weighted`: the OLD (P-AMD-2,
  deficient) LR-weighted computation, kept ONLY for the before/after
  comparison in Section 5 below — not called by `main()`.
- The subtype-COVARIATE fit is still run and reported
  (`per_subtype_lr_report`, `SIMULATED_PER_SUBTYPE_LR.tsv`) as
  **informational** output only (a genuinely interpretable per-subtype
  relative-risk estimate in its own right) — it no longer feeds the
  gate6 estimand.

`logistic_estimator.py`, `simulate.py`, `PROTOCOL.md`, and every gate
file are unmodified — confirmed via `git diff` in the acceptance check.

## 4. Verification: does the fix actually remove the application-point inflation?

Computed live this task (not asserted): refitting the subtype-blind
design at near-zero lambda (lambda=0.001, where ridge shrinkage is
negligible) and comparing against `simulate.joint_lr_collapsed` (the
exact, noise-free truth density-mixture value):

| arm | near-zero-lambda subtype-blind LR | exact truth (density-mixture) | relative bias |
|---|---|---|---|
| CORE_HR | 6.1799 | 5.826333 | **+6.07%** |
| DDR_SIGNALING | 5.9731 | 5.154487 | **+15.88%** |

Compare against the OLD (LR-weighted, P-AMD-2) computation's own
near-zero-lambda bias, from `residual_diagnosis/SIMULATED_LAMBDA_SWEEP.tsv`
(P-DIAG-1): **+24.91% (CORE_HR) / +28.90% (DDR_SIGNALING)**.

The CORE_HR near-zero-lambda bias falls from +24.91% to +6.07% — closely
tracking (not exactly matching, since the empirical fit carries its own
finite-sample/model-form noise on top of the pure analytic effect) the
+6.10% application-point effect `RESIDUAL_DIAGNOSIS.md` isolated
analytically. DDR_SIGNALING's residual near-zero-lambda bias (+15.88%)
is larger than its own isolated application-point effect (+9.28%) — the
remaining gap is ordinary logistic-model-form error against the true
generative process's Simpson-integrated latent-Z structure (which a
model linear in log-odds can only approximate), not an application-point
artifact, and not itself attributed further by this task (out of scope
for Part A, which fixes the application point specifically).

**In both cases, the fix substantially and correctly removes the
application-point inflation this task set out to fix.**

## 5. Before / after: the containment gap widens, as expected

"Before" is the actual, committed, pre-fix `production_v2/` output
(preserved unmodified at
`mixture_fix/pre_fix_production_v2_snapshot/SIMULATED_RECOVERED.tsv`,
copied before this fix's `production_v2_run.py` re-run overwrote it —
not recomputed, since the CV-selection RNG stream changes once an extra
selection call is added, so an exact re-derivation of the old numbers
from the current code is not meaningful; the committed artifact is the
authoritative record of the pre-fix run).

| arm | recovered point | CI | relative bias | CI contains injected? |
|---|---|---|---|---|
| CORE_HR (BEFORE, legacy LR-weighted) | 5.041024 | [4.480710, 5.773397] | −13.48% | NO (miss 0.0529) |
| CORE_HR (AFTER, corrected subtype-blind) | 4.822998 | [4.279654, 5.496457] | −17.22% | NO (miss 0.329876) |
| DDR_SIGNALING (BEFORE, legacy LR-weighted) | 4.831241 | [4.295171, 5.477147] | −6.27% | YES |
| DDR_SIGNALING (AFTER, corrected subtype-blind) | 4.655099 | [4.144367, 5.301606] | −9.69% | YES |

Injected values (unchanged, `SIMULATED_TRUTH.tsv`): CORE_HR 5.826333,
DDR_SIGNALING 5.154487.

**This widening is the correct, expected outcome, not a regression.**
The old computation's downward shrinkage bias was being partially
masked by an upward application-point artifact of the wrong statistical
operation; removing that artifact necessarily makes the pure shrinkage
bias more visible, not smaller. Standing Rule 2 governs how this is
reported: a wider gap that reveals a real, quantifiable estimator
property is not a failure of this fix — presenting it as anything other
than "expected and correct" would itself be the kind of narrative-spin
Standing Rule 2 forbids.

## 6. Re-established shrinkage attribution (post-fix lambda sweep + seed variation)

Per this task's explicit instruction ("so the shrinkage attribution is
re-established on the corrected computation"), P-DIAG-1's STEP 1/STEP 3/
STEP 4 diagnostics are re-run against the corrected computation, written
to `mixture_fix/` (separate from `production_v2/` and from
`residual_diagnosis/`, which remains P-DIAG-1's untouched historical
record):

- `mixture_fix_lambda_sweep.py` -> `mixture_fix/SIMULATED_LAMBDA_SWEEP_POST_FIX.tsv`
- `mixture_fix_seed_variation.py` -> `mixture_fix/SIMULATED_SEED_VARIATION_POST_FIX.tsv` (+ summary)

Results: `MIXTURE_FIX_POST_FIX_DIAGNOSTICS.md`.
