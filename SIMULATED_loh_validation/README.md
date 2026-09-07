SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SIMULATED_loh_validation/ — direction-aware LOH caller outputs

SIMULATED: every file in this directory is produced by `loh_caller.py`
running against the SIMULATED tumor/normal data under `SIMULATED_data/`
(itself produced by `simulate.py`, a prior task in this session). None of
it is derived from real patient, tumor, or sequencing data. No ACMG
evidence strength is assigned to anything here.

**Why the `.tsv` files here don't each start with the banner line
literally:** the same convention already established for
`SIMULATED_data/` and `SIMULATED_TRUTH.tsv` — `SIMULATED_recovered_quantities.tsv`
is read directly by `gates/gate6_recovery.py` via a plain `csv.DictReader`
with no comment-line support, so a banner line would break that gate.
Every other `.tsv` here keeps the same plain-header convention for
uniformity. The banner requirement is instead satisfied at the directory
level (here) and in the top-level `SIMULATED_loh_validation.md` report.

| File | Contents |
|---|---|
| `SIMULATED_loh_calls.tsv` | one row per variant call: predicted direction-aware category, confidence (posterior on the winning hypothesis), all 3 hypothesis posteriors, true (mapped) category, purity/depth/copy-number context, and a correctness flag |
| `SIMULATED_confusion_matrix.tsv` | true-category x predicted-category counts, long format |
| `SIMULATED_rates_table.tsv` | every reported accuracy/rate with its numerator, denominator, and excluded_count (gate7's input; Standing Rule 5) |
| `SIMULATED_recovered_quantities.tsv` | the 2 of 6 `SIMULATED_TRUTH.tsv` quantities this caller can recover (the LOH-direction LRs), with patient-clustered bootstrap 95% CIs (gate6's input) |
