# BENCHMARKS_NOTES.md

Companion notes to `BENCHMARKS.tsv`. Read that file first; this explains
methodology, the retrieval-method limitation, and per-category caveats not
captured by the TSV's columns.

## Retrieval method (Standing Rule 4 disclosure)

As in this project's earlier data-access and environment audits, direct
`WebFetch`/`curl` to essentially every primary-literature domain is
**blocked** in this session's network egress policy — confirmed today
(2026-09-07) by testing the exact domains this task needed:

```
www.nature.com                          -> CONNECT denied, 403
www.cell.com                            -> CONNECT denied, 403
www.nejm.org                            -> CONNECT denied, 403
breast-cancer-research.biomedcentral.com -> CONNECT denied, 403
aacrjournals.org                        -> CONNECT denied, 403
www.ncbi.nlm.nih.gov                    -> CONNECT denied, 403
ascopubs.org                            -> CONNECT denied, 403
www.gimjournal.org                      -> CONNECT denied, 403
www.sciencedirect.com                   -> CONNECT denied, 403
synapse.org / www.synapse.org           -> CONNECT denied, 403
```

This is a proxy-level organization policy denial (`connect_rejected`, per
`curl -sS http://127.0.0.1:<proxy-port>/__agentproxy/status`), not a
transient failure, and per this environment's own operating instructions
it is not to be retried or routed around.

**Consequence:** every claim in `BENCHMARKS.tsv` was retrieved via
`WebSearch` (live queries, all dated 2026-09-07) rather than by directly
fetching and reading the cited paper. Every `url` in the TSV is an actual
URL that was returned as a link by a live search this session — never a
recalled, guessed, or reconstructed URL — but in no case was the paper's
full text or table independently read by this session. Where a specific
number appeared only in generative search-summary prose without a
corresponding returned link, or where I could not resolve a precise
single value with confidence, that is disclosed in the row's `note`
column rather than stated as fact, per Standing Rule 3. A follow-up
session with unblocked egress to the domains above should independently
re-verify every row before any of it gates a scientific decision.

## Per-category caveats

- **LOH/two-hit rate (LOH01, LOH02).** Two genuinely different
  populations/denominators are reported and must not be pooled: Huang et
  al. 2018 (LOH01) is pan-cancer, all predisposition genes combined,
  33 cancer types; Maxwell et al. 2017 (LOH02) is breast/ovarian-only,
  BRCA1/BRCA2-specific, and stratified by tissue and gene. Do not average
  43% (LOH01) with 90%/54% (LOH02) — they answer different questions.

- **HRD in HGSOC (HRD01–HRD04).** I could not find one clean,
  single-primary-source table giving BRCA-mutant-vs-wild-type HRD-high
  *percentages* in HGSOC with a URL I'm confident citing — an earlier
  search surfaced a "228/352 (65%) HRD-positive, 102 (29%) BRCA-mutant,
  126 (36%) BRCA-wild-type" figure, but only as search-summary prose with
  no specific backing link, so it is **not** included in the TSV
  (Standing Rule 3: no backing URL means don't assert it). What *is*
  solidly sourced is the unstratified ~50% HGSOC-wide estimate (HRD01)
  and the GIS≥42 threshold with both its analytic origin (HRD02/HRD03)
  and its clinical-outcome validation (HRD04, PAOLA-1). If the design
  needs a BRCA-stratified HRD-high percentage specifically, that remains
  an open gap — treat it as NOT_FOUND for now and re-search with direct
  access to the primary HGSOC HRD literature (Konstantinopoulos, Pennington,
  or the TCGA-OV follow-up papers were not directly checked this session).

- **TCGA-BRCA TP53/PIK3CA (TP01, TP02).** These are two different
  cohorts: TP01 is the primary TCGA-BRCA paper's own >10%-incidence
  threshold claim (825 tumors, exact overall percentage not confirmed by
  direct read this session); TP02 is a *secondary* NGS reanalysis of a
  680-case TCGA-derived IDC subset with concrete numbers (TP53 37%,
  PIK3CA 31%). Per the task instruction not to merge sources, they are
  listed as separate rows — do not report "TCGA-BRCA TP53 = 37%" as if it
  came from the primary 2012 Nature paper itself.

- **PAM50 proportions (PAM01).** The counts (225/126/57/93) surfaced via
  WebSearch synthesis of Figure 1 in the primary TCGA-BRCA paper, not
  from an independently fetched copy of the paper. They sum to 501 of the
  825-tumor cohort (the mRNA-subtyped subset) and appear to exclude a
  small Normal-like group. Treat the derived percentages (44.9/25.1/
  11.4/18.6) as approximate pending direct verification.

- **ENIGMA likelihood ratios (ENIGMA01, ENIGMA02).** Sourced from Spurdle
  et al. 2014 (BCAC+CIMBA+ENIGMA pooled pathology analysis), which is the
  standard citation for tumor-pathology likelihood ratios used in ENIGMA's
  own BRCA1/2 classification approach. Note the BRCA1 and BRCA2 LR tables
  are gene-specific and must not be cross-applied.

- **OddsPath thresholds (ODDS01, ODDS02).** The four pathogenic-direction
  cut-points (2.08 / 4.33 / 18.7 / 350) were corroborated across multiple
  independent search results referencing Tavtigian et al. 2018, which
  increases confidence, but the primary paper itself was not directly
  read this session (gimjournal.org blocked). The benign-direction values
  in ODDS02 are stated in the TSV as *computed reciprocals* of ODDS01,
  not as independently confirmed values from the paper's own text.

- **TCGA HRD/DDR dataset location (DDR01, DDR02).** The Knijnenburg et
  al. 2018 paper (DDR01) and its scope (8,464 TCGA samples) are
  confirmed via search, but I could not confirm a live, currently-
  resolving download URL or Synapse ID for the underlying per-sample
  score table (DDR02 = NOT_FOUND). Per Standing Rule 3, no Synapse ID or
  data-portal URL is invented here — a genuine data-location lookup needs
  direct access to `cell.com` and/or `synapse.org`, both blocked this
  session.

## What this means for downstream controls

Per the task's acceptance criteria, a `NOT_FOUND` row means the
corresponding control cannot run yet. Concretely that is:

- **DDR02** — no automated download of the TCGA per-sample HRD/DDR score
  table is possible from this session; any control that needs to compare
  our computed HRD scores against the *published per-sample* TCGA values
  (not just the summary statistics in DDR01) is blocked until that URL is
  resolved.
- The BRCA-stratified HGSOC HRD-high percentage gap noted under HRD01–04
  above means any control comparing our pipeline's HRD-high rate against
  a published BRCA-mutant-vs-wild-type split in HGSOC specifically cannot
  run yet either — only the unstratified ~50% (HRD01) is available as a
  comparison point today.

No other data was downloaded and no analysis was run in this task; this
is a reconnaissance/benchmark-retrieval deliverable only.

## Addendum (2026-09-07, added while building the simulator)

Two rows were appended for parameters `simulate.py` needed and that
weren't covered by the original 8 categories: **WGD01** (whole-genome
doubling prevalence, Bielski et al. 2018 Nat Genet, ~30% pan-cancer,
confirmed via a real returned URL) and **TMB01** (TCGA-BRCA exome
mutation counts, same primary paper as TP01/PAM01, with an exact
arithmetic mean-per-tumor computed from the cited totals). Same
retrieval method and caveats as every other row in this file apply;
see each row's own note for specifics.
