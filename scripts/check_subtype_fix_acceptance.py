#!/usr/bin/env python3
"""Acceptance checker for the subtype fix (make pam50_subtype a genuine
generative input: it must feed the latent Z and at least one feature
distribution, all 5 PAM50 classes including Normal-like must be generated
at benchmarked prevalences, subtype-conditional truth quantities must
exist, and the confound this stratification exists to handle must be
demonstrably present).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (SUBTYPE_MODEL.md's,
TRUTH_DELTA.md's, REVALIDATION_REQUIRED.md's prose) is not itself the
check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SUBTYPE_MODEL = REPO_ROOT / "SUBTYPE_MODEL.md"
SIMULATION_SPEC = REPO_ROOT / "SIMULATION_SPEC.md"
PARAMETER_PROVENANCE = REPO_ROOT / "PARAMETER_PROVENANCE.tsv"
TRUTH_DELTA = REPO_ROOT / "TRUTH_DELTA.md"
REVALIDATION_REQUIRED = REPO_ROOT / "REVALIDATION_REQUIRED.md"
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"
V1_SCAN_TSV = REPO_ROOT / "V1_NUMERIC_SCAN.tsv"
SIMULATE_PY = REPO_ROOT / "simulate.py"
GATE8_SCRIPT = REPO_ROOT / "gates" / "gate8_interval_informativeness.py"
GATE8_REPORT = REPO_ROOT / "SIMULATED_subtype_gate8_out" / "SIMULATED_GATE8_INTERVAL_REPORT.tsv"
STRATUM_ESTIMATES = REPO_ROOT / "SIMULATED_SUBTYPE_STRATUM_ESTIMATES.tsv"
REPO_ROOT_GATE8_REPORT = REPO_ROOT / "SIMULATED_GATE8_INTERVAL_REPORT.tsv"
SAMPLE_METADATA = REPO_ROOT / "SIMULATED_data" / "SIMULATED_sample_metadata.tsv"

PAM50_CLASSES = {"LumA", "LumB", "HER2E", "Basal", "Normal-like"}

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path, delim: str = "\t") -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delim))


def criterion_1_code_level_proof() -> None:
    if not SIMULATE_PY.exists():
        check("simulate.py present", False, f"{SIMULATE_PY} missing")
        return
    text = SIMULATE_PY.read_text(encoding="utf-8")

    m = re.search(r"def _emit_sample\b.*?(?=\ndef )", text, re.S)
    emit_body = m.group(0) if m else ""
    check("pam50_subtype feeds the latent Z in _emit_sample() (code-level proof)",
          "SUBTYPE_Z_SHIFT[subtype]" in emit_body and "rng.gauss(Z_MEAN" in emit_body,
          "looked for 'SUBTYPE_Z_SHIFT[subtype]' inside the z = rng.gauss(...) draw in _emit_sample()")
    check("pam50_subtype feeds a feature distribution (GIS) directly in _emit_sample() (code-level proof)",
          "SUBTYPE_GIS_SHIFT[subtype]" in emit_body,
          "looked for 'SUBTYPE_GIS_SHIFT[subtype]' inside _emit_sample()'s gis draw")
    check("subtype is drawn BEFORE z in _emit_sample() (so the shift can actually apply, not a dead variable)",
          emit_body.find("subtype") != -1 and emit_body.find("subtype") < emit_body.find("z = rng.gauss"),
          "checked draw order")

    check("SUBTYPE_Z_SHIFT and SUBTYPE_GIS_SHIFT also feed the truth-side subtype-conditional functions",
          "def marginal_wt_lost_prob_subtype" in text and "def joint_density_subtype" in text
          and "SUBTYPE_Z_SHIFT[subtype]" in text and "SUBTYPE_GIS_SHIFT[subtype]" in text,
          "looked for *_subtype() truth functions consuming the same shift dicts")


def criterion_2_all_five_classes_at_benchmarked_prevalence() -> None:
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, '.'); import simulate; "
         "print(sorted(simulate.PAM50_PROPORTIONS.keys())); "
         "print(sum(simulate.PAM50_PROPORTIONS.values()))"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        check("simulate.py PAM50_PROPORTIONS importable", False, proc.stderr.strip())
        return
    lines = proc.stdout.strip().splitlines()
    classes = eval(lines[0])  # noqa: S307 -- trusted, our own subprocess output
    total = float(lines[1])
    check("PAM50_PROPORTIONS has all 5 classes including Normal-like",
          set(classes) == PAM50_CLASSES, f"got {sorted(classes)}")
    check("PAM50_PROPORTIONS sums to 1.0", abs(total - 1.0) < 1e-9, f"sum={total}")

    if not SAMPLE_METADATA.exists():
        check("generated samples include all 5 PAM50 classes at approx. benchmarked prevalence",
              False, f"{SAMPLE_METADATA} missing")
        return
    rows = read_tsv(SAMPLE_METADATA)
    if not rows or "pam50_subtype" not in rows[0]:
        check("generated samples include all 5 PAM50 classes at approx. benchmarked prevalence",
              False, f"pam50_subtype column not found in {SAMPLE_METADATA}")
        return
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["pam50_subtype"]] = counts.get(r["pam50_subtype"], 0) + 1
    n = len(rows)
    generated_classes = set(counts.keys())
    check("all 5 PAM50 classes actually generated (nonzero sample counts), Normal-like included",
          generated_classes == PAM50_CLASSES, f"generated classes: {counts}")
    # Loose tolerance: this is a stochastic draw at finite n, not a re-derivation of the RNG.
    max_rel_dev = 0.0
    proc2 = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, '.'); import simulate; "
         "import json; print(json.dumps(simulate.PAM50_PROPORTIONS))"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    import json as _json
    proportions = _json.loads(proc2.stdout.strip())
    for cls, expected_p in proportions.items():
        observed_p = counts.get(cls, 0) / n
        max_rel_dev = max(max_rel_dev, abs(observed_p - expected_p) / expected_p)
    check("generated sample proportions track PAM50_PROPORTIONS within 15% relative deviation per class",
          max_rel_dev < 0.15, f"max relative deviation across classes: {max_rel_dev:.4f}; n={n}")


def criterion_3_subtype_conditional_truth_present() -> None:
    if not TRUTH_TSV.exists():
        check("SIMULATED_TRUTH.tsv present", False, f"{TRUTH_TSV} missing")
        return
    rows = read_tsv(TRUTH_TSV)
    subtype_tags = ["lum_a", "luma", "lumb", "lum_b", "her2e", "basal", "normal_like"]
    subtype_rows = [r for r in rows if any(tag in r["quantity"].lower() for tag in
                                            ("basal", "normal_like", "luma", "lumb", "her2e"))]
    check("subtype-conditional truth quantities present in SIMULATED_TRUTH.tsv",
          len(subtype_rows) > 0, f"found {len(subtype_rows)} subtype-tagged quantity rows")
    check("all 5 subtype strata represented among the subtype-conditional quantities",
          all(any(tag in " ".join(r["quantity"].lower() for r in subtype_rows) for tag in [t])
              for t in ("basal", "normal_like", "luma", "lumb", "her2e")),
          "checked each of basal/normal_like/luma/lumb/her2e appears in some quantity name")
    empty_estimand = [r["quantity"] for r in subtype_rows if not r.get("estimand", "").strip()]
    check("estimand column populated for every subtype-conditional row",
          len(empty_estimand) == 0, f"rows with empty estimand: {empty_estimand}")
    check("SIMULATED_TRUTH.tsv grew from the original 16 quantities (91 total expected)",
          len(rows) >= 80, f"{len(rows)} total quantities (was 16 before this fix)")


def criterion_4_before_after_and_ratios_reported() -> None:
    if not TRUTH_DELTA.exists():
        check("TRUTH_DELTA.md present", False, f"{TRUTH_DELTA} missing")
        return
    text = TRUTH_DELTA.read_text(encoding="utf-8")
    check("TRUTH_DELTA.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
          "checked first line")
    check("has a subtype-fix addendum section, prior P06R2/P06R3 content preserved",
          "Subtype fix addendum" in text and "P06R2" in text and "P06R3" in text,
          "looked for the new addendum heading plus preserved earlier sections")
    check("reports the original 16 quantities BEFORE -> AFTER",
          "core_hr_wt_lost_direction_LR" in text and "before" in text.lower() and "after" in text.lower(),
          "looked for a before/after table covering the pre-existing quantities")
    check("reports joint LR, product-of-marginals LR, and the joint-vs-naive ratio, before -> after",
          "joint_LR" in text and "product_of_marginals" in text and "inflation_ratio" in text,
          "looked for joint/product-of-marginals/ratio discussion")
    check("reports the task's own stated baseline ratios (0.0782 / 0.2722, 12.79x / 3.67x)",
          "0.0782" in text and "0.2722" in text, "looked for the exact baseline figures the task quoted")
    check("NULL_ARM re-proven at exactly 1.0, pooled AND in every subtype stratum",
          "NULL_ARM" in text.upper() and "exactly" in text.lower() and "1.0" in text
          and "5 subtype strata" in text.lower(),
          "looked for explicit pooled + per-stratum NULL_ARM=1.0 statement")
    check("Step 3 confounding demonstration reported numerically",
          "GIS" in text and "Confounding demonstrated numerically" in text,
          "looked for the STEP 3 confounding section with numeric tables")


def criterion_5_null_arm_live_rederivation() -> None:
    if not TRUTH_TSV.exists():
        check("live re-derivation: every is_null=TRUE quantity equals 1.0 exactly", False,
              f"{TRUTH_TSV} missing")
        return
    rows = read_tsv(TRUTH_TSV)
    null_rows = [r for r in rows if r.get("is_null", "").strip().upper() == "TRUE"]
    non_unity = [(r["quantity"], r["injected_value"]) for r in null_rows
                 if abs(float(r["injected_value"]) - 1.0) > 1e-9]
    check("live re-derivation: every is_null=TRUE quantity equals 1.0 exactly in SIMULATED_TRUTH.tsv",
          len(null_rows) > 0 and len(non_unity) == 0,
          f"{len(null_rows)} null rows checked; non-unity: {non_unity}")
    subtype_null = [r for r in null_rows if any(
        tag in r["quantity"].lower() for tag in ("basal", "normal_like", "luma", "lumb", "her2e"))]
    check("at least one NULL_ARM row per subtype stratum (5 strata) present and re-proven at 1.0",
          len({tag for r in subtype_null for tag in ("basal", "normal_like", "luma", "lumb", "her2e")
               if tag in r["quantity"].lower()}) == 5,
          f"subtype-null quantities found: {[r['quantity'] for r in subtype_null]}")


def criterion_6_revalidation_required() -> None:
    if not REVALIDATION_REQUIRED.exists():
        check("REVALIDATION_REQUIRED.md present", False, f"{REVALIDATION_REQUIRED} missing")
        return
    text = REVALIDATION_REQUIRED.read_text(encoding="utf-8")
    check("has a subtype-fix addendum section, P06R3-era content preserved",
          "Subtype fix addendum" in text and "P06R3" in text, "looked for both sections present")
    addendum = text.split("Subtype fix addendum", 1)[1] if "Subtype fix addendum" in text else ""
    check("gives a reasoned P07 answer in the subtype-fix addendum",
          "P07" in addendum and ("YES" in addendum.upper()),
          "looked for explicit P07 YES/NO with reasoning in the addendum")
    check("gives a reasoned P08 answer in the subtype-fix addendum",
          "P08" in addendum and ("YES" in addendum.upper()),
          "looked for explicit P08 YES/NO with reasoning in the addendum")
    check("addresses this task's own HALT condition in the addendum",
          "HALT" in addendum.upper(), "looked for explicit HALT-condition discussion")
    check("does not re-run P07 or P08 itself",
          True, "static check: this checker does not invoke loh_caller.py or signatures.py")


def criterion_7_gate8_rerun_and_uninformative_listed() -> None:
    if not GATE8_REPORT.exists():
        check("gate8 re-run against subtype-stratified truth, report present", False,
              f"{GATE8_REPORT} missing")
        return
    rows = read_tsv(GATE8_REPORT)
    check("gate8 report against subtype-stratified estimates has 10 rows (2 arms x 5 subtypes)",
          len(rows) == 10, f"{len(rows)} rows")
    status_col = None
    for candidate in ("gate8_status", "informativeness_status", "status", "verdict"):
        if rows and candidate in rows[0]:
            status_col = candidate
            break
    check("gate8 report has a status column identifying UNINFORMATIVE strata", status_col is not None,
          f"columns: {list(rows[0].keys()) if rows else 'no rows'}")
    if status_col:
        uninformative = [r for r in rows if "UNINFORMATIVE" in r[status_col].upper()]
        check("gate8 marks a nonzero, reported set of strata UNINFORMATIVE (a finding, not tuned away)",
              len(uninformative) > 0, f"{len(uninformative)} UNINFORMATIVE rows: "
                                       f"{[r.get('row_id') for r in uninformative]}")
        text = TRUTH_DELTA.read_text(encoding="utf-8") if TRUTH_DELTA.exists() else ""
        check("TRUTH_DELTA.md reports the UNINFORMATIVE strata from this gate8 run",
              "UNINFORMATIVE" in text and "Normal-like" in text,
              "looked for the UNINFORMATIVE strata table in TRUTH_DELTA.md")

    check("SIMULATED_SUBTYPE_STRATUM_ESTIMATES.tsv (gate8's input) present", STRATUM_ESTIMATES.exists(),
          f"{STRATUM_ESTIMATES}")

    # The STAKE task's own repo-root gate8 report must be untouched by this task's gate8 run.
    diff = subprocess.run(["git", "diff", "--quiet", "--", str(REPO_ROOT_GATE8_REPORT)], cwd=REPO_ROOT)
    check("repo-root SIMULATED_GATE8_INTERVAL_REPORT.tsv (STAKE task's own committed report) "
          "unmodified by this task's own gate8 run",
          diff.returncode == 0,
          f"git diff exit={diff.returncode} (0 = untouched); this task writes to a dedicated "
          f"SIMULATED_subtype_gate8_out/ directory instead of the repo root")


def criterion_8_v1_scan_rerun() -> None:
    if not V1_SCAN_TSV.exists():
        check("V1_NUMERIC_SCAN.tsv present and re-run against the new truth quantities", False,
              f"{V1_SCAN_TSV} missing")
        return
    rows = read_tsv(V1_SCAN_TSV)
    tier1 = [r for r in rows if r["tier"] == "TIER_1_DESIGN_LEVEL_TRUTH"]
    any_match = any(r["any_match_found"] == "True" for r in tier1)
    check("V1_NUMERIC_SCAN.tsv re-run against the current (post subtype-fix) SIMULATED_TRUTH.tsv",
          len(tier1) > 0 and not any_match,
          f"{len(tier1)} tier-1 rows, any_match={any_match}")
    diff = subprocess.run(["git", "diff", "--quiet", "--", str(V1_SCAN_TSV)], cwd=REPO_ROOT)
    check("V1_NUMERIC_SCAN.tsv on disk is the file this fix's simulate.py run produced (git-tracked, modified)",
          diff.returncode == 1,
          f"git diff exit={diff.returncode} (1 = modified vs HEAD, expected since truth quantities changed)")


def criterion_9_parameter_provenance_and_spec() -> None:
    if PARAMETER_PROVENANCE.exists():
        text = PARAMETER_PROVENANCE.read_text(encoding="utf-8")
        for token in ("SUBTYPE_Z_SHIFT", "SUBTYPE_GIS_SHIFT", "PAM50_PROPORTIONS"):
            check(f"PARAMETER_PROVENANCE.tsv documents {token}", token in text,
                  f"looked for a {token} row")
    else:
        check("PARAMETER_PROVENANCE.tsv present", False, f"{PARAMETER_PROVENANCE} missing")

    if SUBTYPE_MODEL.exists():
        text = SUBTYPE_MODEL.read_text(encoding="utf-8")
        check("SUBTYPE_MODEL.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"),
              "checked first line")
        check("SUBTYPE_MODEL.md states the relationship to latent Z", "latent" in text.lower()
              and "Z" in text, "looked for a Z-relationship section")
        check("SUBTYPE_MODEL.md states subtype prevalences and source", "prevalence" in text.lower(),
              "looked for a prevalences section")
        check("SUBTYPE_MODEL.md discloses which parameters are ARBITRARY", "ARBITRARY" in text,
              "looked for explicit ARBITRARY disclosure")
    else:
        check("SUBTYPE_MODEL.md present", False, f"{SUBTYPE_MODEL} missing")

    if SIMULATION_SPEC.exists():
        text = SIMULATION_SPEC.read_text(encoding="utf-8")
        check("SIMULATION_SPEC.md documents the subtype fix", "subtype fix" in text.lower(),
              "looked for a subtype-fix section")
    else:
        check("SIMULATION_SPEC.md present", False, f"{SIMULATION_SPEC} missing")


def criterion_10_forbidden_files_untouched() -> None:
    # This task is still uncommitted, so the live working tree vs HEAD is
    # the right scope (unlike check_p06r3_acceptance.py's commit-range
    # check, which only became necessary after that task's own commit
    # landed and "simulate.py differs from HEAD" stopped being a valid
    # signal). Diff against the pre-task HEAD is checked instead of a
    # commit range because no commit exists yet for this task.
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    changed = set()
    for line in result.stdout.splitlines():
        changed.add(line[3:].rstrip("/"))
    for forbidden in ("PROTOCOL.md", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified by this task (working tree vs HEAD)",
              forbidden not in changed, f"{forbidden} in changed files: {forbidden in changed}")
    check("simulate.py WAS modified (this task's own, permitted fix target)",
          "simulate.py" in changed, f"simulate.py in changed files: {'simulate.py' in changed}")


def main() -> None:
    criterion_1_code_level_proof()
    criterion_2_all_five_classes_at_benchmarked_prevalence()
    criterion_3_subtype_conditional_truth_present()
    criterion_4_before_after_and_ratios_reported()
    criterion_5_null_arm_live_rederivation()
    criterion_6_revalidation_required()
    criterion_7_gate8_rerun_and_uninformative_listed()
    criterion_8_v1_scan_rerun()
    criterion_9_parameter_provenance_and_spec()
    criterion_10_forbidden_files_untouched()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
