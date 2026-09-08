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
