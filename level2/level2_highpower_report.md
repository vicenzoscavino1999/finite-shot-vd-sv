# Level 2 Step 5a High-Power Harness

Status: validacion EN FORMA, no matcheo de coeficientes de Nivel 1. Additive Phase B base-data harness; not a freeze and not an adjudication.

## Scope

- Frozen instances: `g6_k2_c000, g6_k2_c001, g6_k2_c002, g6_k2_c003, g6_k2_c004, g8_k3_c000, g8_k3_c001, g8_k3_c002, g8_k3_c003, g8_k3_c004`.
- Methods represented: `unmitigated, sv_mitigated, vd_m2_hadamard_swap`.
- Direct-Z methods use T=`64` noisy Aer trajectory repetitions by splitting a single B_max shot pool per instance.
- VD M=2 uses Step 3 Hadamard/SWAP cross-checks and B_den sizing. Cells whose requested trajectory budget exceeds the cap are marked, not imputed.
- B cap: `8192`; VD trajectory cap per numerator/denominator circuit: `4096`.
- Analyses E5/E7/E8/E12 are deferred to Step 5b/5c over this base table.

## Cross-Checks And Budget

- Sampled aggregate rows: `66`.
- Budget-marked rows: `33`.
- VD budget-marked instances: `g6_k2_c000, g6_k2_c001, g6_k2_c002, g6_k2_c003, g6_k2_c004, g8_k3_c000, g8_k3_c001, g8_k3_c002, g8_k3_c003, g8_k3_c004`.
- Instances not reaching 10x B_den within cap: `g6_k2_c000, g6_k2_c001, g6_k2_c002, g6_k2_c003, g6_k2_c004, g8_k3_c000, g8_k3_c001, g8_k3_c002, g8_k3_c003, g8_k3_c004`.

## Per-Method Summary

| method | sampled rows | budget rows | median abs bias sampled | median MSE sampled |
|---|---:|---:|---:|---:|
| unmitigated | 33 | 0 | 0.113612 | 0.0133196 |
| sv_mitigated | 33 | 0 | 0.0186573 | 0.0019654 |
| vd_m2_hadamard_swap | 0 | 33 | nan | nan |

## Instance Denominator Budget

| instance | n | B_den | B_max | crosses B_den | reaches 10x B_den | VD status | noisy D reference |
|---|---:|---:|---:|---|---|---|---:|
| g6_k2_c000 | 6 | 3865.49 | 8192 | yes | no | budget_exceeded_not_sampled | 0.121094 |
| g6_k2_c001 | 6 | 36632.8 | 8192 | no | no | budget_exceeded_not_sampled | -0.0390625 |
| g6_k2_c002 | 6 | 2326.16 | 8192 | yes | no | budget_exceeded_not_sampled | 0.15625 |
| g6_k2_c003 | 6 | 30304.5 | 8192 | no | no | budget_exceeded_not_sampled | 0.0429688 |
| g6_k2_c004 | 6 | 101332 | 8192 | no | no | budget_exceeded_not_sampled | 0.0234375 |
| g8_k3_c000 | 8 | 57122.5 | 8192 | no | no | budget_exceeded_not_sampled | 0.03125 |
| g8_k3_c001 | 8 | 25488.1 | 8192 | no | no | budget_exceeded_not_sampled | 0.046875 |
| g8_k3_c002 | 8 | 4732.61 | 8192 | yes | no | budget_exceeded_not_sampled | 0.109375 |
| g8_k3_c003 | 8 | 227477 | 8192 | no | no | budget_exceeded_not_sampled | 0.015625 |
| g8_k3_c004 | 8 | 57122.5 | 8192 | no | no | budget_exceeded_not_sampled | 0.03125 |

## Descriptive Conclusion

This file is the base long-format harness output for later Level 2 analyses. Direct-Z unmitigated and SV rows are sampled at T=64 across the frozen ensemble using noisy Aer trajectories and configured tensor-product readout mitigation. VD M=2 rows carry the same B grid, resource columns, noiseless cross-checks, and B_den sizing; however, the noisy VD trajectory budget needed for T=64 at B_max exceeds the current cap, so those cells are explicitly marked as budget-limited rather than treated as evidence. Step 5b/5c should either raise the VD simulation budget or keep the VD limitation as an operational finding.

Runtime for this harness run: `251.587` seconds.
