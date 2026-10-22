# Level 3 hardware summary

Three instances were run on `ibm_marrakesh` (two with n=6, one with n=8) and analysed from
the archived counts, with readout calibration and a bootstrap over calibration epochs. The
results concern the ordering of the methods; the hardware data are not used to check
coefficients.

## Ordering at the largest budget

All values use `B=8192`.

| instance | n | epochs | SV MSE | unmitigated MSE | VD M=2 MSE | order |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `g6_k2_c000` | 6 | 38 | 0.0102628 | 0.0450005 | 0.0741406 | SV < unmitigated < VD |
| `g6_k2_c001` | 6 | 16 | 0.000549129 | 0.0150867 | 0.0490714 | SV < unmitigated < VD |
| `g8_k3_c000` | 8 | 12 | 0.000154919 | 0.0219267 | 6.78047e+06 | SV < unmitigated < VD |

SV and VD are readout-corrected; the unmitigated estimator uses the raw counts.

The two n=6 instances give the same order. For n=8 the 17-qubit VD circuit has depth
3192 after transpilation and a nearly vanishing readout-corrected denominator, so the VD
quotient blows up while SV stays stable.

An independent replicate of `g6_k2_c000` on `ibm_kingston` gives the same order: with 14
epochs fixed in advance by a stopping rule that did not look at the results, the MSEs are
`0.01028` (SV), `0.0415` (unmitigated) and `0.04894` (VD); adding five later jobs (19
epochs) gives `0.01027`, `0.04142` and `0.05032`. See
`level3/level3_backend_replicate_report.md`.

In all four cases, interferometric overhead and denominator instability remove the VD
advantage seen in the optimistic Level 2 model, and calibrated SV has the lowest MSE.

## QPU budget for the last two Marrakesh instances

This run added 12 epochs to `g6_k2_c001` and 12 epochs for `g8_k3_c000`. It stopped well
below the cap once the ordering was clear, so its number of epochs was not fixed in
advance, unlike the Kingston replicate.

| component | QPU seconds |
| --- | ---: |
| `g6_k2_c001` extension | 168 |
| `g8_k3_c000` | 180 |
| total for this period | 348 |
| 18-minute cap | 1080 |
| 20-minute user cap | 1200 |

IBM usage at the end of the run:

```text
usage_consumed_seconds=348
usage_limit_seconds=10800
usage_remaining_seconds=10452
usage_limit_reached=False
```
