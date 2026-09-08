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
