# Level 2 Step 4 Gate Folding

Status: foundation de amplificacion de ruido para E8; validacion EN FORMA. Additive Phase B smoke layer; not a freeze and not an adjudication.

## Scope

- Folding type: global unitary folding on the realistic QAOA state-prep circuit.
- Map: `U -> U (U^dagger U)^k`, with `lambda = 2k + 1`.
- Folded object: state-prep QAOA only. VD c-SWAP/interferometry is not folded here.
- Instance: `g6_k2_c000` only.
- Not implemented here: E5, E7, E8, E12, hardware, or high-power multi-method ensemble.

## Noiseless Invariance Cross-Check

- `mu_ideal_L2`: `-0.243431939047`.
- Max `|mu_noiseless_folded - mu_ideal_L2|`: `2.609e-15`.
- Tolerance: `1.0e-10`.
- Interpretation: folding preserves the logical unitary before noise, as required by unitary folding.

## Noisy Amplification

- Noisy bias is monotone non-decreasing in `lambda`: `True`.
- CX count strictly grows with `lambda`: `True`.
- The noisy population estimate is computed with Aer density-matrix gate noise plus the configured tensorized readout error. This avoids finite-shot noise in the foundation check; high-power sampled runs are deferred.

| lambda | k | CX | depth | mu noiseless | noisy estimate | bias | abs bias | bias-only MSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 97 | 210 | -0.243431939 | -0.0605015447 | 0.182930394 | 0.182930394 | 0.0334635292 |
| 3 | 1 | 291 | 630 | -0.243431939 | -0.00758047963 | 0.235851459 | 0.235851459 | 0.0556259109 |
| 5 | 2 | 485 | 1050 | -0.243431939 | 0.00646908916 | 0.249901028 | 0.249901028 | 0.0624505239 |

## Descriptive Conclusion

The folded circuits leave the noiseless reference invariant while increasing the decomposed CX count and the noisy unmitigated bias. This validates the Level 2 noise-amplification mechanism in form. The folding parameter `lambda` is the device-simulation analogue of the Level 1 noise-strength sweep `p`; it enables the later Step 5 E8/window-location sweep without selecting new instances or changing frozen artifacts.

Runtime for this smoke run: `5.366` seconds.
