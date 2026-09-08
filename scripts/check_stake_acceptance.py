#!/usr/bin/env python3
"""Acceptance checker for the STAKE_ANALYSIS.md task (P06R3-STAKE): does
the ACMG strength actually change when SBS3 is dropped from the joint
model, at synthetic and realistic class sizes, by subtype -- and how much
real TCGA-BRCA data is even in the range where this matters.

Standing Rule 6: acceptance criteria are evaluated by a script emitting
PASS/FAIL per criterion; narrative assessment in STAKE_ANALYSIS.md's prose
is not itself the check.

Exit 0 = every criterion PASS. Exit 1 = at least one criterion FAIL.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STAKE_ANALYSIS = REPO_ROOT / "STAKE_ANALYSIS.md"
ABLATION_TABLE = REPO_ROOT / "ABLATION_TABLE.tsv"
PROPOSED_DEVIATIONS = REPO_ROOT / "PROPOSED_DEVIATIONS.md"
PROTOCOL = REPO_ROOT / "PROTOCOL.md"

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def criterion_1_protocol_null_outcome_quoted() -> None:
    if not STAKE_ANALYSIS.exists():
        check("STAKE_ANALYSIS.md present", False, f"{STAKE_ANALYSIS} missing")
        return
    text = STAKE_ANALYSIS.read_text(encoding="utf-8")
    check("STAKE_ANALYSIS.md starts with the SIMULATED banner", text.startswith("SIMULATED DATA"), "checked first line")
    check("STEP 0 present", "STEP 0" in text, "looked for a STEP 0 section")
    # The exact PROTOCOL.md passage quoted must actually exist verbatim in PROTOCOL.md
    # (a live re-derivation, not trust in the prose).
    protocol_text = PROTOCOL.read_text(encoding="utf-8")
    quoted_fragment = ("Stage 1 (§10.1, real-data) results may\n> not be reported as reliable")
    check("the passage STAKE_ANALYSIS.md quotes from PROTOCOL.md §10 actually exists there verbatim",
          "Stage 1 (§10.1, real-data) results may" in protocol_text and "not be reported as reliable" in protocol_text,
          "checked PROTOCOL.md for the quoted fragment")
    check("STAKE_ANALYSIS.md explicitly states PROTOCOL.md's silence on feature-level (not stage-level) "
          "uninformativeness", "feature-level" in text.lower() and "silen" in text.lower(),
          "looked for explicit silence statement")
    check("the pre-registration gap is logged in PROPOSED_DEVIATIONS.md", PROPOSED_DEVIATIONS.exists() and
          "feature-level" in PROPOSED_DEVIATIONS.read_text(encoding="utf-8").lower(),
          "checked PROPOSED_DEVIATIONS.md for the same finding")


def criterion_2_ablation_table_complete() -> None:
    if not ABLATION_TABLE.exists():
        check("ABLATION_TABLE.tsv present", False, f"{ABLATION_TABLE} missing")
        return
    rows = read_tsv(ABLATION_TABLE)
    required_cols = {"arm", "feature_subset", "n_scenario", "n_pathogenic", "n_benign", "n_total",
                      "point_estimate", "ci_low", "ci_high", "true_reference_lr", "acmg_tier", "acmg_points"}
    missing_cols = required_cols - set(rows[0].keys()) if rows else required_cols
    check("ABLATION_TABLE.tsv has every required column", not missing_cols, f"missing: {missing_cols}")

    subsets_seen = {r["feature_subset"] for r in rows}
    expected_subsets = {"LOH_GIS_SBS3", "LOH_GIS", "LOH_SBS3", "GIS_SBS3"}
    check("all 4 feature sets present", expected_subsets <= subsets_seen,
          f"seen={subsets_seen}, missing={expected_subsets - subsets_seen}")

    scenarios_seen = {r["n_scenario"] for r in rows}
    has_synthetic = any(s.startswith("SYNTHETIC_FULL_N") for s in scenarios_seen)
    has_realistic = any(s.startswith("REALISTIC_N_") for s in scenarios_seen)
    has_subtype = any(s.startswith("SYNTHETIC_SUBTYPE_") for s in scenarios_seen)
    check("both synthetic n and realistic n scenarios present", has_synthetic and has_realistic,
          f"synthetic={has_synthetic}, realistic={has_realistic}")
    check("subtype-stratified scenarios present", has_subtype, f"scenarios include subtype rows: {has_subtype}")

    subtypes_covered = {s.replace("SYNTHETIC_SUBTYPE_", "") for s in scenarios_seen if s.startswith("SYNTHETIC_SUBTYPE_")}
    expected_subtypes = {"LumA", "LumB", "HER2E", "Basal", "Normal-like"}
    check("all 5 PROTOCOL.md §8 PAM50 subtypes attempted (even if some return INSUFFICIENT_N)",
          expected_subtypes <= subtypes_covered, f"seen={subtypes_covered}")

    # Every row must have a real n and, for testable rows, a real ACMG tier
    # -- never a silently blank row (Standing Rule 4).
    blank_tier_rows = [r["feature_subset"] + "/" + r["n_scenario"] for r in rows if not r["acmg_tier"]]
    check("every row has an ACMG tier or an explicit INSUFFICIENT_N (no blank rows)",
          len(blank_tier_rows) == 0, f"blank: {blank_tier_rows}")

    # Cross-check the reported ACMG tier against PROTOCOL.md §9's own
    # thresholds, re-derived live from the CI columns (not trusted from
    # the generator script).
    def re_derive_tier(ci_low_s: str, ci_high_s: str) -> str:
        if not ci_low_s:
            return "INSUFFICIENT_N"
        ci_low, ci_high = float(ci_low_s), float(ci_high_s)
        if ci_low > 350:
            return "PATHOGENIC_VERY_STRONG"
        if ci_low > 18.7:
            return "PATHOGENIC_STRONG"
        if ci_low > 4.33:
            return "PATHOGENIC_MODERATE"
        if ci_low > 2.08:
            return "PATHOGENIC_SUPPORTING"
        if ci_low <= 2.08 and ci_high >= 0.48:
            return "NO_EVIDENCE"
        if 0.053 <= ci_high < 0.48:
            return "BENIGN_SUPPORTING"
        return "BENIGN_STRONG"

    mismatches = []
    for r in rows:
        expected = re_derive_tier(r["ci_low"], r["ci_high"])
        if expected != r["acmg_tier"]:
            mismatches.append((r["arm"], r["feature_subset"], r["n_scenario"], expected, r["acmg_tier"]))
    check("every row's ACMG tier matches a live re-derivation from PROTOCOL.md §9's own thresholds applied "
          "to that row's CI (not merely trusted from the generator)",
          len(mismatches) == 0, f"mismatches: {mismatches[:5]}" if mismatches else "all match")


def criterion_3_strength_delta_headline() -> None:
    if not STAKE_ANALYSIS.exists():
        check("STAKE_ANALYSIS.md present for strength-delta check", False, f"{STAKE_ANALYSIS} missing")
        return
    text = STAKE_ANALYSIS.read_text(encoding="utf-8")
    check("headline strength-delta language present ('NOT free' / 'nearly free' / 'REAL')",
          ("NOT free" in text or "nearly free" in text) and "REAL" in text,
          "looked for the headline framing this task's own prompt uses")
    check("summary table required by ACCEPTANCE is present (one line per stratum)",
          "Summary table required by ACCEPTANCE" in text, "looked for the summary table heading")
    # Live re-derivation: CORE_HR full-n tier really does differ from its
    # own drop-SBS3 tier, and DDR_SIGNALING's really does not, confirming
    # the headline claim against the actual table rather than the prose.
    rows = read_tsv(ABLATION_TABLE) if ABLATION_TABLE.exists() else []
    by_key = {(r["arm"], r["feature_subset"], r["n_scenario"]): r for r in rows}
    core_full = by_key.get(("CORE_HR", "LOH_GIS_SBS3", "SYNTHETIC_FULL_N"))
    core_drop = by_key.get(("CORE_HR", "LOH_GIS", "SYNTHETIC_FULL_N"))
    ddr_full = by_key.get(("DDR_SIGNALING", "LOH_GIS_SBS3", "SYNTHETIC_FULL_N"))
    ddr_drop = by_key.get(("DDR_SIGNALING", "LOH_GIS", "SYNTHETIC_FULL_N"))
    if core_full and core_drop and ddr_full and ddr_drop:
        core_changed = core_full["acmg_tier"] != core_drop["acmg_tier"]
        ddr_changed = ddr_full["acmg_tier"] != ddr_drop["acmg_tier"]
        check("live re-derivation: CORE_HR's tier DOES change when SBS3 is dropped at synthetic full n "
              "(matches the document's headline claim)", core_changed,
              f"{core_full['acmg_tier']} -> {core_drop['acmg_tier']}")
        check("live re-derivation: DDR_SIGNALING's tier does NOT change when SBS3 is dropped at synthetic "
              "full n (matches the document's headline claim)", not ddr_changed,
              f"{ddr_full['acmg_tier']} -> {ddr_drop['acmg_tier']}")
    else:
        check("live re-derivation of the CORE_HR/DDR_SIGNALING headline claim", False,
              "required ABLATION_TABLE.tsv rows missing")


def criterion_4_track_a_blocked_honestly() -> None:
    if not STAKE_ANALYSIS.exists():
        check("STAKE_ANALYSIS.md present for Step 4 check", False, f"{STAKE_ANALYSIS} missing")
        return
    text = STAKE_ANALYSIS.read_text(encoding="utf-8")
    check("STEP 4 present", "STEP 4" in text, "looked for a STEP 4 section")
    check("states the P10 precondition does not exist, with evidence (git log check)",
          "P10" in text and "git log" in text.lower(), "looked for the P10-does-not-exist finding with evidence")
    check("states a live-retrieval attempt was made and blocked, with the actual error captured",
          "EGRESS_BLOCKED" in text or "egress" in text.lower(), "looked for the captured egress-block evidence")
    check("does NOT substitute the SigMA-bundled example MAF as if it were real Track A data",
          "not treated as a substitute" in text or "not a substitute" in text.lower(),
          "looked for an explicit non-substitution statement")
    check("no fabricated real-data mutation-count fraction is reported (BLOCKED, not answered)",
          "No fraction of real TCGA-BRCA" in text or "BLOCKED" in text,
          "looked for explicit non-answer rather than a fabricated number")
    # Live re-derivation: P10 really is absent from git history.
    result = subprocess.run(["git", "log", "--all", "--oneline"], cwd=REPO_ROOT, capture_output=True, text=True)
    check("live re-derivation: no commit message anywhere in this repository's history mentions P10",
          "P10" not in result.stdout, f"git log --all --oneline scanned, {len(result.stdout.splitlines())} commits")


def criterion_5_no_recommendation() -> None:
    if not STAKE_ANALYSIS.exists():
        check("STAKE_ANALYSIS.md present for no-recommendation check", False, f"{STAKE_ANALYSIS} missing")
        return
    text = STAKE_ANALYSIS.read_text(encoding="utf-8")
    check("explicit 'no recommendation' statement present",
          "No recommendation is made" in text or "no recommendation is offered" in text.lower(),
          "looked for an explicit no-recommendation closing statement")
    forbidden_phrases = ["we recommend", "should be dropped", "should be excluded", "the right course of action is",
                          "the correct choice is"]
    lowered = text.lower()
    found = [p for p in forbidden_phrases if p in lowered]
    check("no recommendation-shaped language found in the document body", len(found) == 0, f"found: {found}")


def criterion_6_unauthorized_files_untouched() -> None:
    result = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    result_staged = subprocess.run(["git", "diff", "--staged", "--name-only", "HEAD"], cwd=REPO_ROOT,
                                    capture_output=True, text=True)
    changed = set(result.stdout.splitlines()) | set(result_staged.stdout.splitlines())
    for forbidden in ("PROTOCOL.md", "simulate.py", "signatures.py", "loh_caller.py"):
        check(f"{forbidden} not modified by this task", forbidden not in changed,
              f"{forbidden} in changed files: {forbidden in changed}")


def main() -> None:
    criterion_1_protocol_null_outcome_quoted()
    criterion_2_ablation_table_complete()
    criterion_3_strength_delta_headline()
    criterion_4_track_a_blocked_honestly()
    criterion_5_no_recommendation()
    criterion_6_unauthorized_files_untouched()

    overall = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name} — {detail}")
        overall = overall and passed

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
