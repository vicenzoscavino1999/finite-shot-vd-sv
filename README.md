# Finite-Shot Operating Windows for VD/SV

Reproduction package for the numerical experiments accompanying the paper on
finite-shot operating windows for virtual distillation (VD) and symmetry
verification (SV).

This repository now contains the frozen Level 1 reproduction core, the v2 PAP
amendment audit trail, post-adjudication analysis layers, secondary descriptive
endpoints, and the first two additive Level 2 device-simulation steps.

For the current checkpoint, read:

- `REPRODUCIBILITY_STATUS.md` for the operational status and command map.
- `pap/FREEZE_STATUS.md` for the freeze provenance and real freeze audit.
- `EXPERIMENTAL_PLAN.md` and `REPRODUCIBILITY_PLAN.md` for the frozen formal
  plans. These files are hashed artifacts and are not edited to track day-to-day
  implementation status.

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

### Post-Adjudication And Secondary Layers

The repository also includes additive, non-freeze analysis and secondary
endpoints:

- Ensemble coverage and `c_VD` SE sensitivity under `analysis/`.
- E6, E8, E9, E10, E11, and E12 under `experiments/` with outputs under
  `results/secondary/`.
- These layers are reported descriptively unless their own report says
  otherwise. They are not a new PAP freeze or a new primary adjudication.

### Level 2 Additive Device-Simulation

Level 2 is in `level2/` and remains an additive Phase B robustness layer:

- Step 1: Qiskit/Aer foundation, noiseless reference, ordering check, and
  synthetic Aer noise model.
- Step 2: noisy Aer sampling for unmitigated and readout-mitigated SV, with
  postselection after readout mitigation.

Level 2 validates laws in form only. It is not a Level 1 coefficient-validation
claim, and it is not yet integrated into `reproducibility/verify.py` as an
official relaxed-tolerance reference tier.

## Quick Start

PowerShell pinned environment:

```powershell
$env:PYTHONHASHSEED=0
$env:OMP_NUM_THREADS=1
$env:MKL_NUM_THREADS=1
$env:OPENBLAS_NUM_THREADS=1
```

Install the current development environment, including Level 2 tests:

```bash
pip install -e ".[dev,figures,level2]"
```

For a minimal Level 1-only reproduction environment, Qiskit/Aer is not needed:

```bash
pip install -e .
```

Verify the frozen Level 1 reference outputs:

```bash
python reproducibility/verify.py --reference reproducibility/reference/
```

Run tests:

```bash
python -m pytest tests/ -q
```

Audit the freezes:

```bash
python pap/verify_freeze.py
```

Run Level 2 commands when the `[level2]` extra is installed:

```bash
pip install -e ".[level2]"
python -m level2.circuits
python -m level2.sampling
```

## Make Targets

- `make reproduce-level1`: regenerate Level 1 outputs and verify them.
- `make reproduce-fast`: run the fast Level 1 reproduction path and verify.
- `make reproduce-full`: current Level 1 full path; future Level 2 integration is
  still Phase B work.
- `make verify`: run `reproducibility/verify.py` against the reference outputs.
- `make verify-freeze`: run the real v1/v2 freeze audit.
- `make test`: run the test suite.
- `make level2-foundation`: run the Level 2 foundation smoke check.
- `make level2-sampling`: regenerate the current Level 2 Step 2 sampling report.

## Current Limits

- The official `verify.py` reference package currently verifies the Level 1
  canonical outputs.
- Level 2 Step 1/2 outputs are committed and tested, but not yet registered as a
  relaxed-tolerance reference tier.
- Level 2 folding, VD noisy quotient, and Level 2 E5/E7/E12 are not implemented.
- Level 3 hardware is not implemented; the reproduction contract remains
  analysis-from-archived-counts only if hardware data is ever added.
- Figures are regenerated from numerical data; exact PDF byte identity is not a
  reproducibility claim.

## Licenses

Code is MIT (`LICENSE`). Data and generated figures are CC-BY-4.0
(`LICENSE-DATA`).
