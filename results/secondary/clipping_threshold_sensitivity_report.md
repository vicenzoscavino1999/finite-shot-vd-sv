# Clipping-Threshold Sensitivity

Status: secondary descriptive endpoint (registered robustness check, EXPERIMENTAL_PLAN sec. 10; not primary FWER).

## Design

- p fixed: `0.15`; VD copies M: `2`.
- B grid: `200` to `30000` with `12` log-spaced points.
- Replicas: T=`20000`; bootstrap resamples per B/fraction: `200`.
- Common random numbers: for each instance and B, the same numerator and denominator binomial draws feed all three clipping floors.
- Floors compared: D_M/3, D_M/2, and 2D_M/3; D_M/2 is the reference.

## Per-Instance Leading-Law Fit

| instance | beta1(D/3) +/- 1.96SE | beta1(D/2) +/- 1.96SE | beta1(2D/3) +/- 1.96SE | max abs delta | max rel delta | clip rate at max B |
|---|---:|---:|---:|---:|---:|---:|
| g6_k2_c000 | 6.06736 +/- 0.066 | 6.07196 +/- 0.065 | 6.08643 +/- 0.065 | 1.448e-02 | 2.384e-03 | 0.000e+00 |
| g6_k2_c001 | 7.82508 +/- 0.1 | 7.8338 +/- 0.1 | 7.88288 +/- 0.1 | 4.908e-02 | 6.265e-03 | 0.000e+00 |
| g6_k2_c002 | 8.31345 +/- 0.13 | 8.33821 +/- 0.12 | 8.38913 +/- 0.12 | 5.092e-02 | 6.107e-03 | 0.000e+00 |
| g6_k2_c003 | 8.56043 +/- 0.1 | 8.57175 +/- 0.099 | 8.6206 +/- 0.1 | 4.885e-02 | 5.699e-03 | 0.000e+00 |
| g6_k2_c004 | 7.82555 +/- 0.096 | 7.83538 +/- 0.092 | 7.86946 +/- 0.092 | 3.408e-02 | 4.350e-03 | 0.000e+00 |
| g8_k3_c000 | 20.14 +/- 0.24 | 20.4614 +/- 0.23 | 20.8412 +/- 0.24 | 3.798e-01 | 1.856e-02 | 0.000e+00 |
| g8_k3_c001 | 19.6255 +/- 0.3 | 20.0239 +/- 0.28 | 20.5009 +/- 0.27 | 4.770e-01 | 2.382e-02 | 0.000e+00 |
| g8_k3_c002 | 22.4322 +/- 0.29 | 22.9285 +/- 0.27 | 23.4471 +/- 0.27 | 5.186e-01 | 2.262e-02 | 0.000e+00 |
| g8_k3_c003 | 24.8463 +/- 0.33 | 25.4114 +/- 0.31 | 25.9276 +/- 0.31 | 5.651e-01 | 2.224e-02 | 0.000e+00 |
| g8_k3_c004 | 20.185 +/- 0.25 | 20.499 +/- 0.25 | 20.8825 +/- 0.24 | 3.834e-01 | 1.871e-02 | 0.000e+00 |

## Descriptive Conclusion

With common random numbers, the three estimators coincide in every replica without a clipping event. Across the frozen ensemble, the maximum relative beta1 deviation from the D_M/2 reference is 2.382e-02, below the descriptive tolerance 0.05; the maximum clip-event rate at the largest B is 0.000e+00. The leading law is therefore invariant to the registered clipping-threshold perturbation.
