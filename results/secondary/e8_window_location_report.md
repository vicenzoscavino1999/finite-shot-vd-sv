# E8 Window Location

Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.

## Design

- p grid: `0.0001` to `0.01` with `10` log-spaced points.
- Rationale: small-p asymptotic regime over two decades; the range is chosen by principle, not by per-instance fit quality.
- Resource normalization: kappa_VD=2, kappa_SV=1, kappa_unmitigated=1.
- For each p, method i is the lower-bias method; a genuine leading crossing requires g>0 and Delta s>0.

## Ensemble Summary

| pair | structure | predicted exponent | valid instances | mean exponent | std exponent | mean R2 | mean valid fraction | status summary |
|---|---|---:|---:|---:|---:|---:|---:|---|
| vd2_vs_unmitigated | different_leading_variance | -2 | 10/10 | -1.96617 | 0.00592606 | 0.999895 | 1 | valid_crossing:10 |
| sv_vs_unmitigated | matched_leading_variance | -1 | 0/10 | nan | nan | nan | 0 | no_valid_crossing:10 |

## Per-Instance Fits

| instance | pair | predicted | exponent | 95% CI | R2 | valid fraction | status |
|---|---|---:|---:|---:|---:|---:|---|
| g6_k2_c000 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g6_k2_c000 | vd2_vs_unmitigated | -2 | -1.97593 | [-1.98574, -1.96613] | 0.999949 | 1.000 | valid_crossing |
| g6_k2_c001 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g6_k2_c001 | vd2_vs_unmitigated | -2 | -1.97079 | [-1.98267, -1.95891] | 0.999924 | 1.000 | valid_crossing |
| g6_k2_c002 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g6_k2_c002 | vd2_vs_unmitigated | -2 | -1.96928 | [-1.98177, -1.95679] | 0.999916 | 1.000 | valid_crossing |
| g6_k2_c003 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g6_k2_c003 | vd2_vs_unmitigated | -2 | -1.9695 | [-1.98191, -1.9571] | 0.999917 | 1.000 | valid_crossing |
| g6_k2_c004 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g6_k2_c004 | vd2_vs_unmitigated | -2 | -1.97171 | [-1.98323, -1.96018] | 0.999929 | 1.000 | valid_crossing |
| g8_k3_c000 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g8_k3_c000 | vd2_vs_unmitigated | -2 | -1.96324 | [-1.97823, -1.94825] | 0.999879 | 1.000 | valid_crossing |
| g8_k3_c001 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g8_k3_c001 | vd2_vs_unmitigated | -2 | -1.95932 | [-1.97587, -1.94276] | 0.999851 | 1.000 | valid_crossing |
| g8_k3_c002 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g8_k3_c002 | vd2_vs_unmitigated | -2 | -1.96138 | [-1.97714, -1.94562] | 0.999866 | 1.000 | valid_crossing |
| g8_k3_c003 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g8_k3_c003 | vd2_vs_unmitigated | -2 | -1.96059 | [-1.97667, -1.94451] | 0.99986 | 1.000 | valid_crossing |
| g8_k3_c004 | sv_vs_unmitigated | -1 | nan | [nan, nan] | nan | 0.000 | no_valid_crossing |
| g8_k3_c004 | vd2_vs_unmitigated | -2 | -1.95998 | [-1.97627, -1.94369] | 0.999856 | 1.000 | valid_crossing |

## Descriptive Conclusion

VD(M=2) vs unmitigated has a genuine leading crossing across the full small-p grid and recovers the expected p^-2 scale at the ensemble level. SV vs unmitigated has matched leading variance at p=0 but no genuine crossing in the frozen ensemble/range because the lower-bias SV endpoint also has smaller resource-normalized sampling coefficient; it is therefore reported as no_valid_crossing rather than forced into a p^-1 fit.
