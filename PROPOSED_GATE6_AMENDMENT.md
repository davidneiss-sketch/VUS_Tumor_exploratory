SIMULATED DATA — NOT A SCIENTIFIC RESULT

# PROPOSED_GATE6_AMENDMENT.md — P-AMD-3a Part B (DRAFT ONLY)

**This is a proposal, not an applied change.** Per Standing Rule 10, an
agent may propose a protocol amendment; it may never apply one or waive a
gate. `gates/gate6_recovery.py` and `PROTOCOL.md` are **not modified** by
this document or by any script in this task. Application (P-AMD-3b) runs
only after explicit human sign-off on this draft.

## 0. Why this is being proposed

`RESIDUAL_DIAGNOSIS.md` (P-DIAG-1) attributed CORE_HR's gate6 containment
miss to ridge shrinkage bias at the CV-selected lambda — a known,
expected, now-quantified property of the estimator, not a defect.
`MIXTURE_FIX.md` (this task, Part A) fixed a real, separate defect (the
mixture application-point mismatch) and, as predicted, this WIDENED the
containment gap (removing an artifact that had been partially masking the
shrinkage bias). With the application-point defect fixed, the remaining
miss is attributable to shrinkage alone, and is larger, not smaller, than
before. This makes the criterion question sharper, not resolved by the
fix: gate6 currently requires exact CI containment of the injected value
as a hard pass/fail condition, in addition to a relative-bias tolerance.
For a penalized estimator with a proven, quantified shrinkage bias, is
exact containment of an *unshrunk* target the right criterion?

## 1. The proposed amended criterion

Replace gate6's current dual condition —

- CI must contain the injected value (hard fail if not), **AND**
- relative bias must be within tolerance (currently 0.25)

— with:

1. **Relative bias within the stated tolerance** (unchanged tolerance
   value pending the computation in section 3 below, which may require
   tightening it as a condition of this amendment).
2. **A directional shrinkage-bias check**: the estimator's expected bias
   direction (toward the null, i.e. downward for LR>1 quantities, upward
   for LR<1 quantities) and its approximate magnitude are declared *in
   advance* (before the recovery run, from the CV-selected lambda's own
   shrinkage curve — e.g. via a lambda sweep like the one in
   `MIXTURE_FIX_POST_FIX_DIAGNOSTICS.md`), and the OBSERVED bias must be
   consistent with that prediction: same sign, and not materially larger
   in magnitude than predicted. A result whose bias is the WRONG sign, or
   far larger than the pre-declared expectation, FAILS even when inside
   the raw tolerance — this is what carries gate6's original
   fault-detection job forward (section 4).
3. **CI containment is no longer a hard pass/fail condition.** It is
   still **computed and reported** for every quantity — visible
   information for the reader of `SIMULATED_RECOVERY_TABLE.tsv`, e.g. as
   a `ci_contains_injected` column — but a miss no longer fails the gate
   by itself.

## 2. Rationale, stated honestly

A penalized (ridge) estimator is biased toward the null by construction —
that is the mechanism by which it trades bias for variance reduction at
small class sizes, which is exactly the regime PALB2, RAD51C, and RAD51D
will occupy on real Track B data (class sizes in the tens, per
`SIMULATION_SPEC.md` §6's own Track B derivation). Cross-validation
selects `lambda.1se` to minimize **held-out prediction deviance**, not to
minimize bias in the recovered LR at one specific evaluation point — so a
small, non-zero, and broadly PREDICTABLE residual bias in the recovered
LR at the CV-selected lambda is expected, ordinary behavior of the
selection procedure, not a symptom that something is wrong with the fit.
`MIXTURE_FIX.md`'s lambda sweep shows this bias is monotonic and
well-characterized as a function of lambda for both arms — it is not
erratic or unpredictable, which is precisely why a directional prediction
(criterion 2 above) is a meaningful, checkable substitute for exact
containment rather than a loophole.

## 3. The counter-argument, and the computation it requires

**Counter-argument, stated with equal weight:** gate6 exists because an
earlier production estimator reported a badly wrong recovered value
against its injected target. The task instruction that prompted this
document states this historically as "v2 reported 8.83 against an
injected 4.5" — **this exact figure could not be independently verified
against any on-disk artifact in this repository** (searched: all
committed `.md`/`.tsv` files, and `git log -p` across the full commit
history; no result of `8.83` against an injected `4.5` was found as a
recorded gate6 output). Per Standing Rule 3, this is reported here as
**UNVERIFIED**, not silently treated as fact. The computation below is
performed on the figure exactly as given by the task, disclosed as
unverified, **and independently repeated against an actual, on-disk,
git-tracked fixture** (`tests/fixtures/gate6_bad_ci/`, documented in
`TRIPWIRE_EVIDENCE.md`: recovered=9.3, CI=[7.47, 11.25], injected=4.5),
so the conclusion below does not rest on the unverified figure alone.

**Would either failure still fail under the amended criterion, at the
current 0.25 tolerance? Computed, not asserted:**

| source | recovered | injected | relative bias | vs. 0.25 tolerance |
|---|---|---|---|---|
| task-stated (**UNVERIFIED**, see above) | 8.83 | 4.5 | `(8.83-4.5)/4.5` = **+96.22%** | FAILS (96.22% ≫ 25%) |
| on-disk fixture `gate6_bad_ci` (verified, `TRIPWIRE_EVIDENCE.md`) | 9.3 | 4.5 | `(9.3-4.5)/4.5` = **+106.67%** | FAILS (106.67% ≫ 25%) |

**Both would still fail under the amended criterion, at the current 0.25
tolerance, on relative bias alone** — neither needs the directional check
to be caught; the relative-bias tolerance by itself already rejects a
result this far off. **The tolerance does not need to tighten as a
condition of this amendment** — the motivating failure mode is caught by
the unchanged 0.25 tolerance both under the current criterion and under
the proposed one. (Had the computation come out otherwise — bias within
0.25 but still wrong — tightening the tolerance would have been a
required part of this amendment, per the task's own instruction; that
branch does not apply here.)

This computation also exposes what CI containment was doing in the
`gate6_bad_ci` case that the amended criterion must independently
replace: the recovered CI `[7.47, 11.25]` does not contain `4.5`, so the
OLD criterion catches it two ways at once (containment AND bias). The
amended criterion catches it only one way (bias) — which is why section 4
below is not optional decoration; without a directional check, a
hypothetical FUTURE failure mode that stays within the 0.25 bias
tolerance while still being wrong in a checkable way would slip through
unless something distinguishes "small bias that matches the estimator's
own predicted shrinkage" from "small bias that happens to be small for
the wrong reason."

## 4. What replaces containment as protection against the v2 failure mode

Exact CI containment, as a blunt hard-fail condition, does two jobs at
once: (a) catches gross errors (wrong estimand, sign flip, broken prior-
odds correction — the `gate6_bad_ci`/`gate6_bad_estimand` failure
family), and (b) penalizes small, expected, well-characterized shrinkage
bias identically to (a) — which is the false-positive this amendment
targets. Section 3 shows job (a) survives the amendment intact via the
relative-bias tolerance alone, for both the unverified figure and the
verified on-disk fixture. Job (a)'s SECOND, distinct failure mode —
`gate6_bad_estimand` (an OR-vs-LR mismatch,
`tests/fixtures/gate6_bad_estimand/`) — is unaffected by this amendment
at all: it is caught upstream, by the existing estimand-match check
(`estimand_truth != estimand_recovered`), which this amendment does not
touch.

The **directional shrinkage-bias check** (criterion 2, section 1) is what
specifically replaces containment's role in catching a bias that is
small in magnitude but WRONG — e.g., an estimator whose bias is upward
when downward shrinkage was predicted (sign flip, suggesting a broken
prior-odds correction or an application-point-style defect elsewhere), or
whose bias is far larger than its own declared lambda-sweep would
predict (suggesting the CV-selected lambda or the fitting procedure
itself misbehaved on this particular run, not merely "shrinkage
happened"). A future quantity that passes relative-bias tolerance by
accident, while its bias direction or magnitude contradicts what its own
estimator predicts, is exactly the case containment's blunt version would
have caught by luck and the directional check catches by design.

## 5. What is NOT proposed here

- No change to lambda selection, the ridge penalty, or any estimator
  parameter (Standing Rule 10; and per the user's own explicit caution:
  the CV-selected lambda exists because small-n stability is what the
  study needs — PALB2/RAD51C/RAD51D will have class sizes in the tens,
  and an unpenalized fit would trade a characterized bias on synthetic
  data for unusable intervals on real data).
- No specific tolerance VALUE change (section 3's computation shows the
  current 0.25 is not the binding constraint for either historical
  failure considered).
- No change to `gate6_recovery.py`'s estimand-match check, the null-
  containment check (both untouched by this proposal).
- No decision on WHICH criterion (exact containment vs. the amendment
  above) is correct — that is explicitly the human's decision, per
  Standing Rule 10 and this task's own HALT instruction.
