# Level 3 Hardware Robustness Summary

Status: additive hardware robustness layer complete across three frozen
instances: two n=6 instances and one n=8 instance on `ibm_marrakesh`.

This summary consolidates existing archive-only analyses. It is a qualitative
hardware feasibility and robustness result with calibrated readout, not a
coefficient-validation result.

## Budget

The current IBM usage period started at zero seconds. This run added 12 epochs
to `g6_k2_c001` and 12 epochs for `g8_k3_c000`.

| component | QPU seconds |
|---|---:|
| `g6_k2_c001` extension | 168 |
| `g8_k3_c000` | 180 |
| current-period total | 348 |
| 18 minute cap | 1080 |
| 20 minute user cap | 1200 |

Final IBM usage query:

```text
usage_consumed_seconds=348
usage_limit_seconds=10800
usage_remaining_seconds=10452
usage_limit_reached=False
```

The run stopped far below the cap because the ordering was already clear.

## Largest-B Ordering

All values below use `B=8192` and cluster bootstrap over calibration epochs.

| instance | n | epochs | SV MSE | unmitigated MSE | VD M=2 MSE | largest-B order |
|---|---:|---:|---:|---:|---:|---|
| `g6_k2_c000` | 6 | 38 | 0.0102628 | 0.0450005 | 0.0741406 | SV < unmitigated < VD |
| `g6_k2_c001` | 6 | 16 | 0.000549129 | 0.0150867 | 0.0490714 | SV < unmitigated < VD |
| `g8_k3_c000` | 8 | 12 | 0.000154919 | 0.0219267 | 6.78047e+06 | SV < unmitigated < VD |

SV dominates in all three hardware instances, spanning n=6 and n=8. VD is
degraded by denominator concentration and implementation overhead in all three.

## Interpretation

The n=6 results show that SV dominance is not a single-instance artifact:
`g6_k2_c000` and `g6_k2_c001` both give the same qualitative order after
multi-epoch cluster-bootstrap analysis.

The n=8 result is more severe. The 17-qubit VD M=2 circuit has depth 3192 after
transpilation and an extremely small readout-mitigated denominator. This makes
the VD quotient unstable and produces huge MSE, while SV remains stable and
strongly improves over the unmitigated estimator.

This confirms the Level 3 qualitative story: calibrated SV is the practical
hardware winner in the tested QAOA instances; realistic VD overhead and
denominator instability erase the optimistic VD window on hardware. These are
form/robustness/factibility claims only, not hardware validation of analytic
coefficients.
