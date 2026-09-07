# PROTOCOL.md — Pre-registered analysis protocol

Status: **DRAFT, pending human review.** No code has been run and no data has
been touched to produce this document (task instruction: "No code, no
data"). Every threshold below is a fixed, pre-registered, exact value —
see the task's "DO NOT" clause and the acceptance criterion "no threshold
is unspecified." Where a value genuinely cannot be fixed to one number
today (e.g. the exact ClinVar release date, since `ENVIRONMENT.lock` marks
that UNVERIFIED), the **rule** for choosing it at execution time is fixed
here instead, precisely enough that a reader can predict the outcome
without seeing any data first.

**HALT: this document requires human review before the repository is
tagged `v0.1-preregistered`.** No tag is created by this session. Tagging
is the reviewer's action, taken after reading this file, not an automated
next step.

This protocol builds on, and must be read together with:
- `TRACK.md` — this project runs on **Track A** (open-access TCGA-BRCA /
  TCGA-OV / CPTAC-3-breast data only) today; Track B (controlled-access
  germline variant data) is not authorized. Every rule below that
  references "germline variant" data is written for when Track B (or an
  approved dbGaP DAR) becomes available; nothing in this protocol is
  executed against real germline data under Track A.
- `GATE1.json` / `ENVIRONMENT.lock` — the analysis environment's actual
  tool inventory and pinned versions. `GATE1.json`'s `gate1_result` is
  currently **FAIL** (SigMA could not be installed). This protocol names
  SigMA-dependent steps explicitly as **BLOCKED** below rather than
  silently omitting them, per Standing Rule 4/8, and does not permit
  substituting another tool for SigMA (the earlier task required
  "SigProfilerAssignment AND SigMA" with no "or equivalent" clause).
- `BENCHMARKS.tsv` / `BENCHMARKS_NOTES.md` — every literature-derived
  numeric constant used below (OddsPath thresholds, the GIS≥42 threshold,
  ENIGMA likelihood ratios) is copied verbatim from a `FOUND` row there,
  never re-derived or approximated. Where `BENCHMARKS.tsv` has a
  `NOT_FOUND` row (the BRCA-stratified HGSOC HRD-high split, HRD05; the
  Knijnenburg per-sample data location, DDR02), this protocol says so and
  states which downstream step is blocked as a result, rather than
  inventing a number to fill the gap.

---

## 1. Gene lists

Two gene groups are defined and analyzed **separately** throughout — no
model in this protocol pools variants from both lists into one estimate
unless a step is explicitly labeled "pooled sensitivity analysis," and no
step is so labeled in this version.

### 1.1 CORE_HR (core homologous-recombination machinery), n = 9

`BRCA1, BRCA2, PALB2, RAD51C, RAD51D, RAD51B, BRIP1, BARD1, RAD54L`

Rationale for scope: genes encoding the direct strand-exchange/recombinase
complex and its immediate loading factors (RAD51 paralogs, the
BRCA1–PALB2–BRCA2 loading axis, BARD1 as the obligate BRCA1 heterodimer
partner, RAD54L as the RAD51-motor branch-migration factor). This is a
protocol design decision, stated exactly so it is reproducible — it is not
itself a "published value" requiring a live citation under Standing Rule 3
(it names which genes we chose to study, not a result we compare against).

### 1.2 DDR_SIGNALING (upstream DNA-damage-response signaling / sensing), n = 8

`ATM, CHEK1, CHEK2, ATR, MRE11, RAD50, NBN, FANCM`

Rationale for scope: checkpoint kinases (ATM/ATR/CHEK1/CHEK2), the
MRN double-strand-break sensor complex (MRE11, RAD50, NBN), and FANCM as
the Fanconi-anemia-core-complex DNA-damage sensor/recruiter that acts
upstream of, and mechanistically distinct from, the CORE_HR strand-exchange
step. No gene appears in both lists.

### 1.3 Analysis rule

Every stratified analysis in §8 is run once per gene group (CORE_HR,
DDR_SIGNALING) as two entirely separate model fits, reference sets, and
reported LR tables. A variant in a gene not on either list is out of scope
for this protocol version and is excluded at sample-selection step S1b
(§2).

---

## 2. Sample selection rules, in order, every threshold stated

Applied in this exact order; a sample failing any rule is excluded and
does not proceed to later rules (short-circuit, not independent filters —
this matters for how exclusion counts are reported per Standing Rule 5).

1. **S1a — Cohort.** GDC project = `TCGA-BRCA`. Only Track A open-tier
   data types are read (clinical, biospecimen, gene expression, copy
   number, DNA methylation, masked somatic mutation MAF), per
   `ACCESS_AUDIT.md` / `TRACK.md`. Germline VCFs are controlled-access and
   out of scope until Track B is authorized.
2. **S1b — Gene scope.** The variant(s) under analysis for a sample must
   lie in a CORE_HR or DDR_SIGNALING gene (§1); otherwise the sample is
   out of scope for this protocol (not excluded from the cohort generally
   — simply not an analysis unit here).
3. **S2 — Sample type.** GDC `sample_type` = `Primary Tumor` (code `01`)
   only. Excludes Metastatic (`06`), Additional-Metastatic (`07`),
   Recurrent (`02`), and Solid Tissue Normal (`10`/`11`, used only as the
   paired-normal reference for variant calling, never as an analysis
   unit).
4. **S3 — One aliquot per patient.** Deduplicate by `bcr_patient_barcode`.
   If more than one qualifying Primary Tumor aliquot exists for a patient:
   (a) prefer the aliquot with portion code `01` over higher portion
   numbers; (b) if still tied, prefer the analyte code `D` (DNA) aliquot
   with the largest submitted BAM file size; (c) final deterministic
   tiebreak: the lexicographically smallest GDC file UUID. This exact
   3-step tiebreak, not "pick one," is the rule.
5. **S4 — Histology.** ICD-O-3 morphology code in
   `{8500/3 (infiltrating duct carcinoma, NOS), 8520/3 (lobular carcinoma,
   NOS)}` only. All other morphology codes (mucinous, medullary,
   metaplastic, phyllodes, etc.) are excluded from this protocol version
   in full — there is no sensitivity arm re-including them.
6. **S5 — Sequencing depth.** Mean target coverage ≥30x in the tumor
   BAM and ≥15x in the matched-normal BAM, read from GDC's own BAM QC
   metrics. Samples below either floor are excluded.
7. **S6 — Tumor purity.** ASCAT- and/or FACETS-estimated purity must
   clear the purity floor (§3). If both tools return an estimate and they
   disagree by more than 10 percentage points, the sample is marked
   `NOT_EVALUABLE_PURITY` and excluded (not silently averaged).
8. **S7 — QC exclusions.** Exclude samples on the GDC "Do Not Use" /
   redaction list current as of the GDC Data Release pinned in
   `ENVIRONMENT.lock` at execution time; exclude samples with a
   reported-vs-genotype-inferred sex mismatch; exclude samples with a
   cross-patient contamination estimate (ContEst or the GDC-equivalent
   QC field) > 5%.
9. **S8 — Analysis-unit definition.** After S1–S7, the analysis unit is
   one (patient, gene, variant) triple. A patient carrying more than one
   qualifying variant in the same gene (e.g., a P/LP and a separate VUS)
   contributes one row per variant, not one row per patient — both are
   logged, neither is silently dropped.

**Every run's output must report, per rule S1–S8 in order: the number
excluded at that step and the number remaining**, per Standing Rule 5 (a
final "N analyzed" with no exclusion breakdown is not an acceptable
report under this protocol).

---

## 3. Purity floor and sensitivity values

- **Primary purity floor: 0.20** (≥20% tumor cellularity, ASCAT/FACETS
  consensus per S6 above).
- **Sensitivity value 1 (stricter): 0.30.**
- **Sensitivity value 2 (more permissive): 0.10.**

All three floors are run as three parallel arms on every stratum; the
primary reported LR/CI in every table uses 0.20. The two sensitivity arms
are reported alongside in the same table (not in a separate appendix, not
computed only on request) so a reader can see whether the primary result
is purity-floor-sensitive.

---

## 4. Reference class definitions

### 4.1 ClinVar review-status floor

- **Minimum for any reference-set membership (pathogenic or benign):**
  ≥1 gold star — i.e., `criteria_provided,_single_submitter` or higher.
  Variants with `no_assertion_criteria_provided` (0 stars) are **never**
  members of a reference truth set (they may still appear as VUS analysis
  targets).
- **Primary reference sets:** ≥2 gold stars —
  `criteria_provided,_multiple_submitters,_no_conflicts` or
  `reviewed_by_expert_panel` (3 stars) only.
- **1-star-only variants** form a separate, explicitly labeled
  lower-confidence sensitivity reference set, reported alongside but never
  merged into the primary ≥2-star set.
- **Snapshot pin rule:** the ClinVar release used is the most recent
  monthly archived release (first-Thursday-of-month release, per
  `BENCHMARKS_NOTES.md`) confirmed live with a resolving URL and
  timestamp within 7 days before Stage 0 execution begins (§10). If no
  such confirmation is obtainable, execution halts at Stage 0 and does not
  proceed with an unpinned or guessed release (Standing Rule 3). This is
  a fully specified *rule* rather than an open question — it does not
  depend on the data under analysis, only on the calendar date of
  execution.

### 4.2 gnomAD popmax ceiling for the frequency-matched benign set

- **Ceiling: population-max (popmax) allele frequency ≤ 0.01 (1%).**
  A variant is eligible for the frequency-matched benign reference pool
  only if its gnomAD popmax AF is at or below this ceiling. Rationale:
  this keeps the benign reference set from being dominated by
  ultra-common polymorphisms that would be trivially separable from VUS
  by frequency alone, so that frequency itself is not doing the
  discriminating work that this protocol's LR features (§6) are meant to
  do — frequency is a *selection* criterion for reference-set membership
  here, never a *feature* fed into the LR model.
- Benign reference-set membership additionally requires a ClinVar
  Benign/Likely-Benign classification meeting the review-status floor in
  §4.1 — a gnomAD-popmax-only benign proxy (frequency alone, no ClinVar
  corroboration) is never used as a primary reference-set member; it may
  only appear in an explicitly labeled exploratory arm, never in the
  primary tables.
- **gnomAD release pin rule:** identical procedure to §4.1's ClinVar
  rule — the most recent gnomAD release confirmed live (URL + timestamp)
  within 7 days of Stage 0 execution; halt if unconfirmable.

### 4.3 Circularity exclusion criteria

A candidate reference-truth variant (pathogenic or benign) is **excluded**
from every reference set if **any** of the following hold:

1. Its ClinVar submission's cited evidence includes PS3/BS3 functional-assay
   evidence of homologous-recombination function, tumor-derived LOH or
   second-hit evidence, or a multifactorial-likelihood model output — i.e.,
   any evidence type this protocol itself uses as a feature (§6). Using
   such a variant as ground truth would let the model "recover" evidence
   it was partly derived from.
2. It is a variant known to have been part of the calibration/training set
   used to originally derive the OddsPath thresholds (Tavtigian et al.
   2018, BENCHMARKS ODDS01/ODDS02) or the ENIGMA tumor-pathology
   likelihood-ratio tables (Spurdle et al. 2014, BENCHMARKS ENIGMA01/02),
   where that overlap can be identified from the variant's public ClinVar
   submission history.
3. Its **only** pathogenic/benign evidence in ClinVar is a computational/
   in-silico predictor (a PP3/BP4-only submission), since in-silico scores
   are not independent of feature families this protocol may explore in
   later versions.
4. It would be the **second or later** reference-truth variant contributed
   by the same patient to the same gene group's reference set — capped at
   1 reference-truth variant per patient per gene group, so one heavily
   re-sequenced patient cannot dominate the reference distribution.

---

## 5. Feature definitions

### 5.1 LOH categories (5, discrete, mutually exclusive)

Given tumor purity `p` (§3), local allele-specific copy number (major `M`,
minor `m`, total `CN_t = M + m`) at the germline variant's locus from
ASCAT (primary) or Sequenza (sensitivity — both PASS in `GATE1.json`), and
tumor-sample variant depth `D` with `A` alternate reads:

1. **RETAINED** — minor allele copy number `m ≥ 1` and observed tumor VAF
   falls within `[0.35, 0.65]` (no allelic imbalance).
2. **LOH_SECOND_HIT** — `m = 0` (true LOH) and the binomial model (§5.2)
   does not reject "mutant allele retained" (p ≥ 0.05) while it does
   reject "wild-type allele retained" (p < 0.05). This is a bona fide
   second hit.
3. **LOH_NON_SECOND_HIT** — `m = 0` and the mirror image of (2): "wild-type
   retained" is not rejected, "mutant retained" is rejected. LOH occurred
   but does not constitute a second hit.
4. **LOH_AMBIGUOUS** — `m = 0` but neither hypothesis in (2)/(3) is
   rejected at α = 0.05 (or both are), i.e. the model cannot distinguish
   which allele was retained.
5. **NOT_EVALUABLE** — purity below the active floor (§3), copy-number
   call failed/NA at this locus, or tumor site depth `D < 20`.

### 5.2 Binomial VAF model (exact specification)

Assume the germline variant is heterozygous (VAF = 0.5) in normal cells,
which contribute a `(1-p)` fraction of reads at 2 copies. For a tumor-cell
allele configuration where the mutant allele occupies `X` of the `CN_t`
tumor-cell copies at the locus, the expected VAF is:

```
E[VAF | X] = (p * X + (1 - p) * 1) / (p * CN_t + (1 - p) * 2)
```

Two candidate values of `X` are tested:
- **"Mutant retained"** hypothesis: `X = M` (mutant allele occupies all
  surviving copies, i.e., the wild-type copy was lost).
- **"Wild-type retained"** hypothesis: `X = 0` (mutant allele was lost).

For each hypothesis, compute the exact two-sided binomial test p-value for
observing `A` alt reads out of `D` total reads under
`Binomial(D, E[VAF|X])`. **Significance threshold: α = 0.05** for each
test (not Bonferroni-adjusted across the two tests — they are mutually
exclusive hypotheses about the same locus, not independent comparisons).
**Minimum depth for this test to run at all: `D ≥ 20`**; below that, the
locus is `NOT_EVALUABLE` (§5.1 category 5) regardless of the test outcome.

### 5.3 HRD components

Computed with **scarHRD v0.1.1** (`ENVIRONMENT.lock` §2, `GATE1.json`
PASS), reference build `grch38` (pinned to GRCh38.p14 / `GCF_000001405.40`
per `ENVIRONMENT.lock` §3), on ASCAT segmentation (primary input) with
Sequenza segmentation as a sensitivity input (both PASS in `GATE1.json`):

1. **HRD-LOH** — count of LOH segments with length ≥15 Mb and shorter than
   the whole chromosome.
2. **TAI (telomeric allelic imbalance)** — count of allelic-imbalance
   segments extending to a telomere without spanning the entire
   chromosome.
3. **LST (large-scale state transitions)** — count of chromosomal
   break-junctions between adjacent segments each ≥10 Mb, after smoothing
   away segments <3 Mb.
4. **Composite Genomic Instability Score (GIS) = HRD-LOH + TAI + LST.**
   **HRD-positive threshold: GIS ≥ 42** — copied verbatim from
   `BENCHMARKS.tsv` row `HRD03` (Telli et al. 2016), clinically validated
   in row `HRD04` (PAOLA-1, Ray-Coquard et al. 2019 NEJM). This protocol
   does not use any other GIS cut-point.

### 5.4 Signature tools and COSMIC versions

- **SigProfilerAssignment v1.1.5** (`ENVIRONMENT.lock` §2, `GATE1.json`
  PASS). COSMIC signature reference set: pinned to the version bundled
  with/downloadable by this exact package build at Stage 0 execution
  time, confirmed live and logged (its own internal reference-data
  version may lag the general COSMIC release cadence in
  `ENVIRONMENT.lock` §3, v104 as of 2026-05-18 — do not assume they match
  without checking at run time; log both version strings). Feature
  extracted: cosine-similarity-based relative exposure of COSMIC SBS3
  (homologous-recombination-deficiency signature) per sample.
- **SigMA — BLOCKED.** `GATE1.json` records `status: "FAIL"` for SigMA
  (R CMD INSTALL failed: `BSgenome.Hsapiens.UCSC.hg19` unavailable,
  confirmed 2026-09-07). This protocol specifies SigMA's intended feature
  (a likelihood-based Signature-3 match score plus its multivariate
  `Signature_3_mva` score) for when the tool becomes available, but **no
  Stage of this protocol that includes a SigMA-derived feature may run
  until `GATE1.json` is re-executed and SigMA shows `status: "PASS"` with
  recorded test output.** Any stratum's output that would depend on a
  SigMA feature is populated with the literal string `BLOCKED` (Standing
  Rule 1's permitted status vocabulary) rather than omitted or
  substituted with another tool's output.

### 5.5 Second-hit sources (ordered; all available sources logged, not just the first)

1. **Locus-specific LOH favoring mutant retention** — `LOH_SECOND_HIT`
   per §5.1.
2. **A second somatic P/LP variant in the same gene, same tumor** —
   nonsense, frameshift, canonical splice (±1/2), or a variant itself
   ClinVar-classified P/LP (per the §4.1 review-status floor), found in
   the tumor-only masked somatic MAF (Track A open tier).
3. **Promoter hypermethylation — DISABLED in this protocol version.**
   Track A's open-tier methylation array data cannot resolve which allele
   (mutant vs wild-type) is silenced without haplotype-phasing data this
   protocol does not have access to. This source is not attempted; every
   run logs `"source 3 (promoter methylation): DISABLED, Track A data
   insufficient for allele-specific resolution"` explicitly, rather than
   silently skipping it.

A (patient, gene) pair with neither source 1 nor 2 present is classified
`NO_SECOND_HIT_DETECTED` — an explicit due-diligence-negative result,
never conflated with "no second hit exists."

---

## 6. ESTIMAND DECLARATION

**The target quantity of this protocol is a likelihood ratio (LR), not an
odds ratio (OR).**

```
LR(E) = P(E | Pathogenic) / P(E | Benign)
```

where `E` is the observed evidence feature vector for one germline variant
(LOH category §5.1, HRD-positive status §5.3, SigProfilerAssignment SBS3
exposure §5.4, second-hit status §5.5), and `Pathogenic`/`Benign` are the
two mutually exclusive reference classes defined in §4.

**How this differs from an odds ratio, stated explicitly because the two
are easy to conflate:**

- An **odds ratio** compares the *odds of an outcome* between two exposure
  groups: `OR = [P(outcome|exposed)/P(no-outcome|exposed)] /
  [P(outcome|unexposed)/P(no-outcome|unexposed)]`. It requires a binary
  outcome with a well-defined complement (`P(no-outcome)`), and both its
  numerator and denominator are themselves ratios of complementary
  probabilities *within* one exposure stratum.
- The **LR** here is a ratio of two *conditional likelihoods of the same
  observed evidence* under two competing *hypotheses about variant class*
  — it is not conditioned on an "exposure," and `P(not E)` never enters
  the calculation.
- Practically: an LR combines *multiplicatively* with a prior odds of
  pathogenicity via Bayes' theorem (`posterior odds = prior odds × LR`),
  which is exactly the mechanism of the Tavtigian et al. 2018 Bayesian
  ACMG/AMP framework and its OddsPath thresholds (`BENCHMARKS.tsv`
  ODDS01/ODDS02). An OR has no such direct Bayesian-updating
  interpretation and is **not on the same numeric scale** as the OddsPath
  thresholds.

**Every later comparison in this protocol — Stage 1 estimation (§10),
Stage 2 recovery (§11), the ACMG mapping (§9) — compares an LR (or an LR
confidence bound) against another LR or an LR-derived threshold. No odds
ratio is computed, reported, or substituted for an LR anywhere in this
protocol.**

---

## 7. Model spec, cross-validation, bootstrap

### 7.1 Model

For each feature independently, and for the joint feature vector, the LR
is estimated as a **class-conditional likelihood ratio** (not a
discriminative classifier):

- **Continuous features** (GIS score, SigProfilerAssignment SBS3
  exposure): `f_hat(E|class)` estimated by Gaussian kernel density
  estimation, one KDE fit on the Pathogenic reference set and one on the
  Benign reference set, per feature.
- **Categorical features** (LOH category, second-hit status): `P(E|class)`
  estimated as the empirical proportion within each reference class, with
  a Jeffreys `+0.5` continuity correction applied to every cell (so no
  category with zero observed reference-class members yields an
  undefined/infinite LR).
- **Joint feature vector:** the product of per-feature LRs, under a
  conditional-independence assumption given class. This assumption is
  tested and reported (not assumed silently): pairwise feature
  correlations are computed within each reference class and reported
  alongside every joint LR; no joint LR is reported without its
  supporting correlation diagnostic.

### 7.2 Cross-validation

**Variant-grouped k-fold, k = 5.** Folds are assigned by unique variant
identifier (`chromosome:position:reference:alternate`, GRCh38 coordinates)
so every tumor observation of a recurrent variant (e.g. a founder
mutation seen in multiple patients) stays in a single fold — never split
across folds. Folds are stratified to preserve the Pathogenic:Benign
class ratio within ±5 percentage points of the full-set ratio.

### 7.3 Patient-clustered bootstrap

**Nonparametric cluster bootstrap at the patient level, with replacement,
replicate count B = 2000.** Used to build the 95% CI (2.5th/97.5th
percentile — a percentile bootstrap, not BCa) for every reported LR.
Clustering is at the **patient**, not the variant or observation, level:
a patient can contribute observations to more than one gene-group
analysis (§1.3) if they carry variants in both gene lists, and those
observations share tumor-level nuisance variance (purity-estimate error,
sequencing batch) that variant- or observation-level resampling would
treat as independent when it is not.

---

## 8. Stratification

**Primary stratification: gene group (§1) × PAM50 subtype.** PAM50
subtype categories are the five used in `BENCHMARKS.tsv` row `PAM01`
(Luminal A, Luminal B, HER2-enriched, Basal-like, plus Normal-like as a
sixth category not separately benchmarked but retained as a stratum) — up
to 2 × 5 = 10 strata.

**Secondary stratification, only where n permits (§8's minimum-class-size
rule below): per gene within its gene group**, each further crossed with
PAM50 subtype only if that per-gene × subtype cell itself clears the
minimum class size. 9 CORE_HR genes + 8 DDR_SIGNALING genes = 17
additional single-gene strata.

**Minimum class size: n < 20** reference-class observations (Pathogenic +
Benign combined) in a stratum → that stratum's LR and CI are **not
fit**. The output for that stratum prints the literal string
`INSUFFICIENT_N` in the LR and CI fields, with the actual observed `n`
reported alongside — never a silently blank or omitted row. This n = 20
threshold applies identically at every stratification level (gene-group ×
subtype and per-gene).

---

## 9. ACMG mapping from the CI lower bound at the OddsPath thresholds

**Bound used:** for evidence toward **pathogenicity**, use the **CI lower
bound** (2.5th percentile, §7.3) of the estimated LR — the conservative
bound on the side away from the null. For evidence toward **benign**, use
the **CI upper bound** (97.5th percentile) — likewise the conservative
bound on the side away from the null in that direction. Using the bound
on the wrong side (e.g. the upper bound for a pathogenic call) is a
common error this protocol explicitly forbids.

Thresholds copied verbatim from `BENCHMARKS.tsv` rows `ODDS01`/`ODDS02`
(Tavtigian et al. 2018):

| CI bound condition | ACMG-equivalent call | Evidence points |
|---|---|---|
| CI lower bound > 350 | `PATHOGENIC_VERY_STRONG` | 8 |
| 350 ≥ CI lower bound > 18.7 | `PATHOGENIC_STRONG` | 4 |
| 18.7 ≥ CI lower bound > 4.33 | `PATHOGENIC_MODERATE` | 2 |
| 4.33 ≥ CI lower bound > 2.08 | `PATHOGENIC_SUPPORTING` | 1 |
| CI lower bound ≤ 2.08 **and** CI upper bound ≥ 0.48 | `NO_EVIDENCE` | 0 |
| CI upper bound < 0.48 and ≥ 0.053 | `BENIGN_SUPPORTING` | 1 (benign) |
| CI upper bound < 0.053 | `BENIGN_STRONG` | 4 (benign) |

**No `BENIGN_VERY_STRONG` category exists in this protocol.**
`BENCHMARKS.tsv` row `ODDS02` provides only the supporting and strong
benign-direction reciprocals (0.48 = 1/2.08 and 0.053 = 1/18.7); no
benign-direction reciprocal of 350 was retrieved with a citation this
session. Per Standing Rule 3, this protocol does not compute or use an
un-cited `1/350 ≈ 0.00286` "very strong benign" cut-point — a CI upper
bound below 0.053 is reported as `BENIGN_STRONG` and no stronger, with a
note that a very-strong-benign tier is undefined pending that citation.

---

## 10. Pre-specified interpretation of every outcome, including the null

This section is fixed **before** any data is examined, per the definition
of pre-registration and Standing Rule 2 ("A validation is a comparison
against a target fixed in advance").

- **`PATHOGENIC_*` / `BENIGN_*` (any tier, §9):** the corresponding ACMG
  evidence points are reported as one input to an eventual ACMG
  classification; this protocol does **not** itself issue a final
  ACMG classification (Pathogenic/Likely Pathogenic/VUS/Likely
  Benign/Benign) — that requires combining this LR-derived evidence code
  with the variant's other, non-tumor-derived ACMG evidence, which is out
  of scope here.
- **`NO_EVIDENCE`:** the CI spans the null (does not exclude LR = 1 in
  either the pathogenic or benign direction at the lowest, 2.08/0.48,
  threshold). This is reported as exactly that — no evidence either way
  at the current sample size — never as "trends toward" pathogenic or
  benign. Per Standing Rule 2, a result whose interval includes the null
  is not described with success language.
- **`INSUFFICIENT_N` (§8):** the stratum was not testable at n ≥ 20; this
  is reported as untestable, explicitly distinct from `NO_EVIDENCE` (which
  means "tested, found no signal") — the two must never be conflated in
  any summary table or narrative.
- **`BLOCKED` (§5.4, SigMA):** the corresponding feature/Stage could not
  be computed because a required tool is not installed (`GATE1.json`
  FAIL). This is reported with the same prominence as a completed result
  (Standing Rule 8), not folded into `INSUFFICIENT_N` or `NO_EVIDENCE`
  (those mean something was tested; `BLOCKED` means it could not be).
- **If most strata return `NO_EVIDENCE`:** interpreted as "insufficient
  evidence at current sample size to support or refute the hypothesized
  association between these tumor features and germline variant class in
  these genes" — explicitly **not** interpreted as "these tumor features
  are not informative for classification" (absence of evidence is not
  evidence of absence, stated here so it cannot be silently relitigated
  after seeing results).
- **If Stage 2 (§11) returns mostly `SIMULATED_FAIL`:** interpreted as "the
  LR-estimation pipeline is not adequately calibrated to trust on real
  data." Consequence, fixed now: **Stage 1 (§10.1, real-data) results may
  not be reported as reliable, and no ACMG mapping (§9) may be issued from
  them, until Stage 2 passes** (a majority of tested strata return
  `SIMULATED_PASS`, with none of the gene-group-level primary strata
  failing). This is a hard gate on the order of operations, fixed here
  before any Stage 1 result exists.

### 10.1 Stage 1 (real data)

Executed only once (a) `TRACK.md` records an APPROVED authorization for
the germline-variant data this protocol needs (Track B, or a future
Track A extension that includes germline calls), (b) `GATE1.json` shows
`gate1_result: "PASS"` (currently `FAIL`, blocking on SigMA), and (c)
Stage 2 (§11) has passed per the gate above. None of these three
conditions is met today; Stage 1 does not run under this protocol version.

---

## 11. Stage 2 — synthetic recovery test and RECOVERY TOLERANCE

Stage 2 injects a **known, pre-specified target LR** into a synthetic
feature dataset (generated under the same model form as §7.1, with class
sizes matching the minimum-n rule in §8) and re-runs the full estimation
pipeline (§7) to test whether it recovers that target.

**Standing Rule 1 applies in full to every Stage 2 artifact:** every
output filename contains `SIMULATED`; the first line of every Stage 2
report reads `SIMULATED DATA — NOT A SCIENTIFIC RESULT`; every caption
begins `SIMULATED:`; **no ACMG evidence strength (§9) is assigned to any
Stage 2 output** — the `PATHOGENIC_*`/`BENIGN_*`/`NO_EVIDENCE` vocabulary
of §9 is reserved for Stage 1 only. Stage 2 uses exclusively `SIMULATED`,
`SIMULATED_PASS`, `SIMULATED_FAIL`, `BLOCKED`.

### RECOVERY TOLERANCE — fixed now, before any Stage 2 data exists

A Stage 2 stratum is marked **`SIMULATED_PASS`** if and only if **both**:

1. **Interval containment:** the recovered 95% CI (patient-clustered
   bootstrap, B = 2000, percentile method — identical procedure to §7.3)
   contains the injected target LR value.
2. **Relative bias bound:** `|LR_hat − LR_true| / LR_true ≤ 0.25` (25%),
   where `LR_hat` is the full-sample point estimate (not the bootstrap
   mean) and `LR_true` is the pre-specified injected value.

**Outcome rules:**
- Both (1) and (2) hold → `SIMULATED_PASS`.
- (1) holds but (2) fails → `SIMULATED_FAIL`, with the exact relative-bias
  value reported (never rounded away or omitted).
- (1) fails (CI excludes the injected target) → `SIMULATED_FAIL`
  regardless of (2) — per Standing Rule 2, an interval that excludes its
  target is a failed validation and is reported as `SIMULATED_FAIL`, not
  as "approximately recovered" or any success-adjacent language.
- The stratum's simulated class sizes fall below the §8 minimum (n < 20)
  → `INSUFFICIENT_N`, not `SIMULATED_FAIL` — an untestable configuration
  is not a failed one.

No other tolerance value (e.g. a looser or stricter relative-bias bound,
or a different CI method) is used in this protocol; 0.25 and the
percentile-bootstrap CI from §7.3 are the only recovery criteria.

---

## 12. Summary of what is BLOCKED today, stated up front (Standing Rule 8)

- **All of Stage 1 (§10.1)** — no germline variant data is authorized
  (Track B, per `TRACK.md`) and `GATE1.json` is FAIL.
- **Every SigMA-dependent feature (§5.4)** — until `GATE1.json` is
  re-executed and shows SigMA `PASS`.
- **Promoter-methylation second-hit evidence (§5.5, source 3)** —
  disabled for this protocol version; Track A data cannot resolve it.
- **The BRCA-stratified HGSOC HRD-high percentage** — `BENCHMARKS.tsv`
  row `HRD05` is `NOT_FOUND`; any control that would compare our
  BRCA-mutant-vs-wild-type HRD-high rate against a published split cannot
  run until that benchmark is resolved.
- **Direct comparison against the published per-sample TCGA HRD/DDR score
  table** — `BENCHMARKS.tsv` row `DDR02` is `NOT_FOUND` (no live-resolving
  download location); only the summary statistics in `DDR01` are usable
  today.

Stage 2 (§11, synthetic-data recovery testing) is **not** blocked by any
of the above and may proceed once this protocol is reviewed and tagged,
since it requires no real data and no controlled-access authorization.

---

*End of protocol body. Per the task's HALT instruction, this file is the
stopping point — no `v0.1-preregistered` git tag is created by this
session; that is a human reviewer's action after reading this document.*
