#!/usr/bin/env python3
"""Runs the entire gate test suite (unittest discovery) and prints full
verbose output -- every test's PASS/FAIL and, for failing-input tests,
the captured gate output that proves the tripwire/check actually fired.

Discovery pattern is "test_*.py" (widened from "test_gate*.py" this
session, so non-gate-named test modules -- e.g. test_preflight_collision_check.py,
test_artifact_checksum_check.py -- are not silently excluded from this
suite; test_helpers.py itself matches the pattern too but contains no
TestCase classes, so unittest discovers zero tests in it, harmlessly).

Run: python3 tests/run_all_tests.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(str(Path(__file__).resolve().parent), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
