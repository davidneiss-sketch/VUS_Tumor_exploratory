#!/usr/bin/env python3
"""Acceptance check for PROTOCOL.md (Standing Rule 6): emits PASS/FAIL per
criterion rather than relying on narrative claims.

Criteria, derived from the task's ACCEPTANCE section and DO list:
  1. No threshold is left "to be determined" or "data-driven" (banned
     placeholder-phrase scan).
  2. Every DO-listed required section is present.
  3. The estimand declaration is present: states LR = P(E|Pathogenic) /
     P(E|Benign), and explicitly contrasts it with an odds ratio.
  4. The exact numeric OddsPath thresholds from BENCHMARKS.tsv appear,
     un-altered.
  5. Every numeric threshold the DO list asked for by name is present:
     purity floor + 2 sensitivity values, bootstrap replicate count,
     CV fold count, minimum stratum n, recovery-tolerance relative-bias
     bound.
  6. INSUFFICIENT_N is specified as the literal printed output below the
     minimum class size.
  7. Standing Rule 1's SIMULATED vocabulary is used for Stage 2, and Stage
     2 is explicitly barred from using the ACMG (§9) vocabulary.
  8. GATE1 FAIL / BLOCKED status for SigMA is disclosed, not silently
     dropped (Standing Rule 4/8 cross-check against GATE1.json).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "PROTOCOL.md"
GATE1 = ROOT / "GATE1.json"

results = []


def load_text():
    if not PROTOCOL.exists():
        print("[FAIL] PROTOCOL.md exists — file missing")
        sys.exit(1)
    return PROTOCOL.read_text()


BANNED_PHRASES = [
    r"\bTBD\b",
    r"\bto be determined\b",
    r"\bdata-driven\b",
    r"\bdata driven\b",
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bplaceholder\b",
    r"\bXXX\b",
]


def check_no_placeholders(text):
    hits = []
    for pat in BANNED_PHRASES:
        for m in re.finditer(pat, text, re.IGNORECASE):
            line_no = text[: m.start()].count("\n") + 1
            hits.append(f"{pat!r} at line {line_no}")
    if hits:
        results.append(("no unspecified/placeholder thresholds", False, "; ".join(hits)))
    else:
        results.append(("no unspecified/placeholder thresholds", True, "no banned placeholder phrases found"))


REQUIRED_SECTIONS = [
    ("Gene lists (CORE_HR and DDR_SIGNALING, separate)", [r"CORE_HR", r"DDR_SIGNALING"]),
    ("Sample selection rules, in order", [r"S1a", r"S8\b"]),
    ("Purity floor + two sensitivity values", [r"[Pp]urity floor", r"[Ss]ensitivity value 1", r"[Ss]ensitivity value 2"]),
    ("ClinVar review-status floor", [r"ClinVar review-status floor", r"gold star"]),
    ("gnomAD popmax ceiling", [r"gnomAD popmax ceiling", r"popmax"]),
    ("Circularity exclusion criteria", [r"[Cc]ircularity exclusion"]),
    ("LOH categories", [r"LOH categories", r"LOH_SECOND_HIT", r"LOH_NON_SECOND_HIT", r"LOH_AMBIGUOUS", r"NOT_EVALUABLE"]),
    ("Binomial VAF model", [r"[Bb]inomial VAF model", r"Binomial\(D"]),
    ("HRD components", [r"HRD-LOH", r"\bTAI\b", r"\bLST\b", r"GIS"]),
    ("Signature tools and COSMIC versions", [r"SigProfilerAssignment", r"SigMA", r"COSMIC"]),
    ("Second-hit sources", [r"[Ss]econd-hit sources", r"NO_SECOND_HIT_DETECTED"]),
    ("ESTIMAND DECLARATION", [r"ESTIMAND DECLARATION"]),
    ("Model spec", [r"kernel density", r"Jeffreys"]),
    ("Variant-grouped CV", [r"[Vv]ariant-grouped", r"k\s*=\s*5"]),
    ("Patient-clustered bootstrap with replicate count", [r"[Pp]atient-clustered bootstrap", r"B\s*=\s*2000"]),
    ("Stratification gene group x subtype, per gene where n permits", [r"PAM50", r"per gene"]),
    ("Minimum class size / INSUFFICIENT_N", [r"INSUFFICIENT_N", r"n\s*<\s*20"]),
    ("ACMG mapping from CI lower bound at OddsPath thresholds", [r"CI lower bound", r"PATHOGENIC_VERY_STRONG"]),
    ("Pre-specified interpretation of every outcome including the null", [r"NO_EVIDENCE"]),
    ("RECOVERY TOLERANCE", [r"RECOVERY TOLERANCE", r"SIMULATED_PASS", r"SIMULATED_FAIL"]),
]


def check_required_sections(text):
    missing = []
    for label, patterns in REQUIRED_SECTIONS:
        for pat in patterns:
            if not re.search(pat, text):
                missing.append(f"{label}: missing pattern {pat!r}")
    if missing:
        results.append(("every DO-listed required section is present", False, "; ".join(missing)))
    else:
        results.append(("every DO-listed required section is present", True,
                         f"all {len(REQUIRED_SECTIONS)} required sections found"))


def check_estimand(text):
    norm = re.sub(r"\s+", " ", text)  # collapse markdown line-wraps so phrase regexes aren't line-break-sensitive
    has_formula = bool(re.search(r"P\(E\s*\|\s*Pathogenic\)\s*/\s*P\(E\s*\|\s*Benign\)", norm))
    has_or_contrast = bool(re.search(r"odds ratio", norm, re.IGNORECASE))
    has_lr_to_lr_rule = bool(re.search(r"[Nn]o odds ratio is computed", norm))
    if has_formula and has_or_contrast and has_lr_to_lr_rule:
        results.append(("estimand declared as LR = P(E|Pathogenic)/P(E|Benign), contrasted with OR", True,
                         "formula, OR contrast, and LR-only-comparisons rule all present"))
    else:
        results.append(("estimand declared as LR = P(E|Pathogenic)/P(E|Benign), contrasted with OR", False,
                         f"formula={has_formula}, OR contrast={has_or_contrast}, LR-only rule={has_lr_to_lr_rule}"))


def check_oddspath_thresholds(text):
    required_numbers = ["2.08", "4.33", "18.7", "350", "0.48", "0.053"]
    missing = [n for n in required_numbers if n not in text]
    if missing:
        results.append(("exact BENCHMARKS.tsv OddsPath thresholds present, unaltered", False,
                         f"missing numbers: {missing}"))
    else:
        results.append(("exact BENCHMARKS.tsv OddsPath thresholds present, unaltered", True,
                         f"all of {required_numbers} present"))


def check_named_numeric_thresholds(text):
    checks = {
        "purity floor 0.20": "0.20" in text,
        "sensitivity value 0.30": "0.30" in text,
        "sensitivity value 0.10": "0.10" in text,
        "bootstrap replicate count B=2000": bool(re.search(r"B\s*=\s*2000", text)),
        "CV fold count k=5": bool(re.search(r"k\s*=\s*5\b", text)),
        "minimum stratum n=20": bool(re.search(r"n\s*<\s*20", text)),
        "recovery relative-bias bound 0.25 (25%)": ("0.25" in text and "25%" in text),
        "gnomAD popmax ceiling 0.01 (1%)": ("0.01" in text and "1%" in text),
        "sequencing depth floors 30x/15x": ("30x" in text and "15x" in text),
        "min tumor site depth D>=20 for VAF model": bool(re.search(r"D\s*≥\s*20|D\s*>=\s*20|`D\s*≥\s*20`", text)),
    }
    missing = [k for k, v in checks.items() if not v]
    if missing:
        results.append(("every DO-named numeric threshold has an explicit value", False, f"missing: {missing}"))
    else:
        results.append(("every DO-named numeric threshold has an explicit value", True,
                         f"{len(checks)} named thresholds all present with explicit values"))


def check_simulated_regime(text):
    # Find the Stage 2 section specifically.
    m = re.search(r"## 11\. Stage 2.*", text, re.DOTALL)
    if not m:
        results.append(("Stage 2 uses only Standing-Rule-1 SIMULATED vocabulary, never ACMG codes", False,
                         "could not locate a '## 11. Stage 2' section"))
        return
    stage2_text = re.sub(r"\s+", " ", m.group(0))
    has_simulated_vocab = all(tok in stage2_text for tok in ["SIMULATED_PASS", "SIMULATED_FAIL", "BLOCKED", "SIMULATED DATA"])
    forbids_acmg_in_stage2 = bool(re.search(r"no ACMG evidence strength.*is assigned to any Stage 2", stage2_text) or
                                   re.search(r"reserved for Stage 1 only", stage2_text))
    if has_simulated_vocab and forbids_acmg_in_stage2:
        results.append(("Stage 2 uses only Standing-Rule-1 SIMULATED vocabulary, never ACMG codes", True,
                         "SIMULATED_PASS/SIMULATED_FAIL/BLOCKED present; ACMG vocabulary explicitly reserved for Stage 1"))
    else:
        results.append(("Stage 2 uses only Standing-Rule-1 SIMULATED vocabulary, never ACMG codes", False,
                         f"simulated_vocab={has_simulated_vocab}, acmg_forbidden_note={forbids_acmg_in_stage2}"))


def check_gate1_disclosure(text):
    if not GATE1.exists():
        results.append(("SigMA GATE1 FAIL status is disclosed, matching GATE1.json", False,
                         "GATE1.json not found — cannot cross-check"))
        return
    gate1 = json.loads(GATE1.read_text())
    sigma_entries = [t for t in gate1.get("tools", []) if t.get("name") == "SigMA"]
    if not sigma_entries:
        results.append(("SigMA GATE1 FAIL status is disclosed, matching GATE1.json", False,
                         "no SigMA entry found in GATE1.json"))
        return
    sigma_status = sigma_entries[0].get("status")
    protocol_says_blocked = "BLOCKED" in text and "SigMA" in text and "GATE1.json" in text
    if sigma_status == "FAIL" and protocol_says_blocked:
        results.append(("SigMA GATE1 FAIL status is disclosed, matching GATE1.json", True,
                         "GATE1.json SigMA=FAIL and PROTOCOL.md marks the dependent feature BLOCKED with a citation to GATE1.json"))
    elif sigma_status != "FAIL":
        results.append(("SigMA GATE1 FAIL status is disclosed, matching GATE1.json", True,
                         f"GATE1.json SigMA status is now {sigma_status!r} (not FAIL) — re-review whether PROTOCOL.md's BLOCKED note is stale"))
    else:
        results.append(("SigMA GATE1 FAIL status is disclosed, matching GATE1.json", False,
                         "GATE1.json SigMA=FAIL but PROTOCOL.md does not clearly mark it BLOCKED with a GATE1.json citation"))


def main():
    text = load_text()
    check_no_placeholders(text)
    check_required_sections(text)
    check_estimand(text)
    check_oddspath_thresholds(text)
    check_named_numeric_thresholds(text)
    check_simulated_regime(text)
    check_gate1_disclosure(text)

    overall = True
    for name, passed, detail in results:
        verdict = "PASS" if passed else "FAIL"
        overall = overall and passed
        print(f"[{verdict}] {name} — {detail}")

    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
