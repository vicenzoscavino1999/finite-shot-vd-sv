# PAP Amendment v2: P1 Negative-Control Criterion

Status: pap_freeze_ready.

## Scope

This amendment changes only the negative-control subcriterion inside P1. It does
not change the frozen instance ensemble, QAOA angles, noise channel, grids,
sample sizes, primary family, secondary family, tolerances, clipping rule,
resource normalization, or the P2-P13 criteria.

The original frozen PAP remains the v1 record:

- `PAP_HASH.txt`
- `freeze_manifest.json`
- frozen commit `0814ba796b7d8819e709780ffa01e9f94be7a727`
- PAP hash `31e92d21e0faf32ded9aad84a189fa7ae447afa1fdd9d835f16b74fb8bc443bd`

The v1 confirmatory adjudication is retained in `analysis/adjudication_table.csv`.

## v1 audit finding

P1 required two facts at once:

1. VD needs the `1/B^2` term in the quotient MSE fit.
2. The unmitigated control does not need the `1/B^2` term.

The v1 adjudication applied the frozen rule literally and marked P1 as
`REFUTA`, because the unmitigated control had `Delta AIC > 2` in 4 of 10
instances.

This is a criterion-design failure, not a failure of the Level 1 theory or code.
The unmitigated estimator is a sample mean of the diagonal observable, so its
finite-shot MSE has the exact form

```text
b0^2 + sigma^2 / B
```

with no `1/B^2` term. Any positive AIC selection event for the quadratic term in
the unmitigated control is therefore a statistical false positive. AIC is a model
selection diagnostic with a nonzero false-selection rate under the true linear
model, and that rate is not appropriate as an all-instances negative-control gate
over an ensemble.

The same v1 data show that the principled coefficient test behaves as expected:
for the unmitigated control, the WLS 95% interval for `beta2` contains zero in
10 of 10 instances; for VD, the WLS 95% interval for `beta2` excludes zero in
10 of 10 instances.

## Corrected P1 rule

The v2 P1 rule is:

1. VD `beta1` recovers the closed-form `v + 2bc` within the WLS 95% interval.
2. VD curvature is present: `Delta AIC > 2` for VD and the WLS 95% interval for
   VD `beta2` excludes zero.
3. The unmitigated negative control is linear: the WLS 95% interval for
   unmitigated `beta2` contains zero.

The old requirement "Delta AIC <= 2 for every unmitigated instance" is replaced
by the direct coefficient test "zero lies in the unmitigated `beta2` interval".
This is the direct test of the mathematical null `beta2 = 0` for the control.

The separation in `Delta AIC` between VD and the unmitigated control remains a
reported diagnostic, but it is not used as the negative-control gate.

## v2 execution rule

The amended confirmatory run uses the same frozen design and a fresh, separately
tracked RNG policy:

- `reproducibility/config/rng_policy_v2.yaml`

The v2 run is written to `results/confirmatory_v2/` and adjudicated into
`analysis/adjudication_table_v2.csv`. The v2 freeze is recorded separately in:

- `PAP_HASH_v2.txt`
- `freeze_manifest_v2.json`

The v1 hash files are not overwritten.
