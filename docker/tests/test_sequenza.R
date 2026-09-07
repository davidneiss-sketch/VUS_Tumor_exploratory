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
cat("cellularity/ploidy grid dims:", paste(dim(cp), collapse = "x"), "\n")
stopifnot(all(dim(cp) > 0))
cat("SEQUENZA_TEST_OK\n")
