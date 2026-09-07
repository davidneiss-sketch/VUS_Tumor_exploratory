# local_channel: bioconductor-genomeinfodbdata (rebuilt)

## Why this exists

`bioconductor-genomeinfodbdata` is a required transitive dependency of
`bioconductor-genomeinfodb`, which is in turn required by
`bioconductor-genomicranges`, `bioconductor-variantannotation`,
`bioconductor-bsgenome` / `bioconductor-bsgenome.hsapiens.ucsc.hg19`,
`bioconductor-purecn`, and SigMA's own R dependencies. Its bioconda recipe
does not vendor the actual data in the conda package; a `post-link.sh`
downloads it at install time from, in order:

- `https://bioconductor.org/packages/3.16/data/annotation/src/contrib/GenomeInfoDbData_1.2.9.tar.gz`
- `https://bioarchive.galaxyproject.org/GenomeInfoDbData_1.2.9.tar.gz`
- `https://depot.galaxyproject.org/software/bioconductor-genomeinfodbdata/bioconductor-genomeinfodbdata_1.2.9_src_all.tar.gz`

All three hosts were confirmed blocked by this build environment's network
egress policy (proxy CONNECT denied with 403 for each), which made the
`conda create` for the whole analysis environment fail. See
`ENVIRONMENT.lock` for the retrieval-log entries.

## What's here

`noarch/bioconductor-genomeinfodbdata-1.2.15-r42h_local_0.tar.bz2`: the same
R package, rebuilt from the canonical Bioconductor GitHub mirror instead of
the blocked mirrors above. No source code was modified.

- Source: `https://github.com/Bioconductor/GenomeInfoDbData`
- Commit: `b5339e03cc0c9c188e773a7ec2b80a146601595a` (HEAD at fetch time)
- Upstream package version: `1.2.15` (the bioconda recipe wants `1.2.9`;
  every observed bioconda `GenomeInfoDb`-family dependency constraint on
  this package is `>=1.2.0,<1.3.0`, which `1.2.15` satisfies)
- License: Artistic-2.0 (as declared in the package's own `DESCRIPTION`;
  permits redistribution, unlike SigMA's source -- see the top-level
  `.gitignore` for why SigMA's source is *not* vendored the same way)
- Built with: R 4.2 (conda `r-base=4.2`), `R CMD INSTALL --build`, no
  compiled code (the package is pure data/R, `noarch: generic`)

## How it was rebuilt (reproducible)

```bash
# 1. Fetch the canonical source
git clone https://github.com/Bioconductor/GenomeInfoDbData /tmp/GenomeInfoDbData

# 2. Install R 4.2 (matches this project's pinned r-base) and build the package
conda create -n tiny -y -c conda-forge -c bioconda r-base=4.2
/opt/conda/envs/tiny/bin/R CMD INSTALL --build /tmp/GenomeInfoDbData

# 3. Stage it as a conda package: copy the installed
#    lib/R/library/GenomeInfoDbData tree plus an info/index.json declaring
#    name=bioconductor-genomeinfodbdata, version=1.2.15,
#    build=r42h_local_0, depends=["r-base >=4.2,<4.3.0a0"], noarch=generic;
#    an info/paths.json listing each file's sha256/size; tar czf/bzip2 it
#    into noarch/bioconductor-genomeinfodbdata-1.2.15-r42h_local_0.tar.bz2

# 4. Index the channel
conda index docker/local_channel
```

Verified after installing into a fresh env alongside
`bioconductor-genomeinfodb`:

```r
library(GenomeInfoDbData); library(GenomeInfoDb)
genomeStyles("Homo_sapiens")   # returns the expected 25-row lookup table
```
