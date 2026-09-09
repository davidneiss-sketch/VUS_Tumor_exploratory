#!/usr/bin/env python3
"""P-EST-1-AMEND STEP 3 -- classify every SIMULATED_TRUTH.tsv quantity as
newly reachable, still reachable, or still unreachable under
PROPOSED_PROTOCOL_AMENDMENT.md's replacement estimator (penalized
logistic regression + prior-odds conversion), versus the CURRENT
(product-of-marginals) estimator ESTIMATOR_SPECIFICATION_AUDIT.md
audited.

SIMULATED: this is a classification exercise over already-committed
`SIMULATED_TRUTH.tsv`, read-only. It does not modify `simulate.py`,
`PROTOCOL.md`, or any estimator/pipeline file, and does not implement
the proposed amendment -- see PROPOSED_PROTOCOL_AMENDMENT.md (Standing
Rule 10: propose, do not apply).

Classification logic, applied mechanically to every quantity name (not
hand-typed, to avoid transcription error across 91 rows):

- is_null == TRUE (any of the 19 NULL_ARM / secondary-null rows): always
  STILL_REACHABLE. True LR identically 1.0 under either estimator, for
  the same reason under both (NULL_ARM's two classes share an identical
  Z_MEAN, so both a product of two identical marginal ratios and a true
  joint density ratio of two identical distributions equal 1.0) -- this
  was never blocked by the conditional-independence defect and remains
  unaffected by fixing it.
- non-null, quantity name ends in "_joint_LR" (and is not a
  product-of-marginals row): NEWLY_REACHABLE. Structurally unreachable
  under the current product-of-marginals estimator
  (ESTIMATOR_SPECIFICATION_AUDIT.md STEP 3); becomes the new estimator's
  own primary, correctly-factored target (structurally, not exactly --
  see PROPOSED_PROTOCOL_AMENDMENT.md's log-linearity risk).
- non-null, quantity name ends in "_inflation_ratio": NEWLY_REACHABLE.
  A ratio of joint_LR (newly reachable) over product_of_marginals_LR
  (already reachable) -- the ratio itself was never independently
  verifiable against any estimator output while its numerator was
  unreachable, even though its true value was always computable from
  simulate.py directly.
- non-null, quantity name ends in "product_of_marginals_LR": STILL_REACHABLE.
  This is what the CURRENT estimator's own "joint LR" output already,
  correctly, equals (ESTIMATOR_SPECIFICATION_AUDIT.md STEP 2) -- the
  amendment retains the per-feature marginal KDE/Jeffreys machinery
  unchanged specifically so this stays computable, now as a secondary,
  diagnostic quantity rather than a mislabeled primary one (see
  PROPOSED_PROTOCOL_AMENDMENT.md's Risk 3).
- non-null, quantity name ends in one of the three single-feature
  marginal LR names (wt_lost_direction_LR, gis_score_LR,
  sbs3_exposure_LR): STILL_REACHABLE. Unaffected by the amendment --
  the marginal KDE/Jeffreys machinery these come from is retained
  unchanged, and this is exactly why P07/P08 (which only ever score
  these) survive the amendment unchanged.
- anything not matching one of the above patterns: UNCLASSIFIED, and
  this script exits nonzero rather than silently guessing (Standing Rule
  4) -- as of this task's own run, every one of the 91 committed
  quantities matches one of the patterns above; a future truth-table
  change that adds a new quantity shape would need this script updated,
  not silently mis-tagged.

Run: python3 generate_reachability_table.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"
OUT_TSV = REPO_ROOT / "REACHABILITY_TABLE.tsv"


def classify(quantity: str, is_null: bool) -> tuple[str, str]:
    if is_null:
        return ("STILL_REACHABLE",
                "NULL_ARM/secondary-null quantity: true LR identically 1.0 under either estimator "
                "(identical class-conditional distributions), unaffected by the conditional-independence fix.")
    if quantity.endswith("_inflation_ratio"):
        return ("NEWLY_REACHABLE",
                "Ratio of joint_LR (newly reachable) over product_of_marginals_LR (already reachable) -- "
                "was never independently estimator-verifiable while its numerator was unreachable.")
    if quantity.endswith("product_of_marginals_LR"):
        return ("STILL_REACHABLE",
                "Retained per-feature marginal KDE/Jeffreys machinery, unchanged by the amendment -- this is "
                "what the CURRENT estimator's own output already, correctly, equals (ESTIMATOR_SPECIFICATION_AUDIT.md "
                "STEP 2); becomes a secondary diagnostic quantity under the amendment, not a newly reachable one.")
    if quantity.endswith("_joint_LR"):
        return ("NEWLY_REACHABLE",
                "Structurally unreachable under the current product-of-marginals estimator "
                "(ESTIMATOR_SPECIFICATION_AUDIT.md STEP 3); becomes the amendment's own primary, "
                "correctly-factored target (structural reachability -- see PROPOSED_PROTOCOL_AMENDMENT.md's "
                "log-linearity risk for approximation-quality, a separate question).")
    if any(quantity.endswith(suffix) for suffix in
           ("wt_lost_direction_LR", "gis_score_LR", "sbs3_exposure_LR")):
        return ("STILL_REACHABLE",
                "Single-feature marginal LR -- retained per-feature KDE/Jeffreys machinery, unchanged by the "
                "amendment; this is exactly why P07 (loh_caller.py) and P08 (signatures.py), which only ever "
                "score quantities of this kind, survive the amendment unchanged.")
    return ("UNCLASSIFIED", "Quantity name does not match any known pattern -- see this script's own docstring.")


def main() -> None:
    if not TRUTH_TSV.exists():
        print(f"FATAL: {TRUTH_TSV} not found", file=sys.stderr)
        sys.exit(1)

    with open(TRUTH_TSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    out_rows = []
    unclassified = []
    for r in rows:
        quantity = r["quantity"]
        is_null = r["is_null"].strip().upper() == "TRUE"
        status, reasoning = classify(quantity, is_null)
        if status == "UNCLASSIFIED":
            unclassified.append(quantity)
        out_rows.append({
            "quantity": quantity,
            "is_null": r["is_null"],
            "current_estimator_status": (
                "reachable" if status == "STILL_REACHABLE" else
                "unreachable" if status == "NEWLY_REACHABLE" else "UNCLASSIFIED"
            ),
            "amendment_status": status,
            "reasoning": reasoning,
        })

    if unclassified:
        print(f"FATAL: {len(unclassified)} quantities did not match any known classification pattern: "
              f"{unclassified}", file=sys.stderr)
        print("Refusing to write a table with silently-guessed classifications (Standing Rule 4).",
              file=sys.stderr)
        sys.exit(1)

    with open(OUT_TSV, "w", newline="", encoding="utf-8") as f:
        cols = ["quantity", "is_null", "current_estimator_status", "amendment_status", "reasoning"]
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    counts = {}
    for r in out_rows:
        counts[r["amendment_status"]] = counts.get(r["amendment_status"], 0) + 1
    print(f"Wrote {OUT_TSV} ({len(out_rows)} rows)")
    print(f"Classification counts: {counts}")


if __name__ == "__main__":
    main()
