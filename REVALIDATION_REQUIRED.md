SIMULATED DATA — NOT A SCIENTIFIC RESULT

# REVALIDATION_REQUIRED.md — does P06R3's fix invalidate P07 or P08?

SIMULATED: this document answers, with evidence, whether `loh_caller.py`
(P07) or `signatures.py` (P08 / P08-RERUN) need to be re-run against
P06R3's clipped-density fix. Per this task's explicit instruction, **neither
is re-run from this prompt** regardless of the answer below — this document
only determines whether either must be, for a future task to act on.

## Answer: P07 — NO. P08 — NO (the pipeline does not need re-running), BUT
## P08-RERUN's own narrative documents contain a conclusion this task's
## audit has now overturned, which a future documentation task should
## correct.

## 1. P07 (`loh_caller.py`)

`loh_caller.py`'s `RECOVERY_SCOPE` declares exactly two quantities
`in_scope: TRUE`: `core_hr_wt_lost_direction_LR` and
`ddr_signaling_wt_lost_direction_LR`. Both are derived by
`marginal_wt_lost_prob()`, which reads only `WT_LOST_LINK[arm]`, `Z_MEAN`,
and `Z_SD` — none of which P06R3 touched (FIDELITY_AUDIT.md §2 confirms the
WT_LOST feature has no clip in the generator at all, and its analytic
closed form was already exact). TRUTH_DELTA.md §1 confirms both quantities
are byte-identical before/after P06R3's fix
(`core_hr_wt_lost_direction_LR = 4.480411981797967`,
`ddr_signaling_wt_lost_direction_LR = 2.137348544853484`, unchanged).
**P07 does not need to be re-run: nothing it depends on moved.** This
reaffirms P06R2's own `P07_REVALIDATION_REQUIRED.md` (NO), for an
independent reason (that document concerned the mutation-catalogue shape
fix; this one concerns the SBS3-clip fidelity fix) — P07 has now survived
two separate, independent simulator revisions without needing a re-run,
because its two recovery quantities structurally never touch SBS3, GIS, the
joint model, or the latent Z's distributional shape at all — only the
`WT_LOST_LINK`/`Z_MEAN` closed form, unmodified by either fix.

## 2. P08 / P08-RERUN (`signatures.py`)

### 2a. Does the pipeline need re-running?

`signatures.py`'s `phase6_gate6_recovery()` reads `SIMULATED_TRUTH.tsv`'s
`core_hr_sbs3_exposure_LR` and `ddr_signaling_sbs3_exposure_LR` rows as its
gate6 targets. TRUTH_DELTA.md §1 confirms both are byte-identical before and
after P06R3's fix (`5.644994542233774` and `3.9157230519927206`
respectively — unchanged). `SIMULATED_data/SIMULATED_signature_exposures.tsv`
and `SIMULATED_data/SIMULATED_mutation_catalogs.tsv` (the two files
`signatures.py` actually reads as input) are also confirmed byte-identical
before/after (TRUTH_DELTA.md §1; P06R3's fix touches no RNG-consuming code
path). **Every input `signatures.py` reads, and every target it is scored
against, is numerically unchanged. Re-running the pipeline would reproduce
the same `SIMULATED_signature_validation.md` byte-for-byte** (subject to the
same reproducibility guarantee `check_signatures_acceptance.py`'s
regenerate-and-diff criterion already checks) — there is nothing to gain
from re-running it, and Standing Rule 9 / this task's own "do not re-run
P07 or P08" instruction means it is not run here either way.

### 2b. Does the CONCLUSION drawn from P08-RERUN's own report need correcting?

Yes — separately from whether the pipeline needs re-running. P08-RERUN's
`ANALYTIC_VS_OBSERVED.md` §7 concluded: *"DDR_SIGNALING and NULL_ARM truth
is FAITHFUL; CORE_HR truth is NOT FAITHFUL... a P06 truth-definition
defect."* That conclusion was P08-RERUN's own HALT trigger (its Step 3
found "the analytic truth is not achievable from the observed
distributions" for CORE_HR specifically).

FIDELITY_AUDIT.md's rigorous re-test (exact-CDF binomial testing across 4
window widths, vs. P08-RERUN's narrow-window point-density approximation)
shows this specific claim does not hold: CORE_HR's SBS3 truth is faithful to
its generative distribution at the point actually evaluated, on the same
footing as DDR_SIGNALING (FIDELITY_AUDIT.md §3, §7). This is not a
consequence of any numeric change — TRUTH_DELTA.md §1 shows every truth
quantity is unchanged — it is a correction to how the (unchanged) numbers
should be interpreted.

**Practical consequence for a future task**: both CORE_HR's and
DDR_SIGNALING's gate6 FAILs should now be read as the same kind of failure —
genuine SigProfilerAssignment estimator instability at exome mutation
counts, Task K/P08's original "mechanism 2" (NNLS instability given SBS3's
real ~0.79 cosine similarity to SBS5), not a truth-definition artifact for
one arm and an estimator problem for the other. **This does not require
re-running `signatures.py`** (2a) — it requires a documentation correction
to P08-RERUN's own narrative artifacts (`ANALYTIC_VS_OBSERVED.md` §7,
`PROPOSED_DEVIATIONS.md`'s references to a CORE_HR-specific truth defect).
Per this task's own deliverable list and DO-NOT list, P06R3 does not itself
edit those files (they are not P06R3 deliverables, and rewriting another
session's already-committed report after the fact would violate the "never
hand-patch a generated report" principle applied elsewhere in this project)
— FIDELITY_AUDIT.md, TRUTH_DELTA.md, and this document are the correction of
record; a future task that touches P08-RERUN's artifacts directly should
cite them.

## 3. Summary table

| downstream task | re-run needed? | reasoning |
|---|---|---|
| P07 (`loh_caller.py`) | **NO** | its two in-scope quantities depend only on `WT_LOST_LINK`/`Z_MEAN`, untouched and unmoved by P06R3 (§1) |
| P08 pipeline (`signatures.py` re-run) | **NO** | every input and every gate6 target it reads is byte-identical before/after P06R3 (§2a) |
| P08-RERUN's narrative conclusion (`ANALYTIC_VS_OBSERVED.md` §7, `PROPOSED_DEVIATIONS.md`) | **YES — needs a documentation correction, not a re-run** | this task's audit overturns the specific "CORE_HR truth-definition defect" claim (§2b); a future task should update or annotate those documents accordingly |

## 4. HALT condition (this task's own)

*"If the joint-vs-naive ratio collapses toward 1 under corrected truth, stop
and report."* TRUTH_DELTA.md §1/§3 confirms `core_hr_joint_vs_marginal_inflation_ratio`
(0.0782) and `ddr_signaling_joint_vs_marginal_inflation_ratio` (0.2722) are
unchanged by P06R3's fix — neither collapsed toward 1 (neither was ever
close to 1 to begin with). **This HALT condition does not trigger.**

---

# Subtype fix addendum: does making `pam50_subtype` a genuine generative input invalidate P07 or P08?

SIMULATED: this section answers, with evidence, whether `loh_caller.py`
(P07) or `signatures.py` (P08 / P08-RERUN) need to be re-run against the
subtype fix (`SUBTYPE_MODEL.md`, `TRUTH_DELTA.md`'s subtype-fix addendum).
Per this task's explicit instruction, **neither is re-run from this
prompt** — this only determines whether either must be.

## Answer: YES for both — the presumption this task itself stated is confirmed correct

Unlike the P06R3 addendum above (where every target both P07 and P08 read
turned out byte-identical, so NO re-run was needed despite `simulate.py`
changing), **this fix genuinely moves the targets both P07 and P08 are
scored against**:

## 1. P07 (`loh_caller.py`)

`loh_caller.py`'s two in-scope quantities, `core_hr_wt_lost_direction_LR`
and `ddr_signaling_wt_lost_direction_LR`, are now the subtype-COLLAPSED
(prevalence-weighted mixture) values, not the old Z-only marginal.
`TRUTH_DELTA.md`'s subtype-fix addendum §1 confirms both moved:
`core_hr_wt_lost_direction_LR`: 4.480412 → 4.194289 (−6.39%);
`ddr_signaling_wt_lost_direction_LR`: 2.137349 → 2.084178 (−2.49%). Both
targets moved because `SUBTYPE_Z_SHIFT["Basal"] = 0.4` shifts Z for 18.28%
of the population, and `marginal_wt_lost_prob_collapsed()` is now a
genuine prevalence-weighted mixture over 5 subtype-conditional
probabilities rather than a single Z-only value. **P07's own gate6-scored
report (`SIMULATED_loh_validation.md`, `SIMULATED_RECOVERY_TABLE.tsv`)
was built and committed against the OLD targets — a fresh gate6 run
against the current `SIMULATED_TRUTH.tsv` would score against DIFFERENT
numbers than the ones that report describes.** `loh_caller.py`'s own
MECHANICS do not need to change (it never reads `pam50_subtype`, and
nothing about how it classifies LOH direction from read counts is
affected) — but its recovery SCORE against the new targets is unverified
until re-run.

## 2. P08 (`signatures.py`)

`signatures.py`'s gate6 targets, `core_hr_sbs3_exposure_LR` and
`ddr_signaling_sbs3_exposure_LR`, also moved: 5.644995 → 4.846995
(−14.14%) and 3.915723 → 3.672406 (−6.21%) respectively (`TRUTH_DELTA.md`
subtype-fix addendum §1). `SIMULATED_data/SIMULATED_signature_exposures.tsv`
and `SIMULATED_data/SIMULATED_mutation_catalogs.tsv` (the files
`signatures.py` reads as input) also changed on this run — subtype now
feeds `z` before the SBS3 draw (`_emit_sample()`), so every sample's
`sbs3_relative_exposure_true` value is regenerated with a (small, since
SBS3 has no direct subtype term) but real shift for Basal-like samples,
and the RNG stream order is unaffected (subtype was already drawn before
`z` in the pre-existing code, so no other draw shifted). **P08's own
committed report was built and committed against the OLD catalogue and
OLD targets — re-running would both regenerate different input data and
score against different numbers.**

## 3. Summary table

| downstream task | re-run needed? | reasoning |
|---|---|---|
| P07 (`loh_caller.py`) | **YES** | both in-scope targets moved (−6.39%, −2.49%); mechanics unaffected, but the SCORE against the new targets is unverified |
| P08 (`signatures.py`) | **YES** | both gate6 targets moved (−14.14%, −6.21%), AND the input catalogue/exposure files it reads also regenerated with real (if modest) changes |

## 4. HALT condition (this task's own)

*"If the joint-vs-naive ratio collapses toward 1 under the subtype-aware
model, stop and report."* `TRUTH_DELTA.md` subtype-fix addendum §3 confirms
`core_hr_joint_vs_marginal_inflation_ratio` moved 0.0782 → 0.1246 and
`ddr_signaling_joint_vs_marginal_inflation_ratio` moved 0.2722 → 0.3236 —
both move modestly AWAY from, not toward, 1 in absolute distance-from-1
terms is ambiguous to state cleanly since both are on the same side of 1
throughout (always < 1, moving from ~0.08/0.27 to ~0.12/0.32 — closer to 1
in raw distance, but still an order of magnitude away, not a collapse in
any practically meaningful sense: the naive estimator still overstates the
true joint LR by 8.0x and 3.1x respectively, down from 12.8x and 3.7x).
**This HALT condition does not trigger** — neither ratio approaches 1
closely enough to call the correlation structure this project's joint
model depends on "gone."
