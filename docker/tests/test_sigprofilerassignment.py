#!/usr/bin/env python3
"""Trivial invocation of SigProfilerAssignment: cosmic_fit() on a synthetic
toy SBS96 mutation-count matrix (built here, not downloaded -- cosmic_fit
takes a sample x 96-trinucleotide-context matrix directly and does not need
a reference genome download for this input_type='matrix' path)."""
import itertools
import os
import random
import sys
import tempfile

import SigProfilerAssignment
from SigProfilerAssignment import Analyzer as Analyze

print("SigProfilerAssignment version:", SigProfilerAssignment.__version__)

bases = ["A", "C", "G", "T"]
subs = ["C>A", "C>G", "C>T", "T>A", "T>C", "T>G"]
contexts = []
for sub in subs:
    ref = sub[0]
    for five, three in itertools.product(bases, bases):
        contexts.append(f"{five}[{sub}]{three}")
assert len(contexts) == 96

random.seed(1234)
workdir = tempfile.mkdtemp(prefix="spa_test_")
matrix_path = os.path.join(workdir, "toy.SBS96.txt")
with open(matrix_path, "w") as fh:
    fh.write("MutationType\tToySample1\tToySample2\n")
    for ctx in contexts:
        fh.write(f"{ctx}\t{random.randint(0, 40)}\t{random.randint(0, 40)}\n")

out_dir = os.path.join(workdir, "out")
Analyze.cosmic_fit(
    samples=matrix_path,
    output=out_dir,
    input_type="matrix",
    context_type="96",
    genome_build="GRCh37",
    make_plots=False,
    export_probabilities=False,
    verbose=False,
)

found = []
for root, _dirs, files in os.walk(out_dir):
    for f in files:
        found.append(os.path.join(root, f))
print(f"cosmic_fit produced {len(found)} output file(s) under {out_dir}")
for f in sorted(found)[:20]:
    print(" -", f)
assert len(found) > 0, "cosmic_fit produced no output files"
print("SIGPROFILERASSIGNMENT_TEST_OK")
