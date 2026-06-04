# Ensemble Coverage Analysis

Status: post_adjudication_analysis_only.

This report analyzes coverage and pooled residual behavior on the existing v1 and v2 confirmatory outputs. It does not define a new PAP freeze, does not retry seeds, and does not change either adjudication table.

## Coverage Summary

| Dataset | Coefficient | k/n covered | Binomial P(K<=k; p=0.95) | chi2_n | chi2 p-value | mean(z) | Conclusion |
|---|---|---:|---:|---:|---:|---:|---|
| v1 | VD beta0 (E1) | 10/10 | 1 | 3.348 | 0.972 | -0.281 | consistent with nominal ensemble coverage |
| v1 | VD beta1 (E1) | 10/10 | 1 | 5.869 | 0.8262 | 0.390 | consistent with nominal ensemble coverage |
| v1 | c_VD (E2 instance-p cells) | 27/30 | 0.1878 | 49.383 | 0.01436 | -0.246 | not consistent with nominal ensemble coverage |
| v2 | VD beta0 (E1) | 9/10 | 0.4013 | 14.890 | 0.1361 | 0.500 | consistent with nominal ensemble coverage |
| v2 | VD beta1 (E1) | 8/10 | 0.08614 | 14.304 | 0.1596 | -0.575 | consistent with nominal ensemble coverage |
| v2 | c_VD (E2 instance-p cells) | 28/30 | 0.4465 | 41.519 | 0.07864 | 0.024 | consistent with nominal ensemble coverage |

## Dataset v1

Path: `D:/paper fisica 4/finite-shot-vd-sv/results/confirmatory_full`

### c_SV Equivalence

| Cells within TOST margin | CIs containing zero | mean(c_hat) | median abs(c_hat) | max abs(c_hat) | min margin | median margin | Failures |
|---:|---:|---:|---:|---:|---:|---:|---|
| 30/30 (1.000) | 29/30 | 0.00212 | 0.02143 | 0.05902 | 0.07806 | 0.2666 | none |

Conclusion: c_SV remains numerically centered near zero and is evaluated as an equivalence endpoint, not as closed-form point recovery.

### Delta Consistency

| Coefficient | Non-near-zero pass count | Near-zero count | Max abs error (non-near-zero) | Tolerance | Near-zero instances | Failures |
|---|---:|---:|---:|---:|---|---|
| delta_VD | 7/7 (1.000) | 3 | 0.0007798 | 0.01 | g8_k3_c001, g8_k3_c002, g8_k3_c003 | none |
| delta_SV | 9/9 (1.000) | 1 | 0.0003136 | 0.01 | g8_k3_c001 | none |

Conclusion: the delta checks are deterministic white-box consistency checks on non-near-zero instances; no binomial or pooled-SE test applies.

### Specified Beta1 Near-Miss Check

| Instance | measured beta1 | closed vtilde | SE | abs(z) | Interpretation |
|---|---:|---:|---:|---:|---|
| g6_k2_c000 | 6.1192 | 6.09646 | 0.0330075 | 0.689 | coverage_noise_band |
| g6_k2_c002 | 8.46581 | 8.44161 | 0.0626619 | 0.386 | coverage_noise_band |

Interpretation rule: |z| below roughly 2.5-3 SE is treated as coverage noise; larger values motivate extraction/model-audit work.

## Dataset v2

Path: `D:/paper fisica 4/finite-shot-vd-sv/results/confirmatory_v2`

### c_SV Equivalence

| Cells within TOST margin | CIs containing zero | mean(c_hat) | median abs(c_hat) | max abs(c_hat) | min margin | median margin | Failures |
|---:|---:|---:|---:|---:|---:|---:|---|
| 29/30 (0.967) | 27/30 | 0.002243 | 0.01626 | 0.05923 | 0.07806 | 0.2666 | g6_k2_c000@p=0.12 |

Conclusion: c_SV remains numerically centered near zero and is evaluated as an equivalence endpoint, not as closed-form point recovery.

### Delta Consistency

| Coefficient | Non-near-zero pass count | Near-zero count | Max abs error (non-near-zero) | Tolerance | Near-zero instances | Failures |
|---|---:|---:|---:|---:|---|---|
| delta_VD | 7/7 (1.000) | 3 | 0.0007798 | 0.01 | g8_k3_c001, g8_k3_c002, g8_k3_c003 | none |
| delta_SV | 9/9 (1.000) | 1 | 0.0003136 | 0.01 | g8_k3_c001 | none |

Conclusion: the delta checks are deterministic white-box consistency checks on non-near-zero instances; no binomial or pooled-SE test applies.

### Specified Beta1 Near-Miss Check

| Instance | measured beta1 | closed vtilde | SE | abs(z) | Interpretation |
|---|---:|---:|---:|---:|---|
| g6_k2_c000 | 6.01703 | 6.09646 | 0.0345015 | 2.302 | coverage_noise_band |
| g6_k2_c002 | 8.31557 | 8.44161 | 0.0626668 | 2.011 | coverage_noise_band |

Interpretation rule: |z| below roughly 2.5-3 SE is treated as coverage noise; larger values motivate extraction/model-audit work.

