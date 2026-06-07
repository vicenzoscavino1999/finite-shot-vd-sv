# Level 2 Step 5b Crossing And Denominator Analysis

Status: EN FORMA; denominator concentration (E5/P7) and operating crossings (E7/P9) over existing Level 2 CSVs. Additive Phase B analysis; not a freeze and not a Level 1 formal certificate.

## Inputs And VD Convention

- High-power 5a CSV: `level2_highpower_results.csv`.
- Realistic VD n=6 CSV: `level2_vd_realistic_n6_results.csv`.
- n=6: selected VD is the realistic c-SWAP/interference-including device circuit.
- n=8: selected VD is the optimistic state-noise-only VD from 5a; since it already loses, realistic VD would lose a fortiori.

## E5/P7 Denominator Concentration In Form

| ratio B/B_den | median exact P(D_hat<D/2) | median Bernstein bound |
|---:|---:|---:|
| 0.1 | 0.119279 | 0.501173 |
| 0.25 | 0.0311531 | 0.17782 |
| 0.5 | 0.00409866 | 0.0316209 |
| 1 | 9.20795e-05 | 0.000999954 |
| 2 | 6.16929e-08 | 9.99912e-07 |
| 5 | 3.1987e-17 | 9.99901e-16 |
| 10 | 1.76109e-32 | 9.99805e-31 |

The exact bad-denominator probability drops sharply around the B_den scale and is negligible by 10x B_den. Below the scale, the quotient is clip-sensitive and high-variance, matching the P7 law in form for the Aer/device-sim setting.

## E7/P9 Operating Crossings In Form

- SV vs unmitigated has SV as the large-resource winner in `10/10` instances.
- Selected VD vs SV under the two-qubit proxy is SV-dominant or large-resource SV-winning in `10/10` instances.
- The n=6 optimistic VD contrast has a VD large-resource window in `2/5` two-qubit-proxy comparisons, showing the ideal VD window that the realistic interference overhead erases.

| instance | n | resource | pair | regime | low-R winner | high-R winner | R0 | R0/Rmax | eta status |
|---|---:|---|---|---|---|---|---:|---:|---|
| g6_k2_c000 | 6 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 0.0297992 | 6.5621e-07 | operational_eta_above_half |
| g6_k2_c000 | 6 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c000 | 6 | two_qubit_gate_proxy | vd_optimal_vs_sv_contrast | crossing | sv_mitigated | vd_optimal_contrast | 247848 | 0.38985 | operational_eta_below_half |
| g6_k2_c001 | 6 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 0.561642 | 1.48795e-05 | operational_eta_above_half |
| g6_k2_c001 | 6 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c001 | 6 | two_qubit_gate_proxy | vd_optimal_vs_sv_contrast | crossing | sv_mitigated | vd_optimal_contrast | 628678 | 1.18968 | operational_eta_below_half |
| g6_k2_c002 | 6 | two_qubit_gate_proxy | sv_vs_unmit | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c002 | 6 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c002 | 6 | two_qubit_gate_proxy | vd_optimal_vs_sv_contrast | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c003 | 6 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 14.3252 | 0.000551629 | operational_eta_above_half |
| g6_k2_c003 | 6 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c003 | 6 | two_qubit_gate_proxy | vd_optimal_vs_sv_contrast | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c004 | 6 | two_qubit_gate_proxy | sv_vs_unmit | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c004 | 6 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g6_k2_c004 | 6 | two_qubit_gate_proxy | vd_optimal_vs_sv_contrast | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g8_k3_c000 | 8 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 5.13235 | 4.12798e-07 | operational_eta_above_half |
| g8_k3_c000 | 8 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g8_k3_c001 | 8 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 7.28481 | 6.78209e-07 | operational_eta_above_half |
| g8_k3_c001 | 8 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g8_k3_c002 | 8 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 4.41845 | 3.81478e-07 | operational_eta_above_half |
| g8_k3_c002 | 8 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g8_k3_c003 | 8 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 3.42461 | 2.74032e-07 | operational_eta_above_half |
| g8_k3_c003 | 8 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |
| g8_k3_c004 | 8 | two_qubit_gate_proxy | sv_vs_unmit | crossing | unmitigated | sv_mitigated | 4.70904 | 4.24883e-07 | operational_eta_above_half |
| g8_k3_c004 | 8 | two_qubit_gate_proxy | vd_selected_vs_sv | uniform_sv_mitigated | sv_mitigated | sv_mitigated |  |  | not_applicable_no_positive_crossing |

## Descriptive Conclusion

The denominator analysis shows the expected P7 concentration transition at B/B_den ~ 1. The crossing analysis supports an operating-window narrative rather than a universal winner: SV beats unmitigated at large resource; SV dominates the realistic VD device circuit across the ensemble; and the optimistic n=6 VD window exists only when the c-SWAP/interference overhead is removed.

Runtime for this analysis: `0.122` seconds.
