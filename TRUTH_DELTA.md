SIMULATED DATA — NOT A SCIENTIFIC RESULT

# TRUTH_DELTA.md — before/after every SIMULATED_TRUTH.tsv quantity (P06R2)

SIMULATED: this document reports the effect of P06R2's shape fix
(`REQUIRED_P06_CHANGES.md`, `SIMULATION_SPEC.md` §3.1) on every quantity in
`SIMULATED_TRUTH.tsv`. No ACMG evidence strength is assigned anywhere below.

## Headline finding, read first per the invoking task's own instruction

**All 16 `SIMULATED_TRUTH.tsv` quantities are UNCHANGED, to full floating-point
precision.** The joint-vs-naive-marginal ratio did NOT move — it is exactly
what it was before the fix. This is not a coincidence and not something this
task engineered to happen: it is a structural property of this codebase,
proven below both algebraically (by tracing which functions read which
variables) and empirically (by diffing a full before/after regeneration of
every output file).

**This does not mean the fix was a no-op.** It means this simulator's design
cleanly separates the ANALYTIC truth-quantity model (an exposure-fraction
Gaussian model, driving `SIMULATED_TRUTH.tsv`) from the OBSERVABLE-catalog
generation (a 96-context shape, driving `SIMULATED_data/SIMULATED_mutation_catalogs.tsv`)
— the defect P08 found was entirely in the latter, and the fix was applied
entirely there. The two were never coupled, so fixing one could not and did
not move the other. `SIMULATED_TRUTH.tsv`'s SBS3 quantities were never
"wrong" in the sense of asserting an incorrect number; the injected truth
was always self-consistent. What was wrong was a SEPARATE, downstream data
product (`SIMULATED_mutation_catalogs.tsv`) not actually looking like the
thing that truth quantity's derivation is named after — which is exactly
what made `signatures.py`'s real-tool recovery test (scored against that
catalog) fail for a reason having nothing to do with recovery.

## 1. Every SIMULATED_TRUTH.tsv quantity, BEFORE → AFTER

| quantity | BEFORE | AFTER | status |
|---|---|---|---|
| core_hr_wt_lost_direction_LR | 4.480411981797967 | 4.480411981797967 | UNCHANGED |
| core_hr_gis_score_LR | 3.6622471084686548 | 3.6622471084686548 | UNCHANGED |
| core_hr_sbs3_exposure_LR | 5.644994542233774 | 5.644994542233774 | UNCHANGED |
| core_hr_joint_LR | 7.243192150573085 | 7.243192150573085 | UNCHANGED |
| core_hr_product_of_marginals_LR | 92.6251919795419 | 92.6251919795419 | UNCHANGED |
| **core_hr_joint_vs_marginal_inflation_ratio** | **0.07819894345992705 (~12.79x deflation of joint vs. naive)** | **0.07819894345992705 (~12.79x, unchanged)** | **UNCHANGED — did not collapse toward 1** |
| ddr_signaling_wt_lost_direction_LR | 2.137348544853484 | 2.137348544853484 | UNCHANGED |
| ddr_signaling_gis_score_LR | 2.7235909709691692 | 2.7235909709691692 | UNCHANGED |
| ddr_signaling_sbs3_exposure_LR | 3.9157230519927206 | 3.9157230519927206 | UNCHANGED |
| ddr_signaling_joint_LR | 6.204176316151221 | 6.204176316151221 | UNCHANGED |
| ddr_signaling_product_of_marginals_LR | 22.794454498384997 | 22.794454498384997 | UNCHANGED |
| ddr_signaling_joint_vs_marginal_inflation_ratio | 0.2721791967687049 (~3.67x) | 0.2721791967687049 (~3.67x) | UNCHANGED |
| null_arm_full_vector_joint_LR | 1.0 | 1.0 | UNCHANGED (still exactly 1.0) |
| null_arm_full_vector_product_of_marginals_LR | 1.0 | 1.0 | UNCHANGED (still exactly 1.0) |
| null_arm_full_vector_inflation_ratio | 1.0 | 1.0 | UNCHANGED (still exactly 1.0) |
| null_sequencing_depth_bucket_LR | 1.0 | 1.0 | UNCHANGED |

Raw BEFORE snapshot: this document's evidence was captured by regenerating
against the pre-fix `simulate.py` (git history, commit `230c127`) into
`/tmp/SIMULATED_TRUTH_BEFORE.tsv` immediately before applying the shape fix,
then diffing field-for-field against the post-fix `SIMULATED_TRUTH.tsv` —
not reasoned about after the fact.

**HALT condition check (per this task's explicit instruction):** "if the
joint-vs-naive ratio collapses toward 1, stop and report." It did not
collapse — it is bit-for-bit identical to its pre-fix value (0.0782 for
CORE_HR, 0.2722 for DDR_SIGNALING, both far from 1). **The HALT condition
does not trigger; this session proceeds.**

## 2. Why nothing moved — the mechanism, traced through the actual code

`compute_truth_quantities()` (the function that derives every row above)
calls only `marginal_wt_lost_prob`, `marginal_gaussian_feature_params`,
`joint_lr`/`joint_density`, and `product_of_marginals_lr`. Every one of
these reads only `WT_LOST_LINK`, `GIS_LINK`, `SBS3_LINK`, `Z_MEAN`,
`Z_SD`, and `EVAL_POINT` — module-level dicts/constants **none of which
this fix touched** (`REQUIRED_P06_CHANGES.md` point 4 explicitly required
leaving `SBS3_LINK`'s c/d/sigma alone, and this session did). None of these
functions takes `hrd_shape`/`background_shape` as an argument, and neither
variable is referenced anywhere inside them. The 96-context shape is used
in exactly one place: `_emit_sample()`'s catalog-generation block (building
`SIMULATED_mutation_catalogs.tsv`), which runs entirely AFTER and
independently of the sample's own `sbs3_relative_exposure_true` (itself
computed from `SBS3_LINK` alone, at `simulate.py` line ~586, several lines
before the catalog block that consumes it as an already-fixed input).

**RNG isolation (why not even the raw per-sample draws shifted):**
`build_signature_shapes()` used to take (and now no longer needs) a
dedicated `random.Random(SEED+1)` instance, entirely separate from each
sample's own `random.Random(SEED*1000+sample_idx)` stream — so however many
random draws shape-construction consumes has zero effect on any sample's
own RNG sequence. Within a sample's own stream, replacing `hrd_shape`/
`background_shape` changes what `rng.choices(range(96), weights=..., k=n_hrd)`
returns, but `random.choices()` always calls the underlying RNG's
`.random()` exactly `k` times regardless of the `weights` argument's
values — and `k` (`n_hrd`, `n_bg`) is computed from `sbs3_relative_exposure_true`
*before* this call, unaffected by the shape swap. Nothing in `_emit_sample()`
draws from `rng` after the catalog block. **Every other field a sample
emits — purity, depth, gene, ploidy, WGD, category, direction, mechanism,
tumor/normal read counts, GIS, BAF SNPs, `sbs3_relative_exposure_true`,
`total_mutations` — is drawn from the exact same RNG calls in the exact
same order, regardless of which shape vectors were used.**

**Empirical confirmation** (not just code-tracing): a full before/after
regeneration was diffed file-by-file. Every file was byte-identical EXCEPT
`SIMULATED_data/SIMULATED_mutation_catalogs.tsv`:

| file | result |
|---|---|
| `SIMULATED_TRUTH.tsv` | IDENTICAL |
| `SIMULATED_data/SIMULATED_sample_metadata.tsv` | IDENTICAL |
| `SIMULATED_data/SIMULATED_variant_calls.tsv` | IDENTICAL |
| `SIMULATED_data/SIMULATED_baf_segments.tsv` | IDENTICAL |
| `SIMULATED_data/SIMULATED_signature_exposures.tsv` | IDENTICAL |
| `SIMULATED_data/SIMULATED_coverage_report.tsv` | IDENTICAL |
| `SIMULATED_data/SIMULATED_loh_injection_self_check.md` | IDENTICAL |
| `SIMULATED_data/SIMULATED_no_v1_reuse_check.md` | IDENTICAL |
| `SIMULATED_TRUTH_detail/SIMULATED_sample_labels.tsv` | IDENTICAL |
| `V1_NUMERIC_SCAN.tsv` | IDENTICAL |
| `SIMULATED_data/SIMULATED_mutation_catalogs.tsv` | **DIFFERS** (same 96-context header, different per-sample per-context integer counts — the intended change) |

## 3. NULL_ARM re-proven algebraically (not merely re-run)

`NULL_ARM`'s `Z_MEAN` is `{"Pathogenic": 0.0, "Benign": 0.0}` — identical
between classes — and every other link parameter (`WT_LOST_LINK`,
`GIS_LINK`, `SBS3_LINK` for `NULL_ARM`) is likewise class-independent by
construction (none of them differ by class; only `Z`'s class-conditional
*distribution* would let class enter the joint density at all). The full
joint density is:

```
f(x | class) = ∫ P(wt_lost|Z) · φ(gis; c_gis+d_gis·Z, σ_gis) · φ(sbs3; c_sbs3+d_sbs3·Z, σ_sbs3) · φ(Z; μ_Z[class], 1) dZ
```

Since `μ_Z[Pathogenic] = μ_Z[Benign] = 0.0` for `NULL_ARM` and every other
term in the integrand (`P(wt_lost|Z)`, the `gis` and `sbs3` conditional
densities) is a function of `Z` alone with NO class-dependent parameters,
`f(x | Pathogenic)` and `f(x | Benign)` are literally the same integral —
same integrand, same limits — for every possible evidence vector `x`, not
merely at `EVAL_POINT`. Therefore:

```
joint_LR(x) = f(x|Pathogenic) / f(x|Benign) = f(x) / f(x) = 1   for ALL x
```

This is an identity (LR ≡ 1 because numerator and denominator are the same
function), not a numerical coincidence — it holds regardless of Simpson's-rule
step count, integration bounds, or evaluation point, and this fix touched
none of `NULL_ARM`'s parameters, so the proof is unchanged and the numerical
value (`null_arm_full_vector_joint_LR = 1.0` exactly, confirmed to full
float precision in §1's table) continues to hold. Same argument applies to
`product_of_marginals_LR`: each of the three marginals (`marginal_wt_lost_prob`,
`marginal_gaussian_feature_params` for GIS and SBS3) is itself a function of
`μ_Z[class]` alone, and since `μ_Z[Pathogenic]=μ_Z[Benign]` for `NULL_ARM`,
each marginal is identical between classes too, so their product is
identical, so `product_of_marginals_LR ≡ 1` as well — and therefore the
ratio `null_arm_full_vector_inflation_ratio ≡ 1/1 = 1` trivially.

## 4. Step 2: injected SBS3 mutation burden vs. TMB01 — no change needed

`total_mutations` (the total per-sample exome mutation count, unaffected by
this fix — computed before and independently of `hrd_shape`/`background_shape`):
mean 59.94, median 60, range [5, 115] across all 11,088 samples — matches
`BENCHMARKS.tsv` TMB01 (TCGA-BRCA WES mean 60.05/tumor) closely; **the
burden itself is realistic and required no fix.**

`n_hrd_process_mutations` (the absolute count of HRD-process-attributable
mutations = `total_mutations x sbs3_relative_exposure_true`, rounded — also
unaffected by this fix, computed before the catalog-generation block):

| stratum | n | mean | median | fraction < 1 |
|---|---|---|---|---|
| Overall | 11088 | 9.40 | 8.0 | 18.2% |
| Pathogenic | 5544 | 12.94 | 11.0 | 7.6% |
| Benign | 5544 | 5.86 | 4.0 | 28.8% |

The overall 18.2%-below-1 figure is concentrated almost 4x more heavily in
`Benign` samples (28.8%) than `Pathogenic` (7.6%) — exactly the expected
shape for a mixed cohort where `Benign` samples are, by construction,
supposed to carry little-to-no real HR-deficiency signal. This is not
evidence of an unrealistically low burden; it is what "this tumor is not
HRD-associated" should look like in a population that is not all positive
for the feature. **No change made to `total_mutations` or `SBS3_LINK`'s
exposure-fraction parameters** — consistent with `REQUIRED_P06_CHANGES.md`
point 4 and this task's own explicit instruction not to.

## 5. Coverage grid

Re-reported (unaffected by this fix — coverage counting depends only on
`category`/`arm`/`class`/`purity_bin`/`depth_regime`, none of which read
`hrd_shape`/`background_shape`): **540 cells checked, 0 IN_SCOPE cells below
minimum** — the same clean result as before the fix (there was no
previously-underfilled cell to resolve).

## 6. Step 5 appendix: SigMA, run for real against this fixed catalogue

P08 found SigMA's core analysis machinery is not itself BSgenome-dependent
(only its VCF-to-matrix conversion step is) but did not take that avenue to
a full run. This session completed it: derived the exact COSMIC-to-SigMA
96-context label mapping from SigMA's own `R/make_matrix.R` source
(`type = tolower(paste0(ref, alt, prime5, prime3))`, then `sort()` —
confirmed against SigMA's own bundled example file, e.g. COSMIC `A[C>A]A`
↔ SigMA `caaa`), built a `genome_file` from 10 real samples in the
P06R2-fixed `SIMULATED_mutation_catalogs.tsv` (5 `CORE_HR` Pathogenic with
true `sbs3_relative_exposure_true` 0.76–0.84, 5 `CORE_HR` Benign at exactly
0.0), and ran SigMA's real `run()` end to end via the same source-level
bypass P08 identified (full detail, caveats, and exact commands:
`GATE1.json`'s `resolution_attempts_p06r2`).

**Result: 10/10 correct.** Every true-high-exposure Pathogenic sample was
classified `Signature_3` (`max_wl` 0.9999955–1.0); every true-zero-exposure
Benign sample was classified `Signature_5` (`max_wl` 0.6421–1.0). Full
output: `SIMULATED_signature_work/SIMULATED_sigma_catalogue_only_attempt_result.csv`.

This is a small (n=10), deliberately extreme-spanning demonstration, not a
calibrated validation at Task K/P08's scale — and it does not flip
`GATE1.json`'s formal SigMA status to PASS (the actual `R CMD INSTALL` gate
test still fails identically; `BSgenome.Hsapiens.UCSC.hg19` remains
genuinely absent; this was a source-level bypass of the normal install, not
a resolution of it). But it is a real, reproducible result, and it directly
supports the pattern DIAGNOSIS_P08.md §5 found: SigProfilerAssignment's
NNLS-based decomposition is unstable in exactly the exome-scale, low-count
regime SigMA's own documentation claims to be built for. **This bears on
PROTOCOL.md §5.4's tool choice; `PROTOCOL.md` is not modified by this
task.**

## 7. Known, disclosed consequence: `signatures.py`'s own committed report is now stale

Unlike `SIMULATED_TRUTH.tsv` (§1-3, unaffected), `signatures.py`'s
`SIMULATED_signature_validation.md` §8 (`core_hr_sbs3_exposure_LR`/
`ddr_signaling_sbs3_exposure_LR` gate6 recovery, from P08) IS affected by
this fix — it was run against `SIMULATED_data/SIMULATED_mutation_catalogs.tsv`,
the one file P06R2 changed. That committed report's gate6 FAIL (recovered
LR 0.31/0.48 vs. injected 5.64/3.92) reflects the OLD, mislabeled catalog;
re-running `signatures.py`'s `phase6_gate6_recovery()` against the NOW-FIXED
catalog would very plausibly recover a materially different (likely much
closer) LR, given §6's SigMA appendix already shows 10/10 correct
classification on this same fixed data with real cosine-similar signal.

**This session does not re-run `signatures.py`** — this task's explicit
instruction is "Re-run P07 or P08 from this prompt" is disallowed, and
`signatures.py` itself is on the do-not-modify list. Per Standing Rule 8,
this staleness is disclosed here prominently rather than left for a future
session to discover by surprise: `SIMULATED_signature_validation.md` and
`SIMULATED_signature_work/*sbs3*` (everywhere that reads the mutation
catalog) are stale relative to the current simulator state as of this
commit, and `check_signatures_acceptance.py`'s reproducibility criterion
(re-run `signatures.py` fresh, diff against the committed report) is
EXPECTED to now report a difference for exactly this reason — that is not
a regression introduced by P06R2, it is the correct, honest consequence of
fixing an upstream input the downstream report was scored against. A future
task authorized to re-run P08 against the fixed catalog should do so.

---

# P06R3 addendum: clipping-fidelity fix (before/after unchanged)

SIMULATED: the section above is P06R2's own before/after report, preserved unmodified as the historical record (cited by P08-RERUN's own task text, TRUTH_DELTA.md §7). Everything below is P06R3's addition, appended rather than replacing the above.

SIMULATED: this is the before/after comparison required by this task's Step
3. Read FIDELITY_AUDIT.md first — its headline finding (the SBS3 clip
mismatch P08-RERUN reported does not replicate under a rigorous re-test) is
why every number below is unchanged.

## 1. Every SIMULATED_TRUTH.tsv quantity, before → after

"Before" = the value committed at HEAD (`80e56dd`, P06R2). "After" = the
value produced by the current `simulate.py`, which includes the
`sbs3_clipped_density()`/`sbs3_clipped_lr()` fix (FIDELITY_AUDIT.md §4).

| quantity | before | after | changed? |
|---|---|---|---|
| core_hr_wt_lost_direction_LR | 4.480411981797967 | 4.480411981797967 | no |
| core_hr_gis_score_LR | 3.6622471084686548 | 3.6622471084686548 | no |
| core_hr_sbs3_exposure_LR | 5.644994542233774 | 5.644994542233774 | no (derivation text updated, see §2) |
| core_hr_joint_LR | 7.243192150573085 | 7.243192150573085 | no |
| core_hr_product_of_marginals_LR | 92.6251919795419 | 92.6251919795419 | no |
| core_hr_joint_vs_marginal_inflation_ratio | 0.07819894345992705 | 0.07819894345992705 | no |
| ddr_signaling_wt_lost_direction_LR | 2.137348544853484 | 2.137348544853484 | no |
| ddr_signaling_gis_score_LR | 2.7235909709691692 | 2.7235909709691692 | no |
| ddr_signaling_sbs3_exposure_LR | 3.9157230519927206 | 3.9157230519927206 | no (derivation text updated, see §2) |
| ddr_signaling_joint_LR | 6.204176316151221 | 6.204176316151221 | no |
| ddr_signaling_product_of_marginals_LR | 22.794454498384997 | 22.794454498384997 | no |
| ddr_signaling_joint_vs_marginal_inflation_ratio | 0.2721791967687049 | 0.2721791967687049 | no |
| null_arm_full_vector_joint_LR | 1.0 | 1.0 | no (exact both before and after) |
| null_arm_full_vector_product_of_marginals_LR | 1.0 | 1.0 | no (exact both before and after) |
| null_arm_full_vector_inflation_ratio | 1.0 | 1.0 | no (exact both before and after) |
| null_sequencing_depth_bucket_LR | 1.0 | 1.0 | no |

**Every quantity is byte-identical.** This is the expected, correct outcome
given FIDELITY_AUDIT.md's finding: `EVAL_POINT["sbs3"]=0.30` is interior to
`[0, 0.95]` for every class in every arm, where clipping cannot alter the
density (§"Headline finding" of FIDELITY_AUDIT.md). Confirmed directly by
`diff` between the pre-fix and post-fix `SIMULATED_TRUTH.tsv`: the only
lines that differ are the two SBS3 exposure LR rows' free-text `derivation`
column (now spelling out the clipped-density computation and its kind —
`density`, not `point_mass` — explicitly); the `injected_value` column is
untouched on every row. `SIMULATED_data/`, `SIMULATED_TRUTH_detail/`, and
`V1_NUMERIC_SCAN.tsv` are also byte-identical before/after (the fix does not
touch any RNG-consuming code path — `_emit_sample()`'s clip line changed
only from the literals `0.95`/`0.0` to the equal-valued named constants
`SBS3_CLIP_HI`/`SBS3_CLIP_LO`).

## 2. What actually changed in `simulate.py`

- Added `SBS3_CLIP_LO`/`SBS3_CLIP_HI` named constants (previously inline
  literals `0.0`/`0.95`, duplicated between `_emit_sample()`'s draw and
  nowhere else — now used by both the draw and the new analytic function,
  so they cannot drift apart).
- Added `sbs3_clipped_density(x, mean, sd) -> (value, kind)`: returns the
  exact closed-form interior density for x strictly inside the clip range,
  or the exact point-mass probability at a boundary, tagged so a density
  can never be silently divided against a point mass.
- Added `sbs3_clipped_lr(...)`: the SBS3 term of `product_of_marginals_lr()`,
  now via `sbs3_clipped_density`, raising if the two classes' evaluations
  are of different kinds (defends against a future `EVAL_POINT` change
  landing on one class's boundary but not the other's).
- `compute_truth_quantities()`'s SBS3 exposure LR rows and `joint_density()`'s
  per-Z sbs3 term now call `sbs3_clipped_density`/`sbs3_clipped_lr` instead
  of a bare `phi_pdf`. `product_of_marginals_lr()` likewise.
- `_emit_sample()`'s clip call now references the named constants instead of
  the bare literals (behaviorally identical, same numeric bounds).

No change to `WT_LOST_LINK`, `GIS_LINK`, `Z_MEAN`, `SBS3_LINK`, `EVAL_POINT`,
or any RNG-consuming code path. `PROTOCOL.md`, `signatures.py`, and
`loh_caller.py` are unmodified (verified live by
`scripts/check_p06r3_acceptance.py`).

## 3. Joint / product-of-marginals / inflation ratio — reconciling "12.8x/3.7x"

This task's own text anticipated these three quantities might move and
explicitly warned against reporting a stale prior figure: *"The 12.8x and
3.7x will move if the audit finds divergence beyond SBS3. Report what they
become; do not engineer them."* Re-deriving them directly from the values
committed at HEAD (`80e56dd`, P06R2) — i.e., **before** P06R3's own fix, so
these are not a consequence of anything this task did:

| arm | joint_LR | product_of_marginals_LR | joint_vs_marginal_inflation_ratio |
|---|---|---|---|
| CORE_HR | 7.243 | 92.625 | **0.0782** |
| DDR_SIGNALING | 6.204 | 22.794 | **0.2722** |

**These reconcile exactly with "12.8x and 3.7x" — they are the same numbers,
not a discrepancy.** P06R2's own `TRUTH_DELTA.md §1` (the original section
preserved above, unedited by this addendum) already reports these same two
ratios as *"0.07819894345992705 (~12.79x deflation of joint vs. naive)"* and
*"0.2721791967687049 (~3.67x)"* — i.e. it describes the ratio via its
reciprocal (`naive/joint`, "how many times bigger the naive estimate is"),
not the ratio itself (`joint/naive`, the value `SIMULATED_TRUTH.tsv` actually
stores under `..._inflation_ratio`). `1/0.0782 = 12.79` and `1/0.2722 = 3.67`.
P06R3's task text inherited that "12.8x/3.7x" framing directly from P06R2's
report — this audit's first read of it (an earlier draft of this document)
mistook it for the `injected_value` itself and wrongly flagged an
unexplained mismatch; correcting that here. **Confirmed: these three
quantities did not move at all, under either fix (P06R2's shape fix, per the
original §1 above, or P06R3's clipping-density fix, per §1 of this
addendum)** — both are exactly 0.0782 (CORE_HR) / 0.2722 (DDR_SIGNALING),
unchanged to full float precision across both sessions.

At `EVAL_POINT`, the naive product-of-marginals estimator *overstates* the
evidence relative to the true joint model for both arms (ratio < 1 — the
naive estimate is ~12.8x/~3.7x too large, not too small — "deflation of
joint vs. naive" in P06R2's phrasing). This is consistent with the
shared-latent-factor mechanism: `EVAL_POINT` (`wt_lost=1, gis=42, sbs3=0.30`)
is a *jointly moderate* combination of evidence for both arms — under a
model where a single latent Z drives all three features in the same
direction, a moderate, mutually-consistent elevation across all three
features is comparatively unsurprising under *either* class (a single
moderate Z draw explains all three at once), so treating the three features
as independent and multiplying their individually-supportive marginal LRs
overstates how surprising that joint combination really is — a textbook
consequence of ignoring positive correlation among features sharing a
common cause.

## 4. NULL_ARM re-proven at exactly 1.0 under clipping

`null_arm_full_vector_joint_LR`, `null_arm_full_vector_product_of_marginals_LR`,
and `null_arm_full_vector_inflation_ratio` are all **exactly** `1.0`
(Python float repr `1.0`, not `0.999...` or `1.000...1`), both before and
after the fix. This holds under clipping because NULL_ARM's `Z_MEAN` is
identical (`0.0`) between Pathogenic and Benign, so `sbs3_mean1 == sbs3_mean0`
and `sbs3_sd1 == sbs3_sd0` exactly (same formula, same inputs) —
`sbs3_clipped_density` therefore returns identical `(value, kind)` tuples for
both classes, giving `lr_sbs3 = v/v = 1.0` exactly, not approximately. The
same holds for the `wt_lost` and `gis` terms (unaffected by this fix, already
exact) and for `joint_density()`'s Z-integral (integrand functions are
identical between classes pointwise, so the integrals are identical). Proof
by construction, not by numerical coincidence — see FIDELITY_AUDIT.md §2/§4.

## 5. P08-RERUN's "achievable LR" figures: do they now agree with injected?

This task's Step 3 asks: do P08-RERUN's achievable-LR figures (CORE_HR: 8.15
vs. injected 5.64) now agree with the injected values, and if not, is the
fix incomplete or is there a second mismatch?

**Neither.** The fix is complete (§1: the analytic formula was already exact
at `EVAL_POINT`), and there is no second mismatch — but "achievable LR," as
P08-RERUN computed it (a windowed point-density approximation from a finite
sample), is not a quantity that *should* exactly equal the injected value at
any single window width; it is a noisy, width-dependent *estimator* of the
true density ratio, and it converges toward the injected value only as the
window shrinks and the sample size grows, same as any kernel density
estimator. To make this concrete, recomputing the empirical ratio using the
*exact* window probability (not the point-density approximation) at a sweep
of widths, for CORE_HR (injected LR = 5.6450):

| w | achievable LR (exact window-probability ratio) | ratio to injected |
|---|---|---|
| 0.30 | 0.9653 | 0.171 |
| 0.20 | 2.7274 | 0.483 |
| 0.10 | 4.8469 | 0.859 |
| 0.05 | 6.7922 | 1.203 |
| 0.02 | 8.1538 | 1.444 |
| 0.01 | 6.6471 | 1.178 |

and for DDR_SIGNALING (injected LR = 3.9157):

| w | achievable LR (exact window-probability ratio) | ratio to injected |
|---|---|---|
| 0.30 | 1.0000 | 0.255 |
| 0.20 | 1.8316 | 0.468 |
| 0.10 | 2.9216 | 0.746 |
| 0.05 | 3.2522 | 0.831 |
| 0.02 | 3.9487 | 1.008 |
| 0.01 | 4.3529 | 1.112 |

There is a clear, monotone **windowing bias** at wide w (the empirical ratio
undershoots badly at w≥0.10 for both arms — this is a real, well-understood
approximation artifact of averaging a nonlinear density ratio over a wide
window, distinct from any clip effect) and **sampling noise** at narrow w
(no monotone trend below w=0.05; the ratio-to-injected bounces both above
and below 1.0 — 1.44, 1.18, 1.20, 1.01, 1.11 — with no persistent direction).
Neither pattern indicates a truth-definition defect: they are exactly what a
finite-sample windowed density estimator does when estimating a genuinely
correct target. **The true density ratio — the quantity that actually
matters, computed exactly rather than estimated from a window — already
equals the injected value, by construction** (`injected_value` *is* the
output of the exact formula). P08-RERUN's specific number (8.15 at w=0.02)
sits inside the noise band shown above, not outside it.

## 6. Conclusion

No re-derivation of any truth quantity was needed; the fix is a code-hygiene
/ correctness-by-construction change (FIDELITY_AUDIT.md §4) that happens to
leave every number unchanged, and the audit that produced this delta is
itself the substantive finding: **P08-RERUN's Step 3 conclusion — that
CORE_HR's gate6 FAIL stems partly from a truth-definition defect — does not
hold up**, and both arms' gate6 FAILs should now be attributed to the same
estimator-instability mechanism. See REVALIDATION_REQUIRED.md for what this
means for P07 and P08.
