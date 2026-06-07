# Level 2 Step 5a High-Power Harness (Redo, Option A)

Status: validacion EN FORMA, no matcheo de coeficientes de Nivel 1. Additive Phase B base-data harness; not a freeze and not an adjudication.

## Scope

- Frozen instances: `g6_k2_c000, g6_k2_c001, g6_k2_c002, g6_k2_c003, g6_k2_c004, g8_k3_c000, g8_k3_c001, g8_k3_c002, g8_k3_c003, g8_k3_c004`.
- Methods represented: `unmitigated, sv_mitigated, vd_m2_hadamard_binomial`.
- Repetitions per cell: `100`.
- Common base: exact Aer density matrix of the noisy state-preparation circuit at `mixer_trotter_steps=1`.
- Unmitigated/SV model: exact rho plus configured tensor-product readout, then multinomial finite-shot sampling.
- VD model: exact `D_2=Tr(rho^2)` and `N_2=Tr(O rho^2)` plus independent Hadamard-binomial finite-shot sampling.
- VD framing: state-noise-only optimistic model; it omits the extra c-SWAP/interference/readout noise characterized in Step 3.
- Analyses E5/E7/E8/E12 are deferred to Step 5b/5c over this base table.

## Cross-Checks And Grid

- Sampled aggregate rows: `210`.
- Budget-marked rows: `0`.
- Instances not reaching 10x B_den: `none`.
- Absolute B ceiling configured: `20000000`.

## Per-Method Summary

| method | rows | median abs empirical bias | median MSE | median population bias |
|---|---:|---:|---:|---:|
| unmitigated | 70 | 0.104397 | 0.0110173 | 0.104409 |
| sv_mitigated | 70 | 0.0144562 | 0.00036541 | 0.0144463 |
| vd_m2_hadamard_binomial | 70 | 0.0549494 | 0.0332066 | 0.0747067 |

## Inter-Instance Dispersion

| method | large-B mean abs bias avg | large-B mean abs bias sd | large-B MSE avg | large-B MSE sd |
|---|---:|---:|---:|---:|
| unmitigated | 0.106045 | 0.043941 | 0.012985 | 0.00983965 |
| sv_mitigated | 0.0263133 | 0.0253283 | 0.00127151 | 0.00198144 |
| vd_m2_hadamard_binomial | 0.0778666 | 0.0697943 | 0.0122755 | 0.0114568 |

## Instance Denominator Grid

| instance | n | D_2 exact | B_den | B_max | reaches 10x B_den | VD sampled |
|---|---:|---:|---:|---:|---|---|
| g6_k2_c000 | 6 | 0.111672 | 4541.07 | 45411 | yes | yes |
| g6_k2_c001 | 6 | 0.122551 | 3774.56 | 37746 | yes | yes |
| g6_k2_c002 | 6 | 0.148171 | 2586.16 | 25862 | yes | yes |
| g6_k2_c003 | 6 | 0.147866 | 2596.82 | 25969 | yes | yes |
| g6_k2_c004 | 6 | 0.120478 | 3904.9 | 39050 | yes | yes |
| g8_k3_c000 | 8 | 0.00667417 | 1.24331e+06 | 12433078 | yes | yes |
| g8_k3_c001 | 8 | 0.00718115 | 1.07412e+06 | 10741241 | yes | yes |
| g8_k3_c002 | 8 | 0.00691518 | 1.15824e+06 | 11582429 | yes | yes |
| g8_k3_c003 | 8 | 0.00665702 | 1.24971e+06 | 12497138 | yes | yes |
| g8_k3_c004 | 8 | 0.0070694 | 1.10831e+06 | 11083128 | yes | yes |

## Descriptive Conclusion

This redo replaces the trajectory-capped Step 5a table with exact-rho Option A. VD is sampled in every frozen instance and every grid reaches at least 10x B_den. The ordering of VD/SV/unmitigated is operating-window dependent, not universal: the optimistic VD model has the smaller bias floor in the n=6 moderate-noise window, while SV has the smaller error in the n=8 extreme-decoherence window where D_2 is near 0.007. Two caveats are explicit: the n=6 VD rows are an optimistic state-noise-only model without c-SWAP/interference/readout overhead, and the n=8 window is close to maximally mixed. No E5/E7/E8/E12 conclusions are drawn here; those analyses consume this table next.

Runtime for this harness run: `43.763` seconds.
