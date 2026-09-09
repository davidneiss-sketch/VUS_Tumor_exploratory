SIMULATED DATA — NOT A SCIENTIFIC RESULT

# INTERVAL_INSTABILITY_V2.md — the new estimator's small-n behavior, by feature-vector dimension

SIMULATED: this re-runs `INTERVAL_INSTABILITY.md`'s sweep
(`interval_instability_sweep.py`) against `logistic_estimator.py` (the
new ridge-logistic estimator), via `interval_instability_sweep_v2.py`.
Full data: `SIMULATED_INTERVAL_INSTABILITY_SWEEP_V2.tsv` (72 rows). Does
not modify `PROTOCOL.md`, `simulate.py`, `logistic_estimator.py`, or the
old sweep script/report — `INTERVAL_INSTABILITY.md` remains the record
of the OLD estimator's behavior, unedited.

## Method (same n-grid as the old sweep, reduced repeat/bootstrap count, disclosed)

Same 12 class sizes (n=12-160/class), same 2 arms, same 3
feature-subset "dimensions" as `INTERVAL_INSTABILITY.md`.
`R_REPEATS=8` (reduced from the old sweep's 15) and `B_SWEEP=100`
(reduced from the old sweep's 300) for tractability in pure-Python ridge
logistic regression across 2×3×12×8 = 576 trials — disclosed, not
silent (Standing Rule 4). **This reduction genuinely widens the
sampling noise on every fraction reported below** (a single trial flip
at R=8 is a 12.5-percentage-point swing, vs. 6.7 points at the old
sweep's R=15) — read the per-cell fractions with that in mind; they are
noisier than the old sweep's own numbers, not more precise.

**What "dimension" means here differs structurally from the old sweep,
disclosed rather than glossed over**: the old, product-of-marginals
estimator's "dimension 1" fit ONLY a single feature (SBS3 alone) — a
true reduction in model complexity. The new estimator's model is
ALWAYS the full 9-parameter regression (`PROPOSED_PROTOCOL_AMENDMENT.md`
specifies purity, subtype, and WGD as mandatory covariates, not
optional) — so "dimension" here means which of the 3 EVIDENTIARY
features carry real, sample-to-sample variation, with the other
evidentiary feature(s) held at a fixed, uninformative constant (not
included at all). This is a reasonable analogy to the old sweep's
intent, not an identical experiment — **the new estimator's parameter
count does not shrink with "dimension" the way the old one's did**, and
that is likely part of why the clean "richer feature set -> more stable"
pattern `INTERVAL_INSTABILITY.md` Headline finding 4 reported for the OLD
estimator does not repeat as cleanly below.

## Finding 1 — the density-underflow failure mode is GONE, exactly as anticipated

**`n_estimator_error` (this sweep's equivalent of the old sweep's
`ZERO_DENSITY_UNDEFINED`) is 0 across all 576 trials, every arm,
dimension, and n value.** Ridge logistic regression has no density to
underflow — `sigmoid()` is mathematically bounded in `(0,1)` for any
finite linear predictor, and ridge's own regularization keeps the fitted
coefficients (and therefore the linear predictor) bounded even at the
smallest n tested (n=12/class). This is a genuine, structural
improvement over the old estimator's own small-n failure mode
(`ESTIMATOR_SPECIFICATION_AUDIT.md` STEP 4a), not a tuning artifact —
this task's own framing anticipated exactly this ("Logistic regression
has no density to underflow, so the small-n behaviour should differ"),
and the data confirms it cleanly.

## Finding 2 — informativeness is STILL a real limitation at small-to-mid n, not solved by the estimator swap alone

**This is reported plainly, per Standing Rule 2 — the estimator swap
fixes the UNDEFINED failure mode, it does not by itself make small-n
intervals informative.** First n (in the tested grid) at which
`not_usable_fraction` (now purely `UNINFORMATIVE` — no more
`ZERO_DENSITY_UNDEFINED` split, so this is directly the fraction of
gate8-rejected intervals) drops to ≤0.5 (a majority-informative
threshold), and the fraction at the largest tested n=160:

| arm | dimension | first n with ≤50% UNINFORMATIVE | UNINFORMATIVE fraction at n=160 |
|---|---|---|---|
| CORE_HR | 1 (SBS3_ONLY) | 50 | 0.25 |
| CORE_HR | 2 (LOH_SBS3) | 15 | 0.375 |
| CORE_HR | 3 (LOH_GIS_SBS3) | 50 | 0.25 |
| DDR_SIGNALING | 1 (SBS3_ONLY) | 130 | **0.75** |
| DDR_SIGNALING | 2 (LOH_SBS3) | 65 | 0.25 |
| DDR_SIGNALING | 3 (LOH_GIS_SBS3) | 75 | 0.25 |

**DDR_SIGNALING's single-feature (SBS3-alone) dimension is NOTABLY
WORSE than the old estimator's own equivalent row at n=160** — 0.75
(6/8) UNINFORMATIVE here, vs. 0.467 (7/15) for the old estimator's
`INTERVAL_INSTABILITY.md` Headline finding 3 table. **This is reported
as a genuine finding, not smoothed over**: it is not proof the new
estimator is worse in general (DDR_SIGNALING's OTHER two dimensions, 2
and 3, both reach the ≤50% threshold well within the tested range, at
n=65 and n=75 respectively — better than or comparable to the old
estimator's corresponding rows), but the single-feature case is the
worst-behaved cell in this sweep for the new estimator, same as it was
for the old one (`INTERVAL_INSTABILITY.md` Headline finding 3 already
flagged DDR_SIGNALING/SBS3-alone as never dropping below 33%
UNINFORMATIVE anywhere in ITS tested range either — this remains the
hardest cell for BOTH estimators, worse in absolute terms for the new
one in this specific run).

A plausible, disclosed (not confirmed) mechanism: per the dimension
caveat above, the new estimator's "dimension 1" fit still carries the
FULL 9-parameter model (covariates + 2 held-constant evidentiary
features), spending ridge-penalized degrees of freedom on parameters
that carry no signal in that scenario, rather than a true 1-parameter
fit — this could plausibly widen bootstrap CIs relative to a genuinely
reduced model, but this sweep does not isolate that mechanism directly
(it would require a second sweep with covariates OMITTED from the
"dimension 1" fit entirely, contradicting the amendment's own
mandatory-covariates specification, so it is not run here — reported as
an open question, not resolved).

## Finding 3 — what this means for Track B

Full data table: `SIMULATED_INTERVAL_INSTABILITY_SWEEP_V2.tsv`. The
realistic Track B class sizes this project has already derived
(`SIMULATION_SPEC.md` §6: CORE_HR 55-75/class, DDR_SIGNALING 25-35/class)
sit BELOW every "first n with ≤50% UNINFORMATIVE" threshold in the table
above except CORE_HR's dimension-2 row (threshold n=15, comfortably
below the realistic range) — **for the full 3-feature vector
(dimension 3, the production model), CORE_HR's realistic range
(55-75) sits below its own n=50 threshold only at the top of that range,
and DDR_SIGNALING's realistic range (25-35) sits well below its n=75
threshold entirely.** This governs what Track B can report per gene
under the new estimator at these class sizes: **CORE_HR's realistic
range is marginal (its threshold, 50, sits inside the realistic 55-75
band, so roughly the lower half of that band is still expected to
produce UNINFORMATIVE intervals a meaningful fraction of the time);
DDR_SIGNALING's realistic range (25-35) sits well below its own n=75
threshold — DDR_SIGNALING-scale genes should expect UNINFORMATIVE
full-vector intervals more often than not at these class sizes**, per
this (noisy, R=8) sweep. This is a finding about what this study design
can resolve, reported per this task's own framing ("This number governs
what Track B can report per gene"), not a problem this document proposes
to fix by tuning.
