SIMULATED DATA — NOT A SCIENTIFIC RESULT

# PROTOCOL_DEVIATIONS.md — pre-registered protocol amendments

SIMULATED: this document records amendments to the pre-registered
`PROTOCOL.md`, made in response to evidence, not silently absorbed into
a later methods section. Per Standing Rule 10, an agent may PROPOSE an
amendment; it may never APPLY one. **This entry is a DRAFT.** No entry
in this document takes effect until its Approver field is completed by
a human and `PROTOCOL.md` is itself edited in a separate, subsequent
task — this document, on its own, changes nothing.

This document is distinct from `PROPOSED_DEVIATIONS.md` (an earlier,
still-standing set of proposals concerning P07's purity/depth floors and
a P08 SBS3-informativeness addendum) — that document is unaffected by
this one and remains open on its own terms.

---

## Entry 1 — Replace PROTOCOL.md §7.1's estimator (product-of-marginals) with penalized logistic regression

| field | value |
|---|---|
| **Status** | DRAFT — not yet applied |
| **Date drafted** | 2026-09-09 |
| **Section amended** | PROTOCOL.md §7.1 ("Model") |
| **Approver** | _(blank — for human completion)_ |

### What changed

The current §7.1 specifies "the product of per-feature LRs, under a
conditional-independence assumption given class" for the joint feature
vector's likelihood ratio. This entry proposes replacing that with
**L2-penalized (ridge) logistic regression on the full feature vector,
with purity, PAM50 subtype, and WGD as covariates**, converting the
fitted probability to a likelihood ratio by dividing out the reference
set's own class-balance-implied prior odds. Full replacement text:
`PROPOSED_PROTOCOL_AMENDMENT.md`.

### Why

`ESTIMATOR_SPECIFICATION_AUDIT.md` (this session, prior task) proved from
the code that §7.1's current estimator, exactly as specified and
implemented, cannot represent correlation between features at all — it
is a literal, in-code product of independently-estimated marginal
likelihood ratios, with no step conditioning one feature's density
estimate on another. This was then proven numerically by a decisive
constructed test, not inferred from behavior: two synthetic datasets with
IDENTICAL class-conditional marginal feature distributions and DIFFERENT
correlation structure (one drawn from this project's own shared-latent-Z
generative model, one with the three features drawn independently from
the same closed-form marginals) were both run through the estimator.

**The evidence, in full (`SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST.tsv`,
prior task):**

| arm | true joint LR (correlated data) | true joint LR (independent data) = product-of-marginals LR | estimator's mean, correlated data | estimator's mean, independent data | difference (pooled-sd units) |
|---|---|---|---|---|---|
| CORE_HR | 7.243 | 92.625 | 73.151 | 78.535 | 0.26 |
| DDR_SIGNALING | 6.204 | 22.794 | 21.320 | 21.470 | 0.02 |

The true joint LR differs from the true product-of-marginals LR by 12.8x
(CORE_HR) and 3.7x (DDR_SIGNALING) by construction — a large, real,
by-design gap this project's own shared-latent-variable simulator (P06R)
exists specifically to make testable. The estimator's own empirical mean
is statistically indistinguishable between the correlated and independent
datasets (0.26 and 0.02 pooled-sd units apart — noise) and sits close to
the product-of-marginals value in both cases, nowhere near the true joint
value of the correlated dataset. **This estimator cannot recover the
joint-density quantities this study was built to measure, regardless of
sample size, bootstrap replicate count, or KDE implementation quality —
this is structural to its factorization, not a small-n artifact.**

This is precisely the failure mode the original brief this project
started from identified as the error reviewers look for first: three
readouts of one underlying biological event (HR-deficiency), treated as
if independent, and multiplied. The features are three readouts of one
underlying event; the independence assumption is known false by this
project's own generative design (P06R's shared latent variable exists to
make it false and testable) — not a hypothetical concern raised in the
abstract.

### What was known at pre-registration, and what was not

**Known at pre-registration:** that the joint feature vector's LR would
be computed as *some* combination of the three evidentiary features, and
that §7.1's text itself disclosed the combination as a product under a
stated conditional-independence assumption, with correlation "tested and
reported (not assumed silently)" via pairwise correlation diagnostics.

**Not known at pre-registration:** that the correlation diagnostics
§7.1 already required to be reported would, when actually computed
against this project's own shared-latent-variable simulator (built in a
LATER task, P06R, specifically to make the correlation testable). show a
gap this large (12.8x / 3.7x, later 8.0x / 3.1x post the subtype fix) —
and, more fundamentally, that no amount of larger sample size or better
per-feature density estimation could close it, because the estimator's
own factorization structurally forecloses recovering the joint quantity
regardless of how well each marginal piece is estimated. This was not
resolvable at pre-registration time: it required both (a) building a
generative model with a genuine, quantifiable correlation structure
(P06R, a later task) and (b) the decisive two-dataset test constructed
specifically to distinguish "estimator models the joint density" from
"estimator multiplies marginals" (P-EST-1, this session's immediately
prior task) — neither existed when §7.1 was first written.

### Is this a legitimate amendment, or the study editing its own criteria?

Standing Rule 10 exists precisely to stop a result from editing the
criteria it is judged against, and to require that an amendment be
PROPOSED and recorded, never silently applied or used to waive a gate.
This entry is permitted under that rule for a specific, narrow reason,
stated here rather than assumed: **the finding is not that §7.1's
estimator produced an unfavorable result and is being replaced to get a
more favorable one — the finding is that the specified method cannot
structurally answer the specified question, proven by a test whose
outcome was not predetermined** (a true joint estimator would have
passed STEP 2's test; this one did not, and the test does not know in
advance which way it will come out). No gate was waived to reach this
conclusion — `ESTIMATOR_SPECIFICATION_AUDIT.md` explicitly reported the
finding and HALTed rather than acting on it, and this document records
the resulting amendment rather than applying it. The distinction Standing
Rule 10 draws — "an agent that can waive its own gates has no gates" —
is respected here: no code, gate, or protocol file is edited by this
document; `PROTOCOL.md` amendment happens, if at all, in a separate,
subsequent, human-approved task.

### Evidence

- `ESTIMATOR_SPECIFICATION_AUDIT.md` — STEP 1 (code-vs-spec agreement),
  STEP 2 (the decisive numeric test, full table above), STEP 3 (what
  becomes unreachable under the current estimator), STEP 4 (the two
  separate GATE8 instability findings, neither a consequence of the
  independence assumption).
- `SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST.tsv` /
  `SIMULATED_ESTIMATOR_JOINT_VS_PRODUCT_TEST_REPLICATES.tsv` — the raw
  test output the table above is drawn from.
- `ESTIMATOR_OPTIONS.md` — the four candidate paths this decision chose
  among (this entry implements Option C: penalized logistic regression
  with the prior-odds correction, per the original brief's own
  specification).
- `REACHABILITY_TABLE.tsv` — every `SIMULATED_TRUTH.tsv` quantity's
  reachability status under this amendment (24 of 91 quantities move from
  unreachable to newly reachable; the remaining 67 were, and remain,
  reachable).

### Downstream consequence for gate6 / P09

Under the CURRENT estimator, `*_joint_LR` and `*_joint_vs_marginal_inflation_ratio`
quantities (24 of 91) are structurally unreachable — a gate6 run against
them would and should FAIL regardless of tuning. Under this amendment,
those same 24 quantities become the estimator's own primary,
correctly-factored target. `REACHABILITY_TABLE.tsv` gives the full,
per-quantity classification.

---

## Entry 2 — Implementation deviation in `production_v2_run.py`: hardcoded lambda, occurred and corrected

| field | value |
|---|---|
| **Status** | RESOLVED — occurred, then corrected, both logged (Standing Rule 4: a mistake fixed is still logged, not erased) |
| **Date occurred** | 2026-09-09 |
| **Date corrected** | 2026-09-09 (same day, next task in this series) |
| **File** | `production_v2_run.py` |

### What happened

`production_v2_run.py`'s first version (committed 2026-09-09, this
session) used `LAMBDA_FIXED = 1.0`, a hardcoded ridge-penalty constant,
for its production fits — not the CV-selected `lambda.1se`
`PROPOSED_PROTOCOL_AMENDMENT.md`'s own approved §7.1 replacement text
specifies. `logistic_estimator.py` itself already implemented CV
selection correctly (exercised in `CALIBRATION_DIAGNOSTICS.md`'s own
runs); the production script simply did not call it, for its own
disclosed reason at the time (bounding the cost of 2 strata × B=2000 to
a single lambda value rather than 2 strata × 5-fold CV × 9-lambda-grid
× B=2000). That disclosed reason did not make the choice compliant with
the approved amendment — **a production run with a hardcoded penalty
did not implement the amended protocol**, a finding distinct from (and
more severe than) the evaluation-methodology gap Entry 2's sibling
finding (single-subtype evaluation, below) describes.

### Correction

`production_v2_run.py` now calls `logistic_estimator.py`'s own
`select_lambda_cv()` for every production fit (pooled recovery AND the
gate9 imbalance sweep), and carries an explicit provenance guard
(`select_cv_lambda_with_provenance()` / `assert_cv_selected()`) that
raises `AssertionError` and halts the run if any downstream computation
is ever reached with a lambda value not tagged `CV_SELECTED` — a
structural guard against this specific deviation recurring, not merely
a corrected value. `logistic_estimator.py` itself is unmodified (per
this task's own DO-NOT clause) — the guard lives entirely in the calling
script.

### Compounding finding, same production run: single-subtype evaluation

The same first version of `production_v2_run.py` also evaluated the
pooled `core_hr_joint_LR` / `ddr_signaling_joint_LR` quantities at a
single reference subtype (`subtype="LumA"`) rather than the
PAM50-prevalence-weighted mixture `SIMULATED_TRUTH.tsv`'s own pooled
quantities represent — an ESTIMAND MISMATCH, the same class of error as
the prior-odds conversion issue that broke "v2" and as P07's own first
pass (both cases of scoring a recovered value against a target it was
not actually computing). **This is the third time this project has hit
an estimand mismatch.** Corrected the same day: `production_v2_run.py`
now evaluates the fitted model at all 5 PAM50 subtype levels and
prevalence-weights them using the SAME `simulate.PAM50_PROPORTIONS`
values `SIMULATED_TRUTH.tsv`'s own truth derivation uses (imported
directly, not re-derived), and prints the injected and recovered
estimand definitions side by side on every run (see
`DEPLOYMENT_LOG.md`'s Invocation 5) — making the comparison visible by
default, per this task's own instruction, rather than something a future
session must diagnose from a bare `SIMULATED_FAIL` line.

### Result after both corrections

See `DEPLOYMENT_LOG.md`'s Invocation 5 for gate4/gate6/gate8/gate9's
results against the corrected production run. Per this task's own
instruction, no further methodology change is made in direct response to
that result (whatever it is) — Standing Rule 2 applies: a failed
validation reported honestly is a successful session, and this project's
own DO-NOT clause ("do not tune anything toward a target recovery
value") means the result stands as computed.

---

## Entry 3 — Amend PROTOCOL.md §11's recovery-tolerance criterion: CI containment reported, not gated; directional shrinkage-bias check added

| field | value |
|---|---|
| **Status** | **APPLIED** — approved and implemented this task (P-AMD-3b) |
| **Date drafted** | 2026-09-09 (P-AMD-3a, `PROPOSED_GATE6_AMENDMENT.md`) |
| **Date approved** | 2026-09-09 |
| **Date applied** | 2026-09-09 (same day) |
| **Section amended** | `PROTOCOL.md` §11 ("Stage 2 — synthetic recovery test and RECOVERY TOLERANCE") |
| **Files changed** | `gates/gate6_recovery.py`, `PROTOCOL.md` §11, `REPORT.md`, `tests/test_gate6.py` + 2 new fixtures |
| **Approver** | davidneiss@unicauca.edu.co (session user — sign-off given as an explicit task message this session: "SIGN-OFF GIVEN. The amendment drafted in PROPOSED_GATE6_AMENDMENT.md is approved as written, with one addition (Part D below)." This is the verified, session-authenticated user identity available; no other identifier is invented per Standing Rule 3.) |

### What changed

`PROTOCOL.md` §11's Stage 2 recovery criterion previously required BOTH
(1) the recovered 95% CI to contain the injected target value, AND (2)
relative bias ≤ 0.25 — either failing meant `SIMULATED_FAIL`. This entry
replaces (1): **CI containment of the injected value is no longer a hard
pass/fail condition.** It is computed and reported for every quantity
(new `ci_contains_injected` column in `SIMULATED_RECOVERY_TABLE.tsv`),
but does not affect `status`. In its place, a NEW, additive **directional
shrinkage-bias check**: when the estimator's expected bias magnitude for
a quantity is declared in advance (a new, optional `--bias-prediction`
input to `gate6_recovery.py`, sourced from the estimator's own
characterized shrinkage curve — e.g. a lambda sweep at the CV-selected
penalty), the observed bias must be the same sign as predicted (toward
the null: downward for LR>1, upward for LR<1) and not materially larger
in magnitude (slack factor 1.5x, `gate6_recovery.py`'s
`MAGNITUDE_SLACK_FACTOR`, disclosed there) — a wrong-sign or
much-larger-than-predicted bias FAILS even when within the raw 0.25
tolerance. Relative bias itself (2) is UNCHANGED, still at 0.25. The
existing null-containment check (for injected-null quantities) is
UNCHANGED and still gates.

Also added (Part D of this task, at the human's own request, appended to
the approved draft): a `NEAR_TIER_BOUNDARY` column, computed whenever a
bias-prediction magnitude is available for a pathogenic-direction
(injected > 1) quantity, flagging whether the recovered CI lower bound
falls within the characterized-bias "danger zone"
(`CONSERVATIVE_ASSIGNMENT_ANALYSIS.md`'s `f/(1-f)`-of-boundary result) of
one of §9's four OddsPath boundaries. This is a standing, always-computed
part of `gate6_recovery.py`'s output, not a one-time analysis.

### Why

`RESIDUAL_DIAGNOSIS.md` (P-DIAG-1) established that CORE_HR's CI
containment miss was caused by ridge shrinkage bias at the CV-selected
lambda — a known, expected property of the penalized estimator, not a
defect (0/15 independent seeds contained, ruling out Monte Carlo noise;
the mixture-weighting application-point defect, once isolated, pushed the
wrong direction to explain it alone). `MIXTURE_FIX.md` (P-AMD-3a) then
fixed that separate application-point defect and, as predicted, the
containment gap WIDENED (0.053 → 0.330 for CORE_HR) because removing the
defect stopped it from partially offsetting the shrinkage bias — the
miss is real, systematic, reproducible, and now larger, not an artifact
of the fixed bug. `PROPOSED_GATE6_AMENDMENT.md` computed, rather than
asserted, that the historical failure motivating gate6's original design
(the on-disk `tests/fixtures/gate6_bad_ci/` fixture: recovered=9.3,
injected=4.5, CI=`[7.47, 11.25]`) still fails under the amended criterion
at the current 0.25 tolerance (relative bias 106.67%) — so no tolerance
tightening was required. (Note on provenance, from the approving human:
the task text's own "v2 reported 8.83 against an injected 4.5" figure
came from a conversation transcript, not this repository, and was
correctly flagged `UNVERIFIED` in `PROPOSED_GATE6_AMENDMENT.md` rather
than treated as fact; the on-disk `gate6_bad_ci` fixture is the
authoritative regression target, per the approving human's own
instruction, and is what `tests/test_gate6.py` now asserts against.)

### Directionality confirmation (Part D requirement, run before this text was added)

`scripts/confirm_tier_directionality.py` verified, against the corrected
P-AMD-3a production output, that every tier movement this amendment's
own `NEAR_TIER_BOUNDARY`/`CONSERVATIVE_ASSIGNMENT_ANALYSIS.md` findings
identify moves in the CONSERVATIVE direction only (recovered ACMG tier
≤ true tier, never >) — see that script's own output, captured in
`CONFIRM_TIER_DIRECTIONALITY_RESULT.md`. Per this task's own explicit
HALT condition, had any movement gone the other way, this text would not
have been added to `PROTOCOL.md` and the task would have stopped instead.

### What was NOT changed

- The relative-bias tolerance value (0.25) — computed as not requiring a
  change, see above.
- The estimand-match check (comparing an OR to an LR remains an automatic
  fail regardless of any of this).
- The null-containment check (injected-null quantities' CI must still
  contain 1.0).
- `PROTOCOL.md` §7.1's model specification — this entry is independent of
  Entry 1 (the §7.1 model-replacement amendment), which **remains DRAFT**
  and unapplied. §11's amended criterion is written to apply regardless
  of which model §7.1 ultimately specifies; see §11's own closing note in
  `PROTOCOL.md`.
- `logistic_estimator.py`, `simulate.py`, `signatures.py`,
  `loh_caller.py` — none modified by this task.
- Lambda selection, the ridge penalty, or any estimator parameter — this
  amendment characterizes and reports the estimator's known behavior, it
  does not tune the estimator toward a passing result.

---

## Approver (Entry 1 only)

_(blank — for human completion. Entry 1 (the §7.1 model-replacement
amendment) does not take effect, and `PROTOCOL.md` §7.1 is not edited,
until THIS field is completed and a separate, subsequent implementation
task is run. Entry 3's own approval is recorded in its own table above,
distinct from this field — Entry 3 does not depend on Entry 1's
approval, and does not complete it.)_
