# DEPLOYMENT_LOG.md

Records that gates 2–7 — gate5 and gate6 in particular, per the task's
explicit "DEPLOY THE TRIPWIRES" requirement — were run against real,
on-disk **production** output files, by name, not only inside the test
suite's own throwaway fixtures. Every command below was actually executed
in this session; the captured output is real tool output, not a
transcription.

## What "production" means here

There is no real pipeline output to deploy against yet: `TRACK.md` limits
this project to Track A (no germline variant access), and
`GATE1.json`'s `gate1_result` is `FAIL` (SigMA not installed), so Stage 1
of `PROTOCOL.md` has not run and cannot produce real results. What *can*
run without real data is Stage 2 (synthetic recovery testing) — so
`production/` holds one deterministic, fully-labeled **SIMULATED**
instance of what a real pipeline's gate-input files look like, generated
by the checked-in `production/generate_production_run.py` (fixed inputs,
no randomness). This is the honest distinction the task draws between
"production outputs" and "test fixtures": these files are a durable,
named, on-disk deliverable that gate5/gate6 (and every other gate) treat
as real input on every invocation — not values constructed inline inside
a unit test and discarded. Standing Rule 1 applies in full to every file
under `production/`: every filename contains `SIMULATED`, and
`SIMULATED_RECOVERY_TABLE.md`'s first line is the mandated banner.

The production dataset is deliberately clean (all gates PASS) — proving
each gate *can* fail on bad input is the test suite's job
(`TRIPWIRE_EVIDENCE.md`), not this deployment log's.

## Production files scanned, by name

| File | Used by |
|---|---|
| `production/SIMULATED_raw_manifest.tsv`, `production/SIMULATED_provenance.tsv`, `production/SIMULATED_analyzed_samples.tsv`, `production/SIMULATED_raw/SIMULATED_SIM-S00{1..6}.rawtxt` | gate2 |
| `production/SIMULATED_phase_log.tsv` | gate3 |
| `production/SIMULATED_LR_TABLE.tsv` | gate4, gate5 |
| `production/SIMULATED_metrics.tsv`, `production/SIMULATED_thresholds.tsv`, `production/SIMULATED_circularity.tsv`, `production/SIMULATED_LR_TABLE.tsv` | **gate5** |
| `production/SIMULATED_TRUTH.tsv`, `production/SIMULATED_RECOVERED.tsv`, `production/SIMULATED_scope.tsv` → emits `production/SIMULATED_RECOVERY_TABLE.tsv` + `.md` | **gate6** |
| `production/SIMULATED_rates_table.tsv` | gate7 |

## Run log (real commands, real output, this session)

Generated the production dataset:

```
$ python3 production/generate_production_run.py
Generated production run files under /home/user/VUS_Tumor_exploratory/production
```

### gate2_data_reality.py — run 2026-09-07T18:20:25Z

```
$ python3 gates/gate2_data_reality.py \
    --manifest production/SIMULATED_raw_manifest.tsv \
    --provenance production/SIMULATED_provenance.tsv \
    --analyzed production/SIMULATED_analyzed_samples.tsv \
    --claimed-count 6

=== gate2_data_reality ===
[PASS] all required input files present — manifest=SIMULATED_raw_manifest.tsv, provenance=SIMULATED_provenance.tsv, analyzed=SIMULATED_analyzed_samples.tsv
[PASS] every raw file's on-disk size/md5/header matches its provenance record — 6 raw file(s) verified, 2145 total bytes read
[PASS] input volume consistent with claimed sample count — 6 raw manifest row(s) vs claimed_count=6
[PASS] every analyzed sample traces to a provenance row — 6 analyzed sample(s), all present in 6-row provenance table

gate2_data_reality OVERALL: PASS
EXIT_CODE=0
```

### gate3_runtime.py

**Updated 2026-09-07 (gate housekeeping task): `--track` is now required** —
see GATE3.json and GATE_HOUSEKEEPING.md. This repo's runs are all Track S
(TRACK.md: Track A only, no germline access, so no real Track B run has
ever happened here) — the command below reflects that explicitly rather
than relying on a since-removed default.

```
$ python3 gates/gate3_runtime.py --phase-log production/SIMULATED_phase_log.tsv --track TRACK_S

=== gate3_runtime ===
[PASS] phase log present — SIMULATED_phase_log.tsv, 5 phase(s), track=TRACK_S
[PASS] every phase has all required runtime fields recorded — all 5 phase(s) have command/exit_code/wall_clock/peak_rss/cpu_hours/bytes_read
[PASS] every phase exited 0 — all 5 phase(s) exited 0
[PASS] every phase's per-sample runtime exceeds its floor — all 5 phase(s) at/above floor (track=TRACK_S, floors: {'copy_number_calling': 5.0, 'hrd_scoring': 1.0, 'signature_assignment': 2.0, 'loh_binomial_test': 0.02, 'second_hit_scan': 0.05})
[PASS] no phase relies on an UNVERIFIED TRACK_S floor — every phase in this log has a verified floor for this track
gate3_runtime OVERALL: PASS
EXIT_CODE=0
```

### gate4_statistics.py

**Updated 2026-09-07 (gate housekeeping task): the expected replicate
count is now read live from PROTOCOL.md's own `B = <n>` text at run time**
(`--expected-replicates` was previously a hardcoded default of 2000 —
see GATE_HOUSEKEEPING.md for why that silently desynchronizes when the
protocol changes). No `--protocol` override needed below; it defaults to
the real repo `PROTOCOL.md`.

```
$ python3 gates/gate4_statistics.py --lr-table production/SIMULATED_LR_TABLE.tsv

=== gate4_statistics ===
[PASS] expected replicate count read from PROTOCOL.md — read B = 2000 from PROTOCOL.md
[PASS] LR table present — SIMULATED_LR_TABLE.tsv, 6 stratum row(s)
[PASS] every row's status is FITTED or INSUFFICIENT_N — all 6 row(s) have a valid status
[PASS] every fitted row carries n_pathogenic and n_benign (non-negative) — all 6 row(s) carry valid denominators
[PASS] every bootstrap CI contains its own point estimate — all 5 fitted row(s) OK
[PASS] replicate count matches protocol (B=2000, read live from PROTOCOL.md) — all 5 fitted row(s) OK
[PASS] CI widths vary across strata — 5 distinct CI width(s) across 5 fitted stratum/strata
gate4_statistics OVERALL: PASS
EXIT_CODE=0
```

### gate5_tripwires.py — **MANDATORY deploy-on-every-invocation gate**

```
$ python3 gates/gate5_tripwires.py \
    --metrics production/SIMULATED_metrics.tsv \
    --thresholds production/SIMULATED_thresholds.tsv \
    --circularity production/SIMULATED_circularity.tsv \
    --lr-table production/SIMULATED_LR_TABLE.tsv

=== gate5_tripwires ===
[PASS] all required input files present — metrics=SIMULATED_metrics.tsv, thresholds=SIMULATED_thresholds.tsv, circularity=SIMULATED_circularity.tsv, lr_table=SIMULATED_LR_TABLE.tsv
[PASS] no concordance/AUC-like metric exceeds ceiling (0.95) — no AUC/concordance metric exceeded the ceiling
[PASS] no control matches its cited benchmark within 1.0% — no suspiciously exact benchmark match
[PASS] every derived threshold's reported bias matches its recomputed bias — all 1 threshold row(s) self-consistent
[PASS] no gene group has a circularity-exclusion count of zero — all 2 gene-group row(s) have nonzero exclusions
[PASS] no negative-control CI is narrower than a comparable-n (±20.0%) positive-control CI — 1 negative-control / 1 positive-control row(s) compared, no violation
gate5_tripwires OVERALL: PASS
EXIT_CODE=0
```

### gate6_recovery.py — **NEW, MANDATORY deploy-on-every-invocation gate**

**Updated 2026-09-07 (gate housekeeping task): `--scope` is now required**
to avoid a silent "scored a subset, subset undeclared" scope bug (see
GATE_HOUSEKEEPING.md). `production/SIMULATED_scope.tsv` declares all 3 of
this production run's quantities `in_scope=TRUE` (all 3 are computed by
its own LR-fitting pipeline).

```
$ python3 gates/gate6_recovery.py \
    --truth production/SIMULATED_TRUTH.tsv \
    --recovered production/SIMULATED_RECOVERED.tsv \
    --scope production/SIMULATED_scope.tsv \
    --outdir production

core_hr_lumA_LR: estimand truth=LR, recovered=LR (MATCH)
[SIMULATED_PASS] core_hr_lumA_LR: injected=8.0, recovered=8.2, CI=[3.1, 19.5], relative_bias=0.0250
ddr_signaling_lumA_LR: estimand truth=LR, recovered=LR (MATCH)
[SIMULATED_PASS] ddr_signaling_lumA_LR: injected=1.0, recovered=1.05, CI=[0.55, 1.95], relative_bias=0.0500
core_hr_basal_LR: estimand truth=LR, recovered=LR (MATCH)
[SIMULATED_PASS] core_hr_basal_LR: injected=15.0, recovered=15.6, CI=[6.0, 42.0], relative_bias=0.0400
=== gate6_recovery ===
[PASS] truth and recovered files present — truth=SIMULATED_TRUTH.tsv (3 quantities), recovered=SIMULATED_RECOVERED.tsv (3 rows)
[PASS] SIMULATED_RECOVERY_TABLE.tsv and .md emitted — production/SIMULATED_RECOVERY_TABLE.tsv (3 rows), production/SIMULATED_RECOVERY_TABLE.md
[PASS] every truth quantity has a declared scope (no UNDECLARED quantities) — every quantity has a scope declaration
[PASS] every quantity is SIMULATED_PASS or declared out of scope (any single FAIL halts the pipeline) — all quantities passed or were declared out of scope
gate6_recovery OVERALL: PASS
EXIT_CODE=0
```

Emitted artifacts (real files on disk after this run):
`production/SIMULATED_RECOVERY_TABLE.tsv`, `production/SIMULATED_RECOVERY_TABLE.md`.

### gate7_denominators.py

```
$ python3 gates/gate7_denominators.py --rates-table production/SIMULATED_rates_table.tsv

=== gate7_denominators ===
[PASS] rates table present — SIMULATED_rates_table.tsv, 3 metric row(s)
[PASS] every row has a positive denominator — all 3 row(s) have a positive denominator
[PASS] every row has an explicit (non-blank) excluded_count — all 3 row(s) carry an explicit excluded_count
[PASS] numerator never exceeds denominator — all 3 row(s) OK
[PASS] reported rate (if present) matches numerator/denominator — all reported rates internally consistent
gate7_denominators OVERALL: PASS
EXIT_CODE=0
```

## Summary

All 6 gates: **PASS**, run against the named production files above, this
session, 2026-09-07. This log is the record required by the task's
deploy clause: "Record, per run, that each gate was evaluated against the
real output files by name." Every future pipeline invocation must append
a new dated entry here (or an equivalent structured log) naming the exact
production files gate5 and gate6 were run against for that invocation —
a tripwire gate whose only evidence of running is its own unit test is,
per the task, not deployed.

## Invocation 2 — direction-aware LOH caller (`loh_caller.py`), 2026-09-07T22:08:14Z

A new production component (`loh_caller.py`, its own task) ran gate6 and
gate7 against its own real, on-disk output files — not the fixtures
above, and not the `production/` directory's earlier fixture set.

| File | Used by |
|---|---|
| `SIMULATED_TRUTH.tsv` (repo root — the real simulator ground truth, 6 quantities), `SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv` (2 quantities this caller recovers), `SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv` (scope declaration for all 6) → emits `SIMULATED_RECOVERY_TABLE.tsv` + `.md` (repo root) | **gate6** |
| `SIMULATED_loh_validation/SIMULATED_rates_table.tsv` | gate7 |

**Updated 2026-09-07T22:32:43Z (gate housekeeping task): `--scope` is now
required.** The 4 quantities this caller doesn't compute are now declared
`NOT_IN_SCOPE` (reported as `BLOCKED`, not a fabricated `SIMULATED_FAIL`)
instead of silently reading as "no recovered value found" with no scope
statement — see GATE_HOUSEKEEPING.md.

```
$ python3 gates/gate6_recovery.py --truth SIMULATED_TRUTH.tsv \
    --recovered SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv \
    --scope SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv --outdir .

core_hr_loh_second_hit_LR: estimand truth=LR, recovered=LR (MATCH)
[SIMULATED_FAIL] core_hr_loh_second_hit_LR: injected=6.999999999999999, recovered=4.6, CI=[1.9090909090909092, 25.0], relative_bias=0.3429 — relative bias 0.3429 exceeds tolerance 0.25
ddr_signaling_loh_second_hit_LR: estimand truth=LR, recovered=LR (MATCH)
[SIMULATED_FAIL] ddr_signaling_loh_second_hit_LR: injected=2.666666666666667, recovered=3.6666666666666665, CI=[1.0, 17.0], relative_bias=0.3750 — relative bias 0.3750 exceeds tolerance 0.25
[BLOCKED] core_hr_gis_score_LR: declared NOT_IN_SCOPE -- requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute
[BLOCKED] ddr_signaling_gis_score_LR: declared NOT_IN_SCOPE -- requires an HRD/GIS-score feature (scarHRD) this LOH caller does not compute
[BLOCKED] core_hr_sbs3_exposure_LR: declared NOT_IN_SCOPE -- requires a SigProfilerAssignment SBS3-exposure feature this LOH caller does not compute
[BLOCKED] null_sequencing_depth_bucket_LR: declared NOT_IN_SCOPE -- an engineered-null depth-bucket feature unrelated to LOH direction; not this caller's estimand
=== gate6_recovery ===
[PASS] truth and recovered files present — truth=SIMULATED_TRUTH.tsv (6 quantities), recovered=SIMULATED_recovered_quantities.tsv (2 rows)
[PASS] SIMULATED_RECOVERY_TABLE.tsv and .md emitted — SIMULATED_RECOVERY_TABLE.tsv (6 rows), SIMULATED_RECOVERY_TABLE.md
[PASS] every truth quantity has a declared scope (no UNDECLARED quantities) — every quantity has a scope declaration
[FAIL] every quantity is SIMULATED_PASS or declared out of scope (any single FAIL halts the pipeline) — at least one quantity is SIMULATED_FAIL — see SIMULATED_RECOVERY_TABLE.tsv for detail
gate6_recovery OVERALL: FAIL
EXIT_CODE=1
```

**This FAIL is genuine and expected, reported per Standing Rule 2, not spun.**
Of the 6 `SIMULATED_TRUTH.tsv` quantities: 4 (both GIS/HRD-score quantities,
the SBS3-exposure quantity, the engineered null) are out of scope for an
LOH caller — it never fabricated a recovered value for them, so gate6
correctly reports "no recovered value found" for each. The 2 in-scope
LOH-direction quantities (`core_hr_loh_second_hit_LR`,
`ddr_signaling_loh_second_hit_LR`) are a real, uncontrived test: both
CIs contain their injected target, but both relative-bias values
(0.3429, 0.3750) exceed PROTOCOL.md §11's 0.25 tolerance —
**`SIMULATED_FAIL`**, not tuned to pass. Full breakdown, root-cause
investigation, and the confusion matrix / stratified accuracy this
caller was scored on: `SIMULATED_loh_validation.md`.

```
$ python3 gates/gate7_denominators.py --rates-table SIMULATED_loh_validation/SIMULATED_rates_table.tsv

=== gate7_denominators ===
[PASS] rates table present — SIMULATED_rates_table.tsv, 14 metric row(s)
[PASS] every row has a positive denominator — all 14 row(s) have a positive denominator
[PASS] every row has an explicit (non-blank) excluded_count — all 14 row(s) carry an explicit excluded_count
[PASS] numerator never exceeds denominator — all 14 row(s) OK
[PASS] reported rate (if present) matches numerator/denominator — all reported rates internally consistent
gate7_denominators OVERALL: PASS
EXIT_CODE=0
```

## Invocation 3 — gate8_interval_informativeness.py, NEW MANDATORY gate, run against real production output alongside gate5/gate6

`gate8_interval_informativeness.py` (P-DEC-1 task: an ACMG-mapping rule
that only checks which side of a threshold a CI's lower bound falls on
will assign a strength to ANY interval, however wide or numerically
degenerate — see the gate's own docstring and `INTERVAL_INSTABILITY.md`
for the full rationale and the two pre-specified, cited thresholds). Run
here against `ABLATION_TABLE.tsv` — the real, on-disk, already-committed
production output that contains the row this gate exists to catch
(`STAKE_ANALYSIS.md`'s DDR_SIGNALING n=35 full-feature-set row, CI upper
bound 3.65 billion) — not only against `tests/fixtures/gate8_*`.

| File | Used by |
|---|---|
| `ABLATION_TABLE.tsv` (repo root) → emits `SIMULATED_GATE8_INTERVAL_REPORT.tsv` (repo root) | **gate8** |

```
$ python3 gates/gate8_interval_informativeness.py \
    --table ABLATION_TABLE.tsv \
    --id-cols arm,feature_subset,n_scenario \
    --point-col point_estimate --ci-low-col ci_low --ci-high-col ci_high \
    --outdir .

=== gate8_interval_informativeness ===
[PASS] input table present — ABLATION_TABLE.tsv (64 rows)
[PASS] SIMULATED_GATE8_INTERVAL_REPORT.tsv emitted — SIMULATED_GATE8_INTERVAL_REPORT.tsv (64 rows: 46 INFORMATIVE, 10 UNINFORMATIVE, 8 NOT_APPLICABLE)
[FAIL] every row with a computable interval is INFORMATIVE — 10 row(s) UNINFORMATIVE — see SIMULATED_GATE8_INTERVAL_REPORT.tsv for detail
gate8_interval_informativeness OVERALL: FAIL
EXIT_CODE=1
```

**This FAIL is genuine and expected, reported per Standing Rule 2, not
spun.** All 10 `UNINFORMATIVE` rows are `REALISTIC_N_*` rows — exactly the
class-size regime `STAKE_ANALYSIS.md` Step 2 already flagged as producing
estimator instability, now caught by a script rather than left to manual
inspection. The flagged row itself
(`DDR_SIGNALING/LOH_GIS_SBS3/REALISTIC_N_35`, CI=[759.6, 3.65e9]) is
confirmed present and rejected, with both violated thresholds named in its
`reason` field (`upper_point_ratio` ≈330901, and the interval's upper
bound exceeds `ABSOLUTE_UPPER_CEILING`). The 46 `INFORMATIVE` rows include
every `SYNTHETIC_FULL_N` row and most subtype-stratified rows, confirming
gate8 does not indiscriminately fail a whole table once one row is bad —
it evaluates each row independently, exactly as designed and unit-tested
(`tests/test_gate8.py`). Emitted artifact:
`SIMULATED_GATE8_INTERVAL_REPORT.tsv` (repo root).

Per the task's deploy clause (see "Summary" above): gate8 is now part of
the standard invocation set alongside gate5 and gate6, and this entry is
the record of it running against real, on-disk production output, by file
name, this session.
