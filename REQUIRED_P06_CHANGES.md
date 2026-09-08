SIMULATED DATA — NOT A SCIENTIFIC RESULT

# REQUIRED_P06_CHANGES.md — simulate.py fix required before P08 can re-run

SIMULATED: this document specifies a REQUIRED change to `simulate.py` (owned
by the P06 task). Per this task's explicit instruction, `simulate.py` is
**not modified from this prompt** — P06's own acceptance criteria and truth
derivations depend on it, and that task, not this one, owns the change.

## The defect (see DIAGNOSIS_P08.md §2 for full evidence)

`simulate.py`'s `build_signature_shapes()` (lines 538-541) generates the
96-trinucleotide-context vector it calls `hrd_shape` — used to inject
"SBS3-like" mutations into `SIMULATED_data/SIMULATED_mutation_catalogs.tsv`,
which `core_hr_sbs3_exposure_LR` and `ddr_signaling_sbs3_exposure_LR` in
`SIMULATED_TRUTH.tsv` are defined against — via `_make_shape(rng, "C>T",
4.0)`: a RANDOM shape that upweights the C>T substitution class 4x with
per-context `uniform(0.7, 1.3)` jitter. This was disclosed in-code as
"ARBITRARY, stylized... NOT real COSMIC SBS3 weights" (correctly, since
cancer.sanger.ac.uk was network-blocked when `simulate.py` was written), but
its quantitative resemblance to real SBS3 was never checked.

This session (Task K) obtained live access to the real COSMIC v3.6 SBS3
weight vector (bundled with the now-verified-working SigProfilerAssignment
1.1.5 package). Reproducing the exact seeded `hrd_shape`
(`build_signature_shapes(random.Random(SEED+1))`, `SEED=20260908`) and
computing its real cosine similarity to real COSMIC SBS3:

| comparison | cosine similarity |
|---|---|
| ARBITRARY `hrd_shape` vs. real COSMIC **SBS3** | **0.6877** |
| ARBITRARY `hrd_shape` vs. real COSMIC **SBS5** (the alternative/background signature) | **0.8015** |
| Most cosine-similar real COSMIC signature to the ARBITRARY `hrd_shape` | **SBS40a (0.8330)**, not SBS3 |

**The vector being injected as "SBS3-like" is more similar to SBS5 (the
signature it is supposed to be distinguished FROM) than to real SBS3, and
its closest real match isn't SBS3 at all.** Any tool decomposing against
real COSMIC references (SigProfilerAssignment, SigMA, or any future
signature tool) will correctly find little real-SBS3 signal in this catalog,
because there mostly isn't any — this is not a tool-recovery failure, it is
an injected-truth-quantity that does not measure what its name and
`SIMULATED_TRUTH.tsv` estimand definition claim it measures.

## Required fix

Replace `_make_shape(rng, "C>T", 4.0)` / `_make_shape(rng, "", 1.0)` with
REAL COSMIC signature weight vectors as the injected "HRD-process" and
"background" 96-context shapes — exactly the approach Task K's own
`signatures.py` already uses for its independent validation catalog
(`SIMULATED_signature_work/SIMULATED_cosmic_reference_extract.tsv`, real
COSMIC v3.6 SBS3 and SBS5, extracted live from the installed
SigProfilerAssignment package, no network access required — see that file
and its companion `SIMULATED_cosmic_reference_provenance.json` for the exact
extraction method P06 can reuse). Recommended:

1. `hrd_shape` := real COSMIC v3.6 SBS3 (normalized to sum to 1 over the 96
   contexts, same context ordering as `simulate.py`'s existing
   `SBS_CONTEXTS` list — a direct label-matched substitution, no reordering
   needed since both use the standard `{5'}[{sub}]{3'}` 96-context
   convention).
2. `background_shape` := real COSMIC v3.6 SBS5 (same extraction).
3. Document the change in `SIMULATION_SPEC.md` (which section currently
   describes `_make_shape`/`build_signature_shapes` as producing
   "ARBITRARY, stylized" shapes) and in `PARAMETER_PROVENANCE.tsv` (add rows
   for `hrd_shape`/`background_shape` with `source_type=BENCHMARKS_ROW` or a
   new source-type category for "installed package data," referencing the
   exact COSMIC file path and package version — no such rows currently
   exist for these two vectors at all; only the exposure-FRACTION parameters
   `SBS3_LINK.*` are documented in `PARAMETER_PROVENANCE.tsv`, and those are
   NOT implicated by this defect).
4. **Do not change `SBS3_LINK`'s c/d/sigma parameters** (`PARAMETER_PROVENANCE.tsv`
   rows for `SBS3_LINK.CORE_HR/.DDR_SIGNALING/.NULL_ARM`) — DIAGNOSIS_P08.md
   §1 found the injected exposure FRACTION magnitudes are not the problem;
   only the 96-context SHAPE is.
5. Re-derive `SIMULATED_data/SIMULATED_mutation_catalogs.tsv`,
   `SIMULATED_data/SIMULATED_signature_exposures.tsv`, and
   `V1_NUMERIC_SCAN.tsv` (the numeric-scan baseline) after the shape change
   — every downstream file that reads the old arbitrary-shape catalog is
   stale once this fix lands, including this task's own §8
   (`core_hr_sbs3_exposure_LR`/`ddr_signaling_sbs3_exposure_LR` recovery in
   `signatures.py`'s `phase6_gate6_recovery()`), which will need to be
   re-run against the corrected catalog once P06 lands the fix (out of
   scope for this prompt).

## What does NOT need to change

- `signatures.py`'s own §4-7 validation (the real-COSMIC-vector catalog it
  builds independently) is unaffected by this defect — it already uses real
  COSMIC SBS3/SBS5 weights and is not gate6-scored. Its separate finding
  (DIAGNOSIS_P08.md §5 — genuine NNLS decomposition instability at
  exome-scale counts) stands on its own and requires no simulator change.
- `SBS3_LINK`'s exposure-fraction parameters (see point 4 above).
- The trinucleotide exome/genome normalization factors and COSMIC-version
  pinning work (Task K, unaffected).

## Halt

Per this task's instruction: since the diagnosis for the gate6-blocking
mechanism points at the simulator, this session stops here on that branch.
`simulate.py` is not modified. P08 does not re-run against a fixed catalog
in this session; that requires P06 to land the fix above first.
