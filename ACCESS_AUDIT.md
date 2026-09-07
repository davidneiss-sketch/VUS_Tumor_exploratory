# Access Audit — What Data This Project Can Reach Today

Retrieval session date: **2026-09-07** (all URLs below were queried live on this date).
No data was downloaded. No analysis was performed. This document is reconnaissance only.

## 0. Retrieval-method limitation (log per Standing Rule 4)

`WebFetch` (direct page retrieval) was **BLOCKED** for every external documentation
domain attempted in this session, confirmed at the network-egress-proxy level, not
just at the tool level:

```
$ curl -sS -o /dev/null -w "%{http_code}" https://docs.gdc.cancer.gov/...
curl: (56) CONNECT tunnel failed, response 403

Proxy status log entry:
{"ts":"2026-09-07T15:10:52.450Z","kind":"connect_rejected",
 "detail":"gateway answered 403 to CONNECT (policy denial or upstream failure)",
 "host":"docs.gdc.cancer.gov:443"}
```

The same 403 policy denial occurred for `www.ncbi.nlm.nih.gov`, `docs.icgc-argo.org`,
`proteomic.datacommons.cancer.gov`, `portal.gdc.cancer.gov`, and `registry.opendata.aws`.
Per this environment's own operating instructions, an organization policy denial (403)
is not to be retried or routed around — it is reported here instead, per Standing Rule 4
("log it, stop that branch, put it in the summary").

**Consequence:** every fact below was retrieved via `WebSearch` (a live query tool that
was not subject to the same egress block) rather than by directly fetching and reading
the source page. Each row cites the actual URL returned by that live search — never a
recalled or guessed URL — but the page content is a search-snippet synthesis, not a
verified direct read of the primary source. Where a specific fine-grained value (e.g. an
exact current dbGaP version suffix) appeared only in generative search-summary prose and
was **not** backed by an actual returned link, it is marked `UNVERIFIED` below rather than
stated as fact, per Standing Rule 3. A follow-up session with unblocked egress to
`*.cancer.gov`, `ncbi.nlm.nih.gov`, `icgc-argo.org`, and `ega-archive.org` should
independently re-verify every row here via direct fetch before any of it is used to
gate a decision beyond this reconnaissance document.

---

## 1. Controlled-access accessions / mechanisms (retrieved live, not recalled)

| Item | Value found | Confidence | Source URL(s) | Retrieved |
|---|---|---|---|---|
| dbGaP study governing TCGA controlled-access data | **phs000178** (root accession). Version-specific pages actually returned as links: `.v1.p1`, `.v5.p5`, `.v7.p6`, `.v9.p8` | Root accession + versions v1–v9.p8: **confirmed** (each appeared as an actual returned URL). A search-summary sentence additionally asserted `.v11.p8` as "most recent" but no link for that version was returned — **UNVERIFIED, do not cite v11.p8 as current without a direct fetch**; highest independently-confirmed version this session is v9.p8. | https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs000178.v9.p8 (also v1.p1, v5.p5, v7.p6 variants of the same URL) | 2026-09-07 |
| dbGaP study governing CPTAC-3 controlled genomic data | **phs001287** ("CPTAC 3 Study") | Confirmed (returned as actual links, v1.p1 and v2.p2) | https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001287.v1.p1 , https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001287.v2.p2 | 2026-09-07 |
| ICGC controlled-data access mechanism | ICGC **DACO** (Data Access Compliance Office) approval → EGA account provisioned (~3–5 days after approval) for raw-sequence (BAM) files; approval window is 2 years from grant date | Confirmed (returned as actual link + snippet) | https://docs.icgc-argo.org/docs/data-access/daco/approval , https://docs.icgc-argo.org/docs/data-access/daco/applying | 2026-09-07 |
| ICGC legacy 25K / PCAWG data — current hosting after ICGC DCC portal retirement | ICGC Data Portal (`dcc.icgc.org`) is **retired** (interactive browse/download no longer available). Legacy files are redistributed: raw sequencing/controlled data via **EGA** (DACO-gated) and cross-listed under **dbGaP phs000178**; some processed data referenced via GDC. | Confirmed (portal root itself now serves a retirement notice) | https://dcc.icgc.org/ (retirement notice), https://github.com/icgc-dcc/retirement-notice , https://docs.icgc-argo.org/docs/data-access/icgc-25k-data | 2026-09-07 |
| EGA Data Access Committee (DAC) application mechanism | Applicant locates the dataset's DAC, submits an application + Data Access Agreement (DAA) via the DAC's page; no fixed SLA, "allow up to four weeks"; approved users get a personal EGA account with the granted permissions. | Confirmed (returned as actual links) | https://www.ebi.ac.uk/training/online/courses/ega-quick-tour/accessing-the-data-in-the-ega/ , https://ega-archive.org/access/data-access-committee/what-is-dac/ , https://ega-archive.org/access/request-data/how-to-request-data/ | 2026-09-07 |

---

## 2. Data-type × cohort × tier table (every cell has a source URL)

Tiers reported: **Open** (no authorization required) / **Controlled** (dbGaP/DACO
authorization required) / **BLOCKED-TODAY** (mechanism retired/unreachable regardless of
authorization) / **UNVERIFIED** (Standing Rule 3 — no live-retrieved confirmation).

### TCGA-BRCA and TCGA-OV (both governed by the same GDC-wide access policy)

| Data type | Tier | Source URL | Retrieved |
|---|---|---|---|
| Clinical (demographic / diagnosis / follow-up) | Open | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Biospecimen | Open | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Gene Expression Quantification (RNA-seq) | Open | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Copy Number Variation | Open | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| DNA Methylation | Open | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Masked Somatic Mutation (open-access MAF, germline-filtered) | Open | https://docs.gdc.cancer.gov/Encyclopedia/pages/Mutation_Annotation_Format/ | 2026-09-07 |
| Protected MAF (unfiltered, may contain germline calls) | Controlled | https://docs.gdc.cancer.gov/Encyclopedia/pages/Mutation_Annotation_Format/ | 2026-09-07 |
| Germline variant calls (VCF) | Controlled | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| SNP6 genotype (.CEL) | Controlled | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Raw sequencing reads (BAM/FASTQ) | Controlled | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Free-text clinical fields | Controlled | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Project scale (context, not a tier) | TCGA-BRCA: 1,098 cases / 71,079 files reported. TCGA-OV: 608 cases, 15,166 files total across categories reported (Clinical 608/597, Biospecimen 608/2,601, Transcriptome 492/2,135, CNV 597/2,401, SNV 443/4,880, Methylation 602/623, Sequencing Reads 575/1,929). | https://portal.gdc.cancer.gov/projects/TCGA-BRCA , https://portal.gdc.cancer.gov/projects/TCGA-OV | 2026-09-07 — **UNVERIFIED beyond search-snippet**: these counts came from `WebSearch` synthesis of the live GDC portal pages, not a direct fetch (GDC portal is one of the blocked domains, §0). Treat as approximate/point-in-time, re-verify by direct fetch before citing in any report. |

### CPTAC-3 (breast cohort)

| Data type | Tier | Source URL | Retrieved |
|---|---|---|---|
| Genomic — WGS/WXS/RNA-seq | Open or Controlled, split the same way as TCGA above; controlled portion gated by dbGaP phs001287 | https://docs.cancergenomicscloud.org/docs/cptac-data , https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001287.v2.p2 | 2026-09-07 |
| Clinical / biospecimen | Open (consistent with GDC-hosted policy above) | https://gdc.cancer.gov/access-data/data-access-processes-and-tools | 2026-09-07 |
| Proteomics (proteome, phosphoproteome, acetylome — mass spectrometry) | Open, subject to a Data Use Agreement (not dbGaP-gated) | https://proteomic.datacommons.cancer.gov/pdc/faq , https://pdc.cancer.gov/pdc/faq | 2026-09-07 |
| Breast-specific PDC studies (e.g. Prospective Breast / Broad Institute study; CompRef Acetylome/Proteome/Phosphoproteome) | Open | https://datascience.cancer.gov/news-events/news/new-data-pdc-breast-ovarian-and-pediatric-cancer-studies | 2026-09-07 |

### PCAWG / ICGC breast cohort (BRCA-EU, BRCA-UK)

| Data type | Tier | Source URL | Retrieved |
|---|---|---|---|
| Interactive browse/download via original ICGC DCC portal | **BLOCKED-TODAY** — portal retired, no longer serves data regardless of authorization | https://dcc.icgc.org/ , https://github.com/icgc-dcc/retirement-notice | 2026-09-07 |
| Donor/clinical metadata (legacy) | UNVERIFIED — original portal retired; whether an open aggregate mirror is still reachable was not confirmed via any live-retrieved primary source this session | https://docs.icgc-argo.org/docs/data-access/icgc-25k-data | 2026-09-07 |
| Simple Somatic Mutation calls (aggregated, historically open under old ICGC DCC tiering) | UNVERIFIED — historical tier does not establish current reachability given portal retirement; no live confirmation obtained | https://docs.icgc-argo.org/docs/data-access/icgc-25k-data | 2026-09-07 |
| Raw WGS reads (BAM/FASTQ) | Controlled — via EGA (DACO-gated) and cross-listed under dbGaP phs000178 | https://docs.icgc-argo.org/docs/data-access/icgc-25k-data , https://docs.icgc-argo.org/docs/data-access/daco/approval | 2026-09-07 |
| Germline variant calls | Controlled — same mechanism as raw reads | https://docs.icgc-argo.org/docs/data-access/icgc-25k-data | 2026-09-07 |

---

## 3. Authorization state per cohort (Standing Rule: PENDING ≠ access)

This session has no prior history in this repository (empty repo, no commits, no
CLAUDE.md, no artifacts) and no ability to query the user's personal dbGaP/eRA Commons
or EGA/DACO account. These states were obtained by directly asking the project owner
(`davidneiss@unicauca.edu.co`) via `AskUserQuestion` on 2026-09-07, not inferred or
guessed, per Standing Rule 3.

| Cohort | Controlled-data mechanism | State | Evidence |
|---|---|---|---|
| TCGA-BRCA | dbGaP DAR against phs000178 | **PENDING** | User-reported 2026-09-07 via direct question. Submission date: **UNKNOWN** (user does not have it on hand). Project/request ID: not provided. |
| TCGA-OV | dbGaP DAR against phs000178 | **PENDING** | Same DAR as TCGA-BRCA (same accession, same user response). Submission date: **UNKNOWN**. |
| CPTAC-3 (breast, controlled genomic portion) | dbGaP DAR against phs001287 | **PENDING** — *caveat below* | User answered a single combined question covering "TCGA-BRCA/TCGA-OV ... this same dbGaP mechanism also governs CPTAC-3": **PENDING**. However, a dbGaP DAR is submitted per named study; it is **UNVERIFIED whether the pending request's study list actually includes phs001287** as opposed to only phs000178. Do not treat CPTAC-3 controlled data as equivalently covered until the DAR's requested-studies list is confirmed. |
| PCAWG/ICGC breast (BRCA-EU, BRCA-UK) | ICGC DACO → EGA account | **UNKNOWN** | User-reported 2026-09-07: not sure of current state. |

**No cohort has an APPROVED state for any controlled-access tier.** Per the task's DO-NOT
list, PENDING is not recorded as access anywhere in this document or in TRACK.md.

---

## 4. Summary of what is reachable *today*, without any authorization

- **TCGA-BRCA, TCGA-OV**: open-tier GDC data only (clinical, biospecimen, expression,
  copy number, methylation, open/masked-somatic MAF). All germline, protected-MAF, and
  raw-read data BLOCKED pending dbGaP DAR (currently PENDING, not approved).
- **CPTAC-3 breast**: open-tier GDC genomic data (same split as above) **plus** all PDC
  proteomics data (proteome/phosphoproteome/acetylome), which is open regardless of the
  dbGaP DAR status. Controlled genomic portion (phs001287) BLOCKED pending confirmation
  of DAR scope (§3) and in any case not APPROVED.
- **PCAWG/ICGC breast**: **nothing new is reachable today.** The original open-tier portal
  is retired (BLOCKED-TODAY); the only current path to any of this cohort's data is
  controlled (EGA DACO or dbGaP phs000178), and authorization state is UNKNOWN, never
  APPROVED.
