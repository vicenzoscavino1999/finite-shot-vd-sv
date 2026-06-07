# Level 3 Hardware Size Check: g8_k3_c000

Status: additive n=8 hardware check complete for `g8_k3_c000` on
`ibm_marrakesh`.

This run extends the Stage 3 hardware robustness layer from n=6 to n=8. It is a
qualitative feasibility/form result with calibrated readout, not a validation of
Level 1 coefficients.

## Scope And Framing

The n=8 VD M=2 circuit uses 17 logical qubits and is substantially deeper than
the n=6 circuits. The expected honest outcome is that calibrated SV remains
stable, while VD is highly unstable because the interferometry circuit is deep
and the denominator is very small. This is consistent with the Level 2
device-simulation result that realistic VD overhead erases optimistic VD windows.

The Level 2 noiseless reference used for this instance is:

```text
mu_ideal_noiseless_l2 ~= -0.0668269693964
```

## Dry-Run Before Submission

Command:

```text
python -m level3.stage3 --instance-id g8_k3_c000 --seed-transpiler 20260611 --real-backend-dry-run
```

Output summary:

```text
STAGE3_REAL_BACKEND_DRY_RUN backend=ibm_marrakesh operational=true pending_jobs=0 status_msg=active
BUDGET_ESTIMATE circuits=5 shots_per_circuit=8192 total_shots=40960 max_total_shots=40960 near_cap=true max_circuit_depth=3192 estimated_qpu_seconds=130.744
```

Transpiled circuit summary:

| label | depth | size | cz | sx | rz | x | measure |
|---|---:|---:|---:|---:|---:|---:|---:|
| readout_calib_0 | 1 | 18 | 0 | 0 | 0 | 0 | 18 |
| qaoa_z | 1633 | 3315 | 812 | 1732 | 753 | 10 | 8 |
| vd_m2_numerator | 3192 | 7529 | 1927 | 4003 | 1531 | 51 | 17 |
| vd_m2_denominator | 1869 | 6157 | 1482 | 3116 | 1491 | 51 | 17 |
| readout_calib_1 | 2 | 36 | 0 | 0 | 0 | 18 | 18 |

Calibration physical qubits:

```text
[78, 88, 86, 97, 98, 111, 108, 110, 69, 89, 85, 87, 91, 112, 107, 109, 118, 90]
```

Shared Z logical-to-physical layout:

| logical | physical |
|---:|---:|
| 0 | 87 |
| 1 | 98 |
| 2 | 111 |
| 3 | 97 |
| 4 | 107 |
| 5 | 109 |
| 6 | 110 |
| 7 | 108 |

## Submission Summary

After the dry-run, one real epoch was run to measure actual QPU usage. It used
15 seconds. Eleven additional epochs were then run, for 12 total epochs and 180
QPU seconds.

| quantity | value |
|---|---:|
| instance | `g8_k3_c000` |
| backend | `ibm_marrakesh` |
| epochs | 12 |
| shots per circuit per epoch | 8192 |
| circuits per epoch | 5 |
| total shots per epoch | 40960 |
| total QPU seconds | 180 |

Job ids:

```text
d8iufope8nrc73biqlb0,d8iugdm6983c73dskdd0,d8iugotv8cos73f63g9g,d8iugutv8cos73f63gf0,d8iuh69e8nrc73biqmp0,d8iuhc9e8nrc73biqn00,d8iuhte6983c73dsket0,d8iui8dv8cos73f63hp0,d8iuie66983c73dskfeg,d8iuirpe8nrc73biqodg,d8iuj1lv8cos73f63ijg,d8iuj7e6983c73dskg90
```

## Archive-Only Analysis

Command:

```text
python -m level3.analyze_full level3/archive/stage3_g8_k3_c000_ibm_marrakesh_epoch*.json.gz --json-out level3/archive/stage3_g8_k3_c000_ibm_marrakesh_full_analysis.json --bootstrap-reps 2000
```

Bootstrap: cluster bootstrap over epochs, 2000 replicates, seed 33033.

### B Sweep

| method | B | estimate | bias | epoch variance | MSE | MSE CI 95% |
|---|---:|---:|---:|---:|---:|---|
| SV readout-mitigated | 512 | -0.0855503 | -0.0187233 | 0.000182285 | 0.000517656 | [0.000287143, 0.000743386] |
| SV readout-mitigated | 1024 | -0.0837339 | -0.0169069 | 5.81904e-05 | 0.000339185 | [0.000200477, 0.000495840] |
| SV readout-mitigated | 2048 | -0.0816839 | -0.0148569 | 4.92577e-05 | 0.000265881 | [0.000157633, 0.000405611] |
| SV readout-mitigated | 4096 | -0.0810547 | -0.0142277 | 1.39611e-05 | 0.000215225 | [0.000159005, 0.000276218] |
| SV readout-mitigated | 8192 | -0.0788151 | -0.0119881 | 1.22225e-05 | 0.000154919 | [0.000112434, 0.000200939] |
| unmitigated | 512 | 0.0814988 | 0.148326 | 0.000174725 | 0.0221607 | [0.0199764, 0.0241304] |
| unmitigated | 1024 | 0.0836003 | 0.150427 | 0.000240841 | 0.0228491 | [0.0202899, 0.0253258] |
| unmitigated | 2048 | 0.0836558 | 0.150483 | 0.000304319 | 0.0229240 | [0.0201317, 0.0256325] |
| unmitigated | 4096 | 0.0824406 | 0.149268 | 0.000117839 | 0.0223888 | [0.0205836, 0.0240079] |
| unmitigated | 8192 | 0.0810921 | 0.147919 | 5.08888e-05 | 0.0219267 | [0.0207509, 0.0230196] |
| VD M=2 readout-mitigated | 512 | -1236.73 | -1236.66 | 9.43795e+06 | 1.01808e+07 | [1.28863e+05, 2.67019e+07] |
| VD M=2 readout-mitigated | 1024 | 2869.27 | 2869.34 | 3.54741e+07 | 4.07510e+07 | [643.175, 1.05940e+08] |
| VD M=2 readout-mitigated | 2048 | 968.912 | 968.978 | 2.04497e+07 | 1.96845e+07 | [3.97567e+06, 4.15315e+07] |
| VD M=2 readout-mitigated | 4096 | -140.976 | -140.909 | 6.06328e+06 | 5.57786e+06 | [2.11458e+06, 9.93910e+06] |
| VD M=2 readout-mitigated | 8192 | -595.103 | -595.037 | 7.01062e+06 | 6.78047e+06 | [1.71825e+06, 1.29395e+07] |

At the largest B, the MSE ordering is:

```text
SV readout-mitigated: 0.000154919
unmitigated:          0.0219267
VD M=2:               6.78047e+06
```

SV dominates clearly. VD is not merely worse than SV; it is numerically unstable
because the denominator is near zero on hardware for this deep 17-qubit
interferometry circuit.

## P7 Denominator Behavior

| B | mean VD denominator | B / B_den estimate |
|---:|---:|---:|
| 512 | -0.0107336 | 1.62453e-05 |
| 1024 | -0.00771876 | 3.24906e-05 |
| 2048 | -0.00241972 | 6.49812e-05 |
| 4096 | -0.00234607 | 0.000129962 |
| 8192 | -0.00335657 | 0.000259925 |

The denominator is effectively unconcentrated in the available budget. This is
the expected n=8 hardware behavior: the VD circuit is deep and the denominator
is too small for a stable quotient in this resource window.
