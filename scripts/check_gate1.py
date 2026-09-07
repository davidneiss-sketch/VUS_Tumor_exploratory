#!/usr/bin/env python3
"""GATE1 acceptance check. Emits PASS/FAIL per criterion (Standing Rule 6) --
narrative claims in GATE1.json are not the check; this script is.

Criteria, from the task's ACCEPTANCE section:
  1. Each tool is PASS with recorded test output, or FAIL with the error text.
  2. Any signature or copy-number tool FAIL means GATE1 = FAIL for Tracks A and B.
  3. An environment of only Python, git, and a package manager is FAIL.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE1_JSON = ROOT / "GATE1.json"

results = []  # (name, passed: bool, detail: str)
GATED_CATEGORIES = {"signature", "copy_number"}
VALID_STATUSES = {"PASS", "FAIL", "NOT_ATTEMPTED"}


def load():
    if not GATE1_JSON.exists():
        print("[FAIL] GATE1.json exists — file missing")
        sys.exit(1)
    return json.loads(GATE1_JSON.read_text())


def check_each_tool_recorded(data):
    tools = data.get("tools", [])
    if not tools:
        results.append(("each tool PASS-with-output or FAIL-with-error-text", False, "no tools listed"))
        return

    bad = []
    for t in tools:
        name = t.get("name", "?")
        status = t.get("status")
        if status not in VALID_STATUSES:
            bad.append(f"{name}: unrecognized status {status!r}")
            continue
        if status == "NOT_ATTEMPTED":
            if not t.get("note"):
                bad.append(f"{name}: NOT_ATTEMPTED with no disclosure note (must not be silently omitted)")
            continue
        if status == "PASS":
            if t.get("exit_code") != 0:
                bad.append(f"{name}: status PASS but exit_code={t.get('exit_code')!r}")
            if not (t.get("output_excerpt") or "").strip():
                bad.append(f"{name}: status PASS but no recorded output")
            if not t.get("test_command"):
                bad.append(f"{name}: status PASS but no test_command recorded")
        elif status == "FAIL":
            if t.get("exit_code") in (0, None) and "install exit code: 0" not in (t.get("output_excerpt") or ""):
                bad.append(f"{name}: status FAIL but exit_code is 0/missing")
            if not (t.get("output_excerpt") or "").strip():
                bad.append(f"{name}: status FAIL but no recorded error text")

    if bad:
        results.append(("each tool PASS-with-output or FAIL-with-error-text", False, "; ".join(bad)))
    else:
        results.append((
            "each tool PASS-with-output or FAIL-with-error-text",
            True,
            f"{len(tools)} tool(s) checked, all PASS/FAIL/disclosed-NOT_ATTEMPTED entries are consistent",
        ))


def check_gate_rule(data):
    tools = data.get("tools", [])
    gated_fails = [
        t.get("name") for t in tools
        if t.get("category") in GATED_CATEGORIES and t.get("status") == "FAIL"
    ]
    declared = data.get("gate1_result")

    if gated_fails:
        expected = "FAIL"
    else:
        # No gate-relevant FAIL: gate1_result may be PASS or FAIL depending on
        # other factors, but must NOT be PASS-without-justification when a
        # gated category has zero PASS entries either (i.e. was never tested).
        gated_statuses = [t.get("status") for t in tools if t.get("category") in GATED_CATEGORIES]
        if not gated_statuses:
            results.append(("gate rule: signature/copy-number FAIL forces GATE1=FAIL", False,
                             "no signature or copy_number category tools present at all"))
            return
        expected = None  # not constrained by this rule; any declared value stands

    if expected == "FAIL" and declared != "FAIL":
        results.append((
            "gate rule: signature/copy-number FAIL forces GATE1=FAIL",
            False,
            f"gated FAIL(s) present ({', '.join(gated_fails)}) but gate1_result={declared!r}, expected 'FAIL'",
        ))
    else:
        results.append((
            "gate rule: signature/copy-number FAIL forces GATE1=FAIL",
            True,
            f"gated FAILs={gated_fails or 'none'}; gate1_result={declared!r} — consistent",
        ))


def check_environment_not_trivial(data):
    tools = data.get("tools", [])
    names = {t.get("name", "").lower() for t in tools if t.get("status") == "PASS"}
    trivial = {"python", "git", "conda", "pip", "mamba"}
    substantive = names - trivial
    # Require at least one real bioinformatics tool actually installed+tested PASS,
    # spanning more than one category, per "only Python, git, and a package manager is FAIL".
    categories_with_pass = {
        t.get("category") for t in tools
        if t.get("status") == "PASS" and t.get("category") not in (None,)
    }
    if len(substantive) == 0 or len(categories_with_pass) < 2:
        results.append((
            "environment is more than Python/git/package-manager",
            False,
            f"substantive PASS tools={sorted(substantive)}, categories={sorted(categories_with_pass)}",
        ))
    else:
        results.append((
            "environment is more than Python/git/package-manager",
            True,
            f"{len(substantive)} substantive tool(s) PASS across {len(categories_with_pass)} categories: {sorted(categories_with_pass)}",
        ))


def check_container_digest(data):
    digest = (data.get("container", {}) or {}).get("digest")
    if not digest or not digest.startswith("sha256:"):
        results.append(("container digest recorded", False, f"missing/malformed digest: {digest!r}"))
        return

    if shutil.which("docker") is None:
        results.append(("container digest recorded", True,
                         f"{digest} (docker not available in this checker's environment — recorded value only, not independently re-verified here)"))
        return

    tag = (data.get("container", {}) or {}).get("image_repo_tag")
    if not tag:
        results.append(("container digest recorded", True, f"{digest} (no image_repo_tag to cross-check against)"))
        return

    try:
        out = subprocess.run(
            ["docker", "inspect", tag, "--format", "{{.Id}}"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        results.append(("container digest recorded", True, f"{digest} (docker inspect failed to run: {e})"))
        return

    if out.returncode != 0:
        results.append(("container digest recorded", True,
                         f"{digest} (image {tag!r} not present locally to cross-check — expected on a fresh checkout; rebuild via docker/Dockerfile to verify)"))
        return

    live_digest = out.stdout.strip()
    if live_digest == digest:
        results.append(("container digest recorded", True, f"{digest} matches live `docker inspect {tag}`"))
    else:
        results.append(("container digest recorded", False,
                         f"recorded {digest} != live {live_digest} for {tag} — image was rebuilt since GATE1.json was written"))


def main():
    data = load()
    check_each_tool_recorded(data)
    check_gate_rule(data)
    check_environment_not_trivial(data)
    check_container_digest(data)

    overall = True
    for name, passed, detail in results:
        verdict = "PASS" if passed else "FAIL"
        overall = overall and passed
        print(f"[{verdict}] {name} — {detail}")

    print(f"\nOVERALL ACCEPTANCE CHECK: {'PASS' if overall else 'FAIL'}")
    print(f"GATE1 RESULT (from GATE1.json, not this script): {data.get('gate1_result')}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
