SIMULATED DATA — NOT A SCIENTIFIC RESULT

# REPORT.md

SIMULATED: **this file did not exist in this repository before this
task.** It is created now specifically because this task's own
instruction requires the protocol-amendment deviation below to "appear
prominently in REPORT.md, not only in an appendix." This file is not a
synthesized retrospective of every prior task in this session — assembling
that would mean generating narrative content this task was not asked to
produce and was not scoped to verify; doing so here, unprompted, would
risk exactly the kind of unverified, invented content Standing Rule 3
forbids. What follows is the deviation entry, placed first and
prominently, as instructed. A future task that assembles a full study
report should read this file's deviation sections as-is (not
re-summarized) and prepend or append the rest of the study's narrative
around them.

---

## Protocol deviation in effect (APPLIED): PROTOCOL.md §11's recovery-tolerance criterion, and a known estimator-bias disclosure

**Status: APPLIED.** `PROTOCOL.md` §11 (Stage 2 recovery-tolerance
criterion) was amended and applied this task
(`PROTOCOL_DEVIATIONS.md` Entry 3, approver recorded there).

**What changed:** CI containment of the injected value is **no longer a
hard pass/fail condition** for Stage 2 `SIMULATED_PASS`/`SIMULATED_FAIL`
status — it is computed and reported for every quantity
(`ci_contains_injected` in `SIMULATED_RECOVERY_TABLE.tsv`), information
for the reader, not a gate. In its place: the existing 0.25 relative-bias
tolerance (unchanged), plus a new **directional shrinkage-bias check** —
when the estimator's expected bias magnitude for a quantity is declared
in advance from its own characterized shrinkage curve, an observed bias
of the wrong sign, or materially larger than predicted, still FAILS the
quantity even when inside the raw tolerance.

**Why:** `RESIDUAL_DIAGNOSIS.md` (P-DIAG-1) and `MIXTURE_FIX.md`
(P-AMD-3a) established that CORE_HR's CI-containment miss is caused by
ridge shrinkage bias at the CV-selected penalty — a known, expected,
now-quantified property of the currently-used estimator, not a defect
(Monte Carlo noise and a separate mixture-weighting defect were both
ruled out or fixed first). `PROPOSED_GATE6_AMENDMENT.md` computed,
against the actual on-disk `tests/fixtures/gate6_bad_ci/` fixture (the
case that motivated building gate6: recovered=9.3 vs injected=4.5), that
this amendment does **not** let that historical failure pass — it still
fails, on relative bias alone (106.67% ≫ 25%) — so no tolerance
tightening was required.

**Known conservative bias, disclosed here as instructed (not merely in
an appendix):** the CV-selected penalty's shrinkage-toward-the-null bias
systematically UNDERSTATES evidentiary strength — downward for LR>1
(pathogenic-leaning) quantities, upward for LR<1 (benign-leaning) ones —
**never the reverse**, by construction of the shrinkage mechanism. Since
`PROTOCOL.md` §9 assigns ACMG-equivalent evidence from the CI lower
bound, a true quantity near an OddsPath boundary may be assigned ONE
TIER LOWER than its true strength; it will never be assigned a tier that
OVERSTATES the true strength. This is not hypothetical for this study:
**both of the two quantities this project has actually recovered so far
(CORE_HR and DDR_SIGNALING) show exactly this — a realized, one-tier
downgrade** (`PATHOGENIC_MODERATE` → `PATHOGENIC_SUPPORTING`), confirmed
conservative in direction (never an over-call) by
`scripts/confirm_tier_directionality.py`, whose full output is
`CONFIRM_TIER_DIRECTIONALITY_RESULT.md`. `gate6_recovery.py`'s
`SIMULATED_RECOVERY_TABLE.tsv` now carries this as a standing
`near_tier_boundary` column on every run, not a one-time note. Full
quantification and both draft-and-applied disclosure texts:
`CONSERVATIVE_ASSIGNMENT_ANALYSIS.md`.

**What this means for reading this study's results:** every
`PATHOGENIC_SUPPORTING` or `PATHOGENIC_MODERATE` call landing near a §9
boundary should be read with this conservative margin in mind — the true
strength is at least this strong, plausibly one tier stronger, never
weaker than reported.

Nothing about §7.1's model specification changed as part of this entry —
see the next section for that separate, still-unapplied amendment, and
`PROTOCOL.md` §11's own closing note for how the two relate.

---

## Protocol deviation in effect (draft): PROTOCOL.md §7.1's estimator

**Status: DRAFT — proposed, not applied. PROTOCOL.md is unmodified.**

`PROTOCOL.md` §7.1 currently specifies a joint feature-vector likelihood
ratio computed as a **product of per-feature marginal likelihood ratios
under a conditional-independence assumption**. This project's own audit
(`ESTIMATOR_SPECIFICATION_AUDIT.md`) proved — first from the code, then
by a decisive numeric test constructed so that only a true joint-density
estimator could pass it — that this estimator **cannot recover the
joint-density quantities this study was built to measure, at any sample
size**: run on two datasets with identical marginal feature distributions
and different correlation structure, its output was statistically
indistinguishable between them (0.26 and 0.02 pooled-standard-deviation
units apart, for CORE_HR and DDR_SIGNALING respectively) even though the
true joint likelihood ratios differed by 12.8x and 3.7x by construction.

**The decision has been made to replace this estimator with penalized
logistic regression** (L2/ridge, with purity, PAM50 subtype, and WGD as
covariates, converting fitted probability to likelihood ratio via an
explicit prior-odds division), as the project's original brief specified.
The full replacement text for §7.1, the deviation record, and the
quantity-by-quantity reachability analysis are in three companion
documents:

- **`PROPOSED_PROTOCOL_AMENDMENT.md`** — the complete, exact replacement
  text for §7.1, including the prior-odds conversion arithmetic written
  out explicitly (this is the step that broke a prior version of this
  project's pipeline, "v2" — the arithmetic is not left to a future
  implementer to infer).
- **`PROTOCOL_DEVIATIONS.md`** — the formal deviation record: what
  changed, why, the evidence and its numbers, what was known at
  pre-registration versus what was not, and an **Approver field left
  blank for a human to complete.** This amendment does not take effect
  until that field is filled in and `PROTOCOL.md` is edited in a
  separate, subsequent, human-approved task.
- **`REACHABILITY_TABLE.tsv`** — every one of `SIMULATED_TRUTH.tsv`'s 91
  quantities, classified as newly reachable (24 — every `*_joint_LR` and
  `*_joint_vs_marginal_inflation_ratio` quantity, pooled and
  subtype-stratified, across both arms), still reachable (67 — every
  single-feature marginal LR, every `*_product_of_marginals_LR`, and
  every NULL_ARM/secondary-null quantity), or still unreachable (0 — no
  currently-committed truth quantity remains unreachable under this
  amendment; this is reported as a finding, not assumed).

**This is a pre-registered protocol being amended in response to a
result.** Per Standing Rule 10, that is permitted only because the
finding is that the specified method cannot structurally answer the
specified question — proven by a test whose outcome was not
predetermined — not because an unfavorable result is being edited away.
No gate was waived to reach this conclusion; the prior task
(`ESTIMATOR_SPECIFICATION_AUDIT.md`) reported the finding and HALTed
rather than acting on it. This report, and the deviation record it
points to, are the recording of that finding — not its resolution.
Nothing downstream (gate6, P09, or any pipeline file) has been re-run
against this amendment. **HALT: this amendment requires human review,
sign-off, and tagging before anything proceeds.**

---

*(No further sections beyond the two deviation entries above. This
file's scope, as created and extended across P-AMD-3a/3b, ends here —
see this file's own opening note.)*
