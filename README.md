# Finite-Shot Operating Windows for VD/SV

Reproduction package for the numerical experiments accompanying the paper on
finite-shot operating windows for virtual distillation (VD) and symmetry
verification (SV).

This repository contains the frozen Level 1 reproduction core, the v2 PAP
amendment audit trail, post-freeze diagnostic analyses, secondary robustness
benchmarks, the additive Level 2 device-simulation layer, and the archive-only
Level 3 IBM hardware analysis layer.

For current reproduction, use:

- `REPRODUCIBILITY_STATUS.md` for the operational status and command map.
- `pap/FREEZE_STATUS.md` for the freeze provenance and real freeze audit.
- `REPRODUCING.md` for the one-command reviewer path.

`EXPERIMENTAL_PLAN.md`, `REPRODUCIBILITY_PLAN.md`, and `METHODS.md` are frozen,
hash-audited artifacts. They are retained for provenance and are not the current
reviewer guide.

The active post-freeze driver is `reproducibility/run_all_current.py`. The
original `reproducibility/run_all.py` and `reproducibility/run_all_v2.py` remain
unchanged PAP artifacts so the registered freezes stay auditable.

Entrypoint status for reviewers:

| Status | Entrypoints | Use |
| --- | --- | --- |
| Canonical | `reproducibility/run_all_current.py`, `reproducibility/verify_current.py` | Use these for current reproduction. `verify_current.py` validates the Level 1 reference checksums before comparing generated outputs. |
| Frozen PAP artifacts | `reproducibility/run_all.py`, `reproducibility/run_all_v2.py`, `reproducibility/verify.py` | Do not run these for current reproduction; they remain only so the registered PAP freezes can be audited. `verify.py` does not validate reference checksums. |

## Canonical Reproduction Contract

The canonical numerical environment is the Linux/amd64 Docker image defined by
`Dockerfile`. Its base image is pinned by digest and Python dependencies are
installed from the single hash-locked `requirements.lock` file.

Canonical Level 1 reference data in `reproducibility/reference/` are generated
inside that Linux/amd64 container in `--mode full`. In the canonical container,
`--exact-numeric` is the expected verification mode. Windows and macOS are
treated as non-canonical cross-platform checks and are verified with the
registered tolerances in `reproducibility/config/tolerances.yaml`.

Use `REPRODUCING.md` for the one-command reviewer path.

## Freeze Status

There are two registered freezes:

- v1 original PAP: `freeze_manifest.json`, `PAP_HASH.txt`, frozen commit
  `0814ba7...`.
- v2 P1 negative-control amendment: `freeze_manifest_v2.json`,
  `PAP_HASH_v2.txt`, frozen commit `555d3dc...`.

The current tree is expected to audit as:

- v1: intact with the documented expected CRLF drift.
- v2: intact with zero drift.

Run the real audit with:

```bash
python pap/verify_freeze.py
```

`pap/hash_pap.py --check-only` and `pap/hash_pap_v2.py --check-only` are not the
registered drift audit; they recompute hashes. Use `pap/verify_freeze.py` for
freeze integrity.

## What Is Reproducible Now

Manuscript figures regenerate with `make figures-manuscript` from committed
`results/confirmatory_v2/`, Level 2 CSVs, `results/secondary/` where relevant,
and `level3/archive/`. Exact PDF byte identity is not a reproducibility claim.

### Level 1 Core

The hard reproducible numerical core is Level 1 white-box density-matrix
simulation. It uses NumPy/SciPy only and does not require Qiskit.

Canonical Level 1 outputs are verified against `reproducibility/reference/`:

| Experiment | Prediction family | Output |
| --- | --- | --- |
| E1 quotient MSE decomposition | P1, P2 | `e1_quotient_decomposition.csv` |
| E2 `c_SV = 0` vs `c_VD != 0` | P3, P4 | `e2_c_sv_zero.csv` |
| E3 `delta_VD` from generator | P5 | `e3_delta_vd_generator.csv` |
| E4 `delta_SV` first order | P6 | `e4_delta_sv_firstorder.csv` |
| E5 denominator concentration | P7 | `e5_denominator_concentration.csv` |
| E7 certified-crossing diagnostic | P9 | `e7_certified_crossing.csv` |
| E7 resource/observable sensitivity | robustness | `e7_resource_observable_sensitivity.csv` |

### Post-Freeze Diagnostics And Secondary Layers

The repository also includes additive, non-freeze analysis and secondary
benchmarks:

- Ensemble coverage and `c_VD` SE sensitivity under `analysis/`.
- E6, E8, E9, E10, E11, and E12 under `experiments/` with outputs under
  `results/secondary/`.
- These layers are reported descriptively unless their own report says
  otherwise. They are not a new PAP freeze or a new primary validation tier.

### Level 2 Additive Device-Simulation

Level 2 is in `level2/` and remains an additive Phase B robustness layer:

- Qiskit/Aer foundation, noiseless reference, ordering check, and synthetic Aer
  noise model.
- Noisy Aer sampling for unmitigated and readout-mitigated SV, with
  postselection after readout mitigation.
- VD Hadamard/SWAP smoke checks.
- High-power exact-rho device-simulation harness.
- Realistic n=6 VD with interferometry/c-SWAP overhead.
- Denominator concentration, crossing diagnostics, Efron--Stein window checks,
  and small-noise P10 scaling.

Level 2 validates laws in form only. It is not a Level 1 coefficient-validation
claim, and it is outside the active `verify_current.py` reference contract. The
consolidated status is `level2/LEVEL2_SUMMARY.md`.

### Level 3 Archive-Only Hardware Analysis

Level 3 is in `level3/` and is reproducible from archived hardware counts only:

- Stage 2 precursor: `level3/level3_hardware_run_report.md`.
- Full Stage 3 `g6_k2_c000`: `level3/level3_full_p7p9_report.md`.
- Preliminary `g6_k2_c001` robustness check:
  `level3/level3_robustness_g6c001_report.md`.

Recompute the consolidated archive-only analyses in read-only mode with:

```bash
python scripts/reanalyze_level3_archives.py
```

or:

```bash
make analysis-from-hardware
```

This path reads `level3/archive/*.json.gz`; it does not connect to IBM Runtime
and does not submit QPU jobs. Hardware claims are qualitative feasibility and
form/robustness claims, not coefficient validation.

To intentionally refresh the versioned consolidated JSON summaries, use
`python scripts/reanalyze_level3_archives.py --update` or
`make analysis-from-hardware-update`.

## Quick Start

Canonical Docker path:

```bash
docker build --platform linux/amd64 -t finite-shot-vd-sv:repro .
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro bash -lc "make check-ci"
```

Expected canonical verifier line:

```bash
VERIFY PASS: 18260 numeric comparisons within tolerance across 7 files; reference checksums OK
```

For the full reviewer command including freeze audit and figure regeneration:

```bash
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro bash -lc "make reproduce-all"
```

Local non-Docker install from the canonical lock:

```bash
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
```

Set deterministic environment variables before local reproduction:

```bash
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

On PowerShell:

```powershell
$env:PYTHONHASHSEED=0
$env:OMP_NUM_THREADS=1
$env:MKL_NUM_THREADS=1
$env:OPENBLAS_NUM_THREADS=1
```

Regenerate and verify the canonical full Level 1 reference outputs:

```bash
python reproducibility/run_all_current.py --mode full --output results
python reproducibility/verify_current.py \
  --reference reproducibility/reference/ \
  --generated results \
  --exact-numeric
```

Verify the committed reference package without regenerating:

```bash
python reproducibility/verify_current.py \
  --reference reproducibility/reference/ \
  --generated reproducibility/reference/ \
  --exact-numeric
```

Use `--exact-numeric` for canonical Linux/Docker checks. For Windows/macOS,
omit `--exact-numeric` and use the registered tolerances; tiny ULP differences
in eigensolver/linear-algebra paths are treated as expected non-canonical drift.

Run tests:

```bash
python -m pytest tests/ -q
```

Audit the freezes:

```bash
python pap/verify_freeze.py
```

Verify Level 3 archive-only analyses without rewriting committed JSON files:

```bash
python scripts/verify_level3_archives.py
```

Docker path:

```bash
docker build --platform linux/amd64 -t finite-shot-vd-sv:repro .
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro
```

The Docker image runs the canonical Level 1 reproduction path by default.

Run Level 2 commands when the `[level2]` extra is installed:

```bash
pip install -e ".[level2]"
python -m level2.circuits
python -m level2.sampling
python -m level2.vd
python -m level2.highpower
python -m level2.vd_realistic_n6
python -m level2.crossing_denominator
python -m level2.window_efronstein
python -m level2.p10_smallnoise
```

## Make Targets

- `make reproduce-level1`: regenerate Level 1 outputs and verify them.
- `make reproduce-fast`: fast smoke/schema check against its own generated
  output; not the canonical reference comparison.
- `make reproduce-full`: regenerate the canonical full Level 1 outputs and
  verify them with `--exact-numeric`.
- `make reproduce-all`: run strict environment check, canonical Level 1,
  tests, freeze audit, Level 3 archive verification, and figure generation.
- `make verify`: run `reproducibility/verify_current.py` against generated
  outputs in `results/`.
- `make verify-exact`: exact numeric check against generated outputs in
  `results/`.
- `make verify-reference`: validate the committed Level 1 reference package.
- `make verify-freeze`: run the real v1/v2 freeze audit.
- `make verify-level3`: recompute Level 3 archive analyses in memory and compare
  them to committed JSON summaries.
- `make test`: run the test suite.
- `make check-ci`: canonical container check path: strict env, three full
  deterministic runs, exact full reproduction, tests, reference integrity, and
  Level 3 archive verification.
- `make audit`: run `pip-audit` against `requirements.lock`.
- `make reference-manifest`: refresh `reproducibility/reference/` checksums.
- `make level3-manifest`: refresh Level 3 archive checksums.
- `make level2-foundation`: run the Level 2 foundation smoke check.
- `make level2-sampling`: regenerate the Level 2 sampling report.
- `make analysis-from-hardware`: recompute Level 3 analysis from archived
  counts without rewriting committed JSON summaries.
- `make analysis-from-hardware-update`: intentionally refresh the consolidated
  Level 3 analysis JSON summaries.

## Current Limits

- The official `verify.py` reference package currently verifies the Level 1
  canonical outputs. The active wrapper is `verify_current.py`, which also
  checks reference SHA-256 manifests.
- Level 2 outputs are committed and tested as form validation. They are outside
  the official numeric reference contract unless a separate relaxed-tolerance
  Level 2 tier is explicitly defined.
- Level 3 hardware outputs are committed as raw-count archives plus reports;
  public reproduction is analysis-from-archived-counts only. The raw `.json.gz`
  archives and consolidated `.json` summaries are registered in
  `level3/archive/level3_archive_manifest.json`.
- `requirements.lock` is the single dependency lock for the canonical Docker
  environment and is installed with `pip --require-hashes`.
- The versioned archive DOI for the release used in the manuscript is
  `10.5281/zenodo.20682998`.
- Figures are regenerated from numerical data; exact PDF byte identity is not a
  reproducibility claim.

## Licenses

Code is MIT (`LICENSE`). Data and generated figures are CC-BY-4.0
(`LICENSE-DATA`).
