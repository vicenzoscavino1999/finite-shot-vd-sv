# METHODS (Phase A / Level 1)

This documents the computational choices for the Level 1 white-box reproduction.
The Phase B archival release expands this to the full 8–12 page target.

## 1. Why a custom density-matrix simulator (not Qiskit/Aer)

Level 1 uses an explicit dense density-matrix implementation so the noise model,
the generator `Delta = L(rho_star)`, the estimator sampling, and the finite-shot
bookkeeping are transparent and fully controlled. This lets the closed-form
coefficients `delta_VD`, `delta_SV`, `c_SV` and the certified crossing be audited
directly. Qiskit/Aer is required only for the Level 2 device-simulation
robustness experiments (Phase B); it is not part of the Level 1 path. Hardware
(Level 3) is a feasibility demonstration whose only reproducible artifact is the
analysis applied to archived counts.

## 2. Instance family — XY-mixer QAOA on a fixed Hamming-weight sector

`n` qubits on a (weighted) ring. Cost `H_C = sum_{(i,j)} w_ij Z_i Z_j` is
Z-diagonal; observable `O = H_C / ||H_C||_inf` (so `||O||_inf = 1`). The XY mixer
`H_M = sum_{(i,j)} (X_i X_j + Y_i Y_j)` preserves total magnetization
`S = sum_i Z_i` (Hamming weight). The QAOA state
`|psi> = prod_l e^{-i beta_l H_M} e^{-i gamma_l H_C} |D^n_k>` (Dicke initial state)
lives in the weight-`k` sector, so `P rho_star P = rho_star` and `P O = O P`
(SV hypothesis). Angles are frozen by minimizing the noiseless `<H_C>` with a
fixed optimizer + seed (`optimize_angles`).

**Sector choice.** We use `k != n/2`. At half-filling `k = n/2` the QAOA state is
invariant under the bit-complement (particle-hole) symmetry `s_i -> -s_i`, which
forces all odd correlators — and hence `delta_VD` and `delta_SV` — to vanish
identically. A non-half-filled sector gives the generic first-order-bias case.

## 3. Noise channels and the generator

Per-qubit product channels at scale `p`, applied via exact Kraus maps so `rho_p`
is exact CPTP:

- amplitude damping (rate `c_ad_i * p`) + dephasing (Z-twirl, rate `c_pd_i * p`) — primary;
- depolarizing (Pauli-twirl) — sensitivity.

`Delta = L(rho_star) = sum_i` (per-qubit Lindblad dissipators) is computed in
closed form and cross-checked by Richardson finite differences
(`assert_delta_consistency`). Rates are **heterogeneous** (per-qubit): with a
Z-diagonal `O` and a fixed sector, homogeneous amplitude damping makes the
within-sector generator proportional to the sector-constant number operator,
cancelling `delta`. Heterogeneous rates (qubit-dependent T1/T2) give the generic
nonzero case.

## 4. Qubit ordering

Big-endian: qubit 0 is the leftmost tensor factor. For basis index `z`,
qubit `i` has value `(z >> (n-1-i)) & 1`; the Hamming weight is the number of `1`
bits. The Qiskit cross-check mapping (Level 2) is the bit reversal of this order.

| n=3 example | z=0b011 → qubits (0,1,2) | weight |
| --- | --- | --- |
| q0=0, q1=1, q2=1 | one excitation pattern | 2 |

## 5. Estimators

- **VD (Hadamard test).** Independent numerator/denominator signs in `{+-1}` with
  means `N_M = Tr(O rho_p^M)`, `D_M = Tr(rho_p^M)` → `sigma_N^2 = 1-N^2`,
  `sigma_D^2 = 1-D^2`, `sigma_ND = 0`. Clipped quotient `N_hat / max(D_hat, D_M/2)`.
  Sampled from binomial counts (memory `O(T)`).
- **SV (Hamming postselection).** Measure in Z, accept correct weight, evaluate
  `O` on accepted bitstrings; clipped `Z_bar / max(A_bar, a/2)`. Sampled from a
  multinomial over the `2^n` outcomes. All shots (accepted + rejected) counted as
  resource.
- **Unmitigated.** Sample mean of `O` in the Z basis.

## 6. Coefficient extraction and adjudication

- `delta_VD = 2 Re <psi| O Q_star Delta |psi>`; `delta_SV = Tr(O P Delta P) - mu_star Tr(P Delta P)`.
- E1 fits `MSE ~ beta0 + beta1/B + beta2/B^2` by WLS (weights from a 200-sample
  bootstrap of the MSE); `beta0 ~ b^2`, `beta1 ~ v + 2bc`; AIC compares the
  quadratic vs linear model. `beta2` is an effective curvature, **not** the
  certified remainder `C`.
- E2 fits `E[mu_hat] - mu_pop ~ c/B + d/B^2` (no intercept); `c` is the quotient-
  bias coefficient. VD: CI excludes 0; SV: `c_SV = 0` exactly.
- E3/E4 fit `b(p) ~ delta*p + kappa*p^2` and compare the slope to the closed form.
- E5 fixes a small-denominator VD cell and sweeps `B/B_den` to compare the exact
  binomial bad-denominator probability, the Bernstein upper bound, the empirical
  clip-activation rate, quotient kurtosis, and deviation from the leading P1 law.
- E7 finds the empirical crossing root of the sampled MSE difference and reports
  a fitted-remainder diagnostic `eta_operational = 4C_fit/(g R0^2)`. This is a
  scale diagnostic, not the formal certified P9 band; the confirmatory run must
  replace `C_fit` with a pre-registered conservative remainder bound.
- The E7 sensitivity table recomputes the leading crossing under four resource
  conventions (`paired_sample`, `hadamard_call`, `two_qubit_gate_proxy`,
  `wall_clock_proxy`) and two observable conventions (`inf`,
  `sector_trace_zero_spectral`). It reports any displacement of `R0` as a
  convention dependence, not as a hidden post-hoc choice.

## 7. Randomness and determinism

All randomness uses `numpy.random.Generator(numpy.random.PCG64(seed))`; per-
experiment seeds are in `reproducibility/config/rng_policy.yaml`. Binomial /
multinomial draws are platform-independent, so seeded outputs are deterministic.
The Docker image pins `PYTHONHASHSEED` and BLAS/OpenMP thread counts so the
density-matrix eigendecompositions are bit-stable.

## 8. Tolerances

Closed-form / deterministic columns use machine-tight tolerances; finite-shot
columns are tight here (deterministic bit-stream) and recalibrated from ≥3
container runs in Phase B (`reproducibility/config/tolerances.yaml`).
