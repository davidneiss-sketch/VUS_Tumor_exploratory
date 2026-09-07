"""Shared helpers for gate2..gate7. Every gate script imports this module
rather than duplicating TSV I/O and PASS/FAIL reporting.

Exit-code convention (all gates): 0 = every check passed, 1 = at least one
check failed. This directly encodes Standing Rule 4 ("Nonzero exit is
failure even if a file appeared") for the gates themselves, and every gate
that shells out to another command must propagate that command's exit code
the same way -- a nonzero exit from a wrapped command is never treated as
success just because it produced output.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class GateReport:
    gate_name: str
    checks: list[CheckResult] = field(default_factory=list)

    def check(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append(CheckResult(name, passed, detail))

    def overall_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def print_and_exit(self) -> None:
        print(f"=== {self.gate_name} ===")
        for c in self.checks:
            verdict = "PASS" if c.passed else "FAIL"
            print(f"[{verdict}] {c.name} — {c.detail}")
        overall = self.overall_passed()
        print(f"\n{self.gate_name} OVERALL: {'PASS' if overall else 'FAIL'}")
        sys.exit(0 if overall else 1)


def read_tsv(path: Path) -> list[dict[str, str]]:
    """Read a TSV into a list of dicts. Raises FileNotFoundError (not a
    silent empty-list return) if the file is missing -- gates must never
    treat a missing input file as "zero rows, all checks vacuously pass"."""
    if not path.exists():
        raise FileNotFoundError(f"required input file missing: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
    return rows


def write_tsv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def to_float(value: str, field_name: str, row_id: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"row {row_id!r}: field {field_name!r} = {value!r} is not numeric") from e


def to_int(value: str, field_name: str, row_id: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"row {row_id!r}: field {field_name!r} = {value!r} is not an integer") from e
