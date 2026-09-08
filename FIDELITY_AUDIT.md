SIMULATED DATA — NOT A SCIENTIFIC RESULT

# P06R3 fidelity audit: analytic truth vs. generative distribution, every feature

SIMULATED: this audits every feature that enters `compute_truth_quantities()` —
SBS3 exposure, LOH (WT-lost) direction, GIS score, and the shared latent
HR-deficiency variable Z — for divergence between the distribution the
analytic truth formula assumes and the distribution `_emit_sample()` actually
draws from, including every clip, floor, ceiling, truncation, rounding, and
discretization applied between the draw and the emitted value. This was
triggered by P08-RERUN's finding of an apparent clipping-induced mismatch in
the SBS3 feature; per this task's Step 1 instruction, nothing else had been
checked, so this audit does not assume the defect is SBS3-specific and does
not assume it is real until re-verified.

**Headline finding, stated up front because it changes the shape of the rest
of this task**: re-verifying P08-RERUN's SBS3 finding with a more rigorous
test (exact-CDF binomial testing across multiple window widths, instead of a
narrow-window point-density approximation) shows **the finding does not
replicate**. Clipping is a measure-preserving identity map on the open
interval between the clip bounds: it cannot alter the continuous density
there, only concentrate the excluded tail mass into a point mass exactly at
the boundary. `EVAL_POINT["sbs3"] = 0.30` sits strictly interior to
`[0, 0.95]` for every class in every arm (0.21–1.94 SD from the relevant
class means — see §2), so the pre-P06R3 analytic formula was **already
exact** there. P08-RERUN's "44%/76% achievable-LR gap" is attributed to a
windowed-histogram measurement artifact: it tested only w ∈ {0.01, 0.02,
0.03, 0.05}, a range narrow enough that CORE_HR Benign's particular sampling
noise (n≈17–77 in-window counts) happened to lean the same direction across
all four; a wider window (w=0.10, n≈196) reverses the direction (§3). None
of the four features carries a real analytic-vs-generative mismatch AT THE
EVALUATION POINTS THIS PROJECT ACTUALLY USES. See §7 for what is and is not
implied by this.

## 1. Method

For each (feature, arm, class) combination (n=1848 samples/class/arm, the
current committed `simulate.py` population, arms CORE_HR / DDR_SIGNALING /
NULL_ARM):

- **Categorical (WT_LOST direction) and Gaussian-marginal (GIS, latent Z)
  features**: compare the analytic mean/probability/sd against the sample
  mean/proportion/sd, using the analytic distribution's own standard error to
  compute a z-score. |z| > ~2 on an isolated test would be notable; with 18
  comparisons total across this audit, 0–1 such values are expected by chance
  at α≈0.05 and are not evidence of a defect.
- **SBS3 (the one feature with a real clip in the generator)**: two
  complementary checks — (a) the boundary point-mass fraction (exact zeros)
  compared against the analytic `Phi()`-predicted clip probability, which
  *should* match closely since this is exactly what clipping predicts; (b)
  the **exact-CDF interior-window test**: for a window `[a,b]` fully inside
  `(0, 0.95)`, `P(sbs3 in [a,b])` under the (correctly unclipped-marginal)
  analytic model is `Phi((b-mean)/sd) - Phi((a-mean)/sd)` exactly — this is
  the exact probability, not the point-density-times-width approximation
  P08-RERUN used, which has its own bias at anything but vanishingly small
  w. Comparing the resulting expected count against the observed count with
  a binomial z-score, across w ∈ {0.02, 0.05, 0.10, 0.15}, is materially more
  powerful and materially less biased than the prior narrow-window scan.

## 2. Feature-by-feature table

| feature | analytic distribution | generative distribution | clip/floor/ceiling/rounding between draw and emitted value | match at the point/region this project evaluates? | divergence magnitude |
|---|---|---|---|---|---|
| **WT_LOST direction** | `P(WT_LOST=1\|class) = Phi((a+b·muZ)/sqrt(1+b²))` (exact Gaussian-probit convolution identity; `marginal_wt_lost_prob()`) | `p_wt_lost = Phi(a+b·z)`, `z~Normal(muZ,1)`, then a genuine Bernoulli draw (`rng.random() < p_wt_lost`) — `simulate.py:442-448` | **none**. `Phi()`'s domain is all of ℝ; the Bernoulli draw itself has no clip, floor, or rounding | **YES**, exactly (closed form, not an approximation) | none. z-scores across 6 (arm,class) cells: -2.04, 0.01, -0.15, -1.21, 0.43, -0.26 — all within sampling noise (max \|z\|=2.04 of 6 tests) |
| **GIS score** | `Normal(c+d·muZ, sqrt(d²+sigma²))` (`marginal_gaussian_feature_params()`) | `gis = c + d·z + Normal(0,sigma)` — `simulate.py:633` | **none**. No `min`/`max`/`round` applied to the value used for any density computation (`round(gis,4)` is applied only when writing `SIMULATED_sample_metadata.tsv` for display, a rounding of ≤5e-5 relative magnitude, immaterial) | **YES**, exactly (sum of two independent Gaussians is exactly Gaussian; unclipped) | none. z-scores on the mean across 6 cells: 0.68, -0.30, 0.09, -1.11, -0.73, -0.27 — all within sampling noise. Empirical range extends below 0 (e.g. DDR_SIGNALING Benign: [-17.06, 70.36]) confirming no floor is applied either analytically or generatively — consistent, not a mismatch, though a biologically-motivated floor at 0 would be a separate, deliberate future design choice, not a fidelity bug |
| **SBS3 exposure** | `Normal(c+d·muZ, sqrt(d²+sigma²))`, evaluated as a continuous density (pre-P06R3: `phi_pdf`; post-P06R3: `sbs3_clipped_density`, see §4) | `sbs3 = min(0.95, max(0.0, c + d·z + Normal(0,sigma)))` — clipped, `simulate.py:696` (constants now named `SBS3_CLIP_LO=0.0`, `SBS3_CLIP_HI=0.95`) | **real clip** to `[0.0, 0.95]`. This creates point mass exactly at 0.0 (substantial: 1–42% depending on class, see below) and negligible point mass at 0.95 (<0.001% every class — no class mean sits anywhere near the upper bound) | **YES at the evaluation points this project actually uses** (`EVAL_POINT["sbs3"]=0.30`, and the whole windowed region tested, §3) — because clipping is measure-preserving on the open interior and 0.30 is interior for every class (0.21–1.94 SD from the class mean). **NO at the boundary itself** — a plain continuous-density evaluation at x=0 or x=0.95 would be wrong; see §4 for the fix that makes this a non-issue rather than a latent trap | Interior (x=0.30): none — see §3's z-scores, all \|z\|≤2.05 across 4 window widths × 6 (arm,class) cells, no directional pattern that survives a wider window. Boundary (x=0.0): real and large for classes whose mean sits near 0 — CORE_HR Benign observed 42.15% vs. Phi-predicted 41.76% (Δ=0.39pp); DDR_SIGNALING Benign observed 23.38% vs. predicted 23.98% (Δ=0.60pp); full table below |
| **latent Z (HR-deficiency variable)** | `Normal(muZ, 1)` per (arm, class) — the model's own defining assumption, not derived from anything else | `z = rng.gauss(Z_MEAN[arm][cls], Z_SD)` — `simulate.py:614`, drawn once per sample and shared across all 3 downstream features | **none**. Stored to 6 decimal places in `SIMULATED_sample_labels.tsv` (`round(z,6)`), immaterial rounding; no clip anywhere in the Z draw itself | **YES**, exactly (it's drawn directly from the distribution the analytic model assumes — there is nothing to diverge) | none. z-scores on the mean across 6 cells: 0.59, -0.11, 0.23, -0.35, -0.03, 0.14 — all within sampling noise; empirical sd all within [0.9917, 1.0120] of the analytic 1.0 |

### SBS3 boundary point-mass detail (obs vs. Phi-predicted, all n=1848)

| arm | class | mean | sd | observed P(sbs3=0) | Phi-predicted P(sbs3=0) | Δ (pp) |
|---|---|---|---|---|---|---|
| CORE_HR | Pathogenic | 0.3300 | 0.1442 | 0.0097 | 0.0111 | 0.14 |
| CORE_HR | Benign | 0.0300 | 0.1442 | 0.4215 | 0.4176 | 0.39 |
| DDR_SIGNALING | Pathogenic | 0.1840 | 0.1131 | 0.0503 | 0.0519 | 0.16 |
| DDR_SIGNALING | Benign | 0.0800 | 0.1131 | 0.2338 | 0.2398 | 0.60 |
| NULL_ARM | Pathogenic | 0.1200 | 0.1131 | 0.1412 | 0.1444 | 0.32 |
| NULL_ARM | Benign | 0.1200 | 0.1131 | 0.1439 | 0.1444 | 0.05 |

Every Δ is within 2 SE of sampling noise at n=1848 (SE of a proportion near
these values is ≈1.0–1.2pp) — the point-mass mechanism matches the analytic
`Phi()` prediction closely, confirming the generator behaves exactly as the
clipping model says it should. This table is included for completeness (the
divergence *would* matter if a quantity were ever evaluated at x=0), not
because it affects any currently-computed truth quantity.

## 3. Exact-CDF re-test of P08-RERUN's SBS3 finding

For each (arm, class) and window half-width w around `EVAL_POINT["sbs3"]=0.30`,
`exact_p = Phi((0.30+w−mean)/sd) − Phi((0.30−w−mean)/sd)` gives the *exact*
probability mass the analytic clipped-marginal model predicts inside the
window (not the point-density approximation). `expected_count = exact_p·n`,
compared against the actually-observed count via
`z = (observed − expected) / sqrt(n·p·(1−p))`:

| arm | class | w=0.02 | w=0.05 | w=0.10 | w=0.15 |
|---|---|---|---|---|---|
| CORE_HR | Pathogenic | z=1.01 | z=1.69 | z=1.03 | z=0.78 |
| CORE_HR | Benign | z=-1.64 | z=-1.70 | z=-1.09 | **z=-2.05** |
| DDR_SIGNALING | Pathogenic | z=-0.01 | z=-0.67 | z=0.70 | z=-0.09 |
| DDR_SIGNALING | Benign | z=-0.15 | z=0.78 | z=0.36 | z=-0.28 |
| NULL_ARM | Pathogenic | z=-0.49 | z=1.47 | z=0.29 | z=0.17 |
| NULL_ARM | Benign | z=-0.96 | z=0.33 | z=-1.53 | z=-1.50 |

24 tests total; the single largest deviation is CORE_HR Benign at w=0.15
(z=-2.05, a ~4% two-sided tail event, unremarkable among 24 comparisons at
α=0.05, where ~1 exceedance is expected by chance). **CORE_HR Benign does
lean consistently negative across all 4 widths** (z = -1.64, -1.70, -1.09,
-2.05) — this is the exact pattern P08-RERUN read as "sign never flips
across 4 window widths" and treated as evidence of a real, directional
defect. Under the rigorous exact-CDF test, none of these 4 values is
individually significant, and the pattern is fully consistent with one
noisy binomial proportion staying on the same side of its (correctly
specified) expectation across correlated, overlapping windows — overlapping
windows are not independent tests, so "consistent sign across 4 widths" is
much weaker evidence than it sounds. There is no arm/class combination where
the deviation is large *and* significant *and* the mechanism (proximity to
the clip boundary) is required to explain it — CORE_HR Pathogenic, whose
mean (0.33) is nowhere near either boundary, shows comparable-magnitude
z-scores (up to 1.69) to CORE_HR Benign, which is the pattern expected from
ordinary sampling variance, not from a boundary-driven analytic defect.

**Conclusion: the P08-RERUN Step 3 finding does not survive a properly
powered re-test. It was a real observation (the four narrow-window ratios
genuinely did lean the same direction in that sample) but not a real
defect** — see §7 for what should now happen to that finding's downstream
conclusions (P08-RERUN's HALT, ANALYTIC_VS_OBSERVED.md, PROPOSED_DEVIATIONS.md).

## 4. Why there is still a fix (§ "STEP 2" of this task)

Even though no currently-evaluated quantity is wrong, `compute_truth_quantities()`
computing a continuous density via `phi_pdf()` for a variable that is
*actually* clipped is a latent correctness trap: if `EVAL_POINT["sbs3"]`
were ever moved near or onto a clip boundary in a future task, the formula
would silently return a wrong (and un-normalizable) value with no warning.
`simulate.py` now defines `sbs3_clipped_density(x, mean, sd)`
(`simulate.py`, added near `marginal_gaussian_feature_params`), which:

- returns `(phi_pdf(x, mean, sd), "density")` for `x` strictly inside
  `(SBS3_CLIP_LO, SBS3_CLIP_HI)` — a closed form, not numerical integration,
  because the clip-is-identity-on-the-interior argument in §"Headline
  finding" makes the closed form exact there; no numerical integration is
  needed or used for this piece,
- returns `(Phi((SBS3_CLIP_LO-mean)/sd), "point_mass")` at or below the
  lower bound, and the symmetric upper-tail expression at or above the
  upper bound,
- tags every return with which of the two it is, and `sbs3_clipped_lr()`
  refuses (raises) to divide a density by a point mass or vice versa, so a
  future boundary-adjacent `EVAL_POINT` fails loudly instead of silently.

`joint_density()`'s per-Z sbs3 term now also calls this function (against
the conditional-on-Z mean `c+d·z`, sd `sigma`) rather than a bare
`phi_pdf`, by the same interior-identity argument applied pointwise for
every z. `SBS3_CLIP_LO`/`SBS3_CLIP_HI` are now named constants shared
between `_emit_sample()`'s draw and this function, replacing the previously
duplicated literals `0.0`/`0.95`, so the two cannot drift apart.

**This is the STEP 2 fix.** It is deliberately a hardening / correctness-
by-construction change, not a numeric correction — because §3 establishes
there is nothing to numerically correct at the current evaluation point.
See TRUTH_DELTA.md for the before/after values, which are confirmed
identical for every quantity except the two SBS3 exposure LR rows' free-text
`derivation` column (unchanged `injected_value`).

## 5. Scope note: what this audit did NOT find

This audit deliberately re-opened the possibility that GIS or LOH direction
carry the same defect as SBS3 (this task's explicit instruction: "do not
assume the defect is SBS3-specific"). They do not — neither is clipped,
floored, or otherwise transformed between the draw and the analytic
formula's assumption, confirmed both by code inspection (§2 table) and by
empirical z-tests (§2, all \|z\|<2.1 of 12 tests). **P07's gate6 pass and the
joint-vs-naive ratio do not rest on the SBS3 clipping mismatch**, because
(a) P07's own quantities (`*_wt_lost_direction_LR`) never touch SBS3 at all
(already established independently by P06R2's `P07_REVALIDATION_REQUIRED.md`),
and (b) the joint/product-of-marginals/ratio quantities, while they DO
include an SBS3 term, are numerically unaffected by the P06R3 fix (§4,
TRUTH_DELTA.md) since that term was already exact. See
REVALIDATION_REQUIRED.md for the formal per-task revalidation decision.

## 6. Method note: what this audit does not claim

This is not a claim that clipping is harmless in general, or that the SBS3
feature is unproblematic as a real-world estimation target — Task K/P08's
independent finding (NNLS instability recovering SBS3 exposure from mutation
catalogues at exome mutation counts, given SBS3's real ~0.79 cosine
similarity to SBS5) is untouched by this audit and remains a genuine,
separate estimator-side problem. This audit is narrowly about whether the
*analytic ground-truth formula* (`compute_truth_quantities()`) correctly
describes the *generative* distribution `_emit_sample()` draws from, at the
specific evaluation points this project actually uses — a question that is
entirely upstream of, and independent from, whether any real tool can
recover that ground truth from noisy catalogue data.

## 7. What this means for P08-RERUN's own conclusions

P08-RERUN's `ANALYTIC_VS_OBSERVED.md` §7 stated an explicit per-quantity
verdict: "CORE_HR NOT faithful ... a genuine P06 truth-definition defect,"
and used that finding to independently trigger this task's own HALT
condition ("if step 3 shows the analytic truth is not achievable from the
observed distributions"). This audit's more rigorous re-test overturns that
specific claim: CORE_HR's analytic truth **is** faithful to its generative
distribution at the point actually evaluated, on the same footing as
DDR_SIGNALING and NULL_ARM. P08-RERUN's own artifacts
(`ANALYTIC_VS_OBSERVED.md`, `PROPOSED_DEVIATIONS.md`,
`SIMULATED_signature_validation.md`) are left as the historical record of
that session's analysis and are **not** edited by this task (not in its
deliverable list, and rewriting another session's report after the fact
would itself violate the "never hand-patch a generated report" principle
this project applies elsewhere) — this document and REVALIDATION_REQUIRED.md
are the vehicle for the correction instead. The practical consequence: both
CORE_HR's and DDR_SIGNALING's gate6 FAILs (Task K / P08-RERUN) should now be
read as the **same kind of failure** — genuine SigProfilerAssignment
estimator instability at exome mutation counts (Task K/P08's original
"mechanism 2"), not a truth-definition artifact for one and an estimator
problem for the other. See REVALIDATION_REQUIRED.md.
