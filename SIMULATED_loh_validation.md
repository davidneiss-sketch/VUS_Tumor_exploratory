SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_loh_validation.md — direction-aware LOH caller validation

SIMULATED: this report validates `loh_caller.py` against `SIMULATED_TRUTH.tsv` and the SIMULATED tumor/normal data under `SIMULATED_data/`, produced by `simulate.py` (a prior task in this session). No real patient, tumor, or sequencing data appears anywhere below. No ACMG evidence strength is assigned to anything in this report.

**Overall session status: `SIMULATED_FAIL`** (gate6 exit=1, gate7 exit=0).

## 1. Method (per the task's exact specification)

`E[VAF|X] = (rho*X + (1-rho)*1) / (rho*CN_t + (1-rho)*2)` (PROTOCOL.md §5.2, reused verbatim from `simulate.py`'s own `expected_vaf()`). For every variant call with tumor depth >= 20 (PROTOCOL.md's own evaluable-depth floor), three canonical hypotheses about the mutant allele's tumor-cell copy count X are scored by **exact binomial log-likelihood** of the observed (alt reads, depth) — `WT_LOST_DIRECTION` (X = CN_t, WT allele fully lost), `VARIANT_LOST_DIRECTION` (X = 0, mutant allele fully lost), `RETENTION_DIRECTION` (X = round(CN_t/2), a preserved heterozygous variant). A uniform prior over the 3 turns the likelihoods into a posterior (softmax); the call is the argmax hypothesis and **the posterior mass on that hypothesis is the reported confidence** — a genuine per-locus confidence, not a fixed p-value cutoff. Below `CONFIDENCE_THRESHOLD = 0.80` (fixed before this script was ever run, not tuned to the accuracy numbers below), the call is `AMBIGUOUS` instead. Loci with depth < 20 never enter this competition at all and are called `NOT_EVALUABLE` (a 6th status this script adds to the task's 5-category list — see `loh_caller.py`'s NOTE_ON_NOT_EVALUABLE docstring for why silently dropping it would violate Standing Rule 4 / PROTOCOL.md §10).

A `WT_LOST_DIRECTION` win is further split by copy-number mechanism: `CN_NEUTRAL_LOH_WT_LOSS` if the locus's total copy number equals the sample's baseline ploidy state (copy-neutral LOH / acquired uniparental disomy — the WT copy lost, the mutant copy duplicated to compensate); bare `WT_LOSS` if total copy number differs from baseline (a genuine hemizygous deletion of the WT allele, net copy loss). `VARIANT_LOSS` is never split this way and remains its own, single, distinct output class (confirmed below, §5).

## 2. Confusion matrix (true direction-aware category x predicted category)

| true \ predicted | RETENTION | WT_LOSS | CN_NEUTRAL_LOH_WT_LOSS | VARIANT_LOSS | AMBIGUOUS | NOT_EVALUABLE |
|---|---|---|---|---|---|---|
| RETENTION | 14 | 0 | 0 | 3 | 5 | 0 |
| WT_LOSS | 0 | 0 | 0 | 0 | 0 | 0 |
| CN_NEUTRAL_LOH_WT_LOSS | 0 | 0 | 19 | 0 | 2 | 0 |
| VARIANT_LOSS | 0 | 0 | 0 | 9 | 1 | 0 |
| AMBIGUOUS | 4 | 0 | 0 | 0 | 1 | 0 |
| NOT_EVALUABLE | 0 | 0 | 0 | 0 | 0 | 2 |

SIMULATED: 60 total variant calls attempted. PROTOCOL.md's own truth vocabulary (`assigned_loh_category`) maps onto this caller's direction-aware vocabulary via `TRUTH_CATEGORY_MAP` in `loh_caller.py`; `LOH_SECOND_HIT` maps to `CN_NEUTRAL_LOH_WT_LOSS` specifically (never bare `WT_LOSS`) because `simulate.py`'s own category generator sets `major_cn == cn_total` for every LOH category it injects — confirmed on this run's actual data: 21 `LOH_SECOND_HIT` truth loci, of which 0 have a copy-number-altered (non-copy-neutral) total CN.

**Coverage gap, investigated and disclosed rather than silently absent:** bare `WT_LOSS` (a genuine hemizygous-deletion-type WT loss) has **zero** true instances and **zero** predicted instances in this validation set. This is not a caller bug — it is because `simulate.py` (see `PARAMETER_PROVENANCE.tsv` / `cn_and_depth_for_category()`) only ever injects copy-neutral LOH mechanisms; it never models an actual hemizygous deletion (`major_cn < baseline_cn`). **This caller's accuracy for true deletion-type WT_LOSS is therefore UNCHECKED by this validation, not merely untested-and-presumed-fine** — a real gap for a future simulator enhancement (out of scope for this task, Standing Rule 9).

## 3. Denominator-explicit accuracy (Standing Rule 5, gate7-checked)

| metric | numerator | denominator | excluded_count | rate |
|---|---|---|---|---|
| overall_accuracy_including_ambiguous_and_not_evaluable | 45 | 60 | 0 | 0.75 |
| overall_accuracy_excluding_ambiguous_and_not_evaluable | 42 | 49 | 11 | 0.857143 |
| confidence_filter_ambiguous_rate | 9 | 58 | 0 | 0.155172 |
| not_evaluable_rate_depth_lt_20 | 2 | 60 | 0 | 0.033333 |
| accuracy_by_purity_LOW_0.10_0.35 | 7 | 8 | 10 | 0.875 |
| accuracy_by_purity_MID_0.35_0.65 | 16 | 20 | 1 | 0.8 |
| accuracy_by_purity_HIGH_0.65_0.95 | 19 | 21 | 0 | 0.904762 |
| accuracy_by_depth_BORDERLINE_20_30 | 0 | 4 | 1 | 0.0 |
| accuracy_by_depth_MODERATE_30_60 | 2 | 2 | 0 | 1.0 |
| accuracy_by_depth_HIGH_60_plus | 40 | 43 | 8 | 0.930233 |
| accuracy_by_total_copy_number_CN2 | 29 | 33 | 8 | 0.878788 |
| accuracy_by_total_copy_number_CN4 | 13 | 16 | 3 | 0.8125 |
| accuracy_by_wgd_status_NON_WGD | 29 | 33 | 8 | 0.878788 |
| accuracy_by_wgd_status_WGD | 13 | 16 | 3 | 0.8125 |

SIMULATED: of 60 total calls attempted, `2` were `NOT_EVALUABLE` (depth < 20, excluded pre-emptively before any hypothesis competition) and, of the `58` depth-evaluable loci remaining, `9` were reclassified `AMBIGUOUS` by the confidence < 0.80 filter (confidence-filter exclusion rate = 0.155172). Accuracy **including** those excluded calls (scored against their own true category) = 0.75 (45/60). Accuracy **excluding** them (the only fair comparison of the caller's *definitive* calls) = 0.857143 (42/49, 11 excluded).

## 4. The unreliable operating region (investigated, not asserted)

The worst-performing definitive-call stratum in the breakdown above is **`accuracy_by_depth_BORDERLINE_20_30`** at rate **0.0** (0/4, 1 excluded as AMBIGUOUS/NOT_EVALUABLE within that stratum). All 5 true-`AMBIGUOUS` loci in this dataset fall in exactly this depth band (`simulate.py`'s `cn_and_depth_for_category()` deliberately draws `LOH_AMBIGUOUS` depth from `[20,25]`); 4 of the 5 are confidently (posterior >= 0.85) called `RETENTION` instead.

**Root cause investigated and proved analytically, not just observed:** `expected_vaf(rho, CN_t, X)` is an **affine (linear) function of X**. `simulate.py`'s `LOH_AMBIGUOUS` category sets its injected VAF target to the arithmetic midpoint of the two loss-direction extremes, `(expected_vaf(rho,CN_t,CN_t) + expected_vaf(rho,CN_t,0)) / 2`. Because `expected_vaf` is affine in X, that midpoint is *exactly* `expected_vaf(rho,CN_t,CN_t/2)` — algebraically identical to this caller's `RETENTION_DIRECTION` hypothesis, for **every** purity and every `CN_t` (verified numerically across rho in {0.1,...,0.95} and CN_t in {2,4}: both equal 0.5 exactly in every case checked). This is a mathematical identity of the linear VAF model, not an approximation or a coincidence of these particular parameter draws. **Consequence:** a true `LOH_AMBIGUOUS` locus and a true `RETENTION` locus have, in expectation, the identical read-count distribution — no likelihood-based method operating on VAF/depth alone (this caller included) can distinguish them; the only apparent separation comes from finite-depth binomial sampling noise around that one shared central value, and at the deliberately low depth (20-25x) this category uses, that noise is more likely to look like a confident RETENTION call than to land close enough to either extreme to register as ambiguous. This is a structural identifiability limit of the VAF-only binomial model itself (matching PROTOCOL.md §5.1's own definition of `LOH_AMBIGUOUS` as "the model cannot distinguish which allele was retained" — here it additionally cannot distinguish AMBIGUOUS from RETENTION), not a bug in this caller's implementation.

**Secondary, smaller effect, also investigated:** `accuracy_by_wgd_status_WGD` (0.8125) is below `accuracy_by_wgd_status_NON_WGD` (0.878788). Root cause: `simulate.py`'s `cn_and_depth_for_category()` hard-codes `mutant_copies = 1` for the `RETAINED`/`NOT_EVALUABLE` categories *regardless of ploidy*, rather than scaling to `cn_total // 2` for a WGD-doubled (`cn_total = 4`) sample the way a genuinely preserved heterozygous variant requires. This caller's `RETENTION_DIRECTION` hypothesis uses the ploidy-scaled `X = round(CN_t/2)` (2, not 1, when `CN_t = 4`) — the generalization PROTOCOL.md's own `E[VAF|X]` formula implies for whole-genome doubling. The simulator's actual generated VAF for WGD `RETAINED` samples is therefore more diluted than this caller's hypothesis expects, a disclosed **simulator-model/caller-model mismatch on WGD-doubled preserved-heterozygous loci**, not a caller implementation bug — the caller's assumption is the biologically general one; the simulator's is a simplification that does not scale `mutant_copies` with ploidy. Not fixed here by reverse-engineering the caller to match the simulator's simplification (that would overfit this caller to one synthetic generator's quirk rather than validating it as a general tool).

## 5. VARIANT_LOSS is a distinct output class

SIMULATED: `VARIANT_LOSS` appears as its own row and column in the confusion matrix above, distinct from `WT_LOSS`/`CN_NEUTRAL_LOH_WT_LOSS` — 10 true instances, 12 predicted instances this run. `loh_caller.py`'s `call_locus()` never merges the two loss directions into one bucket: they come from two separate hypotheses (`WT_LOST_DIRECTION` vs `VARIANT_LOST_DIRECTION`) with independently computed likelihoods.

## 6. gate6 — recovery against SIMULATED_TRUTH.tsv, scope declared for every quantity

gate6_recovery.py exit code: **1** (at least one in-scope quantity SIMULATED_FAIL — reported as FAILED, per the task). Every one of the 6 `SIMULATED_TRUTH.tsv` quantities is declared in `SIMULATED_recovery_scope.tsv` (gate6 housekeeping fix: a gate that scores a subset without declaring the subset is a scope bug) and appears below, whether in scope, out of scope, or undeclared (0 undeclared this run).

In-scope quantities (2 of 6 — this caller's own deliverable, scored for real):

| quantity | injected | recovered | ci_low | ci_high | status | reason |
|---|---|---|---|---|---|---|
| core_hr_loh_second_hit_LR | 6.999999999999999 | 4.6 | 1.9090909090909092 | 25.0 | SIMULATED_FAIL | relative bias 0.3429 exceeds tolerance 0.25 |
| ddr_signaling_loh_second_hit_LR | 2.666666666666667 | 3.6666666666666665 | 1.0 | 17.0 | SIMULATED_FAIL | relative bias 0.3750 exceeds tolerance 0.25 |

Declared out-of-scope quantities (4 of 6 — GIS/HRD-score and SBS3-exposure features require scarHRD/SigProfilerAssignment outputs this LOH caller does not compute). gate6 reports these as `BLOCKED`, Standing Rule 1's permitted vocabulary for 'could not be computed, disclosed with the same prominence as a completed result' — **not** as a fabricated `SIMULATED_FAIL`, and not omitted from the table:

| quantity | status | scope_status | reason |
|---|---|---|---|
| core_hr_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| ddr_signaling_gis_score_LR | BLOCKED | NOT_IN_SCOPE | requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute |
| core_hr_sbs3_exposure_LR | BLOCKED | NOT_IN_SCOPE | requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute |
| null_sequencing_depth_bucket_LR | BLOCKED | NOT_IN_SCOPE | an engineered-null depth-bucket feature unrelated to LOH direction; not this caller's estimand |

**Per the task's exact acceptance wording ("gate6 PASS on every recovery quantity, or the session reports FAILED"): this session reports gate6 as FAILED.** The 2 in-scope LOH-direction quantities are the only ones this gate run scores as PASS/FAIL; both real results are shown in the table above (a real, uncontrived test result, not tuned to pass). The 4 declared-out-of-scope quantities are `BLOCKED`, not scored, and do not by themselves cause gate6's exit code to be nonzero — only a real SIMULATED_FAIL among the in-scope quantities, or any UNDECLARED quantity, does that.

## 7. gate7 — denominators

gate7_denominators.py exit code: **0** (PASS).

```
=== gate7_denominators ===
[PASS] rates table present — SIMULATED_rates_table.tsv, 14 metric row(s)
[PASS] every row has a positive denominator — all 14 row(s) have a positive denominator
[PASS] every row has an explicit (non-blank) excluded_count — all 14 row(s) carry an explicit excluded_count
[PASS] numerator never exceeds denominator — all 14 row(s) OK
[PASS] reported rate (if present) matches numerator/denominator — all reported rates internally consistent

gate7_denominators OVERALL: PASS
```

## 8. Files

| File | Contents |
|---|---|
| `SIMULATED_loh_validation/SIMULATED_loh_calls.tsv` | one row per variant call: predicted category, confidence, posteriors, true category, correctness |
| `SIMULATED_loh_validation/SIMULATED_confusion_matrix.tsv` | true x predicted category counts (long format) |
| `SIMULATED_loh_validation/SIMULATED_rates_table.tsv` | every reported rate with numerator/denominator/excluded_count (gate7 input) |
| `SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv` | the 2 recovered LR quantities with bootstrap CIs (gate6 `--recovered` input) |
| `SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv` | scope declaration for all 6 SIMULATED_TRUTH.tsv quantities (gate6 `--scope` input) |
| `SIMULATED_RECOVERY_TABLE.tsv` / `.md` | gate6's own emitted output (repo root), covering all 6 SIMULATED_TRUTH.tsv quantities |

