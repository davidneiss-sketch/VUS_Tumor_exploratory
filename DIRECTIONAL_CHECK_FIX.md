SIMULATED DATA — NOT A SCIENTIFIC RESULT

# DIRECTIONAL_CHECK_FIX.md — repairing the zero-bias miscalibration in `gates/gate6_recovery.py`'s directional shrinkage-bias check

**Status: gate code change APPLIED to `gates/gate6_recovery.py` (permitted
this task). PROTOCOL.md §11 clarification text is DRAFTED below and
flagged for human sign-off — NOT applied to PROTOCOL.md, per Standing
Rule 10.**

## 1. The miscalibration

`PROPOSED_GATE6_AMENDMENT.md` / `PROTOCOL_DEVIATIONS.md` Entry 3 (applied
in P-AMD-3b) added a directional shrinkage-bias check to
`gates/gate6_recovery.py`'s Stage 2 criterion, for a specific estimator:
an L2-penalized logistic regression whose CV-selected penalty produces a
**known, nonzero, characterized shrinkage bias** (`logistic_estimator.py`
/ `CONSERVATIVE_ASSIGNMENT_ANALYSIS.md`). The check, as implemented in
`directional_check()`, does two things once a `predicted_relative_bias_magnitude`
has been declared for a quantity:

1. Reject immediately if the observed bias has the wrong sign relative to
   the predicted shrinkage direction.
2. Reject if the observed bias magnitude exceeds
   `predicted_magnitude * MAGNITUDE_SLACK_FACTOR` (1.5x), a real
   tolerance band built around a genuinely nonzero prediction.

P07-RERUN2 (`9135963`) applied this same mechanism to the LOH caller —
an estimator that is **not** a penalized/shrinkage estimator and has no
systematic-bias mechanism of that kind. Its `SIMULATED_BIAS_PREDICTION.tsv`
declared, honestly, the only systematic (non-sampling) effect this
caller's point estimate has: the Jeffreys +0.5/+1 continuity correction
used to keep `wt_lost_direction_LR` finite at small cell counts. Those
magnitudes are tiny (0.06%–11.9% by stratum, see §3) because the
continuity correction genuinely is tiny relative to the point estimate at
these stratum sizes.

The bug: feeding that tiny-but-nonzero number through the existing
1.5x-slack magnitude test treats it as though it were the estimator's
**entire** tolerance for deviation from truth — including ordinary
sampling noise, which at these stratum sizes (n as low as 27/36 for
Normal-like) is far larger than 0.06%–11.9%. `1.5 * 0.001037 ≈ 0.0016`,
a tolerance band of about one sixth of one percent, when the CIs
routinely span 15–30% of the point estimate. The check was answering "is
the observed bias consistent with the *declared shrinkage mechanism*
alone?" when the honest question for a non-penalized estimator is "is
the observed deviation consistent with **zero** systematic bias, allowing
for the sampling noise this stratum actually has?" Those are different
questions, and the P07-RERUN2 run asked the first one of an estimator for
which the correct prediction is functionally the second. That produced
11 of 12 strata FAILing the directional check — not eleven findings
about the LOH caller, but one miscalibration in the check, exactly as
this task states.

P08 supplies the same kind of prediction (a real but small systematic
correction against an estimator with no shrinkage mechanism, evaluated
at finite-n strata) and would hit the identical wall unfixed.

## 2. The fix

Preserves `directional_check()` **completely unmodified** — no line in
that function changed. Adds a **parallel path** for a genuinely
zero-valued `predicted_relative_bias_magnitude`, dispatched in `main()`
before scoring:

- `predicted_magnitude == 0.0` → `zero_bias_check()` (new)
- `predicted_magnitude != 0.0` → `directional_check()` (unchanged)

### `zero_bias_check()`

A zero-bias prediction states "no systematic mechanism predicts a
directional bias here" — under that null hypothesis there is no
predicted *sign* to violate, only a magnitude of deviation that ordinary
sampling noise could plausibly produce. So:

- **No sign check** (there is no predicted direction).
- **Noise allowance** = `se_multiplier x SE`, where `SE` is estimated
  from the quantity's own reported 95% bootstrap CI via the standard
  normal approximation:

  `SE ≈ (ci_high − ci_low) / (2 x 1.959964)`

  (`estimate_se_from_ci()`). This scales correctly with n automatically
  — a small stratum has a wide CI, a large SE, and a proportionately
  larger noise allowance — with no per-quantity tuning, exactly as this
  task specifies.
- **PASS** iff `|recovered − injected| ≤ se_multiplier x SE`.
- `se_multiplier` comes from the new optional `noise_allowance_se_multiples`
  column in the `--bias-prediction` TSV (falls back to the module
  constant `ZERO_BIAS_NOISE_ALLOWANCE_SE_MULTIPLIER` when blank/absent).

### Multiplier: 3.0 standard errors

**Chosen value: `ZERO_BIAS_NOISE_ALLOWANCE_SE_MULTIPLIER = 3.0`.**

Justification (computed, not asserted — `two_sided_false_failure_rate()`
in `gates/gate6_recovery.py`, implemented via `math.erf`, since this
codebase has no scipy/numpy):

```
two_sided_false_failure_rate(k) = 2 * (1 - Φ(k))
```

where `Φ` is the standard normal CDF. This is the probability that, under
a **true** zero systematic bias, a single quantity's observed deviation
falls outside `±k` SE purely from sampling noise — i.e. the false-failure
(false-alarm) rate this check would produce on a correctly-specified
zero-bias null.

Computed values (`k`, per-quantity false-failure rate, family-wise rate
across P07-RERUN2's 12 simultaneously-tested quantities via
`family_wise_false_failure_rate(p, 12) = 1 − (1 − p)^12`):

| k (SE multiples) | per-quantity false-failure rate | family-wise rate (n=12) |
|---|---|---|
| 1.0 | 31.73% | 98.98% |
| 1.5 | 13.36% | 82.11% |
| 2.0 | 4.55% | 42.81% |
| 2.5 | 1.24% | 13.93% |
| **3.0 (chosen)** | **0.27%** | **3.19%** |

At `k=3.0`: a single correctly-null quantity has a **0.270%** chance of
spuriously failing this check on sampling noise alone; across 12
simultaneously-scored quantities (P07-RERUN2's in-scope set) the
probability that **at least one** spuriously fails is **3.19%**.

This is a deliberate choice to favor a low false-alarm rate over
sensitivity to small deviations, and it is safe to do so because a real
systematic bias that happens to be smaller than 3 SE (and would therefore
not be caught by this check) is still independently exposed by the
unchanged **0.25 relative-bias tolerance** (§11 criterion 1, unaffected
by this fix) — the zero-bias check does not need to be the only
safeguard, it only needs to stop the specific failure mode this task
identifies (spurious rejection of a correctly-specified zero-bias
estimator from ordinary noise). A smaller multiplier (e.g. 1.5x, matching
`MAGNITUDE_SLACK_FACTOR`'s nonzero-case value) was considered and
rejected: at 1.5 SE the family-wise false-failure rate across 12
quantities is 82%, i.e. this check would almost certainly flag some
quantity on every run regardless of whether the estimator is actually
unbiased — precisely the miscalibration this fix exists to remove, just
moved to a different threshold instead of eliminated.

### Nonzero-prediction path: unchanged, verified unchanged

`directional_check()` was not edited. The HALT condition for this task —
"if the repaired directional check causes gate6_bad_ci to pass, or
weakens the nonzero-prediction path" — is verified false:

- `tests/fixtures/gate6_bad_ci/` (no bias-prediction declared at all,
  recovers 9.3 against injected 4.5) → still `test_bad_ci_fixture_rejects_ci_7_47_to_11_25_against_injected_4_5`
  and `test_amended_criterion_fails_bad_ci_fixture_on_relative_bias_not_containment`
  **PASS** (i.e. the fixture is still correctly rejected — see §4).
- The wrong-sign nonzero fixture (`predicted_relative_bias_magnitude=0.15`,
  nonzero, wrong-sign observed) → `test_wrong_sign_bias_fixture_fails_directional_check_within_tolerance`
  still **PASS** (fixture still correctly FAILs gate6).
- The correct-sign-within-slack nonzero fixture → `test_correct_sign_within_slack_bias_fixture_passes`
  still **PASS**.

Neither fixture's magnitude is zero, so neither was ever at risk of being
routed to the new code path — confirmed empirically, not just by
inspection.

## 3. Fixtures and test results

Four fixtures, four outcomes, all as specified:

| Fixture | `predicted_relative_bias_magnitude` | Design | Result |
|---|---|---|---|
| `tests/fixtures/gate6_zero_bias_within_allowance/` | 0 | injected=5.0, recovered=5.3, CI=[4.5,6.1] → SE≈0.408, allowance(3x)≈1.224, deviation=0.3 < allowance | **PASS** (as specified) |
| `tests/fixtures/gate6_zero_bias_exceeds_allowance/` | 0 | injected=5.0, recovered=6.0, CI=[5.7,6.3] (tight) → SE≈0.153, allowance(3x)≈0.459, deviation=1.0 > allowance; relative_bias=0.20, within the raw 0.25 tolerance, isolating the zero-bias check as sole cause | **FAIL** (as specified) |
| wrong-sign nonzero fixture (pre-existing) | 0.15 | wrong sign vs. predicted shrinkage direction | **FAIL, unchanged** |
| `tests/fixtures/gate6_bad_ci/` | (none declared) | recovers 9.3 vs injected 4.5 | **FAIL, unchanged** |

`tests/test_gate6.py` — full suite run (`python3 -m unittest test_gate6 -v`
from `tests/`): **10/10 PASS**, including the 2 new tests
(`test_zero_bias_prediction_within_noise_allowance_passes`,
`test_zero_bias_prediction_exceeding_noise_allowance_fails`) and all 8
pre-existing tests unchanged.

## 4. Re-scoring P07-RERUN2's 12 in-scope quantities under the repaired check

Per this task's explicit instruction, the LOH caller was **not re-run**.
The existing, committed P07-RERUN2 output
(`SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv`,
`SIMULATED_recovery_scope.tsv`, both unchanged) was re-scored against a
new bias-prediction file,
`SIMULATED_loh_validation/SIMULATED_BIAS_PREDICTION_REPAIRED.tsv`, which
declares `predicted_relative_bias_magnitude=0` (correctly: this caller's
only non-sampling deviation source, the Jeffreys continuity correction,
is negligible relative to its sampling noise at every in-scope stratum —
see §1) with `noise_allowance_se_multiples=3.0`, sourced with the
reasoning above rather than treated as a magnitude-scale tolerance band.
The original `SIMULATED_BIAS_PREDICTION.tsv` from P07-RERUN2 is left
untouched as the historical record of what was actually run at the time.

Invocation (via `scripts/run_with_integrity_checks.py`, writing to a new
directory so the P07-RERUN2-committed `SIMULATED_loh_validation/` outputs
are not overwritten):

```
$ python3 scripts/run_with_integrity_checks.py \
    --expect-changed "SIMULATED_loh_validation/gate6_directional_check_fix_rescoring/*" -- \
    python3 gates/gate6_recovery.py --truth SIMULATED_TRUTH.tsv \
      --recovered SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv \
      --scope SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv \
      --bias-prediction SIMULATED_loh_validation/SIMULATED_BIAS_PREDICTION_REPAIRED.tsv \
      --outdir SIMULATED_loh_validation/gate6_directional_check_fix_rescoring
```

`artifact_checksum_check verify`: 0 unexpected changes (PASS).

### Before (P07-RERUN2, miscalibrated check, `9135963`)

**1 of 12** in-scope quantities SIMULATED_PASS
(`ddr_signaling_normal_like_wt_lost_direction_LR` only). 11 FAIL the
directional check; of those, `core_hr_normal_like_wt_lost_direction_LR`
also independently fails the raw 0.25 relative-bias tolerance.

### After (repaired check, this task)

**10 of 12** in-scope quantities SIMULATED_PASS. 2 FAIL:

| Quantity | Failure mode | Detail |
|---|---|---|
| `core_hr_luma_wt_lost_direction_LR` | zero-bias noise-allowance check | \|recovered−injected\|=0.8441 vs. allowance 3.00×SE(0.2808)=0.8425 — fails by 0.0016, essentially at the 3-SE boundary |
| `core_hr_normal_like_wt_lost_direction_LR` | raw 0.25 relative-bias tolerance (criterion 1, unaffected by this fix) | relative_bias=0.2788 > 0.25; directional check itself now PASSES (0.0 predicted, well inside allowance) — same small-n (36/27) sampling-variance stratum flagged in P07-RERUN2, now correctly isolated as a criterion-1 failure rather than compounded with a criterion-2 false failure |

The repair resolves the miscalibration for 10 of the 11 previously
false-failing strata. `core_hr_normal_like`'s failure is unchanged in
substance (it was always a criterion-1, small-n sampling-variance
failure, now correctly reported as only that) and
`core_hr_luma`'s failure sits within 0.2% of the allowance boundary — a
single quantity landing just outside a 3-SE band is exactly the residual
false-failure risk (0.27% per-quantity, 3.19% family-wise at n=12,
§2) this multiplier accepts by design, not evidence the check is still
miscalibrated.

Full per-quantity detail:
`SIMULATED_loh_validation/gate6_directional_check_fix_rescoring/SIMULATED_RECOVERY_TABLE.tsv`
and `.md`.

## 5. Draft PROTOCOL.md §11 clarification (NOT APPLIED — flagged for sign-off)

Per Standing Rule 10, this text is proposed only. It is not written into
PROTOCOL.md. If approved, it would be inserted into §11's "Directional
shrinkage-bias check (NEW)" bullet (criterion 2), as a clarifying
sub-paragraph immediately following it.

> **Zero-bias predictions (clarification).** Criterion 2's advance
> prediction is not restricted to a nonzero shrinkage magnitude. An
> estimator with no penalized/shrinkage mechanism — one for which the
> correct advance prediction is "no systematic directional bias" — may
> declare `predicted_relative_bias_magnitude = 0`. In that case criterion
> 2 is evaluated as a **noise-allowance check** rather than a
> sign-plus-slack-around-a-nonzero-magnitude check: there being no
> predicted direction, no sign test applies, and the tolerance is an
> explicit multiple of the quantity's own bootstrap standard error
> (estimated from its reported 95% CI width), not a multiple of the
> (zero) predicted magnitude. The standard multiplier is 3 SE
> (`gates/gate6_recovery.py`'s `ZERO_BIAS_NOISE_ALLOWANCE_SE_MULTIPLIER`),
> chosen to keep the per-quantity false-failure rate under a true zero
> bias at 0.27% (family-wise ≈3.2% across a 12-quantity panel); a
> declaring caller may override the multiplier per-quantity via the
> `--bias-prediction` file's optional `noise_allowance_se_multiples`
> column, with justification recorded in that file's `source` field.
> This clarification does not change criterion 2's behavior for any
> nonzero-magnitude prediction, and does not change criterion 1 (the 0.25
> relative-bias tolerance) at all.

**Rationale for flagging rather than applying:** this is a protocol-text
change and per Standing Rule 10 an agent may propose but never apply a
protocol amendment. The gate-code change it describes is already applied
(permitted this task); the protocol text should be reconciled to match it
only after a human reviews both the multiplier choice (§2) and the
re-scoring result (§4).
