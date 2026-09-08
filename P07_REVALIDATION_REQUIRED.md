SIMULATED DATA — NOT A SCIENTIFIC RESULT

# P07_REVALIDATION_REQUIRED.md — does P06R2's fix invalidate P07's gate6 pass?

SIMULATED: this document answers, with evidence, whether `loh_caller.py`
(P07) needs to be re-run against the corrected simulator. Per this task's
explicit instruction, P07 is **not re-run from this prompt** regardless of
the answer below — this document only determines whether it must be.

## Answer: NO

P07's gate6 pass does not need to be re-run. Full reasoning follows.

## 1. P07's two recovery quantities

`loh_caller.py`'s `RECOVERY_SCOPE` (line 537) declares exactly two
quantities `in_scope: TRUE`:

- `core_hr_wt_lost_direction_LR`
- `ddr_signaling_wt_lost_direction_LR`

(the other 14 `SIMULATED_TRUTH.tsv` quantities — GIS/SBS3/joint/product/
NULL_ARM — are declared `NOT_IN_SCOPE`, unaffected either way since P07
never computes them.)

## 2. Do these two quantities depend on anything P06R2 changed?

`compute_truth_quantities()` derives `{arm}_wt_lost_direction_LR` as
`marginal_wt_lost_prob(arm, "Pathogenic") / marginal_wt_lost_prob(arm, "Benign")`,
and `marginal_wt_lost_prob()` reads only `WT_LOST_LINK[arm]` and
`Z_MEAN[arm][cls]` — **P06R2 touched neither.** `TRUTH_DELTA.md` §1 confirms
both values are bit-for-bit unchanged:

| quantity | BEFORE | AFTER |
|---|---|---|
| core_hr_wt_lost_direction_LR | 4.480411981797967 | 4.480411981797967 |
| ddr_signaling_wt_lost_direction_LR | 2.137348544853484 | 2.137348544853484 |

The injected TARGETS `loh_caller.py` was scored against in P07 are
identical.

## 3. Does `loh_caller.py`'s actual INPUT DATA depend on anything P06R2 changed?

`loh_caller.py` reads exactly four `SIMULATED_data`/`SIMULATED_TRUTH_detail`
files (grep-confirmed, not assumed):

- `SIMULATED_data/SIMULATED_baf_segments.tsv`
- `SIMULATED_data/SIMULATED_sample_metadata.tsv`
- `SIMULATED_TRUTH_detail/SIMULATED_sample_labels.tsv`
- `SIMULATED_data/SIMULATED_variant_calls.tsv`

It does **not** read `SIMULATED_data/SIMULATED_mutation_catalogs.tsv` — the
one file P06R2's fix actually changed. `TRUTH_DELTA.md` §2's before/after
file diff confirms all four of `loh_caller.py`'s actual input files are
**byte-identical** to what P07 ran against.

## 4. Conclusion

- Same injected targets (§2).
- Same input data, byte-for-byte (§3).
- `loh_caller.py`'s own code is unmodified (this task's explicit
  instruction, and confirmed: `git diff --name-only` shows no change to
  `loh_caller.py`).

A deterministic program given identical inputs and identical code produces
identical output. There is nothing for a re-run to discover that P07's
existing recorded run does not already show. **Re-running P07 would be
pure recomputation of an already-known-identical result, not a genuine
revalidation** — the honest answer is that no revalidation is required,
not merely that P07 "probably still passes."

This conclusion is scoped strictly to P06R2's actual change (the SBS3
catalog shape). It says nothing about whether a FUTURE change to
`WT_LOST_LINK`, `Z_MEAN`, or any of P07's four input-generating code paths
would invalidate P07 — such a change would require this same analysis
repeated against its own diff.
