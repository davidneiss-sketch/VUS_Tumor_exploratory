# GATE_HOUSEKEEPING.md — gate harness housekeeping fixes

No science is claimed or produced here. This is a maintenance pass on the
verification machinery itself (gate3, gate4, gate6) and a citation audit of
two PROTOCOL.md passages, per the task's exact scope. Standing Rules 1-9
apply throughout (every artifact touched here is either SIMULATED-regime
or a documentation/citation fix; no real data is used or claimed).

---

## 1. gate3 — track-conditional runtime floors

### Problem

`gates/gate3_runtime.py` enforced a single per-phase runtime floor
regardless of track. That floor passes on a synthetic/toy-scale run (this
repo's actual current state — see `TRACK.md`: Track A only, no germline
access, so every real invocation so far has been what is now called
Track S) but was never calibrated to bind on the one case that actually
matters: **a Track B run claiming real, exome-scale tool execution that
it did not actually do.**

### Fix

`gate3_runtime.py` now requires `--track {TRACK_S,TRACK_B}` (no default —
a caller must declare which track a phase log represents). Two floor sets
exist:

- **TRACK_S** — unchanged from the gate's original design (`copy_number_calling`=5.0,
  `hrd_scoring`=1.0, `signature_assignment`=2.0, `loh_binomial_test`=0.02,
  `second_hit_scan`=0.05 sec/sample). Still `ARBITRARY`, calibrated only to
  catch a stub finishing in milliseconds on toy input.
- **TRACK_B** — derived from real, live-cited tool runtimes wherever a
  genuine citation could be found (see §1.1 below for the full research
  trail — every URL, what was and wasn't found, and every disclosed
  conservatism factor). Recorded in full, with per-phase derivation and
  citations, in **`GATE3.json`**.

| Phase | TRACK_S floor | TRACK_B floor | TRACK_B basis |
|---|---|---|---|
| `copy_number_calling` | 5.0 sec/sample | 90.0 sec/sample | ASCAT README WGS figure (1800 sec) / ARBITRARY 20x margin |
| `hrd_scoring` | 1.0 sec/sample | 24.0 sec/sample | scarHRD README qualitative figure ("a few minutes", low-end 120 sec) / ARBITRARY 5x margin |
| `signature_assignment` | 2.0 sec/sample | **`null` (UNVERIFIED)** | no usable SigProfilerAssignment runtime citation found — see §1.1 |
| `loh_binomial_test` | 0.02 sec/sample | 0.02 sec/sample | in-house code, no third-party tool to benchmark |
| `second_hit_scan` | 0.05 sec/sample | 0.05 sec/sample | in-house code, no third-party tool to benchmark |

A Track B phase log entry for `signature_assignment` now fails this gate
outright (a new, distinct "no phase relies on an UNVERIFIED TRACK_B floor"
check) — Standing Rule 3 ("otherwise write UNVERIFIED and stop") means an
absent citation is reported as a hard gap, never silently passed or
silently given the (looser) Track S floor.

**Proof the fix binds where the old single floor didn't:**
`tests/fixtures/gate3_trackb_stub/phase_log.tsv` (6 sec/sample
`copy_number_calling`, 1.5 sec/sample `hrd_scoring`) **passes** under
`--track TRACK_S` and **fails** under `--track TRACK_B` — the exact "Track
B run claiming exome-scale work it did not do" scenario the task
describes (`tests/test_gate3.py::test_same_runtime_passes_track_s_but_fails_track_b`).

### 1.1 Research trail — real per-exome/WGS tool runtime citations

A genuine search was run for real, live-citable runtime figures for
ASCAT, FACETS, Sequenza, scarHRD, and SigProfilerAssignment on
whole-exome data. Findings (every URL fetched or search-confirmed
2026-09-07; full detail also in `GATE3.json`'s `track_b_derivation`):

- **ASCAT**: only a **WGS** figure exists — "~30 minutes with 12 CPUs
  from BAMs to CNA profiles" (fast purity/ploidy fit), explicitly under
  the README's WGS subsection; no WES-specific figure anywhere in the
  source. https://github.com/VanLoo-lab/ascat/blob/master/README.md
- **FACETS**: only a **WGS** figure exists, and only from a third-party
  teaching document (not FACETS' own docs, which state no runtime at
  all) — snp-pileup: 2 CPUs/4GB/1.5 hour; FACETS R analysis: 2 CPUs/40GB/
  15 min, for one WGS tumor/normal pair.
  https://github.com/NCI-ITEB/tumor_epidemiology_approaches/blob/main/sessions/session_7/practical.md
- **Sequenza**: a "~40 minutes" figure exists but is explicitly for a
  heavily subsetted toy dataset (first 60Mb of chr5, ~1.9% of the
  genome) in a teaching tutorial — too weak to use as a real-world
  citation, and not used.
  https://github.com/BPA-CSIRO-Workshops/cancer-manuals/blob/master/docs/modules/cancer-module-cnv/cnv-tut.md
- **scarHRD**: only a qualitative figure exists — "this step only takes
  a few minutes" (no numeric minutes/hours anywhere in the source;
  documentation dated 2020).
  https://github.com/sztup/scarHRD/blob/master/README.md
- **SigProfilerAssignment**: **NOT_FOUND.** The official GitHub repo's
  README contains no runtime statement. A WebSearch snippet suggested a
  COSMIC page states "about 15 seconds" for low-mutation-count samples,
  but this could not be confirmed by direct fetch (cancer.sanger.ac.uk
  is blocked by this session's network egress policy) and is therefore
  **not** reported as verified, per Standing Rule 3. The primary paper
  (Díaz-Gay et al. 2023, *Bioinformatics* btad756) likely contains a
  real CPU-time benchmarking table per search snippets, but
  academic.oup.com/biorxiv.org/pmc.ncbi.nlm.nih.gov are all blocked from
  this session, so it could not be read or verified.

**Network egress caveat:** this session's proxy blocks essentially all
non-GitHub domains (academic.oup.com, cran.r-project.org,
pmc.ncbi.nlm.nih.gov, pubmed.ncbi.nlm.nih.gov, biorxiv.org,
cancer.sanger.ac.uk, etc. — confirmed repeatedly). Only GitHub-hosted
pages could be fetched directly. The primary papers most likely to carry
real per-exome benchmarking tables could not be read from this
environment. A future session with broader network access should
re-attempt this research against those primary sources, especially the
SigProfilerAssignment paper, to replace the UNVERIFIED
`signature_assignment` floor and tighten the disclosed ARBITRARY
conservatism margins above with real WES-specific figures.

---

## 2. gate4 — replicate count read from PROTOCOL.md, not hardcoded

### Problem

`gates/gate4_statistics.py` took `--expected-replicates` with a
**hardcoded default of 2000**. If PROTOCOL.md's own §7.3 bootstrap
replicate count ever changed, this gate would keep silently enforcing
the stale number while still claiming to check "the protocol."

### Fix

`--expected-replicates` is now an **optional override**, not a default.
With it omitted, gate4 reads PROTOCOL.md's own `B = <n>` occurrences at
run time (`read_protocol_replicate_count()`), requires that every
occurrence agree, and fails loudly (not silently) if:
- PROTOCOL.md is missing,
- no `B = <n>` pattern exists in it,
- PROTOCOL.md itself states two different values (a protocol authoring
  bug, not a gate4 input problem), or
- an explicit `--expected-replicates` override disagrees with
  PROTOCOL.md's own value (a caller cannot silently redefine B).

**Proof the fix does what it claims** (`tests/test_gate4.py`):
- `test_replicate_count_is_read_from_protocol_not_hardcoded` — an LR
  table with `n_replicates=500` is rejected against the **real** repo
  `PROTOCOL.md` (B=2000), with no `--expected-replicates` passed at all.
- `test_missing_protocol_file_fails_loudly_not_silently_defaulted` and
  `test_protocol_internal_disagreement_fails_loudly` — both hard-fail as
  designed, using a fixture PROTOCOL.md that states B=2000 in one place
  and B=5000 in another.
- `test_explicit_override_disagreeing_with_protocol_fails` — an explicit
  `--expected-replicates 999` is rejected against the real PROTOCOL.md.

---

## 3. gate6 — every SIMULATED_TRUTH.tsv quantity gets a declared scope

### Problem

`gates/gate6_recovery.py` scored whatever subset of quantities a caller
happened to provide a `--recovered` row for for. A quantity with no
recovered row was reported as `SIMULATED_FAIL: no recovered value found`
— indistinguishable, in the output, from a quantity nobody ever intended
to compute at all. **A gate that scores a subset without declaring the
subset is a scope bug**, not a passing (or even an honestly-failing)
result.

### Fix

`gate6_recovery.py` now takes `--scope FILE` (TSV: `quantity, in_scope,
reason`). Every `SIMULATED_TRUTH.tsv` quantity appears in
`SIMULATED_RECOVERY_TABLE.tsv` in exactly one of four states:

1. **Declared `in_scope=TRUE`, recovered value present** → scored exactly
   as before (estimand match, CI containment, null containment, 0.25
   relative-bias tolerance) → `SIMULATED_PASS` / `SIMULATED_FAIL`.
2. **Declared `in_scope=TRUE`, recovered value missing** →
   `SIMULATED_FAIL`, "no recovered value found for this quantity"
   (unchanged — an in-scope quantity that wasn't actually computed is a
   real failure).
3. **Declared `in_scope=FALSE`** → status `BLOCKED` (Standing Rule 1's
   permitted vocabulary), with new `scope_status=NOT_IN_SCOPE` and
   `scope_reason` columns carrying the declared reason. Reported with the
   same prominence as a completed result (Standing Rule 8) — never
   omitted from the table.
4. **Not declared at all** (no `--scope` file, or the file doesn't
   mention this quantity) → `SIMULATED_FAIL`, `scope_status=UNDECLARED`,
   with an explicit "UNDECLARED SCOPE" reason — and this **does** count
   toward the overall gate failure. Omitting `--scope` entirely now means
   every quantity is undeclared (a hard failure for each), by design:
   there is no default that silently treats an unscoped invocation as
   fine.

Only a real `SIMULATED_FAIL` (case 1/2) or an `UNDECLARED` quantity
(case 4) fails the gate; a declared-out-of-scope (`BLOCKED`) quantity
does not, by itself.

**Both existing production callers were updated** to declare scope
explicitly:
- `production/generate_production_run.py` now emits
  `production/SIMULATED_scope.tsv` (all 3 quantities `in_scope=TRUE` —
  computed by its own LR-fitting pipeline).
- `loh_caller.py` now emits `SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv`
  (the 2 LOH-direction quantities `in_scope=TRUE`; the 4 GIS/HRD-score,
  SBS3-exposure, and engineered-null quantities `in_scope=FALSE`, each
  with its own reason). Re-running `loh_caller.py` after this fix: the 4
  out-of-scope quantities now correctly show `BLOCKED`/`NOT_IN_SCOPE`
  instead of a misleading generic `SIMULATED_FAIL`; gate6's overall exit
  is still 1 (FAIL), but now purely because the 2 in-scope quantities'
  real relative-bias results (0.3429, 0.3750) exceed the 0.25 tolerance
  — the honest reason, not an artifact of unscored quantities.

**Proof** (`tests/test_gate6.py`):
`test_no_scope_file_means_every_quantity_undeclared_and_fails` and
`test_scope_mixed_in_scope_out_of_scope_and_undeclared` (one fixture
exercising all three non-trivial outcomes — IN_SCOPE+scored,
declared NOT_IN_SCOPE+BLOCKED, and UNDECLARED+hard-fail — in one run).

---

## 4. PROTOCOL.md citation audit — the two checker-adjacent passages

The task's instruction: verify that wording PROTOCOL.md carries to
satisfy `scripts/check_protocol.py` still specifies exact values, since
"rewording to pass a checker is the failure mode Standing Rule 6 was
written against, including in good faith."

**Important scoping note:** `git log -- PROTOCOL.md` shows exactly one
commit for this file — there is no preserved "before/after" diff of any
literal rewording event to inspect. The two passages identified below are
the two places in PROTOCOL.md that most resemble checker-satisfying,
defensive prose (each explicitly pre-empts a "this is just TBD" reading,
and `§4.2` literally states it follows "identical procedure" to `§4.1`,
making them a structurally paired pair) rather than a literal diffable
edit. Both were audited directly against what they claim.

### Passage 1 — PROTOCOL.md §4.1, ClinVar Snapshot pin rule (BEFORE this fix)

> **Snapshot pin rule:** the ClinVar release used is the most recent
> monthly archived release (first-Thursday-of-month release, per
> `BENCHMARKS_NOTES.md`) confirmed live with a resolving URL and
> timestamp within 7 days before Stage 0 execution begins (§10). If no
> such confirmation is obtainable, execution halts at Stage 0 and does
> not proceed with an unpinned or guessed release (Standing Rule 3). This
> is a fully specified *rule* rather than an open question — it does not
> depend on the data under analysis, only on the calendar date of
> execution.

**Finding: a real defect.** This passage cites `BENCHMARKS_NOTES.md` for
the specific factual claim "first-Thursday-of-month." Grepping
`BENCHMARKS_NOTES.md` and `BENCHMARKS.tsv` for `Thursday`, `monthly`,
`release cadence`, and even `ClinVar` returned **zero hits** before this
fix — the cited source never contained the claim it was cited for. This
is exactly Standing Rule 3's failure mode (a specific claim without a
live, checkable citation), reached in good faith (the sentence explicitly
argues "this is a fully specified rule, not TBD" — confident,
checker-satisfying language sitting on top of an uncited specific).
`scripts/check_protocol.py` never itself checks this cadence claim (its
`REQUIRED_SECTIONS` regex for this area only checks for the words
"ClinVar review-status floor" and "gold star", a different subsection) —
so passing the checker never required this citation to be accurate, and
nothing forced it to be checked until this review.

**Verification:** the underlying claim is true. Live-confirmed
2026-09-07 at NCBI's own documentation:
https://www.ncbi.nlm.nih.gov/clinvar/docs/release_cycle/ — "The complete
dataset for ClinVar is posted to the FTP site on the first Thursday of
each month." Not a fabricated fact — a broken citation trail pointing at
the wrong (silent) source.

**Fix applied:** PROTOCOL.md §4.1 now cites `BENCHMARKS.tsv` row
`CLINVAR01` (added this session, with the real URL and a 2026-09-07
retrieval date) instead of the non-existent `BENCHMARKS_NOTES.md` claim.
`BENCHMARKS_NOTES.md` gets a matching addendum documenting the defect and
its correction. Current (corrected) text:

> **Snapshot pin rule:** the ClinVar release used is the most recent
> monthly archived release (first-Thursday-of-month release, per
> `BENCHMARKS.tsv` row `CLINVAR01` — NCBI ClinVar's own "Release cycle"
> documentation, confirmed live 2026-09-07 at
> https://www.ncbi.nlm.nih.gov/clinvar/docs/release_cycle/; this replaces
> an earlier draft of this section that mis-cited `BENCHMARKS_NOTES.md`,
> which never actually stated this cadence — corrected during this
> project's gate-housekeeping review) confirmed live with a resolving URL
> and timestamp within 7 days before Stage 0 execution begins (§10). If no
> such confirmation is obtainable, execution halts at Stage 0 and does not
> proceed with an unpinned or guessed release (Standing Rule 3). This is
> a fully specified *rule* rather than an open question — it does not
> depend on the data under analysis, only on the calendar date of
> execution.

`scripts/check_protocol.py` re-run after this fix: still `OVERALL: PASS`
(unaffected — it never checked this specific claim either way).

### Passage 2 — PROTOCOL.md §4.2, gnomAD release pin rule

> **gnomAD release pin rule:** identical procedure to §4.1's ClinVar
> rule — the most recent gnomAD release confirmed live (URL + timestamp)
> within 7 days of Stage 0 execution; halt if unconfirmable.

**Finding: sound as written.** Unlike §4.1, this passage makes **no**
specific factual claim needing its own citation (no cadence detail, no
"first Thursday"-style specific) — it only commits to a deterministic
runtime *procedure* ("confirm live, halt if you can't"), which is itself
a fully-specified, checkable rule requiring no external citation. No
change made.

**Does either passage "still specify exact values"?** Both specify an
exact, deterministic *selection rule* rather than a single fixed number
— which is the correct, honest design for a value that generically
changes over time (a rolling data release), not a loophole: PROTOCOL.md's
own opening paragraph pre-declares this exact tradeoff ("Where a value
genuinely cannot be fixed to one number today... the rule for choosing it
at execution time is fixed here instead, precisely enough that a reader
can predict the outcome without seeing any data first"). §4.1's defect
was never the rule-vs-value design choice itself — it was the broken
citation trail underneath one factual detail inside that rule, now fixed.

---

## 5. Full regression check

`tests/run_all_tests.py` (26 tests, up from 17 before this task),
`scripts/check_gates_acceptance.py`, `scripts/check_simulator_acceptance.py`,
`scripts/check_loh_caller_acceptance.py`, and `scripts/check_protocol.py`
were all re-run after every fix above and confirmed `OVERALL: PASS` (or,
for the test suite, all tests `OK`) with no regressions.
