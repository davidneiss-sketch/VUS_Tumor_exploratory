SIMULATED DATA — NOT A SCIENTIFIC RESULT

# RESIDUAL_DIAGNOSIS.md — P-DIAG-1: Characterizing the residual CORE_HR containment miss

This is a diagnosis, not a fix.
Nothing was adjusted in this session (Standing Rule 10). All diagnostic
output lives in `residual_diagnosis/`, separate from `production_v2/`; no
committed artifact was changed to produce it.

## 0. The miss under diagnosis

After P-FIX-1's two corrections, gate6 on CORE_HR reads:

```
injected 5.8263, CI [4.4807, 5.7734], relative bias 13.5%
```

The CI's upper bound misses the injected value by **0.0529** (5.8263 −
5.7734), under 1% of the interval's own width. Relative bias (13.5%) is
inside gate6's 0.25 tolerance; CI containment is not. DDR_SIGNALING passes
cleanly (6.3% relative bias, contained).

Three candidate explanations were investigated in parallel, per the task
spec: (1) Monte Carlo error on the bootstrap CI endpoints, (2) a mixture-
weight mismatch between the truth side and the production side, (3) ridge
shrinkage bias at the CV-selected lambda. Each is reported below with its
evidence, then attributed.

## 1. STEP 1 + STEP 4 — Monte Carlo error on the CI endpoints

**Method.** `residual_diagnosis_seed_variation.py` reran the full,
fixed-population (n=1848/1848, no subsampling — only the bootstrap
resampling seed varies) patient-clustered bootstrap at each arm's own
CV-selected lambda, under **15 independent seeds**, at a disclosed,
reduced replicate count **B=500** (vs. the committed run's B=2000; Standing
Rule 4 — arbitrary reduction for tractability, compensated by an analytic
B-scaling extrapolation rather than presented as B=2000-equivalent).
Seeds: `88000000 + seed_idx*1000 + hash(arm)%997`, disclosed and distinct
from every other seed used this session. Full per-seed CIs and containment
flags: `residual_diagnosis/SIMULATED_SEED_VARIATION.tsv` (30 rows);
summary: `residual_diagnosis/SIMULATED_SEED_VARIATION_SUMMARY.tsv`.

**Results.**

| arm | seeds | B | mean upper bound | SE(upper), B=500 | SE(upper), extrapolated to B=2000 | seeds containing injected |
|---|---|---|---|---|---|---|
| CORE_HR | 15 | 500 | 5.7351 | 0.0506 | 0.0253 | **0 / 15** |
| DDR_SIGNALING | 15 | 500 | 5.4817 | 0.0448 | 0.0224 | **15 / 15** |

CORE_HR's upper bound ranged from 5.6366 to 5.8031 across the 15 seeds —
every single one landed below the injected value 5.8263. DDR_SIGNALING's
upper bound ranged from 5.4186 to 5.5693 — every single one landed above
its injected value 5.1545 (i.e. contained, since the lower bound is also
below it in all 15 cases; see the TSV for lower bounds).

**Is 0.0529 within seed-to-seed variation?** **No.** The empirical
seed-to-seed SE of the upper bound, even extrapolated up to the committed
run's B=2000 (0.0253), is roughly half the size of the 0.0529 gap, and —
more decisively — the containment outcome itself did not flip even once
across 15 independent seeds for either arm (0/15 and 15/15). A quantity
whose sign never changes across 15 independent draws is not behaving like
a coin flip; the qualitative CORE_HR-fails / DDR_SIGNALING-passes split is
reproducible, not seed-dependent. This directly answers the task's own
"read first" framing: containment here is not noise, and the question is
not resolved by seed selection.

**Runtime cost to shrink SE further.** Per the task's explicit request,
even though the above already settles the "is it noise" question:

- SE(upper) ≤ 50% of 0.0529 (0.02645): requires **B ≈ 1,827**, ≈ 3.4 min
  per seed (single-seed estimate, at the ~0.112 s/fit benchmarked this
  session).
- SE(upper) ≤ 10% of 0.0529 (0.00529): requires **B ≈ 45,675**, ≈ 85.3 min
  per seed.

Both are far above the committed B=2000, and the qualitative finding above
does not depend on reaching either threshold — it is already established
at B=500 across 15 seeds.

**STEP 4 — is DDR_SIGNALING's pass robust?** Yes: 15/15 seeds contain the
injected value, the same directional robustness as CORE_HR's failure. The
gate6 criterion does not flip for either arm across seeds; this is not a
"criterion flips both arms" symptom, which would have pointed at a
criterion (or endpoint-estimation) defect per the task's own STEP 4
framing. It instead points to a systematic, non-noise cause for CORE_HR's
miss specifically.

**Conclusion for this candidate: not sufficient, alone or at all, to
explain the miss.** The miss is real and reproducible, not a Monte Carlo
artifact.

## 2. STEP 2 — Mixture weight match and application point

**Method.** `residual_diagnosis_weights_check.py` printed the truth-side
weights (`simulate.PAM50_PROPORTIONS`, sourced from `BENCHMARKS.tsv`
PAM01/PAM02 per `SUBTYPE_MODEL.md` §4) and the production-side weights
(`production_v2_run.py`'s `mixture_point_estimate()`, which reads
`simulate.PAM50_PROPORTIONS` directly) side by side, and confirmed via `is`
identity check that both sides reference the **same Python object**, not
independently re-derived copies.

**Weight values** (`residual_diagnosis/SIMULATED_WEIGHTS_COMPARISON.tsv`):

| subtype | truth-side | production-side | identical |
|---|---|---|---|
| LumA | 0.44225834 | 0.44225834 | True |
| LumB | 0.24766467 | 0.24766467 | True |
| HER2E | 0.11203878 | 0.11203878 | True |
| Basal | 0.18280011 | 0.18280011 | True |
| Normal-like | 0.01523810 | 0.01523810 | True |

**Weights are identical in value and identity.** The mismatch the task
asked to check for — different weight values, or independently-derived
copies that happen to agree — is not present.

**Application point, however, genuinely differs**, confirmed by direct
source comparison of the two computations:

- **Truth side** (`simulate.joint_density_collapsed` /
  `joint_lr_collapsed`): `joint_density_collapsed(cls) = Σ_s w_s ·
  joint_density_subtype(s, cls)` — weights are applied to the per-subtype
  **density**, once per class, **before** the division that forms the LR.
- **Production side** (`production_v2_run.py`'s `mixture_point_estimate`):
  for each subtype, fit a per-subtype LR (`lr_s =
  probability_to_lr(predict_proba(...))`), **then** `weighted_lr = Σ_s w_s
  · lr_s` — weights are applied to the already-divided per-subtype
  **ratio**, after each subtype's own division.

These are not the same operation: weighting densities then dividing is
mathematically different from weighting already-divided ratios (Jensen's
inequality applies, since LR is a ratio of the mixture components, not
linear in the weights).

**Isolating the application-point effect analytically** (no model
fitting, no ridge bias — computed purely from `simulate.py`'s own exact,
noise-free generative functions, so this isolates the application-point
choice from every other source of error;
`residual_diagnosis/SIMULATED_APPLICATION_POINT_ISOLATION.tsv`):

| arm | true density-mixture LR (truth definition) | true LR-mixture (production's operation, exact inputs) | relative displacement |
|---|---|---|---|
| CORE_HR | 5.826333 | 6.181888 | **+6.10%** |
| DDR_SIGNALING | 5.154487 | 5.633027 | **+9.28%** |

**The application-point effect is real, confirmed, and non-trivial in
size — but it pushes the estimate ABOVE truth, the opposite direction
from the observed miss** (production's actual CORE_HR point estimate sits
below truth, not above it). Per the task's own STEP 2 instruction ("If
they differ in value or in application point, that is the cause and this
step ends the diagnosis"), the letter of that instruction cannot be
mechanically applied here: application point does differ, but that
difference alone is insufficient — indeed counterproductive in sign — to
account for the observed downward miss. Reporting this honestly (Standing
Rule 2's spirit — state what the evidence shows, not what would make a
tidy narrative) means this step does *not* end the diagnosis on its own;
it identifies a real, disclosed distinction whose effect must be netted
against the other candidate below.

**Why the LR-mixture, not the density-mixture, is the operation actually
available to this estimator class.** A logistic regression model fit with
subtype as a covariate estimates P(class | X, subtype) — from which only
the ratio f(x | Pathogenic, subtype) / f(x | Benign, subtype) is
identifiable per subtype level. The absolute per-subtype class-conditional
densities are not separately recoverable from a discriminative fit without
additional, untested assumptions (e.g. an assumed marginal class
distribution per subtype). This means `SIMULATED_TRUTH.tsv`'s own
density-mixture definition is not directly reachable from per-subtype
logistic evaluations by construction — the LR-mixture is what this
estimator class can produce. That is a structural property of the modeling
approach, not a simple mislabeled-weight bug with an obvious one-line fix;
it is noted here as a confirmed, disclosed finding, not corrected (Standing
Rule 10 — no estimator file is touched by this task).

**Conclusion for this candidate: real and confirmed, but not sufficient
alone, and in the wrong direction, to explain the observed miss.**

## 3. STEP 3 — Ridge shrinkage bias vs. lambda

**Method.** `residual_diagnosis_lambda_sweep.py` refit the ridge logistic
model on the full, fixed population (deterministic, no bootstrap) across
`LAMBDA_GRID = [0.001, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 60.0,
100.0, 200.0, 500.0, 1000.0]`, calling production's own
`mixture_point_estimate` at each lambda. Lambda **selection** itself was
not touched — this sweep quantifies the known shrinkage property; it does
not license changing which lambda is selected. Full data:
`residual_diagnosis/SIMULATED_LAMBDA_SWEEP.tsv`.

**Results (selected points):**

| arm | lambda | mixture LR | relative bias | note |
|---|---|---|---|---|
| CORE_HR | 0.001 (≈unpenalized) | 7.2779 | +24.91% | |
| CORE_HR | 10.0 | 6.1159 | +4.97% | |
| CORE_HR | **30.0** | **5.0410** | **−13.48%** | **CV-selected (lambda.1se)** |
| CORE_HR | 60.0 | 4.2359 | −27.30% | |
| DDR_SIGNALING | 0.001 (≈unpenalized) | 6.6439 | +28.90% | |
| DDR_SIGNALING | 60.0 | 5.3323 | +3.45% | |
| DDR_SIGNALING | **100.0** | **4.8312** | **−6.27%** | **CV-selected (lambda.1se)** |
| DDR_SIGNALING | 200.0 | 4.0368 | −21.68% | |

**Direction and magnitude.** Bias vs. lambda is monotonic and large: near
zero lambda, both arms substantially *overshoot* the injected value
(+24.9%/+28.9%); as lambda increases, the mixture LR shrinks toward the
null (LR=1) monotonically, crossing zero relative bias between lambda=10
and lambda=30 for CORE_HR, and between lambda=60 and lambda=100 for
DDR_SIGNALING. **Both CV-selected lambdas sit just past their arm's own
zero-bias crossing** — CORE_HR's CV-selected lambda=30 is the first grid
point past the crossing (bias already −13.48%), and DDR_SIGNALING's
CV-selected lambda=100 is likewise just past its crossing (bias −6.27%).

**Is the observed 13.5% bias consistent with shrinkage?** Yes, directly:
the −13.48% relative bias at lambda=30 in this diagnostic sweep, computed
independently by refitting on the full fixed population, reproduces the
committed production run's own reported 13.5% relative bias to within
rounding. This is not merely "consistent with" shrinkage — it *is* the
shrinkage curve, evaluated at the selected lambda.

**Conclusion for this candidate: this is the dominant, sufficient
explanation for the direction and magnitude of the net observed bias**,
and — critically — it is large enough (13.5 percentage points of downward
bias) to fully absorb and reverse the smaller, opposing +6.1% application-
point effect from Section 2, netting to an overall downward miss.

## 4. Attribution

Per the task's STEP 5 instruction, the three candidates are not equally
weighted contributors; they resolve as follows:

- **Endpoint Monte Carlo error (Section 1): ruled out.** The miss is
  reproducible across 15 independent seeds (0/15 containing for CORE_HR,
  15/15 for DDR_SIGNALING); it is not seed-dependent noise.
- **Mixture weight/application-point mismatch (Section 2): real and
  disclosed, but insufficient and wrong-signed alone.** Weights are
  identical; the application point (LR-mixture vs. density-mixture)
  genuinely differs and is quantified at +6.1% for CORE_HR — but this
  pushes the estimate *toward* the injected value, not away from it, so it
  cannot be the cause of a miss where production sits *below* truth. It is
  best understood as a structural consequence of what a per-subtype
  discriminative model can identify (Section 2, final paragraph), not a
  mislabeled-weight defect.
- **Ridge shrinkage bias (Section 3): the dominant, sufficient cause.**
  The independently-computed shrinkage curve reproduces the observed
  13.5%/6.3% biases at the CV-selected lambdas, in the correct (downward)
  direction, and is large enough to net against and reverse the smaller
  application-point effect.

**Net attribution: ridge shrinkage at the CV-selected lambda, partially
offset by the (smaller, opposite-sign) application-point effect, jointly
and fully account for CORE_HR's residual containment miss.** No component
of the miss is left unexplained by these two candidates working together;
Monte Carlo endpoint noise contributes negligibly and does not change the
qualitative outcome. **No evidence of an estimator, weighting, or
implementation defect was found.** This is a known, expected property of
a penalized estimator evaluated against an exact (unshrunk) synthetic
target — not a bug.

This finding does **not** license changing lambda, the mixture weighting
operation, gate6's criterion, or any other estimator parameter in this
session (Standing Rule 10; task DO-NOT list). Per the task's own framing:
the CV-selected lambda exists because small-n stability is what the study
needs, and PALB2/RAD51C will have class sizes in the tens, where an
unpenalized fit would trade this synthetic-data bias for unusable
intervals on real data. That tradeoff is not reopened here.

## 5. Disposition

Because the evidence cleanly attributes the miss to a known, expected,
quantified estimator property rather than a defect, and because that
property (shrinkage bias under a criterion requiring exact-point CI
containment) raises a genuine protocol question about what gate6 should be
testing for a penalized estimator, **a `PROPOSED_DEVIATIONS.md` entry is
warranted** and is added below (proposal only; gate6's logic is not
modified, per Standing Rule 10).

## 6. Integrity

- All diagnostic scripts (`residual_diagnosis_seed_variation.py`,
  `residual_diagnosis_weights_check.py`, `residual_diagnosis_lambda_sweep.py`)
  import `logistic_estimator.py`, `simulate.py`, and `production_v2_run.py`
  read-only; none of the three is modified.
  `PROTOCOL.md`, `signatures.py`, `loh_caller.py`, and every gate script
  are untouched (confirmed by `git diff` — see acceptance check).
- All diagnostic output is written under `residual_diagnosis/`, separate
  from `production_v2/`; no committed artifact was overwritten.
- Preflight collision check and checksum snapshot/verify were run against
  this task's changes; see `scripts/check_p_diag_1_acceptance.py` output.
