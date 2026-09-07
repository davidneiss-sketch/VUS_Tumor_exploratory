#!/usr/bin/env bash
# Trivial invocation of bcftools on a toy VCF, exercising the normalization
# toolchain: bgzip + tabix index, then `bcftools norm` (left-align indels,
# split multiallelics), then `bcftools view`.
set -euo pipefail
cd "$(dirname "$0")"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

bcftools --version | head -1
samtools faidx toy_ref.fa
cp toy.vcf "$WORK/toy.vcf"
bgzip -f "$WORK/toy.vcf"
tabix -p vcf "$WORK/toy.vcf.gz"

echo "--- input (unnormalized) ---"
bcftools view "$WORK/toy.vcf.gz"

echo "--- bcftools norm -m -any -f toy_ref.fa (split multiallelics, left-align) ---"
bcftools norm -m -any -f toy_ref.fa -Ov "$WORK/toy.vcf.gz"

echo "--- bcftools norm exit code check + write output ---"
bcftools norm -m -any -f toy_ref.fa -Oz -o "$WORK/toy.norm.vcf.gz" "$WORK/toy.vcf.gz"
tabix -p vcf "$WORK/toy.norm.vcf.gz"
bcftools stats "$WORK/toy.norm.vcf.gz" | grep "^SN"
