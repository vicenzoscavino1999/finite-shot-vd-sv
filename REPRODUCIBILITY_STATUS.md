# Current Reproducibility Status

Status: operational status note. Not a PAP freeze, not a primary validation
decision, and not a replacement for the frozen `REPRODUCIBILITY_PLAN.md`.

## Scope

The current public reproduction contract is:

- Level 1 is the canonical numerical reference layer.
- The canonical environment is Linux/amd64 Docker, using the base digest pinned
  in `Dockerfile` and the single hash-locked `requirements.lock`.
- The canonical Level 1 reference package is
  `reproducibility/reference/`, generated in Docker with
  `reproducibility/run_all_current.py --mode full`.
- Canonical Docker checks use `--exact-numeric`.
- Windows/macOS checks are non-canonical portability checks and use registered
  tolerances.
- Level 2 is additive Qiskit/Aer form validation, not part of the official
  numeric reference contract.
- Level 3 is archive-only analysis from committed raw-count files; it never
  requires re-running QPU jobs.

No new PAP freeze is active. The v1/v2 PAP freezes remain historical scientific
freeze artifacts and are not rewritten by the current Linux reference package.

## Freeze Provenance

| Freeze | Role | Manifest | Hash file | Frozen commit | Expected current audit |
| --- | --- | --- | --- | --- | --- |
| v1 | original PAP | `freeze_manifest.json` | `PAP_HASH.txt` | `0814ba7...` | intact with expected CRLF drift |
| v2 | P1 negative-control amendment | `freeze_manifest_v2.json` | `PAP_HASH_v2.txt` | `555d3dc...` | intact, zero drift |

Use:

```bash
python pap/verify_freeze.py
```

Expected verdicts:

- `freeze_manifest.json (v1)`: `INTACT_WITH_EXPECTED_DRIFT`
- `freeze_manifest_v2.json (v2)`: `INTACT_ZERO_DRIFT`

Interpret this only with `git status --short` clean when auditing a checkout.

## Canonical Commands

Build and run the canonical container:

```bash
docker build --platform linux/amd64 -t finite-shot-vd-sv:repro .
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro bash -lc "make check-ci"
```

One-command reviewer path:

```bash
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro bash -lc "make reproduce-all"
```

Expected Level 1 verifier line:

```text
VERIFY PASS: 18260 numeric comparisons within tolerance across 7 files; reference checksums OK
```

Expected final `reproduce-all` line:

```text
REPRODUCE_ALL_PASS: Level 1 exact, tests, PAP freeze, Level 3 archived-count verification, and figures completed
```

## Local Non-Canonical Install

When not using Docker, install from the same lock and set deterministic env vars:

```bash
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

Then run the full path with tolerance unless the platform is the canonical
Linux/amd64 Docker image:

```bash
python reproducibility/run_all_current.py --mode full --output results
python reproducibility/verify_current.py --reference reproducibility/reference --generated results
```

## Level 1 Reference Package

`reproducibility/reference/reference_manifest.json` records:

- canonical platform and Python version,
- NumPy/SciPy versions,
- deterministic environment values,
- `requirements.lock` SHA-256,
- Docker base image digest,
- RNG policy and per-experiment seeds,
- SHA-256 checksums for all canonical CSV outputs.

Reference integrity check:

```bash
python reproducibility/verify_current.py \
  --reference reproducibility/reference \
  --generated reproducibility/reference \
  --exact-numeric
```

## Level 2 Device-Simulation Layer

Level 2 outputs and tests are committed as additive form validation under
Qiskit/Aer. They are intentionally outside the official numeric reference
contract. A separate relaxed-tolerance Level 2 tier can be defined explicitly,
but this snapshot does not claim Level 2 byte- or coefficient-level identity.

Summary: `level2/LEVEL2_SUMMARY.md`.

## Level 3 Hardware Archive Analysis

Level 3 public reproduction is analysis-from-archived-counts only.

Verify without rewriting committed summaries:

```bash
python scripts/verify_level3_archives.py
```

This verifies:

- `level3/archive/level3_archive_manifest.json`,
- `level3/archive/checksums.sha256`,
- all registered raw-count `.json.gz` files,
- all registered consolidated analysis `.json` files,
- recomputed Stage 3 analyses against committed summaries.

It does not reconnect to IBM Runtime or re-execute hardware jobs.

## Artifact Map

| Area | Current artifacts | Status |
| --- | --- | --- |
| Freeze audit | `pap/verify_freeze.py`, `pap/FREEZE_STATUS.md` | active audit |
| Level 1 reference | `reproducibility/reference/*` | canonical Linux/Docker reference |
| Dependency lock | `requirements.lock` | single hash-locked environment |
| Docker | `Dockerfile` | base digest pinned |
| CI | `.github/workflows/reproduce.yml` | canonical exact Docker job plus cross-platform tolerance matrix |
| Level 2 | `level2/*`, `level2/LEVEL2_SUMMARY.md` | additive form validation |
| Level 3 | `level3/archive/*`, `scripts/verify_level3_archives.py` | archive-only hardware analysis |
| Figures | `scripts/generate_all_figures.py`, `figures/` | regenerated from numerical data; no PDF byte identity claim |

## Release Boundary

This snapshot claims the code/data reproduction boundary above. It does not
claim:

- a container registry digest,
- byte-identical manuscript/figure PDFs,
- Level 2 coefficient-level identity,
- new QPU submissions for Level 3 reproduction.

The versioned archive DOI for the release used in the manuscript is
`10.5281/zenodo.20682998`.

## Maintenance Guardrails

- Do not edit files listed in `freeze_manifest.json` or
  `freeze_manifest_v2.json` unless intentionally creating a documented new
  scientific freeze.
- Do not update Level 1 reference data outside the canonical Linux/amd64 Docker
  path.
- Keep Level 2 as form validation unless a separate tolerance tier is explicitly
  registered.
- Keep Level 3 as analysis-from-archived-counts only.
- Run `python pap/verify_freeze.py` and confirm v2 zero drift before claiming
  the audit trail is clean.
