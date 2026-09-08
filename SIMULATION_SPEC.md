SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATION_SPEC.md (v2)

SIMULATED: this document specifies `simulate.py`'s design and the full
derivation of every injected quantity in `SIMULATED_TRUTH.tsv`. It is
itself a description of a simulator, not a scientific claim about real
tumors — no ACMG evidence strength is assigned anywhere in this project's
simulated artifacts (Standing Rule 1).

This is a **structural revision** of the simulator built in an earlier
task. §0 below lists the four defects that revision fixed, each with the
fix applied and where to find the proof. Everything after §0 describes
the current (v2) design in full; it does not separately re-derive v1's
now-superseded design.

## 0. Defects fixed in this revision

**DEFECT 1 — the primary target category was never generated.** v1 only
ever injected copy-neutral LOH (`major_cn == cn_total`); bare, deletion-
type `WT_LOSS` (n_t=1, wild-type allele deleted) never occurred, so a
caller's ability to detect the Knudson two-hit event itself was never
tested. **Fix:** deletion-type `WT_LOSS` and deletion-type `VARIANT_LOSS`
(n_t=1, wild-type retained) are now generated across the full purity x
depth grid (§2). Confirmed on this run's actual data: `WT_LOSS` n=2855,
100% with `cn_total=1`; `VARIANT_LOSS` (deletion mechanism) n=1671,
100% with `cn_total=1` (see `SIMULATED_data/SIMULATED_variant_calls.tsv`,
`mechanism` column). Full per-cell instance counts:
`SIMULATED_data/SIMULATED_coverage_report.tsv`.

**DEFECT 2 — an unidentifiable truth category.** v1's `LOH_AMBIGUOUS`
set its injected VAF target to the arithmetic midpoint of the two
loss-direction extremes. Because `expected_vaf(rho,CN_t,X)` is affine in
`X`, that midpoint is *exactly* `expected_vaf(rho,CN_t,CN_t/2)` — the
same value as the `RETENTION` hypothesis, for every purity and every
`CN_t`. This is a real limit of the single-variant binomial model, not of
the simulator, and is not resolvable by changing the midpoint construction.
**Fix (§4 below): injected together with the information needed to
separate it, not dropped.** `AMBIGUOUS` now uses a REAL hidden-direction
target VAF (not a midpoint) at deliberately low, near-floor depth — a
genuinely underpowered call, not a mathematically-guaranteed tie. This
script also now emits per-segment B-allele frequencies from `N_BAF_SNPS`
flanking heterozygous SNPs (§4), which resolve the *separate* degeneracy
between `RETENTION` and any LOH state (`m=0`) — see §4's proof.

**DEFECT 3 — independent features.** v1 drew LOH direction, GIS score,
and SBS3 exposure independently given class, so a product of per-feature
LRs was mathematically identical to the true joint LR — the entire
premise of testing whether a naive product-of-marginals estimator
under-/over-states the truth was vacuous. **Fix (§3):** a shared latent
HR-deficiency variable `Z` now drives all three features (a one-factor
model); the injected joint LR is computed from the TRUE joint density
(1D numerical integration over `Z`), and both the joint LR and the naive
product-of-marginals LR are persisted, along with their ratio. Confirmed
non-trivial on this run: `core_hr_joint_LR`=7.24 vs
`core_hr_product_of_marginals_LR`=92.6 (ratio 0.078 — the naive product
overstates the truth by ~12.8x); `ddr_signaling_joint_LR`=6.20 vs
`ddr_signaling_product_of_marginals_LR`=22.8 (ratio 0.272).

**DEFECT 4 — a weak null.** v1's only null was a single-feature
(sequencing-depth-bucket) indicator; the case a prior version's
regression got wrong was a FULL-FEATURE-VECTOR null returning 0.36
[0.30–0.43] instead of ~1. **Fix (§5):** `NULL_ARM`, a DDR-signaling-
analogue arm (same gene list and link parameters as `DDR_SIGNALING`,
differing only in that its class-conditional `Z` distribution is
IDENTICAL between Pathogenic and Benign) has a true joint LR of exactly
1.0 for every possible evidence vector — proved algebraically in §5, not
merely verified at one point. The old depth-bucket null is kept as a
secondary null per this task's explicit instruction.

Also in this revision: `n` was raised substantially (§6, with a
justification against real Track B class sizes) and the old filename-
only "no v1 reuse" check was replaced with a scan of every emitted
numeric VALUE against the retracted v1 figures (§7).

## 1. Estimand (unchanged from v1, copied from PROTOCOL.md §6)

Every LR-estimand quantity in `SIMULATED_TRUTH.tsv` is

```
LR(E) = P(E | Pathogenic) / P(E | Benign)
```

— never an odds ratio. The new `*_inflation_ratio` quantities use a
distinct estimand string, `LR_RATIO` (a ratio of two LRs, not itself an
LR against which `gate6_recovery.py`'s automatic OR-vs-LR check would
apply) — see §3.

## 2. Tumor/normal pair generation: the purity x depth coverage grid

Every sample belongs to one of 3 arms (`CORE_HR`, `DDR_SIGNALING`,
`NULL_ARM` — gene lists in `simulate.py`'s `GENE_GROUPS`) x 2 classes
(`Pathogenic`, `Benign`). For each (arm, class), samples are drawn into
a **purity x depth grid**:

- **Purity bins:** `LOW` [0.10,0.35), `MID` [0.35,0.65), `HIGH` [0.65,0.95]
- **Depth bins (evaluable range only, tumor depth):** `LOW` [25,45),
  `MID` [45,75), `HIGH` [75,120)

For each of the 9 (purity_bin, depth_bin) cells, `DRAWS_PER_GRID_CELL`
= 200 samples are drawn with purity/depth uniform within that cell's
range. Within each draw, the assigned LOH category is a genuine
stochastic outcome of the shared-latent model (§3) — the grid controls
*difficulty* (how hard the call is), not the *category proportions*
(which are purity/depth-independent, driven only by `Z`/class). Enough
draws per cell (200) ensure every one of the 4 "grid categories"
(`RETENTION`, `CN_NEUTRAL_LOH_WT_LOSS`, `WT_LOSS`, `VARIANT_LOSS`)
reaches `MIN_PER_CELL_GRID` = 5 instances per cell with high probability
— verified on this run: **all 540 IN_SCOPE grid cells meet the minimum**
(`SIMULATED_data/SIMULATED_coverage_report.tsv`; 0 cells below minimum).

`AMBIGUOUS` and `NOT_EVALUABLE` are defined by construction OUTSIDE the
evaluable-depth grid (near-floor depth [20,35) and sub-floor depth [4,19)
respectively) — every grid cell for these two categories is therefore
explicitly declared `OUT_OF_SCOPE` in the coverage report (not silently
absent), with the reason stated; they instead get their own purity-only
allocation (`MIN_PER_CELL_SIDE_ARM` = 8 per (purity_bin, arm, class)).

Every sample also independently draws: gene (uniform within its arm's
gene list), PAM50 subtype (`BENCHMARKS.tsv` `PAM01`), ploidy
(`PLOIDY_RANGE`), a WGD flag (`BENCHMARKS.tsv` `WGD01`, sets baseline
`CN_t` = 4 if WGD else 2), and normal sequencing depth.

### 2.1 Copy-number construction per category

| Category | Mechanism | major_cn | minor_cn | mutant_copies |
|---|---|---|---|---|
| `RETENTION` | — | `CN_t/2` | `CN_t/2` | `CN_t/2` |
| `CN_NEUTRAL_LOH_WT_LOSS` | copy-neutral | `CN_t` | 0 | `CN_t` |
| `WT_LOSS` | **deletion** | **1** | **0** | **1** |
| `VARIANT_LOSS` | copy-neutral | `CN_t` | 0 | 0 |
| `VARIANT_LOSS` | **deletion** | **1** | **0** | **0** |
| `AMBIGUOUS` | deletion | 1 | 0 | 1 or 0 (hidden true direction, 50/50) |
| `NOT_EVALUABLE` | — | `CN_t/2` | `CN_t/2` | `CN_t/2` (irrelevant — depth alone determines this category) |

`RETENTION`'s `mutant_copies = CN_t/2` (not a fixed 1 regardless of
ploidy, as v1 used) is itself a correctness fix made as a side effect of
this rewrite: a preserved heterozygous variant under whole-genome
doubling genuinely occupies half the doubled copies, and using the
ploidy-scaled value here removes a WGD/RETENTION VAF mismatch the prior
LOH-caller-validation task had identified and documented as a disclosed,
out-of-scope-at-the-time limitation. This was not one of the four listed
defects but was fixed in passing since this rewrite touches the same code
path; it does not otherwise change this task's scope.

Tumor/normal reads are drawn binomially around `expected_vaf(purity,
CN_t, mutant_copies)` (PROTOCOL.md §5.2, unchanged) at the depth assigned
by the grid cell (or the side-arm's depth range for AMBIGUOUS/
NOT_EVALUABLE).

## 3. The one-factor shared-latent model and the joint-vs-marginal LR (DEFECT 3)

For each sample, `Z ~ Normal(Z_MEAN[arm][class], 1)` is drawn once and
shared across all three features:

- **LOH direction** (binary): `P(WT_LOST_DIRECTION | Z) = Phi(a[arm] + b[arm]*Z)`
  (a probit link). Given NOT WT-lost, a further ARBITRARY, disclosed,
  Z-independent split (0.6 `RETENTION` / 0.4 `VARIANT_LOSS`) and, given
  either loss direction, an ARBITRARY 0.65/0.35 `DELETION`/`COPY_NEUTRAL`
  mechanism split (deletion weighted higher: large-scale copy loss is the
  more commonly reported real-world second-hit mechanism).
- **GIS/HRD score** (continuous): `GIS = c[arm] + d[arm]*Z + Normal(0, sigma[arm])`.
- **SBS3 exposure** (continuous): `SBS3 = c[arm] + d[arm]*Z + Normal(0, sigma[arm])`,
  clipped to [0, 0.95].

Because all three depend on the SAME `Z`, they are genuinely correlated
given class — exactly the "LOH, HRD and SBS3 are three views of one
event" premise the task requires, and precisely what makes the joint
density differ from a product of marginals.

### 3.1 Marginal LRs (closed form)

`GIS`/`SBS3` given class are linear-Gaussian in `Z`, hence themselves
Gaussian: `X | class ~ Normal(c + d*muZ, sqrt(d^2 * Var(Z) + sigma^2))`.
The `WT_LOST_DIRECTION` marginal probability uses the exact
Gaussian-probit convolution identity (`Var(Z)=1` fixed):

```
P(WT_LOST_DIRECTION | class) = Phi( (a + b*muZ) / sqrt(1 + b^2) )
```

Each marginal LR (`*_wt_lost_direction_LR`, `*_gis_score_LR`,
`*_sbs3_exposure_LR`) is the ratio of these class-conditional marginals,
evaluated at the fixed point `EVAL_POINT = {wt_lost:1, gis:42.0 (the
real BENCHMARKS.tsv HRD03 GIS-positive threshold), sbs3:0.30}`, chosen in
advance.

### 3.2 The joint density (numerical, not closed-form) and the injected joint LR

`simulate.py`'s `joint_density(arm, cls, x)` computes this class-conditional
joint density directly (not a product of marginals):

```
joint_density(x | class) = f(wt_lost, gis, sbs3 | class) = INTEGRAL over Z of
    [ Phi(a+bZ) if wt_lost=1 else (1-Phi(a+bZ)) ]
  * Normal_pdf(gis;  c_GIS  + d_GIS*Z,  sigma_GIS)
  * Normal_pdf(sbs3; c_SBS3 + d_SBS3*Z, sigma_SBS3)
  * Normal_pdf(Z; muZ_class, 1)                        dZ
```

This integral has no closed form (the probit term prevents one), so it
is computed by 1D composite Simpson's-rule integration (`simulate.py`'s
`simpson_integrate()`, stdlib `math` only, Z in [-8,8], 4000 steps) —
reproducible, deterministic, and self-checked: `normalization_self_check()`
integrates `P(wt_lost=1|class) + P(wt_lost=0|class)` over `Z` and confirms
it sums to 1.0 to 10 decimal places for every arm/class this run.

```
joint_LR(x*) = f(x*|Pathogenic) / f(x*|Benign)
product_of_marginals_LR(x*) = [marginal WT LR] * [marginal GIS LR] * [marginal SBS3 LR], same x*
```

**Both are persisted** (`*_joint_LR`, `*_product_of_marginals_LR`), plus
their ratio `*_joint_vs_marginal_inflation_ratio = joint_LR / product_LR`
(estimand `LR_RATIO`, distinct from bare `LR`) — this ratio is the
target quantity a future estimation-pipeline task (referred to in the
originating task as "P09") would need to recover to demonstrate whether
a naive conditional-independence estimator is biased. Confirmed
non-trivial this run (§0's DEFECT 3 entry has the exact numbers): the
naive product overstates `CORE_HR`'s true joint LR by ~12.8x and
`DDR_SIGNALING`'s by ~3.7x.

## 3.1 The SBS3 mutation catalog: real COSMIC shape (P06R2 fix)

`SIMULATED_TRUTH.tsv`'s `*_sbs3_exposure_LR`/`*_joint_LR`/etc. above are
derived entirely from `SBS3_LINK`'s analytic Gaussian model of the
**exposure fraction** (a scalar per sample, e.g. the value compared against
`EVAL_POINT["sbs3"]=0.30`) — they have no dependence on the shape of the
96-trinucleotide-context mutation catalog a signature-calling tool would
actually decompose. That catalog (`SIMULATED_data/SIMULATED_mutation_catalogs.tsv`)
is a SEPARATE, downstream data product: `_emit_sample()` takes the sample's
already-drawn exposure fraction and total mutation count, splits them into
`n_hrd`/`n_bg` integer read counts, then distributes those reads across the
96 contexts using two FIXED 96-context weight vectors, `hrd_shape` and
`background_shape` (identical for every sample in the population).

**P08 found `hrd_shape` was, until this fix, an ARBITRARY, stylized
C>T-favored construction with real cosine similarity 0.688 to real COSMIC
SBS3 and 0.802 to real COSMIC SBS5 — closer to the alternative signature
than to the one it was named after** (`DIAGNOSIS_P08.md` §2,
`REQUIRED_P06_CHANGES.md`). Any tool decomposing the resulting catalog
against real COSMIC references would correctly find little real SBS3 signal
in it, because there mostly wasn't any.

**Fix (P06R2):** `hrd_shape` and `background_shape` are now the REAL COSMIC
v3.6 `SBS3` and `SBS5` weight vectors respectively, read from
`COSMIC_SBS3_SBS5_v3.6_reference.tsv` — extracted live from
the same installed, GATE1.json-verified SigProfilerAssignment 1.1.5 package
Task K used, no hand-tuning, no approximation (see that file's companion
`_PROVENANCE.md` for the exact source path/digest). Real cosine
similarities, computed from that same file:

| pair | cosine similarity |
|---|---|
| SBS3 vs SBS3 (self) | 1.0 |
| SBS3 vs SBS5 (`hrd_shape` vs `background_shape` — the property that must survive this fix) | **0.7928** |
| SBS3 vs SBS39 (an HRD-associated real signature flagged in Task K's own WebSearch) | 0.7909 |
| SBS3 vs (SBS40a+SBS40b+SBS40c, summed — the OLD arbitrary shape's closest real match) | 0.8498 |

This 0.7928 similarity between `hrd_shape` and `background_shape` is a real,
fixed, unavoidable property of these two actual biological signatures — it
is asserted at runtime (`build_signature_shapes()`'s `COSINE_SIM_TO_REAL_SBS5_BAND`
check) to guard against ever "fixing" this defect in the opposite direction
(an unrealistically easy-to-separate target, which would be the same defect
wearing different clothes — P08's own framing).

**Blast radius (verified, not merely reasoned about):** because
`compute_truth_quantities()` never reads `hrd_shape`/`background_shape` (it
only reads `SBS3_LINK`, `GIS_LINK`, `WT_LOST_LINK`, `Z_MEAN`), and because
`build_signature_shapes()` uses its own dedicated RNG stream entirely
separate from each sample's per-sample stream, AND `random.choices()`
consumes exactly `k` draws regardless of the weights it is given (so
swapping `hrd_shape`/`background_shape` does not shift any other draw in a
sample's RNG sequence either) — replacing the shape changes **only**
`SIMULATED_mutation_catalogs.tsv`. Every other output file, including
`SIMULATED_TRUTH.tsv` and `SIMULATED_data/SIMULATED_signature_exposures.tsv`'s
`sbs3_relative_exposure_true` column, is **byte-identical** before and
after this fix — confirmed by a real diff of a full before/after
regeneration, not asserted from code-reading alone. See `TRUTH_DELTA.md`
for the full before/after table and the diff evidence.

## 3.2 SBS3's clipped-density fidelity fix (P06R3)

§3.1's `*_sbs3_exposure_LR` marginal LR is derived from `SBS3_LINK`'s
Gaussian model of `sbs3_raw = c + d*Z + Normal(0, sigma)` — but
`_emit_sample()` actually draws `sbs3 = min(SBS3_CLIP_HI, max(SBS3_CLIP_LO,
sbs3_raw))`, `SBS3_CLIP_LO=0.0`, `SBS3_CLIP_HI=0.95`. P08-RERUN's Step 3
found an apparent mismatch between the analytic (unclipped) formula and
this clipped generative distribution at `EVAL_POINT["sbs3"]=0.30`. P06R3's
`FIDELITY_AUDIT.md` re-tested this rigorously (exact-CDF binomial testing
across 4 window widths, instead of a narrow-window point-density
approximation) and found **it does not replicate**: clipping is a
measure-preserving identity map on the open interval between the clip
bounds — for any interior point, `P(clip(raw) in [a,b)) == P(raw in
[a,b))` exactly, since `clip(v)==v` there — so the continuous density on
the interior is mathematically unchanged by clipping. `0.30` sits strictly
interior to `[0, 0.95]` for every class in every arm (0.21–1.94 SD from the
relevant class means), so the pre-existing formula was already exact there.

`simulate.py` now makes this explicit and defensive rather than merely
correct-by-luck: `sbs3_clipped_density(x, mean, sd)` returns the exact
interior density (closed form, no numerical integration needed — the
interior-identity argument above makes the closed form exact) for `x`
strictly inside `(SBS3_CLIP_LO, SBS3_CLIP_HI)`, or the exact boundary
point-mass probability at `x <= SBS3_CLIP_LO`/`x >= SBS3_CLIP_HI`, tagged
by kind so a caller cannot silently divide a density by a point mass (or
vice versa) if a future `EVAL_POINT` ever lands on a boundary.
`compute_truth_quantities()`'s SBS3 rows, `product_of_marginals_lr()`, and
`joint_density()`'s per-Z sbs3 term all now go through this function.
**Every `SIMULATED_TRUTH.tsv` quantity is confirmed byte-identical before
and after this fix** (see `TRUTH_DELTA.md` §1) — this is the expected,
correct outcome given the interior-identity argument above, not something
this fix engineered. See `FIDELITY_AUDIT.md` for the full per-feature audit
(WT_LOST direction, GIS score, and the latent Z were also re-checked and
confirmed to have no clip/floor/ceiling divergence at all) and
`REVALIDATION_REQUIRED.md` for what this means for P07/P08.

## 3.3 pam50_subtype: from decorative to a genuine generative input (subtype fix)

P-DEC-1 proved `pam50_subtype` was drawn independently of `cls` and of
every evidentiary feature, and that Normal-like was never generated at all
despite being named in `PROTOCOL.md`. This fix wires subtype into the
generative model as a genuine, class-independent confounder, per the full
design specification in `SUBTYPE_MODEL.md` (written and fixed BEFORE any
`simulate.py` code change, per that task's STEP 1).

**Mechanism.** Two channels, both class-independent additive shifts
applied identically to Pathogenic and Benign within a subtype (this is
what makes it a confound rather than a second hidden class signal):

1. `z = Normal(Z_MEAN[arm][cls] + SUBTYPE_Z_SHIFT[subtype], Z_SD)` — a
   generic elevated-instability-propensity term, nonzero only for Basal
   (`0.4`, modest relative to the 1.3–2.5 class gaps already in the model).
2. `gis = c + d*z + SUBTYPE_GIS_SHIFT[subtype] + Normal(0, sigma)` — a
   separate, larger, direct GIS elevation (`10.0` for Basal), motivated by
   literature reporting basal-like tumors carry elevated genomic
   instability independent of germline BRCA1/2 status (qualitative
   existence cited, magnitude ARBITRARY — `SUBTYPE_MODEL.md` §2).

SBS3 and WT_LOST direction get no separate direct subtype term (only the
small indirect effect via Z) — an evidence-absence decision, not an
oversight (`SUBTYPE_MODEL.md` §3). `PAM50_PROPORTIONS` is now a genuine
5-category distribution including Normal-like (`SUBTYPE_MODEL.md` §4).

**Mixture-density mechanics.** Once subtype genuinely shifts a
subpopulation's mean, the pooled (subtype-collapsed) truth is a
prevalence-weighted MIXTURE of Gaussians, not a single Gaussian with the
mixture's pooled mean/sd — `phi_pdf` evaluated at a "mixture mean" would be
mathematically wrong. `simulate.py` adds
`gaussian_density_collapsed()`/`sbs3_density_collapsed()`/
`joint_density_collapsed()`, each a prevalence-weighted sum of the five
per-subtype component densities evaluated at the same point, not a moment-
matched single-Gaussian shortcut. The pre-existing bare functions
(`marginal_wt_lost_prob`, `marginal_gaussian_feature_params`,
`joint_density`, `joint_lr`, `product_of_marginals_lr`) are left
unchanged, for `stake_ablation.py`'s existing call sites; new
`_subtype`/`_collapsed`-suffixed functions carry the corrected truth.

**Verification.** LumA (`SUBTYPE_Z_SHIFT`/`SUBTYPE_GIS_SHIFT` both `0.0`)
strata reproduce the pre-fix pooled values exactly, confirming the mixture
machinery collapses correctly to the old single-Gaussian case when every
shift is zero. Full before→after numbers for all 91 `SIMULATED_TRUTH.tsv`
quantities, the joint/product-of-marginals/ratio reporting, the NULL_ARM
re-proof (exactly 1.0 in every stratum), and the STEP 3 confounding
demonstration (naive pooled CORE_HR GIS LR favors Pathogenic while the
Basal stratum alone flips to favor Benign) are in `TRUTH_DELTA.md`'s
subtype-fix addendum. `REVALIDATION_REQUIRED.md`'s subtype-fix addendum
concludes both P07 and P08 need re-running (unlike the P06R3 fix above,
this one moves the actual scored targets). `PARAMETER_PROVENANCE.tsv`
carries every new parameter's `source_type` and rationale.

## 4. LOH_AMBIGUOUS and the BAF channel (DEFECT 2)

### 4.1 AMBIGUOUS's new construction

Unlike v1, `AMBIGUOUS` samples use a REAL, non-midpoint target VAF: a
hidden true direction is drawn (50/50, not Z-linked — this is an
engineered hard case, not a Z-model outcome), `major_cn=1, minor_cn=0`
(deletion mechanism, matching `WT_LOSS`/`VARIANT_LOSS`'s deletion
flavor), `mutant_copies` set from the hidden direction, and depth drawn
from `[20,35)` — near, but not below, the evaluable floor. At this depth,
the exact binomial test (PROTOCOL.md §5.1/§5.2) genuinely sometimes
cannot reject either hypothesis — the ambiguity is a real, depth-driven
statistical property of the data, not a rigged mathematical identity.
Confirmed this run: only 43/144 (29.9%) of `AMBIGUOUS` samples' own
single-variant reads resolve to `classify_loh() == LOH_AMBIGUOUS` — the
rest resolve to a definite direction by chance, exactly as expected for
a genuinely (not artificially) underpowered call
(`SIMULATED_data/SIMULATED_loh_injection_self_check.md`).

### 4.2 The BAF channel — what it resolves, and the proof

`simulate.py` emits `N_BAF_SNPS` = 15 flanking heterozygous SNPs per
segment (`SIMULATED_data/SIMULATED_baf_segments.tsv`: `sample_id,
snp_index, phase, normal_ref_reads, normal_alt_reads, tumor_ref_reads,
tumor_alt_reads, mirrored_baf`). Each SNP's phase (whether ITS OWN alt
allele sits on the major or minor copy) is independent and unknown a
priori (50/50) — this is what makes a real BAF track show two symmetric
bands for an imbalanced segment. Mirroring (`min(vaf, 1-vaf)`) folds
away the phase ambiguity, revealing the true |allelic imbalance|
regardless of which physical allele happened to be "alt" at each SNP.
`SIMULATED_variant_calls.tsv` also carries a convenience
`mirrored_baf_mean`/`n_baf_snps` summary per sample.

**Proof this breaks the RETENTION-vs-AMBIGUOUS degeneracy:** `expected_vaf`
is affine in `X`. For `RETENTION` (`X = CN_t/2`, i.e. both phase choices
give the SAME expected VAF since major=minor):

```
E[VAF | X=CN_t/2] = (p*(CN_t/2) + (1-p)) / (p*CN_t + 2(1-p)) = 1/2   exactly,
```

for every purity `p` and every `CN_t` — an invariant, algebraically
independent of purity/ploidy. For ANY `m=0` category (`CN_NEUTRAL_LOH_WT_LOSS`,
`WT_LOSS`, `VARIANT_LOSS`, `AMBIGUOUS`), both phase choices (X=CN_t or
X=0) mirror to the SAME value:

```
mirror(E[VAF|X=CN_t]) = mirror(E[VAF|X=0]) = (1-p) / (p*CN_t + 2(1-p))   <  1/2  for any p > 0.
```

So **`E[mirrored BAF] = 0.5` for `RETENTION`, and `< 0.5` for every LOH
state (including `AMBIGUOUS`), for every purity and `CN_t`** — a clean,
provable separation entirely independent of the single at-risk variant's
own read noise. Confirmed empirically this run (n and stdev shown; SEMs
are non-overlapping by a wide margin):

| Category | n | mean mirrored BAF | sd |
|---|---|---|---|
| `RETENTION` | 3894 | 0.4478 | 0.0104 |
| `AMBIGUOUS` | 144 | 0.3102 | 0.1160 |
| `CN_NEUTRAL_LOH_WT_LOSS` | 1504 | 0.2316 | 0.1254 |
| `WT_LOSS` | 2855 | 0.3040 | 0.1175 |
| `VARIANT_LOSS` | 2547 | 0.2793 | 0.1240 |
| `NOT_EVALUABLE` | 144 | 0.4480 | 0.0099 |

(`RETENTION`'s observed mean, 0.4478, sits slightly below the true 0.5
target — expected: mirroring a noisy binomial observation around a true
mean of exactly 0.5 biases the empirical mean downward, a real,
well-understood property of the fold/mirror transform under finite
depth, not an error.) `RETENTION` is separated from every LOH state
(including `AMBIGUOUS`) by 0.12–0.22 in mean mirrored BAF, against SEMs
of ~0.0002 (`RETENTION`, n=3894) and ~0.01 (`AMBIGUOUS`, n=144) — the gap
is many SEMs wide, not a coincidence of this run's particular seed.

BAF does NOT resolve DIRECTION (which specific allele, WT or mutant, is
retained) — both loss directions mirror to the identical value, by the
same algebra above. Direction remains the single at-risk variant's own
read-count job (PROTOCOL.md §5.1/§5.2), exactly where `AMBIGUOUS`'s
genuine, depth-driven uncertainty now correctly lives.

**Decision recorded, per the task's requirement:** `LOH_AMBIGUOUS` was
NOT dropped as an injectable category (the "drop it" option was
available and considered) — it was resolved by injecting it together
with the BAF channel, matching the task's second option, because
dropping it would have discarded a real, useful evidentiary state
(PROTOCOL.md §5.1's own category 4) rather than fixing the actual defect
(an unresolvable construction), and because the BAF channel was already
independently required by this task's DO list for its own sake.

## 5. NULL_ARM — a full-feature-vector null (DEFECT 4)

`NULL_ARM` shares `DDR_SIGNALING`'s gene list and every link parameter
(`WT_LOST_LINK`, `GIS_LINK`, `SBS3_LINK` — identical dicts), differing
ONLY in `Z_MEAN`: `{"Pathogenic": 0.0, "Benign": 0.0}` (identical,
vs. `DDR_SIGNALING`'s `{0.8, -0.5}`).

**Proof the true joint LR is exactly 1.0 for every possible evidence
vector `x`, not merely at one evaluation point:** `f(x|Pathogenic)` and
`f(x|Benign)` are the SAME function of `x` when every parameter feeding
that function (`Z`'s mean AND variance, and every link coefficient) is
identical between classes — the two class-conditional distributions are
literally the same distribution. Therefore `LR(x) = f(x|Path)/f(x|Benign)
= f(x)/f(x) = 1` identically, for every `x` in the support, not just at
`EVAL_POINT`. Since every marginal of two identical distributions is
itself identical, the naive product-of-marginals estimator is ALSO
exactly 1.0 here — this null tests the FULL feature vector (the case a
prior version's regression got wrong, returning 0.36 [0.30–0.43] instead
of ~1), not merely a single engineered-independent feature. Verified
numerically at `EVAL_POINT` this run:
`null_arm_full_vector_joint_LR` = 1.0, `null_arm_full_vector_product_of_marginals_LR`
= 1.0, `null_arm_full_vector_inflation_ratio` = 1.0 — all exact
(`repr()`-written floats, no rounding).

The old, single-feature `null_sequencing_depth_bucket_LR` (an engineered-
identical-by-construction categorical coin flip) is kept as a **secondary**
null per the task's explicit instruction.

## 6. Raising n — justification against realistic Track B class sizes

**New n: `DRAWS_PER_GRID_CELL` = 200 per (purity_bin, depth_bin, arm,
class) grid cell** (9 cells) **+ `MIN_PER_CELL_SIDE_ARM` = 8 per
(purity_bin, arm, class) for each of `AMBIGUOUS`/`NOT_EVALUABLE`** (3
purity bins each) = `9*200 + 3*8 + 3*8` = **1848 samples per (arm,
class)**, i.e. **3696 per arm** (Pathogenic+Benign), **11088 total**
across all 3 arms — up from v1's 60 total (15 per cell x 4 cells).

**This n is derived bottom-up from DEFECT 1's coverage-grid requirement**
(enough draws per cell that all 4 grid categories clear
`MIN_PER_CELL_GRID`=5 with high probability — verified, not merely
assumed: 0 of 540 in-scope cells fall short this run), **not picked to
match real-world Track B class sizes.** Those are, in fact, far smaller:

- `BENCHMARKS.tsv` `BRCA_PREV01` (Yost et al. 2019, JNCI Cancer Spectrum,
  live-cited): a TCGA-derived breast-cancer cohort shows 5.0% (39/779)
  germline BRCA1/BRCA2 pathogenic-carrier frequency — BRCA1/2 dominate
  this project's `CORE_HR` gene list.
- `BENCHMARKS.tsv` `DDR_PREV01` (Couch et al. 2017, JAMA Oncology,
  live-cited): a large panel-testing-referred cohort shows CHEK2 1.73%,
  ATM 1.06% carrier prevalence — ATM+CHEK2 dominate `DDR_SIGNALING`.

Extrapolating both (arithmetic done here, not itself a published figure,
and explicitly caveated: Couch 2017 is a clinically-referred cohort, not
an unselected population, so its prevalence likely overstates an
unselected cohort's true rate) to a ~1097-patient TCGA-BRCA-scale cohort:
**`CORE_HR` pathogenic class ≈ 55–75 patients; `DDR_SIGNALING` pathogenic
class ≈ 25–35 patients** — both far below this simulator's 1848-per-class
figure.

**This is a deliberate, disclosed departure, not an oversight.** Stage 2's
purpose is to verify the ESTIMATION MACHINERY recovers known targets
correctly given adequate statistical power; it is not a claim about what
a real Track B run will produce. A real Stage 1 run at the realistic
class sizes above may frequently need to declare `INSUFFICIENT_N`
(PROTOCOL.md §8, `n < 20` per stratum — note CORE_HR's realistic ~55-75
total, split across ~10 sub-gene and PAM50 strata per PROTOCOL.md §8,
could plausibly fall under 20 in several individual strata even though
the gene-group-level total clears it) for individual strata even as the
gene-group-level total clears PROTOCOL's n≥20 floor. This tension is
recorded here explicitly rather than hidden by picking a "realistic-
looking" n that would leave gate6 exactly as imprecise as before.

## 7. Numeric v1-reuse scan (replaces the filename-only check)

A filename scan tests naming, not values — the actual rule (Standing
Rule 3/"do not reuse a retracted figure") is about VALUES. `simulate.py`
now scans every emitted numeric value in two tiers:

- **Tier 1 (what actually matters):** every `SIMULATED_TRUTH.tsv`
  `injected_value` (16 design-level quantities) against all 9 retracted
  v1 figures (`-3.54, 34.0, 0.9598, 0.9976, 15.13, 4.45, 0.99, 80.0,
  91.7`) at `rel_tol=1e-3, abs_tol=1e-6`. **Result this run: ZERO
  matches.**
- **Tier 2 (context, not itself evidence):** every raw per-sample/per-
  observation value (depths, read counts, per-SNP BAFs, purity/ploidy/
  GIS draws — ~1.2M values per figure this run). Matches WERE found here
  for several figures (e.g. `normal_depth=34.0` — an exact match, since
  `normal_depth` is an integer-valued field and 34 is a common draw
  within its distribution). **These are reported in full (Standing Rule
  4), and are expected, not evidence of reuse:** integer-valued fields
  will exactly equal an integer-valued target at a predictable base rate
  purely from quantization, and continuous fields drawn from a wide
  distribution will occasionally land within 0.1% of any fixed target
  purely by chance when ~1.2M values are scanned per figure. No design-
  level parameter was tuned to produce any Tier-2 coincidence.

Full detail, every figure's scanned-count and match locations:
`V1_NUMERIC_SCAN.tsv`; narrative: `SIMULATED_data/SIMULATED_no_v1_reuse_check.md`.

## 8. File layout

```
SIMULATED_data/
  SIMULATED_sample_metadata.tsv     <- +purity_bin, depth_regime, gis_score columns (new)
  SIMULATED_variant_calls.tsv       <- +mechanism, mirrored_baf_mean, n_baf_snps columns (new)
  SIMULATED_baf_segments.tsv        <- NEW: per-segment flanking-SNP BAF (DEFECT 2)
  SIMULATED_mutation_catalogs.tsv
  SIMULATED_signature_exposures.tsv
  SIMULATED_coverage_report.tsv     <- NEW: every (category,arm,class,purity_bin,depth_regime) cell,
                                        count + scope_status + reason (DEFECT 1's coverage requirement)
  SIMULATED_loh_injection_self_check.md
  SIMULATED_no_v1_reuse_check.md    <- now narrates the numeric scan, not a filename scan

SIMULATED_TRUTH.tsv                 <- 16 quantities now (was 6), estimand column populated for all
SIMULATED_TRUTH_detail/
  SIMULATED_sample_labels.tsv       <- +z_latent, hidden_direction columns (new)

V1_NUMERIC_SCAN.tsv                 <- NEW deliverable: the two-tier numeric scan, every figure
```

## 9. Known, disclosed downstream incompatibility (Standing Rule 4/8)

**`loh_caller.py` (built against v1's schema, a prior task) is now
BROKEN against this revision** — confirmed by actually running it:
`KeyError: 'WT_LOSS'` in `load_loci()`'s `TRUTH_CATEGORY_MAP` lookup,
because v1's `assigned_loh_category` values were PROTOCOL vocabulary
(`RETAINED`, `LOH_SECOND_HIT`, ...) requiring translation, whereas v2
emits the direction-aware vocabulary directly (`RETENTION`, `WT_LOSS`,
...) with no such mapping needed or present. `scripts/check_loh_caller_acceptance.py`
and the `SIMULATED_loh_validation/` artifacts it depends on are
consequently stale/inapplicable to this revision's output too. This is
**explicitly out of scope for this task** (the DELIVERABLE list here is
`simulate.py, SIMULATED_data/, SIMULATED_TRUTH.tsv, SIMULATION_SPEC.md,
PARAMETER_PROVENANCE.tsv, V1_NUMERIC_SCAN.tsv` only) and per Standing
Rule 9 is not fixed here — updating `loh_caller.py` for the new schema
is a follow-up task. Reported here prominently, per Standing Rule 8,
rather than left for a future session to discover by surprise.
