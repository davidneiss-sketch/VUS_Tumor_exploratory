#!/usr/bin/env python3
"""GATE 6 — Recovery. NEW AND MANDATORY (per this task). Runs against
PRODUCTION output files on every pipeline invocation, exactly like gate5
(see DEPLOYMENT_LOG.md).

For every quantity with an entry in SIMULATED_TRUTH.tsv (quantity,
injected_value, estimand, is_null), this gate now requires an explicit
SCOPE DECLARATION (--scope FILE: quantity, in_scope, reason) naming
whether that quantity is in scope for the invoking prompt/component, and
why. This is a housekeeping fix: a gate that silently scores only the
subset of quantities a caller happened to provide a recovered value for
-- with no declared reason a quantity was omitted -- is a scope bug, not
a passing result. Every truth quantity now appears in
SIMULATED_RECOVERY_TABLE.tsv, in exactly one of these states:

  1. Declared in_scope=TRUE, recovered value present -> scored as before
     (estimand match, CI containment, null containment, relative-bias
     tolerance) -> status SIMULATED_PASS / SIMULATED_FAIL.
  2. Declared in_scope=TRUE, recovered value MISSING -> SIMULATED_FAIL,
     "no recovered value found for this quantity" (unchanged from before
     -- an in-scope quantity that was not actually computed is a real
     failure, not a scope statement).
  3. Declared in_scope=FALSE -> status BLOCKED (Standing Rule 1's
     permitted vocabulary), with scope_status=NOT_IN_SCOPE and the
     declared reason recorded -- reported with the same prominence as a
     completed result (Standing Rule 8), never omitted from the table.
  4. NOT declared at all (no --scope file, or the file doesn't mention
     this quantity) -> SIMULATED_FAIL with an explicit "UNDECLARED SCOPE"
     reason, and this counts toward the overall gate failure. A gate that
     scores a subset without declaring the subset is a scope bug; an
     undeclared quantity is therefore never silently treated as
     out-of-scope or silently skipped.

  1. Asserts the injected target and the recovered quantity are the SAME
     ESTIMAND and prints which. Comparing an OR to an LR (or vice versa)
     is an AUTOMATIC FAIL regardless of numeric CI overlap -- the two are
     not on the same scale (PROTOCOL.md §6, ESTIMAND DECLARATION).
  2. Asserts the recovered CI contains the injected value (Standing Rule
     2: an interval that excludes its target is a FAILED validation,
     reported as FAIL, never as "approximately recovered").
  3. For injected-null quantities (is_null = TRUE), additionally asserts
     the interval contains 1.0 (the LR null).
  4. Asserts relative bias |recovered_point - injected_value| /
     injected_value is within the PROTOCOL.md §11 recovery tolerance
     (default 0.25 / 25%, overridable via --tolerance but the default
     matches the pre-registered protocol value exactly).

Any single FAIL halts the pipeline: this script exits 1 if any quantity
fails (including any UNDECLARED-scope quantity; BLOCKED/NOT_IN_SCOPE rows
do not by themselves cause a failure -- an honestly-declared scope
boundary is not a bug).

Per Standing Rule 1 (SIMULATED regime -- every input to this gate is,
by construction, synthetic/injected data): the emitted table is named
`SIMULATED_RECOVERY_TABLE.tsv` (not "RECOVERY_TABLE.tsv" -- Standing
Rule 1 overrides that literal filename from the task text, since it
requires the word SIMULATED in every output filename), its status
column uses only `SIMULATED_PASS`/`SIMULATED_FAIL`/`BLOCKED` (never bare
PASS/FAIL), and a companion human-readable `SIMULATED_RECOVERY_TABLE.md`
report is emitted whose first line is the mandated
"SIMULATED DATA — NOT A SCIENTIFIC RESULT" banner.

Usage:
  gate6_recovery.py --truth FILE --recovered FILE --scope FILE --outdir DIR
                     [--tolerance 0.25]

--scope is optional only in the sense that omitting it means EVERY
quantity is treated as undeclared (a hard failure for each) -- this is
deliberate: there is no default that silently treats an unscoped gate6
invocation as fine.

Exit 0 = every quantity SIMULATED_PASS, BLOCKED (declared out of scope),
or legitimately INSUFFICIENT_N. Exit 1 = at least one quantity
SIMULATED_FAIL (including any undeclared-scope quantity).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_float, write_tsv  # noqa: E402

DEFAULT_TOLERANCE = 0.25  # PROTOCOL.md §11 relative-bias bound

RECOVERY_COLUMNS = [
    "quantity", "injected", "recovered", "ci_low", "ci_high",
    "estimand_truth", "estimand_recovered", "relative_bias", "status",
    "scope_status", "scope_reason", "reason",
]


def parse_bool(value: str) -> bool:
    return value.strip().upper() in ("TRUE", "1", "YES")


def read_existing_recovery_table(path: Path) -> dict[str, dict]:
    """P06R3 REVERSION_DIAGNOSIS.md: multiple callers can legitimately write
    to the SAME --outdir (e.g. loh_caller.py's own repo-root
    SIMULATED_RECOVERY_TABLE.tsv is regenerated by every loh_caller.py or
    check_loh_caller_acceptance.py run, using ONLY loh_caller.py's own
    2-quantity scope) -- a caller whose --scope declares only a SUBSET of
    SIMULATED_TRUTH.tsv's quantities must not silently blow away another
    caller's already-recorded IN_SCOPE rows for the quantities THIS run
    doesn't declare. Returns {} if no prior file exists (first write, or a
    fresh --outdir) -- there is nothing to preserve in that case."""
    if not path.exists():
        return {}
    try:
        return {r["quantity"]: r for r in read_tsv(path)}
    except (KeyError, OSError):
        return {}


def read_scope(path: Path | None) -> dict[str, tuple[bool, str]]:
    """Returns {quantity: (in_scope, reason)}. Missing path -> empty dict,
    which the caller treats as "every quantity undeclared", not "every
    quantity in scope" -- the safe default is to fail loudly, never to
    assume scope silently."""
    if path is None:
        return {}
    rows = read_tsv(path)
    scope = {}
    for r in rows:
        scope[r["quantity"]] = (parse_bool(r["in_scope"]), r.get("reason", ""))
    return scope


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", required=True, type=Path)
    ap.add_argument("--recovered", required=True, type=Path)
    ap.add_argument("--scope", type=Path, default=None,
                     help="TSV (quantity, in_scope, reason) declaring every truth quantity's scope. "
                          "Omitting this treats every quantity as undeclared (a hard failure each).")
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    args = ap.parse_args()

    report = GateReport("gate6_recovery")

    try:
        truth_rows = read_tsv(args.truth)
        recovered_rows = read_tsv(args.recovered)
    except FileNotFoundError as e:
        report.check("truth and recovered files present", False, str(e))
        report.print_and_exit()
        return
    report.check(
        "truth and recovered files present",
        True,
        f"truth={args.truth.name} ({len(truth_rows)} quantities), recovered={args.recovered.name} ({len(recovered_rows)} rows)",
    )

    scope = read_scope(args.scope)
    if args.scope is None:
        print("NOTE: no --scope file provided -- every truth quantity is treated as UNDECLARED "
              "(a scope bug per this gate's own rule), not silently accepted.")

    recovered_by_quantity = {r["quantity"]: r for r in recovered_rows}
    existing_table = read_existing_recovery_table(args.outdir / "SIMULATED_RECOVERY_TABLE.tsv")
    table_rows = []
    any_fail = False
    undeclared_quantities = []
    preserved_from_other_caller = []

    for t in truth_rows:
        q = t["quantity"]
        injected = to_float(t["injected_value"], "injected_value", q)
        estimand_truth = t["estimand"].strip()
        is_null = parse_bool(t.get("is_null") or "FALSE")

        # P06R3 REVERSION_DIAGNOSIS.md: this run is not authoritative for a
        # quantity it doesn't declare in_scope=TRUE. If some OTHER caller
        # already wrote an IN_SCOPE (actually scored) row for this quantity
        # at this same --outdir, preserve it instead of downgrading it to
        # this run's own UNDECLARED/NOT_IN_SCOPE placeholder -- this run's
        # own exit code (any_fail) is unaffected either way, since it is
        # computed only from quantities THIS run's own --scope claims.
        existing_row = existing_table.get(q)
        can_preserve = existing_row is not None and existing_row.get("scope_status") == "IN_SCOPE"

        if q not in scope:
            if can_preserve:
                table_rows.append(existing_row)
                preserved_from_other_caller.append(q)
                print(f"[PRESERVED] {q}: UNDECLARED in this run's own --scope, but an existing "
                      f"IN_SCOPE row from a prior/other caller was found at this --outdir -- kept, not overwritten")
                continue
            undeclared_quantities.append(q)
            table_rows.append({
                "quantity": q, "injected": injected, "recovered": "", "ci_low": "", "ci_high": "",
                "estimand_truth": estimand_truth, "estimand_recovered": "",
                "relative_bias": "", "status": "SIMULATED_FAIL",
                "scope_status": "UNDECLARED", "scope_reason": "",
                "reason": "UNDECLARED SCOPE: no --scope entry provided for this quantity -- "
                          "a gate that scores a subset without declaring the subset is a scope bug",
            })
            any_fail = True
            print(f"[SIMULATED_FAIL] {q}: UNDECLARED SCOPE -- no --scope entry provided")
            continue

        in_scope, scope_reason = scope[q]
        if not in_scope:
            if can_preserve:
                table_rows.append(existing_row)
                preserved_from_other_caller.append(q)
                print(f"[PRESERVED] {q}: declared NOT_IN_SCOPE by this run's own --scope ({scope_reason}), "
                      f"but an existing IN_SCOPE row from a prior/other caller was found at this --outdir "
                      f"-- kept, not overwritten with this run's own BLOCKED placeholder")
                continue
            table_rows.append({
                "quantity": q, "injected": injected, "recovered": "", "ci_low": "", "ci_high": "",
                "estimand_truth": estimand_truth, "estimand_recovered": "",
                "relative_bias": "", "status": "BLOCKED",
                "scope_status": "NOT_IN_SCOPE", "scope_reason": scope_reason,
                "reason": scope_reason,
            })
            print(f"[BLOCKED] {q}: declared NOT_IN_SCOPE -- {scope_reason}")
            continue

        rec = recovered_by_quantity.get(q)
        if rec is None:
            table_rows.append({
                "quantity": q, "injected": injected, "recovered": "", "ci_low": "", "ci_high": "",
                "estimand_truth": estimand_truth, "estimand_recovered": "",
                "relative_bias": "", "status": "SIMULATED_FAIL",
                "scope_status": "IN_SCOPE", "scope_reason": scope_reason,
                "reason": "no recovered value found for this quantity",
            })
            any_fail = True
            print(f"[SIMULATED_FAIL] {q}: no recovered value found (declared IN_SCOPE: {scope_reason})")
            continue

        estimand_recovered = rec["estimand"].strip()
        recovered_point = to_float(rec["recovered_point"], "recovered_point", q)
        ci_low = to_float(rec["ci_low"], "ci_low", q)
        ci_high = to_float(rec["ci_high"], "ci_high", q)

        reasons = []
        estimand_match = estimand_truth == estimand_recovered
        print(f"{q}: estimand truth={estimand_truth}, recovered={estimand_recovered} "
              f"({'MATCH' if estimand_match else 'MISMATCH — AUTOMATIC FAIL'})")
        if not estimand_match:
            reasons.append(
                f"estimand mismatch: truth={estimand_truth}, recovered={estimand_recovered} "
                f"— comparing these is invalid regardless of CI overlap (AUTOMATIC FAIL)"
            )

        ci_contains_injected = ci_low <= injected <= ci_high
        if not ci_contains_injected:
            reasons.append(f"CI [{ci_low}, {ci_high}] does not contain injected value {injected} — FAILED per Standing Rule 2")

        if is_null:
            ci_contains_null = ci_low <= 1.0 <= ci_high
            if not ci_contains_null:
                reasons.append(f"injected-null quantity but CI [{ci_low}, {ci_high}] does not contain 1.0")

        if injected == 0:
            relative_bias = abs(recovered_point - injected)
            reasons.append("injected_value is 0 — reporting absolute, not relative, bias")
        else:
            relative_bias = abs(recovered_point - injected) / abs(injected)
        if relative_bias > args.tolerance:
            reasons.append(f"relative bias {relative_bias:.4f} exceeds tolerance {args.tolerance}")

        status = "SIMULATED_FAIL" if reasons else "SIMULATED_PASS"
        if status == "SIMULATED_FAIL":
            any_fail = True

        print(f"[{status}] {q}: injected={injected}, recovered={recovered_point}, "
              f"CI=[{ci_low}, {ci_high}], relative_bias={relative_bias:.4f}"
              + (f" — {'; '.join(reasons)}" if reasons else ""))

        table_rows.append({
            "quantity": q, "injected": injected, "recovered": recovered_point,
            "ci_low": ci_low, "ci_high": ci_high,
            "estimand_truth": estimand_truth, "estimand_recovered": estimand_recovered,
            "relative_bias": round(relative_bias, 6), "status": status,
            "scope_status": "IN_SCOPE", "scope_reason": scope_reason,
            "reason": "; ".join(reasons) if reasons else "",
        })

    args.outdir.mkdir(parents=True, exist_ok=True)
    tsv_path = args.outdir / "SIMULATED_RECOVERY_TABLE.tsv"
    write_tsv(tsv_path, table_rows, RECOVERY_COLUMNS)

    md_path = args.outdir / "SIMULATED_RECOVERY_TABLE.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("SIMULATED DATA — NOT A SCIENTIFIC RESULT\n\n")
        f.write("# Stage 2 recovery table\n\n")
        f.write("SIMULATED: recovered quantities vs their pre-specified injected targets, and the "
                "declared scope of every quantity in SIMULATED_TRUTH.tsv. Status values are "
                "SIMULATED_PASS / SIMULATED_FAIL / BLOCKED only, per Standing Rule 1.\n\n")
        f.write("| quantity | injected | recovered | ci_low | ci_high | estimand (truth/recovered) | relative_bias | status | scope | reason |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in table_rows:
            f.write(
                f"| {r['quantity']} | {r['injected']} | {r['recovered']} | {r['ci_low']} | {r['ci_high']} | "
                f"{r['estimand_truth']}/{r['estimand_recovered']} | {r['relative_bias']} | {r['status']} | "
                f"{r['scope_status']} | {r['reason']} |\n"
            )

    report.check(
        "SIMULATED_RECOVERY_TABLE.tsv and .md emitted",
        True,
        f"{tsv_path} ({len(table_rows)} rows), {md_path}",
    )
    if preserved_from_other_caller:
        report.check(
            "quantities outside this run's own --scope, but already IN_SCOPE at this --outdir "
            "from a prior/other caller, were preserved rather than overwritten (P06R3 REVERSION_DIAGNOSIS.md)",
            True,
            f"preserved: {preserved_from_other_caller}",
        )
    report.check(
        "every truth quantity has a declared scope (no UNDECLARED quantities)",
        len(undeclared_quantities) == 0,
        "every quantity has a scope declaration" if not undeclared_quantities
        else f"undeclared quantities (scope bug): {undeclared_quantities}",
    )
    report.check(
        "every quantity is SIMULATED_PASS or declared out of scope (any single FAIL halts the pipeline)",
        not any_fail,
        "all quantities passed or were declared out of scope" if not any_fail
        else "at least one quantity is SIMULATED_FAIL — see SIMULATED_RECOVERY_TABLE.tsv for detail",
    )

    report.print_and_exit()


if __name__ == "__main__":
    main()
