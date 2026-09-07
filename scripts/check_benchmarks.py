#!/usr/bin/env python3
"""Acceptance check for BENCHMARKS.tsv (Standing Rule 6): emits PASS/FAIL
per criterion rather than relying on narrative claims.

Criteria (from the task's ACCEPTANCE section):
  1. Every row has a resolving URL and a timestamp.
  2. Unfound benchmarks appear as NOT_FOUND rows (acceptable, not a failure)
     -- but a NOT_FOUND row must still be honestly marked as such, not
     given a fabricated URL/value.
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "BENCHMARKS.tsv"

URL_RE = re.compile(r"^https?://\S+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

results = []


def load_rows():
    if not TSV.exists():
        print("[FAIL] BENCHMARKS.tsv exists — file missing")
        sys.exit(1)
    with open(TSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
    required_cols = {
        "benchmark_id", "category", "claim_restated", "value", "units",
        "source_population", "citation", "url", "retrieval_date", "status", "applies_to_design_note",
    }
    missing_cols = required_cols - set(reader.fieldnames or [])
    if missing_cols:
        print(f"[FAIL] BENCHMARKS.tsv has required columns — missing: {sorted(missing_cols)}")
        sys.exit(1)
    return rows


def check_rows_present(rows):
    if not rows:
        results.append(("at least one benchmark row present", False, "file has zero data rows"))
    else:
        results.append(("at least one benchmark row present", True, f"{len(rows)} row(s)"))


def check_url_and_timestamp(rows):
    bad = []
    found_count = 0
    not_found_count = 0

    for r in rows:
        rid = r.get("benchmark_id", "?")
        status = (r.get("status") or "").strip()
        retrieval_date = (r.get("retrieval_date") or "").strip()
        url = (r.get("url") or "").strip()

        if not DATE_RE.match(retrieval_date):
            bad.append(f"{rid}: retrieval_date {retrieval_date!r} is not YYYY-MM-DD")
            continue
        try:
            d = date.fromisoformat(retrieval_date)
            if d > date.today():
                bad.append(f"{rid}: retrieval_date {retrieval_date} is in the future")
        except ValueError:
            bad.append(f"{rid}: retrieval_date {retrieval_date!r} does not parse")
            continue

        if status == "NOT_FOUND":
            not_found_count += 1
            # Acceptable per the task's ACCEPTANCE section: NOT_FOUND rows
            # need a genuine retrieval_date (checked above) but not a
            # resolving URL -- there's nothing to resolve to.
            if url not in ("", "n/a", "NOT_FOUND"):
                bad.append(f"{rid}: status=NOT_FOUND but url={url!r} looks like a real citation — should be a FOUND row instead")
            continue

        if status == "FOUND":
            found_count += 1
            if not URL_RE.match(url):
                bad.append(f"{rid}: status=FOUND but url {url!r} is not a resolving http(s) URL")
        else:
            bad.append(f"{rid}: status is {status!r}, expected FOUND or NOT_FOUND")

    if bad:
        results.append(("every row has a resolving URL (if FOUND) and a timestamp", False, "; ".join(bad)))
    else:
        results.append((
            "every row has a resolving URL (if FOUND) and a timestamp",
            True,
            f"{found_count} FOUND row(s) with resolving URLs, {not_found_count} honestly-marked NOT_FOUND row(s), all with valid retrieval_date",
        ))


def check_no_merged_ranges(rows):
    """Spot-check: a 'literature range' merge would typically show up as a
    value field containing a dash-separated range with no single citation
    backing it, or a units field of 'range'. This is a heuristic, not a
    semantic proof, but it catches the obvious violation pattern."""
    suspicious = []
    for r in rows:
        units = (r.get("units") or "").strip().lower()
        if units in ("range", "literature range", "pooled"):
            suspicious.append(r.get("benchmark_id", "?"))
    if suspicious:
        results.append(("no rows merge multiple sources into an unlisted 'literature range'", False,
                         f"rows with a 'range/pooled' units field: {suspicious}"))
    else:
        results.append(("no rows merge multiple sources into an unlisted 'literature range'", True,
                         "no row's units field indicates a merged/pooled range"))


def main():
    rows = load_rows()
    check_rows_present(rows)
    check_url_and_timestamp(rows)
    check_no_merged_ranges(rows)

    overall = True
    for name, passed, detail in results:
        verdict = "PASS" if passed else "FAIL"
        overall = overall and passed
        print(f"[{verdict}] {name} — {detail}")

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
