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
report should read this file's deviation section as-is (not
re-summarized) and prepend or append the rest of the study's narrative
around it.

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

*(No further sections. This file's scope, as created by this task, ends
here — see this file's own opening note.)*
