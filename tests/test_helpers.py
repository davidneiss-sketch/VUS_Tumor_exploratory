"""Shared subprocess-running helper for the gate test suite."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GATES_DIR = REPO_ROOT / "gates"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def run_gate(script_name: str, *args: str) -> subprocess.CompletedProcess:
    """Runs a gate script as a real subprocess (not an in-process import)
    so the test suite exercises exactly what a pipeline invocation would
    run, cwd fixed at the repo root so fixture-relative paths resolve."""
    cmd = [sys.executable, str(GATES_DIR / script_name), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=60)
