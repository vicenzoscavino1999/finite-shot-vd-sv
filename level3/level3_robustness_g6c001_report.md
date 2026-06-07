# Level 3 Robustness Check: g6_k2_c001

Status: preliminary inter-instance robustness check complete for `g6_k2_c001`
on `ibm_marrakesh`.

This is an additive Stage 3 hardware check, not a new coefficient claim. The
purpose is to test whether the qualitative SV dominance seen in `g6_k2_c000`
persists on a second frozen n=6 instance under the same calibrated-readout
pipeline. With only four calibration epochs, confidence intervals are wide,
especially for VD. Robust inter-instance conclusions remain deferred to the
180 minute run.

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

## Prerequisites And Budget

Credential source: global saved IBM account loaded by `QiskitRuntimeService()`.
No credential material is stored in this repository.

Read-only backend check:

```text
service_connected=YES
ibm_marrakesh: operational=True pending_jobs=0 status_msg=active
ibm_kingston: operational=True pending_jobs=0 status_msg=active
ibm_fez: operational=True pending_jobs=0 status_msg=active
```

Budget before this check was reconstructed from the archived Stage 2 and Stage
3 usage artifacts:

| quantity | seconds |
|---|---:|
| Stage 2 precursor | 5 |
| Stage 3 `g6_k2_c000` | 532 |
| total before `g6_k2_c001` | 537 |
| remaining before `g6_k2_c001` vs 600 s allocation | 63 |

After the run, the IBM usage query reported:

```text
usage_consumed_seconds=593
usage_limit_seconds=600
usage_remaining_seconds=7
usage_limit_reached=False
```

## Dry-Run Before Submission

Command:

```text
python -m level3.stage3 --instance-id g6_k2_c001 --seed-transpiler 20260608 --real-backend-dry-run
```

Output summary:

```text
STAGE3_REAL_BACKEND_DRY_RUN backend=ibm_marrakesh operational=true pending_jobs=0 status_msg=active
BUDGET_ESTIMATE circuits=5 shots_per_circuit=8192 total_shots=40960 max_total_shots=40960 near_cap=true max_circuit_depth=1001 estimated_qpu_seconds=41.001
```

Transpiled circuit summary:

| label | depth | size | cz | sx | rz | x | measure |
|---|---:|---:|---:|---:|---:|---:|---:|
| readout_calib_0 | 1 | 15 | 0 | 0 | 0 | 0 | 15 |
| qaoa_z | 490 | 947 | 213 | 456 | 263 | 9 | 6 |
| vd_m2_numerator | 1001 | 2402 | 555 | 1175 | 629 | 30 | 13 |
| vd_m2_denominator | 686 | 2145 | 461 | 1013 | 625 | 33 | 13 |
| readout_calib_1 | 2 | 30 | 0 | 0 | 0 | 15 | 15 |

The VD numerator is much deeper than the direct Z circuit, as expected for
Hadamard/SWAP and controlled-SWAP routing overhead on heavy-hex hardware.

Seed:

```text
seed_transpiler = 20260608
```

Calibration physical qubits:

```text
[110, 111, 91, 90, 89, 87, 109, 112, 98, 92, 78, 86, 88, 108, 107]
```

Shared Z logical-to-physical layout:

| logical | physical |
|---:|---:|
| 0 | 89 |
| 1 | 98 |
| 2 | 88 |
| 3 | 111 |
| 4 | 91 |
| 5 | 90 |

VD denominator logical-to-physical layout:

```text
0->110, 1->111, 2->91, 3->90, 4->89, 5->87, 6->109,
7->112, 8->98, 9->92, 10->78, 11->86, 12->88
```

VD numerator logical-to-physical layout:

```text
0->89, 1->90, 2->98, 3->91, 4->110, 5->108, 6->88,
7->78, 8->112, 9->92, 10->111, 11->107, 12->109
```

## Submission Summary

The adaptive plan first ran one epoch, read real QPU usage, then ran three more
epochs because the first job consumed 14 seconds. This used 56 seconds total:
slightly above the 55 second soft target, but below the 63 second remaining
allocation and below the 600 second global limit.

| quantity | value |
|---|---:|
| instance | `g6_k2_c001` |
| backend | `ibm_marrakesh` |
| epochs | 4 |
| shots per circuit per epoch | 8192 |
| circuits per epoch | 5 |
| total shots per epoch | 40960 |
| QPU seconds for this check | 56 |
| total QPU seconds after this check | 593 |
| allocation limit seconds | 600 |
| remaining seconds after this check | 7 |

Job ids:

```text
d8ir1ilv8cos73f5uqkg,d8ir245v8cos73f5ur7g,d8ir29c2upec739mjcd0,d8ir2f42upec739mjcj0
```

Epoch archives:

```text
level3/archive/stage3_g6_k2_c001_ibm_marrakesh_epoch*.json.gz
```

Consolidated archive-only analysis:

```text
level3/archive/stage3_g6_k2_c001_ibm_marrakesh_full_analysis.json
```

## Archive-Only Analysis

Command:

```text
$archives = Get-ChildItem level3/archive -Filter 'stage3_g6_k2_c001_ibm_marrakesh_epoch*.json.gz' | Sort-Object LastWriteTime | ForEach-Object { $_.FullName }
python -m level3.analyze_full @archives --json-out level3/archive/stage3_g6_k2_c001_ibm_marrakesh_full_analysis.json --bootstrap-reps 2000
```

The analysis reads only archived bitstrings/counts. It does not connect to IBM
Runtime or query the device.

Bootstrap: cluster bootstrap over epochs, 2000 replicates, seed 33033.

### B Sweep

| method | B | estimate | bias | epoch variance | MSE | MSE CI 95% |
|---|---:|---:|---:|---:|---:|---|
| SV readout-mitigated | 512 | -0.128892 | 0.0586544 | 0.000401534 | 0.00374149 | [0.00197877, 0.00526289] |
| SV readout-mitigated | 1024 | -0.136924 | 0.0506225 | 8.66843e-05 | 0.00262765 | [0.00182773, 0.00342757] |
| SV readout-mitigated | 2048 | -0.141554 | 0.0459923 | 4.37101e-05 | 0.00214807 | [0.00163867, 0.00265748] |
| SV readout-mitigated | 4096 | -0.140554 | 0.0469922 | 3.35718e-06 | 0.00221079 | [0.00206682, 0.00235475] |
| SV readout-mitigated | 8192 | -0.142345 | 0.0452006 | 2.29683e-06 | 0.00204482 | [0.00193447, 0.00217272] |
| unmitigated | 512 | -0.0173271 | 0.170219 | 5.71088e-05 | 0.0290173 | [0.0268993, 0.0311353] |
| unmitigated | 1024 | -0.0257219 | 0.161824 | 0.000123014 | 0.0262793 | [0.0234071, 0.0291515] |
| unmitigated | 2048 | -0.0319066 | 0.15564 | 1.85963e-05 | 0.0242376 | [0.0231742, 0.025301] |
| unmitigated | 4096 | -0.0292718 | 0.158274 | 2.67464e-05 | 0.0250708 | [0.0234849, 0.0261084] |
| unmitigated | 8192 | -0.0293892 | 0.158157 | 5.30988e-06 | 0.0250176 | [0.0244231, 0.0256121] |
| VD M=2 readout-mitigated | 512 | 0.155839 | 0.343385 | 0.125705 | 0.212192 | [0.0357321, 0.467413] |
| VD M=2 readout-mitigated | 1024 | 0.0898074 | 0.277353 | 0.0580569 | 0.120468 | [0.0130763, 0.255511] |
| VD M=2 readout-mitigated | 2048 | 0.0157642 | 0.20331 | 0.101242 | 0.117266 | [0.00354719, 0.319702] |
| VD M=2 readout-mitigated | 4096 | -0.0347863 | 0.15276 | 0.000852176 | 0.0239747 | [0.0165877, 0.0322011] |
| VD M=2 readout-mitigated | 8192 | -0.0405705 | 0.146976 | 0.00425796 | 0.0247953 | [0.00968077, 0.0363812] |

At the largest B, the MSE ordering is:

```text
SV readout-mitigated: 0.00204482
VD M=2:               0.0247953
unmitigated:          0.0250176
```

SV clearly remains the best method in this preliminary check. The strict
`g6_k2_c000` ordering `SV < unmitigated < VD` does not repeat exactly at the
largest B: VD is slightly below unmitigated by MSE, but the difference is only
about 2.2e-4 and VD has a wide four-epoch bootstrap interval. This should not be
reported as a resolved VD improvement over unmitigated.

## P7 Denominator Behavior

The readout-mitigated VD denominator remains small and below the estimated
concentration scale in the available B grid.

| B | mean VD denominator | B / B_den estimate |
|---:|---:|---:|
| 512 | 0.0310232 | 0.0334876 |
| 1024 | 0.0433274 | 0.0669752 |
| 2048 | 0.0467173 | 0.13395 |
| 4096 | 0.0528544 | 0.267901 |
| 8192 | 0.0651504 | 0.535802 |

This is consistent with the Stage 3 hardware interpretation: VD is sensitive to
denominator concentration and implementation overhead on the available B grid.

## Comparison With g6_k2_c000

Largest-B MSE comparison:

| instance | epochs | SV | unmitigated | VD M=2 | strict order at B=8192 |
|---|---:|---:|---:|---:|---|
| `g6_k2_c000` | 38 | 0.0102628 | 0.0450005 | 0.0741406 | SV < unmitigated < VD |
| `g6_k2_c001` | 4 | 0.00204482 | 0.0250176 | 0.0247953 | SV < VD < unmitigated |

The robust qualitative feature that repeats is SV dominance. The full strict
ordering does not repeat at B=8192, but the unmitigated-vs-VD separation in
`g6_k2_c001` is not resolved with only four epochs. At B=512, 1024, and 2048,
`g6_k2_c001` does show the same `SV < unmitigated < VD` ordering seen in
`g6_k2_c000`; at B=4096 and 8192, VD edges just below unmitigated while
remaining far worse than SV.

The honest conclusion is preliminary: this second instance supports the claim
that SV remains the practical hardware winner under calibrated readout. It does
not support any coefficient-level claim or a precise inter-instance CI claim.
The full robustness test remains the 180 minute run.
