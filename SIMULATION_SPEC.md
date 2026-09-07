SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATION_SPEC.md

SIMULATED: this document specifies `simulate.py`'s design and, in full,
the derivation of every injected likelihood ratio in `SIMULATED_TRUTH.tsv`.
It is itself a description of a simulator, not a scientific claim about
real tumors — no ACMG evidence strength is assigned anywhere in this
project's simulated artifacts (Standing Rule 1).

## Scope note

This deliverable builds the **simulator** only: it generates synthetic
tumor/normal pairs with known ground truth and writes that truth down. It
does **not** run PROTOCOL.md §7's estimation pipeline (KDE/Jeffreys
class-conditional LR fitting, variant-grouped CV, patient-clustered
bootstrap) against this simulated data — that is `gate6_recovery.py`'s
job, consuming a *future* task's fitted output against the
`SIMULATED_TRUTH.tsv` this script produces. Per Standing Rule 9, that next
step is explicitly out of scope here.

## 1. Estimand (copied from PROTOCOL.md §6, not redefined)

Every injected quantity in `SIMULATED_TRUTH.tsv` is a **likelihood ratio**:

```
LR(E) = P(E | Pathogenic) / P(E | Benign)
```

— never an odds ratio. `gate6_recovery.py` treats an OR compared against
an LR target as an automatic FAIL regardless of numeric CI overlap; this
simulator only ever injects LR-estimand quantities, and every row in
`SIMULATED_TRUTH.tsv` has `estimand = LR`.

## 2. The six injected quantities and their derivations

Each is computed **analytically**, in closed form, directly from the same
class-conditional distribution parameters that `simulate.py` uses to draw
the actual per-sample data (see `PARAMETER_PROVENANCE.tsv` for the
provenance of every number below). This is the load-bearing design choice
that makes the truth genuine: the "true LR" is not a separately-invented
label bolted onto arbitrary data — it is the actual data-generating
parameter, in closed form.

### 2.1 Categorical (Bernoulli) features — LOH_SECOND_HIT

For a binary evidence event `E = {variant shows LOH_SECOND_HIT}`
(PROTOCOL.md §5.1 category), with class-conditional Bernoulli
probabilities `π₁ = P(E|Pathogenic)` and `π₀ = P(E|Benign)`:

```
LR(E) = P(E|Pathogenic) / P(E|Benign) = π₁ / π₀
```

This is the estimand formula directly — no additional derivation step,
since a Bernoulli's "density" at the observed outcome *is* its
probability mass.

**`core_hr_loh_second_hit_LR`**: π₁ = 0.70 (CORE_HR, Pathogenic), π₀ = 0.10
(CORE_HR, Benign) → `LR = 0.70 / 0.10 = 7.0`.

**`ddr_signaling_loh_second_hit_LR`**: π₁ = 0.40, π₀ = 0.15 →
`LR = 0.40 / 0.15 = 2.6666...7`.

`simulate.py` draws each sample's assigned LOH category from exactly
these Bernoulli probabilities (`draw_loh_category()`), then constructs
the tumor allele-specific copy number and read counts for that category
using PROTOCOL.md §5.2's own binomial VAF model (`cn_and_depth_for_category()`,
`expected_vaf()`) — so the *data*, not just the label, is generated
consistent with the injected LOH state.

### 2.2 Continuous (Gaussian) features — HRD/GIS score, SBS3 exposure

For continuous evidence `E = x` with class-conditional densities
`f(x|Pathogenic) = Normal(μ₁, σ₁)` and `f(x|Benign) = Normal(μ₀, σ₀)`:

```
LR(E=x) = f(x|Pathogenic) / f(x|Benign)
        = [ (1/(σ₁√(2π))) · exp(−(x−μ₁)²/(2σ₁²)) ]
        / [ (1/(σ₀√(2π))) · exp(−(x−μ₀)²/(2σ₀²)) ]
```

implemented exactly as `gaussian_lr()` / `norm_pdf()` in `simulate.py`.
Each quantity below is this ratio evaluated at one fixed `x`, chosen in
advance (not searched for after seeing any result).

**`core_hr_gis_score_LR`** (CORE_HR gene group): Pathogenic ~ N(55, 12),
Benign ~ N(25, 10), evaluated at x = 55 (the Pathogenic mean, also above
the BENCHMARKS.tsv `HRD03` GIS≥42 threshold):

```
f(55 | N(55,12)) = 1/(12√(2π)) · exp(0)          = 0.0332452...
f(55 | N(25,10)) = 1/(10√(2π)) · exp(−(30)²/200) = 0.0004432...
LR = 0.0332452 / 0.0004432 = 75.01427608376818
```

**`ddr_signaling_gis_score_LR`** (DDR_SIGNALING gene group): Pathogenic ~
N(40, 15), Benign ~ N(25, 12), evaluated at x = 40:

```
LR = f(40|N(40,15)) / f(40|N(25,12)) = 1.7473606486524944
```

Deliberately chosen so this quantity's true LR (1.75) is non-null but
still falls *below* the BENCHMARKS.tsv `ODDS01` supporting threshold
(2.08) — a concrete illustration that "not exactly 1.0" and "clears the
supporting-evidence bar" are different claims; PROTOCOL.md §10 requires
this distinction be kept explicit.

**`core_hr_sbs3_exposure_LR`**: Pathogenic ~ N(0.35, 0.10), Benign ~
N(0.10, 0.08), evaluated at x = 0.35:

```
LR = f(0.35|N(0.35,0.10)) / f(0.35|N(0.10,0.08)) = 105.6011169807864
```

`simulate.py` draws each sample's true SBS3-like relative exposure from
these same Normals, then builds an actual 96-trinucleotide-context
mutation catalog: total mutation count ~ Normal(mean = `MEAN_MUTATIONS_PER_EXOME`
= 60.05, `BENCHMARKS.tsv` `TMB01`), split between an arbitrary "HRD-like"
signature shape and an arbitrary "background" shape in proportion to the
drawn exposure (see `PARAMETER_PROVENANCE.tsv` for why these shapes are
declared arbitrary rather than the real COSMIC SBS3 weights).

### 2.3 The injected null

PROTOCOL.md §11 requires at least one injected-null quantity (true
LR = 1.0). **`null_sequencing_depth_bucket_LR`** uses a categorical
"HIGH_DEPTH" indicator with `P(HIGH_DEPTH|Pathogenic) = P(HIGH_DEPTH|Benign)
= 0.50` — identical *by construction*, not by coincidence of sampling:

```
LR = 0.50 / 0.50 = 1.0   exactly
```

`is_null = TRUE` for this row in `SIMULATED_TRUTH.tsv`; every other row
is `FALSE`.

## 3. ACMG-band coverage (context, not itself an ACMG classification)

For reference only — no ACMG evidence strength is assigned to any of
these values anywhere in this project's simulated artifacts, per
Standing Rule 1. This just documents that the six chosen parameter sets
span a useful range of `BENCHMARKS.tsv` `ODDS01` bands, which is why
these particular parameter values were picked:

| Quantity | True LR | ODDS01 band it would fall in, if this were a real Stage-1 result |
|---|---|---|
| `null_sequencing_depth_bucket_LR` | 1.0 | (null — no evidence direction) |
| `ddr_signaling_gis_score_LR` | 1.747 | below supporting (2.08) — NO_EVIDENCE |
| `ddr_signaling_loh_second_hit_LR` | 2.667 | SUPPORTING (2.08–4.33) |
| `core_hr_loh_second_hit_LR` | 7.0 | MODERATE (4.33–18.7) |
| `core_hr_gis_score_LR` | 75.014 | STRONG (18.7–350) |
| `core_hr_sbs3_exposure_LR` | 105.601 | STRONG (18.7–350) |

## 4. Tumor/normal pair generation

For each of 4 cells (`{CORE_HR, DDR_SIGNALING} × {Pathogenic, Benign}`),
`N_PER_CELL = 15` samples are drawn (60 total), each independently
assigned:

- a gene (uniform within its gene group's PROTOCOL.md §1 list)
- a PAM50 subtype (weighted by `BENCHMARKS.tsv` `PAM01`)
- purity ~ Uniform(0.10, 0.95)
- ploidy ~ Uniform(1.5, 5.5)
- a WGD flag ~ Bernoulli(`BENCHMARKS.tsv` `WGD01` = 0.30), which sets the
  per-locus total copy number used below (`CN_t = 4` if WGD else `2`)
- normal sequencing depth ~ Normal(40, 8)
- an LOH category (§2.1) and, from it, allele-specific copy number
  (major/minor) and a target tumor VAF via PROTOCOL.md §5.2's exact
  formula `E[VAF|X] = (p·X + (1−p)·1) / (p·CN_t + (1−p)·2)`
- actual tumor/normal ALT/REF read counts, drawn binomially around that
  target VAF and around a normal-VAF of 0.5, at depths drawn from
  Normal(80, 15) / Normal(40, 8) (tumor/normal) — except `LOH_AMBIGUOUS`
  (deliberately borderline depth, 20–25x) and `NOT_EVALUABLE`
  (deliberately below PROTOCOL.md's 20x evaluable floor)
- a true SBS3-like exposure (§2.2) and a synthetic 96-context mutation
  catalog built from it

**Self-check, run and reported on every invocation** (not merely
described here): `simulate.py` re-implements PROTOCOL.md §5.1/§5.2's own
binomial-test classification logic (`classify_loh()` /
`binom_two_sided_pvalue()`, stdlib-only exact binomial p-values, no
scipy) and re-classifies every generated sample's read counts, comparing
the recovered category against the category it was told to inject.
Result this run: **57/60 samples' recovered category matched the
assigned category** (see `SIMULATED_data/SIMULATED_loh_injection_self_check.md`
for the live figure). A less-than-100% match rate is expected and
correct, not a bug: `LOH_AMBIGUOUS` is defined (PROTOCOL.md §5.1) as a
locus where the binomial test *cannot* confidently distinguish the two
hypotheses — under real binomial sampling noise it will sometimes
resolve to a definite category by chance, exactly as a real ambiguous
locus would. `NOT_EVALUABLE` is expected to match 100% of the time,
since it is determined by depth alone.

## 5. File layout

```
SIMULATED_data/                          <- observable, pipeline-input-shaped files
  SIMULATED_sample_metadata.tsv
  SIMULATED_variant_calls.tsv
  SIMULATED_mutation_catalogs.tsv
  SIMULATED_signature_exposures.tsv
  SIMULATED_loh_injection_self_check.md
  SIMULATED_no_v1_reuse_check.md
  README.md

SIMULATED_TRUTH.tsv                      <- repo root: aggregate LR ground truth, separate from SIMULATED_data/
SIMULATED_TRUTH_detail/                  <- also separate from SIMULATED_data/
  SIMULATED_sample_labels.tsv            <- per-sample hidden class label (the answer key)
  README.md
```

`SIMULATED_TRUTH.tsv` and `SIMULATED_TRUTH_detail/` are both physically
separate directories/files from `SIMULATED_data/`, satisfying the
task's "in a directory separate from the simulated data" requirement —
not nested inside it.

## 6. Parameter independence (Standing Rule: no tuning to reproduce a prior number)

Every constant `simulate.py` uses is listed in `PARAMETER_PROVENANCE.tsv`
with either a `BENCHMARKS.tsv` row ID or an explicit `ARBITRARY` +
rationale. None of the `ARBITRARY` values was chosen by first computing
what value would reproduce a specific prior output — each is justified
independently (either against PROTOCOL.md's own pre-registered
thresholds, against an installed tool's own operational bounds, or as a
declared free design choice for spanning a useful evidence range).

**No-v1-reuse check** (run automatically on every `simulate.py`
invocation, not a one-off manual claim): a repository-wide scan for any
filename matching the word `v1` or containing `retract` (excluding
`.git/`). This session's scan found **zero** such files anywhere in this
repository — there are no retracted v1 artifacts to have reproduced a
value from, confirmed by the scan rather than assumed. Full output:
`SIMULATED_data/SIMULATED_no_v1_reuse_check.md`.
