# Canonical Linux/amd64 reproducibility image.
# Base image inspected with:
#   docker buildx imagetools inspect python:3.12.4-slim
FROM python:3.12.4-slim@sha256:a074fac67aa01841fee592d00bae14d25dcaf98ef6e12a683ecceb7e0147e2d1

# Deterministic numerical defaults: pin BLAS/OpenMP thread counts so the order
# of floating-point operations is stable, which the Level 1 density-matrix
# eigendecompositions depend on for tight tolerances.
ENV PYTHONHASHSEED=0 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SOURCE_DATE_EPOCH=1719878400 \
    MPLCONFIGDIR=/tmp/matplotlib \
    REPRO_DOCKER_BASE_IMAGE=python:3.12.4-slim \
    REPRO_DOCKER_BASE_DIGEST=sha256:a074fac67aa01841fee592d00bae14d25dcaf98ef6e12a683ecceb7e0147e2d1 \
    REPRO_DOCKER_PLATFORM=linux/amd64

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash make \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md requirements.lock ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock \
    && python -m pip install --no-cache-dir --no-deps --no-build-isolation -e .

COPY . .

CMD ["make", "reproduce-level1"]
