# P1 Amendment Audit Summary

Status: completed_after_v2_run.

## v1 result

The original frozen criterion marked P1 as `REFUTA`.

The failure mode was the unmitigated negative-control AIC gate: the unmitigated
control had `Delta AIC > 2` in 4 of 10 instances, even though the unmitigated
estimator is a sample mean whose MSE is mathematically linear in `1/B`.

The v1 post-run audit showed:

- VD `Delta AIC > 2`: 10/10 instances, range 42.247-78.868.
- VD `beta1` closed form in WLS 95% interval: 10/10 instances.
- VD `beta2` WLS 95% interval excludes zero: 10/10 instances.
- Unmitigated `beta2` WLS 95% interval contains zero: 10/10 instances.

This supports the diagnosis that the v1 all-instances AIC gate was a
negative-control criterion flaw, not a failure of the Level 1 theory or code.

## v2 amendment

The v2 amendment replaced the unmitigated AIC gate with a direct coefficient
test:

```text
unmitigated beta2 WLS 95% interval contains zero
```

It also required VD `beta2` to exclude zero, while preserving the original VD
`beta1` recovery and VD `Delta AIC > 2` requirements.

The v2 freeze is recorded in:

- `PAP_HASH_v2.txt`
- `freeze_manifest_v2.json`

## v2 result

The v2 confirmatory run used `reproducibility/config/rng_policy_v2.yaml` and
wrote outputs under `results/confirmatory_v2/`.

P1 is still marked `REFUTA` in `analysis/adjudication_table_v2.csv`.

The v2 P1 details are:

- VD `Delta AIC > 2`: 10/10 instances, range 27.546-88.970.
- VD `beta2` WLS 95% interval excludes zero: 10/10 instances.
- VD `beta1` closed form in WLS 95% interval: 8/10 instances.
- VD `beta0` closed form in WLS 95% interval: 9/10 instances.
- Unmitigated `beta2` WLS 95% interval contains zero: 9/10 instances.

The failed v2 cases were:

- VD `beta1`: `g6_k2_c000`, `g6_k2_c002`.
- VD `beta0`: `g6_k2_c004`.
- Unmitigated `beta2`: `g8_k3_c004`.

Secondary and diagnostic endpoints remain informative:

- P3 diagnostic: 30/30 VD `c_slope` cells pass.
- P4 diagnostic: 29/30 SV TOST cells pass.
- P5 diagnostic: all non-near-zero VD delta cases pass; 3 are near-zero by the
  frozen policy.
- P6 diagnostic: all non-near-zero SV delta cases pass; 1 is near-zero by the
  frozen policy.
- P7 confirms as a secondary denominator-regime endpoint.
- P9 remains secondary and does not confirm under the operational fitted-C band.

## Interpretation

The v2 amendment fixed the specific AIC negative-control flaw, but the fresh-seed
confirmatory run shows that the remaining all-instances coefficient-interval
gates are still too brittle for a clean primary confirmatory chain.

No additional seed retry is justified. The next scientific step is a design-level
audit of the P1/P2 interval construction and ensemble-level adjudication rule,
not another confirmatory rerun.
