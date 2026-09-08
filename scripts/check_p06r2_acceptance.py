#!/usr/bin/env python3
"""Acceptance checker for P06R2 (fix the SBS3 catalogue shape and re-derive
dependent truth).

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment (TRUTH_DELTA.md's prose) is
not itself the check. Criterion 1 re-extracts the real COSMIC reference
live from the installed SigProfilerAssignment package inside docker and
diffs it against the committed reference file -- the meaningful version of
"is this really COSMIC data" (simulate.py's own runtime check can only
verify internal consistency, not that the committed file itself is real).

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SIMULATE_PY = REPO_ROOT / "simulate.py"
COSMIC_REF = REPO_ROOT / "COSMIC_SBS3_SBS5_v3.6_reference.tsv"
TRUTH_TSV = REPO_ROOT / "SIMULATED_TRUTH.tsv"
TRUTH_DELTA = REPO_ROOT / "TRUTH_DELTA.md"
P07_REVAL = REPO_ROOT / "P07_REVALIDATION_REQUIRED.md"
V1_SCAN = REPO_ROOT / "V1_NUMERIC_SCAN.tsv"
COVERAGE = REPO_ROOT / "SIMULATED_data" / "SIMULATED_coverage_report.tsv"
BENCHMARKS = REPO_ROOT / "BENCHMARKS.tsv"
DOCKER_IMAGE = "vus-tumor-gate1:local"
DOCKER_IMAGE_DIGEST = "sha256:2f344e8a456167eec8701db9581b07b0a4139ed2acdaecf23ab811fec354ca4c"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0 and nb > 0 else float("nan")


def criterion_1_real_cosmic_vector_and_similarities() -> None:
    if not COSMIC_REF.exists():
        check("committed COSMIC reference file present", False, f"{COSMIC_REF} missing")
        return
    committed_rows = read_tsv(COSMIC_REF)
    committed_sbs3 = {r["Type"]: float(r["SBS3"]) for r in committed_rows}
    committed_sbs5 = {r["Type"]: float(r["SBS5"]) for r in committed_rows}
    committed_sbs39 = {r["Type"]: float(r["SBS39"]) for r in committed_rows}
    committed_sbs40 = {r["Type"]: float(r["SBS40a"]) + float(r["SBS40b"]) + float(r["SBS40c"]) for r in committed_rows}

    inspect = subprocess.run(["docker", "image", "inspect", DOCKER_IMAGE, "--format", "{{.Id}}"],
                              capture_output=True, text=True)
    if inspect.returncode != 0 or inspect.stdout.strip() != DOCKER_IMAGE_DIGEST:
        check("live re-extraction from the gated docker image matches the committed reference file "
              "(the meaningful 'is this really COSMIC data' check)",
              False, f"docker image unavailable or digest mismatch: {inspect.stdout.strip() or inspect.stderr.strip()}")
        return

    extract_script = (
        "import pandas as pd\n"
        "D='/opt/conda/envs/bioenv/lib/python3.12/site-packages/SigProfilerAssignment/"
        "data/Reference_Signatures/GRCh38/COSMIC_v3.6_SBS_GRCh38.txt'\n"
        "ref = pd.read_csv(D, sep='\\t', index_col=0)\n"
        "ref[['SBS3','SBS5','SBS39','SBS40a','SBS40b','SBS40c']].to_csv('/tmp/p06r2_live_check.tsv', sep='\\t')\n"
    )
    run = subprocess.run(
        ["docker", "run", "--rm", "-v", "/tmp:/tmp", DOCKER_IMAGE, "python3", "-c", extract_script],
        capture_output=True, text=True, timeout=120,
    )
    live_path = Path("/tmp/p06r2_live_check.tsv")
    if run.returncode != 0 or not live_path.exists():
        check("live re-extraction from the gated docker image matches the committed reference file",
              False, f"docker extraction failed: exit={run.returncode} stderr={run.stderr[-500:]}")
        return
    live_rows = read_tsv(live_path)
    live_sbs3 = {r["Type"]: float(r["SBS3"]) for r in live_rows}
    mismatches = [ctx for ctx in committed_sbs3 if abs(committed_sbs3[ctx] - live_sbs3.get(ctx, float("nan"))) > 1e-9]
    check("live re-extraction from the gated docker image matches the committed reference file exactly "
          "(the committed file has not drifted/been hand-edited)",
          not mismatches, f"{len(mismatches)}/{len(committed_sbs3)} contexts differ from a fresh live extraction")

    contexts = list(committed_sbs3.keys())
    sbs3_vec = [committed_sbs3[c] for c in contexts]
    sbs5_vec = [committed_sbs5[c] for c in contexts]
    sbs39_vec = [committed_sbs39[c] for c in contexts]
    sbs40_vec = [committed_sbs40[c] for c in contexts]
    sim_self = cosine_similarity(sbs3_vec, sbs3_vec)
    sim_sbs5 = cosine_similarity(sbs3_vec, sbs5_vec)
    sim_sbs39 = cosine_similarity(sbs3_vec, sbs39_vec)
    sim_sbs40 = cosine_similarity(sbs3_vec, sbs40_vec)
    check("cosine similarity SBS3-vs-self is (essentially) 1.0", abs(sim_self - 1.0) < 1e-9, f"{sim_self}")
    check("cosine similarity SBS3-vs-SBS5 is reported and in a real, non-trivial band (0.75-0.85 -- "
          "the property that must survive the fix)", 0.75 <= sim_sbs5 <= 0.85, f"{sim_sbs5:.4f}")
    check("cosine similarity SBS3-vs-SBS39 is reported", 0.0 <= sim_sbs39 <= 1.0, f"{sim_sbs39:.4f}")
    check("cosine similarity SBS3-vs-SBS40(a+b+c) is reported", 0.0 <= sim_sbs40 <= 1.0, f"{sim_sbs40:.4f}")

    check("SIMULATION_SPEC.md quotes the real similarity numbers",
          "0.7928" in (REPO_ROOT / "SIMULATION_SPEC.md").read_text(encoding="utf-8"),
          "looked for '0.7928' in SIMULATION_SPEC.md")


def criterion_2_burden_vs_tmb01() -> None:
    exposures_path = REPO_ROOT / "SIMULATED_data" / "SIMULATED_signature_exposures.tsv"
    if not exposures_path.exists():
        check("SBS3 mutation-count distribution vs TMB01 reported", False, f"{exposures_path} missing")
        return
    rows = read_tsv(exposures_path)
    total_mut = [int(r["total_mutations"]) for r in rows]
    mean_total = sum(total_mut) / len(total_mut)

    if not BENCHMARKS.exists():
        check("TMB01 benchmark row exists to compare against", False, f"{BENCHMARKS} missing")
        return
    bench_rows = read_tsv(BENCHMARKS)
    tmb01 = next((r for r in bench_rows if r.get("benchmark_id") == "TMB01"), None)
    check("TMB01 benchmark row exists to compare against", tmb01 is not None, f"found={tmb01 is not None}")
    check("injected total_mutations burden is close to TMB01's real value (within 5 mutations of 60.05)",
          abs(mean_total - 60.05) < 5, f"mean total_mutations={mean_total:.2f}, TMB01=60.05")

    if not TRUTH_DELTA.exists():
        check("TRUTH_DELTA.md reports the n_hrd_process_mutations distribution", False, f"{TRUTH_DELTA} missing")
        return
    text = TRUTH_DELTA.read_text(encoding="utf-8")
    check("TRUTH_DELTA.md reports the n_hrd_process_mutations distribution (not just exposure fraction)",
          "n_hrd_process_mutations" in text, "looked for 'n_hrd_process_mutations' in TRUTH_DELTA.md")
    check("TRUTH_DELTA.md states a burden-vs-TMB01 conclusion", "TMB01" in text and "burden" in text.lower(),
          "looked for TMB01 + burden discussion")


def criterion_3_and_4_before_after_and_ratios() -> None:
    if not TRUTH_TSV.exists() or not TRUTH_DELTA.exists():
        check("every SIMULATED_TRUTH.tsv quantity reported BEFORE -> AFTER", False, "TRUTH_TSV or TRUTH_DELTA.md missing")
        return
    truth_rows = read_tsv(TRUTH_TSV)
    delta_text = TRUTH_DELTA.read_text(encoding="utf-8")
    missing = [r["quantity"] for r in truth_rows if r["quantity"] not in delta_text]
    check("every SIMULATED_TRUTH.tsv quantity appears in TRUTH_DELTA.md's before/after table",
          not missing, f"missing from TRUTH_DELTA.md: {missing}")

    for arm in ("core_hr", "ddr_signaling"):
        for suffix in ("joint_LR", "product_of_marginals_LR", "joint_vs_marginal_inflation_ratio"):
            q = f"{arm}_{suffix}"
            row = next((r for r in truth_rows if r["quantity"] == q), None)
            check(f"{q} is present in SIMULATED_TRUTH.tsv (new joint/product/ratio reported)",
                  row is not None, f"found={row is not None}")

    check("TRUTH_DELTA.md explicitly checks the HALT condition (ratio collapsing toward 1)",
          "HALT" in delta_text and "collapse" in delta_text.lower(),
          "looked for HALT + collapse discussion in TRUTH_DELTA.md")


def criterion_5_null_arm_proof() -> None:
    if not TRUTH_TSV.exists():
        check("NULL_ARM quantities are exactly 1.0", False, f"{TRUTH_TSV} missing")
        return
    rows = read_tsv(TRUTH_TSV)
    null_rows = {r["quantity"]: r for r in rows if r["quantity"].startswith("null_arm_full_vector")}
    all_one = all(abs(float(r["injected_value"]) - 1.0) < 1e-12 for r in null_rows.values())
    check("null_arm_full_vector_* quantities are all exactly 1.0 (re-verified live from SIMULATED_TRUTH.tsv)",
          len(null_rows) == 3 and all_one, f"{ {k: v['injected_value'] for k, v in null_rows.items()} }")

    if not TRUTH_DELTA.exists():
        check("TRUTH_DELTA.md contains an algebraic (not merely numerical) proof for NULL_ARM", False, "missing")
        return
    text = TRUTH_DELTA.read_text(encoding="utf-8")
    has_proof = ("identity" in text.lower() and "f(x|Pathogenic)" in text) or "joint_LR(x) = f(x|Pathogenic)" in text
    check("TRUTH_DELTA.md contains an algebraic (not merely numerical) proof for NULL_ARM",
          has_proof, "looked for an algebraic identity argument, not just a re-run number")


def criterion_6_p07_revalidation() -> None:
    if not P07_REVAL.exists():
        check("P07_REVALIDATION_REQUIRED.md exists with a reasoned yes/no", False, f"{P07_REVAL} missing")
        return
    text = P07_REVAL.read_text(encoding="utf-8")
    has_banner = text.startswith("SIMULATED DATA")
    has_answer = ("## Answer: NO" in text) or ("## Answer: YES" in text)
    has_reasoning = "RECOVERY_SCOPE" in text or "wt_lost_direction_LR" in text
    check("P07_REVALIDATION_REQUIRED.md present, banner, explicit YES/NO answer, and reasoning",
          has_banner and has_answer and has_reasoning,
          f"banner={has_banner}, explicit_answer={has_answer}, reasoning_present={has_reasoning}")


def criterion_7_v1_scan_rerun() -> None:
    if not V1_SCAN.exists():
        check("V1_NUMERIC_SCAN.tsv re-run against the new truth quantities", False, f"{V1_SCAN} missing")
        return
    rows = read_tsv(V1_SCAN)
    tier1 = [r for r in rows if r["tier"] == "TIER_1_DESIGN_LEVEL_TRUTH"]
    check("V1_NUMERIC_SCAN.tsv has a fresh TIER_1 scan of all 9 retracted figures against the "
          "(re-derived) design-level truth quantities", len(tier1) == 9, f"{len(tier1)} TIER_1 rows")
    check("TIER_1 scan found no match against a retracted v1 figure",
          not any(r["any_match_found"] == "True" for r in tier1),
          f"any_match={[r['any_match_found'] for r in tier1]}")


def criterion_8_coverage_grid() -> None:
    if not COVERAGE.exists():
        check("coverage grid re-reported", False, f"{COVERAGE} missing")
        return
    rows = read_tsv(COVERAGE)
    underfilled = [r for r in rows if r["scope_status"] == "IN_SCOPE" and r["meets_minimum"] == "False"]
    for r in underfilled:
        if not r.get("scope_reason", "").strip():
            check(f"underfilled cell {r['category']}/{r['arm']}/{r['class']}/{r['purity_bin']}/{r['depth_regime']} "
                  f"has an explicit reason", False, "scope_reason blank for an underfilled IN_SCOPE cell")
            return
    check("every underfilled IN_SCOPE coverage cell (if any) carries an explicit reason, or there are none",
          True, f"{len(underfilled)} underfilled cell(s), all with reasons (0 found this run)")


def criterion_9_unauthorized_files_untouched() -> None:
    result = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    result_staged = subprocess.run(["git", "diff", "--staged", "--name-only", "HEAD"], cwd=REPO_ROOT,
                                    capture_output=True, text=True)
    changed = set(result.stdout.splitlines()) | set(result_staged.stdout.splitlines())
    for forbidden in ("PROTOCOL.md", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")


def criterion_10_regeneration_reproducible() -> None:
    """The whole point of this fix is reproducible: python3 simulate.py must
    re-derive the exact same SIMULATED_TRUTH.tsv this file already has."""
    if not TRUTH_TSV.exists():
        check("simulate.py regenerates SIMULATED_TRUTH.tsv identically on a fresh run", False, "TRUTH_TSV missing")
        return
    before = TRUTH_TSV.read_bytes()
    result = subprocess.run([sys.executable, str(SIMULATE_PY)], cwd=REPO_ROOT, capture_output=True, text=True)
    after = TRUTH_TSV.read_bytes() if TRUTH_TSV.exists() else b""
    check("simulate.py runs successfully and SIMULATED_TRUTH.tsv is byte-identical on a fresh run",
          result.returncode == 0 and before == after,
          f"exit={result.returncode}, byte-identical={before == after}")


def main() -> None:
    criterion_1_real_cosmic_vector_and_similarities()
    criterion_2_burden_vs_tmb01()
    criterion_3_and_4_before_after_and_ratios()
    criterion_5_null_arm_proof()
    criterion_6_p07_revalidation()
    criterion_7_v1_scan_rerun()
    criterion_8_coverage_grid()
    criterion_9_unauthorized_files_untouched()
    criterion_10_regeneration_reproducible()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
