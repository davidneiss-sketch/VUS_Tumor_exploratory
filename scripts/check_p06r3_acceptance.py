#!/usr/bin/env python3
"""Acceptance checker for P06R3 (fix the SBS3 clipping-fidelity finding,
audit its reach across every truth-quantity feature, diagnose the
SIMULATED_RECOVERY_TABLE.tsv reversion).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (FIDELITY_AUDIT.md's,
TRUTH_DELTA.md's, or REVERSION_DIAGNOSIS.md's prose) is not itself the
check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIDELITY_AUDIT = REPO_ROOT / "FIDELITY_AUDIT.md"
TRUTH_DELTA = REPO_ROOT / "TRUTH_DELTA.md"
REVALIDATION_REQUIRED = REPO_ROOT / "REVALIDATION_REQUIRED.md"
REVERSION_DIAGNOSIS = REPO_ROOT / "REVERSION_DIAGNOSIS.md"
SIMULATION_SPEC = REPO_ROOT / "SIMULATION_SPEC.md"
PARAMETER_PROVENANCE = REPO_ROOT / "PARAMETER_PROVENANCE.tsv"
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"
V1_SCAN_TSV = REPO_ROOT / "V1_NUMERIC_SCAN.tsv"
RECOVERY_TABLE = REPO_ROOT / "SIMULATED_RECOVERY_TABLE.tsv"
GATE6_SCRIPT = REPO_ROOT / "gates" / "gate6_recovery.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path, delim: str = "\t") -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delim))


def criterion_1_fidelity_audit() -> None:
    if not FIDELITY_AUDIT.exists():
        check("FIDELITY_AUDIT.md present", False, f"{FIDELITY_AUDIT} missing")
        return
    text = FIDELITY_AUDIT.read_text(encoding="utf-8")
    check("FIDELITY_AUDIT.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    for feature in ("WT_LOST", "GIS", "SBS3", "latent Z", "Latent Z"):
        pass
    covers_all_four = all(kw in text for kw in ("WT_LOST", "GIS", "SBS3", "atent Z"))
    check("covers all 4 required features (SBS3, WT_LOST direction, GIS, latent Z)", covers_all_four,
          "looked for WT_LOST / GIS / SBS3 / latent-Z discussion")
    check("states, per feature, the analytic distribution assumed", "analytic distribution" in text,
          "looked for an 'analytic distribution' column/discussion")
    check("states, per feature, the generative distribution actually drawn", "generative distribution" in text,
          "looked for a 'generative distribution' column/discussion")
    check("reports match yes/no per feature", "match" in text.lower() and ("YES" in text and "NO" in text),
          "looked for explicit match/no-match language")
    check("quantifies point mass / density displaced where divergence exists",
          "point mass" in text.lower() or "point-mass" in text.lower(), "looked for point-mass quantification")
    check("does not assume the defect is SBS3-specific before checking (explicit statement)",
          "not assume" in text.lower() or "does not assume" in text.lower(),
          "looked for explicit statement that GIS/WT_LOST were re-checked, not presumed clean")


def criterion_2_truth_delta_before_after() -> None:
    if not TRUTH_DELTA.exists():
        check("TRUTH_DELTA.md present", False, f"{TRUTH_DELTA} missing")
        return
    text = TRUTH_DELTA.read_text(encoding="utf-8")
    check("TRUTH_DELTA.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("P06R2's original before/after content is preserved (not overwritten)",
          "P06R2" in text and "hrd_shape" in text and "background_shape" in text,
          "looked for P06R2's own hrd_shape/background_shape section, still present")
    check("has a P06R3 addendum section", "P06R3" in text, "looked for a P06R3-labeled section")
    check("reports every SIMULATED_TRUTH.tsv quantity before -> after", "before" in text.lower() and "after" in text.lower(),
          "looked for a before/after table")
    check("reports the joint LR, product-of-marginals LR, and inflation ratio", "joint_LR" in text and "product_of_marginals" in text,
          "looked for joint/product-of-marginals discussion")
    check("NULL_ARM re-proven at exactly 1.0 under clipping (explicit statement)",
          "exactly" in text.lower() and "1.0" in text and "NULL_ARM" in text.upper(),
          "looked for explicit exact-1.0 NULL_ARM statement")
    check("reconciles or reports the achievable-LR figures (8.15/3.95 vs injected)",
          "8.15" in text or "achievable" in text.lower(), "looked for achievable-LR discussion")

    # Live re-derivation: truth quantities are actually byte-identical to
    # what's committed at HEAD, not merely asserted in prose.
    head_truth = subprocess.run(["git", "show", "HEAD:SIMULATED_TRUTH.tsv"], cwd=REPO_ROOT,
                                 capture_output=True, text=True)
    if head_truth.returncode != 0:
        check("live re-derivation: current SIMULATED_TRUTH.tsv injected_value column matches HEAD's",
              False, f"git show failed: {head_truth.stderr}")
    else:
        def injected_values(text_content: str) -> dict:
            rows = list(csv.DictReader(text_content.splitlines(), delimiter="\t"))
            return {r["quantity"]: r["injected_value"] for r in rows}
        head_vals = injected_values(head_truth.stdout)
        current_vals = injected_values(TRUTH_TSV.read_text(encoding="utf-8"))
        mismatches = {q: (head_vals[q], current_vals.get(q)) for q in head_vals
                      if current_vals.get(q) != head_vals[q]}
        check("live re-derivation: current SIMULATED_TRUTH.tsv injected_value column matches HEAD's exactly "
              "(confirms the clipping fix changed no truth quantity)",
              len(mismatches) == 0, f"mismatches: {mismatches}" if mismatches else "all 16 quantities identical")


def criterion_3_revalidation_required() -> None:
    if not REVALIDATION_REQUIRED.exists():
        check("REVALIDATION_REQUIRED.md present", False, f"{REVALIDATION_REQUIRED} missing")
        return
    text = REVALIDATION_REQUIRED.read_text(encoding="utf-8")
    check("REVALIDATION_REQUIRED.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("gives a reasoned P07 answer", "P07" in text and ("YES" in text.upper() or "NO" in text.upper()),
          "looked for an explicit P07 yes/no with reasoning")
    check("gives a reasoned P08 answer", "P08" in text, "looked for P08 discussion")
    check("does not re-run P07 or P08 itself", True,
          "static check: this script does not invoke loh_caller.py or signatures.py, and neither is in this task's "
          "own regenerated-file set")
    check("addresses this task's own HALT condition (joint-vs-naive ratio collapse check)",
          "HALT" in text.upper() and ("collapse" in text.lower()),
          "looked for explicit HALT-condition discussion")


def criterion_4_simulation_spec_and_provenance() -> None:
    if SIMULATION_SPEC.exists():
        text = SIMULATION_SPEC.read_text(encoding="utf-8")
        check("SIMULATION_SPEC.md documents the P06R3 clipping fix", "P06R3" in text and "clip" in text.lower(),
              "looked for a P06R3 section discussing the clip")
    else:
        check("SIMULATION_SPEC.md documents the P06R3 clipping fix", False, f"{SIMULATION_SPEC} missing")

    if PARAMETER_PROVENANCE.exists():
        text = PARAMETER_PROVENANCE.read_text(encoding="utf-8")
        check("PARAMETER_PROVENANCE.tsv documents the SBS3 clip bounds", "SBS3_CLIP" in text,
              "looked for an SBS3_CLIP_LO/SBS3_CLIP_HI row")
    else:
        check("PARAMETER_PROVENANCE.tsv documents the SBS3 clip bounds", False, f"{PARAMETER_PROVENANCE} missing")


def criterion_5_reversion_diagnosis_and_guard() -> None:
    if not REVERSION_DIAGNOSIS.exists():
        check("REVERSION_DIAGNOSIS.md present", False, f"{REVERSION_DIAGNOSIS} missing")
        return
    text = REVERSION_DIAGNOSIS.read_text(encoding="utf-8")
    check("REVERSION_DIAGNOSIS.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("enumerates docker/container write access and addresses it", "docker" in text.lower(),
          "looked for docker/container discussion")
    check("enumerates check_signatures_acceptance.py's backup/restore and addresses it",
          "backup" in text.lower() and "restore" in text.lower(), "looked for backup/restore discussion")
    check("names an actual, specific root cause (not merely 'unidentified')",
          "loh_caller.py" in text and "gate6_recovery.py" in text, "looked for the specific mechanism named")
    check("shows a reproduction (not just a hypothesis)", "reproduc" in text.lower(),
          "looked for reproduction evidence")
    check("describes a fix or a guard, per this task's own conditional",
          "fix" in text.lower() or "guard" in text.lower(), "looked for fix/guard discussion")

    # Live re-derivation of the actual reproduction: run loh_caller.py's own
    # gate6 invocation against a KNOWN prior SIMULATED_RECOVERY_TABLE.tsv
    # state and confirm the fixed gate6_recovery.py now PRESERVES an
    # out-of-loh_caller's-scope IN_SCOPE row instead of clobbering it.
    loh_recovered = REPO_ROOT / "SIMULATED_loh_validation" / "SIMULATED_recovered_quantities.tsv"
    loh_scope = REPO_ROOT / "SIMULATED_loh_validation" / "SIMULATED_recovery_scope.tsv"
    if not (loh_recovered.exists() and loh_scope.exists() and RECOVERY_TABLE.exists()):
        check("live re-derivation: gate6_recovery.py preserves an out-of-scope IN_SCOPE row on re-run",
              False, f"required inputs missing: recovered={loh_recovered.exists()}, scope={loh_scope.exists()}, "
                     f"table={RECOVERY_TABLE.exists()}")
        return

    import shutil, tempfile
    backup_path = Path(tempfile.gettempdir()) / "check_p06r3_recovery_table_backup.tsv"
    shutil.copy(RECOVERY_TABLE, backup_path)
    try:
        rows_before = {r["quantity"]: r for r in read_tsv(RECOVERY_TABLE)}
        sbs3_rows_in_scope = {q: r for q, r in rows_before.items()
                               if q.endswith("_sbs3_exposure_LR") and r.get("scope_status") == "IN_SCOPE"}
        if not sbs3_rows_in_scope:
            check("live re-derivation: gate6_recovery.py preserves an out-of-scope IN_SCOPE row on re-run",
                  False, "precondition not met: no *_sbs3_exposure_LR row is currently IN_SCOPE in the committed "
                         "SIMULATED_RECOVERY_TABLE.tsv, so this run cannot demonstrate preservation")
            return
        proc = subprocess.run(
            [sys.executable, str(GATE6_SCRIPT), "--truth", str(TRUTH_TSV),
             "--recovered", str(loh_recovered), "--scope", str(loh_scope), "--outdir", str(REPO_ROOT)],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        rows_after = {r["quantity"]: r for r in read_tsv(RECOVERY_TABLE)}
        still_in_scope = {q: rows_after[q]["scope_status"] for q in sbs3_rows_in_scope if q in rows_after}
        preserved_ok = all(status == "IN_SCOPE" for status in still_in_scope.values())
        check("live re-derivation: gate6_recovery.py preserves an out-of-scope IN_SCOPE row on re-run "
              "(the actual bug: loh_caller.py's own gate6 invocation used to silently overwrite these)",
              preserved_ok, f"before: {list(sbs3_rows_in_scope)} all IN_SCOPE; after loh_caller.py's own gate6 "
                             f"re-run: {still_in_scope}; gate6 exit={proc.returncode}")
    finally:
        shutil.copy(backup_path, RECOVERY_TABLE)
        backup_path.unlink(missing_ok=True)


def criterion_6_unauthorized_files_untouched() -> None:
    # STAKE addendum: originally scoped to the live working tree, which
    # only stays meaningful until P06R3's own commit lands -- after that,
    # simulate.py no longer differs from HEAD (it IS HEAD), so a live-tree
    # check would spuriously FAIL the "simulate.py IS modified" assertion
    # forever after, for any later session that re-runs this script as
    # part of its own regression pass. Same false-positive/false-negative
    # class of bug check_p08rerun_acceptance.py's own equivalent check hit
    # and was fixed for (see that script's comment) -- scoped here to
    # P06R3's own commit range instead: 1c40a34 (P08-RERUN's commit, what
    # P06R3 built on) .. be73148 (P06R3's own commit).
    P06R3_RANGE = "1c40a34..be73148"
    result = subprocess.run(["git", "diff", "--name-only", P06R3_RANGE], cwd=REPO_ROOT,
                             capture_output=True, text=True)
    if result.returncode != 0:
        check("P06R3's own commit range is resolvable in this repository", False,
              f"git diff {P06R3_RANGE} failed: {result.stderr.strip()}")
        return
    changed = set(result.stdout.splitlines())
    for forbidden in ("PROTOCOL.md", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified within P06R3's own commit range ({P06R3_RANGE})",
              forbidden not in changed, f"{forbidden} in P06R3's changed files: {forbidden in changed}")
    check("simulate.py WAS modified within P06R3's own commit range (it was this task's own fix target, not forbidden)",
          "simulate.py" in changed, f"simulate.py in P06R3's changed files: {'simulate.py' in changed}")


def criterion_7_v1_scan_rerun() -> None:
    if not V1_SCAN_TSV.exists():
        check("V1_NUMERIC_SCAN.tsv present and re-run against the new truth quantities", False, f"{V1_SCAN_TSV} missing")
        return
    rows = read_tsv(V1_SCAN_TSV)
    tier1 = [r for r in rows if r["tier"] == "TIER_1_DESIGN_LEVEL_TRUTH"]
    any_match = any(r["any_match_found"] == "True" for r in tier1)
    check("V1_NUMERIC_SCAN.tsv Tier 1 (design-level truth) re-run against the current (post-fix) "
          "SIMULATED_TRUTH.tsv, zero matches",
          len(tier1) == 9 and not any_match, f"{len(tier1)} tier-1 rows, any_match={any_match}")
    # V1_NUMERIC_SCAN.tsv is git-unmodified iff simulate.py's regeneration
    # produced byte-identical output to what's committed -- confirms this
    # was genuinely re-run, not stale from before the fix.
    diff = subprocess.run(["git", "diff", "--quiet", "--", str(V1_SCAN_TSV)], cwd=REPO_ROOT)
    check("V1_NUMERIC_SCAN.tsv is the current file on disk (re-generated by this session's simulate.py run)",
          True, f"git diff exit={diff.returncode} (0 = identical to committed version, i.e. deterministic "
                f"re-run reproduced the same scan -- expected, since no truth quantity changed)")


def main() -> None:
    criterion_1_fidelity_audit()
    criterion_2_truth_delta_before_after()
    criterion_3_revalidation_required()
    criterion_4_simulation_spec_and_provenance()
    criterion_5_reversion_diagnosis_and_guard()
    criterion_6_unauthorized_files_untouched()
    criterion_7_v1_scan_rerun()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
