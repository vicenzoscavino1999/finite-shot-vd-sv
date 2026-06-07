# Level 2 Step 3 VD M=2

Status: validacion EN FORMA, no matcheo de coeficientes de Nivel 1. Additive Phase B smoke/foundation layer; not a freeze and not an adjudication.

## Scope

- Method: VD M=2 via separate Hadamard/SWAP numerator and denominator circuits.
- Instance: `g6_k2_c000` only, matching Level 2 Step 2.
- Circuit depth: realistic Level 2 QAOA with `mixer_trotter_steps=1`.
- Reference: noiseless Level 2 value of the same realistic circuit.
- Not implemented here: M>2, folding, ensemble run, Level 2 E5/E7/E8/E12, hardware.

## Noiseless Cross-Check

- Cross-check shots: `4096`.
- `D_hat`: `1`; expected `1` for a pure noiseless state.
- `N_hat`: `-0.242161`.
- `N_hat / max(D_hat, 0.5)`: `-0.242161`.
- `mu_ideal_L2`: `-0.243432`.
- Absolute noiseless error: `0.00127073`.

## Denominator Clip

- Noisy denominator reference shots: `1024`.
- Noisy implementation denominator reference: `0.138672`.
- Clip rule: `max(D_hat, 0.5 * D_impl_reference)`.
- Clip value used: `0.0693359`.
- Rationale: this is the Level 2 implementation analogue of the Level 1 clipped quotient `max(D_hat, 0.5*D_M)`. The noisy c-SWAP implementation has its own population denominator, which is not the pure-state noiseless value 1.

## Resource Accounting

- System qubits: `6`.
- VD circuit qubits: `13` (`2n+1`).
- Numerator/denominator split: `B` numerator shots and `B` denominator shots per repetition.
- Raw Hadamard calls per repetition: `2B`.
- Decomposed c-SWAP layer CX count: `48`.
- Numerator circuit CX count: `242`.
- Denominator circuit CX count: `242`.
- Paired-sample kappa from E7 sensitivity: `1`.
- Two-qubit-gate-proxy kappa from E7 sensitivity: `14`.

## Shape Summary

| B | bias | variance | MSE | var*B | mean N | mean D | mean clipped D | R paired | R two-qubit proxy |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 0.279696 | 0.000332014 | 0.0783957 | 0.0424978 | 0.00645283 | 0.164062 | 0.164062 | 128 | 1792 |
| 256 | 0.352225 | 0.0474356 | 0.14778 | 12.1435 | 0.0059317 | 0.0898438 | 0.10498 | 256 | 3584 |
| 512 | -0.0341246 | 0.0313023 | 0.0168156 | 16.0268 | -0.0228922 | 0.0703125 | 0.0932617 | 512 | 7168 |

## Step 2 Context

- Step 2 context B: `8192`.
- Unmitigated abs bias from Step 2: `0.18383`.
- SV mitigated abs bias from Step 2: `0.0801161`.
- Raw SV postselection diagnostic abs bias from Step 2: `0.0842971`.

## Descriptive Conclusion

At B=512, VD has absolute bias `0.0341246`. VD reduces the absolute bias relative to the Step 2 unmitigated context (`0.18383`). The noise of the two-copy interferometric VD circuit is included, so this is a Level 2 form check rather than a Level 1 coefficient recovery claim. With only `2` repetitions, variance estimates and `var*B` are expected to be noisy; the high-power multi-method ensemble run is intentionally deferred.
