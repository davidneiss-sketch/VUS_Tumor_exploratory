SIMULATED DATA — NOT A SCIENTIFIC RESULT

# PROPOSED_DEVIATIONS.md — proposed protocol deviations (P07 purity/depth
# floors; P08 SBS3 feature-informativeness addendum, §4)

SIMULATED: this document PROPOSES protocol deviations for human review. It
does not apply them. **`PROTOCOL.md` is not modified by this task.** No
ACMG evidence strength is assigned anywhere below. §1-3 are P07's original
proposals (unchanged); §4 is a P08 addendum.

Per this task's Step 4: "P07 should set the purity and depth floors, not
inherit them." Evidence below is from the remediated simulator's full
11088-sample run (`SIMULATED_loh_validation/SIMULATED_loh_calls.tsv`),
using a "clean" direction-accuracy metric that excludes true `AMBIGUOUS`/
`NOT_EVALUABLE` loci (these have no single "correct" direction answer by
construction — see the depth-floor analysis in §2 for why including them
would fabricate a false depth-floor signal).

## 1. Purity: propose a stricter floor than PROTOCOL.md §3's current 0.20

**Finding (clean direction accuracy, n stated for every bin):**

| purity band | n (definitive) | n (excluded AMBIGUOUS/NOT_EVALUABLE) | accuracy |
|---|---|---|---|
| 0.10–0.15 | 338 | 367 | **0.657** |
| 0.15–0.20 | 458 | 272 | **0.797** |
| 0.20–0.25 | 605 | 158 | 0.899 |
| 0.25–0.30 | 618 | 85 | 0.984 |
| 0.30–0.35 | 649 | 49 | 0.985 |

**PROTOCOL.md §3's three purity arms, evaluated against this evidence:**

- **Sensitivity value 2 (0.10, "more permissive"):** the [0.10,0.15)
  sub-band alone already shows 65.7% direction accuracy with more than
  half of all attempted calls (367/705 = 52%) excluded as `AMBIGUOUS`/
  `NOT_EVALUABLE`. **Proposed: flag the 0.10 sensitivity arm as unusable
  for P07 and recommend its removal from any P07-dependent analysis.**
  This is a real accuracy collapse, not a small-n artifact — n=705 in
  this narrow sub-band alone.
- **Primary floor (0.20):** accuracy immediately below this floor
  (0.15–0.20: 79.7%) is materially worse than immediately above it
  (0.20–0.25: 89.9%), and neither is yet at the >95% level reached by
  0.25+. **Proposed: the primary floor is in approximately the right
  place directionally (accuracy does step up crossing it) but P07's own
  operating characteristics do not reach high reliability (>=95%
  direction accuracy) until approximately purity >= 0.25–0.30** — i.e.
  the evidence supports tightening, not loosening, the primary floor for
  P07 specifically.
- **Sensitivity value 1 (0.30, "stricter"):** consistent with the
  evidence above — 0.30 is close to where P07's accuracy actually
  plateaus (98.4–98.5%). **No change proposed to this arm**; if
  anything, this run's evidence is the strongest argument FOR keeping a
  0.30 arm rather than relying on 0.20 alone.

**Proposed deviation for P07 specifically:** raise P07's own effective
purity floor to **0.25** (between PROTOCOL's primary 0.20 and stricter
0.30), and mark any P07 call below 0.20 (the current primary floor) as
`SIMULATED`-regime `LOW_CONFIDENCE_REGION` in addition to whatever
category it received — i.e., P07 should not silently inherit PROTOCOL's
0.20 as "reliable enough for this specific instrument" without its own
stated caveat below 0.25–0.30. This is a **proposal**, not an edit to
PROTOCOL.md's own §3 (which governs the whole pipeline's sample-selection
rule, not P07's own reliability characterization) — a human reviewer
should decide whether PROTOCOL.md's own S6 threshold changes, versus
P07 simply documenting its own narrower reliable range within it.

## 2. Depth: no floor change proposed — the apparent cliff is a scoring artifact, not a caller defect

An initial look at raw (unfiltered) depth-stratified accuracy showed a
dramatic **0% accuracy at depth [20,25)** (0/30 definitive calls). This
is **not** evidence of caller unreliability at low depth: every single
locus in that narrow depth band is a true-`AMBIGUOUS` locus (confirmed
directly — `simulate.py`'s `AMBIGUOUS_DEPTH_RANGE = [20,35)` deliberately
places these there), and an `AMBIGUOUS`-true locus that resolves to a
confident, correct-per-its-hidden-direction call is *scored* as
"incorrect" by the `true_direction_category == "AMBIGUOUS"` comparison —
a property of the scoring definition, not of the caller. Once true-
`AMBIGUOUS`/`NOT_EVALUABLE` loci are excluded (the same "clean" metric
used in §1), the [20,25) depth band has **zero remaining observations**
(confirmed: n=0), and the clean depth-accuracy profile is **flat, high,
and shows no floor-adjacent cliff at all**:

| depth band | n (definitive, clean) | accuracy |
|---|---|---|
| 25–30 | 675 | 0.979 |
| 30–40 | 1619 | 0.968 |
| 40–60 | 2480 | 0.967 |
| 60+ | 5063 | 0.970 |

**Proposed: no change to PROTOCOL.md §5.2's D>=20 depth floor for P07.**
The evidence does not support tightening it (accuracy is already >=96.7%
immediately above the floor once the AMBIGUOUS-scoring artifact is
excluded), and the apparent collapse at exactly [20,25) is fully
explained by the simulator's own `AMBIGUOUS` construction, not by P07's
detection power at that depth.

## 3. Summary of proposals (none applied; PROTOCOL.md unmodified)

1. **Flag PROTOCOL.md §3's 0.10 sensitivity arm as unusable for P07**
   (65.7% direction accuracy, 52% exclusion rate, n=705) — recommend its
   removal from P07-dependent analyses specifically.
2. **Propose P07 adopt an internal 0.25 purity floor** (tighter than
   PROTOCOL's 0.20 primary floor) for calls it reports as reliable,
   while still processing and reporting calls between 0.20–0.25 with an
   explicit low-confidence caveat rather than silently treating them as
   equally reliable as higher-purity calls.
3. **No change proposed to the depth floor** (D>=20, PROTOCOL.md §5.2) —
   the apparent depth-related accuracy cliff is a scoring-definition
   artifact of the simulator's own `AMBIGUOUS` construction, not a real
   caller limitation, once correctly isolated (§2).

**This document proposes; it does not decide.** A human reviewer should
weigh these findings against PROTOCOL.md §3's broader rationale (the
three purity arms exist to test purity-floor sensitivity across the WHOLE
pipeline, not P07 alone) before any change is made to PROTOCOL.md itself.

## 4. SBS3's informativeness for the joint model and Track B power (P08 addendum)

SIMULATED: this section is a P08 addendum to the P07 proposals above (§1-3,
unchanged, still open). Evidence: `DIAGNOSIS_P08.md`,
`SIMULATED_signature_validation.md` §4-7 (Mechanism 2).

**Finding.** PROTOCOL.md's joint model (`simulate.py`'s `joint_lr`/
`product_of_marginals_lr`, `EVAL_POINT`) treats LOH direction, GIS/HRD score,
and SBS3 exposure as three informative features combining multiplicatively
via a shared latent HR-deficiency variable. This session found that **SBS3
exposure, as actually recovered by real SigProfilerAssignment 1.1.5 at
exome-scale mutation counts (5-115 mutations, the realistic TCGA-BRCA range
per BENCHMARKS.tsv TMB01), is near-uninformative across most of the tested
range** — not because the injected signal was absent (a real COSMIC SBS3
vector was used for this specific test, ruling out the simulator-shape
defect in §8 above), but because of a genuine NNLS decomposition-instability
limitation of the tool itself (`DIAGNOSIS_P08.md` §5, Mechanism 2, confirmed
by two targeted experiments). Concretely: even restricting to samples with a
clearly non-trivial expected SBS3 signal (>=5 expected SBS3-attributable
mutations, up to a mean of ~15-16 in the highest-count bins tested),
SigProfilerAssignment recovered **exactly zero** SBS3 exposure for 89-100%
of samples in every bin below the top of the tested range.

**Implication.** If this finding holds after P06's shape fix (§8 above) is
applied and re-tested — which this task does not do, since `simulate.py` is
out of scope here — then **SBS3-via-SigProfilerAssignment contributes
essentially no usable evidence for the large majority of exome-scale
samples this study's Track B is designed around.** A three-feature joint
model in which one feature is null (returns the same value, ~0, regardless
of true class) for most of the cohort does not behave like a three-feature
model for most samples — it behaves like a two-feature model (LOH direction
+ GIS) with an occasional third data point, and any power calculation for
Track B that assumed SBS3's full contribution across the cohort is
optimistic for the majority of samples in the realistic mutation-count
range.

**Proposed (not applied):**

1. **Re-run this session's Mechanism-2 test after P06's shape fix lands**,
   to confirm the near-null finding is not itself confounded by the
   simulator defect (it should not be, since §4-7's catalog already used
   the real COSMIC vector — but an independent re-confirmation against the
   corrected `simulate.py` catalog would remove any remaining doubt).
2. **If confirmed, treat SBS3-via-SigProfilerAssignment as a
   low-mutation-count-conditional feature in the joint model**, not a
   uniformly-available third feature — e.g., only counted with full weight
   above some minimum total-mutation-count / expected-SBS3-count threshold
   (this session's data did not identify a clean threshold within 5-115;
   see `SIMULATED_signature_validation.md` §6), with the LOW_CONFIDENCE /
   COMPUTED_ZERO distinction (§7) carried through rather than treating a
   zero point estimate as equally informative as a well-supported one.
3. **Resolve SigMA** (a tool purpose-built for this exact low-SNV-count
   regime, per its own `DESCRIPTION`) before finalizing any power
   calculation that depends on SBS3's contribution — this session's
   resolution attempts (`GATE1.json` `resolution_attempts_p08`) were
   unsuccessful but identified a partial, promising avenue (SigMA's core
   analysis functions are not themselves BSgenome-dependent, only its
   VCF-to-matrix step is) that a future session could pursue further.
4. **Track B's power justification (SIMULATION_SPEC.md §6) should be
   revisited** if it assumed SBS3's full three-feature contribution
   uniformly across the cohort, once (1) is confirmed.

**This document proposes; it does not decide.** A human reviewer should
weigh this against the study's overall design goals — a two-feature model
with an occasional third data point may still be adequate for Track B's
purposes, depending on what margin the original power calculation assumed.

## 5. SigMA at scale: it holds up, and PROTOCOL.md's tool ordering should be revisited (P08-RERUN addendum)

SIMULATED: this section is a P08-RERUN addendum. Evidence:
`SIMULATED_signature_work/SIMULATED_sigma_382sample_stratified_result.csv`,
`SIMULATED_signature_work/SIMULATED_sigma_7392population_result.csv`,
`SIMULATED_signature_work/SIMULATED_sigma_vs_spa_by_bin.tsv`. §4 above
(P06R2) showed 10/10 correct binary classification for SigMA on the
newly-fixed catalog. That was a small, easy demonstration. This section
scales it: SigMA's `run()`, via the same source-level catalogue-only
bypass, was run against (a) the same 382-sample, mutation-count-stratified
subset `signatures.py` uses for its SigProfilerAssignment curve (real
apples-to-apples axis, not ten hand-picked samples), and (b) the full
7392-sample `CORE_HR`+`DDR_SIGNALING` population `signatures.py`'s gate6
scoring uses, fit against SigMA's full COSMIC-derived basis (not a
2-signature restriction — the `cosmic_v2_inhouse` catalog covers ~30
signatures, confirmed by the wide signature column set in the raw output).
Both runs completed quickly (382 samples: 13s; 7392 samples: 232s) — this
is not a performance-limited comparison.

### 5.1 Recovery error vs. mutation count, both tools, same bins

| bin | n | mean true | SPA mean recovered | SPA MAE | SPA frac exact-0 | SigMA mean recovered | SigMA MAE | SigMA frac exact-0 |
|---|---|---|---|---|---|---|---|---|
| [5,15) | 7 | 0.0949 | 0.0000 | 0.0949 | 1.00 | 0.0273 | 0.0929 | 0.29 |
| [15,25) | 40 | 0.1739 | 0.0000 | 0.1739 | 1.00 | 0.0458 | 0.1449 | 0.33 |
| [25,35) | 40 | 0.1179 | 0.0142 | 0.1226 | 0.97 | 0.0710 | 0.1026 | 0.38 |
| [35,45) | 40 | 0.1672 | 0.0000 | 0.1672 | 1.00 | 0.1259 | 0.1048 | 0.23 |
| [45,55) | 40 | 0.1374 | 0.0118 | 0.1433 | 0.97 | 0.1479 | 0.0956 | 0.28 |
| [55,65) | 40 | 0.1615 | 0.0139 | 0.1548 | 0.97 | 0.1606 | 0.1165 | 0.23 |
| [65,75) | 40 | 0.1568 | 0.0273 | 0.1607 | 0.95 | 0.2116 | 0.1121 | 0.07 |
| [75,85) | 40 | 0.1111 | 0.0202 | 0.1067 | 0.95 | 0.2085 | 0.1318 | 0.15 |
| [85,95) | 40 | 0.1687 | 0.0365 | 0.1680 | 0.93 | 0.2852 | 0.1431 | 0.07 |
| [95,105) | 40 | 0.1592 | 0.0471 | 0.1559 | 0.90 | 0.2885 | 0.1674 | 0.15 |
| [105,116) | 15 | 0.1469 | 0.0652 | 0.1114 | 0.87 | 0.3186 | 0.1891 | 0.20 |

Applying the same MAE<=0.15 recoverability criterion `signatures.py` uses:
**SigMA clears it in 9/11 bins (all of [5,95), failing only the top two
bins [95,116)); SigProfilerAssignment clears it in only 4/11 bins,
scattered non-monotonically** (consistent with `DIAGNOSIS_P08.md`'s
finding that SPA's per-bin MAE is noisy, not a clean function of count).
**SigMA's exact-zero rate stays below 40% in every bin tested; SPA's stays
above 87% in every bin** — SigMA does not show the catastrophic
collapse-to-zero `DIAGNOSIS_P08.md` §5 (Mechanism 2) found for SPA.

**SigMA's failure mode at high counts is different in kind, not just
degree**: it does not collapse to zero — it OVER-attributes (mean
recovered 0.29-0.32 vs. true ~0.15 in the top two bins, roughly double).
This was not tuned or selected for; it is what SigMA's real NNLS+likelihood
fit returns.

### 5.2 Population-level LR (same construction gate6 uses)

Fitting the same class-conditional-Gaussian-at-`EVAL_POINT`
(`sbs3=0.30`) LR construction `signatures.py`'s `phase6_gate6_recovery()`
uses, to SigMA's `exp_sig3` recovered exposures across the full
7392-sample population:

| quantity | injected | SPA recovered (CI) | SPA relative bias | SigMA recovered (CI) | SigMA relative bias |
|---|---|---|---|---|---|
| core_hr_sbs3_exposure_LR | 5.6450 | 435.24 [61.32, 14426.86] | 76.10 | 2.32 [2.11, 2.56] | 0.59 |
| ddr_signaling_sbs3_exposure_LR | 3.9157 | 112.02 [11.59, 7897.46] | 27.61 | 1.52 [1.40, 1.67] | 0.61 |

**Both tools still FAIL gate6's 0.25 relative-bias tolerance on both
quantities** — SigMA does not pass outright. But the difference in
*degree* is enormous: SPA's error is 27-76x the injected value (driven by
a degenerate class-conditional fit — SPA's recovered exposures are 88-98%
EXACT ZERO in every class, `SIMULATED_signature_work/SIMULATED_existing_catalog_recovered_sbs3.tsv`,
so a Gaussian fit to that distribution evaluated at `x=0.30` sits several
standard deviations into a near-degenerate tail). SigMA's recovered
class-conditional distributions are smooth, sensibly-shaped Gaussians
(frac-zero 7-24%, not 88-98%) and its LR, while still off, is off by
roughly half rather than by 30-80x.

### 5.3 Recommendation (proposed, not applied)

**PROTOCOL.md §5.4 currently orders SigProfilerAssignment as the primary,
gated tool and SigMA as BLOCKED/secondary.** The evidence above — real
runs, same data, same axis, same LR construction, same tolerance — shows
SigMA materially outperforms SigProfilerAssignment at exome-scale mutation
counts in this simulated regime, both in per-sample recovery error (§5.1)
and in population-level LR distortion (§5.2), consistent with SigMA's own
documentation ("optimized to detect...Signature 3...from...exomes",
"for panels with low SNV counts, conventional signature analysis tools do
not perform well"). **Proposed: once SigMA is genuinely installable (not
just source-bypassable) in this environment, PROTOCOL.md §5.4 should be
revisited to make SigMA the primary SBS3-exposure tool for exome-scale
data, with SigProfilerAssignment retained as a cross-check** — the reverse
of the current ordering. This is not applied: `PROTOCOL.md` is not
modified by this task, and `GATE1.json`'s formal SigMA status remains FAIL
(the source-level bypass is evidence of capability, not a resolution of
the `BSgenome.Hsapiens.UCSC.hg19` blocker — see `GATE1.json`
`resolution_attempts_p08rerun`).

**This document proposes; it does not decide.** A human reviewer should
weigh whether the source-level bypass is an acceptable production pathway
(it is not, as currently constructed — it bypasses the package's own
installation and dependency-checking machinery) before treating SigMA as
anything other than BLOCKED for actual Stage 1 use, regardless of how
well it performs here.

## 6. P08-RERUN session disposition

Both of this task's HALT conditions are met, independently:

1. **`ANALYTIC_VS_OBSERVED.md` found `core_hr_sbs3_exposure_LR`'s analytic
   truth is not achievable from the observed (true, exactly-known)
   distributions** — a P06 truth-definition defect, not fixed here.
2. **`ddr_signaling_sbs3_exposure_LR`'s analytic truth WAS confirmed
   faithful** (`ANALYTIC_VS_OBSERVED.md` §7), and gate6 still FAILs on it
   with both tools (SigProfilerAssignment relative bias 27.6, SigMA 0.61)
   — a genuine estimator problem with a confirmed-faithful truth.

Per this task's explicit instruction, **this session does not proceed to
P09**, and does not fix either finding from this prompt. `simulate.py`
(the P06 truth-definition fix `ANALYTIC_VS_OBSERVED.md` §7 recommends) and
`PROTOCOL.md` (the tool-ordering change §5.3 above recommends) are both
left unmodified, per this task's DO NOT list.

*Note (P06R3, later): finding 1 above (`core_hr_sbs3_exposure_LR`'s truth
"not achievable") did not survive a more rigorous re-test — see
`FIDELITY_AUDIT.md` and `REVALIDATION_REQUIRED.md`. Left unedited here as
the historical record of what P08-RERUN itself found and concluded at the
time; the correction is documented in those later files, not by rewriting
this one.*

---

## 7. PROTOCOL.md is silent on feature-level (not stage-level) uninformativeness (STAKE_ANALYSIS.md addendum)

SIMULATED: `STAKE_ANALYSIS.md` Step 0 found that `PROTOCOL.md` §10 pre-
specifies what happens when Stage 2 is *mostly* uncalibrated (blocks Stage
1 reporting entirely) and what vocabulary to print for an individual
out-of-scope/untestable/blocked *outcome*, but nowhere specifies what
should happen to the joint LR, or to Stage 1 reporting, when **one named
feature inside an otherwise-computable joint vector** (SBS3) is
specifically and consistently hard to recover with the chosen estimator,
while the truth is confirmed faithful (`FIDELITY_AUDIT.md`) and another
named feature in the same vector (LOH/WT_LOST direction) recovers cleanly.
§7.1 commits structurally to always reporting every per-feature LR *and*
the joint feature vector's LR together, with no described mechanism for
excluding, downweighting, or flagging one feature within that vector based
on its own individual recovery performance.

**Proposed (not applied): a future protocol revision could add a §10 rule
along these lines** — e.g., "if a single feature's Stage 2 recovery
consistently fails while its analytic truth is confirmed faithful (ruling
out a truth-definition defect as the cause), the joint LR is reported both
with and without that feature, with the feature-dropped ACMG tier reported
alongside the full-vector tier rather than only the latter." `STAKE_ANALYSIS.md`'s
ablation shows this choice is not academic: at synthetic n it changes
CORE_HR's ACMG tier by 2 points and leaves DDR_SIGNALING's unchanged; at
subtype-stratified synthetic n it changes DDR_SIGNALING's tier too; at
realistic n the picture is dominated by estimator instability rather than
by SBS3's presence or absence per se (see `STAKE_ANALYSIS.md` Step 2). This
is a proposal only — `PROTOCOL.md` is not modified by this task, per
Standing Rule 10 ("An agent may PROPOSE a protocol amendment. It may never
APPLY one").

**Second, smaller finding logged here for completeness:** `simulate.py`'s
`PAM50_PROPORTIONS` implements only 4 of the 5 PAM50 categories
`PROTOCOL.md` §8 names for stratification (Luminal A, Luminal B,
HER2-enriched, Basal-like) — it never generates a "Normal-like" sample.
Every `SYNTHETIC_SUBTYPE_Normal-like` cell in `ABLATION_TABLE.tsv` has n=0,
a simulator/protocol stratification-scheme mismatch rather than a power
limitation. Proposed (not applied): either add Normal-like to
`PAM50_PROPORTIONS` in a future simulator revision, or narrow
`PROTOCOL.md` §8's stratification list to the 4 categories the simulator
actually generates, with the discrepancy disclosed either way.
