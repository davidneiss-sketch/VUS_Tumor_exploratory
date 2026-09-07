SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_TRUTH_detail/ — the per-sample answer key

SIMULATED: this directory holds the per-sample hidden ground-truth class
label (`true_class`: Pathogenic or Benign) that a real downstream
classifier would never see — the answer key, kept separate from both
`SIMULATED_data/` (the observable, pipeline-input-shaped files) and the
top-level `SIMULATED_TRUTH.tsv` (the aggregate, analytically-derived
likelihood-ratio ground truth for the 6 injected quantities defined in
SIMULATION_SPEC.md). `SIMULATED_sample_labels.tsv` keeps a real,
machine-parseable TSV header (see `SIMULATED_data/README.md` for why the
banner is not embedded as its literal first line); it is declared here
instead. No ACMG evidence strength is assigned to anything here.
