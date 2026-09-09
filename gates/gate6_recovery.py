#!/usr/bin/env python3
"""GATE 6 — Recovery. NEW AND MANDATORY (per this task). Runs against
PRODUCTION output files on every pipeline invocation, exactly like gate5
(see DEPLOYMENT_LOG.md).

REVISION (P-AMD-3b, PROTOCOL_DEVIATIONS.md Entry 3, approved): the
recovery criterion is AMENDED. Exact CI containment of the injected
value is no longer a hard pass/fail condition -- it is COMPUTED AND
REPORTED for every scored quantity (`ci_contains_injected` column) but
no longer contributes to `status`. In its place: (a) the existing
relative-bias tolerance (unchanged, PROTOCOL.md §11), AND (b) an OPTIONAL
directional shrinkage-bias check, evaluated whenever a `--bias-prediction`
file declares a quantity's EXPECTED bias magnitude in advance (from the
estimator's own characterized shrinkage curve, e.g.
`MIXTURE_FIX_POST_FIX_DIAGNOSTICS.md`'s lambda sweep at the CV-selected
lambda) -- the expected DIRECTION is derived automatically (shrinkage
toward the null: downward for an injected value > 1, upward for < 1).
A quantity whose OBSERVED bias is the WRONG SIGN relative to that
prediction, or materially larger in magnitude, FAILS even when inside
the raw 0.25 tolerance -- this is what replaces containment's role in
catching a result that is wrong in a checkable way (not merely biased in
the expected, characterized way). See PROPOSED_GATE6_AMENDMENT.md for
the full rationale and the computation showing the historical
`gate6_bad_ci` fixture (recovered=9.3 vs injected=4.5) still fails under
this amended criterion, on relative bias alone.

A quantity with NO `--bias-prediction` entry is scored on relative bias
alone (containment still reported, not gated) -- the directional check
is additive protection where a prediction is available, not a universal
requirement; this is disclosed here rather than silently assumed
(Standing Rule 4).

Also new (P-AMD-3b, Part D): a `NEAR_TIER_BOUNDARY` column, computed
whenever a `--bias-prediction` magnitude is available for a
pathogenic-direction (injected > 1) quantity -- flags whether the
quantity's CI lower bound falls within the characterized-bias "danger
zone" of one of PROTOCOL.md §9's four OddsPath boundaries (350, 18.7,
4.33, 2.08), per `CONSERVATIVE_ASSIGNMENT_ANALYSIS.md`'s
`f / (1 - f)`-of-boundary result. This is a standing, always-computed
part of the output, not a one-time analysis.

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

# PROTOCOL.md §9's OddsPath thresholds, pathogenic direction (CI lower
# bound), highest first -- (boundary, tier_name, points).
ODDSPATH_PATHOGENIC_BOUNDARIES = [
    (350.0, "PATHOGENIC_VERY_STRONG", 8),
    (18.7, "PATHOGENIC_STRONG", 4),
    (4.33, "PATHOGENIC_MODERATE", 2),
    (2.08, "PATHOGENIC_SUPPORTING", 1),
]

# Disclosed, ARBITRARY slack multiplier for "materially larger than
# predicted" (CONSERVATIVE_ASSIGNMENT_ANALYSIS.md/PROPOSED_GATE6_AMENDMENT.md
# do not fix a numeric value; this is the first place one is needed, so it
# is set and disclosed here rather than left implicit). An observed
# relative bias up to 1.5x the predicted magnitude is treated as
# consistent with the prediction; beyond that, the estimator's ACTUAL
# behavior on this run has departed from its own characterized shrinkage
# curve, which is exactly the kind of "wrong in a checkable way" the
# directional check exists to catch.
MAGNITUDE_SLACK_FACTOR = 1.5

RECOVERY_COLUMNS = [
    "quantity", "injected", "recovered", "ci_low", "ci_high",
    "estimand_truth", "estimand_recovered", "relative_bias", "status",
    "scope_status", "scope_reason", "ci_contains_injected",
    "predicted_bias_direction", "predicted_bias_magnitude",
    "directional_check", "near_tier_boundary", "reason",
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


def read_bias_prediction(path: Path | None) -> dict[str, tuple[float, str]]:
    """Returns {quantity: (predicted_relative_bias_magnitude, source)}.
    Missing path or missing entry for a quantity -> that quantity's
    directional check and NEAR_TIER_BOUNDARY column are simply not
    evaluated (reported as such, never silently treated as "no bias
    predicted" == "prediction of zero bias")."""
    if path is None:
        return {}
    rows = read_tsv(path)
    out = {}
    for r in rows:
        out[r["quantity"]] = (float(r["predicted_relative_bias_magnitude"]), r.get("source", ""))
    return out


def expected_bias_direction(injected: float) -> str:
    """Shrinkage-toward-the-null direction implied by the injected value
    alone: an LR > 1 (pathogenic-leaning) quantity is expected to shrink
    DOWN toward 1; an LR < 1 (benign-leaning) quantity is expected to
    shrink UP toward 1. injected == 1 has no meaningful direction."""
    if injected > 1.0:
        return "down"
    if injected < 1.0:
        return "up"
    return "none"


def observed_bias_direction(recovered_point: float, injected: float) -> str:
    if recovered_point < injected:
        return "down"
    if recovered_point > injected:
        return "up"
    return "none"


def directional_check(injected: float, recovered_point: float, relative_bias: float,
                       predicted_magnitude: float) -> tuple[bool, str]:
    """Returns (passed, detail). Wrong sign -> FAIL regardless of
    magnitude. Right sign (or zero observed bias) but observed magnitude
    > predicted * MAGNITUDE_SLACK_FACTOR -> FAIL ("materially larger than
    predicted")."""
    predicted_dir = expected_bias_direction(injected)
    observed_dir = observed_bias_direction(recovered_point, injected)
    if predicted_dir != "none" and observed_dir != "none" and observed_dir != predicted_dir:
        return False, (f"bias direction WRONG SIGN: predicted {predicted_dir} (toward null, from injected="
                        f"{injected}), observed {observed_dir} (recovered={recovered_point})")
    magnitude_limit = predicted_magnitude * MAGNITUDE_SLACK_FACTOR
    if relative_bias > magnitude_limit:
        return False, (f"observed relative bias {relative_bias:.4f} materially exceeds predicted "
                        f"{predicted_magnitude:.4f} (slack factor {MAGNITUDE_SLACK_FACTOR}x -> limit "
                        f"{magnitude_limit:.4f})")
    return True, (f"consistent with prediction: direction={predicted_dir}, predicted magnitude="
                   f"{predicted_magnitude:.4f}, observed={relative_bias:.4f} (limit {magnitude_limit:.4f})")


def near_tier_boundary(injected: float, ci_low: float, predicted_magnitude: float) -> tuple[str, str]:
    """Returns (near_tier_boundary, detail). Only evaluated for
    pathogenic-direction quantities (injected > 1) with a predicted bias
    magnitude available -- per CONSERVATIVE_ASSIGNMENT_ANALYSIS.md's
    f/(1-f)-of-boundary danger zone. Two distinct cases, both reported
    (never collapsed into a single FALSE that could read as "no risk"
    when a downgrade already happened -- Standing Rule 4):

    - "AT_RISK": ci_low sits ABOVE a boundary B, within the danger zone
      (B, B*(1+f/(1-f))] -- an unbiased estimate landing here could
      plausibly have been pushed below B by a bias of magnitude f.
    - "REALIZED_DOWNGRADE": ci_low sits AT OR BELOW a boundary B, but
      "de-shrinking" it by the predicted magnitude (ci_low / (1-f)) would
      put it back above B -- i.e. shrinkage of the predicted magnitude is
      SUFFICIENT to explain ci_low landing in the tier below B, exactly
      the pattern `scripts/confirm_tier_directionality.py` independently
      confirms against the injected value for the two production
      quantities this task scores.
    - "FALSE": neither case applies at any of the four boundaries."""
    if injected <= 1.0:
        return "N/A", "not a pathogenic-direction (injected > 1) quantity"
    if predicted_magnitude <= 0:
        return "N/A", "predicted bias magnitude is zero or unavailable"
    f = predicted_magnitude
    danger_fraction = f / (1.0 - f) if f < 1.0 else float("inf")
    de_shrunk_ci_low = ci_low / (1.0 - f) if f < 1.0 else float("inf")
    for boundary, tier_name, _points in ODDSPATH_PATHOGENIC_BOUNDARIES:
        danger_zone_hi = boundary * (1.0 + danger_fraction)
        if boundary < ci_low <= danger_zone_hi:
            return "AT_RISK", (f"ci_low={ci_low:.4f} is within the danger zone ({boundary}, {danger_zone_hi:.4f}] "
                                f"of the {tier_name} boundary ({boundary}) at predicted bias magnitude {f:.4f}")
        if ci_low <= boundary < de_shrunk_ci_low:
            return "REALIZED_DOWNGRADE", (
                f"ci_low={ci_low:.4f} is AT/BELOW the {tier_name} boundary ({boundary}), but de-shrinking by "
                f"the predicted bias magnitude {f:.4f} (ci_low/(1-f)={de_shrunk_ci_low:.4f}) would clear it -- "
                f"consistent with shrinkage of this magnitude alone explaining a one-tier downgrade here")
    return "FALSE", f"ci_low={ci_low:.4f} not within {f:.4f}-magnitude danger zone of any OddsPath boundary"


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
    ap.add_argument("--bias-prediction", type=Path, default=None,
                     help="TSV (quantity, predicted_relative_bias_magnitude, source) declaring each "
                          "quantity's expected shrinkage-bias magnitude IN ADVANCE, from the estimator's "
                          "own characterized shrinkage curve. A quantity with no entry here is scored on "
                          "relative bias alone (the directional check and NEAR_TIER_BOUNDARY column are "
                          "not evaluated for it).")
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

    bias_prediction = read_bias_prediction(args.bias_prediction)
    if args.bias_prediction is None:
        print("NOTE: no --bias-prediction file provided -- the directional shrinkage-bias check and "
              "NEAR_TIER_BOUNDARY column are not evaluated for any quantity this run (relative-bias "
              "tolerance alone still applies).")

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
                "ci_contains_injected": "", "predicted_bias_direction": "", "predicted_bias_magnitude": "",
                "directional_check": "", "near_tier_boundary": "",
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
                "ci_contains_injected": "", "predicted_bias_direction": "", "predicted_bias_magnitude": "",
                "directional_check": "", "near_tier_boundary": "",
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
                "ci_contains_injected": "", "predicted_bias_direction": "", "predicted_bias_magnitude": "",
                "directional_check": "", "near_tier_boundary": "",
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

        # AMENDED (P-AMD-3b, PROTOCOL_DEVIATIONS.md Entry 3): CI containment
        # of the injected value is COMPUTED AND REPORTED for every quantity
        # but no longer added to `reasons` -- it is information, not a gate.
        # The null-containment check below is UNCHANGED and still gates
        # (PROPOSED_GATE6_AMENDMENT.md section 5: not touched by this
        # amendment).
        ci_contains_injected = ci_low <= injected <= ci_high
        print(f"    [containment, reported not gated] CI [{ci_low}, {ci_high}] "
              f"{'contains' if ci_contains_injected else 'does NOT contain'} injected value {injected}")

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

        # NEW (P-AMD-3b Part A): the directional shrinkage-bias check --
        # evaluated only when a --bias-prediction entry exists for this
        # quantity (see read_bias_prediction's own docstring for why a
        # missing entry is NOT treated as "predicted zero bias").
        predicted_bias_direction = ""
        predicted_bias_magnitude = ""
        directional_check_result = ""
        near_tier_boundary_flag = "N/A"
        if q in bias_prediction:
            pred_magnitude, pred_source = bias_prediction[q]
            predicted_bias_direction = expected_bias_direction(injected)
            predicted_bias_magnitude = round(pred_magnitude, 6)
            dir_ok, dir_detail = directional_check(injected, recovered_point, relative_bias, pred_magnitude)
            directional_check_result = "PASS" if dir_ok else "FAIL"
            print(f"    [directional check, source={pred_source}] {directional_check_result} — {dir_detail}")
            if not dir_ok:
                reasons.append(f"directional shrinkage-bias check FAILED: {dir_detail}")
            near_tier_boundary_flag, near_detail = near_tier_boundary(injected, ci_low, pred_magnitude)
            print(f"    [near_tier_boundary] {near_tier_boundary_flag} — {near_detail}")
        else:
            print(f"    [directional check] SKIPPED — no --bias-prediction entry for {q}")

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
            "ci_contains_injected": ci_contains_injected,
            "predicted_bias_direction": predicted_bias_direction,
            "predicted_bias_magnitude": predicted_bias_magnitude,
            "directional_check": directional_check_result,
            "near_tier_boundary": near_tier_boundary_flag,
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
                "SIMULATED_PASS / SIMULATED_FAIL / BLOCKED only, per Standing Rule 1. AMENDED criterion "
                "(PROTOCOL_DEVIATIONS.md Entry 3): `status` is driven by relative-bias tolerance and the "
                "directional shrinkage-bias check (when a --bias-prediction entry exists), NOT by CI "
                "containment of the injected value -- `ci_contains_injected` is reported for every "
                "quantity as information only.\n\n")
        f.write("| quantity | injected | recovered | ci_low | ci_high | estimand (truth/recovered) | "
                "relative_bias | ci_contains_injected | predicted_bias_direction | predicted_bias_magnitude "
                "| directional_check | near_tier_boundary | status | scope | reason |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in table_rows:
            f.write(
                f"| {r['quantity']} | {r['injected']} | {r['recovered']} | {r['ci_low']} | {r['ci_high']} | "
                f"{r['estimand_truth']}/{r['estimand_recovered']} | {r['relative_bias']} | "
                f"{r['ci_contains_injected']} | {r['predicted_bias_direction']} | {r['predicted_bias_magnitude']} | "
                f"{r['directional_check']} | {r['near_tier_boundary']} | {r['status']} | "
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
