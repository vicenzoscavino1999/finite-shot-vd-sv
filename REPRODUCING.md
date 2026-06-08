# Reproducing The Results

The canonical environment is Linux/amd64 Docker. Windows and macOS are
cross-platform tolerance checks, not the source of reference truth.

## One Command

```bash
docker build --platform linux/amd64 -t finite-shot-vd-sv:repro .
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro bash -lc "make reproduce-all"
```

Canonical entrypoints are `reproducibility/run_all_current.py` and
`reproducibility/verify_current.py`; the PAP-frozen `run_all.py`,
`run_all_v2.py`, and `verify.py` are audit artifacts, not the current
reproduction path. `verify.py` does not validate reference checksums.

Expected final line:

```text
REPRODUCE_ALL_PASS: Level 1 exact, tests, PAP freeze, Level 3 archived-count verification, and figures completed
```

Expected Level 1 verifier line:

```text
VERIFY PASS: 18260 numeric comparisons within tolerance across 7 files; reference checksums OK
```

Typical runtime on a laptop-class x86_64 machine is about 25-35 minutes for
`make reproduce-all`, dominated by three full deterministic Level 1 runs and
Level 3 archive verification. `make check-ci` skips figure generation and the
full freeze-integrity test that needs git object history, but still runs the
PAP freeze auditor included in the image.

## What This Proves

- The canonical Linux/amd64 Docker environment is hash-locked by
  `requirements.lock` and pinned to the base image digest in `Dockerfile`.
- Level 1 full outputs reproduce byte/float-stream exactly against
  `reproducibility/reference/`.
- Three full canonical runs are mutually exact via `make determinism-check`.
- Level 3 analyses are recomputed from archived `.json.gz` count files without
  connecting to IBM Runtime.
- Figures are regenerated from numerical outputs, but PDF byte identity is not
  claimed.

## Non-Canonical Platforms

For Windows/macOS checks, install from the same lock when possible and omit
`--exact-numeric`:

```bash
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python reproducibility/run_all_current.py --mode full --output results
python reproducibility/verify_current.py --reference reproducibility/reference --generated results
```

Set these environment variables before running outside Docker:

```bash
PYTHONHASHSEED=0
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
```

Tiny final-ULP drift outside the canonical Linux/Docker environment is expected
and is covered by `reproducibility/config/tolerances.yaml`.
