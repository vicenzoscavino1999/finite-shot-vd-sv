# Reproducing the results

This guide gives every reproduction step with its expected output. The one-command
version is in the [README](README.md).

## 1. Choose an environment

**Docker (reference environment).** The Linux/amd64 image defined by `Dockerfile` pins
the base image by digest and installs the hash-locked `requirements.lock`. The Level 1
reference outputs were generated in this image, so it is the only environment in which
Level 1 is expected to match them digit for digit.

```bash
docker build --platform linux/amd64 -t finite-shot-vd-sv:repro .
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro bash -lc "make reproduce-all"
```

Run any single step below inside the container by replacing `make reproduce-all` with
the command of that step.

**Local install (Linux, macOS or Windows; Python 3.11 or later, 3.12 recommended).**

```bash
python -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
```

The lock includes Qiskit and Qiskit Aer for Level 2. Before running anything, fix the
threading and hashing environment so that results do not depend on the machine load:

```bash
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
```

```powershell
$env:PYTHONHASHSEED=0; $env:OMP_NUM_THREADS=1; $env:MKL_NUM_THREADS=1; $env:OPENBLAS_NUM_THREADS=1
```

Outside Docker, linear-algebra libraries can differ in the last digits. Level 1 is then
checked with the tolerances registered in `reproducibility/config/tolerances.yaml`
(drop `--exact-numeric` from the commands below); differences of order 1e-14 relative
are expected and accepted.

## 2. Level 1: exact white-box simulation

**Check the committed reference outputs (a few seconds).**

```bash
python reproducibility/verify_current.py --reference reproducibility/reference \
  --generated reproducibility/reference --exact-numeric
```

Expected:

```text
VERIFY PASS: 18260 numeric comparisons within tolerance across 7 files; reference checksums OK
```

**Regenerate the v1 run and compare it with the reference (about 5 minutes).** The
reference outputs are the v1 run, archived in `results/confirmatory_full/`.

```bash
python reproducibility/run_all_current.py --mode full --level 1 --output rerun_v1
python reproducibility/verify_current.py --reference reproducibility/reference \
  --generated rerun_v1 --exact-numeric
```

The expected line is the same `VERIFY PASS` as above.

**Regenerate the v2 run reported in the paper (about 5 minutes).** The v2 run differs
from v1 only in its random seeds.

```bash
python reproducibility/run_all_current.py --mode full --level 1 \
  --rng-policy reproducibility/config/rng_policy_v2.yaml --output rerun_v2
python reproducibility/verify_current.py --reference results/confirmatory_v2 \
  --generated rerun_v2 --skip-reference-checksums
```

`results/confirmatory_v2/` has no checksum file, hence `--skip-reference-checksums`; the
numerical comparison is the same and ends with `VERIFY PASS`.

**Adjudicate the primary checks.** `analysis/adjudicate_level1.py --results <dir>
--output <file> --version v2` rebuilds the table of primary checks from a results
directory; the committed tables are `analysis/adjudication_table.csv` (v1) and
`analysis/adjudication_table_v2.csv` (v2).

**Secondary checks and robustness.** Each of these scripts rewrites its CSV and report in
`results/secondary/`; `git diff --stat results/secondary` then shows whether anything
changed.

```bash
python -m experiments.e6_copy_log_scale
python -m experiments.e8_window_location
python -m experiments.e9_selection_trichotomy
python -m experiments.e10_implementation_noise
python -m experiments.e11_lecam_efficiency
python -m experiments.e12_efron_stein_operational
python -m experiments.clipping_threshold_sensitivity
python -m experiments.channel_sensitivity_delta
```

## 3. The analysis-plan freeze

```bash
python pap/verify_freeze.py
```

Expected verdicts: v2 `INTACT_ZERO_DRIFT` and v1 `INTACT_WITH_EXPECTED_DRIFT` (two files
whose line endings differ in a Windows checkout). Read the result with a clean
`git status`; see [pap/FREEZE_STATUS.md](pap/FREEZE_STATUS.md).

## 4. Level 3: hardware archives (about 1 to 2 minutes)

```bash
python scripts/verify_level3_archives.py
```

This checks the checksums of the archived counts and re-analyses them in memory,
without contacting IBM. Expected final line:

```text
LEVEL3_VERIFY_ALL_PASS cases=5
```

## 5. Tests (about 5 minutes)

```bash
python -m pytest tests/
```

`tests/test_freeze_integrity.py` needs the git history and is skipped in the container
(`make test-ci`).

## 6. Figures

```bash
python scripts/generate_manuscript_figures.py
```

The figures are written to `figures/` from `results/confirmatory_v2/`, the Level 2 CSVs
and `level3/archive/`. The PDF files can differ byte for byte between runs because of
embedded metadata; the plotted data do not.

## 7. Level 2: device simulation (optional)

The committed CSVs and reports in `level2/` are the outputs used in the paper. Each step
can be rerun; `level2/LEVEL2_SUMMARY.md` lists which script produces which file.

```bash
python -m level2.highpower
python -m level2.vd_realistic_n6
python -m level2.crossing_denominator
python -m level2.window_efronstein
python -m level2.p10_smallnoise
```

These are seeded but not part of the digit-level comparison: Aer results can change with
the Aer version and platform, so the check is that the conclusions in the summary hold.

## 8. Sector-toy certificate (appendix, about 2 seconds)

```bash
python scripts/sector_toy_certified_crossing.py
```

It recomputes the remainder bounds and the certified interval, checks them against the
exact binomial sums, and ends with `SECTOR_TOY_CERTIFICATE_PASS`.

## Reporting a problem

Please open an issue with the Docker image digest or your Python, NumPy and SciPy
versions, the Git tag, the command you ran, and its output (for Level 1, also the
`manifest.json` written to the output directory).
