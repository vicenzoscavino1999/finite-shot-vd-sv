# c_VD SE Sensitivity

Status: post_adjudication_sensitivity_only. Not a gate, not an adjudication, not a freeze.

Bootstrap target: N_boot=2000, bootstrap_seed=731029.

Implementation note: the confirmatory WLS slope is linear in the per-B means when the original WLS weights are fixed. The script therefore reports the exact nonparametric bootstrap SE implied by resampling the T estimator replicas at each B, instead of materializing Monte Carlo index draws. This removes bootstrap Monte Carlo noise while preserving the requested replica-resampling variance for the fixed-weight estimator.

Causal interpretation is intentionally open: any residual flag is described as probable miscalibration of the analytic SE under the fitted design / dependent finite-shot structure, not as a closed claim about collinearity alone.

## Replay Self-Check

| Dataset | E2 seed | cells | max abs c_slope diff | max abs analytic SE diff |
|---|---:|---:|---:|---:|
| v1 | 202 | 30 | 0.000e+00 | 4.441e-16 |
| v2 | 10202 | 30 | 0.000e+00 | 4.441e-16 |

## Cell-Level Pooled c_VD

| Dataset | n cells | median SE_boot/SE_analytic | ratio range | analytic chi2_30 | analytic p | bootstrap chi2_30 | bootstrap p | analytic mean(z) | bootstrap mean(z) | Conclusion |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| v1 | 30 | 0.999993 | 0.999993-0.999993 | 49.383 | 0.01436 | 49.384 | 0.01436 | -0.246 | -0.246 | cell-level inconsistency remains under this sensitivity |
| v2 | 30 | 0.999993 | 0.999993-0.999993 | 41.519 | 0.07864 | 41.520 | 0.07863 | 0.024 | 0.024 | bootstrap pooled statistic is consistent; no gate interpretation |

## Instance-Aggregated Pooled c_VD

Aggregation: one z per instance, computed as the unscaled average of its three p-cell z values. This is a conservative dependence check because it does not treat the three p cells as fully independent evidence.

| Dataset | n instances | analytic chi2_10 | analytic p | bootstrap chi2_10 | bootstrap p | analytic mean(instance z) | bootstrap mean(instance z) |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 10 | 5.845 | 0.8281 | 5.845 | 0.8281 | -0.246 | -0.246 |
| v2 | 10 | 4.390 | 0.928 | 4.390 | 0.928 | 0.024 | 0.024 |

## Dataset Conclusions

- v1: the fixed-weight replica bootstrap does not resolve the cell-level pooled flag (p=0.01436); mean(z) remains close to zero. This leaves a residual SE/dependence calibration issue to investigate rather than evidence of a systematic c_VD extraction bias or theory failure.
- v2: the bootstrap pooled statistic is consistent, but the SE ratio does not show inflation of the analytic SE. Treat this as a sensitivity statistic, not a new adjudication.
