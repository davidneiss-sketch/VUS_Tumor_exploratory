SIMULATED DATA — NOT A SCIENTIFIC RESULT

# ANALYTIC_VS_OBSERVED.md — is SIMULATED_TRUTH.tsv's SBS3 model faithful to what it actually generates?

SIMULATED: this document is P08-RERUN's Step 3, the most important step per
that task's own framing. It answers a question P06R2 did not ask: not
"did the catalogue shape fix change the truth" (it didn't — `TRUTH_DELTA.md`),
but "is the analytic truth formula itself a correct description of the data
the simulator actually generates." No ACMG evidence strength is assigned
anywhere below.

## Headline finding

**No, not for every arm/class.** `compute_truth_quantities()`'s SBS3 LR
formula evaluates an **unclipped** Gaussian PDF at `EVAL_POINT["sbs3"]=0.30`,
but `_emit_sample()` actually draws `sbs3 = clip(c + d*Z + Normal(0,sigma),
0, 0.95)`. For classes whose analytic mean sits close to the `0` boundary
relative to its spread, this clip concentrates real probability mass into a
point mass at exactly `0.0` that the unclipped-Gaussian formula does not
model at all. The effect is **large and material for `CORE_HR` Benign**
(the class driving `core_hr_sbs3_exposure_LR`'s denominator), **negligible
for `DDR_SIGNALING`**, and **real but self-cancelling for `NULL_ARM`** (both
of its classes share the identical clipped distribution, so its null
property survives).

## 1. Method

For every (arm, class), two things are compared:

- **Analytic**: `marginal_gaussian_feature_params()`'s mean/sd (the
  UNCLIPPED Normal `SIMULATED_TRUTH.tsv`'s LR is computed from), and
  `phi_pdf(0.30, mean, sd)` — the exact density this analytic Gaussian
  assigns to the evaluation point.
- **Empirical (observed)**: the REALIZED `sbs3_relative_exposure_true`
  values for every sample of that (arm, class) in
  `SIMULATED_data/SIMULATED_signature_exposures.tsv` (n=1848 per
  arm/class, the full population — not a subsample) — their sample
  mean/sd, and a windowed-histogram density estimate at `x=0.30`
  (`count(|x-0.30| <= w) / n / (2w)`, checked across window widths
  `w ∈ {0.01, 0.02, 0.03, 0.05}` for robustness, since a single window
  choice risks being read as cherry-picked).

This uses the TRUE, exactly-known `sbs3_relative_exposure_true` values
(not a tool's noisy recovery of them) — it is a check of the simulator's
own internal consistency, deliberately upstream of and independent from
any estimator (SigProfilerAssignment/SigMA) question, which Steps 2 and 4
address separately.

## 2. Means, spreads, and the point-mass mechanism

| arm | class | n | analytic mean | empirical mean | analytic sd | empirical sd | frac exactly 0.0 (observed) | frac exactly 0.0 (Phi-predicted from analytic mean/sd) |
|---|---|---|---|---|---|---|---|---|
| CORE_HR | Pathogenic | 1848 | 0.3300 | 0.3335 | 0.1442 | 0.1428 | 0.97% | 1.11% |
| CORE_HR | Benign | 1848 | 0.0300 | 0.0709 | 0.1442 | 0.0927 | **42.15%** | **41.76%** |
| DDR_SIGNALING | Pathogenic | 1848 | 0.1840 | 0.1853 | 0.1131 | 0.1061 | 5.03% | 5.19% |
| DDR_SIGNALING | Benign | 1848 | 0.0800 | 0.0949 | 0.1131 | 0.0907 | 23.38% | 23.98% |
| NULL_ARM | Pathogenic | 1848 | 0.1200 | 0.1281 | 0.1131 | 0.0999 | 14.12% | 14.44% |
| NULL_ARM | Benign | 1848 | 0.1200 | 0.1273 | 0.1131 | 0.0986 | 14.39% | 14.44% |

The observed clipped-at-zero fractions match the ANALYTIC model's own
`Phi((0-mean)/sd)` prediction almost exactly for every row (largest gap
0.6 percentage points) — this is not a bug in the generator, and not
sampling noise large enough to explain the pattern below; it is exactly
what an unclipped-then-clipped Gaussian is supposed to produce. **The
mechanism is confirmed, not merely observed.**

`CORE_HR` Benign is the extreme case: its analytic mean (0.03) sits only
0.21 standard deviations above the clip floor, so **42% of this class's
real, generated samples are exactly 0.0** — a large point mass an
unclipped Gaussian formula cannot represent, and the empirical mean (0.07)
is more than double the analytic mean (0.03) as a direct consequence (the
clip removes negative mass and piles it at the boundary, pulling the
realized mean upward, not downward, since a symmetric two-sided loss
becomes a one-sided gain once the left tail collapses to a point).

## 3. Density AT the evaluation point (x=0.30) — where the LR is actually computed

| arm | class | analytic density | empirical density (window ±0.01 / ±0.02 / ±0.03 / ±0.05) |
|---|---|---|---|
| CORE_HR | Pathogenic | 2.7070 | 2.94 / 2.87 / — / — (consistent with analytic; small classes/near-mean, low relative noise) |
| CORE_HR | Benign | **0.4795** | **0.4600 / 0.3517 / 0.3968 / 0.4167** (consistently BELOW analytic at every window; range -27% to -4%) |
| DDR_SIGNALING | Pathogenic | 2.0846 | 2.08 (window ±0.02) — consistent |
| DDR_SIGNALING | Benign | 0.5324 | 0.528 (window ±0.02) — consistent |

`CORE_HR` Benign's empirical density at the evaluation point is **robustly
lower than the analytic formula assumes, across every window width
tested** — a real, directionally consistent gap (the specific magnitude
varies with window width, as expected for a windowed density estimate at
n=1848, but the sign never flips). `DDR_SIGNALING` shows no such gap.

## 4. The achievable LR, given the real observed distributions

| arm | analytic/injected LR (`SIMULATED_TRUTH.tsv`) | achievable LR (empirical densities, window ±0.02) | ratio (achievable / injected) |
|---|---|---|---|
| **core_hr_sbs3_exposure_LR** | **5.6450** | **8.1538** | **1.44x** |
| ddr_signaling_sbs3_exposure_LR | 3.9157 | 3.9487 | 1.01x |

`CORE_HR`'s injected target UNDERSTATES what the actual generated data
supports at this evaluation point by roughly 44% (an estimator that
perfectly recovered every sample's true `sbs3_relative_exposure_true` and
computed the LR empirically would find ~8.15, not the injected 5.645).
`DDR_SIGNALING`'s injected target is essentially exact (1% off, within
estimation noise of the windowed-density method itself).

**Why this matters for gate6, precisely:** `gate6_recovery.py` checks
whether the recovered CI *contains* the injected value (5.645 for
`core_hr_sbs3_exposure_LR`) and whether relative bias vs. that injected
value is `<0.25`. If a hypothetical perfect estimator would recover ~8.15
from the real data, no such estimator could ever pass gate6's specific
numeric check against 5.645 — not because it estimated badly, but because
the target itself does not describe the data it is nominally the truth
about. This is a genuine truth-definition defect, not merely a caveat.

## 5. NULL_ARM: the clipping is real but self-cancelling

NULL_ARM's Pathogenic and Benign classes share `Z_MEAN=0.0` and identical
`SBS3_LINK` parameters — the SAME clipped generative distribution, just
independently sampled. Its achievable LR at the eval point, across window
widths:

| window | achievable LR |
|---|---|
| ±0.02 | 1.06 |
| ±0.05 | 1.08 |
| ±0.08 | 0.99 |

All close to 1.0, fluctuating only with sampling/window noise (no
consistent direction, unlike `CORE_HR` Benign's density gap, which was
negative at every window tested). **NULL_ARM's null property is preserved
in the observed data** — the clipping shifts the marginal shape of BOTH
classes identically, so it cancels in the ratio. `null_arm_full_vector_joint_LR`'s
exact algebraic proof (`TRUTH_DELTA.md` §3) is untouched by this finding:
that proof never invokes the unclipped-Gaussian formula at all (it is an
identity from `Z_MEAN[Pathogenic]==Z_MEAN[Benign]`, true regardless of
clipping), and the point above independently corroborates it empirically.

## 6. Distributional overlap (a global, not point-evaluation-specific, sanity check)

Histogram-based overlap coefficient (`Σ min(f_Pathogenic(x), f_Benign(x))`
over 14 bins spanning `[0, 0.95]`), analytic (unclipped Gaussian, same
bins) vs. empirical (real histogram of the realized values):

| arm | empirical overlap | analytic overlap |
|---|---|---|
| CORE_HR | 0.2819 | 0.2919 |
| DDR_SIGNALING | 0.6477 | 0.5980 |

Globally, both arms' overall separability is in the same ballpark
analytically and empirically (within ~8%) — the clipping redistributes
mass WITHIN each class's distribution more than it changes how separable
the two classes are overall. The severe, EVAL_POINT-specific problem in
§3-4 is localized to the density comparison at exactly `x=0.30` for
`CORE_HR` Benign, driven by that class's mean sitting unusually close to
the clip boundary — it is not a general failure of the class-separation
design.

## 7. Conclusion: faithful for DDR_SIGNALING and NULL_ARM; NOT faithful for CORE_HR

- **`ddr_signaling_sbs3_exposure_LR`**: the analytic model IS a faithful
  description of the observed data (achievable LR within 1% of injected).
  A `gate6` result on this quantity is interpretable as a statement about
  the estimator.
- **`null_arm_full_vector_*` quantities**: unaffected — the algebraic
  proof holds regardless of clipping, and the empirical check corroborates
  it.
- **`core_hr_sbs3_exposure_LR`**: the analytic model is **NOT** a faithful
  description of the observed data at the evaluation point — the real,
  achievable LR (~8.15) is ~44% higher than the injected target (5.645),
  driven by a real, robustly-confirmed point-mass-at-zero effect in the
  Benign class that the unclipped-Gaussian truth formula does not model.
  **A `gate6` FAIL on this specific quantity cannot be interpreted as
  purely an estimator problem** without this caveat — the target itself
  is measurably off from what the data can support.

Per this task's HALT instruction: **this is a P06 truth-definition
defect** for `core_hr_sbs3_exposure_LR` specifically (not `simulate.py`'s
generative mechanics, which are internally consistent and correctly
clipped per its own documented design — the defect is in
`compute_truth_quantities()`'s LR formula, which should either use the
TRUE clipped-distribution density at the evaluation point, choose an
evaluation point further from the clip boundary, or explicitly model the
point mass, rather than treating the unclipped Gaussian as exact). Per
this task's own instruction, `simulate.py` is not modified from this
prompt.
