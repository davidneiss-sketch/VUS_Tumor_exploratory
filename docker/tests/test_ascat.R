#!/usr/bin/env Rscript
# Trivial invocation of ASCAT on its own bundled toy example (single
# simulated chromosome, inst/extdata/{tumour,normal}.{logR,BAF}.txt), the
# same files ASCAT's own README/vignette uses to demonstrate the pipeline.
suppressMessages(library(ASCAT))
cat("ASCAT version:", as.character(packageVersion("ASCAT")), "\n")

extdata <- system.file("extdata", package = "ASCAT")
setwd(tempdir())

ascat.bc <- ascat.loadData(
  Tumor_LogR_file    = file.path(extdata, "tumour.logR.txt"),
  Tumor_BAF_file     = file.path(extdata, "tumour.BAF.txt"),
  Germline_LogR_file = file.path(extdata, "normal.logR.txt"),
  Germline_BAF_file  = file.path(extdata, "normal.BAF.txt"),
  chrs = c("1"),
  sexchromosomes = character(0)
)
ascat.bc <- ascat.aspcf(ascat.bc)
ascat.output <- ascat.runAscat(ascat.bc, write_segments = FALSE)

cat("n samples fit:", length(ascat.output$segments_raw), "\n")
str(ascat.output$purity)
str(ascat.output$ploidy)
stopifnot(length(ascat.output$segments_raw) > 0)
cat("ASCAT_TEST_OK\n")
