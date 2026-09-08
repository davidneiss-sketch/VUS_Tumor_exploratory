SIMULATED DATA — NOT A SCIENTIFIC RESULT

# DIAGNOSIS_P08.md — why SBS3 recovers as exact zero across most of the tested range

SIMULATED: every number below is derived from SIMULATED data run through the
REAL SigProfilerAssignment 1.1.5 tool. No ACMG evidence strength is assigned
anywhere below. Per this task's instruction, `signatures.py` is NOT modified
until this document names a mechanism; all four hypotheses were tested before
any conclusion was drawn.

## Summary of the finding under diagnosis

P08 (the prior session) reported: SBS3 relative exposure recovers as **exactly
zero** for ~100% of samples below 25 total exome mutations, and stays
substantially degraded up to 115 (the top of the tested range), with a
catastrophic gate6 FAIL on both `core_hr_sbs3_exposure_LR` and
`ddr_signaling_sbs3_exposure_LR` (recovered LR 0.31 and 0.48 against injected
5.64 and 3.92). This document finds **two distinct, independently-verified
mechanisms**, not one — they explain different parts of the prior report and
require different fixes.

- **Mechanism 1 (dominant cause of the gate6 FAIL, §8 of the report):** the
  mutation catalog `core_hr_sbs3_exposure_LR`/`ddr_signaling_sbs3_exposure_LR`
  are scored against — `SIMULATED_data/SIMULATED_mutation_catalogs.tsv`,
  produced by `simulate.py`'s `build_signature_shapes()` — was built from an
  ARBITRARY 96-context shape that is **not actually SBS3-shaped**. This is a
  simulator (P06) defect. See §2 below.
- **Mechanism 2 (dominant cause of §4-7's near-total exact-zero recovery,
  where the REAL COSMIC SBS3 vector WAS used for injection):** SigProfilerAssignment's
  NNLS-based decomposition is genuinely unstable at exome-scale mutation
  counts when candidate signatures are highly cosine-similar (SBS3~SBS5=0.79,
  SBS3~SBS39=0.79) — a real tool/statistical-identifiability limitation, not
  a simulator defect, not an absent signal, not an estimand mismatch, and not
  the tool declining to fit. See §4 below.

## 1. Hypothesis (a) — is the signal physically present?

**Test:** computed the injected SBS3 MUTATION COUNT per sample
(`total_mutations x sbs3_relative_exposure_true`) for all 382 samples in the
§4-7 validation catalog (the one built from the REAL COSMIC SBS3 vector).

| statistic | value |
|---|---|
| n | 382 |
| mean expected SBS3 count | 9.04 |
| median | 6.01 |
| p10 / p25 / p75 / p90 | 0.0 / 1.31 / 13.57 / 22.95 |
| fraction with expected count < 1 | 24.1% |
| fraction with expected count < 3 | 34.0% |
| fraction with expected count < 5 | 43.7% |
| fraction with expected count < 10 | 64.9% |

Per total_mutations bin (mean expected SBS3 count, and — critically — the
exact-zero recovery rate restricted to ONLY samples with expected count >= 5,
i.e. samples where the signal is clearly not "empty"):

| bin | n | mean expected SBS3 ct | n(ct>=5) | frac exact-zero recovery among ct>=5 |
|---|---|---|---|---|
| [5,15) | 7 | 0.58 | 0 | n/a (no samples with ct>=5 — genuinely empty) |
| [15,25) | 40 | 3.70 | 13 | 1.00 |
| [25,35) | 40 | 3.61 | 13 | 0.92 |
| [35,45) | 40 | 6.70 | 23 | 1.00 |
| [45,55) | 40 | 6.82 | 22 | 0.95 |
| [55,65) | 40 | 9.49 | 26 | 0.96 |
| [65,75) | 40 | 10.87 | 27 | 0.93 |
| [75,85) | 40 | 8.69 | 23 | 0.91 |
| [85,95) | 40 | 14.94 | 31 | 0.90 |
| [95,105) | 40 | 15.49 | 28 | 0.89 |
| [105,116) | 15 | 15.86 | 9 | 0.78 |

**Cross-check against TMB01 (BENCHMARKS.tsv):** TMB01 gives a real TCGA-BRCA
WES mean of 60.05 total coding mutations/tumor (30,626 across 510 tumors).
`simulate.py`'s `MEAN_MUTATIONS_PER_EXOME = 60.05` is pinned directly to this,
and this session's own catalog reproduces it (median total_mutations = 60
across the 382-sample subset — see `SIMULATED_signature_validation.md` §6).
**The total mutation burden is realistic; TMB01 says nothing about the
SBS3-specific fraction of it** (TMB01 is a total-burden benchmark, not a
signature-decomposition benchmark) — that fraction (`sbs3_relative_exposure_true`,
mean ~0.15 across this population) remains an ARBITRARY, disclosed simulator
parameter (`SBS3_LINK`, per `PARAMETER_PROVENANCE.tsv`), not an unbenchmarked
or obviously-inflated one.

**Verdict:** hypothesis (a) explains the [5,15) bin's failure completely (mean
expected count 0.58 — genuinely empty). It does **not** explain the rest of
the range: even restricting to only the subset of samples with clearly
non-trivial signal (expected count >= 5, up to a mean of ~15-16 in the top
bins), the exact-zero recovery rate stays at 89-100% everywhere except the
very top bin. **Extreme individual example:** sample `SIM-01485` (total=105,
true exposure=0.50, expected SBS3 count = **52.8** — more than half its
mutations) still recovered as **exactly zero** under default settings. A
catalogue that is not empty is still returning zero. Hypothesis (a) is
**PARTIAL** — real, but insufficient — and the diagnosis continues per the
task's instruction not to stop here.

## 2. Hypothesis (b) — estimand match

**Units check (§4-7 catalog, the real-COSMIC-vector one):** injected
`sbs3_relative_exposure_true` = mixing fraction of total mutation count drawn
from the real COSMIC SBS3 vector (unitless fraction, [0,1], `sbs3.py`
Task-K-session construction: `n_hrd = total*true_exp`, hard integer split).
Recovered `recovered_exome_normalized` = `activities["SBS3"] / sum(all
signature activities)` from `cosmic_fit`'s `Assignment_Solution_Activities.txt`
— also a unitless fraction of total mutation count, same denominator. **No
units/normalization mismatch for this catalog** — both sides are fractions of
the same total, and the real COSMIC SBS3 vector was used to both generate and
score the injection.

**Units check (§8, `core_hr_sbs3_exposure_LR`, scored against `simulate.py`'s
EXISTING catalog):** same construction verified in `simulate.py` line 619:
`n_hrd = round(total_muts * sbs3)`, identical fraction-of-total-mutations
semantics — no unit mismatch there either. **But** a categorically different
problem was found by checking WHAT VECTOR is actually being injected:

```
simulate.py:526-530 (_make_shape):
    weights = []
    for ctx in SBS_CONTEXTS:
        w = favored_weight if favored_substr in ctx else 1.0   # favored_substr="C>T", favored_weight=4.0
        w *= rng.uniform(0.7, 1.3)
        weights.append(w)
    ...
simulate.py:538-541 (build_signature_shapes):
    hrd_shape = _make_shape(rng, "C>T", 4.0)         # <- "SBS3-like" shape
    background_shape = _make_shape(rng, "", 1.0)
```

This shape is explicitly disclosed in-code as "ARBITRARY, stylized... NOT
real COSMIC SBS3 weights" (`simulate.py` line 527), so its existence was
known — but its **quantitative similarity to real SBS3 was never checked**.
Reproducing it exactly (`build_signature_shapes(random.Random(SEED+1))`,
`SEED=20260908`, matching `simulate.py` line 690) and computing real cosine
similarity against the REAL COSMIC v3.6 signature vectors extracted live in
Task K (`SIMULATED_signature_work/SIMULATED_cosmic_reference_extract.tsv`):

| comparison | cosine similarity |
|---|---|
| ARBITRARY `hrd_shape` vs. real COSMIC **SBS3** | **0.6877** |
| ARBITRARY `hrd_shape` vs. real COSMIC **SBS5** | **0.8015** |
| ARBITRARY `hrd_shape` vs. ARBITRARY `background_shape` (its own paired "background") | 0.7754 |
| ARBITRARY `background_shape` vs. real COSMIC SBS3 | 0.8446 |
| Most cosine-similar REAL COSMIC signature to the ARBITRARY `hrd_shape` | **SBS40a (0.8330)** — not SBS3 |

**The vector `simulate.py` calls "SBS3-like" and injects as the HRD-process
signal is, by real cosine similarity, LESS like real SBS3 (0.688) than it is
like real SBS5 (0.802) or even its own paired "background" shape (0.775) —
and its single closest real-world match is SBS40a, not SBS3 at all.**

**Verdict:** this is a genuine estimand-validity failure for §8's gate6-scored
quantities specifically. `core_hr_sbs3_exposure_LR`'s injected value is
defined over `sbs3_relative_exposure_true` — exposure to a vector the
simulator calls "SBS3" but which does not, in fact, resemble real SBS3 more
than it resembles the alternative signature (SBS5) or an unrelated real
signature (SBS40a). Real `cosmic_fit`, decomposing against REAL COSMIC
reference vectors, correctly finds little real-SBS3 signal in this catalog —
**because there mostly isn't any** — and the resulting near-null recovered LR
(0.31, 0.48 — both near the LR-null of 1.0) is the tool behaving *correctly*
against a mislabeled input, not a recovery failure. **This is a simulator
(P06) defect**, per hypothesis (b) — the "per-signature vs per-catalogue
normalization" failure mode the task's Step 1(b) named, generalized to a
shape-identity mismatch rather than a bare unit-conversion bug.

## 3. Hypothesis (c) — latent leakage

`simulate.py`'s injected `{arm}_sbs3_exposure_LR` (lines 288-296) is defined
as `phi_pdf(0.30, mean1, sd1) / phi_pdf(0.30, mean0, sd0)`, where `mean_c,
sd_c = marginal_gaussian_feature_params(SBS3_LINK[arm], arm, cls)` — the
**analytic population-marginal** Gaussian of `sbs3_relative_exposure_true`
given class, integrating out the latent `Z`'s within-class residual variance
(`sd = sqrt(d^2 * Var(Z) + sigma^2)`). It is a function of `sbs3` alone, not
of `Z`.

`signatures.py`'s `phase6_gate6_recovery()` fits `mean_hat, sd_hat` directly
from the **observed distribution of `recovered_sbs3_exposure`** (the real
`cosmic_fit` SBS3 column) within each `(arm, true_class)` group — an
empirical population-marginal estimate of the SAME feature, likewise
integrating over each sample's own (unobserved-to-the-estimator) `Z`. Neither
side references `Z` or the LOH-direction/GIS features. The join used is
`sample_id -> gene_group, true_class` from
`SIMULATED_TRUTH_detail/SIMULATED_sample_labels.tsv`; the resulting split
(1848 Pathogenic / 1848 Benign per arm, an exact 50/50 of the 3696-sample arm
population) confirms no join misalignment. **Both injected and recovered
quantities are the marginal-over-Z distribution of the SAME feature (SBS3
exposure alone) at the same evaluation point (0.30), given class.**

**Verdict: CLEARED.** No latent leakage, no marginal/conditional mismatch, no
join-key error. The recovery is scored against SBS3's own injected exposure,
exactly as the estimand requires.

## 4. Hypothesis (d) — structural zero vs. declined-to-fit

Checked the `value_status` classification (`COMPUTED_ZERO` / `LOW_CONFIDENCE`
/ `COMPUTED_NONZERO` / `NOT_COMPUTED`) already built into `signatures.py`'s
bootstrap output, plus a direct check that every one of the 382 main-run
samples and all 44 bootstrap-subset samples has a non-blank numeric
`recovered_exome_normalized` value (`cosmic_fit`'s `Activities.txt` is a
dense matrix — every sample gets an explicit fitted row, including explicit
zeros, never a missing row):

```
bootstrap value_status counts (44 samples x 100 replicates each): {'COMPUTED_ZERO': 26, 'LOW_CONFIDENCE': 18}
NOT_COMPUTED: 0 (all 382 main-run samples; all 44 bootstrap samples)
```

**Verdict: CLEARED as an explanation, but confirms the failure is real.**
The tool is not refusing to fit — it fits every sample and explicitly assigns
SBS3 a weight of exactly zero in the majority case. This rules out "the tool
declined" and confirms the zeros are genuine fitted decisions requiring
mechanism 2 below.

## 5. The mechanism behind §4-7 (real-COSMIC-vector catalog, hypotheses a-d exhausted)

Since (a)-(d) do not explain §4-7's near-total exact-zero recovery even with
the REAL SBS3 vector injected and substantial expected counts, two targeted
follow-up experiments were run against 10 known-failing high-expected-count
samples (expected SBS3 count 29.7 to 52.8, i.e. clearly non-trivial signal),
using the real `cosmic_fit` tool each time:

**Experiment 1 — pruning-penalty sensitivity.** Reran with
`nnls_remove_penalty=0`, `initial_remove_penalty=0`, `nnls_add_penalty=0`
(vs. defaults 0.01/0.05/0.05). If a pruning threshold were removing a
real-but-small SBS3 contribution, zeroing the penalties should restore it.
**Result: it did not** — SBS3 remained ~0 for 7/10 samples (only 3 samples
picked up a token weight of 3), and the total SBS5 assignment for these
samples also collapsed to 0, with mass moving elsewhere. **Penalty tuning is
not the mechanism.**

**Experiment 2 — restricted basis.** Reran using a reference database
restricted to ONLY the two true generating signatures, `{SBS3, SBS5}`
(`signature_database=` a 2-column subset of the real COSMIC v3.6 matrix),
removing all basis collinearity with the other ~77-99 reference signatures.
**Result:** one sample (`SIM-01485`, true exposure 0.50) now got **100%** of
its 105 mutations assigned to SBS3 (true value: 52.8 — the tool overshot to
the opposite extreme). The other 9 samples (true exposures 0.33-0.60, expected
counts 29.7-51.6) all got **100%** assigned to SBS5, 0% to SBS3.

**Under default settings**, the same 10 samples' true SBS3 signal was found
distributed across `SBS39` (43 counts for `SIM-01485`), `SBS5`, `SBS16`,
`SBS7c`, `SBS28` — real COSMIC signatures, none of them SBS3. Checking why
`SBS39` specifically: real `cos(SBS3, SBS39) = 0.791` — nearly identical to
`cos(SBS3, SBS5) = 0.793`. `SBS39` was independently flagged in this
session's own live WebSearch results as a signature the field associates with
homologous-recombination deficiency (a real, cosine-similar, HRD-adjacent
signature that competes directly with SBS3 for the same mutational signal).
For `SIM-01485` specifically, the noisy *observed* 96-context histogram's
cosine similarity to real SBS3 (0.741) is actually **higher** than to SBS39
(0.696) or SBS5 (0.691) — so a single-signature nearest-neighbor match would
correctly pick SBS3. The full multi-signature NNLS least-squares fit,
however, does not — a combination of several correlated signatures achieves a
lower overall residual than SBS3 alone.

**Named mechanism:** SigProfilerAssignment's NNLS-based decomposition is
genuinely **unstable at exome-scale mutation counts** (tens, not thousands,
of mutations) when the true generating signature has real cosine similarity
>=0.79 to one or more competing reference signatures (SBS5, SBS39 both
qualify for SBS3). This instability is not a pruning-threshold artifact
(ruled out by Experiment 1) and is not solely a basis-size/collinearity
artifact (Experiment 2's minimal 2-signature basis still produced near-binary,
frequently-wrong all-or-nothing solutions rather than proportional recovery
of the true mixing fraction). This is a real, defensible finding about the
tool's statistical identifiability limit in this regime — consistent with
why SigMA (a tool purpose-built for exactly this low-count regime, see
DESCRIPTION: "optimized to detect... Signature 3... from... exomes" and
"For panels with low SNV counts, conventional signature analysis tools do
not perform well") exists as a separate tool in the first place. It does not
require a simulator change; it is not fixable by a simple `signatures.py`
parameter adjustment (both directions tested made things equal or worse); it
is the honest characterization of SigProfilerAssignment's real behavior in
this regime.

## 6. Conclusion and disposition

Two independently-confirmed mechanisms, requiring two different
dispositions per this task's Step 4 branching:

- **Mechanism 1 (§2, hypothesis b) drives the gate6 FAIL** (both
  `core_hr_sbs3_exposure_LR` and `ddr_signaling_sbs3_exposure_LR` are scored
  against the mislabeled-shape catalog). This is a **simulator (P06) defect**.
  Per this task's explicit instruction, `simulate.py` is NOT modified from
  this prompt. See `REQUIRED_P06_CHANGES.md`. **HALT on this branch** — no
  attempt is made to "fix" gate6 via `signatures.py` changes, since no
  `signatures.py` change can correct a mislabeled injected shape.
- **Mechanism 2 (§5) explains §4-7's separate, non-gate6-scored finding**
  (real SBS3 vector injected, still near-total exact-zero recovery). This is
  a genuine tool-behavior finding, not a simulator defect and not a
  `signatures.py` bug — it stands as reported, with the two confirmatory
  experiments now included as evidence (§5) rather than the prior session's
  unexplained "structural failure" framing.

This diagnosis and the HALT are consistent with the task's own framing:
"if the diagnosis points at the simulator, emit REQUIRED_P06_CHANGES.md and
stop." That is true for the quantities gate6 actually scores.
