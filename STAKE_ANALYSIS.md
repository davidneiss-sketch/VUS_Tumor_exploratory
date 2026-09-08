SIMULATED DATA — NOT A SCIENTIFIC RESULT

# STAKE_ANALYSIS.md — how much does the gate6 SBS3 FAIL actually matter?

SIMULATED: this quantifies the stakes of P06R3's finding (gate6 FAILs on
both SBS3 quantities against a truth now confirmed faithful) before any
decision is made about it. Per this task's explicit instruction, **no
recommendation is offered**. This document does not decide anything;
`scripts/check_stake_acceptance.py` scores its deliverables against the
ACCEPTANCE criteria below.

---

## STEP 0 — does PROTOCOL.md already decide this?

**Partially. It pre-specifies what happens when the pipeline as a whole is
uncalibrated, and what happens to an individual out-of-scope outcome — it
does not pre-specify what happens when one feature inside an otherwise
computable joint vector proves specifically hard to recover while the
others do not.** Quoting PROTOCOL.md §10 in full, the passage closest to
"what happens when a feature proves uninformative":

> **If Stage 2 (§11) returns mostly `SIMULATED_FAIL`:** interpreted as "the
> LR-estimation pipeline is not adequately calibrated to trust on real
> data." Consequence, fixed now: **Stage 1 (§10.1, real-data) results may
> not be reported as reliable, and no ACMG mapping (§9) may be issued from
> them, until Stage 2 passes** (a majority of tested strata return
> `SIMULATED_PASS`, with none of the gene-group-level primary strata
> failing). This is a hard gate on the order of operations, fixed here
> before any Stage 1 result exists.

This is an **aggregate, stage-level** rule (does the whole pipeline pass
enough of its recovery tests to be trusted at all), not a **feature-level**
rule (what happens to the joint LR, or to Stage 1 reporting, when one named
feature — SBS3 — specifically and consistently fails recovery while another
named feature — LOH direction — specifically and consistently passes).
Applying the literal aggregate rule to what has actually been tested in this
project to date: of the 4 `SIMULATED_TRUTH.tsv` quantities any tool in this
project has ever attempted to recover (`core_hr_wt_lost_direction_LR` /
`ddr_signaling_wt_lost_direction_LR`, both `SIMULATED_PASS`;
`core_hr_sbs3_exposure_LR` / `ddr_signaling_sbs3_exposure_LR`, both
`SIMULATED_FAIL`), that is a 2-of-4 split, not "mostly `SIMULATED_FAIL`" —
so §10's aggregate gate, read literally, does not currently block Stage 1
on this basis (Stage 1 is independently blocked anyway: Track B is
unauthorized and `GATE1.json` is FAIL, per §10.1). GIS recovery, joint-LR
recovery, and NULL_ARM recovery have never been implemented by any tool in
this project (`SIMULATED_RECOVERY_TABLE.tsv` marks all three `BLOCKED`/
`NOT_IN_SCOPE`), so they cannot even enter this tally.

**PROTOCOL.md §7.1 separately, structurally, commits to always reporting
every per-feature LR and the joint LR together** ("For each feature
independently, and for the joint feature vector, the LR is estimated...");
it does not describe a feature-selection, feature-exclusion, or feature-
reweighting mechanism triggered by one feature's recovery performance. The
protocol's only other outcome vocabulary — `NO_EVIDENCE` (a CI spanning the
null), `INSUFFICIENT_N` (an untestable stratum), `BLOCKED` (a tool
unavailable) — describes what to print for a *result*, not a rule for
deciding whether to *include a feature in the joint estimator in the first
place*.

**This silence is logged as a finding in `PROPOSED_DEVIATIONS.md`** (this
task's own instruction: "A pre-registration that did not anticipate an
uninformative feature is itself a finding"). Per Standing Rule 10, that
entry is a *proposal*, not an amendment — `PROTOCOL.md` is not modified by
this task.

---

## STEP 1 — ablation on synthetic data (full n)

Implemented `stake_ablation.py` (new file, does not modify `simulate.py`,
`signatures.py`, `loh_caller.py`, or `PROTOCOL.md`): PROTOCOL.md §7.1's own
pre-registered estimator — Gaussian KDE for continuous features (GIS, SBS3),
Jeffreys `+0.5`-corrected empirical proportion for the categorical feature
(LOH/WT_LOST direction), joint LR as the product of per-feature LRs
(conditional-independence assumption, exactly as §7.1 specifies — this is
**not** the simulator's true latent-integrated joint density; PROTOCOL's own
pre-registered estimator is the naive product, so that is what is ablated
here) — applied to the full existing synthetic population
(`SIMULATED_data/`, `SIMULATED_TRUTH_detail/`; NULL_ARM excluded, it is not
one of PROTOCOL's own gene groups), evaluated at the same fixed
`EVAL_POINT` used throughout this project (`wt_lost=1, gis=42.0, sbs3=0.30`),
with a patient-clustered percentile bootstrap CI (B=2000 per PROTOCOL §7.3,
reduced to B=500 at the full 1848-per-class synthetic n only, for
tractability in this stdlib-only, no-numpy environment — disclosed, not
silent). Full numbers: `ABLATION_TABLE.tsv`, rows with
`n_scenario=SYNTHETIC_FULL_N`.

| arm | feature set | point est. | 95% CI | ACMG tier (pts) |
|---|---|---|---|---|
| CORE_HR | {LOH, GIS, SBS3} | 101.24 | [71.27, 158.67] | `PATHOGENIC_STRONG` (4) |
| CORE_HR | {LOH, GIS} — SBS3 dropped | 14.69 | [11.81, 17.93] | `PATHOGENIC_MODERATE` (2) |
| CORE_HR | {LOH, SBS3} — GIS dropped | 30.10 | [22.41, 42.56] | `PATHOGENIC_STRONG` (4) |
| CORE_HR | {GIS, SBS3} — LOH dropped | 23.19 | [17.14, 33.51] | `PATHOGENIC_MODERATE` (2) |
| DDR_SIGNALING | {LOH, GIS, SBS3} | 19.95 | [14.10, 28.59] | `PATHOGENIC_MODERATE` (2) |
| DDR_SIGNALING | {LOH, GIS} — SBS3 dropped | 5.47 | [4.53, 6.75] | `PATHOGENIC_MODERATE` (2) |
| DDR_SIGNALING | {LOH, SBS3} — GIS dropped | 8.16 | [6.46, 11.00] | `PATHOGENIC_MODERATE` (2) |
| DDR_SIGNALING | {GIS, SBS3} — LOH dropped | 8.91 | [6.91, 12.47] | `PATHOGENIC_MODERATE` (2) |

### HEADLINE — strength delta from dropping SBS3, full synthetic n

- **CORE_HR: NOT free. CI lower bound 71.27 → 11.81, crossing the
  strong/moderate boundary (18.7). `PATHOGENIC_STRONG` (4 points) →
  `PATHOGENIC_MODERATE` (2 points), a 2-point ACMG evidence loss.**
- **DDR_SIGNALING: nearly free at this stratification level.** CI lower
  bound 14.10 → 4.53, both inside the `PATHOGENIC_MODERATE` band (4.33,
  18.7]. The point estimate and CI both shrink substantially, but the
  assigned tier does not change.

The two primary gene-group strata disagree with each other on whether
dropping SBS3 matters. It is CORE_HR, not DDR_SIGNALING, where the tier
actually moves — worth noting since the task's own worked hypothesis in
Step 3 ("SBS3 should contribute most in basal-like... where baseline HRD is
low") is about *subtype*, not gene group; the gene-group-level result here
is a separate axis from that hypothesis (see Step 3).

---

## STEP 2 — realistic class sizes (BENCHMARKS.tsv-derived)

**Realistic n, from `SIMULATION_SPEC.md` §6 (itself derived from
`BENCHMARKS.tsv` `BRCA_PREV01` (Yost et al. 2019) and `DDR_PREV01` (Couch et
al. 2017), extrapolated to a ~1097-patient TCGA-BRCA-scale cohort — not
re-derived here, the existing citation and arithmetic are reused verbatim):
CORE_HR pathogenic-class n ≈ 55–75; DDR_SIGNALING pathogenic-class n ≈
25–35.** Benign-class n has **no published citation anywhere in
`BENCHMARKS.tsv`** — this ablation sets it equal to the pathogenic-class
target as a disclosed, **uncited assumption** (Standing Rule 3: this is
explicitly not a retrieved value). Both endpoints of each range are run.
Full numbers: `ABLATION_TABLE.tsv`, rows with `n_scenario` starting
`REALISTIC_N_`.

**Not every stratum returns `INSUFFICIENT_N` at realistic n** — combined
class size clears PROTOCOL.md §8's `n ≥ 20` floor at every realistic-n
scenario tested here (CORE_HR: 110 or 150 combined; DDR_SIGNALING: 50 or
70 combined) at the gene-group level. **But this is not the reassuring
result it sounds like — the more important finding is that the ESTIMATOR
ITSELF becomes badly unstable at these sizes, in a way that can produce a
dangerously overconfident ACMG call from noise:**

| arm | feature set | n_scenario | point est. | 95% CI | ACMG tier |
|---|---|---|---|---|---|
| DDR_SIGNALING | {LOH, GIS, SBS3} | REALISTIC_N_35 (n=35/class) | **11016.6** | **[759.6, 3.65 BILLION]** | `PATHOGENIC_VERY_STRONG` (8) |
| DDR_SIGNALING | {LOH, GIS} — SBS3 dropped | REALISTIC_N_35 | 15.3 | [5.53, 193.8] | `PATHOGENIC_MODERATE` (2) |

**Mechanism, verified directly (not asserted):** at n=35/class, DDR_SIGNALING
Benign's SBS3 values are heavily zero-inflated (per `FIDELITY_AUDIT.md`'s
own clip-mechanism finding) with a Silverman bandwidth of ≈0.046 at this n.
`EVAL_POINT["sbs3"]=0.30` is ~6.6 bandwidths from the zero cluster and past
the largest nonzero value seen in a typical 35-sample draw. On a bootstrap
resample where, by chance, none of the resampled Benign values fall near
0.30, the Gaussian-kernel density there decays exponentially toward zero,
inflating that replicate's LR by orders of magnitude. Directly inspecting
the B=2000 bootstrap distribution for this exact cell: median ≈62.6, but
the 99.9th percentile is ≈32.5 million and the maximum replicate is
≈38.1 million (a separate run against a fixed rng seed produced a CI upper
bound over 3 billion — the exact value is itself unstable across reruns,
which is the point). **A CI lower bound of 759.6, alone, would be read as
`PATHOGENIC_VERY_STRONG` (8 ACMG points, the maximum tier) by PROTOCOL.md
§9's rule applied exactly as written — from an estimator whose own
bootstrap distribution has a multi-order-of-magnitude-heavier right tail
than its median, driven by a small handful of degenerate resamples, not by
genuine precision.** This is reported as a finding about the pre-registered
Section 7.1 estimator's behavior at realistic n, per Standing Rule 10 — not
fixed, capped, or reweighted by this task, and no protocol amendment is
applied.

The DDR_SIGNALING n=25 cell shows the same effect in the other, more
directly SBS3-relevant direction:

| arm | feature set | n_scenario | ACMG tier |
|---|---|---|---|
| DDR_SIGNALING | {LOH, GIS, SBS3} | REALISTIC_N_25 | `PATHOGENIC_SUPPORTING` (1) |
| DDR_SIGNALING | {LOH, GIS} — SBS3 dropped | REALISTIC_N_25 | `NO_EVIDENCE` (0) |

Here dropping SBS3 **is** consequential (crosses the supporting/no-evidence
threshold) — the opposite conclusion from the same gene group's full-
synthetic-n result (Step 1: "nearly free" for DDR_SIGNALING). **The
strength-delta answer for DDR_SIGNALING flips sign between synthetic n and
realistic n** — at tight synthetic CIs, SBS3 was redundant with LOH+GIS; at
loose realistic-n CIs, SBS3's presence or absence can be the difference
between `PATHOGENIC_SUPPORTING` and `NO_EVIDENCE`, though per the mechanism
above, some of these realistic-n CI endpoints should be read with
considerable caution given the demonstrated instability.

CORE_HR's realistic-n results are qualitatively consistent with its
synthetic-n result (SBS3 drop crosses `STRONG`→`MODERATE` at both n=55 and
n=75), without the extreme-outlier pathology seen for DDR_SIGNALING —
CORE_HR's SBS3 marginal distributions are further from the zero clip
boundary (Pathogenic mean 0.33, Benign mean 0.03) than DDR_SIGNALING's
(Pathogenic mean 0.184, Benign mean 0.08), giving somewhat more bootstrap
stability, though CORE_HR n=55's CI still spans [56, 42041] — also very
wide.

---

## STEP 3 — stratify by subtype

**Structural finding, established from the code, not from the numbers
below: `simulate.py`'s `pam50_subtype` is drawn independently of every
class-conditional feature.** `subtype = rng.choices(list(PAM50_PROPORTIONS),
...)` is computed from a fixed, class-independent, arm-independent
multinomial and is never read by any of `z = rng.gauss(...)`,
`draw_category_and_mechanism()` (LOH/WT_LOST direction), or the
`gis`/`sbs3` draws. **By construction, subtype is statistically independent
of `true_class`, `wt_lost`, `gis`, and `sbs3` in this simulator — no
subtype-dependent SBS3 signal of the kind the task's own hypothesis
describes ("SBS3 should contribute most in basal-like... where baseline HRD
is low") can exist in this synthetic data, regardless of what the
per-subtype numbers below show.** This is reported prominently because
without it, an apparent subtype pattern in the table below could be
misread as biological signal when it is a construction artifact plus
sampling noise from smaller per-cell n.

**Second structural finding: `simulate.py`'s `PAM50_PROPORTIONS` has only 4
categories** (LumA, LumB, HER2E, Basal) — **it never generates a
"Normal-like" sample at all**, while `PROTOCOL.md` §8 explicitly names
Normal-like as a sixth/fifth stratification category. Every
`SYNTHETIC_SUBTYPE_Normal-like` row in `ABLATION_TABLE.tsv` has n=0 (not
merely n<20) — a simulator/protocol stratification-scheme mismatch, not
sampling variability. Logged as an additional finding for
`PROPOSED_DEVIATIONS.md`.

Ablation at synthetic n, by subtype (full `ABLATION_TABLE.tsv` has the CIs
and point estimates; tier-change summary here):

| arm | subtype | n (Path/Benign) | full-set tier | drop-SBS3 tier | tier changed? |
|---|---|---|---|---|---|
| CORE_HR | LumA | 845/809 | `PATHOGENIC_STRONG` | `PATHOGENIC_MODERATE` | YES |
| CORE_HR | LumB | 461/430 | `PATHOGENIC_STRONG` | `PATHOGENIC_MODERATE` | YES |
| CORE_HR | HER2E | 214/242 | `PATHOGENIC_STRONG` | `PATHOGENIC_MODERATE` | YES |
| CORE_HR | Basal | 328/367 | `PATHOGENIC_STRONG` | `PATHOGENIC_MODERATE` | YES |
| CORE_HR | Normal-like | 0/0 | `INSUFFICIENT_N` | `INSUFFICIENT_N` | n/a |
| DDR_SIGNALING | LumA | 783/851 | `PATHOGENIC_MODERATE` | `PATHOGENIC_SUPPORTING` | YES |
| DDR_SIGNALING | LumB | 470/443 | `PATHOGENIC_MODERATE` | `PATHOGENIC_SUPPORTING` | YES |
| DDR_SIGNALING | HER2E | 225/203 | `PATHOGENIC_MODERATE` | `PATHOGENIC_SUPPORTING` | YES |
| DDR_SIGNALING | Basal | 370/351 | `PATHOGENIC_MODERATE` | `PATHOGENIC_SUPPORTING` | YES |
| DDR_SIGNALING | Normal-like | 0/0 | `INSUFFICIENT_N` | `INSUFFICIENT_N` | n/a |

**The task's specific hypothesis (basal-like most SBS3-dependent, ER+/HER2-
least) cannot be tested by this data — every testable subtype shows the
same tier change for a given arm** (CORE_HR: STRONG→MODERATE in all 4;
DDR_SIGNALING: MODERATE→SUPPORTING in all 4), consistent with the
structural finding above: there is no subtype-conditional mechanism in this
simulator to produce a differential effect. **The one real finding here is
different from the hypothesized one: for DDR_SIGNALING, stratifying by
subtype ALONE — with no biological subtype-SBS3 relationship at all, purely
through reduced per-cell n (roughly 350–850/class vs. 1848/class pooled) —
flips the SBS3 strength delta from "nearly free" (Step 1, pooled) to "a
real one-point ACMG loss" in every subtype cell.** Stratification itself,
independent of any subtype-specific biology, changes the stakes.

---

## STEP 4 — how much real data is even in range

**BLOCKED, for two independent reasons, neither of which is a decision
this task is making — both are logged per Standing Rule 4/8.**

**1. The stated precondition does not exist.** This step's instruction
begins "From the Track A open-access TCGA-BRCA somatic MAFs already
assembled in P10" — no task named or numbered "P10" appears anywhere in
this repository's git history (`git log --all --oneline`, 19 commits total,
checked in full — the closest prior real-data step is `TRACK.md`'s original
declaration that Track A is *reachable*, explicitly followed by "This
session does **not** decide which... path the next task takes" and no
Track-A retrieval since). No TCGA-BRCA MAF file of any kind exists in this
repository outside `docker/sigma-src/` (the third-party SigMA R package's
own bundled example/test data, `tcga_mc3_brca.maf` and
`test_mutations_50sample.maf` — vendor example fixtures for demonstrating
SigMA's API, not this project's own retrieved, cited, provenance-tracked
Track A dataset, and not treated as a substitute here per Standing Rule 4:
"never substitute silently").

**2. Live retrieval, attempted as the resourceful alternative, is also
blocked.** `TRACK.md` establishes Track A (GDC open-access TCGA-BRCA) is
reachable with no authorization gate, so this session attempted a live,
first-hand retrieval to fulfill this step's actual intent rather than stop
at (1) alone. Two independent mechanisms confirm the attempt is blocked by
this session's own network egress policy, not by GDC:

```
$ curl -sS -m 15 https://api.gdc.cancer.gov/status
curl: (56) CONNECT tunnel failed, response 403
$ curl -sS "$HTTPS_PROXY/__agentproxy/status"
  ... "recentRelayFailures": [{"kind": "connect_rejected",
      "detail": "gateway answered 403 to CONNECT (policy denial or
      upstream failure)", "host": "api.gdc.cancer.gov:443"}] ...
```

WebFetch (a second, independent retrieval path) against the same URL:

```
{"error_type":"EGRESS_BLOCKED","domain":"api.gdc.cancer.gov",
 "message":"Access to api.gdc.cancer.gov is blocked by the network
 egress proxy."}
```

**No fraction of real TCGA-BRCA tumors below the SBS3-recoverability
threshold is reported, because no real mutation-count distribution was
retrieved.** Standing Rule 3 ("Otherwise write UNVERIFIED and stop") and
Standing Rule 4 ("never substitute silently... stop that branch") both
apply directly. This step is `UNCHECKED`/`BLOCKED`, not answered — per the
task's own framing, this may well have been "the most important finding in
this session," and its absence is reported with the same prominence as
every completed step (Standing Rule 8), not folded into a footnote.

---

## Summary table required by ACCEPTANCE (strength delta, one line per stratum)

| stratum | n regime | strength delta from dropping SBS3 |
|---|---|---|
| CORE_HR (gene-group) | synthetic full (n=3696) | REAL: STRONG(4)→MODERATE(2) |
| CORE_HR (gene-group) | realistic n=55 | REAL: STRONG(4)→MODERATE(2), but CI extremely wide at both ends |
| CORE_HR (gene-group) | realistic n=75 | REAL: STRONG(4)→MODERATE(2), CI wide |
| DDR_SIGNALING (gene-group) | synthetic full (n=3696) | NEARLY FREE: MODERATE(2)→MODERATE(2) |
| DDR_SIGNALING (gene-group) | realistic n=25 | REAL: SUPPORTING(1)→NO_EVIDENCE(0) |
| DDR_SIGNALING (gene-group) | realistic n=35 | REAL: VERY_STRONG(8)→MODERATE(2) — but the VERY_STRONG endpoint is itself estimator-instability-driven (see Step 2), not read at face value |
| CORE_HR × LumA/LumB/HER2E/Basal | synthetic, per-subtype | REAL in all 4: STRONG(4)→MODERATE(2) |
| CORE_HR × Normal-like | synthetic, per-subtype | UNTESTABLE (n=0, simulator never generates this subtype) |
| DDR_SIGNALING × LumA/LumB/HER2E/Basal | synthetic, per-subtype | REAL in all 4: MODERATE(2)→SUPPORTING(1) |
| DDR_SIGNALING × Normal-like | synthetic, per-subtype | UNTESTABLE (n=0, simulator never generates this subtype) |
| Real-data fraction below SBS3-recoverability threshold | Track A, TCGA-BRCA | `BLOCKED` — Step 4, no data retrieved (see above) |

No recommendation is made anywhere in this document.
