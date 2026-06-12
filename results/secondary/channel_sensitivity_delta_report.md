# Depolarizing-Channel Delta Sensitivity

Status: secondary descriptive endpoint (registered robustness check, EXPERIMENTAL_PLAN sec. 10; not primary FWER).

## Design

- Channel: heterogeneous depolarizing with per-qubit c_i ~ Uniform(0.4, 1.3).
- RNG: numpy Generator/PCG64 with base seed `14014` and per-instance stable_seed.
- Richardson h: `1e-05`; absolute-error tolerance: `0.0001`.

## Per-Instance Delta Checks

| instance | delta_VD closed | delta_VD fd | VD abs err | delta_SV closed | delta_SV fd | SV abs err |
|---|---:|---:|---:|---:|---:|---:|
| g6_k2_c000 | -0.0278413 | -0.0278413 | 3.528e-11 | 1.11022e-16 | -4.44089e-11 | 4.441e-11 |
| g6_k2_c001 | -0.0329258 | -0.0329258 | 1.958e-11 | 4.44089e-16 | -5.55112e-11 | 5.551e-11 |
| g6_k2_c002 | -0.0925819 | -0.0925819 | 4.804e-11 | -6.66134e-16 | -7.77156e-11 | 7.771e-11 |
| g6_k2_c003 | 0.0217811 | 0.0217811 | 2.342e-11 | 4.44089e-16 | -1.30451e-10 | 1.305e-10 |
| g6_k2_c004 | -0.0659505 | -0.0659505 | 2.785e-11 | -3.33067e-16 | -1.52656e-11 | 1.527e-11 |
| g8_k3_c000 | -0.0256442 | -0.0256442 | 3.701e-12 | -2.77556e-16 | 2.77556e-12 | 2.776e-12 |
| g8_k3_c001 | -0.00315319 | -0.00315319 | 1.615e-11 | 0 | -3.88578e-11 | 3.886e-11 |
| g8_k3_c002 | -0.0135002 | -0.0135002 | 3.150e-11 | -1.66533e-16 | -2.35922e-11 | 2.359e-11 |
| g8_k3_c003 | -0.0162291 | -0.0162291 | 3.253e-11 | -8.88178e-16 | -5.55112e-12 | 5.550e-12 |
| g8_k3_c004 | -0.00902098 | -0.00902098 | 3.071e-11 | 3.33067e-16 | -5.27356e-11 | 5.274e-11 |

## Descriptive Conclusions

Generator consistency passes 10/10 instances; the maximum Richardson absolute error is 1.305e-10 (VD max 4.804e-11, SV max 1.305e-10).

Empirically on the frozen ensemble under heterogeneous depolarizing channels, delta_SV is zero to machine precision (max |delta_SV| = 8.882e-16), while delta_VD remains generic. This is an ensemble observation, not a theorem.
