# Track Declaration

Date: 2026-09-07. This document declares which track this project runs on **today**,
based solely on `ACCESS_AUDIT.md`. No data was downloaded and no analysis was run to
produce this declaration.

## Track taxonomy (defined here — no prior definition exists in this repo)

This is a freshly initialized, empty repository: no commits, no `CLAUDE.md`, no prior
`TRACK.md`. No project glossary defines "Track S / A / B" anywhere accessible to this
session. The definitions below are therefore established now, for this audit, and
should be treated as provisional until confirmed by the project owner:

- **Track S — Simulated.** Work proceeds on synthetic/simulated inputs only, under the
  full SIMULATED regime (Standing Rule 1: `SIMULATED` filenames, the mandated first-line
  banner, no ACMG evidence assignment, restricted status vocabulary). Used when the real
  data a task needs is not currently reachable at all.
- **Track A — Open-access real data.** Work proceeds on real data that is retrievable
  today with no authorization step (no dbGaP/DACO/EGA gate), for whichever cohorts and
  data types are confirmed open in `ACCESS_AUDIT.md`.
- **Track B — Controlled-access real data.** Work proceeds on dbGaP/DACO/EGA-gated data
  (germline variants, raw reads, protected MAF, EGA-hosted PCAWG files). Requires an
  **APPROVED** authorization state — never PENDING, never UNKNOWN.

## Declaration: **Track A**

### Gate evidence

1. **Track B is BLOCKED today.** Per `ACCESS_AUDIT.md` §3, no cohort has an APPROVED
   controlled-access authorization:
   - TCGA-BRCA / TCGA-OV: dbGaP DAR (phs000178) is **PENDING**, submission date UNKNOWN.
   - CPTAC-3 controlled genomic portion (phs001287): reported PENDING but scope-of-request
     unconfirmed (see caveat in `ACCESS_AUDIT.md` §3) — not usable regardless.
   - PCAWG/ICGC breast (BRCA-EU/BRCA-UK): ICGC DACO/EGA state is **UNKNOWN**.
   Per this task's explicit instruction, PENDING is not recorded as access. Track B is
   therefore not available, full stop, independent of how close any DAR might be.

2. **Track A is available today for TCGA-BRCA, TCGA-OV, and CPTAC-3 breast.**
   `ACCESS_AUDIT.md` §2 shows open-tier data — clinical, biospecimen, gene expression,
   copy number, DNA methylation, and open/masked-somatic-MAF — is retrievable from the
   GDC with no authentication, per
   https://gdc.cancer.gov/access-data/data-access-processes-and-tools (retrieved
   2026-09-07). CPTAC-3 additionally has fully open proteomics data (proteome,
   phosphoproteome, acetylome) via the Proteomic Data Commons, independent of any dbGaP
   gate, per https://proteomic.datacommons.cancer.gov/pdc/faq (retrieved 2026-09-07).

3. **PCAWG/ICGC breast is excluded from this project's Track A scope today.** Its
   original open-tier portal is retired (`https://dcc.icgc.org/`, retirement notice,
   retrieved 2026-09-07); every remaining path to this cohort's data is controlled
   (EGA DACO or dbGaP phs000178), and that state is UNKNOWN, never APPROVED. There is
   currently no reachable data for this cohort under any track except Track S.

### What this means going forward (not started here, per instruction to stop at this deliverable)

- Any exploratory work on TCGA-BRCA / TCGA-OV / CPTAC-3-breast that needs only the open
  data types listed above can proceed under **Track A** once a future task begins.
- Any exploratory work that specifically requires germline variants, raw reads, protected
  MAF, or the PCAWG/ICGC breast cohort must either (a) wait for an APPROVED dbGaP DAR or
  ICGC DACO decision — currently PENDING/UNKNOWN, not actionable today — or (b) run under
  **Track S** (simulated) in the interim, under the full Standing Rule 1 regime.
- This session does **not** decide which of those two paths the next task takes. That is
  explicitly out of scope here (task instruction: "Do not begin the next task in this
  series").

### Status

**BLOCKED (Track B), UNKNOWN-gated (PCAWG/ICGC breast) — Track A is the declared track.**
