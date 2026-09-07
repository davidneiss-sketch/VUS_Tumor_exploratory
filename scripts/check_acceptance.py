#!/usr/bin/env python3
"""Acceptance check for the data-reachability audit deliverable.

Emits PASS or FAIL per criterion, per Standing Rule 6: a narrative claim of
"done" is not a check; only this script's verdict counts.

Criterion 1: TRACK.md names exactly one track (S, A, or B) and cites gate
             evidence for it.
Criterion 2: every row of every "Source URL"-bearing table in ACCESS_AUDIT.md
             has a non-empty URL in that column.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK_MD = ROOT / "TRACK.md"
AUDIT_MD = ROOT / "ACCESS_AUDIT.md"

results = []  # (criterion, passed: bool, detail: str)


def check_track_declaration():
    if not TRACK_MD.exists():
        results.append(("TRACK.md names one track + cites gate evidence", False, "TRACK.md missing"))
        return
    text = TRACK_MD.read_text()

    declared = set(re.findall(r"Declaration:\s*\*\*Track\s+([SAB])\*\*", text))
    if len(declared) != 1:
        results.append((
            "TRACK.md names one track + cites gate evidence",
            False,
            f"expected exactly one declared track, found {sorted(declared)}",
        ))
        return

    m = re.search(r"###\s*Gate evidence\s*\n(.*?)(\n##|\Z)", text, re.S)
    if not m or len(m.group(1).strip()) < 50:
        results.append((
            "TRACK.md names one track + cites gate evidence",
            False,
            "no substantive '### Gate evidence' section found",
        ))
        return

    evidence_body = m.group(1)
    urls = re.findall(r"https?://\S+", evidence_body)
    if not urls:
        results.append((
            "TRACK.md names one track + cites gate evidence",
            False,
            "gate evidence section cites no source URLs",
        ))
        return

    results.append((
        "TRACK.md names one track + cites gate evidence",
        True,
        f"Track {declared.pop()} declared; gate evidence cites {len(urls)} URL(s)",
    ))


def find_tables(text):
    """Yield lists of raw table lines (contiguous lines starting with '|')."""
    table = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            table.append(line)
        else:
            if table:
                yield table
                table = []
    if table:
        yield table


def check_table_urls():
    if not AUDIT_MD.exists():
        results.append(("every table cell in the data-type x cohort x tier table has a source URL", False, "ACCESS_AUDIT.md missing"))
        return

    text = AUDIT_MD.read_text()
    tables = list(find_tables(text))

    checked_tables = 0
    failures = []

    for table in tables:
        header_cells = [c.strip() for c in table[0].strip("|").split("|")]
        url_col = None
        for i, h in enumerate(header_cells):
            if "source url" in h.lower():
                url_col = i
                break
        if url_col is None:
            continue  # not a table this criterion applies to (e.g. authorization-state table)

        checked_tables += 1
        # table[1] is the '---' separator row
        for row_num, row in enumerate(table[2:], start=3):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) <= url_col:
                failures.append(f"row {row_num}: malformed row, missing URL column")
                continue
            cell = cells[url_col]
            if "http://" not in cell and "https://" not in cell:
                first_col = cells[0] if cells else "?"
                failures.append(f"row '{first_col}': Source URL cell has no http(s) URL")

    if checked_tables == 0:
        results.append((
            "every table cell in the data-type x cohort x tier table has a source URL",
            False,
            "no table with a 'Source URL' column found in ACCESS_AUDIT.md",
        ))
        return

    if failures:
        results.append((
            "every table cell in the data-type x cohort x tier table has a source URL",
            False,
            f"{len(failures)} row(s) missing a URL: " + "; ".join(failures[:5]),
        ))
    else:
        results.append((
            "every table cell in the data-type x cohort x tier table has a source URL",
            True,
            f"{checked_tables} table(s) checked, all rows carry a source URL",
        ))


def main():
    check_track_declaration()
    check_table_urls()

    overall = True
    for name, passed, detail in results:
        verdict = "PASS" if passed else "FAIL"
        overall = overall and passed
        print(f"[{verdict}] {name} — {detail}")

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
