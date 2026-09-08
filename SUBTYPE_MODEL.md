SIMULATED DATA — NOT A SCIENTIFIC RESULT

# SUBTYPE_MODEL.md — specifying pam50_subtype's generative role before coding it

SIMULATED: this is written and fixed BEFORE any implementation change to
`simulate.py`, per this task's own STEP 1 instruction. No parameter below
was chosen by running the model and looking at whether it produced a
convenient subtype contrast — the confounding demonstration in
`STAKE_ANALYSIS.md`'s successor document (§3 of the accompanying report)
is a test of what this specification produces, not a target this
specification was reverse-engineered to hit.

## 1. Relationship to the latent HR-deficiency variable Z

**Subtype feeds Z directly, through a modest, class-independent additive
shift** — `z = Normal(Z_MEAN[arm][cls] + SUBTYPE_Z_SHIFT[subtype], Z_SD)`.
`SUBTYPE_Z_SHIFT` is the SAME value added to a given subtype regardless of
`cls` (Pathogenic or Benign) — this is what makes it a genuine confounder
rather than a second, hidden class signal: it shifts the *baseline* Z that
both classes share within a subtype, without touching the *separation*
between classes (`Z_MEAN[arm]["Pathogenic"] - Z_MEAN[arm]["Benign"]` is
unchanged). Only `Basal` gets a nonzero shift
(`SUBTYPE_Z_SHIFT["Basal"] = 0.4`, ARBITRARY — see §4); every other
subtype's shift is `0.0`.

This is a deliberately SMALL contribution relative to the class gaps
already in the model (CORE_HR: 1.5 − (−1.0) = 2.5; DDR_SIGNALING: 0.8 −
(−0.5) = 1.3) — it represents a generic "elevated genomic-instability
propensity" correlated with whatever the one-factor model's Z already
captures, not a second, dominant confound that would swamp the class
signal Z is supposed to represent. The larger, literature-motivated
channel is §2 below.

## 2. Direct effect on GIS (the explicit, literature-cited channel)

**`gis` gets a SEPARATE, direct, class-independent additive shift on top
of whatever it inherits via Z**: `gis = c + d*z + SUBTYPE_GIS_SHIFT[subtype]
+ Normal(0, sigma)`. Real basal-like/triple-negative breast cancers are
reported, in real literature, to carry elevated genomic instability
independent of germline BRCA1/2 mutation status — this is the exact
confounder PROTOCOL.md's subtype stratification exists to handle, and it
is generated here, not assumed away:

- "Basal-like breast cancers share several histo-molecular characteristics
  with BRCA1-deficient tumors, including genomic instability and reduced
  BRCA1 expression beyond germline-mutated cases" — WebSearch-sourced
  summary of literature on homologous recombination pathway alterations in
  basal-like breast cancer (session, 2026-09-08; direct WebFetch to the
  underlying PubMed/PMC/Frontiers sources was blocked by this session's
  network egress policy — the same limitation `BENCHMARKS.tsv`'s own PAM01
  row already discloses for a different citation in this file, "nature.com
  blocked this session... treat as approximate pending direct-fetch
  confirmation" — so this is recorded as qualitative, directional evidence
  for the EXISTENCE of the effect, not a numeric magnitude retrieved from
  a specific study).
- A companion finding, same WebSearch session: a genomic-instability-score
  (the same LOH+TAI+LST composite this simulator's `gis_score` represents,
  `BENCHMARKS.tsv` HRD02/HRD03) study is titled "genomic instability score
  distributions differ among breast cancer subtypes" (Breast Cancer
  Research and Treatment, 2023) — confirming the qualitative claim that
  GIS itself, not just a generic HRD concept, is reported to vary by
  subtype. The magnitude was not independently confirmed by direct fetch
  (same egress block), so is not used as a numeric source either.

**The MAGNITUDE of the shift is ARBITRARY, disclosed, not a retrieved
published number** (Standing Rule 3: the qualitative existence of the
effect is cited above; its size is a simulator design choice, exactly the
same status as `GIS_LINK`'s own `c`/`d`/`sigma` parameters already carry in
`PARAMETER_PROVENANCE.tsv`). `SUBTYPE_GIS_SHIFT["Basal"] = 10.0`; every
other subtype's shift is `0.0`. Combined with §1's Z-mediated
contribution, Basal's total GIS elevation is `~10 + d_arm * 0.4` (≈14.8
GIS points for CORE_HR, ≈13.2 for DDR_SIGNALING) — large enough to move a
material fraction of Benign-Basal tumors' GIS distribution meaningfully
toward, without reaching, the `BENCHMARKS.tsv` HRD03 GIS≥42 threshold
(Benign-Basal baseline moves from ~18/21 to ~33/34, still short of 42 —
this is a REAL, generatable confound, not a caricature that makes Basal
indistinguishable from Pathogenic).

## 3. SBS3 and LOH/WT_LOST direction: literature search did not surface a citable, independent-of-Z effect

Per this task's own instruction ("State explicitly which of these are
literature-grounded and which are ARBITRARY with rationale") — this
search did **not** find a clean, directly citable claim that PAM50 subtype
modulates the SBS3 mutational-signature exposure or the second-hit/LOH
direction rate *independent of* whatever a shared genomic-instability
latent already explains. (A well-known, different fact — BRCA1-mutant
tumors are disproportionately basal-like — is a *reverse*-direction claim,
germline status → subtype composition, not subtype → feature distribution
independent of germline status. Modeling that would make subtype's own
marginal prevalence class-dependent, which STEP 2's own check explicitly
treats as the thing that should NOT happen for "a purely stratifying
variable" — so it is deliberately not modeled here, and subtype's
prevalence stays identical for Pathogenic and Benign, per §5.)

**Decision: SBS3 and WT_LOST direction get NO additional direct subtype
term.** They still inherit a small effect via §1's Z-shift (since both are
downstream of Z), but no separate `SUBTYPE_SBS3_SHIFT` or
`SUBTYPE_WT_LOST_SHIFT` is added. This is an evidence-absence decision,
not an oversight — logged here explicitly rather than silently applying a
made-up magnitude to features for which no citable literature basis was
found in this session's (egress-restricted) search.

## 4. Subtype prevalences and source

**All 5 PAM50 categories, at benchmarked prevalences, combining two
citations from the SAME primary paper at two different denominators —
disclosed, not a single clean source:**

| subtype | proportion | source |
|---|---|---|
| Luminal A | 0.44226 | `BENCHMARKS.tsv` PAM01 (225/501), renormalized (see below) |
| Luminal B | 0.24766 | PAM01 (126/501), renormalized |
| HER2-enriched | 0.11204 | PAM01 (57/501), renormalized |
| Basal-like | 0.18280 | PAM01 (93/501), renormalized |
| Normal-like | 0.01524 | 8/525, WebSearch-sourced, see below |

`BENCHMARKS.tsv` PAM01 (The Cancer Genome Atlas Network, "Comprehensive
molecular portraits of human breast tumours," Nature 2012,
https://www.nature.com/articles/nature11412) gives 225/126/57/93 of a
501-tumor mRNA-subtyped subset — but its own notes field states this
**"Excludes a small Normal-like group not captured in this search"** — no
Normal-like figure is available from that citation. A second WebSearch
(this session, 2026-09-08) against the SAME paper surfaced: "There were
only eight normal-like and eight claudin-low tumours" out of the 525
tumors the paper profiled — a different, larger denominator than PAM01's
501-tumor mRNA-subtyped subset (both from the same paper, describing
overlapping but not identical cohorts). Direct WebFetch to confirm the
exact wording and denominator against the primary text was blocked by
this session's network egress policy
(`EGRESS_BLOCKED: www.nature.com`, `pmc.ncbi.nlm.nih.gov`) — this figure
is WebSearch-snippet-sourced only, not independently confirmed by direct
fetch, the same limitation this repository's own PAM01 row already
discloses for its 4-way split.

**Arithmetic (not itself a published figure, disclosed here in full):**
`Normal-like = 8/525 ≈ 0.015238`; the other 4 categories are renormalized
to sum to `1 − 8/525` while preserving their original 225:126:57:93 ratio
— i.e. each of PAM01's 4 proportions is multiplied by `(1 − 8/525)`. This
combines two citations at two different (but close, same-paper) cohort
sizes into one 5-way distribution that sums to exactly 1.0 — an explicit,
disclosed approximation rather than a fabricated single-source figure.

## 5. Subtype's own marginal prevalence stays class- and arm-independent

`pam50_subtype` continues to be drawn as an independent categorical draw
from the fixed 5-way distribution in §4, identically for every (arm,
class) combination — unchanged mechanically from the pre-existing
(4-category) draw, just with 5 categories now instead of 4. This is
deliberate: the confound this document specifies is entirely a
feature-distribution effect (§1, §2), not a composition effect — subtype's
own prevalence must NOT differ by class, or the "purely stratifying
variable" check STEP 2 of the invoking task requires (marginal, subtype-
collapsed quantities should stay close to their pre-subtype-aware values)
would not hold for a reason unrelated to what this document is actually
testing.

## Summary table for PARAMETER_PROVENANCE.tsv

| parameter | value | source_type | rationale |
|---|---|---|---|
| `PAM50_PROPORTIONS` (4 non-Normal-like categories) | renormalized 225/126/57/93 of 501 × (1−8/525) | `BENCHMARKS_ROW` (PAM01) + arithmetic | see §4 |
| `PAM50_PROPORTIONS["Normal-like"]` | 8/525 ≈ 0.01524 | `WEBSEARCH_SOURCED` (new provenance tier — not independently direct-fetch-confirmed) | see §4 |
| `SUBTYPE_Z_SHIFT["Basal"]` | 0.4 | ARBITRARY | see §1 — modest relative to existing class gaps 1.3–2.5 |
| `SUBTYPE_Z_SHIFT` (all other subtypes) | 0.0 | ARBITRARY | no literature basis found for a non-Basal shift |
| `SUBTYPE_GIS_SHIFT["Basal"]` | 10.0 | ARBITRARY (qualitative existence cited, magnitude is not) | see §2 |
| `SUBTYPE_GIS_SHIFT` (all other subtypes) | 0.0 | ARBITRARY | no literature basis found for a non-Basal shift |
| SBS3, WT_LOST direct subtype terms | not modeled (0.0 implicit, via Z only) | evidence-absence decision | see §3 |
