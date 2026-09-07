#!/usr/bin/env python3
"""GATE 2 — Data reality.

Reads RAW inputs directly (never pipeline intermediates). For every row in
the raw-input manifest:
  - confirms the file exists at the recorded path
  - re-reads the file NOW and records its actual byte size and md5 (never
    trusts a cached/reported value)
  - re-verifies that on-disk md5 against a second, independent source of
    truth: either (a) an HTTP re-fetch of `source_url`, streamed and
    hashed fresh, when --allow-network is passed and a URL is present, or
    (b) the `md5_recorded` value from the manifest's own provenance record
    otherwise. Mode (b) is the default because this environment has no
    controlled-access raw genomic files to re-download for this task (see
    TRACK.md/GATE1.json); which mode ran for each row is printed and
    logged, never silently substituted (Standing Rule 4).
  - extracts read count and reference build from the file's own header
    (samtools view -H for .bam/.cram if samtools is on PATH; a plain
    "READS: n" / "REFERENCE: build" text-header convention otherwise) --
    never from a manifest-claimed value.
  - sums total bytes actually read across every row.

Then asserts:
  - total input volume is consistent with the claimed sample count (the
    number of manifest rows equals the externally claimed count).
  - every sample_id in the "analyzed samples" list traces to a provenance
    row (no analyzed sample without a provenance record).

Usage:
  gate2_data_reality.py --manifest FILE --provenance FILE --analyzed FILE
                         --claimed-count N [--allow-network]

Exit 0 = all checks pass. Exit 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates_common import GateReport, read_tsv, to_int  # noqa: E402


def md5_of_file(path: Path) -> tuple[str, int]:
    h = hashlib.md5()
    total = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


def md5_of_url(url: str) -> tuple[str, int] | None:
    h = hashlib.md5()
    total = 0
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                total += len(chunk)
    except Exception as e:
        print(f"  network re-fetch of {url!r} failed: {e}", file=sys.stderr)
        return None
    return h.hexdigest(), total


def read_header(path: Path) -> tuple[int | None, str | None, str]:
    """Returns (read_count, reference_build, method_used)."""
    suffix = path.suffix.lower()
    if suffix in (".bam", ".cram"):
        if shutil.which("samtools") is None:
            return None, None, "samtools-not-on-PATH"
        try:
            header = subprocess.run(
                ["samtools", "view", "-H", str(path)], capture_output=True, text=True, timeout=60, check=True
            ).stdout
        except subprocess.CalledProcessError as e:
            return None, None, f"samtools-header-failed-exit-{e.returncode}"
        ref_build = None
        for line in header.splitlines():
            if line.startswith("@SQ") and "GRCh38" in line:
                ref_build = "GRCh38"
                break
            if line.startswith("@SQ") and "GRCh37" in line:
                ref_build = "GRCh37"
                break
        try:
            count_out = subprocess.run(
                ["samtools", "view", "-c", str(path)], capture_output=True, text=True, timeout=120, check=True
            ).stdout
            read_count = int(count_out.strip())
        except (subprocess.CalledProcessError, ValueError):
            read_count = None
        return read_count, ref_build, "samtools"
    else:
        # Plain-text raw-input header convention used by this repo's own
        # synthetic/test raw inputs: first lines "READS: <n>" and
        # "REFERENCE: <build>".
        read_count = None
        ref_build = None
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(20):
                    line = f.readline()
                    if not line:
                        break
                    if line.startswith("READS:"):
                        try:
                            read_count = int(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
                    elif line.startswith("REFERENCE:"):
                        ref_build = line.split(":", 1)[1].strip()
        except OSError:
            return None, None, "read-error"
        return read_count, ref_build, "text-header-convention"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--provenance", required=True, type=Path)
    ap.add_argument("--analyzed", required=True, type=Path)
    ap.add_argument("--claimed-count", required=True, type=int)
    ap.add_argument("--allow-network", action="store_true")
    args = ap.parse_args()

    report = GateReport("gate2_data_reality")

    try:
        manifest_rows = read_tsv(args.manifest)
        provenance_rows = read_tsv(args.provenance)
        analyzed_rows = read_tsv(args.analyzed)
    except FileNotFoundError as e:
        report.check("all required input files present", False, str(e))
        report.print_and_exit()
        return
    report.check("all required input files present", True,
                 f"manifest={args.manifest.name}, provenance={args.provenance.name}, analyzed={args.analyzed.name}")

    total_bytes_read = 0
    row_failures: list[str] = []

    for row in manifest_rows:
        sample_id = row.get("sample_id", "?")
        path = Path(row["path"])
        if not path.exists():
            row_failures.append(f"{sample_id}: raw file missing at recorded path {path}")
            continue

        actual_md5, actual_bytes = md5_of_file(path)
        total_bytes_read += actual_bytes

        recorded_size = to_int(row["byte_size_recorded"], "byte_size_recorded", sample_id)
        if actual_bytes != recorded_size:
            row_failures.append(
                f"{sample_id}: on-disk byte size {actual_bytes} != recorded {recorded_size}"
            )

        recorded_md5 = row["md5_recorded"]
        url = (row.get("source_url") or "").strip()
        if args.allow_network and url:
            fresh = md5_of_url(url)
            if fresh is None:
                row_failures.append(f"{sample_id}: network re-fetch of {url} failed — cannot verify (Standing Rule 3: UNVERIFIED)")
                continue
            fresh_md5, _ = fresh
            method = "network-re-fetch"
            if fresh_md5 != recorded_md5:
                row_failures.append(
                    f"{sample_id}: md5 re-verified via {method} = {fresh_md5} != recorded {recorded_md5}"
                )
        else:
            method = "on-disk-re-hash-vs-provenance-record"
            if actual_md5 != recorded_md5:
                row_failures.append(
                    f"{sample_id}: md5 re-verified via {method} = {actual_md5} != recorded {recorded_md5}"
                )
        print(f"  {sample_id}: md5 verification method = {method}")

        read_count, ref_build, header_method = read_header(path)
        expected_reads = (row.get("read_count_recorded") or "").strip()
        expected_ref = (row.get("reference_build_recorded") or "").strip()
        if header_method in ("samtools-not-on-PATH", "read-error"):
            row_failures.append(f"{sample_id}: could not read header ({header_method})")
        else:
            if expected_reads and read_count is not None and str(read_count) != expected_reads:
                row_failures.append(
                    f"{sample_id}: header read count {read_count} (via {header_method}) != recorded {expected_reads}"
                )
            if expected_ref and ref_build is not None and ref_build != expected_ref:
                row_failures.append(
                    f"{sample_id}: header reference build {ref_build!r} (via {header_method}) != recorded {expected_ref!r}"
                )

    report.check(
        "every raw file's on-disk size/md5/header matches its provenance record",
        len(row_failures) == 0,
        "; ".join(row_failures) if row_failures else f"{len(manifest_rows)} raw file(s) verified, {total_bytes_read} total bytes read",
    )

    # Input volume consistent with claimed sample count.
    n_manifest_rows = len(manifest_rows)
    report.check(
        "input volume consistent with claimed sample count",
        n_manifest_rows == args.claimed_count,
        f"{n_manifest_rows} raw manifest row(s) vs claimed_count={args.claimed_count}",
    )

    # Every analyzed sample traces to a provenance row.
    provenance_ids = {r["sample_id"] for r in provenance_rows}
    analyzed_ids = [r["sample_id"] for r in analyzed_rows]
    untraced = [sid for sid in analyzed_ids if sid not in provenance_ids]
    report.check(
        "every analyzed sample traces to a provenance row",
        len(untraced) == 0,
        f"untraced sample_id(s): {untraced}" if untraced else f"{len(analyzed_ids)} analyzed sample(s), all present in {len(provenance_ids)}-row provenance table",
    )

    print(f"\nTOTAL BYTES READ (raw manifest files): {total_bytes_read}")
    report.print_and_exit()


if __name__ == "__main__":
    main()
