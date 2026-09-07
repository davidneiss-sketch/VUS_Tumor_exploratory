# TRIPWIRE_EVIDENCE.md

For every check in gate2–gate7, this records the constructed bad-input
fixture that deliberately trips it, the exact command run, and the real
captured output proving it fired (exit code 1, plus the specific
`[FAIL]` line). All fixtures live under `tests/fixtures/`; all tests
under `tests/test_gate*.py` assert on this exact output. This file's
evidence blocks are the real stdout of the commands shown — not a
description of expected behavior.

Full test suite (`python3 tests/run_all_tests.py`): **17 tests, 17 passed**
— every gate has at least one passing-fixture test and at least one
failing-fixture test, per the task's acceptance criterion.

---

## gate2_data_reality.py

Fixture: `tests/fixtures/gate2_bad/` — manifest records a wrong md5 for
the (real, on-disk) raw file, and `analyzed.tsv` lists a sample
(`SAMPLE_GHOST`) with no provenance row.

```
$ python3 gates/gate2_data_reality.py \
    --manifest tests/fixtures/gate2_bad/manifest.tsv \
    --provenance tests/fixtures/gate2_bad/provenance.tsv \
    --analyzed tests/fixtures/gate2_bad/analyzed.tsv \
    --claimed-count 1

[FAIL] every raw file's on-disk size/md5/header matches its provenance record — SAMPLE_B: md5 re-verified via on-disk-re-hash-vs-provenance-record = 4199cce3e9600134155536fe3e20396e != recorded deadbeefdeadbeefdeadbeefdeadbeef
[FAIL] every analyzed sample traces to a provenance row — untraced sample_id(s): ['SAMPLE_GHOST']

gate2_data_reality OVERALL: FAIL
EXIT=1
```

Both deliberately-broken conditions fired; the file-presence and
sample-count checks correctly stayed PASS since only those two fields
were sabotaged.

---

## gate3_runtime.py

Fixture: `tests/fixtures/gate3_bad/phase_log.tsv` — one phase with
`exit_code=1`, one phase whose wall-clock time is far below its
per-sample floor.

```
$ python3 gates/gate3_runtime.py --phase-log tests/fixtures/gate3_bad/phase_log.tsv

[FAIL] every phase exited 0 — copy_number_calling: exit_code=1 (command: SIMULATED: test cmd that crashed)
[FAIL] every phase's per-sample runtime exceeds its floor — hrd_scoring: 0.1000 sec/sample < floor 1.0 sec/sample (wall_clock=1.0s, n_samples=10)

gate3_runtime OVERALL: FAIL
EXIT=1
```

This is the gate that mechanically enforces Standing Rule 4 ("Nonzero
exit is failure even if a file appeared") for the pipeline's own phases.

---

## gate4_statistics.py

**Exact ACCEPTANCE criterion: "gate4 rejects a table with a CI excluding
its estimate."**

Fixture: `tests/fixtures/gate4_bad/lr_table.tsv` — `point_estimate=10.0`
but `ci_low=12.0, ci_high=20.0` (the point estimate is below the interval
entirely).

```
$ python3 gates/gate4_statistics.py --lr-table tests/fixtures/gate4_bad/lr_table.tsv

[FAIL] every bootstrap CI contains its own point estimate — STRATUM_BAD: CI [12.0, 20.0] does not contain point estimate 10.0

gate4_statistics OVERALL: FAIL
EXIT=1
```

---

## gate5_tripwires.py

**Exact ACCEPTANCE criteria: "gate5 flags an AUC of 0.998 and an exact
benchmark match."** All five tripwires are exercised together in one
fixture set (`tests/fixtures/gate5_bad/`); each is also asserted
individually in `tests/test_gate5.py`.

```
$ python3 gates/gate5_tripwires.py \
    --metrics tests/fixtures/gate5_bad/metrics.tsv \
    --thresholds tests/fixtures/gate5_bad/thresholds.tsv \
    --circularity tests/fixtures/gate5_bad/circularity.tsv \
    --lr-table tests/fixtures/gate5_bad/lr_table.tsv

[FAIL] no concordance/AUC-like metric exceeds ceiling (0.95) — auc_test=0.998 > ceiling 0.95
[FAIL] no control matches its cited benchmark within 1.0% — exact_match_metric: value=0.5 vs benchmark=0.5 (source=test benchmark exact match) — 0.000% apart, <= 1.0% ceiling
[FAIL] every derived threshold's reported bias matches its recomputed bias — inconsistent_threshold: recomputed bias 19.048% vs reported bias 1.0% (disagree by more than 1.0pp)
[FAIL] no gene group has a circularity-exclusion count of zero — CORE_HR: circularity exclusion count is 0
[FAIL] no negative-control CI is narrower than a comparable-n (±20.0%) positive-control CI — NEG1 (n=40, width=0.100) narrower than POS1 (n=41, width=16.000) at comparable n

gate5_tripwires OVERALL: FAIL
EXIT=1
```

All five tripwires fired in a single run against this one deliberately-bad
fixture set — tripwire 1 (0.998 > 0.95 ceiling) and tripwire 2 (0.5 vs
0.5, 0.000% apart) are the two literally named in the ACCEPTANCE section.

---

## gate6_recovery.py

**Exact ACCEPTANCE criteria: "gate6 rejects a recovered CI of [7.47,
11.25] against an injected 4.5, and rejects an OR-vs-LR comparison."**
Two separate fixtures, one per criterion.

### CI-exclusion case — `tests/fixtures/gate6_bad_ci/`

```
$ python3 gates/gate6_recovery.py \
    --truth tests/fixtures/gate6_bad_ci/truth.tsv \
    --recovered tests/fixtures/gate6_bad_ci/recovered.tsv \
    --outdir /tmp/tripwire_evidence/gate6_bad_ci_out

BAD_CI_QUANTITY: estimand truth=LR, recovered=LR (MATCH)
[SIMULATED_FAIL] BAD_CI_QUANTITY: injected=4.5, recovered=9.3, CI=[7.47, 11.25], relative_bias=1.0667 — CI [7.47, 11.25] does not contain injected value 4.5 — FAILED per Standing Rule 2; relative bias 1.0667 exceeds tolerance 0.25

[FAIL] every quantity is SIMULATED_PASS (any single FAIL halts the pipeline) — at least one quantity is SIMULATED_FAIL — see SIMULATED_RECOVERY_TABLE.tsv for detail

gate6_recovery OVERALL: FAIL
EXIT=1
```

The recovered CI `[7.47, 11.25]` does not contain the injected `4.5` —
rejected exactly as required, reported as `SIMULATED_FAIL` (never
"approximately recovered"), and the relative-bias tolerance breach
(106.7% > 25%) is reported alongside as a second, independent reason.

### Estimand-mismatch case — `tests/fixtures/gate6_bad_estimand/`

```
$ python3 gates/gate6_recovery.py \
    --truth tests/fixtures/gate6_bad_estimand/truth.tsv \
    --recovered tests/fixtures/gate6_bad_estimand/recovered.tsv \
    --outdir /tmp/tripwire_evidence/gate6_bad_estimand_out

BAD_ESTIMAND_QUANTITY: estimand truth=LR, recovered=OR (MISMATCH — AUTOMATIC FAIL)
[SIMULATED_FAIL] BAD_ESTIMAND_QUANTITY: injected=5.0, recovered=5.1, CI=[3.0, 8.0], relative_bias=0.0200 — estimand mismatch: truth=LR, recovered=OR — comparing these is invalid regardless of CI overlap (AUTOMATIC FAIL)

gate6_recovery OVERALL: FAIL
EXIT=1
```

Note the CI `[3.0, 8.0]` *does* contain the injected `5.0`, and the
relative bias (2%) is well within tolerance — this quantity fails
**solely** because the recovered value is reported on an OR scale while
the injected target is an LR, which the gate treats as an automatic
failure regardless of numeric overlap, exactly as PROTOCOL.md §6 (the
estimand declaration) requires.

---

## gate7_denominators.py

**Acceptance-adjacent criterion: "A reported accuracy with no
AMBIGUOUS/excluded count is FAIL."**

Fixture: `tests/fixtures/gate7_bad/rates_table.tsv` — a row with a blank
`excluded_count`.

```
$ python3 gates/gate7_denominators.py --rates-table tests/fixtures/gate7_bad/rates_table.tsv

[FAIL] every row has an explicit (non-blank) excluded_count — accuracy_no_denominator_disclosure: excluded_count is missing/blank/NA — not an acceptable result

gate7_denominators OVERALL: FAIL
EXIT=1
```

---

## Bugs this test suite itself caught (disclosed, not swept under the rug)

Writing these tests surfaced two real bugs in the gate scripts before
this deliverable was finalized, both fixed and re-verified (Standing
Rule 4 — logged here rather than silently corrected):

1. **gate7_denominators.py** crashed with an unhandled `AttributeError`
   on a real short/malformed input row (a trailing column absent rather
   than merely blank), because `row.get("rate", "").strip()` returns
   `None` — not the given default — when `csv.DictReader` pads a short
   row with `None` for a present-but-empty trailing column. Fixed to
   `(row.get("rate") or "").strip()`. The same fragile pattern was found
   and fixed the same way in `gate2_data_reality.py` (2 call sites) and
   `gate6_recovery.py` (1 call site) and `gate5_tripwires.py` (1 call
   site) before they were exercised by a similarly-shaped bad row.
2. A malformed TSV fixture (`tests/fixtures/gate4_good/lr_table.tsv`)
   initially had too few tab-separated fields on its `INSUFFICIENT_N`
   row, which shifted every later column left by two — caught
   immediately by `test_gate4.TestGate4Statistics.test_good_fixture_passes`
   failing when it should have passed. This was a fixture-authoring bug,
   not a gate-script bug; the fixture was corrected and the fix verified.
