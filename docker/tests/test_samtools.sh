#!/usr/bin/env bash
# Trivial invocation of samtools on a toy SAM -> sorted, indexed BAM -> view.
set -euo pipefail
cd "$(dirname "$0")"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

samtools --version | head -1
samtools view -b -T toy_ref.fa toy.sam > "$WORK/toy.bam"
samtools sort -o "$WORK/toy.sorted.bam" "$WORK/toy.bam"
samtools index "$WORK/toy.sorted.bam"
echo "--- samtools view of sorted/indexed toy BAM ---"
samtools view "$WORK/toy.sorted.bam"
echo "--- samtools flagstat ---"
samtools flagstat "$WORK/toy.sorted.bam"
