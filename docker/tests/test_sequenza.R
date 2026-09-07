#!/usr/bin/env Rscript
# Trivial invocation of Sequenza on its own bundled example .seqz file
# (inst/extdata/example.seqz.txt.gz), restricted to one chromosome to keep
# this a "toy" run rather than a full-genome fit.
suppressMessages(library(sequenza))
cat("sequenza version:", as.character(packageVersion("sequenza")), "\n")

seqz_file <- system.file("extdata", "example.seqz.txt.gz", package = "sequenza")
stopifnot(file.exists(seqz_file))

test <- sequenza.extract(seqz_file, chromosome.list = "1", verbose = FALSE)
cp <- sequenza.fit(test)
stopifnot(is.list(cp), all(c("ploidy", "cellularity", "lpp") %in% names(cp)))
cat("ploidy grid points:", length(cp$ploidy), "\n")
cat("cellularity grid points:", length(cp$cellularity), "\n")
best <- which(cp$lpp == max(cp$lpp), arr.ind = TRUE)[1, ]
cat("best-fit ploidy:", cp$ploidy[best["row"]], "\n")
cat("best-fit cellularity:", cp$cellularity[best["col"]], "\n")
stopifnot(length(cp$ploidy) > 0, length(cp$cellularity) > 0, is.finite(cp$lpp[best["row"], best["col"]]))
cat("SEQUENZA_TEST_OK\n")
