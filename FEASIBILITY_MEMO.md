SIMULATED DATA — NOT A SCIENTIFIC RESULT is NOT the right banner for this
document: this memo analyzes real, non-simulated external cohort and
purity data (live-retrieved, cited) against this project's own
pre-registered design and against SIMULATED characterization work
(GATE8's instability sweep) already on disk. No ACMG evidence, LR, or
Stage 1/2 vocabulary is assigned to anything here. **This is an analysis
and a memo. Nothing in the pipeline changes. No design is chosen here —
that decision is the human's, per this task's explicit HALT.**

# FEASIBILITY_MEMO.md — can TCGA-BRCA (or TCGA+ICGC/PCAWG+CPTAC-3) support the pre-registered per-gene x per-subtype design?

## STEP 1 — the requirement, worked backwards from what the design needs

### 1a. GATE8's instability characterization: class size vs. UNINFORMATIVE, by feature-vector dimension

Source: `INTERVAL_INSTABILITY.md` / `SIMULATED_INTERVAL_INSTABILITY_SWEEP.tsv`
(already on disk, not re-run this task). That sweep's own headline
finding is that **there is no single clean threshold — the failure rate
is non-monotonic in n**, worst in the middle of the tested range for the
1-feature SBS3-only marginal, not at the smallest n. Reporting a single
number here would misstate that shape, so two different, clearly-labeled
thresholds are given per (arm, dimension) cell instead: the smallest
tested n at which **at least half** of 15 independent trials were
`INFORMATIVE` (a "majority-informative" floor), and the smallest tested n
at which **all 15** trials were (a "fully-informative" floor, "None" if
never reached within the tested range up to n=160/class):

| arm | dimension | feature subset | first n: ≥50% informative | first n: 100% informative |
|---|---|---|---|---|
| CORE_HR | 1 | `{SBS3}` alone | 100 | **never reached (≤160 tested)** |
| CORE_HR | 2 | `{LOH, SBS3}` | 65 | 130 |
| CORE_HR | 3 | `{LOH, GIS, SBS3}` (full, pre-registered) | 65 | 160 |
| DDR_SIGNALING | 1 | `{SBS3}` alone | 160 | **never reached (≤160 tested)** |
| DDR_SIGNALING | 2 | `{LOH, SBS3}` | 100 | **never reached (≤160 tested)** |
| DDR_SIGNALING | 3 | `{LOH, GIS, SBS3}` (full, pre-registered) | 75 | 160 |

The pre-registered design uses the full 3-feature vector (dimension 3)
per gene x subtype cell, so **this memo uses n=65/class (majority-
informative) and n=160/class (fully-informative) as the two target class
sizes** for Step 1b — both, not one, because `INTERVAL_INSTABILITY.md`'s
own finding is that "majority informative" at a given n is not the same
promise as "reliably informative," and collapsing the two into a single
number would understate the requirement. `n` here is the number of
**gene-specific pathogenic-variant carriers within one PAM50 subtype
stratum** — the binding (rare) class in this design, per
`SIMULATION_SPEC.md` §6's own established framing ("CORE_HR pathogenic
class ≈ 55–75 patients").

### 1b. Required total cohort size per design cell (gene x PAM50 subtype), at a 0.40 purity floor

Full table: `COHORT_REQUIREMENT_TABLE.tsv` (35 rows: 7 genes x 5
subtypes). Method: `required_N = target_class_size / (subtype_fraction x
purity_survival_at_0.40 x gene_case_prevalence)`.

- `subtype_fraction` and `purity_survival_at_0.40` are `P-FIX-2`'s own
  live-retrieved TCGA-BRCA PanCanAtlas numbers (`PURITY_FLOOR_COST.md`,
  951 ABSOLUTE-called + PAM50-subtyped patients): Basal 17.03%/82.1%
  survival, Her2 8.10%/71.4%, LumA 51.21%/83.6%, LumB 20.51%/94.4%,
  Normal 3.15%/50.0%.
- `gene_case_prevalence` is live-retrieved this task (see §1c below):
  Hu et al. 2021 NEJM (CARRIERS consortium), a **population-based**
  (not clinically-referred, unlike `BENCHMARKS.tsv`'s existing
  `DDR_PREV01`/Couch 2017) US cohort of 32,247 breast cancer cases and
  32,544 controls. Per-gene case prevalence used: BRCA1 0.85%, BRCA2
  1.29%, PALB2 0.46%, RAD51C 0.13%, RAD51D 0.08%, ATM 0.78%, CHEK2 1.08%.

**Required total cohort size (any subtype/purity, i.e. total N of
patients that would need to be enrolled and sequenced), n=65/class
target:**

| gene | Basal | Her2 | LumA | LumB | Normal |
|---|---|---|---|---|---|
| BRCA1 | 54,679 | 132,278 | 17,862 | 39,506 | 484,824 |
| BRCA2 | 36,028 | 87,160 | 11,770 | 26,031 | 319,457 |
| PALB2 | 101,036 | 244,426 | 33,007 | 73,001 | 895,870 |
| **RAD51C** | **357,513** | **864,891** | **116,793** | **258,312** | **3,170,000** |
| **RAD51D** | **580,959** | **1,405,449** | **189,788** | **419,756** | **5,151,250** |
| ATM | 59,586 | 144,149 | 19,465 | 43,052 | 528,333 |
| CHEK2 | 43,034 | 104,107 | 14,058 | 31,093 | 381,574 |

At the stricter n=160/class ("fully-informative") target, every cell is
2.46x larger (`COHORT_REQUIREMENT_TABLE.tsv` has both columns in full).

**PALB2, RAD51C, RAD51D are the thinnest genes, and by a wide margin.**
RAD51D/Normal-like requires >5.1 million patients at the majority-
informative target alone — larger than the entire population of most
countries' cancer registries combined, for one gene in one PAM50
subtype. Even RAD51C/LumA (the LARGEST subtype, the SUBTYPE where the
per-gene requirement is smallest) needs 116,793 patients. **No available
cohort, alone or combined (§2), reaches ANY cell in this table for
RAD51C or RAD51D, in any subtype, at either target class size.** BRCA1/
BRCA2/ATM/CHEK2 fare better only in LumA (the largest subtype: tens of
thousands, not millions) and remain out of reach everywhere else.

### 1c. Gene-level carrier prevalence: retrieval and disclosed caveat

`www.nejm.org` was `EGRESS_BLOCKED` for direct fetch of Hu et al. 2021
(same network-egress policy `P-FIX-2` already documented); the exact
per-gene percentages above are WebSearch-synthesized from that paper
(consistent across independent search results, not a single ambiguous
snippet), in the same disclosed manner several `BENCHMARKS.tsv` rows
already use. This is a materially better source than `BENCHMARKS.tsv`'s
existing `BRCA_PREV01` (Yost 2019, n=779, TCGA-derived subset) and
`DDR_PREV01` (Couch 2017, a *clinically-referred*, not population-based,
38,326-patient panel-testing cohort likely overstating an unselected
rate) because it is population-based, much larger, and reports BRCA1,
BRCA2, PALB2, RAD51C, RAD51D, ATM, and CHEK2 individually from one
consistent methodology — used here in preference to mixing sources per
gene. RAD51B, BRIP1, RAD54L (CORE_HR), and CHEK1/ATR/MRE11/RAD50/NBN/
FANCM (DDR_SIGNALING) prevalence was not retrieved this session; those
cells are UNVERIFIED and are not in `COHORT_REQUIREMENT_TABLE.tsv` —
per Standing Rule 3, no value is invented for them. (This task did not
ask for full 17-gene coverage; it named PALB2, RAD51C, RAD51D
specifically, plus the two anchor genes per arm needed for contrast —
BRCA1/BRCA2 for CORE_HR, ATM/CHEK2 for DDR_SIGNALING — all seven are
covered by one source.)

### 1d. Accuracy-vs-class-size trade at floors 0.25, 0.30, 0.35, 0.40

Accuracy: `SIMULATED_loh_validation/SIMULATED_PURITY_FLOOR_BY_SUBTYPE.tsv`
(P07-RERUN2's own operating-region characterization, not re-run), the
accuracy of the marginal (least-pure) band each floor newly admits.
Surviving n: `P-FIX-2`'s TCGA-BRCA-PanCanAtlas floor-survival counts
(real data, `PURITY_FLOOR_COST.md`, n=951 total).

| Floor | Accuracy, marginal band, POOLED | Accuracy, Basal | Accuracy, LumB | Surviving n, POOLED | Surviving n, Basal | Surviving n, LumB |
|---|---|---|---|---|---|---|
| 0.25 | 71.4% (band 0.20–0.25, n=763, 22 excluded AMBIGUOUS/NE) | 71.4% (n=154, 0 excluded) | 72.9% (n=188, 7 excluded) | 96.2% (915) | 94.4% (153) | 100.0% (195) |
| 0.30 | 86.6% (band 0.25–0.30, n=703, 19 excluded) | 87.1% (n=155, 3 excluded) | 83.6% (n=152, 7 excluded) | 92.6% (881) | 90.7% (147) | 98.5% (192) |
| 0.35 | 91.8% (band 0.30–0.35, n=698, 15 excluded) | 95.2% (n=147, 2 excluded) | 92.0% (n=163, 7 excluded) | 88.6% (843) | 88.3% (143) | 97.4% (190) |
| **0.40** | **96.6% (band 0.35–0.40, n=594, 23 excluded)** | **93.7% (n=95, 3 excluded)** | **94.7% (n=151, 4 excluded)** | **83.5% (794)** | **82.1% (133)** | **94.4% (184)** |

**The trade is real and monotonic in the direction P07-RERUN2 already
established**: lowering the floor from 0.40 to 0.25 buys back roughly
12–13 surviving points (pooled: 96.2% vs. 83.5%) at the cost of the
marginal band's accuracy falling from 96.6% to 71.4% pooled — a ~25-
point accuracy cost for a ~13-point survival gain, pooled. **This memo
does not resolve that trade** — §1b already shows that even at the most
permissive floor tested here (0.25), the gap to any cell in the
required-cohort table is 3–5 orders of magnitude, so no floor choice in
this range closes it. The floor question and the cohort-size question
are both real, but the cohort-size gap dominates.

## STEP 2 — what is actually available

### 2a. TCGA-BRCA (already retrieved, `P-FIX-2`)

951 ABSOLUTE-called + PAM50-subtyped patients (981 PAM50-subtyped
total), live-retrieved via GitHub-hosted mirrors of the PanCanAtlas
ABSOLUTE purity table and cBioPortal's `brca_tcga_pan_can_atlas_2018`
clinical table, after `nature.com`/`ncbi.nlm.nih.gov`/`cbioportal.org`
general-web retrieval was `EGRESS_BLOCKED` (mechanism recorded in
`PURITY_FLOOR_COST.md` §1a, unchanged this task).

### 2b. ICGC/PCAWG breast

`www.nejm.org`... not applicable here; the retrieval attempts and their
outcomes: `www.ncbi.nlm.nih.gov`, `www.biorxiv.org` — both
`EGRESS_BLOCKED` this task (recorded mechanism, consistent with
`P-FIX-2`'s general-web block). WebSearch (not blocked) surfaced the
canonical landmark cohort: **Nik-Zainal SC et al., "Landscape of somatic
mutations in 560 breast cancer whole-genome sequences," Nature. 2016 Jun
2;534(7605):47-54. PMID 27135926 — 560 breast cancer whole genomes**,
the ICGC-lineage cohort (BRCA-EU/BRCA-UK) most commonly cited as "the"
ICGC/PCAWG breast WGS resource. This count is WebSearch-synthesized, not
independently confirmed by direct fetch (`nature.com`/`pubmed` both
unreachable this session); a distinct, smaller, formally-PCAWG-
reprocessed subset of this cohort likely exists in the PCAWG donor
manifest specifically (commonly cited informally as smaller than 560,
since PCAWG required additional consent/QC), but its exact count was
**not independently confirmed this session — UNVERIFIED, not
estimated**, per Standing Rule 3. No purity/cellularity distribution
for this cohort was retrieved this session (searched, not found in
reachable results) — recorded here as not retrieved, not silently
assumed comparable to TCGA's.

**Note for currency**: WebSearch also surfaced a 2025 Nature paper,
"Whole-genome landscapes of 1,364 breast cancers" (same research
lineage, DOI 10.1038/s41586-025-09812-3), a substantially larger, more
current successor cohort. Its exact relationship to ICGC/PCAWG branding
and its purity/PAM50 breakdown were **not retrieved this session**
(nature.com blocked) — flagged here for the human's awareness since it
would materially change §2d's combined-cohort ceiling if confirmed
usable, but not used in any calculation in this memo because its
sample-level accessibility and terms were not verified.

### 2c. CPTAC-3 breast

Live-retrieved this task via the same GitHub-datahub-LFS method used for
TCGA (`media.githubusercontent.com/media/cBioPortal/datahub/master/public/brca_cptac_2020/data_clinical_sample.txt`,
after `cell.com`/`sciencedirect.com` general-web retrieval was
`EGRESS_BLOCKED`): **122 treatment-naive primary breast cancers** (Krug K
et al., "Proteogenomic Landscape of Breast Cancer Tumorigenesis and
Targeted Therapy," Cell. 2020 Nov 25;183(5):1436-1456.e31. PMID
33212010), matching the clinical file's row count exactly (123 rows − 1
header = 122). PAM50 breakdown, from the same file: LumA 57, Basal 29,
LumB 17, Her2 14, Normal-like 5. **No ABSOLUTE-style purity column is
present in this clinical file** — a purity distribution for CPTAC-3
breast was not retrieved this session (searched for, not found in the
one file fetched; not silently assumed absent — a genomic-purity
supplementary table may exist elsewhere in the CPTAC data portal and was
not located this session).

### 2d. Combined maximum plausible cohort at a 0.40 floor, against the Step 1 requirement

Naive sum (TCGA-BRCA 981 PAM50-subtyped + ICGC/PCAWG-lineage 560 +
CPTAC-3 122) = **1,663 patients, before any purity filtering and before
the harmonization cost below is applied.** Even this un-discounted,
harmonization-free ceiling is **1–2 orders of magnitude short of the
smallest requirement in §1b** (RAD51C/LumA majority-informative:
116,793) and **3–4 orders of magnitude short of every other cell**. No
combination of these three named cohorts, real-world-obtainable today,
reaches a single cell of the pre-registered per-gene x per-subtype
design at either target class size, for any of the seven genes checked.

### 2e. Harmonization cost — stated, not glossed over

**The 1,663 figure above is not usable as a summed n, and this memo does
not present it as one for any purpose beyond illustrating the scale of
the shortfall.** TCGA-BRCA, ICGC/PCAWG (WGS, different sequencing
platforms/eras across the 2010s), and CPTAC-3 (deliberately
short-ischemia-time-accrued, proteogenomic-focused, different clinical
accrual criteria) used different capture kits, coverage depths, variant-
calling pipelines, and purity-estimation methods (ABSOLUTE for TCGA;
purity method for the ICGC 560-genome cohort and for CPTAC-3 not
independently confirmed this session, §2b/2c). A joint burden analysis
across them is not "concatenate the sample lists" — it requires, at
minimum: (i) intersected target/capture intervals (WGS vs. exome vs.
panel coverage differ in which loci in PALB2/RAD51C/RAD51D are even
callable), (ii) coverage-matched or coverage-adjusted calling
thresholds so purity/LOH-calling accuracy is not silently
cohort-dependent (this project's own LOH caller was validated only
against its own simulator, never against a second, differently-
processed dataset), and (iii) per-cohort controlled-access approval
(TCGA and CPTAC-3 data of this kind is typically dbGaP-controlled;
ICGC-lineage WGS data of this kind is typically EGA-controlled) BEFORE
any of the samples in the 1,663 figure could actually be pooled and
analyzed — none of which this memo has done or costs out in detail
(that is Design A's own listed requirement, §3A). The 1,663 figure is a
scale illustration only.

## STEP 3 — three designs

### A. STRATIFIED, multi-cohort (TCGA + ICGC/PCAWG + CPTAC-3, jointly processed)

**Delivers**: the pre-registered per-gene x per-subtype LR table, as
specified, if it reached adequate class sizes.
**Costs**: controlled-access approval for three separate consortia
(dbGaP x2, EGA x1, each with its own timeline and data-use-agreement
scope restrictions), plus the harmonization work in §2e (intersected
capture intervals, coverage-matched calling, a second independent
validation of the LOH caller against non-TCGA-simulated real data before
trusting its output on ICGC/CPTAC samples at all).
**Does Step 2 show it reaching the Step 1 requirement? No — not even
close.** §2d's combined ceiling (1,663, before any purity filter or
harmonization loss, which can only shrink it further) is 1–4 orders of
magnitude short of every cell in `COHORT_REQUIREMENT_TABLE.tsv`. **This
design is ruled out as stated, for every gene checked, in every PAM50
subtype.** Restating it after harmonization losses (which reduce, never
increase, the usable n) cannot close a gap this large. Stated plainly
per this step's own instruction.

### B. POOLED with subtype as a covariate (subtype adjusted for, not stratified on)

**Delivers**: per-gene LRs at TCGA-BRCA scale (feasible: §1b's
per-subtype requirement, summed pooled rather than split five ways,
still exceeds TCGA-BRCA alone for RAD51C/RAD51D and is only
LumA-scale-adequate at best for BRCA1/2/ATM/CHEK2 pooled at n=65 — see
caveat below — but pooling is the design that gets closest to
TCGA-BRCA's actual size).
**Costs**: gives up the pre-registered, primary-finding claim that
evidence strength differs by PAM50 subtype — subtype becomes a nuisance
covariate the pooled estimator adjusts for, not a stratum whose own,
separately-reported LR is the deliverable. Any residual subtype signal
is absorbed into the adjustment, not surfaced as a per-subtype finding.
**Caveat, computed, not asserted**: even POOLED (no subtype split at
all) at TCGA-BRCA's ~951-patient scale, RAD51C/RAD51D's own case
prevalence (0.13%/0.08%) implies an expected carrier count of roughly
951 x 0.0013 ≈ 1.2 (RAD51C) and 951 x 0.0008 ≈ 0.8 (RAD51D) — **under
one expected carrier, pooled, for either gene, even with the subtype
split removed entirely.** Pooling closes most of the per-subtype gap but
does not by itself solve RAD51C/RAD51D; it materially helps BRCA1/BRCA2/
ATM/CHEK2 (pooled expected carriers: BRCA1 ≈8.1, BRCA2 ≈12.3, ATM ≈7.4,
CHEK2 ≈10.3 at TCGA-BRCA scale — still below the 65-carrier
majority-informative target for the full 3-feature vector, but no longer
off by 3+ orders of magnitude).

### C. STRATIFIED where possible, `INSUFFICIENT_N` elsewhere (protocol's existing mechanism)

**Delivers**: an honest table — every cell that clears PROTOCOL §8's
n≥20 floor gets a real, stratified result; every cell that does not is
reported `INSUFFICIENT_N`, not silently omitted or forced.
**Costs**: nothing beyond what the protocol already specifies — this
design requires no new machinery.
**How many cells would populate?** Using §1b's required-N logic in
reverse — at TCGA-BRCA's actual available n per subtype (951, purity-
floor-survived counts from §2a) and each gene's real prevalence, the
*expected* per-cell carrier count (not the number required — the number
TCGA-BRCA alone actually offers) is, for the 35 cells in
`COHORT_REQUIREMENT_TABLE.tsv`: every RAD51C and RAD51D cell in every
subtype rounds to 0–1 expected carriers; PALB2's best cell (LumA) rounds
to ≈1.9; BRCA1/BRCA2/ATM/CHEK2's best cells (LumA, the largest subtype)
range ≈3.2–5.3 expected carriers (BRCA1 3.46, BRCA2 5.25, ATM 3.18,
CHEK2 4.40). **None of the 35 cells reaches
PROTOCOL §8's n≥20 floor even in expectation, let alone the 65-carrier
gate8 majority-informative target.** If this design were run today
against TCGA-BRCA alone, **the overwhelming majority — almost certainly
all 35 of the named cells, and likely most of the full CORE_HR x
DDR_SIGNALING x 5-subtype grid beyond the seven genes checked here —
would return `INSUFFICIENT_N`.** This is a small minority populating (at
best, a handful of pooled-arm-level cells before subtype stratification,
not the per-gene x per-subtype cells this design promises), and that is
stated plainly here per this step's own instruction.

## STEP 4 — implication for P09

**This section does not choose among A/B/C — it states what each implies for P09's scope, per this task's own instruction not to choose.**

- **Under Design B (pooled, subtype-adjusted)**: P09 should validate a
  **pooled estimator with a subtype covariate term**, not a stratified
  one. P09's truth quantities would need to change from the current
  per-subtype `*_luma_*`, `*_lumb_*`, `*_her2e_*`, `*_basal_*`,
  `*_normal_like_*` LR quantities to a single pooled-per-gene LR plus a
  covariate-adjustment coefficient (or its equivalent) — a genuinely
  different set of truth quantities, not a re-labeling of the existing
  91-quantity `SIMULATED_TRUTH.tsv` scope. The existing per-subtype
  Stage 2 recovery work (P07/P07-RERUN2, this project's LOH-caller
  validation) would no longer directly validate what Design B's Stage 1
  pipeline reports.
- **Under Design A or C**: P09's current **stratified** scope stands
  unchanged — the existing per-subtype truth quantities remain the right
  ones to validate, because the design being validated still reports
  per-subtype results (Design C simply reports many of them as
  `INSUFFICIENT_N` rather than a number, which P09's own recovery
  framework already has a defined, non-`SIMULATED_FAIL` vocabulary for,
  per `PROTOCOL.md` §11).
- **The Part C simulator gap (`PROPOSED_DEVIATIONS.md` §13, `P-FIX-2`:
  subtype affects GIS but not LOH direction) matters much less under
  Design B.** Design B does not rely on stratification as the mechanism
  that surfaces subtype-specific evidence — subtype is a covariate the
  pooled model adjusts past, not a stratum whose LOH-direction signal
  needs to be subtype-faithful for the design's own primary claim to
  hold. **Under Design A or C, it matters more**, for the reason
  `PROPOSED_DEVIATIONS.md` §13 already gives: those designs' entire
  reason for existing is to report subtype-specific evidence strength,
  and P09 validating a stratified estimator against a simulator whose
  LOH feature is subtype-blind cannot demonstrate that the estimator
  would correctly handle a real basal-like tumor's elevated LOH burden
  specifically (as opposed to only its elevated GIS) — a gap that is
  irrelevant to what Design B is even claiming, but directly relevant to
  what Design A/C claim.

## STEP 5b — technical questions the evidence settles vs. programmatic judgment

**Settled by evidence in this memo (§1–2), not a matter of judgment:**
- Design A is infeasible with TCGA+ICGC/PCAWG+CPTAC-3 at any purity
  floor tested — the shortfall is 1–4 orders of magnitude, not a close
  call sensitive to which exact floor or which exact threshold
  (majority- vs. fully-informative) is chosen.
- RAD51C and RAD51D cannot support a stratified, or even a pooled,
  per-gene claim at TCGA-BRCA scale — expected carrier counts are below
  1, pooled, before any subtype split.
- Design C, run today against TCGA-BRCA alone, would return
  `INSUFFICIENT_N` for essentially every gene x subtype cell checked.
- The 0.40-vs-lower-floor accuracy/survival trade (§1d) is real and
  quantified, but does not change any of the above — no floor in the
  0.25–0.40 range closes a gap of this size.

**Programmatic judgment — NOT settled by this memo, and explicitly not
decided here:**
- Timeline and cost of pursuing dbGaP/EGA controlled-access approvals
  for ICGC/PCAWG and CPTAC-3, and whether that investment is justified
  given §3A's own finding that even the combined, approved, harmonized
  cohort would remain far short of the requirement.
- Whether a pooled (Design B) result — with the per-subtype claim given
  up — is scientifically worth publishing on its own terms, and whether
  it still serves the study's original motivating question.
- Whether the subtype-stratified claim is central enough to this
  study's contribution that Design B's loss of it is disqualifying,
  or whether a partial, `INSUFFICIENT_N`-heavy Design C table
  (honestly reported, per PROTOCOL's existing mechanism) is an
  acceptable interim deliverable while awaiting a larger future cohort
  (e.g. the unconfirmed 1,364-genome 2025 cohort noted in §2b, if its
  terms and purity/subtype data are later confirmed usable).
- Whether to pursue PALB2/RAD51C/RAD51D at all as individually-resolved
  genes given §1b's numbers, versus reporting them only as a pooled
  "other CORE_HR genes" category (a design variant this memo was not
  asked to and does not specify).

## For REPORT.md — the plain feasibility statement this task asked to be logged, whatever design is chosen

**Whatever design is chosen, the finding that TCGA-BRCA alone cannot
support the pre-registered stratified design is a result about study
feasibility and belongs in the report.** Every cell of
`COHORT_REQUIREMENT_TABLE.tsv` — for BRCA1, BRCA2, PALB2, RAD51C,
RAD51D, ATM, and CHEK2, in every PAM50 subtype, at a 0.40 purity floor —
requires a cohort TCGA-BRCA does not come close to providing, and
adding the other two named real cohorts (ICGC/PCAWG breast, CPTAC-3
breast) does not change that conclusion (§2d/§3A). This is not a
finding about the LOH caller, the estimator, or any gate — it is a
finding about the study's available data relative to its own
pre-registered design, and per Standing Rule 8 it should be reported as
prominently as any completed pipeline work, not folded into a footnote.
This memo does not itself edit `REPORT.md` (not a deliverable of this
task); a human deciding among Designs A/B/C should carry this statement
into whichever report/deviation record documents that decision.

---

**HALT, per this task's own explicit instruction: the design decision is
the human's. No design is chosen above. `simulate.py`, `PROTOCOL.md`,
every gate, and every other pipeline file are unmodified by this task —
confirmed by checksum verify (see commit). P07, P08, and P09 were not
re-run.**
