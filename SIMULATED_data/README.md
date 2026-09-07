SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_data/ — what's in this directory

SIMULATED: every file in this directory is fabricated by `simulate.py`
with a fixed random seed, per PROTOCOL.md's SIMULATED regime (Standing
Rule 1). None of it is derived from real patient, tumor, or sequencing
data. No ACMG evidence strength is assigned to anything here.

**Why the `.tsv` files here don't each start with the banner line
literally:** `SIMULATED_TRUTH.tsv` (repo root, separate from this
directory) is read directly by `gates/gate6_recovery.py` via a plain
`csv.DictReader` with no comment-line support — prefixing its real
header row with a banner line would make every column resolve to the
wrong name and break that gate outright. The same plain-TSV convention
is used consistently for every other `.tsv` here, so a future consumer
can rely on "first line = real column headers" uniformly across this
repository (see every other `.tsv` already in this repo — none of them
carry an embedded banner line either). The banner requirement is instead
satisfied here, at the directory level, and in each file's companion
`.md` report (`SIMULATED_loh_injection_self_check.md`,
`SIMULATED_no_v1_reuse_check.md`) and in `SIMULATION_SPEC.md`.

| File | Contents |
|---|---|
| `SIMULATED_sample_metadata.tsv` | one row per simulated tumor/normal pair: gene, gene group, PAM50 subtype, purity, ploidy, WGD flag, normal depth |
| `SIMULATED_variant_calls.tsv` | one row per simulated germline variant: normal/tumor ref+alt read counts, allele-specific copy number, and the injected LOH category |
| `SIMULATED_mutation_catalogs.tsv` | one row per sample, 96 SBS-trinucleotide-context mutation counts |
| `SIMULATED_signature_exposures.tsv` | the true injected SBS3-like relative exposure and mutation-count breakdown per sample |
| `SIMULATED_loh_injection_self_check.md` | confirms the injected LOH categories are recoverable by re-running PROTOCOL.md §5.1/§5.2's own classification logic on the generated reads |
| `SIMULATED_no_v1_reuse_check.md` | the repo-wide scan for retracted v1 artifacts (parameter-independence check) |
