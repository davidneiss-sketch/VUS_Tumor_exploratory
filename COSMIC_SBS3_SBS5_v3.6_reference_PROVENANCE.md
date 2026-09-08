SIMULATED DATA — NOT A SCIENTIFIC RESULT

# COSMIC_SBS3_SBS5_v3.6_reference.tsv — provenance

SIMULATED: this file is real reference DATA (COSMIC v3.6 signature weight
vectors), used as an INPUT to the simulator below, not itself a simulated
output. No ACMG evidence strength is assigned to anything derived from it.

## Source

Extracted 2026-09-08 from the file `SigProfilerAssignment` reads at runtime
for `cosmic_version=3.6`, `genome_build='GRCh38'`:

```
/opt/conda/envs/bioenv/lib/python3.12/site-packages/SigProfilerAssignment/data/Reference_Signatures/GRCh38/COSMIC_v3.6_SBS_GRCh38.txt
```

inside docker image `vus-tumor-gate1:local`, digest
`sha256:2f344e8a456167eec8701db9581b07b0a4139ed2acdaecf23ab811fec354ca4c`
(the same digest `GATE1.json` pins for the SigProfilerAssignment 1.1.5
PASS entry). Not a live URL fetch — `cancer.sanger.ac.uk` remains
network-blocked in this environment (ENVIRONMENT.lock §0); this is the exact
file the real, installed, gate-verified tool itself reads at runtime, the
same evidentiary standard used throughout this task series (e.g. GATE1.json's
SigMA `DESCRIPTION`-file citation, Task K's `SIMULATED_cosmic_reference_extract.tsv`).

COSMIC version: **3.6**, PROTOCOL.md §5.4's pinned "version bundled
with/downloadable by this exact package build," confirmed live via
`inspect.signature(Analyzer.cosmic_fit).parameters['cosmic_version'].default`
in Task K.

## Columns

`Type` (96-context label, `{5'}[{substitution}]{3'}` format — verified to be
the exact same 96-label set as `simulate.py`'s own `SBS_CONTEXTS` list, by
direct set comparison, so no reordering/relabeling was needed), then raw
(un-normalized, sums to 1 already per COSMIC's own convention) weights for
`SBS3`, `SBS5`, `SBS39`, `SBS40a`, `SBS40b`, `SBS40c`.

`SBS3` and `SBS5` are the two vectors P06R2 uses to replace `simulate.py`'s
ARBITRARY `hrd_shape`/`background_shape` (see `REQUIRED_P06_CHANGES.md` and
`SIMULATION_SPEC.md`'s updated §0 addendum). `SBS39` and `SBS40a/b/c` are
included only for the cosine-similarity report P06R2's task requires (real
COSMIC signatures with a priori documented or empirically-observed confusion
risk with SBS3 — SBS39 was independently flagged in a live WebSearch during
Task K as HRD-associated in the literature; SBS40a/b/c were the closest real
match to the OLD arbitrary shape this fix replaces).

## Cosine similarities (computed from this file, real values)

| pair | cosine similarity |
|---|---|
| SBS3 vs SBS3 | 1.0 (identity) |
| SBS3 vs SBS5 | 0.7928 |
| SBS3 vs SBS39 | 0.7909 |
| SBS3 vs (SBS40a+SBS40b+SBS40c, summed) | 0.8498 |

These are intrinsic, fixed properties of the real COSMIC v3.6 signature set —
not estimated, not tunable, and (per this task's explicit instruction) not
adjusted to hit any target value. `simulate.py`'s new `hrd_shape` (:= this
file's `SBS3` column exactly) therefore carries the SAME real ~0.79 cosine
similarity to `background_shape` (:= this file's `SBS5` column exactly) as
real SBS3 does to real SBS5 in nature — this is the realistic property that
must survive the fix, not be engineered away.
