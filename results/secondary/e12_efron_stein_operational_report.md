# E12 Efron-Stein Operational Certificate

Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Level-1 white-box version of a Level-2 endpoint. Additive layer, does not modify any frozen/hashed artifact.

## Design

- p fixed: `0.05`; copies M: `2`.
- B grid: ceil(B_den * [1, 2, 4, 8, 16, 32]) per instance; T=`50000` replicas.
- ES coefficient: `8(D+4)^2/D^4`, read from `model.vd(...)["efron_stein_bound"]`.
- Formal scale reference: `1.0e+08`. This is a magnitude reference for the extreme formal constants, not a recomputed threshold.

## Variance Certificate

| quantity | min | median | max |
|---|---:|---:|---:|
| ES constant | 611.701 | 1034.78 | 1507.97 |
| ES / formal scale | 6.117e-06 | 1.035e-05 | 1.508e-05 |
| R_ES vs unmitigated | 418095 | 1.36198e+06 | 3.51287e+06 |
| R_ES vs SV (finite only) | 2.4561e+08 | 3.45919e+09 | 4.46199e+10 |

Certificate cells passing Var_empirical <= ES/B: `60/60`.
SV dominates VD under the ES law in `5/10` frozen instances; remaining VD-vs-SV crossings are very large when finite.

## Descriptive Conclusion

The Efron-Stein clipped-quotient variance certificate holds on every sampled B>=B_den cell. At p=0.05 the ES constants are on an operational 10^3 scale, many orders below the declared 1e8 formal-scale reference. With the ES variance coefficient, VD-vs-unmitigated crossings remain finite and operational in the Level-1 leading law. VD-vs-SV is reported honestly: SV often dominates under the ES law, and finite VD-vs-SV crossings are not the main operational content of P13.
