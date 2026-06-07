# Current Reproducibility Status

Status: additive operational status note. Not a PAP freeze, not an adjudication,
and not a replacement for `REPRODUCIBILITY_PLAN.md`.

This document records the reproducibility state of the repository after the
Level 2 Step 2 checkpoint. The formal plans are frozen artifacts; this file is
the living runbook for what a reviewer or maintainer should run today.

## Scope At This Checkpoint

Last experimental checkpoint before this reproducibility cleanup:

- Commit: `9b6482f`
- Scope: Level 2 Step 2, noisy Aer sampling for unmitigated and
  readout-mitigated SV only.
- Explicitly not included yet: Level 2 VD Hadamard/quotient sampling, gate
  folding, Level 2 E5/E7/E12, and hardware.

The current cleanup is documentation/command organization only. It does not add
experiments, does not change frozen artifacts, and does not create a new freeze.

## Freeze Provenance

The repository has two registered freezes:

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

Interpret this only with `git status --short` clean. The verifier audits the
committed git state with the documented Windows EOL tolerance.

## Command Contract

### Level 1 Reference Verification

```bash
python reproducibility/verify.py --reference reproducibility/reference/
```

What it proves:

- The current Level 1 canonical outputs match the committed reference package
  within registered tolerances.
- The numerical white-box reproduction path is intact.

What it does not prove:

- It does not adjudicate v1/v2 again.
- It does not verify Level 2 outputs yet.
- It does not audit frozen-file drift; use `pap/verify_freeze.py` for that.

### Full Test Suite

```bash
python -m pytest tests/ -q
```

What it proves:

- Scientific invariants, regression checks, freeze-audit tests, secondary
  endpoint tests, and Level 2 Step 1/2 tests pass in the current environment.

Runtime note:

- The suite can take several minutes on Windows because Level 2 sampling tests
  invoke Aer.

### Level 2 Step 1 Foundation

```bash
pip install -e ".[level2]"
python -m level2.circuits
```

What it proves:

- The realistic-depth Qiskit circuit builds.
- The state remains inside the Hamming-weight sector.
- The Qiskit/Level 1 ordering cross-check is exercised.
- The synthetic Aer noise model loads.

It does not run noisy sampling.

### Level 2 Step 2 Sampling

```bash
pip install -e ".[level2]"
python -m level2.sampling
```

What it proves:

- The current additive Level 2 sampling layer regenerates
  `level2/level2_sampling_results.csv` and
  `level2/level2_sampling_report.md`.
- Readout mitigation is applied before SV postselection.
- The reported laws are checked in form, not as Level 1 coefficient recovery.

It does not implement VD, folding, Level 2 E5/E7/E12, or hardware.

## Artifact Map

| Area | Current artifacts | Status |
| --- | --- | --- |
| Freeze audit | `pap/verify_freeze.py`, `pap/FREEZE_STATUS.md` | active, additive |
| Level 1 reference | `reproducibility/reference/*` | official `verify.py` target |
| v1/v2 confirmatory outputs | `results/confirmatory_full/`, `results/confirmatory_v2/` | frozen results, not modified |
| Post-adjudication analysis | `analysis/ensemble_coverage_*`, `analysis/c_vd_se_sensitivity_*`, `analysis/e6_spectral_resolvability_*` | analysis only |
| Secondary endpoints | `results/secondary/e6/e8/e9/e10/e11/e12...` | descriptive, additive |
| Level 2 Step 1 | `level2/circuits.py`, `level2/noise_model.py`, `level2/level2_foundation_report.md` | additive Phase B |
| Level 2 Step 2 | `level2/sampling.py`, `level2/level2_sampling_*` | additive Phase B |

## Remaining Reproducibility Work Before A Final Release

1. Decide which additive secondary and Level 2 outputs appear in the manuscript.
2. For any included Level 2 numerical outputs, add an explicit relaxed-tolerance
   reference tier and manifest entries. Do not mix them silently into Level 1
   tight verification.
3. Run a clean Docker reproduction path and record the platform/runtime.
4. Regenerate figures from the final included numerical outputs.
5. Add CI for the Level 1 fast path and freeze audit.
6. If hardware is included, archive raw counts and calibration snapshots and
   verify only the analysis-from-counts path.
7. Prepare release metadata (`CITATION.cff`, Zenodo metadata, final tag, final
   reference manifest).

## Maintenance Guardrails

- Do not edit files listed in `freeze_manifest.json` or
  `freeze_manifest_v2.json` unless intentionally creating a documented new
  freeze. No such freeze is active now.
- Do not update reference data just because formatting, logging, or docs changed.
- Keep Level 2 as an additive robustness layer until `verify.py` has a documented
  relaxed-tolerance tier for it.
- Always run `python pap/verify_freeze.py` and confirm v2 zero drift before
  claiming the audit trail is clean.
