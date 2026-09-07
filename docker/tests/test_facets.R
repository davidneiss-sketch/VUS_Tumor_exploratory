#!/usr/bin/env Rscript
# Trivial invocation of FACETS on its own bundled example dataset
# (inst/extdata/stomach.csv.gz, the standard FACETS demo snp-pileup counts).
suppressMessages(library(facets))
cat("facets version:", as.character(packageVersion("facets")), "\n")
set.seed(1234)
datafile <- system.file("extdata", "stomach.csv.gz", package = "facets")
stopifnot(file.exists(datafile))
rcmat <- readSnpMatrix(datafile)
xx <- preProcSample(rcmat)
oo <- procSample(xx, cval = 150)
fit <- emcncf(oo)
cat("purity:", fit$purity, "\n")
cat("ploidy:", fit$ploidy, "\n")
cat("n segments:", nrow(fit$cncf), "\n")
stopifnot(nrow(fit$cncf) > 0)
cat("FACETS_TEST_OK\n")
