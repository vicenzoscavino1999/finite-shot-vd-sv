# Level 3 Robustness Check: g6_k2_c001

Status: inter-instance robustness check complete for `g6_k2_c001` on
`ibm_marrakesh`.

This is an additive Stage 3 hardware check, not a new coefficient claim. The
purpose is to test whether the qualitative SV dominance seen in `g6_k2_c000`
persists on a second frozen n=6 instance under the same calibrated-readout
pipeline. The initial four-epoch check was preliminary; this report now uses 16
calibration epochs and should be treated as the solid second n=6 hardware
instance.

## Scope And Framing

Level 3 remains a qualitative feasibility and form/robustness result with
calibrated readout. It is not a hardware validation of Level 1 coefficients.

Each epoch is one SamplerV2 job containing readout calibration, the shared Z
measurement circuit, VD M=2 numerator, and VD M=2 denominator. Epochs are the
bootstrap clusters because shots within one epoch share calibration and device
state.

The reference used for this instance is the Level 2 noiseless value for
`g6_k2_c001`:

```text
mu_ideal_noiseless_l2 = -0.18754608870531345
```

## Submission Summary

The first four epochs were the preliminary inter-instance check. Twelve
additional epochs were then run with seed `20260610`, bringing the archive to 16
epochs. The extension consumed 168 QPU seconds in the current IBM usage period.
The full 16-epoch archive has 224 archived QPU seconds because it includes the
earlier four epochs.

| quantity | value |
|---|---:|
| instance | `g6_k2_c001` |
| backend | `ibm_marrakesh` |
| epochs | 16 |
| shots per circuit per epoch | 8192 |
| circuits per epoch | 5 |
| total shots per epoch | 40960 |
| archived QPU seconds | 224 |
| new QPU seconds in this extension | 168 |

Additional dry-run summary for the 12-epoch extension:

```text
STAGE3_REAL_BACKEND_DRY_RUN backend=ibm_marrakesh operational=true pending_jobs=0 status_msg=active
BUDGET_ESTIMATE circuits=5 shots_per_circuit=8192 total_shots=40960 max_total_shots=40960 near_cap=true max_circuit_depth=1069 estimated_qpu_seconds=43.7862
```

Transpiled circuit depths in the extension:

| label | depth | cz | sx | rz | x | measure |
|---|---:|---:|---:|---:|---:|---:|
| readout_calib_0 | 1 | 0 | 0 | 0 | 0 | 14 |
| qaoa_z | 496 | 225 | 488 | 271 | 6 | 6 |
| vd_m2_numerator | 1069 | 646 | 1351 | 636 | 39 | 13 |
| vd_m2_denominator | 683 | 495 | 1049 | 578 | 32 | 13 |
| readout_calib_1 | 2 | 0 | 0 | 0 | 14 | 14 |

Shared Z logical-to-physical layout in the extension:

| logical | physical |
|---:|---:|
| 0 | 112 |
| 1 | 98 |
| 2 | 89 |
| 3 | 111 |
| 4 | 91 |
| 5 | 90 |

Job ids:

```text
d8ir1ilv8cos73f5uqkg,d8ir245v8cos73f5ur7g,d8ir29c2upec739mjcd0,d8ir2f42upec739mjcj0,d8iud05v8cos73f63c70,d8iud5dv8cos73f63ccg,d8iudak2upec739mo4b0,d8iudfu6983c73dska80,d8iudl66983c73dskafg,d8iudqdv8cos73f63d40,d8iudvtv8cos73f63dag,d8iue5c2upec739mo590,d8iuealv8cos73f63dmg,d8iueg66983c73dskbbg,d8iueldv8cos73f63e4g,d8iueqhe8nrc73biqkc0
```

## Archive-Only Analysis

Command:

```text
python -m level3.analyze_full level3/archive/stage3_g6_k2_c001_ibm_marrakesh_epoch*.json.gz --json-out level3/archive/stage3_g6_k2_c001_ibm_marrakesh_full_analysis.json --bootstrap-reps 2000
```

The analysis reads only archived bitstrings/counts. It does not connect to IBM
Runtime or query the device.

Bootstrap: cluster bootstrap over epochs, 2000 replicates, seed 33033.

### B Sweep

| method | B | estimate | bias | epoch variance | MSE | MSE CI 95% |
|---|---:|---:|---:|---:|---:|---|
| SV readout-mitigated | 512 | -0.163848 | 0.0236984 | 0.000804403 | 0.00131574 | [0.000465326, 0.00232005] |
| SV readout-mitigated | 1024 | -0.167812 | 0.0197345 | 0.000432311 | 0.000794743 | [0.000286991, 0.00140969] |
| SV readout-mitigated | 2048 | -0.170971 | 0.0165756 | 0.000360596 | 0.000612808 | [0.000199023, 0.00111350] |
| SV readout-mitigated | 4096 | -0.172206 | 0.0153405 | 0.000377508 | 0.000589245 | [0.000171609, 0.00110140] |
| SV readout-mitigated | 8192 | -0.171576 | 0.0159703 | 0.000313685 | 0.000549129 | [0.000169504, 0.000966160] |
| unmitigated | 512 | -0.0603989 | 0.127147 | 0.000900673 | 0.0170108 | [0.0133008, 0.0206896] |
| unmitigated | 1024 | -0.0639999 | 0.123546 | 0.000643561 | 0.0158670 | [0.0128590, 0.0191911] |
| unmitigated | 2048 | -0.0673438 | 0.120202 | 0.000493017 | 0.0149108 | [0.0123802, 0.0177780] |
| unmitigated | 4096 | -0.0676741 | 0.119872 | 0.000558041 | 0.0148925 | [0.0121774, 0.0180406] |
| unmitigated | 8192 | -0.0666705 | 0.120876 | 0.000507468 | 0.0150867 | [0.0125563, 0.0182737] |
| VD M=2 readout-mitigated | 512 | 0.222066 | 0.409612 | 0.301801 | 0.450721 | [0.129096, 0.888577] |
| VD M=2 readout-mitigated | 1024 | 0.129495 | 0.317041 | 0.0818348 | 0.177235 | [0.108468, 0.255006] |
| VD M=2 readout-mitigated | 2048 | 0.111846 | 0.299392 | 0.0697226 | 0.155000 | [0.0838645, 0.237799] |
| VD M=2 readout-mitigated | 4096 | 0.0514587 | 0.239005 | 0.0187534 | 0.0747046 | [0.0365720, 0.123817] |
| VD M=2 readout-mitigated | 8192 | 0.00857154 | 0.196118 | 0.0113165 | 0.0490714 | [0.0286580, 0.0718324] |

At the largest B, the MSE ordering is:

```text
SV readout-mitigated: 0.000549129
unmitigated:          0.0150867
VD M=2:               0.0490714
```

SV is now clearly separated from both unmitigated and VD. The second n=6
hardware instance therefore supports the same qualitative conclusion as
`g6_k2_c000`: calibrated SV dominates, while VD is degraded by the denominator
and implementation overhead.

## P7 Denominator Behavior

| B | mean VD denominator | B / B_den estimate |
|---:|---:|---:|
| 512 | 0.0369748 | 0.0192850 |
| 1024 | 0.0480991 | 0.0385700 |
| 2048 | 0.0495084 | 0.0771401 |
| 4096 | 0.0510128 | 0.154280 |
| 8192 | 0.0514859 | 0.308560 |

The denominator remains small and below the estimated concentration scale across
the available B grid. This is qualitative P7 evidence, not a coefficient-level
claim.
