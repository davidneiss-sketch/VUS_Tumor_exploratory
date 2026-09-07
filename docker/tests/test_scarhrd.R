#!/usr/bin/env Rscript
# Trivial invocation of scarHRD on its own bundled small example .seqz file
# (inst/extdata/test1.small.seqz.gz), the same file used in scarHRD's own
# README usage example.
suppressMessages(library(scarHRD))
cat("scarHRD version:", as.character(packageVersion("scarHRD")), "\n")

input <- system.file("extdata", "test1.small.seqz.gz", package = "scarHRD")
stopifnot(file.exists(input))
setwd(tempdir())

res <- scar_score(input, reference = "grch38", seqz = TRUE, chr.in.names = TRUE)
print(res)
stopifnot(is.data.frame(res) || is.matrix(res))
cat("SCARHRD_TEST_OK\n")
