# Simple single-stage Dockerfile for the submission-ready MVP (Phase A).
# The final archival release (Phase B) pins this image by digest and may use a
# multi-stage build.
FROM python:3.11.9-slim

# Deterministic numerical defaults: pin BLAS/OpenMP thread counts so the order
# of floating-point operations is stable, which the Level 1 density-matrix
# eigendecompositions depend on for tight tolerances.
ENV PYTHONHASHSEED=0 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

COPY . .

CMD ["make", "reproduce-level1"]
