# Level 3 Full Hardware P7/P9 Run

Status: full Level 3 qualitative hardware run complete for `g6_k2_c000`.
This is a feasibility and form/robustness result with calibrated readout, not a
hardware validation of Level 1 coefficients.

## Scope And Framing

This run extends the Stage 2 precursor to include VD M=2, a reduced B sweep, and
multiple calibration epochs. The scientific target is qualitative P7/P9 behavior
on hardware:

- P7 form: the VD denominator is small on hardware and remains below its
  concentration scale in the available B grid.
- P9 form: SV dominates the observed MSE curve while VD is degraded by
  Hadamard/SWAP and routing overhead.

The run uses one primary instance, `g6_k2_c000`. A second instance was not run
because the primary run filled the intended hardware budget window with 38
calibration epochs. Claims remain qualitative: no coefficient matching, no
constant validation, and no Level 1 numeric adjudication.

Each epoch is one SamplerV2 job containing readout calibration, the shared Z
measurement circuit, VD numerator, and VD denominator. Epochs are the bootstrap
clusters because shots within an epoch share the same calibration and device
state.

## Prerequisites

Credential source: global saved IBM account loaded by `QiskitRuntimeService()`.
No token, CRN, or credential file is stored in this repository.

Read-only backend check:

```text
qiskit 2.3.1
qiskit_aer 0.17.2
qiskit_ibm_runtime 0.43.1
service_connected=YES
ibm_marrakesh: operational=True pending_jobs=0 status_msg=active
ibm_kingston: operational=True pending_jobs=0 status_msg=active
ibm_fez: operational=True pending_jobs=0 status_msg=active
```

Primary backend used: `ibm_marrakesh`.

## Dry-Run Before Submission

Command:

```text
python -m level3.stage3 --real-backend-dry-run
```

Output summary:

```text
STAGE3_REAL_BACKEND_DRY_RUN backend=ibm_marrakesh operational=true pending_jobs=0 status_msg=active
BUDGET_ESTIMATE circuits=5 shots_per_circuit=8192 total_shots=40960 max_total_shots=40960 near_cap=true max_circuit_depth=821 estimated_qpu_seconds=33.6282
```

Transpiled circuit summary:

| label | depth | size | cz | sx | rz | x | measure |
|---|---:|---:|---:|---:|---:|---:|---:|
| readout_calib_0 | 1 | 15 | 0 | 0 | 0 | 0 | 15 |
| qaoa_z | 542 | 908 | 202 | 431 | 259 | 10 | 6 |
| vd_m2_numerator | 821 | 2502 | 593 | 1250 | 601 | 45 | 13 |
| vd_m2_denominator | 719 | 2246 | 504 | 1074 | 608 | 47 | 13 |
| readout_calib_1 | 2 | 30 | 0 | 0 | 0 | 15 | 15 |

The VD circuit is substantially deeper than the direct Z circuit, as expected
for c-SWAP/Hadamard-SWAP overhead on the device topology.

Calibration physical qubits:

```text
[98, 109, 118, 110, 87, 107, 91, 108, 129, 111, 88, 106, 97, 89, 90]
```

Shared Z logical-to-physical layout:

| logical | physical |
|---:|---:|
| 0 | 107 |
| 1 | 111 |
| 2 | 118 |
| 3 | 110 |
| 4 | 109 |
| 5 | 108 |

## Submission Summary

The adaptive run was executed in four sequential blocks because IBM reported
lower real QPU seconds per epoch than the dry-run estimate. The final total was
38 epochs and 532 quantum seconds, under the 600 second hard cap.

| quantity | value |
|---|---:|
| epochs | 38 |
| shots per circuit per epoch | 8192 |
| circuits per epoch | 5 |
| total shots per epoch | 40960 |
| total QPU seconds | 532 |
| total QPU minutes | 8.8667 |
| hard cap seconds | 600 |

Job ids:

```text
d8ipqak2upec739mhs2g,d8ipqg1e8nrc73bikqjg,d8ipqlc2upec739mhsg0,d8ipqqs2upec739mhsn0,d8ipr0e6983c73dsem0g,d8ipr5k2upec739mht4g,d8ipras2upec739mhtb0,d8iprg42upec739mhtig,d8iprle6983c73dsemn0,d8iprqhe8nrc73biks3g,d8ips042upec739mhu50,d8ips566983c73dsen7g,d8ipsalv8cos73f5tg40,d8ipsfpe8nrc73bikssg,d8ipslc2upec739mhv00,d8ipt51e8nrc73biktl0,d8iptak2upec739mhvpg,d8ipthu6983c73dseop0,d8iptne6983c73dseoug,d8iptss2upec739mi0g0,d8ipu25v8cos73f5ti10,d8ipu7he8nrc73bikutg,d8ipuclv8cos73f5tibg,d8ipuhk2upec739mi1bg,d8ipumpe8nrc73bikveg,d8ipurs2upec739mi1o0,d8ipv1c2upec739mi210,d8ipv6lv8cos73f5tja0,d8ipve5v8cos73f5tjkg,d8ipvj5v8cos73f5tjq0,d8ipvoc2upec739mi2s0,d8ipvtk2upec739mi32g,d8iq02tv8cos73f5tkd0,d8iq08c2upec739mi3jg,d8iq0dlv8cos73f5tkqg,d8iq0qhe8nrc73bil20g,d8iq171e8nrc73bil2g0,d8iq1cc2upec739mi52g
```

All epoch archives are stored under:

```text
level3/archive/stage3_g6_k2_c000_ibm_marrakesh_epoch*.json.gz
```

The consolidated archive-only analysis is:

```text
level3/archive/stage3_g6_k2_c000_ibm_marrakesh_full_analysis.json
```

## Archive-Only Analysis

Command:

```text
$archives = Get-ChildItem level3/archive -Filter 'stage3_g6_k2_c000_ibm_marrakesh_epoch*.json.gz' | Sort-Object LastWriteTime | ForEach-Object { $_.FullName }
python -m level3.analyze_full @archives --json-out level3/archive/stage3_g6_k2_c000_ibm_marrakesh_full_analysis.json --bootstrap-reps 2000
```

The analysis reads only the archived bitstrings/counts. It does not connect to
IBM Runtime or query the device.

Bootstrap: cluster bootstrap over epochs, 2000 replicates, seed 33033.

### B Sweep

| method | B | estimate | bias | epoch variance | MSE | MSE CI 95% |
|---|---:|---:|---:|---:|---:|---|
| unmitigated | 512 | -0.0317942 | 0.211638 | 0.000258378 | 0.0450421 | [0.0428419, 0.0474304] |
| unmitigated | 1024 | -0.032509 | 0.210923 | 0.000142866 | 0.0446276 | [0.0430959, 0.0463153] |
| unmitigated | 2048 | -0.0311744 | 0.212258 | 0.00013111 | 0.0451809 | [0.0436633, 0.0467409] |
| unmitigated | 4096 | -0.0307021 | 0.21273 | 9.52951e-05 | 0.0453468 | [0.0440785, 0.0466488] |
| unmitigated | 8192 | -0.0314699 | 0.211962 | 7.4528e-05 | 0.0450005 | [0.0439296, 0.0461597] |
| SV readout-mitigated | 512 | -0.140644 | 0.102788 | 0.000202802 | 0.0107628 | [0.00982271, 0.0116996] |
| SV readout-mitigated | 1024 | -0.142005 | 0.101427 | 0.000115792 | 0.0104002 | [0.00974167, 0.0110565] |
| SV readout-mitigated | 2048 | -0.141894 | 0.101538 | 7.72697e-05 | 0.0103852 | [0.00982607, 0.0109476] |
| SV readout-mitigated | 4096 | -0.142192 | 0.10124 | 5.67327e-05 | 0.0103047 | [0.00983719, 0.0107831] |
| SV readout-mitigated | 8192 | -0.142347 | 0.101085 | 4.59012e-05 | 0.0102628 | [0.0098343, 0.0106695] |
| VD M=2 readout-mitigated | 512 | -0.0759652 | 0.167467 | 0.0653897 | 0.0917141 | [0.0627138, 0.12473] |
| VD M=2 readout-mitigated | 1024 | 0.0323831 | 0.275815 | 0.047986 | 0.122797 | [0.0786047, 0.175973] |
| VD M=2 readout-mitigated | 2048 | 0.007799 | 0.251231 | 0.0235287 | 0.0860265 | [0.0649306, 0.109403] |
| VD M=2 readout-mitigated | 4096 | 0.015421 | 0.258853 | 0.00980141 | 0.0765483 | [0.0604788, 0.0935955] |
| VD M=2 readout-mitigated | 8192 | 0.0211383 | 0.26457 | 0.00425512 | 0.0741406 | [0.0634224, 0.0855873] |

At the largest B, the MSE ordering is:

```text
SV readout-mitigated: 0.0102628
unmitigated:          0.0450005
VD M=2:               0.0741406
```

VD does not beat SV at any same-B point in the paired-sample convention. Under
the two-qubit-gate proxy, VD is further penalized by `kappa=14`, so the
qualitative ordering remains SV-dominant.

## P7 Denominator Behavior

The readout-mitigated VD denominator is small on hardware and remains below the
estimated concentration scale across the B grid.

| B | mean VD denominator | B / B_den estimate |
|---:|---:|---:|
| 512 | 0.0806874 | 0.0384843 |
| 1024 | 0.0815581 | 0.0769686 |
| 2048 | 0.074012 | 0.153937 |
| 4096 | 0.0678433 | 0.307874 |
| 8192 | 0.0679719 | 0.615749 |

This is qualitative P7 behavior: the denominator is not concentrated at the
available B values, and VD remains high-variance and clip-sensitive. The result
is consistent with the Level 2 expectation that realistic VD overhead erases the
ideal VD window on this hardware-scale run.

## P9 Crossing Interpretation

No resolved VD-over-SV crossing is observed. The qualitative hardware ordering
is:

```text
SV dominates unmitigated and VD in MSE.
VD is degraded by Hadamard/SWAP routing and c-SWAP overhead.
The crossing, if any, is not resolved in this B grid and budget.
```

This should be reported as a Level 3 qualitative hardware result, not as a
coefficient-level confirmation. The data support the operating-window narrative:
SV is the practical hardware winner here, while VD suffers denominator and
implementation overhead.
