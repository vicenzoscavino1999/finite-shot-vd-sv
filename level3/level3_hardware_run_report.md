# Level 3 Stage 2 Hardware Feasibility Run

Status: real IBM hardware precursor run complete. This is a Level 3 feasibility and
pipeline validation result, not a coefficient-validation result.

## Scope And Framing

This 10-minute precursor run checks that the Stage 1 pipeline works on real IBM
hardware and that readout-calibrated SV reduces bias relative to the unmitigated
Z-basis estimator for the frozen instance `g6_k2_c000`.

It is not the full Level 3 endpoint. Level 3 remains a form and robustness check
with calibrated readout on hardware, not a validation of analytic coefficients.
The qualitative P7/P9 hardware evidence for denominator concentration and
crossing behavior is deferred to the later 180-minute run with VD and a resource
sweep.

All circuits were submitted in a single SamplerV2 job, so there is one
calibration epoch. Confidence intervals from this run are within-epoch only; no
cluster bootstrap across calibration epochs is available here.

## Prerequisites

- Credential source: global saved IBM account read by `QiskitRuntimeService()`.
- No token, CRN, or credential file is stored in this repository.
- Primary backend: `ibm_marrakesh`.
- Fallbacks checked but not used: `ibm_kingston`, `ibm_fez`.
- Backend status before submission: `operational=True`, `pending_jobs=0`,
  `status_msg=active`.

## Dry-Run Before Submission

Command:

```text
python -m level3.submit --real-backend-dry-run --optimization-level 3 --initial-layout 145,137,149,146,148,147 --print-json
```

Output summary:

```text
REAL_BACKEND_DRY_RUN backend=ibm_marrakesh operational=true pending_jobs=0 status_msg=active
BUDGET_ESTIMATE circuits=3 shots_per_circuit=4096 total_shots=12288 max_total_shots=12288 near_cap=true max_circuit_depth=456 estimated_qpu_seconds=5.60333
DRY_RUN no submission; use --submit --confirm-submit --confirm-near-cap for QPU
```

Transpilation summary for the QAOA circuit:

| field | value |
|---|---:|
| optimization level | 3 |
| seed transpiler | 20260607 |
| depth | 456 |
| size | 768 |
| cz | 168 |
| sx | 367 |
| rz | 217 |
| x | 10 |
| measure | 6 |

The selected initial physical layout was `[145, 137, 149, 146, 148, 147]`.
The final logical-to-physical measurement layout archived for analysis was:

| logical | physical |
|---:|---:|
| 0 | 137 |
| 1 | 149 |
| 2 | 145 |
| 3 | 146 |
| 4 | 148 |
| 5 | 147 |

Selected initial-layout readout error snapshot:

| physical qubit | readout error |
|---:|---:|
| 137 | 0.013427734375 |
| 145 | 0.0205078125 |
| 146 | 0.00634765625 |
| 147 | 0.0040283203125 |
| 148 | 0.007568359375 |
| 149 | 0.0130615234375 |

Selected connected two-qubit links:

| edge | cz error |
|---|---:|
| 145-146 | 0.0015274301916806399 |
| 137-147 | 0.0022365073344978725 |
| 149-148 | 0.0012593528504693807 |
| 146-147 | 0.0021261119497241465 |
| 148-147 | 0.0014002924238532277 |

## Submission

Command:

```text
python -m level3.submit --submit --confirm-submit --confirm-near-cap --optimization-level 3 --initial-layout 145,137,149,146,148,147 --print-json
```

Result:

| field | value |
|---|---|
| backend | `ibm_marrakesh` |
| job id | `d8ip5t5v8cos73f5sn70` |
| job status | `DONE` |
| created at UTC | `2026-06-07T15:49:20.645914Z` |
| circuits in job | 3 |
| shots per circuit | 4096 |
| total shots | 12288 |
| Sampler | `SamplerV2` |

Archived counts:

```text
level3/archive/ibm_marrakesh_g6_k2_c000_20260607T154920Z_d8ip5t5v8cos73f5sn70.json.gz
```

Analysis JSON:

```text
level3/archive/ibm_marrakesh_g6_k2_c000_20260607T154920Z_d8ip5t5v8cos73f5sn70_analysis.json
```

## Analysis From Archived Counts Only

Command:

```text
python -m level3.analyze level3/archive/ibm_marrakesh_g6_k2_c000_20260607T154920Z_d8ip5t5v8cos73f5sn70.json.gz --json-out level3/archive/ibm_marrakesh_g6_k2_c000_20260607T154920Z_d8ip5t5v8cos73f5sn70_analysis.json
```

Output:

```text
archive=level3\archive\ibm_marrakesh_g6_k2_c000_20260607T154920Z_d8ip5t5v8cos73f5sn70.json.gz
backend=ibm_marrakesh
job_id=d8ip5t5v8cos73f5sn70
instance=g6_k2_c000
mu_ideal_noiseless_l2=-0.243431939047
unmitigated=0.0150525005063
sv_readout_mitigated_weight_postselect=-0.143323560525
abs_bias_unmitigated=0.258484439553
abs_bias_sv_readout_mitigated_weight_postselect=0.100108378522
sv_reduces_abs_bias_vs_unmitigated=YES
```

Estimator summary:

| method | estimate | bias vs mu_ideal | absolute bias |
|---|---:|---:|---:|
| unmitigated | 0.0150525005063 | 0.258484439553 | 0.258484439553 |
| SV readout-mitigated, weight-2 postselect | -0.143323560525 | 0.100108378522 | 0.100108378522 |

The readout-mitigated SV estimator reduces absolute bias relative to the
unmitigated estimator in this real-hardware precursor run.

Additional archived analysis values:

| field | value |
|---|---:|
| qaoa shots | 4096 |
| calibration shots per prepared state | 4096 |
| SV acceptance after readout mitigation | 0.5001136115704663 |
| negative mass before clip | -0.0 |

## Interpretation

This run validates the real-device submission, archive, and archive-only
analysis path for `g6_k2_c000`. The central feasibility observation is that SV,
using the readout matrix measured in the same job and postselection on weight
`k=2`, reduces the observed bias against the noiseless Level 2 reference.

This should be reported as a hardware feasibility precursor. It should not be
described as closing Level 3, validating finite-shot coefficients, or testing
P7/P9 crossings. Those claims require the later VD and resource-sweep hardware
run.

