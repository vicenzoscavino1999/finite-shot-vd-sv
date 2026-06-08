# Single-stage reproducibility image for the current pre-release tree.
# The final archival release should pin this base image by digest and use a
# full hash-locked environment after the manuscript/DOI package is finalized.
FROM python:3.12.4-slim

# Deterministic numerical defaults: pin BLAS/OpenMP thread counts so the order
# of floating-point operations is stable, which the Level 1 density-matrix
# eigendecompositions depend on for tight tolerances.
ENV PYTHONHASHSEED=0 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash make \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md requirements-ci-constraints.txt ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        --constraint requirements-ci-constraints.txt \
        -e ".[dev,level2]"

COPY . .

CMD ["make", "reproduce-level1"]
