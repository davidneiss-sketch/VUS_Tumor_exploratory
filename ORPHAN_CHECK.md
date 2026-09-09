SIMULATED DATA — NOT A SCIENTIFIC RESULT

# ORPHAN_CHECK.md — process/container write-access audit, run FIRST this session

SIMULATED: this document records the mandatory first step of this task
— confirming no orphaned process or container from the prior session
(which ended with a background poll loop live and a production run that
had been executing during a stop hook) still holds write access to this
repository, before any other work in this session.

## Method

Run at session start, before any file was read or written by this
task's own work:

1. `ps aux` — full process table.
2. `ps aux | grep -i "VUS_Tumor\|production_v2\|logistic_estimator\|simulate\.py\|interval_instability\|estimator_joint"` —
   targeted search for any process whose command line references this
   repository or last session's scripts by name.
3. `ps aux | grep -i python` — every Python process, by any name (a
   process need not name the script in a way the targeted grep above
   would catch).
4. `which docker && docker ps -a` — every container, running or
   stopped, if a container runtime is present at all.
5. `lsof +D /home/user/VUS_Tumor_exploratory` — every process holding
   any open file handle (including a bare working-directory handle)
   anywhere under the repository root.
6. `pgrep -af` for the specific script names last session's background
   work used (`production_v2_run.py`, `interval_instability_sweep_v2.py`,
   `logistic_calibration_and_loglinearity.py`,
   `estimator_joint_vs_product_test_v2.py`), plus the poll-loop's own
   marker file name (`prod_v2_done_marker`).
7. `git status --short` — confirms no file is mid-write (an actively
   writing process would typically leave the working tree in a
   partially-modified state at the moment of inspection, in addition to
   not appearing in the process checks above).

## Result: no orphaned process or container found

**(1) Process table.** No `python3`, `python`, or any interpreter
process appears anywhere in the full process listing. The only
long-running processes are session infrastructure (`/process_api`,
`environment-manager`, the `claude` CLI process itself, `sbx-telemetry-collector`,
kernel threads) — none of which are pipeline scripts, and none of which
were started by, or write to, this repository's own code.

**(2)/(6) Targeted and script-name searches.** Zero matches for any of
last session's script names or the poll-loop's marker file, beyond the
`claude` CLI process's own command line (which legitimately references
the repo via `--add-dir /home/user/VUS_Tumor_exploratory` — session
configuration, not a write-capable orphan).

**(3) Every Python process, by any name.** Zero results — confirms (1)
was not merely missing a python-specific grep pattern.

**(4) Containers.** `docker` binary is present, but
`docker ps -a` returns `Cannot connect to the Docker daemon at
unix:///var/run/docker.sock` — the daemon itself is not running in this
environment (consistent with `GATE_HOUSEKEEPING.md`/`ACCESS_AUDIT.md`'s
own prior finding that Docker access is unavailable here). **No
container of any kind — running or stopped — can be write-accessing the
repo, because no container runtime is active.**

**(5) Open file handles under the repo.** Only the current interactive
shell (`bash`), the `claude` CLI process, and the `lsof`/`grep` commands
of this very check hold any handle under the repo path — all holding a
bare working-directory (`cwd`) reference, none holding an open write
handle to any file.

**(7) Working tree state.** `git status --short` returns empty at the
moment of this check (before this task's own work began) — no file is
mid-write.

**The background poll loop from the prior session (`until [ -f
/tmp/prod_v2_done_marker ]; do ... done`) is confirmed stopped** — the
harness's own task-notification for it (delivered at the start of this
session) reports `status=killed`, `"was stopped by the user"`; this
check independently confirms no process matching it, or its marker file
name, exists.

**Leftover artifacts, inert, not evidence of anything active:**
`/tmp/prod_v2.log`, `/tmp/sweep_v2.log`, `/tmp/gate6_out.log` — plain
log files from last session's completed (not orphaned) background runs,
sitting in `/tmp`, outside the repository, held open by nothing. Left in
place (not deleted) — they are historical evidence for the prior
session's own `DEPLOYMENT_LOG.md` entries, and this task did not need to
touch them.

## Conclusion

**Confirmed: no orphaned process, container, or open write handle to
this repository exists at the start of this session.** It is safe to
proceed with Part A and Part B below.
