# Level 2 Step 5c Window Location And Efron-Stein

Status: EN FORMA; E8/P10 folded-noise window-location and E12/P13 Efron-Stein operational analysis. Additive Phase B; not a freeze and not a Level 1 formal certificate.

## E8/P10 Folded-Noise Window Location

- Noise knob: global unitary folding on state preparation with lambda in `{1, 3, 5, 7}`.
- Methods: unmitigated and SV use exact folded rho plus configured readout; VD is the optimistic state-noise-only contrast.
- Important caveat: lambda is a device-depth noise-amplification knob with readout/base-noise floors, not the small-p analytic parameter of Level 1.

- SV-vs-unmit measured slope median: `0.062894` vs expected `-1` matched-leading-variance scaling.
- VD-optimal-vs-SV measured slope median: `nan` vs expected `-2` generic scaling.

| instance | pair | resource | expected | measured | R2 | finite R0 pts | monotone nonincreasing | status |
|---|---|---|---:|---:|---:|---:|---|---|
| g6_k2_c000 | sv_vs_unmit | paired_sample | -1.0 | 0.228903 | 0.937042 | 3 | False | not_asymptotic_or_readout_floor_dominated |
| g6_k2_c000 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 1 |  | insufficient_positive_crossings |
| g6_k2_c001 | sv_vs_unmit | paired_sample | -1.0 | 1.00353 | 0.877386 | 4 | False | not_asymptotic_or_readout_floor_dominated |
| g6_k2_c001 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 1 |  | insufficient_positive_crossings |
| g6_k2_c002 | sv_vs_unmit | paired_sample | -1.0 | 0.983339 | 0.862585 | 4 | False | not_asymptotic_or_readout_floor_dominated |
| g6_k2_c002 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |
| g6_k2_c003 | sv_vs_unmit | paired_sample | -1.0 | 0.516403 | 0.854628 | 4 | False | not_asymptotic_or_readout_floor_dominated |
| g6_k2_c003 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |
| g6_k2_c004 | sv_vs_unmit | paired_sample | -1.0 | 0.0312532 | 0.0672199 | 3 | False | not_asymptotic_or_readout_floor_dominated |
| g6_k2_c004 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |
| g8_k3_c000 | sv_vs_unmit | paired_sample | -1.0 | -0.00813729 | 0.0761538 | 4 | False | decreasing_with_folded_noise |
| g8_k3_c000 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |
| g8_k3_c001 | sv_vs_unmit | paired_sample | -1.0 | 0.0230324 | 0.701624 | 4 | False | not_asymptotic_or_readout_floor_dominated |
| g8_k3_c001 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |
| g8_k3_c002 | sv_vs_unmit | paired_sample | -1.0 | 0.0830484 | 0.834479 | 4 | False | not_asymptotic_or_readout_floor_dominated |
| g8_k3_c002 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |
| g8_k3_c003 | sv_vs_unmit | paired_sample | -1.0 | 0.0427397 | 0.841585 | 4 | False | not_asymptotic_or_readout_floor_dominated |
| g8_k3_c003 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |
| g8_k3_c004 | sv_vs_unmit | paired_sample | -1.0 | 0.0374345 | 0.777879 | 4 | False | not_asymptotic_or_readout_floor_dominated |
| g8_k3_c004 | vd_optimal_vs_sv_contrast | two_qubit_gate_proxy | -2.0 |  |  | 0 |  | insufficient_positive_crossings |

## E12/P13 Efron-Stein Operational Bound

- Selected VD convention: n=6 realistic-interference VD; n=8 optimistic VD as an a-fortiori upper benchmark.
- Selected VD finite two-qubit-proxy R_ES rows: `0/10`.
- Largest finite selected R_ES: `none`.
- Optimistic-contrast finite two-qubit-proxy R_ES rows: `2/10`.
- Largest finite optimistic-contrast R_ES: `5.23141e+09`.
- Selected VD dominates at R_ES on operational scale: `0/10`.

| instance | n | VD variant | resource | R_ES | status | ES constant | VD dominates at R_ES |
|---|---:|---|---|---:|---|---:|---|
| g6_k2_c000 | 6 | vd_selected_realistic_interference_n6 | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 3.92938e+06 | False |
| g6_k2_c001 | 6 | vd_selected_realistic_interference_n6 | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 2.93334e+06 | False |
| g6_k2_c002 | 6 | vd_selected_realistic_interference_n6 | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 1.54792e+06 | False |
| g6_k2_c003 | 6 | vd_selected_realistic_interference_n6 | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 1.55369e+06 | False |
| g6_k2_c004 | 6 | vd_selected_realistic_interference_n6 | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 3.15776e+06 | False |
| g8_k3_c000 | 8 | vd_selected_optimal_n8_a_fortiori | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 6.47247e+10 | False |
| g8_k3_c001 | 8 | vd_selected_optimal_n8_a_fortiori | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 4.83049e+10 | False |
| g8_k3_c002 | 8 | vd_selected_optimal_n8_a_fortiori | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 5.61691e+10 | False |
| g8_k3_c003 | 8 | vd_selected_optimal_n8_a_fortiori | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 6.53935e+10 | False |
| g8_k3_c004 | 8 | vd_selected_optimal_n8_a_fortiori | two_qubit_gate_proxy |  | no_finite_R_ES_bias_or_variance_dominated | 5.14296e+10 | False |

## Descriptive Conclusion

E8 in the folded device-simulation setting does not cleanly recover the small-p Level 1 exponents; the measured slopes are reported with explicit statuses because readout/base-noise floors and global folding move the sweep outside the asymptotic regime. E12 shows that the Efron-Stein VD variance bound does not create an operational resource window where selected VD dominates SV.

Runtime for this analysis: `219.268` seconds.
