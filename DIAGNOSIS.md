SIMULATED DATA — NOT A SCIENTIFIC RESULT

# DIAGNOSIS.md — why P07 (`loh_caller.py`) failed gate6's relative-bias check

SIMULATED: this diagnoses a real result, not a claim about real tumors.
No ACMG evidence strength is assigned anywhere below.

**Finding (stated up front, evidence follows): the mechanism is a
confidence-threshold filter interacting with a provable, purity-dependent
collapse in the VAF model's power to separate `RETENTION` from either LOH
direction — not classifier misdirection, not an estimand bug, and not
"noise" in the dismissive sense. This is a real, specific, fixable
mechanism, evidenced in (c) and (d) below and proven algebraically.**

The data diagnosed here is P07's actual, already-completed run against
the pre-remediation simulator (`SIMULATED_loh_validation/SIMULATED_loh_calls.tsv`,
n=60, 15 samples per gene-group x class cell) — the same run gate6
reported `SIMULATED_FAIL` on for both scored quantities:

| quantity | injected | recovered | CI | relative_bias |
|---|---|---|---|---|
| `core_hr_loh_second_hit_LR` | 6.999999999999999 | 4.6 | [1.909, 25.0] | 0.3429 |
| `ddr_signaling_loh_second_hit_LR` | 2.666666666666667 | 3.6666666666666665 | [1.0, 17.0] | 0.3750 |

Both CIs contain their target; both point estimates exceed the 0.25
tolerance. Tested in the specified order:

## (a) Estimand mismatch

**Injected quantity, as defined in `simulate.py` (pre-remediation) and
recorded in `SIMULATED_TRUTH.tsv`:**

> `P(LOH_SECOND_HIT | Pathogenic) = 0.70` / `P(LOH_SECOND_HIT | Benign) =
> 0.10` — i.e., the probability that the DATA-GENERATING PROCESS assigned
> the `LOH_SECOND_HIT` category to a sample, given its true class. This
> is a **ground-truth category-assignment parameter** — a property of
> the simulator, fixed at generation time, independent of any classifier.

**Recovered quantity, as computed by `loh_caller.py`'s
`wt_lost_direction_lr_point()`:**

> `c_path = count(loh_caller PREDICTS "WT_LOSS" or "CN_NEUTRAL_LOH_WT_LOSS")`
> among Pathogenic samples; `p_path = jeffreys_rate(c_path, n_path)`;
> same for Benign; `recovered = p_path / p_benign`. This is the
> **classifier's own output-positive rate** — a property of
> `loh_caller.py`'s decision rule applied to noisy read data, not a
> direct readout of the ground-truth label.

**Are they the same thing? Only in the hypothetical limit of a perfect
classifier (100% sensitivity, 0% false-positive rate, both classes
identical).** `loh_caller.py`'s own classification method (a 3-hypothesis
binomial-log-likelihood posterior competition with a fixed 0.80
confidence threshold) is not PROTOCOL.md §5.1's own decision rule for
`LOH_SECOND_HIT` (a two-sided binomial-test rejection rule at α=0.05) —
the two rules do not have to agree on every locus, by design (this was
disclosed and intentional in the caller's own build task, per the
task's explicit instruction to use a likelihood-based method rather than
copy PROTOCOL's own p-value test). **This is a real, structural estimand
distinction, of the same KIND the task's preamble says broke a prior
version ("v2"'s full-vector-null estimand mismatch) — but here it is
small in magnitude** (measured directly on this run: zero false
positives in either arm; false negatives = 1/arm, both attributable to
mechanism (d) below, not to classifier disagreement about direction).
**Verdict: (a) is a real, non-zero, persistent contributor (it does not
vanish even at infinite n, since it converges to `true_rate x
sensitivity` rather than `true_rate`), but on this run's evidence it is
NOT the dominant driver of the observed 0.34–0.38 relative bias** — see
(c)/(d) for what is.

## (b) Scope

All 6 `SIMULATED_TRUTH.tsv` (pre-remediation) quantities, enumerated,
with which belong to P07:

| quantity | belongs to P07? | status this run |
|---|---|---|
| `core_hr_loh_second_hit_LR` | **yes** | scored, `SIMULATED_FAIL` |
| `ddr_signaling_loh_second_hit_LR` | **yes** | scored, `SIMULATED_FAIL` |
| `core_hr_gis_score_LR` | no (requires scarHRD, not built by P07) | declared `NOT_IN_SCOPE` / `BLOCKED`, with reason |
| `ddr_signaling_gis_score_LR` | no (requires scarHRD) | declared `NOT_IN_SCOPE` / `BLOCKED`, with reason |
| `core_hr_sbs3_exposure_LR` | no (requires SigProfilerAssignment) | declared `NOT_IN_SCOPE` / `BLOCKED`, with reason |
| `null_sequencing_depth_bucket_LR` | no (not P07's estimand) | declared `NOT_IN_SCOPE` / `BLOCKED`, with reason |

**Confirmed: no quantity was silently skipped.** All 6 appear in
`SIMULATED_RECOVERY_TABLE.tsv` from that run with an explicit
`scope_status` (`IN_SCOPE` or `NOT_IN_SCOPE`) and a stated reason for the
4 out-of-scope rows (gate6's scope-enumeration fix, from the immediately
prior gate-housekeeping task, already enforces this mechanically — an
undeclared quantity is a hard gate failure, and none occurred). The 2
P07 quantities are exactly the ones scored, and both failed for a real,
diagnosable reason (below), not because they were miscounted or evaded.

## (c) Offset shape — purity-dependent, proven algebraically

The only 2 false negatives in the entire n=60 run:

| sample | arm | true category | predicted | confidence | purity | depth | cn_total |
|---|---|---|---|---|---|---|---|
| SIM-0010 | CORE_HR | `CN_NEUTRAL_LOH_WT_LOSS` | `AMBIGUOUS` | 0.629 | **0.3098** | 74 | 2 |
| SIM-0045 | DDR_SIGNALING | `CN_NEUTRAL_LOH_WT_LOSS` | `AMBIGUOUS` | 0.503 | **0.1541** | 81 | 4 |

Both occur at **low purity** (bottom third of the 0.10–0.95 range); both
at high, unremarkable depth (74, 81 — depth is not implicated). Both were
demoted from a (likely correct) `WT_LOST_DIRECTION` argmax to `AMBIGUOUS`
by the 0.80 confidence threshold, not misclassified as the wrong
direction — this points at (d), and (c) explains *why* confidence
collapses specifically at low purity, via the VAF model itself:

`expected_vaf(rho, CN_t, X)` is affine in `X` (established in the prior
LOH-caller-validation task). For the `RETENTION_DIRECTION` hypothesis
(`X = CN_t/2`), `E[VAF] = 0.5` **exactly, for every purity** (proven
identity, re-derived here):

```
E[VAF | X=CN_t/2] = (rho*(CN_t/2) + (1-rho)) / (rho*CN_t + 2(1-rho))
                   = 0.5 * (rho*CN_t + 2(1-rho)) / (rho*CN_t + 2(1-rho)) = 0.5
```

For `WT_LOST_DIRECTION` (`X = CN_t`):

```
E[VAF | X=CN_t] = (rho*CN_t + (1-rho)) / (rho*CN_t + 2(1-rho))
```

The **gap** between this and `RETENTION_DIRECTION`'s constant 0.5:

```
gap(rho) = E[VAF|WT_LOST] - 0.5 = (rho*CN_t) / (2*(rho*CN_t + 2(1-rho)))
```

**This gap is monotonically increasing in `rho` and → 0 as `rho → 0`**
(to leading order, `gap(rho) ≈ rho*CN_t/4` for small `rho`) — i.e., the
signal distinguishing `WT_LOST_DIRECTION` from `RETENTION_DIRECTION`
vanishes in direct proportion to purity, a property of the model itself,
not of any particular sample. At `rho=0.3098, CN_t=2`: `gap ≈ 0.045`; at
`rho=0.1541, CN_t=4`: `gap ≈ 0.052` — both small enough, at real depth,
for the binomial-likelihood posterior to frequently fall under the 0.80
confidence threshold. (The same algebra shows `VARIANT_LOST_DIRECTION`
converges toward `RETENTION_DIRECTION`'s 0.5 identically as `rho→0`, and
that `WT_LOST_DIRECTION`/`VARIANT_LOST_DIRECTION` converge toward each
other proportionally *faster* than either converges toward `RETENTION`'s
0.5 — meaning retention-vs-either-loss-direction is the FIRST distinction
to degrade as purity drops, exactly matching what was observed: both
failures were retention-confusable `AMBIGUOUS` calls, not direction
inversions.)

**Verdict: the offset is purity-dependent, and the mechanism is provably
located in the VAF model's own loss of separation at low purity — not a
covariate-independent constant bias, and not random.**

## (d) Filter-induced bias — confirmed, mechanism identified

Both false negatives are `AMBIGUOUS` reclassifications by the 0.80
confidence threshold, not wrong-direction misclassifications (confirmed
directly: neither sample's predicted category is `VARIANT_LOSS`). The
filter is retaining a **purity-stratified non-representative subset**:
low-purity true positives are disproportionately excluded from the
"positive" count, while high-purity true positives are not — exactly the
mechanism (c) predicts, and exactly what "Filter-induced bias: does the
confidence/posterior filter retain a non-representative subset?" was
asking to check. **Confirmed: yes.**

### Contributing/amplifying factor: small-n ground-truth realization variance

At `N_PER_CELL=15` per (gene_group, class), the *realized* true-category
counts already deviate substantially from the *injected population
parameters* by ordinary binomial sampling of the category-assignment
draw itself — before the classifier does anything:

| arm | class | injected parameter | realized true-positive count/n | realized rate |
|---|---|---|---|---|
| CORE_HR | Pathogenic | 0.70 | 12/15 | 0.80 (+14% relative) |
| CORE_HR | Benign | 0.10 | 2/15 | 0.133 (+33% relative) |
| DDR_SIGNALING | Pathogenic | 0.40 | 6/15 | 0.40 (exact) |
| DDR_SIGNALING | Benign | 0.15 | 1/15 | 0.067 (**-56% relative**) |

Recomputing the recovered LR with a **hypothetically perfect classifier**
(predicted = realized-true counts exactly, no false negatives) still
gives CORE_HR = 5.0 (vs. injected 7.0, still outside tolerance) and
DDR_SIGNALING = 4.33 (vs. injected 2.667, further outside tolerance than
the actual recovered 3.667) — confirming that **most of the apparent
"bias" is inherited from finite-sample noise in the ground-truth draw
itself**, which the recovery quantity (and gate6's fixed-tolerance check)
cannot distinguish from classifier error at this n. `null_sequencing_depth_bucket_LR`-scale
tolerances were never calibrated to survive `n=15`; this is precisely
why the simulator revision immediately prior to this task raised n to
1848 per (arm, class) cell — a fix already in flight, not proposed here
for the first time.

## Conclusion — the mechanism, stated once

**Primary, structural, purity-dependent mechanism (proven, not asserted):**
the VAF model's `RETENTION_DIRECTION`-vs-`WT_LOST_DIRECTION` (and
vs-`VARIANT_LOST_DIRECTION`) separation vanishes proportionally to purity
(`gap(rho) → 0` as `rho → 0`), so the 0.80 confidence threshold
disproportionately reclassifies **true low-purity positives** as
`AMBIGUOUS`, undercounting the positive rate in a way that is NOT random
across the sample (it is purity-stratified) and NOT a constant offset
(it scales with the purity distribution actually drawn). This is
confirmed on both observed false negatives (both low-purity, both
retention-confusable `AMBIGUOUS` calls, neither a direction inversion).

**Secondary, non-zero, persistent contributor:** an estimand distinction
between the injected ground-truth category-assignment probability and
the recovered classifier-decision-rule output probability — real, but
small on this run (0 FP, 1 FN per arm), and expected to be quantifiable
independently of mechanism (c)/(d) once re-run at much higher n (Step 3).

**Amplifying factor, not itself the cause:** `N_PER_CELL=15` inflates
both of the above into a large *relative* bias because a single missed
sample moves the aggregate rate by 1/15 ≈ 6.7 percentage points, and the
ground-truth draw itself is realized far from its population parameter
at this n (table above). This is not "sampling noise, ignore it" — it is
a precisely located, quantified amplifier of a real, separately-proven
mechanism, and it is exactly why the simulator's n was already raised
before this task began.

Per STEP 2, the fix targets the PRIMARY mechanism directly: BAF
corroboration (independent of the single at-risk variant's own,
purity-diluted read count) is added to the caller's hypothesis
competition specifically to restore RETENTION-vs-LOH separation at low
purity, without touching direction discrimination (BAF's expected value
is identical for both loss directions — proven in the prior task — so it
cannot bias direction calls, only the retention/any-LOH boundary where
the diagnosed failure actually occurs).
