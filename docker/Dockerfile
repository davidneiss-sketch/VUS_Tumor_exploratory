# Analysis environment for VUS_Tumor_exploratory GATE1.
#
# Build (network access to conda.anaconda.org, archive.ubuntu.com,
# security.ubuntu.com, repo.anaconda.com and raw.githubusercontent.com is
# required at build time):
#
#   docker build --network host \
#     --build-arg HTTPS_PROXY=<proxy-if-any> --build-arg HTTP_PROXY=<proxy-if-any> \
#     -f docker/Dockerfile -t vus-tumor-gate1:local docker
#
# The HTTP(S)_PROXY build args are Docker's well-known proxy build-args: they
# are used only while building and are NOT persisted into the final image's
# environment or history.

FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG HTTPS_PROXY
ARG HTTP_PROXY
ARG NO_PROXY
ENV DEBIAN_FRONTEND=noninteractive

# --- Trust the build-time TLS-inspecting proxy CA (harmless no-op outside
#     that network: it is added alongside, not instead of, the system roots) ---
COPY agent-proxy-ca.crt /usr/local/share/ca-certificates/agent-proxy-ca.crt
RUN update-ca-certificates
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# --- System packages: samtools/bcftools (apt, Ubuntu 24.04 noble),
#     Ubuntu's HTTP mirrors are rewritten to HTTPS because this build's
#     egress proxy only tunnels HTTPS (CONNECT), not plain HTTP ---
RUN (test -f /etc/apt/sources.list.d/ubuntu.sources && sed -i 's#http://#https://#g' /etc/apt/sources.list.d/ubuntu.sources) || true
RUN (test -f /etc/apt/sources.list && sed -i 's#http://#https://#g' /etc/apt/sources.list) || true
RUN apt-get update \
 && apt-get install -y --no-install-recommends samtools bcftools tabix ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# --- Miniconda (installer fetched from repo.anaconda.com; sha256 recorded
#     in ENVIRONMENT.lock) ---
COPY Miniconda3.sh /tmp/Miniconda3.sh
RUN bash /tmp/Miniconda3.sh -b -p /opt/conda && rm /tmp/Miniconda3.sh
ENV PATH=/opt/conda/bin:$PATH

# This Miniconda build bundles Anaconda Inc.'s telemetry/ToS/auth plugins,
# which unconditionally phone home to repo.anaconda.cloud on ordinary conda
# operations even when only the (unauthenticated, ToS-free) conda-forge and
# bioconda channels are configured. That host is not reachable in this
# build's network policy (confirmed: proxy CONNECT to repo.anaconda.cloud:443
# denied with 403) and is not needed for anything this image does, so the
# plugins are removed outright (plain filesystem/pip operations, no network
# call) rather than routed around.
RUN rm -f /opt/conda/condarc.d/anaconda-auth.yml \
 && /opt/conda/bin/pip uninstall -y anaconda-auth anaconda-cli-base anaconda-anon-usage \
      anaconda-channel-guide conda-anaconda-tos conda-anaconda-telemetry

RUN conda config --system --set ssl_verify /etc/ssl/certs/ca-certificates.crt \
 && conda config --system --set channel_priority strict \
 && (conda config --system --remove channels defaults || true) \
 && conda config --system --prepend channels bioconda \
 && conda config --system --prepend channels conda-forge

# --- The analysis environment. r-base is pinned to 4.2 because r-scarhrd's
#     only bioconda builds require R >=4.2,<4.3 (or the much older R 3.5
#     line); every other requested package is compatible with R 4.2. ---
RUN conda create -n bioenv -y \
    -c conda-forge -c bioconda \
    r-base=4.2 \
    bioconductor-purecn \
    r-facets \
    ascat \
    r-sequenza \
    sequenza-utils \
    r-scarhrd \
    sigprofilerassignment \
    bioconductor-bsgenome \
    bioconductor-bsgenome.hsapiens.ucsc.hg19 \
    r-devtools \
    r-dt \
    bioconductor-genomicranges \
    r-ggplot2 \
    r-gbm \
    r-gridextra \
    bioconductor-iranges \
    r-nnls \
    r-reshape2 \
    r-rmisc \
    bioconductor-variantannotation \
    r-pheatmap \
    bcftools samtools htslib tabix vcftools \
 && conda clean -afy

# --- SigMA (github.com/parklab/SigMA is not distributed via CRAN/Bioconductor
#     or any conda channel; source cloned separately at a pinned commit and
#     installed from source with R CMD INSTALL against the conda-provided
#     dependencies above; no network access needed at this step) ---
COPY sigma-src /opt/SigMA-src
RUN /opt/conda/envs/bioenv/bin/R CMD INSTALL --no-docs --no-build-vignettes --no-byte-compile /opt/SigMA-src \
    2>&1 | tee /opt/sigma_install.log

# --- Toy test inputs and per-tool test scripts ---
COPY tests /opt/tests
ENV PATH=/opt/conda/envs/bioenv/bin:$PATH

WORKDIR /opt
CMD ["/bin/bash"]
