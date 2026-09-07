SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_TRUTH_detail/ — the per-sample answer key

SIMULATED: this directory holds the per-sample hidden ground truth that a
real downstream classifier would never see — `true_class` (Pathogenic or
Benign), and, as of v2, the sample's own drawn `z_latent` (the shared
HR-deficiency latent variable, see SIMULATION_SPEC.md §3) and
`hidden_direction` (the true WT_LOST/NOT_WT_LOST direction, including for
`AMBIGUOUS` samples where the single at-risk variant's own reads are
deliberately underpowered to recover it directly, per SIMULATION_SPEC.md
§4.1). Kept separate from both `SIMULATED_data/` (the observable,
pipeline-input-shaped files) and the top-level `SIMULATED_TRUTH.tsv` (the
aggregate, analytically-derived likelihood-ratio ground truth for the 16
injected quantities defined in SIMULATION_SPEC.md). `SIMULATED_sample_labels.tsv`
keeps a real, machine-parseable TSV header (see `SIMULATED_data/README.md`
for why the banner is not embedded as its literal first line); it is
declared here instead. No ACMG evidence strength is assigned to anything
here.
