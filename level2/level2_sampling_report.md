# Level 2 Step 2 Sampling

Status: Phase B additive validation. Laws validated EN FORMA, not matched to Level 1 coefficients.

## Scope

- Circuit: realistic Level 2 QAOA depth with `mixer_trotter_steps=1`.
- Reference: noiseless Level 2 statevector of that same circuit.
- Methods: direct-Z unmitigated and readout-mitigated SV only.
- Not implemented here: VD Hadamard tests, gate folding, readout-mitigation variants, Level 2 E5/E7/E12.

## Readout Calibration

- Calibration shots per prepared state: `20000`.
- Max absolute calibration error vs configured matrix: `0.0016`.
- Configured readout matrix: `[[0.985, 0.015], [0.025, 0.975]]`.
- Mitigation: tensorized assignment inversion on the full distribution, followed by clipping negative quasi-probabilities to zero and renormalizing. Postselection is applied after mitigation.

## Raw Postselection Contamination

- False-accept mean over non-sector states: `0.03807`.
- False-accept max over non-sector states: `0.073471`.
- False-reject mean over sector states: `0.105637`.
- False-reject max over sector states: `0.108107`.
- Mitigated SV acceptance reference: `0.590989`.

## Shape Summary

| method | B | bias | variance | MSE | var*B | acceptance | fit floor | fit slope | fit R2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sv_mitigated | 512 | 0.0761667 | 0.000244599 | 0.00602558 | 0.125235 | 0.585048 | 0.00612486 | 0.151564 | 0.888791 |
| sv_mitigated | 2048 | 0.0786392 | 9.24632e-05 | 0.00626888 | 0.189365 | 0.587669 | 0.00612486 | 0.151564 | 0.888791 |
| sv_mitigated | 8192 | 0.0801161 | 1.71011e-05 | 0.00643427 | 0.140092 | 0.581328 | 0.00612486 | 0.151564 | 0.888791 |
| sv_raw_postselect_diagnostic | 512 | 0.0804549 | 0.000225638 | 0.00667983 | 0.115527 | 0.548014 | 0.0068003 | 0.138717 | 0.899187 |
| sv_raw_postselect_diagnostic | 2048 | 0.0827588 | 8.38296e-05 | 0.00692587 | 0.171683 | 0.549357 | 0.0068003 | 0.138717 | 0.899187 |
| sv_raw_postselect_diagnostic | 8192 | 0.0842971 | 1.574e-05 | 0.00712043 | 0.128942 | 0.543986 | 0.0068003 | 0.138717 | 0.899187 |
| unmitigated | 512 | 0.182713 | 0.000395142 | 0.0337463 | 0.202313 | 1 | 0.0333685 | 0.140228 | 0.830338 |
| unmitigated | 2048 | 0.181567 | 5.92236e-05 | 0.0330209 | 0.12129 | 1 | 0.0333685 | 0.140228 | 0.830338 |
| unmitigated | 8192 | 0.18383 | 1.18508e-05 | 0.0338044 | 0.097082 | 1 | 0.0333685 | 0.140228 | 0.830338 |

## Descriptive Conclusion

At B=8192, `sv_mitigated` has absolute bias `0.0801161` versus unmitigated `0.18383`. The raw postselection diagnostic bias is `0.0842971`, showing why readout mitigation before postselection is part of the Level 2 workflow. The empirical variances decrease with B in the reported sweep, while fitted MSE floors remain method-dependent bias floors under the Aer noise model.
