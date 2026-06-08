# Level 3 Independent Backend Replicate: g6_k2_c000 on ibm_kingston

Status: fixed-epoch independent backend replicate complete for `g6_k2_c000`
on `ibm_kingston`.

This is an additive Stage 3 hardware robustness check. The claim is qualitative
only: independent backend replicate, calibrated-readout form/robustness, not
hardware validation of coefficients.

## Scope And Stop Rule

The pre-registered rule for this replicate was fixed before submission:

```text
backend: ibm_kingston, falling back to ibm_fez only if Kingston was unavailable
instance: g6_k2_c000
epochs: 14 fixed
stop rule: stop by epoch count or QPU cap, never by inspecting results
```

Each epoch is one SamplerV2 job containing readout calibration, the shared Z
measurement circuit, VD M=2 numerator, and VD M=2 denominator at 8192 shots per
circuit. The B sweep is obtained by deterministic prefix subsampling from the
archived bitstrings. Epochs are the bootstrap clusters because shots within an
epoch share calibration and device state.

Reference:

```text
mu_ideal_noiseless_l2 = -0.243431939046919
```

## Prerequisites

Credential source: global saved IBM account loaded by `QiskitRuntimeService()`.
No token, CRN, or credential file is stored in this repository.

Read-only backend check before submission:

```text
ibm_kingston: operational=True pending_jobs=0 status_msg=active
ibm_fez: operational=True pending_jobs=0 status_msg=active
ibm_marrakesh: operational=True pending_jobs=0 status_msg=active
```

Backend used: `ibm_kingston`.

Backend calibration timestamp:

```text
properties_last_update_date = 2026-06-07 18:04:15-05:00
calibration_id = None
```

## Dry-Run Before Submission

Command:

```text
python -m level3.stage3 --instance-id g6_k2_c000 --backend ibm_kingston --seed-transpiler 20260612 --real-backend-dry-run
```

Output summary:

```text
STAGE3_REAL_BACKEND_DRY_RUN backend=ibm_kingston operational=true pending_jobs=0 status_msg=active
BUDGET_ESTIMATE circuits=5 shots_per_circuit=8192 total_shots=40960 max_total_shots=40960 near_cap=true max_circuit_depth=856 estimated_qpu_seconds=35.0618
```

Transpiled circuit summary:

| label | depth | size | cz | sx | rz | x | measure |
|---|---:|---:|---:|---:|---:|---:|---:|
| readout_calib_0 | 1 | 13 | 0 | 0 | 0 | 0 | 13 |
| qaoa_z | 494 | 926 | 219 | 456 | 231 | 14 | 6 |
| vd_m2_numerator | 856 | 2700 | 647 | 1362 | 638 | 40 | 13 |
| vd_m2_denominator | 765 | 2198 | 494 | 1055 | 598 | 38 | 13 |
| readout_calib_1 | 2 | 26 | 0 | 0 | 0 | 13 | 13 |

The VD circuit is substantially deeper than the direct Z circuit, as expected
for Hadamard/SWAP and controlled-SWAP overhead on the device topology.

Calibration physical qubits:

```text
[72, 89, 75, 73, 91, 93, 71, 98, 59, 74, 90, 79, 92]
```

Shared Z logical-to-physical layout:

| logical | physical |
|---:|---:|
| 0 | 72 |
| 1 | 93 |
| 2 | 92 |
| 3 | 74 |
| 4 | 79 |
| 5 | 73 |

## Submission Summary

The primary analysis uses the first 14 unique jobs sorted by IBM job creation
timestamp, matching the fixed stop rule. These 14 epochs consumed 182 QPU
seconds.

An operational timeout left a submission process continuing in the background,
which produced 5 additional unique Kingston jobs. Those jobs are archived for
provenance but excluded from the primary fixed-epoch analysis. The exclusion is
deterministic and result-blind: first 14 unique jobs by IBM creation timestamp.

| quantity | value |
|---|---:|
| primary fixed epochs | 14 |
| excluded later unique jobs | 5 |
| shots per circuit per epoch | 8192 |
| circuits per epoch | 5 |
| total shots per epoch | 40960 |
| fixed-primary QPU seconds | 182 |
| all submitted replicate QPU seconds | 247 |
| IBM current-period usage after run | 595 / 10800 seconds |

Primary job ids:

```text
d8ivn5tv8cos73f64skg,d8j04uu6983c73dsm7n0,d8j056he8nrc73bisho0,d8j05c9e8nrc73bishv0,d8j05ic2upec739mq700,d8j05odv8cos73f65eo0,d8j05um6983c73dsm93g,d8j064k2upec739mq84g,d8j06dtv8cos73f65flg,d8j06fm6983c73dsm9qg,d8j06is2upec739mq8n0,d8j06mc2upec739mq8tg,d8j06pu6983c73dsmacg,d8j06ue6983c73dsmaig
```

Later jobs excluded from primary fixed analysis:

```text
d8j071k2upec739mq9j0,d8j074s2upec739mq9p0,d8j077s2upec739mq9u0,d8j07au6983c73dsmb30,d8j07e42upec739mqa6g
```

The consolidated archive-only primary analysis is:

```text
level3/archive/stage3_g6_k2_c000_ibm_kingston_fixed14_analysis.json
```

## Archive-Only Analysis

Command:

```text
python scripts/reanalyze_level3_archives.py --instance g6_k2_c000_kingston_fixed14 --bootstrap-reps 2000
```

The analysis reads only archived bitstrings/counts. It does not connect to IBM
Runtime or query the device.

Bootstrap: cluster bootstrap over 14 epochs, 2000 replicates, seed 33033.

### B Sweep

| method | B | estimate | bias | epoch variance | MSE | MSE CI 95% |
|---|---:|---:|---:|---:|---:|---|
| SV readout-mitigated | 512 | -0.138718 | 0.104714 | 0.000202222 | 0.0111528 | [0.00963198, 0.0125462] |
| SV readout-mitigated | 1024 | -0.141412 | 0.102020 | 0.000119994 | 0.0105194 | [0.00941201, 0.0115517] |
| SV readout-mitigated | 2048 | -0.142100 | 0.101332 | 0.0000279559 | 0.0102942 | [0.00978545, 0.0108570] |
| SV readout-mitigated | 4096 | -0.142864 | 0.100568 | 0.0000189560 | 0.0101315 | [0.00968885, 0.0105935] |
| SV readout-mitigated | 8192 | -0.142091 | 0.101341 | 0.00000888089 | 0.0102782 | [0.00997821, 0.0105625] |
| unmitigated | 512 | -0.0381457 | 0.205286 | 0.000274236 | 0.0423971 | [0.0389993, 0.0453655] |
| unmitigated | 1024 | -0.0393389 | 0.204093 | 0.000127817 | 0.0417727 | [0.0394946, 0.0438268] |
| unmitigated | 2048 | -0.0397480 | 0.203684 | 0.0000629887 | 0.0415456 | [0.0400218, 0.0432602] |
| unmitigated | 4096 | -0.0408801 | 0.202552 | 0.0000300388 | 0.0410552 | [0.0399544, 0.0421952] |
| unmitigated | 8192 | -0.0397567 | 0.203675 | 0.0000203848 | 0.0415025 | [0.0405940, 0.0424161] |
| VD M=2 readout-mitigated | 512 | 0.0129686 | 0.256401 | 0.0273190 | 0.0911089 | [0.0483776, 0.140935] |
| VD M=2 readout-mitigated | 1024 | -0.0312391 | 0.212193 | 0.0116091 | 0.0558057 | [0.0335206, 0.0801309] |
| VD M=2 readout-mitigated | 2048 | -0.0200759 | 0.223356 | 0.00287123 | 0.0525541 | [0.0410442, 0.0644515] |
| VD M=2 readout-mitigated | 4096 | -0.0148500 | 0.228582 | 0.00155056 | 0.0536895 | [0.0449105, 0.0632727] |
| VD M=2 readout-mitigated | 8192 | -0.0234425 | 0.219989 | 0.000588195 | 0.0489415 | [0.0434465, 0.0541270] |

At the largest B, the MSE ordering is:

```text
SV readout-mitigated: 0.0102782
unmitigated:          0.0415025
VD M=2:               0.0489415
```

This repeats the qualitative ordering observed on `ibm_marrakesh`.

## Denominator Behavior

| B | mean VD denominator | B / B_den estimate |
|---:|---:|---:|
| 512 | 0.119610 | 0.120115 |
| 1024 | 0.115813 | 0.240230 |
| 2048 | 0.119730 | 0.480459 |
| 4096 | 0.118213 | 0.960918 |
| 8192 | 0.117396 | 1.92184 |

The denominator remains small. Unlike the Marrakesh primary run, the largest-B
point is above the rough denominator concentration scale, but VD still remains
worse than both SV and unmitigated because the quotient is biased and carries
large epoch variance. This is consistent with the same qualitative hardware
story: realistic VD overhead does not produce a practical advantage in this
budget window.

## Backend Replicate Interpretation

Marrakesh primary `g6_k2_c000`, B=8192:

```text
SV readout-mitigated: 0.0102628
unmitigated:          0.0450005
VD M=2:               0.0741406
order: SV < unmitigated < VD
```

Kingston independent replicate `g6_k2_c000`, B=8192:

```text
SV readout-mitigated: 0.0102782
unmitigated:          0.0415025
VD M=2:               0.0489415
order: SV < unmitigated < VD
```

The same qualitative ordering appears on a second backend, so the Level 3
hardware conclusion is not a single-backend snapshot artifact. This remains a
qualitative feasibility and robustness result only. It should not be presented
as coefficient validation or as a hardware determination of constants.
