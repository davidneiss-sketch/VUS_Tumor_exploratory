Not a SIMULATED artifact: this memo analyzes real, non-simulated external
data (live-retrieved where retrieval succeeded, `EGRESS_BLOCKED`/
`UNVERIFIED` disclosed where it did not) against this project's own
pre-registered design and against `SIMULATED` characterization work
(GATE8's instability sweep) already on disk. No ACMG evidence, LR, or
Stage 1/2 vocabulary is assigned to anything here. **Analysis and memo
only. Nothing in the pipeline changes. No design is chosen — that
decision is the human's, per this task's explicit HALT.**

# BRCA_POOLED_FEASIBILITY.md — does collapsing subtype rescue a per-gene BRCA1/BRCA2 LR at TCGA-BRCA scale?

## STEP 1 — the primary number

Method, held identical to `FEASIBILITY_MEMO.md` (P-FEAS-1) for direct
comparability: `required_total_cohort_N = target_class_size /
(purity_survival_at_0.40 x gene_case_prevalence)`, with the SAME Hu et
al. 2021 NEJM (CARRIERS consortium, population-based, 32,247 cases/
32,544 controls) per-gene prevalence (BRCA1 0.85%, BRCA2 1.29%) and the
SAME GATE8 dimension-3 (full feature vector) brackets (n=65/class
majority-informative, n=160/class fully-informative) used there. The
only change: **`subtype_fraction` is dropped (pooled = 100% of the
cohort)**, and `purity_survival_at_0.40` uses the POOLED (not per-
subtype) TCGA-BRCA figure: 794/951 = 83.49% (`PURITY_FLOOR_COST.md`,
unchanged, not re-derived).

| gene | prevalence | required N, n=65 bracket | required N, n=160 bracket |
|---|---|---|---|
| BRCA1 | 0.85% | **9,159** | **22,546** |
| BRCA2 | 1.29% | **6,035** | **14,856** |

**Against the two available cohort figures** (expected post-0.40-floor
carrier count, i.e. what TCGA-BRCA/the combined ceiling actually
delivers, computed the same way — `expected = N x purity_survival x
prevalence`):

| gene | expected carriers, TCGA-BRCA alone (N=951) | expected carriers, combined pre-harmonization ceiling (N=1,663) |
|---|---|---|
| BRCA1 | **6.75** | **11.80** |
| BRCA2 | **10.24** | **17.91** |

**Verdict, stated plainly: neither bracket is reached by either cohort
figure, for either gene.** Even the more permissive target (n=65,
majority-informative — itself a weaker promise than "reliably
informative," per `FEASIBILITY_MEMO.md`'s own disclosed caveat) needs
6,035–9,159 total patients; TCGA-BRCA alone offers 951 and the combined
(pre-harmonization, real-cohort) ceiling offers 1,663 — a shortfall of
roughly **5.6–9.6x at TCGA-BRCA scale, 3.6–5.5x at the combined
ceiling**, for the two best-characterized, highest-prevalence genes in
this project's entire CORE_HR/DDR_SIGNALING list. Pooling subtype away
narrows the gap from `FEASIBILITY_MEMO.md`'s 3–4-order-of-magnitude
shortfall for the per-subtype design down to roughly one order of
magnitude — a real improvement, but **still a NOT VIABLE verdict at
either cohort figure, at either bracket.**

## STEP 2 — sensitivity of the verdict to the GATE8 threshold

`INTERVAL_INSTABILITY.md`'s own headline finding is that the gate8-
rejection rate is non-monotonic in n and that reporting one clean
threshold misstates the shape. At `FEASIBILITY_MEMO.md`'s 100K–5M-patient
gaps for PALB2/RAD51C/RAD51D, this did not matter — no bracket choice in
the tested range could have closed a gap that large. Here, the gap is
roughly one order of magnitude, so it is worth checking directly.

**Required N is linear in the target class size** (`required_N(n) = n /
(purity_survival x prevalence)`), so the exact "flip point" — the target
class size at which 951 or 1,663 exactly suffices — is computable without
restricting to the two named brackets:

| gene | flip-point n vs. TCGA-BRCA alone (951) | flip-point n vs. combined ceiling (1,663) |
|---|---|---|
| BRCA1 | **6.75** | **11.80** |
| BRCA2 | **10.24** | **17.91** |

At face value this looks like it could matter — these flip points (6.75–
17.91) are well below the 65/160 brackets used in Step 1, and inside
`INTERVAL_INSTABILITY.md`'s own tested sweep range (n=12–160/class).
**But checking the actual empirical informative RATE at those n, from
the same sweep (dimension-3, full feature vector, both arms),
shows the flip point is not a rescue:**

| n (class size) | CORE_HR dim-3 informative/15 | DDR_SIGNALING dim-3 informative/15 |
|---|---|---|
| 12 | 0/15 (10 UNINFORMATIVE, 5 `ZERO_DENSITY_UNDEFINED`) | 0/15 (14 UNINFORMATIVE, 1 `ZERO_DENSITY_UNDEFINED`) |
| 15 | 0/15 | 0/15 |
| 20 | 0/15 | 0/15 |
| 25 | 0/15 | 0/15 |
| 30 | 1/15 (6.7%) | 0/15 |

**Every flip point computed above (6.75–17.91) falls inside the n≤25
region where this simulator's own characterization shows a 0% empirical
informative rate for the full feature vector, in both arms** — the
estimator does not merely produce a wide interval at these class sizes,
it produces `UNINFORMATIVE` or outright `ZERO_DENSITY_UNDEFINED`
(no computable number at all) in every single one of the 15 independent
trials tested at n≤25. The first ANY-trial-informative result in the
whole sweep does not appear until n=30 (CORE_HR only, 1/15), still far
below even the 65-bracket used in Step 1.

**The threshold value at which the verdict would flip from NOT VIABLE
to VIABLE does not exist within the plausible/tested range.** Restating
it precisely: reaching "flip-point n" (i.e., TCGA-BRCA or the combined
ceiling delivering enough carriers to equal the target) is NECESSARY but
is nowhere near SUFFICIENT, because at every n at or below the computed
flip points, GATE8's own empirical characterization shows the estimator
essentially never produces an informative interval regardless of how
many carriers happen to land there. **The verdict is NOT sensitive to
the choice of bracket** in the sense the task worried about — not
because the brackets don't matter in principle, but because both
available cohort figures fall so far below where this simulator's own
sweep ever shows informativeness (n≥30 for even a single trial, n≥65
for a majority) that no defensible choice of "informative" threshold
within the empirically-characterized range flips the verdict. This
finding is itself only as strong as `INTERVAL_INSTABILITY.md`'s
15-repeats-per-cell sweep (not re-run this task) and does not extend
past n=160, which is not relevant here since the flip points sit at the
opposite end of the tested range.

## STEP 3 — the purity floor trade at BRCA1/BRCA2 pooled scale

Applying `FEASIBILITY_MEMO.md`'s floor-vs-survival trade (0.25/0.30/
0.35/0.40, POOLED figures from `PURITY_FLOOR_COST.md`) to the pooled
per-gene requirement:

| Floor | Pooled survival | Required N, BRCA1, n=65 | Required N, BRCA2, n=65 |
|---|---|---|---|
| 0.25 | 96.2% (915/951) | 7,948 | 5,237 |
| 0.30 | 92.6% (881/951) | 8,255 | 5,439 |
| 0.35 | 88.6% (843/951) | 8,627 | 5,684 |
| **0.40** | **83.5% (794/951)** | **9,159** | **6,035** |

Lowering the floor from 0.40 to 0.25 buys back only **~13% more surviving
patients** (794→915) — a required-N reduction of at most ~1,200 (BRCA1)
or ~800 (BRCA2). **No crossover exists in this range**: even lowering
the floor to a hypothetical 0.0 (100% survival, no purity filtering
whatsoever — the best case physically available, and one this project
has independently established as unreliable for the LOH caller below
~0.30–0.35, `PROPOSED_DEVIATIONS.md` §10) still requires 7,647 (BRCA1)
or 5,039 (BRCA2) total patients — both figures remain **4.6–5.3x above**
TCGA-BRCA alone (951) and **2.9–3.3x above** the combined ceiling
(1,663). **The binding constraint here is gene prevalence, not the
purity floor.** Relaxing the floor is a ~13–17% lever on a problem that
needs a 5–9x lever; it cannot close this gap at any value in the
plausible range, and doing so would also trade away the LOH-caller
accuracy `P07-RERUN2`/`FEASIBILITY_MEMO.md` already quantified (96.6%→
71.4% pooled, marginal-band accuracy, floor 0.40→0.25) for no
compensating feasibility gain.

## STEP 4 — the reference-set constraint

**BLOCKED this session — reported per Standing Rule 3/4/8, not
estimated.** Retrieving live ClinVar BRCA1/BRCA2 variant counts at
`PROTOCOL.md` §4.1's ≥2-star floor
(`criteria_provided,_multiple_submitters,_no_conflicts` or
`reviewed_by_expert_panel`), split P/LP vs. B/LB, and then applying
§4.2's gnomAD popmax ≤0.01 ceiling to the B/LB set, required live access
this session was unable to obtain. Every avenue attempted this task
failed identically:

| domain/service | mechanism attempted | result |
|---|---|---|
| `eutils.ncbi.nlm.nih.gov` (ClinVar E-utilities) | direct `curl` | `connect_rejected`, gateway 403 to CONNECT |
| `eutils.ncbi.nlm.nih.gov` | `WebFetch` | `EGRESS_BLOCKED` |
| `clinicaltables.nlm.nih.gov` | direct `curl` | `connect_rejected`, gateway 403 |
| `rest.ensembl.org` | direct `curl` | `connect_rejected`, gateway 403 |
| `myvariant.info` | direct `curl` | `connect_rejected`, gateway 403 |
| `clinvarminer.genetics.utah.edu` (third-party ClinVar aggregator, not an NCBI domain) | `WebFetch` | `EGRESS_BLOCKED` |
| `github.com/BRCAChallenge/brca-exchange` (GitHub-hosted BRCA variant curation project — GitHub domains are otherwise reachable this session, per `P-FIX-2`/`FEASIBILITY_MEMO.md`'s established mirror technique) | `WebFetch` (repo + releases page) | reachable, but the aggregated variant-classification-count data is not committed as a raw file in the GitHub tree (the repo is pipeline code; the built data releases are external downloads) — no count extractable this way |
| WebSearch (general) | search synthesis | surfaced only qualitative/older context (e.g. "450 BRCA1 missense variants with conflicting interpretations as of Dec 2022" — a different, non-matching cut of the data, not the ≥2-star P/LP vs. B/LB split this protocol needs); no current, gene-specific, review-status-stratified count found |

**This is a policy-level network egress block, the same mechanism
`P-FIX-2`/`FEASIBILITY_MEMO.md` already documented for general-web
domains, now confirmed to also cover ClinVar's own API/web domains and
every third-party ClinVar-mirroring service attempted.** Per Standing
Rule 3, no BRCA1/BRCA2 P/LP or B/LB variant count, and no gnomAD-popmax-
matched benign class size, is reported here — every such number would
have to be invented to fill this section, and this memo does not do
that. **Both class sizes are UNVERIFIED.**

**This means Step 4's own conditional cannot be evaluated this session:
whether the frequency-matched benign class (rather than carrier counts)
is the binding constraint is unresolved, not answered "no."** This is
itself worth stating plainly (Standing Rule 8): this project has
never, at any point across its history recorded in this repository,
confirmed that a frequency-matched benign reference class of adequate
size exists for BRCA1 or BRCA2 under `PROTOCOL.md` §4.1/§4.2's own
stated floor and ceiling. Step 1's carrier-count shortfall is a
*necessary*-condition failure already established; whether the
reference-set constraint would ALSO independently fail, or would bind
even more tightly, remains open. A future session with unblocked
ClinVar/Ensembl/myvariant.info egress (or a different access path this
session did not locate) should resolve this before either constraint is
treated as fully characterized.

## STEP 5 — what the narrowed study would be, conditional on Steps 1 and 4 both clearing

**Step 1 does not clear** (Step 1/2/3 above: NOT VIABLE at either
bracket, either cohort figure, any floor in the tested range) **and
Step 4 is BLOCKED, not cleared.** Neither precondition for this section
currently holds. The following is reported as a conditional/hypothetical
— what would remain to be done IF a materially larger cohort became
available (e.g. the unconfirmed 1,364-genome 2025 cohort
`FEASIBILITY_MEMO.md` §2b flagged) AND Step 4's ClinVar/gnomAD retrieval
were later completed and cleared — per this task's own instruction to
state it regardless:

- **Calibration of tumor-derived evidence for BRCA1/2 germline
  classification in breast cancer** — extending the ENIGMA ovarian-
  cancer pathology-LR precedent (`BENCHMARKS.tsv` `ENIGMA01`/`ENIGMA02`)
  to a new tumor type (breast) and a new assay (this project's LOH/GIS/
  SBS3 tumor-derived evidence, rather than pathology features) would
  remain the core, still-novel contribution.
- **The exome-versus-array HRD calibration** remains an independent
  contribution regardless of the per-gene LR question's outcome — it
  does not depend on carrier class size in the same way and was not
  costed by this memo or `FEASIBILITY_MEMO.md`.
- **Whether subtype survives as a covariate at this scale, or must be
  dropped entirely**, would need to be re-examined empirically once a
  larger cohort exists — this memo's own Step 1 finding (pooling
  narrows but does not close the gap even fully collapsed) suggests
  subtype-as-covariate (`FEASIBILITY_MEMO.md` Design B) is already the
  closest-to-feasible option among the three designs previously laid
  out, and a materially larger cohort would be the more natural lever
  to add subtype back in as a covariate than to add it back as a full
  stratum.

## STEP 6 — draft negative-result text for REPORT.md (NOT APPLIED)

Per Standing Rule 10, drafted only; `REPORT.md` is not edited by this
task (and its own closing note already states its scope "ends here" as
of the P-AMD-3a/3b deviation entries — any future insertion is a human
editorial decision, not made here).

> **Negative result: tumor-derived LR calibration for moderate/high-
> penetrance HRR genes in breast cancer is not achievable at any cohort
> scale that exists outside a large biobank, and the genes with the
> greatest clinical need are the ones this constraint bites hardest.**
> `FEASIBILITY_MEMO.md` established that the pre-registered per-gene x
> PAM50-subtype design cannot be supported by TCGA-BRCA, ICGC/PCAWG
> breast, or CPTAC-3 breast, combined or alone — the shortfall for
> PALB2, RAD51C, and RAD51D (the genes with the greatest unmet clinical
> need, per this project's own framing) is 3–4 orders of magnitude even
> at the most permissive informativeness bracket tested. This memo
> (`BRCA_POOLED_FEASIBILITY.md`) shows that even collapsing PAM50
> subtype entirely — giving up the design's own primary subtype-
> stratified claim — does not rescue the two best-characterized,
> highest-prevalence genes in this gene list, BRCA1 and BRCA2: a
> ~5.6–9.6x shortfall remains at TCGA-BRCA scale, and the verdict is
> robust to the specific informativeness threshold chosen, because the
> shortfall's flip point falls inside a region this project's own GATE8
> characterization already shows is empirically non-informative in
> every tested trial. **This is a structural result about tumor-derived
> genomic evidence for moderate-penetrance HRR genes generally, not an
> artifact of this project's specific estimator, gate thresholds, or
> purity floor**: the purity-floor trade (Step 3 above) shows the
> binding constraint is gene carrier prevalence, not the purity floor
> or the estimator's own class-size sensitivity, and relaxing either
> lever by the largest defensible amount closes at most a fraction of
> the gap. A study of this design, for these genes, requires a cohort
> at the scale of a national or international cancer biobank (tens of
> thousands to low millions of patients depending on gene and
> subtype-stratification choice), not a single consortium cohort or
> even several combined. This is a useful, reportable finding for the
> field in its own right — a quantified statement of what scale of
> resource tumor-derived HRR-gene calibration actually requires — and
> should be reported as a primary finding, not buried as a limitations-
> section caveat.

---

**HALT, per this task's own explicit instruction: the design decision is
the human's. No design is chosen above. `simulate.py`, `PROTOCOL.md`,
every gate, and every other pipeline file are unmodified by this task —
confirmed by checksum verify (see commit). P07, P08, and P09 were not
re-run.**
