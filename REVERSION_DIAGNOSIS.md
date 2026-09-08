SIMULATED DATA — NOT A SCIENTIFIC RESULT

# P06R3 STEP 5: diagnosing the SIMULATED_RECOVERY_TABLE.tsv reversion

SIMULATED: during P08-RERUN, the repo-root `SIMULATED_RECOVERY_TABLE.tsv`
was copied from `signatures.py`'s gate6 output (`SIMULATED_signature_work/gate6_out/`)
to satisfy that task's deliverable list, confirmed present immediately
afterward, then found reverted to its pre-existing (`loh_caller.py`/P07)
content later in the same session with no git operation in the reflog to
explain it. This document identifies the mechanism, **reproduces it**, and
fixes it.

## 1. Root cause, stated up front

`SIMULATED_RECOVERY_TABLE.tsv` at the repo root has always been
`loh_caller.py`'s own output file: `loh_caller.py`'s `main()` calls
`gates/gate6_recovery.py --outdir REPO_ROOT` directly (`loh_caller.py:613-617`),
and `scripts/check_loh_caller_acceptance.py`'s `criterion_2_gate6()` does the
same thing again as its own re-verification (`--recovered
SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv --scope
SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv --outdir .`).
`gate6_recovery.py`, prior to this task's fix, **unconditionally overwrote**
the entire `SIMULATED_RECOVERY_TABLE.tsv` file at `--outdir` on every
invocation, using only the calling script's own `--scope` file — and
`loh_caller.py`'s own scope file declares only 2 of the 16
`SIMULATED_TRUTH.tsv` quantities `in_scope=TRUE`; the other 14 (everything
SBS3/GIS/joint/product-of-marginals/NULL_ARM-related) are declared
`in_scope=FALSE` with a `NOT_IN_SCOPE`/`BLOCKED` placeholder.

`signatures.py` (P08/P08-RERUN) never writes to this repo-root path at all
— it targets its own private `SIMULATED_signature_work/gate6_out/` (verified
by grep: `signatures.py`'s only `gate6_recovery.py` invocation uses
`--outdir gate6_out`). The repo-root copy P08-RERUN placed there was a
one-off manual `cp`, done to satisfy that task's deliverable list, with **no
programmatic owner or protection**. Any subsequent run of `loh_caller.py` or
`check_loh_caller_acceptance.py` — both of which are part of this project's
routine "run the full regression suite before committing" step — silently
overwrote it back to `loh_caller.py`'s own 2-quantity-scoped content. The
P08-RERUN session's own "run the full regression suite" step (which
includes `check_loh_caller_acceptance.py`) is almost certainly what caused
the reversion observed in that session.

## 2. Enumeration: every process/container with write access to the repo during a pipeline run

| candidate | write access to repo root? | actually writes `SIMULATED_RECOVERY_TABLE.tsv`? | verdict |
|---|---|---|---|
| `signatures.py`'s docker self-re-exec (`ensure_inside_docker()`, `docker run --rm -v {REPO_ROOT}:{REPO_ROOT} ...`) | **yes**, the mount is the entire repo root, not scoped to `SIMULATED_signature_work/` | **no** — grep-confirmed: `signatures.py`'s only `gate6_recovery.py` call uses `--outdir gate6_out`, never `REPO_ROOT`. Even in a worst-case orphaned-container scenario (parent bash killed mid-run, container detached under dockerd and kept running), this pathway cannot write that specific path at all | **RULED OUT** — not merely "did not happen this time," but structurally cannot produce this file (no code path writes there), and even the reported CONTENT is wrong for this hypothesis (an orphaned `signatures.py` container would write ITS OWN content, i.e. `SIMULATED_FAIL`/IN_SCOPE rows matching `gate6_out/`, not `loh_caller.py`'s `BLOCKED`/NOT_IN_SCOPE rows, which is what was actually observed) |
| `check_signatures_acceptance.py`'s reproducibility check (`criterion_7_reproducibility_regenerate_and_diff()`, `shutil.copytree`/`rmtree`/`move`) | scoped to `SIMULATED_signature_work/` and its sibling `SIMULATED_signature_work_repro_check_backup/` only | **no** — code-read confirmed: every `shutil` call in this function operates on `WORK_DIR` (`= REPO_ROOT / "SIMULATED_signature_work"`) or its backup sibling, never on any repo-root file directly | **RULED OUT** by code-path scope |
| `loh_caller.py`'s own `main()` (`gates/gate6_recovery.py --outdir REPO_ROOT`, `loh_caller.py:613-617`) | yes, writes `SIMULATED_RECOVERY_TABLE.tsv`/`.md` directly at repo root | **yes**, every run, unconditionally (pre-fix) | **CONFIRMED** — content matches (P07's 2-quantity scope, everything else `BLOCKED`/`NOT_IN_SCOPE`) |
| `check_loh_caller_acceptance.py`'s `criterion_2_gate6()` (re-invokes `gates/gate6_recovery.py --outdir REPO_ROOT` with `loh_caller.py`'s own recovered/scope files) | yes, same path | **yes**, every run, unconditionally (pre-fix) | **CONFIRMED — this is what a "run the full regression suite" step actually triggers** (this script, not `loh_caller.py` itself, is what a session re-runs when validating before commit) |

No other script in this repository (`grep -rn "docker run"` across `*.py`,
`scripts/*.py`, `gates/*.py`: zero matches outside `signatures.py`) invokes
a container with repo-root write access, and no other script writes to
`SIMULATED_RECOVERY_TABLE.tsv` at the repo root (`grep -rn
"SIMULATED_RECOVERY_TABLE" .` — the repo-root path is referenced only by
`loh_caller.py` (writer, via `gate6_recovery.py`, and reader for its own
report), `check_loh_caller_acceptance.py` (re-writer via the same gate),
`check_gate_housekeeping_acceptance.py` and `check_p08rerun_acceptance.py`
(readers only)).

## 3. Reproduction

```
$ cp SIMULATED_signature_work/gate6_out/SIMULATED_RECOVERY_TABLE.tsv SIMULATED_RECOVERY_TABLE.tsv
$ grep core_hr_sbs3_exposure_LR SIMULATED_RECOVERY_TABLE.tsv | cut -f1,9
core_hr_sbs3_exposure_LR	SIMULATED_FAIL          # P08's real score

$ python3 gates/gate6_recovery.py --truth SIMULATED_TRUTH.tsv \
    --recovered SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv \
    --scope SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv --outdir .
  # this is EXACTLY check_loh_caller_acceptance.py's criterion_2_gate6() subprocess call
$ grep core_hr_sbs3_exposure_LR SIMULATED_RECOVERY_TABLE.tsv | cut -f1,9
core_hr_sbs3_exposure_LR	BLOCKED                 # reverted to P07's NOT_IN_SCOPE placeholder
```

This reproduces the exact symptom reported at the end of P08-RERUN: a
quantity that had a real, scored `SIMULATED_FAIL` status silently reverts to
`BLOCKED` after an unrelated (and, from the perspective of someone running
"the full regression suite," entirely routine and expected-to-be-harmless)
script runs.

## 4. Fix: merge-aware `gate6_recovery.py`

`loh_caller.py` is on this task's DO-NOT-MODIFY list, so the fix is in
`gates/gate6_recovery.py` (not restricted) instead — it is the shared
component genuinely responsible for the unconditional-overwrite behavior,
and fixing it there fixes every current and future caller, not just this
one collision.

`gate6_recovery.py` now reads any existing `SIMULATED_RECOVERY_TABLE.tsv`
already present at `--outdir` before writing (`read_existing_recovery_table()`).
For a quantity this run's own `--scope` does **not** declare `in_scope=TRUE`
(either `NOT_IN_SCOPE` or fully undeclared), if an existing row for that
same quantity is already present with `scope_status == "IN_SCOPE"` (i.e.
some other caller already legitimately scored it), that existing row is
**preserved** instead of being overwritten with this run's own
`BLOCKED`/`UNDECLARED` placeholder — printed as `[PRESERVED]`, and rolled up
into a new, visible `report.check(...)` line so this is never a silent
effect. A quantity this run's own `--scope` **does** declare `in_scope=TRUE`
is always freshly (re-)scored by this run, never preserved from a stale
prior file — each caller remains fully authoritative for its own declared
scope; only rows that would otherwise be *unclaimed by anyone in this
specific invocation* fall back to "keep what a previous authoritative
caller wrote" instead of "silently downgrade to not-in-scope."

**Fix verified via the exact reproduction above, post-fix**:

```
$ cp /tmp/repro_before.tsv SIMULATED_RECOVERY_TABLE.tsv   # P08's IN_SCOPE/SIMULATED_FAIL content
$ python3 gates/gate6_recovery.py --truth SIMULATED_TRUTH.tsv \
    --recovered SIMULATED_loh_validation/SIMULATED_recovered_quantities.tsv \
    --scope SIMULATED_loh_validation/SIMULATED_recovery_scope.tsv --outdir .
[PRESERVED] core_hr_sbs3_exposure_LR: declared NOT_IN_SCOPE by this run's own --scope (...), but an
  existing IN_SCOPE row from a prior/other caller was found at this --outdir -- kept, not overwritten
  with this run's own BLOCKED placeholder
[PRESERVED] ddr_signaling_sbs3_exposure_LR: ... (same)
[PASS] quantities outside this run's own --scope, but already IN_SCOPE at this --outdir from a
  prior/other caller, were preserved rather than overwritten (P06R3 REVERSION_DIAGNOSIS.md) —
  preserved: ['core_hr_sbs3_exposure_LR', 'ddr_signaling_sbs3_exposure_LR']

$ grep core_hr_sbs3_exposure_LR SIMULATED_RECOVERY_TABLE.tsv | cut -f1,9
core_hr_sbs3_exposure_LR	SIMULATED_FAIL          # PRESERVED -- no longer reverts
```

`loh_caller.py`'s own two in-scope quantities are still freshly scored on
every run (`core_hr_wt_lost_direction_LR` / `ddr_signaling_wt_lost_direction_LR`
both recomputed to `SIMULATED_PASS` in the reproduction above) — the fix
does not freeze or go stale for the quantities a caller actually owns, only
for the quantities it explicitly disclaims.

## 5. Guard, as defense-in-depth

Per this task's instruction, a guard is added even though the mechanism was
identified and fixed directly (not left as "root cause unidentified"):
`scripts/check_p06r3_acceptance.py`'s `criterion_5_reversion_diagnosis_and_guard()`
does not merely assert the fix exists in the source — it **actively
reproduces the original collision on every run** and asserts it no longer
reverts anything: it snapshots the current `SIMULATED_RECOVERY_TABLE.tsv`,
confirms at least one `*_sbs3_exposure_LR` row is currently `IN_SCOPE`
(the exact precondition that made the original bug observable), then
re-invokes `gates/gate6_recovery.py` with `loh_caller.py`'s own
`--recovered`/`--scope` files and `--outdir REPO_ROOT` — the literal command
`check_loh_caller_acceptance.py` and `loh_caller.py`'s own `main()` run —
and asserts that row is **still** `IN_SCOPE` afterward (not reverted to
`BLOCKED`), then restores the pre-check file from its own backup regardless
of outcome. This is a live regression test of the actual reported bug, run
every time the regression suite runs, rather than a static assertion that
could pass even if a future refactor of `gate6_recovery.py` silently
regressed the merge behavior — a raw byte checksum was considered and
rejected for this purpose (the file legitimately, correctly changes
whenever either caller's underlying scores change, so a checksum would
false-positive on every legitimate re-run and provide no real protection).

## 6. Why this was never caught by any existing acceptance script until now

`check_p08rerun_acceptance.py`'s own `criterion_1_gate6_and_gate7_delegated()`
checked that the repo-root table "scores both P08 quantities with a status
and relative_bias" — but only at the moment it happened to run, in a
specific order relative to `check_loh_caller_acceptance.py`. Because the
regression suite's scripts are run individually, by hand, in whatever order
a session happens to invoke them, this check could pass or fail depending
purely on invocation order — a latent, non-deterministic test flake that
this task's fix removes structurally (there is no longer an order in which
`check_loh_caller_acceptance.py` can silently erase `check_p08rerun_acceptance.py`'s
own quantities) rather than by imposing a required run order.
