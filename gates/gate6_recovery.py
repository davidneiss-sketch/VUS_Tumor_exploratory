#!/usr/bin/env python3
"""GATE 6 — Recovery. NEW AND MANDATORY (per this task). Runs against
PRODUCTION output files on every pipeline invocation, exactly like gate5
(see DEPLOYMENT_LOG.md).

For every quantity with an entry in SIMULATED_TRUTH.tsv (quantity,
injected_value, estimand, is_null), looks up the matching recovered
quantity (quantity, recovered_point, ci_low, ci_high, estimand) and:

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
fails.

Per Standing Rule 1 (SIMULATED regime -- every input to this gate is,
by construction, synthetic/injected data): the emitted table is named
`SIMULATED_RECOVERY_TABLE.tsv` (not "RECOVERY_TABLE.tsv" -- Standing
Rule 1 overrides that literal filename from the task text, since it
requires the word SIMULATED in every output filename), its status
column uses only `SIMULATED_PASS`/`SIMULATED_FAIL` (never bare
PASS/FAIL), and a companion human-readable `SIMULATED_RECOVERY_TABLE.md`
report is emitted whose first line is the mandated
"SIMULATED DATA — NOT A SCIENTIFIC RESULT" banner.

Usage:
  gate6_recovery.py --truth FILE --recovered FILE --outdir DIR
                     [--tolerance 0.25]

Exit 0 = every quantity SIMULATED_PASS (or legitimately INSUFFICIENT_N).
Exit 1 = at least one quantity SIMULATED_FAIL.
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
    "estimand_truth", "estimand_recovered", "relative_bias", "status", "reason",
]


def parse_bool(value: str) -> bool:
    return value.strip().upper() in ("TRUE", "1", "YES")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", required=True, type=Path)
    ap.add_argument("--recovered", required=True, type=Path)
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

    recovered_by_quantity = {r["quantity"]: r for r in recovered_rows}
    table_rows = []
    any_fail = False

    for t in truth_rows:
        q = t["quantity"]
        injected = to_float(t["injected_value"], "injected_value", q)
        estimand_truth = t["estimand"].strip()
        is_null = parse_bool(t.get("is_null") or "FALSE")

        rec = recovered_by_quantity.get(q)
        if rec is None:
            table_rows.append({
                "quantity": q, "injected": injected, "recovered": "", "ci_low": "", "ci_high": "",
                "estimand_truth": estimand_truth, "estimand_recovered": "",
                "relative_bias": "", "status": "SIMULATED_FAIL",
                "reason": "no recovered value found for this quantity",
            })
            any_fail = True
            print(f"[SIMULATED_FAIL] {q}: no recovered value found")
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
            "reason": "; ".join(reasons) if reasons else "",
        })

    args.outdir.mkdir(parents=True, exist_ok=True)
    tsv_path = args.outdir / "SIMULATED_RECOVERY_TABLE.tsv"
    write_tsv(tsv_path, table_rows, RECOVERY_COLUMNS)

    md_path = args.outdir / "SIMULATED_RECOVERY_TABLE.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("SIMULATED DATA — NOT A SCIENTIFIC RESULT\n\n")
        f.write("# Stage 2 recovery table\n\n")
        f.write("SIMULATED: recovered quantities vs their pre-specified injected targets. "
                "Status values are SIMULATED_PASS / SIMULATED_FAIL only, per Standing Rule 1.\n\n")
        f.write("| quantity | injected | recovered | ci_low | ci_high | estimand (truth/recovered) | relative_bias | status | reason |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in table_rows:
            f.write(
                f"| {r['quantity']} | {r['injected']} | {r['recovered']} | {r['ci_low']} | {r['ci_high']} | "
                f"{r['estimand_truth']}/{r['estimand_recovered']} | {r['relative_bias']} | {r['status']} | {r['reason']} |\n"
            )

    report.check(
        "SIMULATED_RECOVERY_TABLE.tsv and .md emitted",
        True,
        f"{tsv_path} ({len(table_rows)} rows), {md_path}",
    )
    report.check(
        "every quantity is SIMULATED_PASS (any single FAIL halts the pipeline)",
        not any_fail,
        "all quantities passed" if not any_fail
        else "at least one quantity is SIMULATED_FAIL — see SIMULATED_RECOVERY_TABLE.tsv for detail",
    )

    report.print_and_exit()


if __name__ == "__main__":
    main()
