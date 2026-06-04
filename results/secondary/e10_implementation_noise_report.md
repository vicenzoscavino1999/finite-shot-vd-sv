# E10 Implementation Noise

Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.

## Design

- p fixed: `0.15`; copies M: `2`.
- Finite-shot budget: B=`100000`, T=`200000` replicas per instance/case.
- RNG: numpy Generator/PCG64 with E10 seed `10010` and per-instance/case stable_seed.
- Contractions are declared: baseline eta=1, common eta in {0.9, 0.8}, asymmetric (eta_N, eta_D)=(0.9, 0.95).
- Checks: variance formula relative tolerance `0.02`; asymmetric bias prediction tolerance `4` SE.

## Case Summary

| case | eta_N | eta_D | theta | n | mean b error | max abs b error / SE | mean v rel error | max abs v rel error | mean v inflation | b invariant pass | v formula pass | bias shift pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline_eta_1 | 1 | 1 | 1 | 10 | -1.426e-05 | 2.724 | -7.579e-04 | 5.833e-03 | 1.000 | 10/10 | 10/10 | na |
| common_eta_0.9 | 0.9 | 0.9 | 1 | 10 | -2.088e-05 | 2.189 | -1.959e-04 | 4.448e-03 | 1.237 | 10/10 | 10/10 | na |
| common_eta_0.8 | 0.8 | 0.8 | 1 | 10 | -4.085e-05 | 3.345 | -5.401e-04 | 6.258e-03 | 1.567 | 10/10 | 10/10 | na |
| asymmetric_eta_N_0.9_eta_D_0.95 | 0.9 | 0.95 | 0.947368 | 10 | -1.826e-05 | 1.777 | 1.297e-03 | 9.264e-03 | 1.106 | na | 10/10 | 10/10 |

## Descriptive Conclusion

Common multiplicative contraction leaves the population quotient bias invariant while inflating the sampling variance according to the closed-form implementation-noise expression. The asymmetric contraction produces the predicted additional bias shift and is resolved from the baseline VD bias in every frozen instance. This is a secondary descriptive endpoint and is not used for primary FWER gatekeeping.
