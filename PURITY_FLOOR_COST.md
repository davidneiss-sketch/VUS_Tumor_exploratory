SIMULATED DATA — NOT A SCIENTIFIC RESULT (this document is a feasibility
analysis of real, non-simulated TCGA-BRCA reference data; no ACMG
evidence, LR, or any Stage 1/Stage 2 vocabulary is assigned to anything
in it)

# PURITY_FLOOR_COST.md — costing the 0.40 purity floor against real TCGA-BRCA purity/subtype data

**Status: feasibility analysis. Not a protocol change. Written into
`PROPOSED_DEVIATIONS.md` §12; PROTOCOL.md NOT edited, per this task's
DO-NOT list.**

## 1. Data retrieved (live, this session)

Per Standing Rule 3, this section's numbers are from live retrieval, not
memory. Retrieval was blocked at the general-web level (see §1a) and
succeeded via GitHub-hosted mirrors of the primary published tables
(§1b) — a genuine retrieval, not an estimate, of the same underlying
published data.

### 1a. Blocked retrievals (mechanism disclosed, per Standing Rule 4)

`WebFetch` was attempted against the primary/canonical sources and
failed identically for every one, with the environment surfacing a
structured `EGRESS_BLOCKED` error naming the domain:

- `www.ncbi.nlm.nih.gov` (Aran et al. 2015 PMC full text) — blocked
- `www.nature.com` (Aran et al. 2015 publisher page, ncomms9971) — blocked
- `www.cbioportal.org` (direct API) — blocked (also confirmed via a raw
  `curl` from this session's shell: `CONNECT tunnel failed, response
  403`, `$HTTPS_PROXY/__agentproxy/status` logged
  `"kind":"connect_rejected","detail":"gateway answered 403 to CONNECT
  (policy denial or upstream failure)","host":"www.cbioportal.org:443"`)
- `en.wikipedia.org` — blocked

Mechanism: this session's outbound network egress policy allowlists a
narrow set of infrastructure domains (`api.anthropic.com`,
`registry.npmjs.org`, `pypi.org`, package registries, etc. — see
`$HTTPS_PROXY/__agentproxy/status`) plus GitHub domains
(`github.com`, `raw.githubusercontent.com`, `media.githubusercontent.com`
— consistent with this being a GitHub-repo-centric coding session) and
denies essentially all other general-web hosts, publisher sites
included. This is a policy-level block, not a per-URL failure — every
non-GitHub domain tried failed the same way.

### 1b. What was actually retrieved

Two real, live-fetched, published datasets, both reachable because they
are (or resolve through) GitHub-hosted mirrors:

1. **TCGA PanCanAtlas ABSOLUTE purity/ploidy master calls**
   (`TCGA_mastercalls.abs_tables_JSedit.fixed.txt` — the standard
   ABSOLUTE-derived tumor-purity/ploidy table for the TCGA PanCanAtlas,
   the same file the GDC PanCanAtlas publication page names as the
   canonical purity source), fetched from
   `https://raw.githubusercontent.com/judithabk6/ITH_TCGA/master/external_data/TCGA_mastercalls.abs_tables_JSedit.fixed.txt`
   — 10,404 data rows, columns `array, sample, call status, purity,
   ploidy, ...`. Filtered to `call status == "called"` (9,785 unique
   patients with a numeric purity value; uncalled rows excluded, not
   imputed, per Standing Rule 4).
2. **TCGA PanCanAtlas breast cancer clinical/subtype table**
   (`data_clinical_patient.txt` from the cBioPortal `datahub` repository's
   `brca_tcga_pan_can_atlas_2018` study — this is cBioPortal's own
   curated mirror of the PanCanAtlas clinical annotation, including the
   `SUBTYPE` column with PAM50-derived `BRCA_LumA` / `BRCA_LumB` /
   `BRCA_Her2` / `BRCA_Basal` / `BRCA_Normal` labels), fetched via
   `https://media.githubusercontent.com/media/cBioPortal/datahub/master/public/brca_tcga_pan_can_atlas_2018/data_clinical_patient.txt`
   (the plain `raw.githubusercontent.com` path returns only a Git-LFS
   pointer for this file; the `media.githubusercontent.com/media/...`
   path resolves the actual LFS-stored content — disclosed here since it
   is a nonstandard retrieval path) — 1,084 BRCA patients, 981 with a
   non-blank `SUBTYPE`.

Joined by 12-character TCGA patient barcode (first 12 characters of the
ABSOLUTE table's `sample` column, which matches the clinical table's
`PATIENT_ID` directly): **981 BRCA patients have a PAM50 subtype call;
951 of those also have an ABSOLUTE-called purity value; 30 (3.1%) have a
subtype call but no usable ABSOLUTE purity call at all** — those 30 are
lost to any purity-floor analysis regardless of the floor's value, a
separate, floor-independent attrition source worth flagging on its own
(not double-counted in the floor fractions below, which are computed as
percentages of the 951 with both).

## 2. Fraction of TCGA-BRCA surviving each floor, overall and by subtype

n = 951 (ABSOLUTE-called, PAM50-subtyped BRCA patients).

| Floor | Overall | Basal (n=162) | Her2 (n=77) | LumA (n=487) | LumB (n=195) | Normal (n=30) |
|---|---|---|---|---|---|---|
| 0.20 | 98.5% (937) | 98.1% (159) | 98.7% (76) | 98.4% (479) | 100.0% (195) | 93.3% (28) |
| 0.25 | 96.2% (915) | 94.4% (153) | 94.8% (73) | 96.5% (470) | 100.0% (195) | 80.0% (24) |
| 0.30 | 92.6% (881) | 90.7% (147) | 85.7% (66) | 93.4% (455) | 98.5% (192) | 70.0% (21) |
| **0.40** | **83.5% (794)** | **82.1% (133)** | **71.4% (55)** | **83.6% (407)** | **94.4% (184)** | **50.0% (15)** |
| **0.45** | **77.1% (733)** | **74.7% (121)** | **63.6% (49)** | **77.2% (376)** | **88.7% (173)** | **46.7% (14)** |

Purity summary (same cohort): overall mean 0.586, median 0.590. By
subtype: Basal mean 0.569/median 0.550; Her2 mean 0.499/median 0.500;
LumA mean 0.581/median 0.590; LumB mean 0.661/median 0.680; Normal mean
0.493/median 0.390.

**This does not match the P07-RERUN2 assumption that a 0.40 floor "will
hit Basal hardest."** In this real cohort, **Her2-enriched and
Normal-like are hit hardest** (Her2: 71.4%→63.6% survival at
0.40→0.45; Normal: 50.0%→46.7%, off a tiny n=30 base), while **LumB is
the most purity-robust subtype at every floor** (94.4%/88.7%) and
**Basal sits in the middle** of the five subtypes (82.1%/74.7%,
close to LumA's 83.6%/77.2%). The P07-RERUN2 concern was reasonable to
raise as a hypothesis (Basal tumors are smaller/denser and clinically
harder to obtain high-purity sections in some series), but real
consensus-purity data for this cohort does not bear it out as the worst
case — Her2-enriched and Normal-like are. This is exactly the kind of
claim Standing Rule 3 exists to prevent from being asserted on priors;
the retrieval changes the answer.

## 3. Implication for per-gene reference-set class sizes

`SIMULATION_SPEC.md` already computed (from `BENCHMARKS.tsv`
`BRCA_PREV01`/`DDR_PREV01`) that a **full, purity-unfiltered** ~1097-
patient TCGA-BRCA-scale cohort implies **CORE_HR pathogenic class ≈
55–75 patients; DDR_SIGNALING ≈ 25–35 patients**, already "far below" the
simulator's own working n, and already flagged there as potentially
falling under PROTOCOL §8's `n < 20` per-stratum floor once split across
PAM50 subtypes.

Applying the same flat, unstratified carrier rates (`BRCA_PREV01` 5.0%
CORE_HR; `DDR_PREV01` CHEK2+ATM+PALB2 sum 3.66% DDR_SIGNALING — same
rates and same caveats `SIMULATION_SPEC.md` already discloses: Couch
2017 is a clinically-referred, not unselected, cohort, so these likely
overstate an unselected rate) to this session's real, purity-floor-
survival counts (§2) gives **expected carrier counts, not real per-sample
labels — TCGA-BRCA is not itself annotated with germline BRCA/CHEK2/ATM/
PALB2 status in the tables retrieved here**:

**Expected CORE_HR carriers (5.0% flat rate):**

| Floor | Overall | Basal | Her2 | LumA | LumB | Normal |
|---|---|---|---|---|---|---|
| 0.20 | 46.9 | 8.0 | 3.8 | 24.0 | 9.8 | 1.4 |
| 0.30 | 44.1 | 7.4 | 3.3 | 22.8 | 9.6 | 1.1 |
| **0.40** | **39.7** | **6.7** | **2.8** | **20.4** | **9.2** | **0.8** |
| **0.45** | **36.6** | **6.1** | **2.5** | **18.8** | **8.7** | **0.7** |

**Expected DDR_SIGNALING carriers (3.66% flat rate):**

| Floor | Overall | Basal | Her2 | LumA | LumB | Normal |
|---|---|---|---|---|---|---|
| 0.20 | 34.3 | 5.8 | 2.8 | 17.5 | 7.1 | 1.0 |
| 0.30 | 32.2 | 5.4 | 2.4 | 16.7 | 7.0 | 0.8 |
| **0.40** | **29.1** | **4.9** | **2.0** | **14.9** | **6.7** | **0.5** |
| **0.45** | **26.8** | **4.4** | **1.8** | **13.8** | **6.3** | **0.5** |

Even the **gene-group-level, subtype-pooled** total (Overall column) at
a 0.40 floor (CORE_HR≈39.7, DDR_SIGNALING≈29.1) is now below or at the
low end of the pre-floor 55–75 / 25–35 range `SIMULATION_SPEC.md` already
flagged as marginal against PROTOCOL §8's `n<20` floor when further
split across sub-gene and PAM50 strata. **Split by subtype, every cell
except LumA CORE_HR and LumB CORE_HR/DDR_SIGNALING falls under 20 at a
0.40 floor, and Her2/Normal fall under 20 even pooled across every gene
in either arm** (Her2 CORE_HR≈2.8, DDR_SIGNALING≈2.0; Normal CORE_HR≈0.8,
DDR_SIGNALING≈0.5, at 0.40).

**Caveat on the flat-rate assumption (disclosed, not corrected for, no
number available to correct it with this session):** germline BRCA1
carriers' tumors are well-documented to skew strongly basal-like — a
WebSearch synthesis this session surfaced a representative ~80% figure
(range ~57–91.5% across cited cohorts) for the fraction of BRCA1-mutant
tumors classified basal-like/TNBC, consistent with this project's own
`BENCHMARKS.tsv` `HRD06` row's qualitative note that basal-like tumors
share elevated genomic instability with BRCA1-deficient tumors
independent of germline status. This means the true CORE_HR carrier
**rate** in Basal is almost certainly higher than the flat 5.0% used
above (and correspondingly lower in the other four subtypes), which
would partially offset Basal's purity-floor attrition specifically —
but no subtype-stratified carrier-prevalence percentage was retrieved
this session (a genuinely different, harder-to-find number than the
unstratified rate), so this table uses the flat rate throughout and
this caveat is stated rather than silently corrected for, per Standing
Rule 3/4. The Her2 and Normal-like findings (near-zero expected carrier
count regardless of the exact rate used) are robust to this caveat
because they are driven by TINY subtype `n` at any plausible carrier
rate, not by the rate itself.

## 4. Cross-reference against GATE8's instability characterization

`gates/gate8_interval_informativeness.py`'s existing characterization on
the LOH caller's current (unfiltered, n=27–36 for Normal-like, n≈500–800
in the simulator for the other four subtypes) strata already returns
**`UNINFORMATIVE`** for both Normal-like strata
(`SIMULATED_loh_validation/gate8_out/SIMULATED_GATE8_INTERVAL_REPORT.tsv`)
— `CORE_HR_normal_like` (CI [2.77, 38.59], 3 ACMG tiers spanned,
`MAX_TIERS_SPANNED=2` exceeded) and `DDR_SIGNALING_normal_like` (CI
[1.02, 6.55], same reason) — at a stratum size (27–36) that is already
**larger** than every real-data expected-carrier count in §3's floor-0.40
row except LumA and LumB.

The relationship gate8 characterizes (`tiers_spanned` grows, CI widens,
as stratum n shrinks — visible directly by comparing the 10 `INFORMATIVE`
rows against the 2 `UNINFORMATIVE` Normal-like rows in the same table,
the only two rows built from a comparably small n) implies that **every
subtype x gene-group cell in §3 at a 0.40 or 0.45 floor other than
LumA/LumB would be expected to return `UNINFORMATIVE` under the same
characterization, not merely `INSUFFICIENT_N`** — the two are related
but distinct failure modes (`INSUFFICIENT_N` is PROTOCOL §8's n<20
gate applied before any interval is even built; `UNINFORMATIVE` is
gate8's tier-span check on an interval that DID get built but is too
wide to be actionable) and a stratum can hit either one first depending
on exactly how few carriers it draws. This is a qualitative
extrapolation from gate8's own already-observed behavior at a
comparable n, not a re-run of gate8 or gate6 against real data (neither
was re-run this task, per the DO-NOT list) — stated as an implication,
not asserted as a re-verified gate result.

## 5. Feasibility finding — stated plainly

**A 0.40 (or 0.45) purity floor, applied on top of this project's
already-marginal per-gene reference-set class sizes, leaves too few
carriers for the study to resolve anything per gene within most PAM50
subtypes.** LumA (the largest subtype, ~half the cohort) retains a
CORE_HR class in the high teens/low twenties — itself marginal against
PROTOCOL §8's n<20 floor once split by sub-gene — and LumB (the most
purity-robust subtype) retains single-digit-to-low-double-digit
DDR_SIGNALING carriers. **Her2-enriched and Normal-like are expected to
have fewer than 3 carriers per gene-group at a 0.40 floor, i.e.
essentially no testable stratum at all**, independent of which specific
gene within CORE_HR or DDR_SIGNALING is examined. This is a **Stage 4
feasibility question, answered here before Stage 4 is planned**, exactly
as requested: the study as currently scoped (per-gene, PAM50-subtype-
stratified, at a 0.40+ purity floor) cannot resolve per-gene evidence in
four of five PAM50 subtypes, and is marginal even in the fifth.

This does not by itself argue for or against the 0.40 floor being
correct on accuracy grounds (P07-RERUN2's own accuracy-vs-floor evidence,
`SIMULATED_loh_validation/SIMULATED_PURITY_FLOOR_BY_SUBTYPE.tsv`, is the
basis for that question and is untouched by this analysis). It argues
that if 0.40 (or the subtype-specific 0.40–0.45 band) is adopted on
accuracy grounds, a per-gene PAM50-stratified Stage 4 design cannot be
assumed to be resolvable without either (a) pooling across subtypes for
most genes, forfeiting the subtype-specific evidence this study's own
GIS-confounding finding (see `PROPOSED_DEVIATIONS.md` §13 /
`DIRECTIONAL_CHECK_FIX.md`-adjacent P06/P07 work) was trying to enable,
or (b) a substantially larger input cohort than TCGA-BRCA alone
provides.
