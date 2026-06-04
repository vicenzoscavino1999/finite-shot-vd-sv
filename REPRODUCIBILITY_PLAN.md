# Reproducibility plan for the VD/SV finite-shot operating-windows paper

This document defines the reproducibility package that should accompany the
paper on finite-shot operating windows for virtual distillation (VD) and
symmetry verification (SV). The goal is not only to publish code, but to make
the numerical claims auditable: a reviewer should be able to rebuild the
environment, rerun the experiments, regenerate the paper figures, and verify the
reported numerical outputs.

The public repository should be created as a clean repository, not by uploading
the current working folder directly.

> **Scope note specific to this paper.** Unlike a pure-simulation package, the
> VD/SV experimental plan spans three execution levels: Level 1 (white-box
> density-matrix, where coefficients such as `delta_VD`, `delta_SV`, `c_SV` are
> validated against closed forms), Level 2 (device-simulation with a calibrated
> Aer noise model, where laws are validated in *form*), and Level 3 (hardware,
> feasibility only). The hard-reproducible numerical core is **Level 1**. Level 2
> is reproducible up to RNG seeding. Level 3 is **analysis-reproducible only**,
> from archived raw counts — never by re-executing the quantum device. This
> distinction is enforced throughout the plan (see "Hardware reproduction
> carve-out").

## Core decision

The official reproduction route will be Docker-based.

Docker is the baseline environment, not an optional convenience layer. The local
Python environment can still be useful during development, but the published
instructions should treat the container as the authoritative execution
environment.

The dependency policy is:

- `pyproject.toml`: canonical project metadata and dependency bounds.
- `requirements-lock.txt`: exact locked dependencies generated inside the
  container, preferably with hashes using `pip-compile --generate-hashes`.
- No `environment.yml`, unless a future dependency truly requires Conda.
- No loose, unpinned `requirements.txt` as a reproducibility artifact.

If a casual install file is desired, it can be generated from the lockfile, but
the Docker route remains the official one.

> **Dependency caveat for Level 2/3.** Qiskit/Aer and the IBM Runtime client
> pull large transitive dependency trees and, in the case of the Runtime client,
> talk to an external service. Pin them in the lockfile like everything else, but
> document in `METHODS.md` that the Level 1 white-box core does **not** depend on
> Qiskit, so a reviewer can reproduce the coefficient-validation claims without
> any quantum-cloud account. Level 2/3 dependencies are required only for the
> robustness and feasibility levels.

## Interface with experimental plan

`EXPERIMENTAL_PLAN.md` (the VD/SV experimental plan, experiments E1–E12) is the
canonical source for experimental output filenames, schemas, scientific meaning,
and phase ownership.

This reproducibility plan consumes those outputs and defines how they are
verified, tolerance-checked, archived, versioned, and cited. It must not
redefine output filenames or schemas independently.

Conflict rule:

- `EXPERIMENTAL_PLAN.md` controls output filenames, schemas, phase ownership,
  and scientific interpretation.
- `REPRODUCIBILITY_PLAN.md` controls verification mechanics, tolerances,
  reference-data layout, Docker execution, CI, Zenodo archiving, and versioning.

Implementation rule:

- `reproducibility/config/schemas.yaml` should encode the schemas imported from
  the experiment sections (E1–E12) of `EXPERIMENTAL_PLAN.md`.
- `reproducibility/config/tolerances.yaml` should define tolerances for those
  imported schema fields.
- `reproducibility/reference/reference_manifest.json` should list the canonical
  files produced by the experimental plan and archived as reference outputs.

> **Pre-registration interface.** The VD/SV experimental plan is a pre-analysis
> plan: §2 of `EXPERIMENTAL_PLAN.md` freezes a falsifiable-prediction registry
> (P1–P13) and §9 freezes adjudication thresholds (`tau`, `tau_delta`, TOST
> margins, AIC thresholds) under a SHA-256 hash before any data is generated. The
> reproducibility package must archive that frozen PAP hash alongside the code
> commit, and `verify.py` must treat the prediction registry and adjudication
> table as canonical outputs subject to schema validation (see "Adjudication
> outputs").

## Release phases

The reproducibility work should be split into two phases. This prevents the
reproducibility package from becoming an open-ended blocker before submission.

### Phase A: submission-ready MVP

Goal: enough for a reviewer to verify the numerical claims made in the
manuscript.

Required scope:

- Clean repository skeleton.
- Functional, simple Dockerfile. Multi-stage optimization is not required yet.
- Level 1 white-box density-matrix simulator implemented from scratch in `src/vd_sv/`.
- `run_all.py` can generate the submission-relevant numerical outputs (at minimum
  the Level 1 coefficient-validation experiments E1–E4 and one crossing
  experiment E7).
- `verify.py` can compare generated outputs against reference data.
- `test_determinism.py` and `test_regression.py` pass.
- `README.md` explains `make reproduce-fast`, `make reproduce-full`, and
  `make verify`.
- Minimal `METHODS.md` exists, covering simulator choice, noise channel,
  observable and symmetry (XY-mixer / Hamming-weight sector), VD and SV estimator
  definitions, seed policy, qubit ordering, and how to run the MVP reproduction.
- Draft `CITATION.cff` and `.zenodo.json` exist, but final DOI integration is
  not required before submission.
- The manuscript has a draft code/data availability statement with a placeholder
  for the future Zenodo DOI.

Not required in Phase A:

- Multi-stage Dockerfile.
- Docker digest pinning.
- GitHub Actions.
- Pre-commit hooks.
- `CONTRIBUTING.md`.
- Complete 8-12 page `METHODS.md`.
- Zenodo release and final DOI.
- Full test suite.
- Level 2 (Aer) and Level 3 (hardware) outputs. These may be deferred to Phase B
  if the submission's core claims (coefficient recovery, certified crossing) are
  carried by Level 1.

### Phase B: archival release

Goal: enough for an independent researcher to reproduce, audit, reimplement,
and extend the work several years later.

Required scope:

- Multi-stage Dockerfile pinned by digest.
- Complete test suite.
- CI inside Docker.
- Full `METHODS.md`.
- `CONTRIBUTING.md`.
- Pre-commit guardrails.
- Advisory dependency vulnerability check.
- Final GitHub release.
- Zenodo archival release with version-specific DOI.
- Final paper-to-code mapping and DOI in the manuscript.
- Level 2 device-simulation outputs (reproducible up to RNG) and Level 3
  hardware raw-count archives with analysis-only reproduction.

Phase A is the minimum viable reproduction package. Phase B is the archival
research artifact.

## Repository layout

The target public repository should be:

```text
finite-shot-vd-sv/
  README.md
  METHODS.md
  CONTRIBUTING.md
  LICENSE
  LICENSE-DATA
  CITATION.cff
  .zenodo.json
  PAP_HASH.txt
  EXPERIMENTAL_PLAN.md
  REPRODUCIBILITY_PLAN.md
  Dockerfile
  .dockerignore
  .pre-commit-config.yaml
  .devcontainer/
    devcontainer.json
  Makefile
  pyproject.toml
  requirements-lock.txt
  .github/
    workflows/
      reproduce.yml
  src/
    vd_sv/
      __init__.py
      qaoa.py            # XY-mixer QAOA on a fixed Hamming-weight sector
      noise.py           # one-parameter noise channels; Delta = L(rho_star)
      density_matrix.py  # Level 1 exact density-matrix engine
      estimators.py      # finite-shot sampling, clipped quotient estimator
      vd.py              # controlled-derangement / Hadamard tests, SWAP test
      sv.py              # Hamming-weight postselection
      crossing.py        # certified crossing R*, eta = 4C/(g R0^2)
      lecam.py           # two-point lower bound, Bernoulli Fisher information
      coefficients.py    # closed-form b, c, v, delta_VD, delta_SV (white-box)
      plotting.py
  scripts/
    generate_all_figures.py
    two_qubit_phase_diagram.py
  experiments/
    e1_quotient_decomposition.py
    e2_c_sv_zero.py
    e3_delta_vd_generator.py
    e4_delta_sv_firstorder.py
    e5_denominator_concentration.py
    e6_copy_log_scale.py
    e7_certified_crossing.py
    e8_window_location_scaling.py
    e9_selection_trichotomy.py
    e10_implementation_noise.py
    e11_lecam_efficiency.py
    e12_efron_stein_operational.py
  reproducibility/
    run_all.py
    verify.py
    config/
      level1_coefficients.yaml      # E1-E4, E10 white-box
      level1_crossing.yaml          # E7, E8, E9, E11 white-box
      level2_device_sim.yaml        # E5, E6, E7, E12 on Aer noise model
      level3_hardware.yaml          # E5, E7 feasibility, analysis-only
      rng_policy.yaml
      schemas.yaml
      tolerances.yaml
    reference/
      reference_manifest.json
      <canonical experimental outputs from EXPERIMENTAL_PLAN.md>
      checksums.sha256
    hardware/
      raw_counts/                   # archived device counts (analysis-only)
      calibration_snapshots/
      job_metadata.json
  tests/
    fixtures/
      regression_2x2.csv
    test_quotient_law.py
    test_c_sv_zero.py
    test_delta_generator.py
    test_observable_bounds.py
    test_density_matrix.py
    test_symmetry_compatible.py
    test_crossing_certificate.py
    test_clipped_estimator.py
    test_determinism.py
    test_regression.py
    test_figures.py
    test_verify.py
  data/
  results/
    .partial/
  figures/
  paper/
    main.tex
    references.bib
```

The `paper/` directory is useful, but should remain clean. It should not include
temporary LaTeX files such as `.aux`, `.log`, `.out`, `.synctex.gz`, or local
editor files. The final PDF can be included in the Zenodo archive, but the
repository should not depend on committed compiled artifacts.

`LICENSE` should cover code. `LICENSE-DATA` should cover archived data and
figures, preferably under CC-BY-4.0. This avoids ambiguity when code and
scientific outputs are archived together.

`PAP_HASH.txt` records the SHA-256 hash and timestamp of the frozen pre-analysis
plan, so the confirmatory status of E1–E12 is auditable.

## Docker policy

The Docker image should be based on a pinned Python patch version. During
development, this is acceptable:

```dockerfile
FROM python:3.11.9-slim
```

For the final Zenodo release, pin the image by digest:

```dockerfile
FROM python:3.11.9-slim@sha256:<digest>
```

Do not use a floating tag such as `python:3.11-slim` for the archived release.
Floating tags can change the Debian base layer, system libraries, and numerical
behavior.

Preferred target:

- Multi-stage Dockerfile.
- Build stage installs build tools and dependencies.
- Runtime stage contains only Python, the installed package, and runtime
  dependencies.

A simple Dockerfile is acceptable during the first implementation pass, but the
final public release should use the multi-stage version if it does not create
unnecessary complexity.

The Dockerfile should set deterministic numerical defaults:

```dockerfile
ENV PYTHONHASHSEED=0
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
```

The reason is that BLAS/OpenMP parallelism can change the order of
floating-point operations. Pinning thread counts makes tight numerical
tolerances more defensible. This matters specifically for the Level 1
density-matrix engine, whose eigendecompositions (`lambda_2` for the copy-scale
prediction P8, sector spectra) are sensitive to BLAS operation order.

The repository must also include a `.dockerignore` file so the Docker build
context does not include Git history, large results, figures, LaTeX artifacts,
or — importantly — archived hardware counts.

Suggested `.dockerignore`:

```text
.git
data/
results/
figures/
paper/
reproducibility/hardware/raw_counts/
*.pdf
__pycache__/
*.pyc
.mypy_cache/
.pytest_cache/
```

The repository should also include:

```text
.devcontainer/devcontainer.json
```

This lets collaborators open the same environment in VS Code or compatible
tools.

## Makefile interface

The user-facing commands should be:

```makefile
reproduce: run verify

run:
	python reproducibility/run_all.py

verify:
	python reproducibility/verify.py --reference reproducibility/reference/

figures:
	python scripts/generate_all_figures.py

test:
	pytest tests/ -v

check: test verify

reproduce-fast:
	python reproducibility/run_all.py --mode fast
	python reproducibility/verify.py --reference reproducibility/reference/

reproduce-full:
	python reproducibility/run_all.py --mode full
	python reproducibility/verify.py --reference reproducibility/reference/

reproduce-level1:
	python reproducibility/run_all.py --level 1
	python reproducibility/verify.py --reference reproducibility/reference/

analysis-from-hardware:
	python reproducibility/run_all.py --level 3 --from-archived-counts
	python reproducibility/verify.py --reference reproducibility/reference/
```

`reproduce-fast` should use archived/reference numerical outputs when a full
grid would be too expensive. `reproduce-full` should recompute everything from
scratch (Level 1 and Level 2; Level 3 is never recomputed — see carve-out).

`reproduce-level1` recomputes only the white-box coefficient and crossing claims,
with no Qiskit dependency. This is the command a skeptical reviewer runs to check
that `delta_VD`, `delta_SV`, `c_SV = 0`, and the certified crossing match their
closed forms.

The README must clearly state which command reproduces the paper figures and
which command recomputes all numerical results from zero.

## Reproduction command contracts

The README should state exactly what each reproduction command proves.

`make reproduce-fast`:

- Runs a small deterministic subset defined in the level YAML files under
  `reproducibility/config/`.
- At minimum, this subset should include the Level 1 quotient-decomposition slice
  (E1), the `c_SV = 0` versus `c_VD != 0` discriminating test (E2), and a small
  representative crossing slice (E7).
- May use archived reference data for expensive outputs that are not recomputed
  in fast mode.
- Should complete in minutes, not hours. The measured time must be reported in
  the README before release.
- A pass means the code path, schemas, seeds, and numerical outputs are
  consistent with the published subset.
- A pass does not prove that the full grid has been recomputed correctly.

`make reproduce-full`:

- Recomputes every Level 1 and Level 2 numerical output needed for the paper
  figures and tables.
- Does not rely on archived numerical outputs except as verification targets.
- Does **not** re-execute hardware (Level 3); it consumes archived counts only.
- Should report measured runtime and RAM on the supported Docker platform.
- A pass means the package has reproduced the complete recomputable numerical
  content of the paper within the registered tolerances.

`make reproduce-level1`:

- Recomputes only the white-box coefficient and crossing claims.
- Has no Qiskit/Aer or quantum-cloud dependency.
- A pass means the closed-form coefficients (`b`, `c`, `v`, `delta_VD`,
  `delta_SV`) and the certified crossing reproduce exactly within machine
  tolerance.

`make analysis-from-hardware`:

- Recomputes Level 3 post-processing from archived raw counts and calibration
  snapshots.
- Never contacts a quantum backend.
- A pass means the hardware *analysis* (estimator values from counts, crossing
  diagnostics) reproduces; it does **not** re-run the device.

`make verify`:

- Performs schema validation and numerical comparison.
- Uses hard-fail semantics for canonical numerical outputs unless a field is
  explicitly marked as warning-only in `schemas.yaml`.
- Applies relaxed, documented tolerances to Level 2 fields that depend on
  stochastic noise-model sampling (see "Tolerance tiers by level").

## Fallback without Docker

The official reproduction path is Docker on `linux/amd64`. A non-Docker path can
be documented for users on HPC clusters, Podman, Singularity/Apptainer, or
locked-down institutional machines, but it is not the supported reproduction
path.

Non-Docker users may:

```bash
pip install -e .
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
make reproduce-fast
```

Outside Docker, strict tolerances may not hold. If needed, provide a
`tolerances-relaxed.yaml` file or `verify.py --relaxed` flag. The README should
state clearly that relaxed verification is diagnostic and is not the archival
reproduction standard.

Additional operational targets:

```makefile
check-env:
	python reproducibility/run_all.py --check-env-only

determinism-check:
	python reproducibility/run_all.py --mode fast --output results/determinism-run-1
	python reproducibility/run_all.py --mode fast --output results/determinism-run-2
	python reproducibility/verify.py \
		--reference results/determinism-run-1 \
		--generated results/determinism-run-2 \
		--exact-numeric
```

`determinism-check` should compare only canonical numerical outputs, such as
CSV and JSON result files. It should not compare `manifest.json`, `run.log`, or
generated PDF figures because timestamps, runtimes, and plotting metadata can
differ across runs. It should be restricted to Level 1 outputs; Level 2 Aer
sampling is deterministic only when the noise-model RNG seed is also pinned, so
the determinism check on Level 2 must fix that seed explicitly or be skipped.

## Pre-flight checks

Before any expensive computation, `run_all.py` should execute pre-flight checks.
The same checks should also be available through `make check-env`.

Required checks:

- Python, NumPy, and SciPy versions match the lockfile.
- `PYTHONHASHSEED=0`.
- `OMP_NUM_THREADS=1`.
- `MKL_NUM_THREADS=1`.
- `OPENBLAS_NUM_THREADS=1`.
- Architecture is `x86_64`; warn, but do not necessarily fail, on `aarch64`.
- The working directory has no orphaned partial outputs unless resume mode is
  active.
- The output directory is writable.
- The frozen PAP hash in `PAP_HASH.txt` matches the hash recorded in the
  reference manifest; warn on mismatch (confirmatory-status signal).
- For Level 2 runs: Qiskit/Aer import succeeds and the noise-model RNG seed is
  set.
- For Level 3 analysis runs: archived counts and calibration snapshots exist and
  their checksums match; **fail** if absent, because hardware cannot be
  regenerated.

Critical failures should abort before numerical work starts. This avoids
wasting hours on a run that cannot produce supported reproduction artifacts.

## Long-running execution policy

Any computation expected to exceed roughly 30 minutes should support
checkpointing and recovery.

Rules:

- `run_all.py` writes partial results block-by-block under `results/.partial/`.
- A block is considered complete only after its data and SHA-256 checksum have
  both been written.
- On startup, `run_all.py` detects complete partial blocks and resumes from the
  first missing or corrupt block.
- Corrupt partial blocks are ignored and recomputed.
- `run_all.py --restart` deletes existing partial outputs and starts from
  scratch.
- The final `manifest.json` records whether the run was clean or resumed, how
  many blocks were recovered, and how many blocks were recomputed.

A natural block granularity for this paper is one experiment cell
(instance x n x p x B x M x method), matching the grid structure declared in the
experimental plan. This makes `reproduce-full` robust to interrupted sessions,
power failures, and CI timeouts.

Error handling:

- Default behavior is fail-fast. If an experiment raises an exception, produces
  `NaN`/`Inf`, or fails schema validation, `run_all.py` aborts.
- A diagnostic `--continue-on-error` flag may continue independent experiments,
  but the final manifest must mark failed outputs as `incomplete`.
- `verify.py` must fail when required outputs are marked `incomplete`.
- Memory errors should be logged with the active block id so resumed execution
  can restart from the last complete block.

## Hardware reproduction carve-out

This section has no analogue in a pure-simulation package and is mandatory here
because the experimental plan includes Level 3 (IBM hardware) experiments.

Principle: **quantum-device execution is not reproducible by re-running it.**
Queue conditions, calibration drift, and backend availability make a re-executed
job a different physical experiment. The reproducibility contract for Level 3 is
therefore *analysis reproduction from archived raw data*, not execution
reproduction.

Rules:

- Every hardware job archives, under `reproducibility/hardware/`:
  - raw measurement counts per circuit (`raw_counts/<job_id>.json`),
  - a calibration snapshot at submission time (backend properties: T1/T2, gate
    and readout error rates, `calibration_snapshots/<job_id>.json`),
  - job metadata (backend name, job id, submission UTC, transpilation seed,
    shot count, `job_metadata.json`).
- `verify.py` reproduces only the **post-processing**: estimator values, crossing
  diagnostics, and figures computed *from the archived counts*. It never submits
  a job.
- The counts archive is treated as primary data under `LICENSE-DATA` (CC-BY-4.0)
  and is included in the Zenodo deposit, not in the Docker build context.
- Hardware outputs are explicitly excluded from `determinism-check` and from
  bit-for-bit tolerance claims. Their reproducibility statement is: "the analysis
  pipeline applied to the archived counts reproduces the reported hardware
  estimators within the registered tolerance."
- The README and `METHODS.md` must state plainly that Level 3 results are a
  feasibility demonstration and that the only reproducible artifact is the
  analysis-from-counts path. This honesty is required to avoid a referee reading
  an irreproducible hardware claim as a defect.

## Verification policy

The repository needs explicit numerical verification, not only scripts that
generate plots.

Required files:

```text
reproducibility/
  reference/
    reference_manifest.json
    <canonical experimental reference outputs>
    checksums.sha256
  config/
    level1_coefficients.yaml
    level1_crossing.yaml
    level2_device_sim.yaml
    level3_hardware.yaml
    rng_policy.yaml
    schemas.yaml
    tolerances.yaml
  run_all.py
  verify.py
```

The concrete reference filenames are imported from the canonical output lists in
`EXPERIMENTAL_PLAN.md`. Do not add a new reference filename here unless the
experimental plan first declares it as a canonical output.

The `run_all.py` script should write a provenance manifest at the end of each
execution:

```text
results/manifest.json
```

Minimum manifest content:

```json
{
  "git_commit_sha": "abc123...",
  "git_dirty": false,
  "pap_hash": "sha256:...",
  "level": 1,
  "python_version": "3.11.9",
  "platform": "Linux-6.1.0-x86_64",
  "cpu_model": "AMD EPYC 7763",
  "ram_total_gb": 16.0,
  "timestamp_utc": "2026-05-30T14:32:00Z",
  "dependencies": {
    "numpy": "1.26.4",
    "scipy": "1.12.0",
    "qiskit": "1.x.x",
    "qiskit-aer": "0.x.x"
  },
  "runtime_seconds": 3847.2,
  "outputs": {
    "e2_c_sv_zero.csv": "sha256:...",
    "e3_delta_vd_generator.csv": "sha256:..."
  }
}
```

The `verify.py` script should:

1. Load generated outputs.
2. Load reference outputs.
3. Validate output structure against `schemas.yaml`.
4. Fail clearly on missing rows.
5. Fail clearly on extra or missing columns.
6. Fail clearly on unexpected data types.
7. Fail clearly on `NaN` or `Inf` in numerical columns.
8. Match rows by explicit keys.
9. Compare each numerical column using tolerances from `tolerances.yaml`,
   selecting the tolerance tier by the `level` field of the output.
10. Report pass/fail by file, row group, and column.
11. Read and report `results/manifest.json` when present.
12. Warn, but do not fail, when the manifest is absent.
13. Validate the adjudication table (see "Adjudication outputs") against the
    frozen prediction registry.
14. Exit with nonzero status on numerical or schema failure.

Failure budget:

- Canonical numerical outputs use hard-fail semantics.
- The verification passes if and only if every required numerical field is
  within its registered tolerance and every required schema check passes.
- There is no soft-pass for "small" tolerance violations.
- Warning-only fields must be explicitly marked as warning-only in
  `schemas.yaml`; otherwise failures are hard failures.

The schema file should define expected output formats before any numerical
comparison is attempted. Its filenames and fields should be imported from
`EXPERIMENTAL_PLAN.md`; the YAML below is illustrative only.

Illustrative schema file:

```yaml
e2_c_sv_zero.csv:
  format: csv
  level: 1
  row_matching_key: [noise_strength, B, method]
  columns:
    noise_strength:
      type: float
      min: 0.0
      max: 1.0
    B:
      type: int
      min: 1
    method:
      type: string
      allowed: [vd, sv]
    bias_minus_pop:
      type: float
    c_slope_estimate:
      type: float
    c_slope_ci_lower:
      type: float
    c_slope_ci_upper:
      type: float

e3_delta_vd_generator.csv:
  format: csv
  level: 1
  row_matching_key: [noise_strength]
  columns:
    noise_strength:
      type: float
      min: 0.0
      max: 1.0
    b_vd_inf:
      type: float
    delta_vd_measured:
      type: float
    delta_vd_closed_form:
      type: float

e7_certified_crossing.csv:
  format: csv
  level: 1
  row_matching_key: [noise_strength, resource_R]
  columns:
    noise_strength:
      type: float
    resource_R:
      type: float
      min: 0.0
    mse_vd:
      type: float
      min: 0.0
    mse_sv:
      type: float
      min: 0.0
    crossing_R_empirical:
      type: float
    crossing_R0_certified:
      type: float
    eta_certified:
      type: float
      min: 0.0

manifest.json:
  format: json
  required_fields:
    git_commit_sha:
      type: string
    git_dirty:
      type: bool
      severity_if_true: warning
    pap_hash:
      type: string
    level:
      type: int
    python_version:
      type: string
    platform:
      type: string
    timestamp_utc:
      type: string
    dependencies:
      type: object
    runtime_seconds:
      type: float
      min: 0.0
    outputs:
      type: object
    execution_mode:
      type: string
      allowed: [clean, resumed, restarted]
    recovered_blocks:
      type: int
      min: 0
```

### Adjudication outputs

Because the experimental plan is a pre-analysis plan, the package treats the
prediction registry and its adjudication as canonical, schema-validated outputs.

```yaml
adjudication_table.csv:
  format: csv
  level: 1
  row_matching_key: [prediction_id]
  columns:
    prediction_id:
      type: string
      allowed: [P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13]
    predicted_value_or_scale:
      type: string
    estimate:
      type: float
    ci_lower:
      type: float
    ci_upper:
      type: float
    verdict:
      type: string
      allowed: [CONFIRM, REFUTE, INCONCLUSIVE]
    level_of_evidence:
      type: int
      allowed: [1, 2, 3]
```

`verify.py` should fail if a prediction listed in the frozen registry is missing
from the adjudication table, and should warn if a verdict changes between the
reference and a regenerated run (a strong signal that code or data drifted from
the pre-registered state).

## Tolerance tiers by level

The single most important adaptation from a pure-simulation package: **not all
levels admit the same tolerance regime.** `verify.py` selects the tier by the
`level` field.

- **Level 1 (white-box, deterministic):** tight tolerances. Closed-form
  coefficients and the certified crossing are deterministic given seed, NumPy
  version, and thread counts. Use machine-level `atol` for closed-form quantities
  and calibrated tight tolerances for finite-shot estimators (see registration
  policy). This is the tier that carries the coefficient-validation claims.
- **Level 2 (Aer device-simulation, stochastic):** relaxed, *documented*
  tolerances. The noise-model sampler introduces variation that is deterministic
  only with a pinned RNG seed; even then, Aer version changes can move ULPs.
  Calibrate these tolerances from at least three seeded container runs and record
  them as Level 2 tolerances. Form-level claims (does the law hold, is there a
  crossing) are verified, not exact coefficients.
- **Level 3 (hardware analysis-from-counts):** the counts are fixed archived
  data, so the *analysis* is deterministic and can use Level 1-style tight
  tolerances on the post-processing — but the underlying physical values are not
  reproducible and are never compared across jobs.

Illustrative tolerance file:

```yaml
e3_delta_vd_generator:
  level: 1
  row_matching_key: [noise_strength]
  columns:
    b_vd_inf:
      atol: 1.0e-12
      rtol: 0.0
      # Closed-form / large-M plateau, deterministic.
    delta_vd_measured:
      atol: 1.0e-10
      rtol: 1.0e-8
      # Finite-shot regression slope; tight inside container with fixed seed.
    delta_vd_closed_form:
      atol: 1.0e-12
      rtol: 0.0
      # Closed-form generator expression; deterministic.

e2_c_sv_zero:
  level: 1
  row_matching_key: [noise_strength, B, method]
  columns:
    c_slope_estimate:
      atol: 1.0e-10
      rtol: 1.0e-8
    bias_minus_pop:
      atol: 1.0e-12
      rtol: 0.0

e7_certified_crossing:
  level: 1
  row_matching_key: [noise_strength, resource_R]
  columns:
    crossing_R0_certified:
      atol: 1.0e-10
      rtol: 0.0
      # Closed-form crossing location.
    eta_certified:
      atol: 1.0e-10
      rtol: 0.0
    crossing_R_empirical:
      atol: 1.0e-8
      rtol: 1.0e-6
      # Root of a finite-shot MSE difference; calibrated.

e7_certified_crossing_level2:
  level: 2
  row_matching_key: [noise_strength, resource_R]
  columns:
    crossing_R_empirical:
      atol: 0.0
      rtol: 5.0e-2
      # Aer-sampled; relaxed, calibrated from three seeded runs. Verifies that
      # the crossing falls in the certified band, not its exact location.
```

Important correction: do not promise bit-for-bit reproducibility for every
artifact. Level 1 numerical CSV/JSON outputs can be verified tightly inside the
Docker container. Level 2 outputs are verified at the relaxed tier. Figures and
PDFs should usually be verified by regenerating them without error and by
checking the underlying numerical data. Matplotlib PDFs may contain metadata,
font, or timestamp differences that make strict checksums fragile.

Every tolerance in `tolerances.yaml` should have a one-line justification.
Tight tolerances should be set only after running the same container twice and
measuring the actual differences.

Tolerance registration policy:

- Calibrate tolerances on the `reproduce-fast` subset, not on the full grid.
- Use at least three repeated container runs when setting tight tolerances.
- Set the final tolerance to `max(observed_difference) * safety_factor`, with a
  default safety factor of `10`.
- If the observed difference is exactly zero across all calibration runs, use a
  machine-level tolerance and document the result.
- The same tolerances should then be applied to `reproduce-full` without
  automatic relaxation.
- If the full grid violates tolerances calibrated on the fast subset, investigate
  the cause instead of increasing tolerances to make the full run pass.
- Level 2 tolerances are calibrated separately, with the noise-model RNG seed
  pinned, and are documented as relaxed by construction.

The number of calibration runs, observed maximum difference, and safety factor
should be documented in `METHODS.md`.

Reference data should also be versioned explicitly. Prefer a separate
`reference_manifest.json` instead of embedding comments in CSV files.

Example:

```json
{
  "git_tag": "v1.0.0-initial-submission",
  "git_commit_sha": "abc123...",
  "pap_hash": "sha256:...",
  "created_utc": "2026-05-30T14:32:00Z",
  "files": {
    "e2_c_sv_zero.csv": "sha256:...",
    "e3_delta_vd_generator.csv": "sha256:...",
    "e7_certified_crossing.csv": "sha256:..."
  }
}
```

`verify.py` should compare the generated `manifest.json` tag or commit against
`reference_manifest.json` and emit a warning if they do not match. A mismatch is
not automatically a numerical failure, but it is a strong signal that code and
reference data may come from different release states.

## Reference data update policy

Reference data should change only when the code or configuration that generates
scientific outputs changes.

Rules:

- Do not update reference data for formatting, logging, documentation, or test
  harness changes.
- Every reference-data update requires a commit message explaining why numerical
  values changed.
- If reference data changes but paper-reported values do not change, document
  that the change is below reporting precision.
- If reference data changes and paper-reported values change, create a new minor
  version tag for the manuscript/reproduction package.
- If only metadata changes in `reference_manifest.json`, explain that separately
  from numerical-output changes.
- Hardware count archives are never "updated"; a new device run is a new
  archived artifact with a new job id, not a replacement.

## Execution logging policy

`run_all.py` should use Python's `logging` module instead of raw `print()`
progress output.

Required behavior:

- Write line-oriented logs to `results/run.log`.
- Use the format `ISO_TIMESTAMP | LEVEL | MODULE | MESSAGE`.
- Log each grid block start, finish, duration, and partial-output hash.
- Log pre-flight checks and whether each check passed, warned, or failed.
- Log whether the execution is clean, resumed, or restarted.
- Log the execution level (1, 2, or 3) and, for Level 3, the job ids whose
  archived counts were consumed.
- Record the log path in `results/manifest.json`.

This makes reproduction failures diagnosable without rerunning a long
experiment.

## Data policy

The README must include data policy, platform support, and limitations sections.

Template:

```markdown
## Data Policy

This repository contains three categories of outputs.

### Archived in the Zenodo deposit

- canonical CSV/JSON outputs declared in `EXPERIMENTAL_PLAN.md`
- the adjudication table for predictions P1-P13
- `figures/*.pdf`
- Level 3 hardware raw counts, calibration snapshots, and job metadata

### Recomputable (Level 1 and Level 2)

- Level 1 white-box coefficient and crossing outputs
  - Regenerated by: `make reproduce-level1` (no Qiskit dependency)
- Level 2 device-simulation outputs
  - Regenerated by: `make reproduce-full`
  - Estimated runtime: Phase B deferred until the backend snapshot is frozen
  - Required RAM: Phase B deferred until the backend snapshot is frozen

### Analysis-reproducible only (Level 3)

- Hardware estimator values and crossing diagnostics
  - Regenerated from archived counts by: `make analysis-from-hardware`
  - The quantum device is never re-executed.

All Level 1/2 archived numerical outputs can be independently verified against
regenerated outputs using `make verify`. Level 3 verification reproduces the
analysis pipeline applied to archived counts only.

Code is licensed under MIT. Archived data, hardware counts, and figures are
licensed under CC-BY-4.0.

## Platform Support

Reproducibility is verified inside the Docker container on `linux/amd64`.
Results on `linux/arm64`, including Apple Silicon, may differ at the ULP level
because of different BLAS/LAPACK implementations. Native macOS and Windows
execution are useful for development but are not the supported reproduction
path. Level 2 reproduction additionally depends on the pinned Qiskit/Aer
versions; Level 3 analysis depends only on the archived counts and the
post-processing code.

## Limitations

Figures and PDFs are regenerated from the verified numerical outputs, but they
are not required to be bit-identical because plotting backends may include
metadata, font, or timestamp differences.

Runtime depends on hardware. Reported runtimes are approximate and should list
the CPU, RAM, and Docker platform used for the benchmark.

Out of scope:

- GPU reproduction.
- Native Windows reproduction.
- Native macOS reproduction.
- Interactive notebooks as the official reproduction path.
- Reproduction with future unpinned NumPy/SciPy/Qiskit/Aer versions.
- Re-execution of quantum hardware. Level 3 is analysis-reproducible only.
- Performance benchmarking as a scientific claim.
```

If a full grid is computationally expensive, the runtime and RAM cost should be
reported honestly. This is not a weakness; it prevents reviewers from confusing
a long computation with a broken reproduction package. Any deferred runtime
field must be replaced with measured values before the corresponding public
release.

## Paper-to-code mapping

The README should include a table mapping every paper claim, figure, and table
to the code and verification artifact that supports it. For this paper the
mapping should also name the theorem/proposition label and the prediction id, so
the experiment-theory link is explicit.

Template:

```markdown
| Paper element | Theory anchor | Prediction | Source code | Output | Verification |
| --- | --- | --- | --- | --- | --- |
| VD quotient MSE law | Thm `vd_quotient_certified_v4` | P1 | `experiments/e1_quotient_decomposition.py` | `results/e1_quotient_decomposition.csv`, `figures/e1_quotient_law.pdf` | `verify.py` checks the E1 canonical outputs |
| c_SV = 0 vs c_VD != 0 | `sv_quotient_bias_zero_v14`, `vd_c_v4` | P3, P4 | `experiments/e2_c_sv_zero.py` | `results/e2_c_sv_zero.csv`, `figures/e2_c_sv.pdf` | `verify.py` + `tests/test_c_sv_zero.py` |
| delta_VD from generator | Prop. `vd_delta_generator` | P5 | `experiments/e3_delta_vd_generator.py`, `src/vd_sv/coefficients.py` | `results/e3_delta_vd_generator.csv` | `tests/test_delta_generator.py` |
| Denominator concentration | Lem. `denom_bernstein_v4` | P7 | `experiments/e5_denominator_concentration.py` | `results/e5_denominator_concentration.csv`, `figures/e5_denominator_concentration.pdf` | `verify.py` + `tests/test_denominator_concentration.py` |
| Crossing diagnostic | Thm `certified_crossing` | P9 | `experiments/e7_certified_crossing.py`, `src/vd_sv/crossing.py` | `results/e7_certified_crossing.csv`, `figures/e7_crossing.pdf` | `tests/test_crossing_certificate.py` |
| Resource/O sensitivity | Remark `resource_normalization_v13`, EXP. PLAN §10 | robustness | `experiments/e7_resource_observable_sensitivity.py` | `results/e7_resource_observable_sensitivity.csv`, `figures/e7_resource_observable_sensitivity.pdf` | `verify.py` + `tests/test_sensitivity.py` |
| Symmetry-compatible observable | SV section hypothesis (PO = OP) | — | `src/vd_sv/qaoa.py`, `src/vd_sv/sv.py` | unit-test output | `tests/test_symmetry_compatible.py` |
| Deterministic finite-shot reproduction | — | — | `reproducibility/run_all.py` | repeated fast outputs | `make determinism-check` |
```

This mapping should be updated whenever a paper figure, table, or numerical
claim is added, removed, or renamed.

## Tests

The test suite should focus on scientific correctness and determinism.

Required tests:

```text
tests/
  test_quotient_law.py
  test_c_sv_zero.py
  test_delta_generator.py
  test_observable_bounds.py
  test_density_matrix.py
  test_symmetry_compatible.py
  test_crossing_certificate.py
  test_clipped_estimator.py
  test_determinism.py
  test_regression.py
  test_figures.py
  test_verify.py
```

Test responsibilities:

- `test_quotient_law.py`: the empirical MSE decomposition recovers
  `b^2 + (v + 2bc)/B` to leading order on a small white-box cell, and the
  remainder term is bounded as certified.
- `test_c_sv_zero.py`: the SV quotient bias coefficient is zero within tolerance,
  while the VD coefficient is nonzero and matches `vd_c_v4`. This is the
  discriminating structural test.
- `test_delta_generator.py`: measured `delta_VD` and `delta_SV` agree with the
  closed-form generator expressions on the white-box channel.
- `test_observable_bounds.py`: the cost observable remains inside `[-1, 1]` after
  normalization.
- `test_density_matrix.py`: density matrices remain Hermitian, trace-preserving,
  and positive within numerical tolerance.
- `test_symmetry_compatible.py`: the cost observable commutes with the symmetry
  operator (`PO = OP`), so SV's hypothesis holds for the chosen instance family.
  This guards against silently reverting to a MaxCut/`X^n` setup where the
  hypothesis fails.
- `test_crossing_certificate.py`: the empirical crossing falls inside the
  certified band `[R0(1-eta), R0(1+eta)]` and `eta < 1/2` on the test cell.
- `test_clipped_estimator.py`: the clipped quotient estimator matches the
  ordinary estimator once `B >= B_den`, and the clip activates below threshold.
- `test_determinism.py`: the same seed produces identical Level 1 outputs for a
  small experiment.
- `test_regression.py`: a small `2x2` grid matches a committed reference CSV.
- `test_figures.py`: every figure script runs without error.
- `test_verify.py`: the verifier passes on clean reference outputs and fails on
  deliberately perturbed outputs.

The two most important tests are `test_determinism.py` and
`test_regression.py`. If either fails, the reproduction story is weak.
`test_verify.py` is the guard against a false-positive verifier.
`test_c_sv_zero.py` and `test_delta_generator.py` are the two tests that
demonstrate the apparatus is exercised rather than decorative.

`test_verify.py` should include at least:

- `test_verify_clean_passes`
- `test_verify_perturbed_fails`
- `test_verify_missing_rows_fails`
- `test_verify_extra_columns_fails`
- `test_verify_missing_columns_fails`
- `test_verify_nan_values_fails`
- `test_verify_type_mismatch_fails`
- `test_verify_missing_manifest_warns`
- `test_verify_empty_output_fails`
- `test_verify_missing_prediction_in_adjudication_fails`
- `test_verify_level2_uses_relaxed_tolerance`

## Randomness policy

All finite-shot and bootstrap randomness should be generated with:

```python
numpy.random.Generator(numpy.random.PCG64(seed))
```

Do not use the legacy global `np.random.seed()` API in the reproduction path.

Each experiment should define its seed in a YAML config file. Seeds are arbitrary
constants, not tuned parameters. If an experiment uses multiple seeds for error
bars or bootstrap, the exact seed list or seed range should be written in the
config.

For Level 2, the Aer noise-model sampler has its own RNG; its seed must also be
recorded in `rng_policy.yaml` and set before sampling, otherwise even seeded
container runs will not be reproducible.

The config directory may include:

```text
reproducibility/config/rng_policy.yaml
```

This file should record the global RNG convention, the per-experiment seeds, the
bootstrap seed policy (BCa resampling), and the Aer noise-model seed for Level 2.

## Continuous integration

GitHub Actions should run the fast reproducibility path inside Docker.

Example workflow:

```yaml
name: Reproducibility Check

on:
  push:
  pull_request:

jobs:
  reproduce:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: vd-sv:test
      - run: >
          docker run --rm
          -v ${{ github.workspace }}/ci-results:/app/results
          vd-sv:test
          bash -c "make reproduce-fast && make test"
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: ci-results
          path: ci-results/
      - run: >
          docker run --rm vd-sv:test
          pip-audit -r requirements-lock.txt || true
        continue-on-error: true
```

The full grid does not need to run in CI. CI should check:

- package installation,
- unit tests,
- deterministic mini regression,
- fast reproduction (the Level 1 subset only — CI must not require a
  quantum-cloud account, so Level 2/3 are excluded from CI),
- numerical verification against committed reference outputs.

CI should target `linux/amd64`, matching the supported reproduction platform.
The mounted `ci-results` volume allows `manifest.json`, `run.log`, and failed
outputs to be inspected after CI failures. The `pip-audit` step is advisory and
must not block reproducibility of an archived scientific release.

Pre-commit hooks are recommended but should not block the initial implementation.
The final repository should include `.pre-commit-config.yaml` with:

- `ruff` or `black` for formatting.
- `ruff` for linting.
- a large-file guard that prevents accidental commits of large outputs under
  `results/`, `figures/`, `data/`, or `reproducibility/hardware/raw_counts/`.

## When verification fails

The README or `METHODS.md` should include a short triage guide.

```text
Verification failure
+-- atol/rtol exceeded by < 10x tolerance
|   +-- Level 2 (Aer) output?
|   |   +-- Expected; check Aer seed and version. Use Level 2 relaxed tier.
|   +-- Different architecture (arm64 vs amd64)?
|   |   +-- Expected possibility. Document in METHODS.md.
|   +-- Same architecture, different BLAS?
|   |   +-- Check OMP/MKL/OPENBLAS environment variables.
|   +-- Same environment?
|       +-- Compare NumPy/SciPy versions against manifest.json.
+-- atol/rtol exceeded by > 10x tolerance
|   +-- NaN or Inf present?
|   |   +-- Likely code bug. Check density-matrix and clipped-estimator tests.
|   +-- Finite but wrong?
|       +-- Compare seeds and rng_policy.yaml (including the Aer seed).
+-- Coefficient mismatch (delta_VD, delta_SV, c_SV)
|   +-- Level 1 only: real theory/code discrepancy. Stop and reconcile with the
|       manuscript before proceeding.
+-- Crossing outside certified band
|   +-- Check resource normalization kappa; the band depends on it.
+-- Row count mismatch
|   +-- run_all.py may have crashed mid-execution. Check run.log and .partial/.
+-- Adjudication verdict changed
|   +-- Code or data drifted from the frozen PAP. Check PAP_HASH.txt.
+-- verify.py itself errors
    +-- Possible schema change. Check Git tag against reference_manifest.json.
```

This guide is not a substitute for tests; it is an operational aid for external
users who encounter a failure.

## Versioning policy

Use explicit Git tags for every manuscript submission and revision.

Recommended convention:

```text
v1.0.0-initial-submission
v1.0.1-initial-submission-fix
v1.1.0-revision-1
v1.2.0-revision-2
```

Rules:

- `v1.0.0` is the code/data version accompanying the first manuscript
  submission.
- Patch versions, such as `v1.0.1`, are for fixes that do not change reported
  numerical results.
- Minor versions, such as `v1.1.0`, are for reviewer-response changes that do
  change results, figures, or tables.
- Major versions are reserved for a substantial rewrite of the paper or
  reproduction package.
- The suffix identifies the editorial stage; it is a practical tag convention
  rather than pure SemVer.
- The Zenodo DOI cited in the manuscript must point to the exact Git tag for
  that manuscript version.
- If the manuscript changes, create a new GitHub release and cite the new
  version-specific Zenodo DOI.

## Zenodo and GitHub release policy

The repository should include:

```text
CITATION.cff
.zenodo.json
```

The Zenodo metadata must match the actual paper. The current paper is about
finite-shot operating windows for virtual distillation and symmetry
verification. Do not reuse a title centered on a different method or a previous project.

Draft `.zenodo.json`:

```json
{
  "title": "Code and data for: Finite-Shot Operating Windows for Virtual Distillation and Symmetry Verification",
  "creators": [
    {
      "name": "Apellido, Vicenzo",
      "orcid": "0000-0000-0000-0000"
    }
  ],
  "description": "Reproduction package for the numerical experiments and figures accompanying the paper on finite-shot operating windows for virtual distillation (VD) and symmetry verification (SV). Includes white-box coefficient validation, certified-crossing experiments, device-simulation robustness runs, and archived hardware counts.",
  "license": "MIT",
  "upload_type": "software",
  "keywords": [
    "quantum error mitigation",
    "virtual distillation",
    "symmetry verification",
    "finite shots",
    "operating windows",
    "QAOA"
  ],
  "related_identifiers": []
}
```

Use `MIT` for code. Include `LICENSE-DATA` and the README data policy to state
that archived numerical data, hardware counts, and generated figures are
CC-BY-4.0. If the final archive or journal system requires a single license
field, document the dual-license policy clearly in the archive description.

Once an arXiv identifier or journal DOI exists, update `related_identifiers` in
a new release:

```json
"related_identifiers": [
  {
    "identifier": "arXiv:XXXX.XXXXX",
    "relation": "isSupplementTo",
    "scheme": "arxiv"
  },
  {
    "identifier": "10.XXXX/journal.XXXXX",
    "relation": "isSupplementTo",
    "scheme": "doi"
  }
]
```

The paper should cite the version-specific Zenodo DOI, not only the conceptual
DOI:

```text
Code and data are archived at Zenodo (DOI: 10.5281/zenodo.XXXXXXX,
version v1.0.0-initial-submission).
```

The `CITATION.cff` file should eventually include the paper DOI or arXiv record
as a reference, so GitHub, Zenodo, and the paper point to each other.

## Contributing policy

Include a short `CONTRIBUTING.md`.

Suggested content:

```markdown
# Contributing

This repository is a research reproduction artifact, not a general-purpose
open-source project.

Issues reporting reproduction failures are welcome. Please include the Docker
image digest, Git tag, execution level, `results/manifest.json`, and
`results/run.log`.

Pull requests are considered only for documented bug fixes or reproducibility
fixes. New research extensions should generally be developed in forks.

The code is available under the repository code license, and archived data,
hardware counts, and figures are available under the data license.
```

## METHODS.md content

`METHODS.md` should document the computational choices that may be too detailed
for the main paper.

Required sections:

1. Why the official Level 1 simulator is a custom density-matrix simulator
   rather than Qiskit/Aer, and why Qiskit/Aer is required only for Level 2.
2. Exact QAOA circuit definition, including the XY-mixer and the fixed
   Hamming-weight sector.
3. Exact noise channels and parameter conventions, including how the noise scale
   `p` is defined and how `Delta = L(rho_star)` is obtained (closed form plus
   finite-difference cross-check).
4. Observable definition and the symmetry operator, with an explicit argument
   that the observable is symmetry-compatible (`PO = OP`) for the chosen
   instance family.
5. Qubit ordering convention:
   - little-endian or big-endian,
   - how qubits are indexed in the gate list,
   - whether the convention matches Qiskit,
   - exact mapping needed for Qiskit/Aer cross-checks.
6. How finite-shot samples are generated for VD (controlled-derangement /
   Hadamard tests, SWAP test) and for SV (Hamming-weight postselection), and the
   clipped quotient estimator with its threshold.
7. Random number generator and seed initialization, including the separate Aer
   noise-model seed for Level 2 and the bootstrap (BCa) seed policy.
8. Why deterministic numerical environment variables are set in Docker.
9. How the coefficients `b`, `c`, `v`, `delta_VD`, `delta_SV` are extracted from
   data (the regression/TOST protocol) and compared against closed forms.
10. The certified crossing computation: `R0`, `g`, `eta = 4C/(g R0^2)`, the
    certified band, and the resource normalization `kappa` used.
11. Resource-normalization sensitivity: which `kappa` definitions were used and
    whether any crossing changed side.
12. The three-level architecture and exactly what is reproducible at each level,
    including the hardware analysis-from-counts contract.
13. Difference between `reproduce-fast`, `reproduce-full`, `reproduce-level1`,
    and `analysis-from-hardware`.
14. Known numerical tolerances, by level, and why they are acceptable.

Target detail level:

- Simulator choice, deterministic environment variables, and the four
  reproduction modes: one paragraph each.
- QAOA circuit, symmetry/observable, noise model: one to two paragraphs plus
  equations; enough to reimplement without reading the code.
- Qubit ordering: explicit table with a concrete three- or four-qubit example.
- Finite-shot sampling and RNG (VD and SV separately): one paragraph plus
  pseudocode each.
- VD and SV estimator implementations and the clipped quotient: two to three
  paragraphs each plus equations.
- Coefficient-extraction protocol and crossing certificate: two to three
  paragraphs plus equations.
- Tolerances: table by level, not prose-only explanation.

Target length: 8-12 pages. Shorter is likely insufficient for independent
reimplementation; much longer may indicate material that belongs in a paper
appendix.

For Phase A, a shorter `METHODS.md` is acceptable if it documents the Level 1
simulator, noise channel, symmetry/observable, qubit ordering, VD/SV estimators,
seed policy, and reproduction commands. The 8-12 page target is for the Phase B
archival release.

The explanation for not making Qiskit mandatory should be direct:

```text
The Level 1 simulations use an explicit density-matrix implementation to make the
noise model, the generator Delta = L(rho_star), the estimator sampling, and the
finite-shot bookkeeping transparent and fully controlled, so that the closed-form
coefficients delta_VD, delta_SV, c_SV and the certified crossing can be audited
directly. Qiskit/Aer is required only for the Level 2 device-simulation
robustness experiments; it is not part of the Level 1 coefficient-validation
reproduction path. Hardware (Level 3) is a feasibility demonstration whose only
reproducible artifact is the analysis applied to archived measurement counts.
```

## Implementation sequence

Recommended order with phase and rough effort estimates:

| # | Phase | Task | Estimate | Exit criterion |
| --- | --- | --- | --- | --- |
| 1 | A | Create clean repository skeleton | 1-2 h | Empty repo has the target directory layout. |
| 2 | A | Add `pyproject.toml`, simple `Dockerfile`, `.dockerignore`, `Makefile`, `.gitignore`, and `PAP_HASH.txt` | 3-5 h | `docker build` succeeds and package installs. |
| 3 | A | Implement the Level 1 density-matrix simulator and coefficient code from scratch in `src/vd_sv/` | 1-2 d | Importable package with no script-side global execution. |
| 4 | A | Implement VD/SV estimators and the clipped quotient (`vd.py`, `sv.py`, `estimators.py`) | 1-2 d | Estimators produce finite-shot samples matching small white-box checks. |
| 5 | A | Implement the certified crossing (`crossing.py`) and closed-form coefficients (`coefficients.py`) | 1-2 d | `delta_VD`, `delta_SV`, `c_SV`, `R0`, `eta` computable in closed form. |
| 6 | A | Move E1-E4 and E7 into `experiments/`; wire `run_all.py` for fast / full / level1 flows | 4-8 h | `make reproduce-level1` produces canonical Level 1 outputs. |
| 7 | A | Create minimal reference outputs and `tests/fixtures/` | 2-4 h | Reference CSV/JSON files exist and are small enough for Git. |
| 8 | A | Implement minimal `schemas.yaml`, `tolerances.yaml` (Level 1 tier), and `verify.py` | 1-2 d | `make verify` hard-fails on numerical/schema mismatch. |
| 9 | A | Add core tests: determinism, regression, `c_sv_zero`, `delta_generator`, `symmetry_compatible` | 1 d | Core tests pass inside Docker. |
| 10 | A | Add minimal pre-flight environment checks (incl. PAP-hash check) | 2-4 h | Bad env vars or dependency mismatches abort before compute. |
| 11 | A | Add minimal `manifest.json` with commit, PAP hash, level, dependency versions, output hashes | 3-5 h | Each run records provenance for generated outputs. |
| 12 | A | Write `README.md`, minimal `METHODS.md`, draft `CITATION.cff`, draft `.zenodo.json`, draft adjudication table | 4-8 h | Reviewer can run and understand the MVP reproduction path. |
| 13 | A | Run `make reproduce-level1` and `make verify` from a clean Docker build | 2-4 h | MVP Level 1 reproduction passes from a clean checkout. |
| 14 | A | Run `make reproduce-full` once for the submitted Level 1/2 numerical results | hardware-dependent, 0.5-2 d typical | Full recomputable outputs used by the manuscript are generated and verified. |
| 15 | B | Add Level 2 device-simulation experiments (E5, E6, E7, E12) with pinned Aer seed and Level 2 tolerance tier | 1-2 d | Level 2 outputs verify at the relaxed tier. |
| 16 | B | Implement the hardware analysis-from-counts path and archive structure | 1-2 d | `make analysis-from-hardware` reproduces estimators from archived counts. |
| 17 | B | Add checkpoint/resume behavior for long-running experiments | 1-2 d | Interrupted full run resumes from complete blocks. |
| 18 | B | Add structured logging to `results/run.log` (incl. level and job ids) | 4-6 h | Pre-flight checks, block hashes, failures, and runtimes are logged. |
| 19 | B | Harden `verify.py` and complete `test_verify.py` (incl. adjudication and Level 2 tier tests) | 1 d | Missing rows, columns, NaN/Inf, type errors, manifest, prediction-registry, and tier checks are tested. |
| 20 | B | Add `reference_manifest.json` and reference-data update workflow | 3-5 h | Reference data records tag, commit, PAP hash, timestamps, and hashes. |
| 21 | B | Add `make check-env` and `make determinism-check` (Level 1 scope) | 3-6 h | Three-run tolerance calibration can be performed mechanically. |
| 22 | B | Calibrate final tolerances from at least three fast runs, per level | 2-4 h | Tolerances document observed max difference and safety factor per tier. |
| 23 | B | Add remaining tests: observable bounds, density matrix, crossing certificate, clipped estimator, figures | 1-2 d | Full test suite passes inside Docker. |
| 24 | B | Add GitHub Actions with Docker, artifacts, and advisory `pip-audit` (Level 1 subset only) | 4-8 h | CI runs fast reproduction and uploads failure artifacts without a cloud account. |
| 25 | B | Write full `METHODS.md`, `CONTRIBUTING.md`, `LICENSE-DATA`, final `CITATION.cff`, final `.zenodo.json` | 1-2 d | Archival documentation is complete. |
| 26 | B | Add `.pre-commit-config.yaml` guardrails (incl. hardware-counts large-file guard) | 2-4 h | Formatting/linting and large-file checks are available. |
| 27 | B | Pin final Docker base image by digest and rerun `reproduce-full` | hardware-dependent, 0.5-2 d typical | Release image and full outputs are verified together. |
| 28 | B | Create GitHub release tag, connect Zenodo, insert version-specific DOI, recompile paper | 2-4 h plus Zenodo processing time | Manuscript cites the exact archived code/data release. |

Phase A should happen before or alongside final manuscript preparation. Phase B
can happen after the main numerical story is stable and before public archival
release.

## Immediate next step

Before adding more experiments, complete Phase A steps 1-6: build the clean
repository skeleton, create the simple Docker path, implement from scratch the Level 1
density-matrix simulator and the coefficient code, implement the VD/SV estimators
and the certified crossing, and make `reproduce-level1` generate the E1-E4 and E7
Level 1 outputs. Because the core acceptance argument for this paper is that the
experiments recover the theory's coefficients (`delta_VD`, `delta_SV`,
`c_SV = 0`) and the certified crossing, the Level 1 white-box path is the
reproducibility deliverable that carries the most weight and should be solid
first. Level 2 device-simulation and Level 3 hardware archives are added inside
the same reproducible structure during Phase B.
```
