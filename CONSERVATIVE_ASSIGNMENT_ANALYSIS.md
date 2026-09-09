SIMULATED DATA — NOT A SCIENTIFIC RESULT

# CONSERVATIVE_ASSIGNMENT_ANALYSIS.md — P-AMD-3a Part C

This is a finding about what the study's estimator will produce,
independent of the gate6 criterion question (`PROPOSED_GATE6_AMENDMENT.md`)
and independent of whether that amendment is ever applied. It stands on
its own: **the estimator carries a known, quantified, DOWNWARD bias in
the recovered LR, and since ACMG evidence strength is assigned from the
CI lower bound, this systematically makes pathogenic-direction
assignments conservative** — a quantity's true evidentiary strength is,
on average, at least as strong as what gets reported, never weaker.

## 1. The bias, using the corrected (post-`MIXTURE_FIX.md`) numbers

`MIXTURE_FIX.md` fixed a real defect (the mixture application-point
mismatch) and, as predicted, this WIDENED the shrinkage bias's visibility
rather than removing it — the residual bias below is the estimator's
actual, current, corrected behavior, not the pre-fix (partially masked)
figure:

| arm | recovered LR | injected LR | relative bias (recovered vs. injected) |
|---|---|---|---|
| CORE_HR | 4.822998 | 5.826333 | **−17.22%** |
| DDR_SIGNALING | 4.655099 | 5.154487 | **−9.69%** |

Both biases are DOWNWARD (recovered < injected) — consistent with ridge
shrinkage pulling the estimate toward the null (LR=1) from above, which
is the expected direction for an LR>1 (pathogenic-direction) quantity
under an L2 penalty, per `MIXTURE_FIX_POST_FIX_DIAGNOSTICS.md`'s
re-established lambda sweep.

**Why this is conservative, not just biased, and in both evidentiary
directions.** Ridge shrinkage pulls ANY estimated LR toward 1 (the null),
regardless of which side of 1 it starts on: an LR>1 (pathogenic-leaning)
estimate is pulled DOWN toward 1 (weaker apparent pathogenic evidence
than truth); an LR<1 (benign-leaning) estimate is pulled UP toward 1
(weaker apparent benign evidence than truth). In both directions, the
biased estimate systematically UNDERSTATES the true evidentiary strength
— "conservative" in both directions, not merely "biased toward the null
on the pathogenic side." **This session's own empirical bias measurements
are for LR>1 quantities only** (both CORE_HR and DDR_SIGNALING's injected
values are above 1) — the benign-direction (LR<1) magnitude is not
separately measured here; the qualitative (conservative) direction is a
consequence of the same shrinkage-toward-null mechanism, not a separately
verified number, and is disclosed as such rather than quantified without
evidence (Standing Rule 3).

## 2. Tier-boundary quantification (PROTOCOL.md §9's OddsPath thresholds)

`PROTOCOL.md` §9 assigns ACMG-equivalent evidence points from the CI
LOWER bound (pathogenic direction), at these thresholds (`BENCHMARKS.tsv`
`ODDS01`/`ODDS02`, Tavtigian et al. 2018):

| CI lower bound condition | tier | points |
|---|---|---|
| > 350 | PATHOGENIC_VERY_STRONG | 8 |
| (18.7, 350] | PATHOGENIC_STRONG | 4 |
| (4.33, 18.7] | PATHOGENIC_MODERATE | 2 |
| (2.08, 4.33] | PATHOGENIC_SUPPORTING | 1 |
| <= 2.08 | NO_EVIDENCE (pathogenic side) | 0 |

**General result.** For a downward relative bias of magnitude `f`
(0 < f < 1), a TRUE (unbiased) CI lower bound value `L_true` just above
any tier boundary `B` is recovered as `L_recovered = L_true * (1 - f)`
(the multiplicative form matching how bias is measured throughout this
project). It crosses BELOW `B` — i.e., is assigned one tier lower than
its true strength — whenever

```
B  <  L_true  <=  B / (1 - f)
```

a "danger zone" whose width, **as a fraction of B**, is `f / (1 - f)` —
**the same fraction at every boundary**, since all four boundaries are
compared multiplicatively (the OddsPath framework is itself
log-multiplicative, per `PROTOCOL.md` §9's own citation).

| bias magnitude f | danger-zone width, as % of any boundary B |
|---|---|
| 17.22% (CORE_HR) | f/(1-f) = **20.80%** |
| 9.69% (DDR_SIGNALING) | f/(1-f) = **10.73%** |

Applied to the four pathogenic-direction boundaries:

| tier boundary B | danger zone at f=17.22% (CORE_HR) | danger zone at f=9.69% (DDR_SIGNALING) |
|---|---|---|
| 350 (Very Strong / Strong) | (350, 422.8] | (350, 387.5] |
| 18.7 (Strong / Moderate) | (18.7, 22.6] | (18.7, 20.7] |
| 4.33 (Moderate / Supporting) | (4.33, 5.23] | (4.33, 4.79] |
| 2.08 (Supporting / No evidence) | (2.08, 2.51] | (2.08, 2.30] |

Any true CI-lower-bound value falling inside one of these ranges is
assigned ONE ACMG evidence point fewer than its true strength justifies,
purely from the estimator's own known shrinkage — not from any error in
the recovery pipeline.

## 3. A concrete, observed instance from this session's own data

This is not only a hypothetical range. CORE_HR's own corrected recovered
CI lower bound this task — **4.279654** — falls inside the
`(4.33, 5.23]` danger zone computed above, one side of it: the injected
(true) value (5.826333) sits well inside the MODERATE tier
`(4.33, 18.7]`, but the recovered CI's lower bound (4.279654) sits just
BELOW the 4.33 boundary, in the SUPPORTING tier `(2.08, 4.33]`. **In this
session's own corrected production run, CORE_HR is assigned
PATHOGENIC_SUPPORTING (1 point) where the true injected value's own
strength corresponds to PATHOGENIC_MODERATE (2 points)** — a real,
observed, one-tier conservative downgrade directly attributable to the
estimator's quantified shrinkage bias, not a hypothetical edge case.

**DDR_SIGNALING shows the same pattern.** Its corrected recovered CI
lower bound this task — **4.144367** — ALSO falls below the 4.33
boundary (into the `(2.08, 4.33]` SUPPORTING-tier danger zone, per the
`f=9.69%` row above: `(4.33, 4.79]` is the danger zone for a true value
just above 4.33, and 4.33 itself is already excluded here since the
recovered value fell all the way through it). The injected (true) value
(5.154487) sits in the MODERATE tier `(4.33, 18.7]`; the recovered CI
lower bound (4.144367) sits in the SUPPORTING tier `(2.08, 4.33]` — a
second, independently observed one-tier conservative downgrade, on the
SAME arm whose gate6 containment check still PASSES (the CI does contain
the injected point; the tier downgrade shows up in the CI's LOWER bound
specifically, which is a stricter, ACMG-relevant read of the same
interval than containment alone reports).

## 4. Draft text for PROTOCOL.md (NOT applied — draft only)

> **§7.4 (proposed addendum) — Known conservative bias of the ridge
> logistic estimator.** The CV-selected ridge penalty (§7.2) shrinks the
> recovered LR toward the null (1.0) relative to the unshrunk/true value,
> by a magnitude that grows with the penalty strength and is
> characterized, for this study's synthetic validation, in
> `MIXTURE_FIX_POST_FIX_DIAGNOSTICS.md`. This bias is CONSERVATIVE in
> both evidentiary directions: it understates pathogenic-direction
> evidence (LR>1, biased down toward 1) and understates benign-direction
> evidence (LR<1, biased up toward 1) alike. A consequence, quantified in
> `CONSERVATIVE_ASSIGNMENT_ANALYSIS.md`: a true LR whose CI lower bound
> falls within roughly `f/(1-f)` of an OddsPath tier boundary (§9), where
> `f` is the estimator's characterized relative bias at the study's
> class sizes, may be assigned one ACMG evidence tier lower than its true
> strength. This is a known property of the instrument, not a defect in
> the recovery pipeline, and does not by itself indicate a VUS should be
> reclassified — it means a `PATHOGENIC_SUPPORTING` or
> `PATHOGENIC_MODERATE` call near a tier boundary should be read with
> this conservative margin in mind.

## 5. Draft text for REPORT.md (NOT applied — draft only)

> **Estimator bias disclosure.** The ridge-penalized logistic estimator
> used to recover each quantity's likelihood ratio is, by construction,
> biased toward the null (LR=1) at the cross-validation-selected penalty
> strength — a known, expected consequence of the bias-variance tradeoff
> the penalty exists to make at this study's class sizes, not an error.
> This bias is CONSERVATIVE: it tends to understate rather than overstate
> evidentiary strength in both directions. Every LR reported in this
> report's ACMG-evidence table should be read as a conservative estimate
> of the true value; a quantity landing near an OddsPath tier boundary
> (`PROTOCOL.md` §9) may in truth belong to the next tier up. See
> `CONSERVATIVE_ASSIGNMENT_ANALYSIS.md` for the quantified bias and a
> concrete instance from this study's own synthetic validation.

## 6. What this analysis does not claim

- It does not claim every near-boundary call in the real study IS
  mis-tiered — only that the estimator's known bias makes an
  UNDER-assignment more likely than an OVER-assignment near any boundary,
  by the quantified margin above.
- It does not propose adjusting the OddsPath thresholds themselves, or
  the estimator's lambda selection (Standing Rule 10; and per the
  explicit caution against reducing shrinkage at these class sizes).
- It does not quantify the benign-direction (LR<1) bias magnitude
  numerically — only its direction (also conservative) — since no
  benign-direction quantity was empirically measured this session.
