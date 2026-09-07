#!/usr/bin/env python3
"""Acceptance checker for the gate-harness-housekeeping task (Standing Rule
6: PASS/FAIL per criterion, not narrative). Re-derives every answer from
real on-disk artifacts and real gate re-runs, not from GATE_HOUSEKEEPING.md's
own prose.

Criteria, from the task's ACCEPTANCE section:
  1. GATE3.json carries two floors with the Track B floor's derivation source.
  2. gate4 fails if PROTOCOL.md's replicate count and the output's disagree.
  3. Every SIMULATED_TRUTH.tsv row appears in the recovery table with a
     scope status.
  4. The two reworded PROTOCOL.md passages are quoted in the session
     output for human reading (printed here, and present in
     GATE_HOUSEKEEPING.md).

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE3_JSON = ROOT / "GATE3.json"
PROTOCOL = ROOT / "PROTOCOL.md"
HOUSEKEEPING = ROOT / "GATE_HOUSEKEEPING.md"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True, text=True)


PHASES = ["copy_number_calling", "hrd_scoring", "signature_assignment", "loh_binomial_test", "second_hit_scan"]


def criterion_1_gate3_two_floors_with_source() -> None:
    if not GATE3_JSON.exists():
        check("GATE3.json carries two floors with the Track B floor's derivation source", False, "GATE3.json missing")
        return
    data = json.loads(GATE3_JSON.read_text())
    tracks = data.get("tracks", {})
    missing_tracks = [t for t in ("TRACK_S", "TRACK_B") if t not in tracks]
    if missing_tracks:
        check("GATE3.json carries two floors with the Track B floor's derivation source", False,
              f"missing track(s): {missing_tracks}")
        return

    s_floors = tracks["TRACK_S"].get("floors_sec_per_sample", {})
    b_floors = tracks["TRACK_B"].get("floors_sec_per_sample", {})
    missing_phases_s = [p for p in PHASES if p not in s_floors]
    missing_phases_b = [p for p in PHASES if p not in b_floors]

    derivation = tracks["TRACK_B"].get("track_b_derivation", [])
    derivation_by_phase = {d["phase"]: d for d in derivation}
    missing_derivation = [p for p in PHASES if p not in derivation_by_phase]
    no_source_info = [
        p for p, d in derivation_by_phase.items()
        if not (d.get("citations_found") or d.get("derivation_note") or d.get("source_type") == "UNVERIFIED")
    ]

    ok = not (missing_tracks or missing_phases_s or missing_phases_b or missing_derivation or no_source_info)
    check(
        "GATE3.json carries two floors with the Track B floor's derivation source",
        ok,
        f"TRACK_S floors for all phases={not missing_phases_s}, TRACK_B floors for all phases={not missing_phases_b}, "
        f"derivation entries for all phases={not missing_derivation}, every derivation entry names a "
        f"source or is explicitly UNVERIFIED={not no_source_info}",
    )


def criterion_2_gate4_fails_on_disagreement() -> None:
    fixture = ROOT / "tests" / "fixtures" / "gate4_replicate_mismatch" / "lr_table.tsv"
    if not fixture.exists():
        check("gate4 fails if PROTOCOL.md's replicate count and the output's disagree", False,
              f"{fixture} missing")
        return
    proc = run(["gates/gate4_statistics.py", "--lr-table", str(fixture)])
    ok = proc.returncode == 1 and "n_replicates=500 != expected 2000" in proc.stdout
    check(
        "gate4 fails if PROTOCOL.md's replicate count and the output's disagree",
        ok,
        f"exit={proc.returncode}; live re-run against the real repo PROTOCOL.md (no override passed)",
    )


def criterion_3_every_truth_quantity_has_scope_status() -> None:
    truth = ROOT / "SIMULATED_TRUTH.tsv"
    recovered = ROOT / "SIMULATED_loh_validation" / "SIMULATED_recovered_quantities.tsv"
    scope = ROOT / "SIMULATED_loh_validation" / "SIMULATED_recovery_scope.tsv"
    if not (truth.exists() and recovered.exists() and scope.exists()):
        check("every SIMULATED_TRUTH.tsv row appears in the recovery table with a scope status", False,
              f"required input missing: truth={truth.exists()}, recovered={recovered.exists()}, scope={scope.exists()}")
        return

    proc = run([
        "gates/gate6_recovery.py", "--truth", str(truth), "--recovered", str(recovered),
        "--scope", str(scope), "--outdir", str(ROOT),
    ])
    recovery_table = ROOT / "SIMULATED_RECOVERY_TABLE.tsv"
    if not recovery_table.exists():
        check("every SIMULATED_TRUTH.tsv row appears in the recovery table with a scope status", False,
              "gate6 did not emit SIMULATED_RECOVERY_TABLE.tsv")
        return

    truth_quantities = {r["quantity"] for r in read_tsv(truth)}
    table_rows = {r["quantity"]: r for r in read_tsv(recovery_table)}
    missing_from_table = truth_quantities - set(table_rows)
    missing_scope_status = [q for q in truth_quantities if q in table_rows and not table_rows[q].get("scope_status", "").strip()]

    ok = not missing_from_table and not missing_scope_status
    check(
        "every SIMULATED_TRUTH.tsv row appears in the recovery table with a scope status",
        ok,
        f"{len(truth_quantities)} truth quantities; missing_from_recovery_table={sorted(missing_from_table)}; "
        f"rows_with_blank_scope_status={missing_scope_status}; gate6 live re-run exit={proc.returncode}",
    )


PASSAGE_1_MARKER = "Snapshot pin rule:"
PASSAGE_1_FIXED_SUBSTRING = "BENCHMARKS.tsv` row `CLINVAR01`"
PASSAGE_1_OLD_BROKEN_SUBSTRING = "mis-cited `BENCHMARKS_NOTES.md`"
PASSAGE_2_SUBSTRING = "gnomAD release pin rule:** identical procedure to §4.1's ClinVar"


def criterion_4_two_passages_quoted() -> None:
    if not (PROTOCOL.exists() and HOUSEKEEPING.exists()):
        check("the two reworded PROTOCOL.md passages are quoted for human reading", False,
              f"PROTOCOL.md exists={PROTOCOL.exists()}, GATE_HOUSEKEEPING.md exists={HOUSEKEEPING.exists()}")
        return

    protocol_text = PROTOCOL.read_text(encoding="utf-8")
    housekeeping_text = HOUSEKEEPING.read_text(encoding="utf-8")

    passage_1_live_and_fixed = PASSAGE_1_MARKER in protocol_text and PASSAGE_1_FIXED_SUBSTRING in protocol_text
    passage_2_live = PASSAGE_2_SUBSTRING in protocol_text
    passage_1_quoted_in_doc = PASSAGE_1_FIXED_SUBSTRING in housekeeping_text and PASSAGE_1_OLD_BROKEN_SUBSTRING in housekeeping_text
    passage_2_quoted_in_doc = PASSAGE_2_SUBSTRING in housekeeping_text

    ok = passage_1_live_and_fixed and passage_2_live and passage_1_quoted_in_doc and passage_2_quoted_in_doc
    check(
        "the two reworded PROTOCOL.md passages are quoted for human reading",
        ok,
        f"passage_1 (ClinVar §4.1) live in PROTOCOL.md and fixed={passage_1_live_and_fixed}, "
        f"passage_2 (gnomAD §4.2) live in PROTOCOL.md={passage_2_live}, "
        f"both quoted (before/after for passage 1) in GATE_HOUSEKEEPING.md={passage_1_quoted_in_doc and passage_2_quoted_in_doc}",
    )

    if ok:
        print("\n--- Passage 1 (PROTOCOL.md §4.1, ClinVar Snapshot pin rule) — BEFORE this fix ---")
        print(
            'Snapshot pin rule: the ClinVar release used is the most recent monthly archived '
            'release (first-Thursday-of-month release, per `BENCHMARKS_NOTES.md`) confirmed live '
            'with a resolving URL and timestamp within 7 days before Stage 0 execution begins (S10). '
            'If no such confirmation is obtainable, execution halts at Stage 0 and does not proceed '
            'with an unpinned or guessed release (Standing Rule 3). This is a fully specified rule '
            'rather than an open question -- it does not depend on the data under analysis, only on '
            'the calendar date of execution.\n'
            '[DEFECT: cites BENCHMARKS_NOTES.md for the "first-Thursday-of-month" claim, but that '
            'file never contained it -- confirmed by grep, zero hits, before this fix.]'
        )
        print("\n--- Passage 1 — AFTER this fix (current PROTOCOL.md text) ---")
        # Print the live paragraph straight out of PROTOCOL.md so this is never a stale transcription.
        start = protocol_text.index(PASSAGE_1_MARKER) - len("- **")
        end = protocol_text.index("\n\n", start)
        print(protocol_text[start:end].strip())

        print("\n--- Passage 2 (PROTOCOL.md §4.2, gnomAD release pin rule) — unchanged, verified sound ---")
        start2 = protocol_text.index("gnomAD release pin rule:") - len("- **")
        end2 = protocol_text.index("\n\n", start2)
        print(protocol_text[start2:end2].strip())


def main() -> None:
    criterion_1_gate3_two_floors_with_source()
    criterion_2_gate4_fails_on_disagreement()
    criterion_3_every_truth_quantity_has_scope_status()
    criterion_4_two_passages_quoted()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
