SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_signature_validation.md — SBS3 estimation at exome scale

SIMULATED: every number below comes from SIMULATED data (injected exposures,
11088-sample simulator population from `simulate.py` v2)
run through the REAL SigProfilerAssignment 1.1.5 tool. No ACMG evidence
strength is assigned anywhere in this document.

## 1. Environment

- SigProfilerAssignment: **1.1.5** (expected 1.1.5 per
  `GATE1.json` — MATCHES).
  Run inside `vus-tumor-gate1:local`, digest `sha256:2f344e8a456167eec8701db9581b07b0a4139ed2acdaecf23ab811fec354ca4c` (matches `GATE1.json` — re-verified
  live this session; the docker daemon in this fresh container instance was initially unreachable
  and had to be re-confirmed running before this task could proceed).
- SigMA: re-attempted fresh this session (not assumed from a prior session) —
  **FAIL** (`SigMA_FAIL: there is no package called ‘SigMA’`). `BSgenome.Hsapiens.UCSC.hg19`:
  **FAIL** (`BSGENOME_FAIL: there is no package called ‘BSgenome.Hsapiens.UCSC.hg19’`). This
  MATCHES `GATE1.json`'s recorded
  SigMA `FAIL`. Per PROTOCOL.md §5.4: **no Stage of this task that would depend on a SigMA feature
  runs; the SigMA-derived feature (likelihood-based Signature-3 match score + `Signature_3_mva`) is
  reported as the literal string `BLOCKED`, not omitted or substituted with another tool's output.**
- Genome build used for every `cosmic_fit` call in this document: **GRCh38**
  (PROTOCOL.md's pinned reference build; the package's own bundled *default*
  is `GRCh37` — logged, not silently assumed to match).

## 2. COSMIC version pin

- **Current (package-bundled default)**: COSMIC v**3.6**, confirmed live this
  session via `inspect.signature(Analyzer.cosmic_fit).parameters['cosmic_version'].default`
  (3.6). A live WebSearch this session independently
  corroborated COSMIC Mutational Signatures v3.6 as the current signature-set release
  (cancer.sanger.ac.uk itself remains network-blocked — ENVIRONMENT.lock §0).
- **v2-equivalent (legacy nomenclature)**: COSMIC v**2**, also bundled
  in the same package build, at `/home/user/VUS_Tumor_exploratory/SIMULATED_signature_work/COSMIC_v2_SBS_GRCh38.txt` —
  uses `Signature_3`/`Signature_5` naming (pre-2018 Alexandrov et al. nomenclature) rather than
  `SBS3`/`SBS5`. Cosine similarity between v3.6's `SBS3` and v2's `Signature_3` (same 96-context
  space, both real weights extracted live from the installed package):
  **0.9648** — the shape was only modestly revised
  between the legacy and current signature sets.
- PROTOCOL.md §5.4 requires logging BOTH version strings, since they use different numbering: (a) the signature-matrix version bundled with this package build (3.6, confirmed live above) and (b) the general COSMIC database release cadence (v104 as of 2026-05-18, ENVIRONMENT.lock §3 -- not re-verified live this session, cancer.sanger.ac.uk remains network-blocked; a live WebSearch this session independently corroborated COSMIC Mutational Signatures v3.6 as the current signature-set release, matching (a).)
- Signature shape similarity is also the mechanism behind §5 below: `SBS3` vs `SBS5`
  (v3.6) = **0.7928**, `SBS3` vs `SBS40a` (v3.6) =
  **0.7634**, legacy `Signature_3` (v2) vs unsplit
  `SBS40` (v3) = **0.8988**.

## 3. Trinucleotide exome-to-genome normalization

Factors computed from the REAL installed reference-opportunity files (not COSMIC's copyrighted
signature weights — this is SigProfilerMatrixGenerator's trinucleotide-context census over the
GRCh38 reference, genome-wide vs. exome-only):
`/opt/conda/envs/bioenv/lib/python3.12/site-packages/SigProfilerMatrixGenerator/references/chromosomes/context_distributions/context_counts_GRCh38_96.csv` and its `_exome.csv` counterpart.
Factor = genome_freq / exome_freq per trinucleotide (32 contexts); full table:
`SIMULATED_signature_work/SIMULATED_trinuc_exome_genome_factors.tsv`.

SigProfilerAssignment operationalizes this exact normalization via its `exome` boolean: `exome=True`
swaps the COSMIC reference-signature matrix for a pre-renormalized `COSMIC_v{version}_SBS_GRCh38_exome.txt`
file (confirmed live in `decompose_subroutines.py:getProcessAvg`), rather than rescaling the observed
counts at runtime — i.e. the normalization direction is "renormalize the reference signatures to the
exome's trinucleotide opportunity distribution," not "rescale exome counts up to genome-equivalent."

## 4. No-normalization comparison (exome=True vs exome=False) — REAL, run twice on the same catalog

Same 382-sample catalog, same `cosmic_version=3.6`, only `exome`
toggled. MAE with normalization = **0.1478**, MAE without =
**0.1451**. Normalization gave a lower per-sample error for
**6/382** samples (12 worse,
364 tied). **Honest finding, not the expected direction:** in this simulated
exome-scale, low-mutation-count regime, `exome=True` renormalization does **not** meaningfully
improve SBS3 recovery accuracy over `exome=False` — the two MAEs differ by less than 0.003,
and the recovery error is dominated by the SBS3/SBS5 shape-similarity confound (§2) and by
sparse low-count noise (§6), not by the exome/genome trinucleotide-frequency mismatch this
normalization corrects. Per-sample detail: `SIMULATED_signature_work/SIMULATED_sbs3_exome_compare.tsv`.

## 5. SBS3 misassignment to SBS5/SBS40 across COSMIC versions — REAL, 7 versions run

| cosmic_version | HRD column | n | excluded (true_exp=0) | mean true | mean recovered | mean gap | mean bg frac of true signal | mean SBS40 frac of true signal |
|---|---|---|---|---|---|---|---|---|
| 2 | Signature_3 | 382 | 64 | 0.149267 | 0.096693 | 0.052574 | 0.043478 | 0.0 |
| 3 | SBS3 | 382 | 64 | 0.149267 | 0.042519 | 0.106748 | 0.902747 | 0.051903 |
| 3.1 | SBS3 | 382 | 64 | 0.149267 | 0.040878 | 0.108388 | 0.890824 | 0.048443 |
| 3.2 | SBS3 | 382 | 64 | 0.149267 | 0.041966 | 0.1073 | 0.881839 | 0.045139 |
| 3.3 | SBS3 | 382 | 64 | 0.149267 | 0.041966 | 0.1073 | 0.881839 | 0.045139 |
| 3.4 | SBS3 | 382 | 64 | 0.149267 | 0.024823 | 0.124444 | 0.892713 | 0.073463 |
| 3.6 | SBS3 | 382 | 64 | 0.149267 | 0.020457 | 0.12881 | 0.876444 | 0.056177 |

Detail per sample per version: `SIMULATED_signature_work/SIMULATED_sbs3_by_cosmic_version_detail.tsv`.
The recovery gap (mean true − mean recovered) is large and consistent across every tested COSMIC
version — this is a real, version-independent SBS3 identifiability problem in this exome-scale
regime, not an artifact of any one reference-signature revision.

## 6. Error vs. total mutation count — REAL, 382-sample stratified subset

| total_mutations bin | n | mean true exposure | mean recovered exposure | MAE | fraction exact-zero recovery |
|---|---|---|---|---|---|
| [5,15) | 7 | 0.0949 | 0.0000 | 0.0949 | 1.00 |
| [15,25) | 40 | 0.1739 | 0.0000 | 0.1739 | 1.00 |
| [25,35) | 40 | 0.1179 | 0.0142 | 0.1226 | 0.97 |
| [35,45) | 40 | 0.1672 | 0.0000 | 0.1672 | 1.00 |
| [45,55) | 40 | 0.1374 | 0.0118 | 0.1433 | 0.97 |
| [55,65) | 40 | 0.1615 | 0.0139 | 0.1548 | 0.97 |
| [65,75) | 40 | 0.1568 | 0.0273 | 0.1607 | 0.95 |
| [75,85) | 40 | 0.1111 | 0.0202 | 0.1067 | 0.95 |
| [85,95) | 40 | 0.1687 | 0.0365 | 0.1680 | 0.93 |
| [95,105) | 40 | 0.1592 | 0.0471 | 0.1559 | 0.90 |
| [105,116) | 15 | 0.1469 | 0.0652 | 0.1114 | 0.87 |

**The count below which SBS3 is unrecoverable, stated explicitly:** within the tested range
(total_mutations = 5 to 115 — the realistic per-exome TCGA-BRCA mutation burden per
`BENCHMARKS.tsv` TMB01), SBS3 relative exposure is recovered as **exactly zero** for essentially
all samples with total_mutations < 25 (fraction exact-zero = 1.00 in both bins below 25). This
fraction declines only slowly as total_mutations increases, and **remains 13/15
(87%) even in the top-tested bin ([105,116))** — this analysis's tested range
does not reach a count at which SBS3 becomes reliably recoverable. Stated as a floor rather than a
crisp threshold, because the decline is not monotonic bin-to-bin at n=40/bin (sampling noise —
see the MAE column, which is noisier and non-monotonic; the exact-zero fraction is the more
robust/monotonic statistic and is the basis for this statement). A supplementary single-seed check
at total_mutations up to 5000 (not part of the scored subset; `SIMULATED_signature_work/sanity_out/`)
found recovery remains exactly zero even at n=5000 when true exposure = 0.1 — i.e. **low fractional
exposure, not only low total count, drives non-recoverability**; this is disclosed as a caveat
beyond this task's literal "vs. total mutation count" ask, not folded into the headline curve above.

## 7. Bootstrap: zero vs. low-confidence — REAL, 44 samples x 100 replicates each

Per-sample nonparametric bootstrap (multinomial resample of that sample's own observed 96-context
counts at fixed total_mutations, refit via the same real `cosmic_fit` call). Classification:
`COMPUTED_ZERO` (point estimate 0, CI tight at 0 — confidently absent), `LOW_CONFIDENCE` (CI
contains 0 but is not tight there — a 0 point estimate here must NOT be read as confident absence),
`COMPUTED_NONZERO` (CI excludes 0), `NOT_COMPUTED` (schema-distinct from a true 0 — never coerced
to 0.0). Result: **26 COMPUTED_ZERO, 18 LOW_CONFIDENCE,
0 COMPUTED_NONZERO** (0 NOT_COMPUTED). Full table:
`SIMULATED_signature_work/SIMULATED_sbs3_bootstrap_recovery.tsv`.

## 8. gate6-scored recovery: the two pre-existing SIMULATED_TRUTH.tsv SBS3 quantities

`core_hr_sbs3_exposure_LR` / `ddr_signaling_sbs3_exposure_LR` — declared `NOT_IN_SCOPE` by
`loh_caller.py` ("requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not
compute"). Computed here via real `cosmic_fit` against simulate.py's EXISTING mutation catalogs
(`SIMULATED_data/SIMULATED_mutation_catalogs.tsv`, ARBITRARY 96-context shapes — distinct from the
real-COSMIC-shape catalog used in §4-7 above), then the same class-conditional-Gaussian-at-EVAL_POINT
construction `simulate.py` itself uses for the injected value (`EVAL_POINT["sbs3"]=0.30`), fit to
the REAL recovered per-sample exposures instead of the analytic model parameters, with a
2000-replicate bootstrap CI (resampling the already-recovered scalars, no
re-run of SPA needed for this cheap step).

| quantity | estimand | recovered LR | 95% CI | n Pathogenic | n Benign |
|---|---|---|---|---|---|
| core_hr_sbs3_exposure_LR | LR | 0.309121 | [0.061941, 0.833367] | 1848 | 1848 |
| ddr_signaling_sbs3_exposure_LR | LR | 0.476533 | [0.18614, 0.948359] | 1848 | 1848 |

**gate6_recovery.py: FAIL** (full output: `SIMULATED_signature_work/SIMULATED_gate6_output.txt`,
table: `SIMULATED_signature_work/gate6_out/SIMULATED_RECOVERY_TABLE.tsv`). All 14 other
`SIMULATED_TRUTH.tsv` quantities remain declared `NOT_IN_SCOPE` for this script (GIS/joint/
product-of-marginals/null-arm estimators this script does not compute — see
`SIMULATED_signature_work/SIMULATED_sbs3_gate6_scope.tsv` for the full per-quantity reasons).

## 9. gate7: every rate reported here with its denominator and excluded count

| metric | numerator | denominator | excluded | rate | excluded reason |
|---|---|---|---|---|---|
| exome_normalization_improves_recovery_rate | 6 | 382 | 364 | 0.015707 | normalized and non-normalized abs-error exactly tied (no distinguishable improvement direction) |
| sbs3_exact_zero_recovery_rate_overall_main_subset | 366 | 382 | 0 | 0.958115 |  |
| sbs3_exact_zero_recovery_rate_below_25_total_mutations | 47 | 47 | 0 | 1.0 |  |
| sbs3_exact_zero_recovery_rate_top_bin_105_116 | 13 | 15 | 0 | 0.866667 |  |
| bootstrap_low_confidence_rate | 18 | 44 | 0 | 0.409091 | sample had zero bootstrap replicates return a value (SPA output row missing) |
| sbs3_majority_misassigned_to_bg_or_sbs40_rate_v3.6 | 284 | 318 | 64 | 0.893082 | true injected sbs3_relative_exposure_true == 0 -- 'majority misassigned' is undefined with no true signal to misassign |

**gate7_denominators.py: PASS** (full output: `SIMULATED_signature_work/SIMULATED_gate7_output.txt`).

## 10. Subsampling disclosure

The full injected-exposure population (`SIMULATED_data/SIMULATED_signature_exposures.tsv`) has
11088 samples. Running the real `cosmic_fit` tool against all of them, at
every `cosmic_version` x `exome` combination this task needed, was not feasible within this
session's compute budget (~440-sample runs
already took tens of seconds to low minutes each; the full population would be roughly 29x larger
per run). A stratified subsample (40 per total_mutations bin, seed=20260908) of
**382 samples** was used for §4-6 above; two of eleven bins were undersized in the
raw population (bin [5,15): only 7 available; bin [105,116): only 15 available) and are reported
at their true, smaller n rather than padded. This is a disclosed, documented substitution of a
representative subset for the full population — not a silent one (Standing Rule 4) — and is
distinct from §8's gate6 recovery, which DID run against the full relevant population
(3696 samples per arm, split 1848 Pathogenic / 1848 Benign).

## 11. Overall

- gate6_recovery.py: **FAIL**
- gate7_denominators.py: **PASS**
- SigMA: **BLOCKED** (PROTOCOL.md §5.4 permitted status; re-confirmed FAIL fresh this session, matches `GATE1.json`)
- Headline validation result, stated per Standing Rule 2: SBS3 exposure recovery by real
  SigProfilerAssignment is **substantially compromised** throughout the realistic exome-scale
  mutation-count range tested here — this is reported as the actual finding, not softened.
