#!/usr/bin/env bash
# Runs every tool's bundled-test / toy-invocation script, records
# command + exit code + full output for each into /opt/tests/results/,
# and never aborts early -- a FAIL for one tool must not hide the others.
set -u
export PATH=/opt/conda/envs/bioenv/bin:$PATH
cd /opt/tests
mkdir -p results

run_one() {
  local name="$1"; shift
  local cmd="$*"
  echo "=== $name ==="
  echo "\$ $cmd"
  ( eval "$cmd" ) > "results/${name}.log" 2>&1
  local ec=$?
  echo "$ec" > "results/${name}.exitcode"
  echo "$cmd" > "results/${name}.cmd"
  echo "exit code: $ec"
  tail -n 5 "results/${name}.log"
  echo
}

run_one samtools "bash /opt/tests/test_samtools.sh"
run_one bcftools "bash /opt/tests/test_bcftools.sh"
run_one facets "Rscript /opt/tests/test_facets.R"
run_one ascat "Rscript /opt/tests/test_ascat.R"
run_one sequenza "Rscript /opt/tests/test_sequenza.R"
run_one scarhrd "Rscript /opt/tests/test_scarhrd.R"
run_one sigprofilerassignment "python3 /opt/tests/test_sigprofilerassignment.py"

# SigMA never installed (see /opt/sigma_install.log from the build); record
# that as this tool's result rather than attempting to load a package that
# is not there.
sigma_install_ec=$(cat /opt/sigma_install.exitcode 2>/dev/null || echo "unknown")
{
  echo "\$ R CMD INSTALL of SigMA (build-time step, see docker/Dockerfile)"
  echo "install exit code: $sigma_install_ec"
  echo
  cat /opt/sigma_install.log 2>/dev/null
} > results/sigma.log
echo "$sigma_install_ec" > results/sigma.exitcode
echo "R CMD INSTALL --no-docs --no-build-vignettes --no-byte-compile /opt/SigMA-src (at build time)" > results/sigma.cmd

echo "=== summary ==="
for f in results/*.exitcode; do
  printf "%-25s exit=%s\n" "$(basename "$f" .exitcode)" "$(cat "$f")"
done
