# Finite-Shot Operating Windows for Virtual Distillation and Symmetry Verification

Code and data for the paper *Finite-Shot Operating Windows for Virtual Distillation and
Symmetry Verification* (V. Scavino Alfaro, arXiv:2606.15464). Each release is archived at
Zenodo; DOI [10.5281/zenodo.20670995](https://doi.org/10.5281/zenodo.20670995) resolves to
the latest version, and the paper cites the version it used.

The paper compares virtual distillation (VD) and symmetry verification (SV) at a finite
shot budget and tests its predictions at three levels:

| Level | What it is | What it supports in the paper | How it is reproduced |
| --- | --- | --- | --- |
| 1 | Exact density-matrix simulation of ten QAOA instances (NumPy/SciPy only) | the coefficient checks, the Level 1 tables and figures | regenerated and compared number by number with archived outputs |
| 2 | Gate-level Qiskit/Aer simulation with a synthetic noise model | the form of the laws under device conditions, the Level 2 table and figures | committed outputs; each step can be rerun with `python -m level2.<module>` |
| 3 | Archived counts from IBM hardware (`ibm_marrakesh`, `ibm_kingston`) | the hardware ordering and denominator scale, the hardware table | re-analysed from the archived counts; no IBM account is needed |

## Reproduce everything with one command

With Docker installed, from the repository root:

```bash
docker build --platform linux/amd64 -t finite-shot-vd-sv:repro .
docker run --rm --platform linux/amd64 finite-shot-vd-sv:repro bash -lc "make reproduce-all"
```

This regenerates Level 1 and checks it against the reference outputs, runs the tests,
checks that the frozen analysis plan is unchanged, re-analyses the Level 3 hardware
archives, and regenerates the figures. It takes about 25 to 35 minutes on a laptop and
ends with

```text
REPRODUCE_ALL_PASS: Level 1 exact, tests, PAP freeze, Level 3 archived-count verification, and figures completed
```

[REPRODUCING.md](REPRODUCING.md) gives each step separately, a local install without Docker,
how to regenerate the exact Level 1 run reported in the paper, and what to expect on
Windows and macOS.

## Where each result comes from

| Paper item | Code | Data |
| --- | --- | --- |
| Level 1 primary checks (P1 to P9) and their figures | `experiments/e1_*.py` to `experiments/e7_certified_crossing.py`, `analysis/adjudicate_level1.py` | `results/confirmatory_v2/` (v2 run, reported in the paper), `results/confirmatory_full/` (v1 run) |
| Calibration of the P1 all-instance rule | `analysis/ensemble_coverage_analysis.py` | `analysis/ensemble_coverage_report.md` |
| Secondary checks E6 and E8 to E12 | `experiments/e6_*.py`, `experiments/e8_*.py` to `experiments/e12_*.py` | `results/secondary/` |
| Resource and observable conventions for E7 | `experiments/e7_resource_observable_sensitivity.py` | `results/e7_resource_observable_sensitivity.csv` |
| Clipping-threshold and depolarizing-channel checks | `experiments/clipping_threshold_sensitivity.py`, `experiments/channel_sensitivity_delta.py` | `results/secondary/` |
| Level 2 table and figures | `level2/*.py` | `level2/*_results.csv`; overview in `level2/LEVEL2_SUMMARY.md` |
| Hardware table | `level3/analyze_full.py`, `scripts/verify_level3_archives.py` | `level3/archive/` |
| Certified VD-SV crossing in the sector toy (appendix) | `scripts/sector_toy_certified_crossing.py` | computed exactly; no data files |
| Manuscript figures | `scripts/generate_manuscript_figures.py` (`make figures-manuscript`) | `figures/` |

## Repository layout

| Directory | Contents |
| --- | --- |
| `src/vd_sv/` | the library: density matrices, QAOA instances, noise channels, VD and SV samplers, closed-form coefficients, the comparison rule |
| `experiments/` | the Level 1 experiments E1 to E12 and the robustness checks |
| `analysis/` | adjudication of the Level 1 checks and the P1 calibration |
| `level2/`, `level3/` | the device-simulation and hardware layers |
| `reproducibility/` | the drivers `run_all_current.py` and `verify_current.py`, configuration, and the Level 1 reference outputs |
| `pap/` | the analysis-plan freeze: hashing, audit, amendment |
| `results/`, `figures/` | committed outputs |
| `tests/` | the test suite |

## The analysis plan and its freeze

The analysis plan (`EXPERIMENTAL_PLAN.md`, `REPRODUCIBILITY_PLAN.md`, `METHODS.md`) was
written before the confirmatory runs and frozen by SHA-256 hash. It has two versions:

- **v1**, the original plan (`freeze_manifest.json`, `PAP_HASH.txt`);
- **v2**, its single amendment, which added a negative control to prediction P1
  (`freeze_manifest_v2.json`, `PAP_HASH_v2.txt`,
  `pap/amendment_v2_p1_control_negative.md`).

The v1 and v2 runs use the same code and differ only in their random seeds
(`reproducibility/config/rng_policy.yaml` and `rng_policy_v2.yaml`). The paper reports the
v2 run and quotes the v1 run where they differ.

To check that no frozen file has changed:

```bash
python pap/verify_freeze.py
```

It should report v2 `INTACT_ZERO_DRIFT` and v1 `INTACT_WITH_EXPECTED_DRIFT`; the two
expected differences are line endings in a Windows checkout. Details are in
[pap/FREEZE_STATUS.md](pap/FREEZE_STATUS.md).

The frozen files include the original drivers `reproducibility/run_all.py`,
`run_all_v2.py` and `verify.py`. They are kept unchanged so that the freeze can be
audited; use `run_all_current.py` and `verify_current.py` to reproduce.

## Make targets

| Target | What it does |
| --- | --- |
| `make reproduce-all` | the full check described above |
| `make check-ci` | three identical Level 1 runs, tests, reference integrity and Level 3 verification |
| `make reproduce-level1` | regenerate Level 1 and compare it exactly with the reference |
| `make verify-reference` | check the committed Level 1 reference outputs against their checksums |
| `make verify-freeze` | check the analysis-plan freeze |
| `make verify-level3` | re-analyse the hardware archives and compare with the committed summaries |
| `make test` | run the tests |
| `make figures-manuscript` | regenerate the manuscript figures |
| `make audit` | check the locked dependencies for known vulnerabilities |
| `make analysis-from-hardware-update` | rewrite the committed Level 3 summaries (maintainers only) |
| `make reference-manifest`, `make level3-manifest` | rewrite reference or archive checksums (maintainers only) |

## Citation and licenses

Please cite the paper; citation metadata are in [CITATION.cff](CITATION.cff). Code is under
the MIT license (`LICENSE`); data and figures are under CC-BY-4.0 (`LICENSE-DATA`).
Reproduction problems can be reported as issues; see [CONTRIBUTING.md](CONTRIBUTING.md).
