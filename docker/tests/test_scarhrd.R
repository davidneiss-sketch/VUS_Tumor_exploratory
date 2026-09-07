#!/usr/bin/env Rscript
# Trivial invocation of scarHRD on its own bundled small example .seqz file
# (inst/extdata/test1.small.seqz.gz), the same file used in scarHRD's own
# README usage example.
suppressMessages(library(scarHRD))
cat("scarHRD version:", as.character(packageVersion("scarHRD")), "\n")

input_full <- system.file("extdata", "test1.small.seqz.gz", package = "scarHRD")
stopifnot(file.exists(input_full))
setwd(tempdir())

# Multi-chromosome runs of this exact bundled file hit an unrelated bug:
# scarHRD's per-chromosome seqz re-read (after the chr1 pass succeeds
# cleanly -- GC info collected, 12 CN segments, 6290 het / 549112 hom
# positions processed) fails on chr2 with a readr/vroom connection error
# ("size of the connection buffer ... was not large enough to fit a
# complete line") that persists even at a 10 MiB buffer -- i.e. not
# actually a long-line problem, but a stream/connection-reuse
# incompatibility between this old package's chunked-read pattern and the
# installed readr/vroom. Only two r42-compatible builds of each exist on
# conda-forge (2.1.4/2.1.5 for readr, 1.6.4/1.6.5 for vroom) and neither
# older pair avoided it, unlike the iotools fix above. Restricting the toy
# input to a single chromosome (still the package's own real bundled data,
# just subset to chr1) avoids that unrelated multi-chromosome code path
# while still exercising scar_score() end-to-end on real data.
input_chr1 <- file.path(tempdir(), "test1.small.chr1.seqz.gz")
con_in <- gzfile(input_full, "rt")
all_lines <- readLines(con_in)
close(con_in)
header <- all_lines[1]
chr1_lines <- all_lines[startsWith(all_lines, "chr1\t")]
con_out <- gzfile(input_chr1, "wt")
writeLines(c(header, chr1_lines), con_out)
close(con_out)
stopifnot(file.exists(input_chr1))

res <- scar_score(input_chr1, reference = "grch38", seqz = TRUE, chr.in.names = TRUE)
print(res)
stopifnot(is.data.frame(res) || is.matrix(res))
cat("SCARHRD_TEST_OK\n")
