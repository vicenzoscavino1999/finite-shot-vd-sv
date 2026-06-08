# Current Reproducibility Status

Status: additive operational status note. Not a PAP freeze, not an adjudication,
and not a replacement for the frozen `REPRODUCIBILITY_PLAN.md`.

This document records the current runbook for the repository after the Level 2
device-simulation layer and the Level 3 IBM hardware archive layer. The formal
plans remain frozen artifacts; this file tracks what a reviewer or maintainer
should run today.

## Scope At This Checkpoint

Current checkpoint:

- Commit: use `git rev-parse HEAD` for the current checkout. This status file is
  an operational note, not a hash-registered release manifest.
- Level 1: frozen white-box coefficient-validation core.
- Level 2: additive Qiskit/Aer device-simulation robustness layer complete
  through high-power exact-rho, realistic n=6 VD, denominator concentration,
  crossing diagnostics, Efron--Stein window checks, and small-noise P10.
- Level 3: additive IBM hardware layer complete as archive-only analysis:
  Stage 2 precursor, full Stage 3 `g6_k2_c000`, and preliminary `g6_k2_c001`
  inter-instance robustness check.

No new PAP freeze is active. Level 2 and Level 3 are additive validation layers:
Level 2 validates laws in form under a gate-level model, and Level 3 validates
qualitative feasibility from archived hardware counts. Coefficient-level claims
remain Level 1 only.

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

### Prerequisites

Minimal Level 1 verification needs only the base package:

```bash
pip install -c requirements-ci-constraints.txt -e .
```

The current public test/reproduction environment includes development tools and
Level 2/Aer dependencies. It does not require an IBM account:

```bash
pip install -c requirements-ci-constraints.txt -e ".[dev,level2]"
```

Level 3 analysis from archives does not require an IBM account. Device
submission scripts require a saved global IBM account and are not part of the
public reproduction route.

### Level 1 Reference Verification

```bash
python reproducibility/run_all_current.py --mode fast --output results
python reproducibility/verify_current.py --reference reproducibility/reference/ --generated results
```

What it proves:

- The current Level 1 canonical outputs match the committed reference package
  within registered tolerances.
- The committed reference package SHA-256 manifest is intact.
- The numerical white-box coefficient-validation path is intact.

Use `--exact-numeric` only for same-platform determinism checks. Docker/Linux
may differ from the Windows-authored reference at the final ULP while remaining
within the registered tolerances.

What it does not prove:

- It does not adjudicate v1/v2 again.
- It does not verify Level 2 outputs as a relaxed-tolerance reference tier.
- It does not audit frozen-file drift; use `pap/verify_freeze.py` for that.

### Full Test Suite

```bash
python -m pytest tests/ -q
```

What it proves:

- Scientific invariants, regression checks, freeze-audit tests, secondary
  endpoint tests, Level 2 tests, and Level 3 archive-analysis tests pass in the
  current environment.

Runtime note:

- The suite can take several minutes on Windows because several tests exercise
  Qiskit/Aer and archive-analysis paths.

### Level 2 Device-Simulation Layer

The consolidated Level 2 summary is:

```bash
level2/LEVEL2_SUMMARY.md
```

Representative commands:

```bash
python -m level2.circuits
python -m level2.sampling
python -m level2.vd
python -m level2.highpower
python -m level2.vd_realistic_n6
python -m level2.crossing_denominator
python -m level2.window_efronstein
python -m level2.p10_smallnoise
```

What it proves:

- The finite-shot laws are visible in form under the synthetic Aer device model.
- Readout mitigation is applied before SV postselection.
- Realistic VD overhead is represented by an explicit Hadamard/SWAP
  interferometry circuit rather than by the optimistic state-noise-only contrast.

What it does not prove:

- It does not validate Level 1 analytic coefficients.
- It is not yet registered in `reproducibility/verify.py` as a relaxed-tolerance
  reference tier.

### Level 3 Hardware Archive Analysis

Re-run consolidated hardware analyses from committed archives:

```bash
python scripts/reanalyze_level3_archives.py
```

or:

```bash
make analysis-from-hardware
```

To verify without rewriting committed JSON summaries:

```bash
python scripts/verify_level3_archives.py
```

What it proves:

- The Stage 3 `g6_k2_c000` and `g6_k2_c001` analyses can be reproduced from raw
  archived hardware counts.
- The analysis path does not connect to IBM Runtime and does not submit QPU
  jobs.
- Cluster-bootstrap summaries are recomputed from calibration epochs.

What it does not prove:

- It does not reproduce the hardware experiment by re-executing QPU jobs.
- It does not validate analytic coefficients on hardware.

## Artifact Map

| Area | Current artifacts | Status |
| --- | --- | --- |
| Freeze audit | `pap/verify_freeze.py`, `pap/FREEZE_STATUS.md` | active, additive |
| Level 1 reference | `reproducibility/reference/*` | official Level 1 target; active verifier is `verify_current.py` |
| Level 1 reference package | `reproducibility/reference/*` | committed reference CSVs plus SHA-256 manifest |
| Post-adjudication analysis | `analysis/ensemble_coverage_*`, `analysis/c_vd_se_sensitivity_*`, `analysis/e6_spectral_resolvability_*` | analysis only |
| Secondary endpoints | `results/secondary/e6/e8/e9/e10/e11/e12...` | descriptive, additive |
| Level 2 reports/data | `level2/*_report.md`, `level2/*_results.csv`, `level2/LEVEL2_SUMMARY.md` | additive form-validation |
| Level 3 Stage 2 | `level3/level3_hardware_run_report.md`, `level3/archive/ibm_marrakesh_*.json.gz` | archive-only hardware precursor |
| Level 3 Stage 3 | `level3/level3_full_p7p9_report.md`, `level3/archive/stage3_g6_k2_c000_*.json.gz` | archive-only qualitative hardware P7/P9 |
| Level 3 robustness | `level3/level3_robustness_g6c001_report.md`, `level3/archive/stage3_g6_k2_c001_*.json.gz` | preliminary inter-instance check |

## Remaining Reproducibility Work Before A Final Release

1. Regenerate `requirements-lock.txt` inside the final Docker image and record
   the Docker platform/runtime.
2. Add a documented relaxed-tolerance reference tier if Level 2 outputs are to
   be verified by `reproducibility/verify.py`.
3. Decide whether Level 3 consolidated JSON outputs should also get a separate
   DOI-time checksum manifest.
4. Regenerate final manuscript figures from the final included numerical
   outputs.
5. Add CI for the Level 1 fast path and freeze audit.
6. Prepare final release metadata: final tag, Zenodo DOI, and any public raw
   hardware-count archive outside git if file size policy requires it.

## Maintenance Guardrails

- Do not edit files listed in `freeze_manifest.json` or
  `freeze_manifest_v2.json` unless intentionally creating a documented new
  freeze. No such freeze is active now.
- Do not update Level 1 reference data just because formatting, logging, or
  docs changed.
- Keep Level 2 as a relaxed, form-validation layer unless it is explicitly
  registered with its own tolerance tier.
- Keep Level 3 as analysis-from-archived-counts only. Public reproduction must
  never require re-running QPU jobs.
- Always run `python pap/verify_freeze.py` and confirm v2 zero drift before
  claiming the audit trail is clean.
