# Level 2 Realistic VD n=6

Status: EN FORMA; device-circuit VD con interferencia, n=6. Additive Phase B follow-up; not a freeze and not an adjudication.

## Scope

- Instances: `g6_k2_c000, g6_k2_c001, g6_k2_c002, g6_k2_c003, g6_k2_c004`.
- Repetitions per cell: `64`.
- Circuit: full Step 3 VD M=2 Hadamard/SWAP circuit with decomposed c-SWAP, Aer gate noise, and configured readout.
- Sampling: exact density-matrix outcome distribution of the 13-qubit circuit, followed by multinomial finite-shot sampling.
- Comparison baseline: Step 5a exact-rho optimistic VD and SV conventions; SV is sampled at matched paired-sample and two-qubit-proxy resources.

## Per-Instance Large-B Summary

| instance | B_max | D realistic | B_den | abs bias VD realistic | abs bias VD opt 5a | abs bias SV 5a | VD floor beats SV | VD MSE beats SV paired | VD MSE beats SV twoq |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| g6_k2_c000 | 96876 | 0.0762645 | 9687.55 | 0.0847827 | 0.0302377 | 0.0798731 | no | no | no |
| g6_k2_c001 | 83666 | 0.0821058 | 8366.55 | 0.0633636 | 0.0191644 | 0.0445012 | no | no | no |
| g6_k2_c002 | 60696 | 0.0965033 | 6069.55 | 0.0354366 | 0.0102103 | 0.00900637 | no | no | no |
| g6_k2_c003 | 60810 | 0.0964124 | 6080.93 | 0.0286945 | 0.00521782 | 0.00177351 | no | no | no |
| g6_k2_c004 | 86818 | 0.0805915 | 8681.72 | 0.0292781 | 0.0108637 | 0.00896527 | no | no | no |

## Aggregate Readout

- Bias-floor wins for VD realistic vs SV: `0/5`.
- Large-B MSE wins for VD realistic vs SV at paired-sample resource: `0/5`.
- Large-B MSE wins for VD realistic vs SV at two-qubit-gate-proxy resource: `0/5`.

## Descriptive Conclusion

This follow-up measures whether the n=6 optimistic VD operating window survives the realistic c-SWAP/interference overhead. The table reports the result as measured: no universal winner is assumed. Bias floors, overhead relative to the Step 5a optimistic VD model, and resource-matched SV comparisons are all exposed per instance for the downstream Level 2 analyses.

Runtime for this harness run: `289.203` seconds.
