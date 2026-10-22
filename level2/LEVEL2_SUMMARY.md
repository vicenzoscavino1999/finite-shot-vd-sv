# Level 2 summary

Level 2 asks whether the finite-shot laws checked exactly at Level 1 still hold in form
under a gate-level Qiskit/Aer simulation. This page collects the results reported in the
paper from the committed CSVs and reports; it does not rerun anything.

## Model

- **Circuit.** Trotterized QAOA state preparation (`mixer_trotter_steps=1`) on the ten
  Level 1 instances `g6_k2_c000` to `g6_k2_c004` and `g8_k3_c000` to `g8_k3_c004`. The
  reference value is the noiseless Level 2 circuit, not the exact Level 1 state; the gap
  between the two is reported but not used.
- **Noise.** `AerSyntheticThermalReadoutV1`: thermal relaxation and depolarizing errors on
  every gate (depolarizing probabilities `u=0.0002`, `cx=0.006`) and readout errors
  (matrix `[[0.985,0.015],[0.025,0.975]]`). It is synthetic rather than a snapshot of a
  specific IBM backend; hardware is tested directly at Level 3. Qiskit `2.4.1`, Qiskit Aer
  `0.17.2`, basis gates `u/cx/measure`, seed `20260604`.
- **Sampling.** The noisy state is simulated once per instance as an exact density
  matrix, and finite-shot estimators are sampled from it. The unmitigated estimator uses
  the raw counts, so its readout error is not corrected; SV is readout-corrected before
  postselection. The SV-versus-unmitigated gap therefore includes the readout correction.
- **VD.** Two versions. The *optimistic* VD (`M=2`) uses the exact `Tr(rho^2)` and
  `Tr(O rho^2)` of the noisy state, with no circuit overhead: a best case for the
  distillation mechanism. The *realistic* VD (n=6 only) runs the Hadamard/SWAP
  interferometry circuit with decomposed c-SWAP, gate noise and readout. For n=8 the
  optimistic VD already loses to SV, so the realistic one would lose a fortiori. *Selected
  VD* means realistic VD for n=6 and optimistic VD for n=8.

## Files

| Part | Script | CSV | Report |
| --- | --- | --- | --- |
| Circuit and noise model | `level2/circuits.py`, `level2/noise_model.py` | n/a | `level2/level2_foundation_report.md` |
| Sampling check | `level2/sampling.py` | `level2/level2_sampling_results.csv` | `level2/level2_sampling_report.md` |
| VD circuit check | `level2/vd.py` | `level2/level2_vd_results.csv` | `level2/level2_vd_report.md` |
| Unitary folding | `level2/folding.py` | `level2/level2_folding_results.csv` | `level2/level2_folding_report.md` |
| Exact-density-matrix sampling | `level2/highpower.py` | `level2/level2_highpower_results.csv` | `level2/level2_highpower_report.md` |
| Realistic VD, n=6 | `level2/vd_realistic_n6.py` | `level2/level2_vd_realistic_n6_results.csv` | `level2/level2_vd_realistic_n6_report.md` |
| Denominator concentration and crossings (E5, E7) | `level2/crossing_denominator.py` | `level2/level2_crossing_denominator_results.csv` | `level2/level2_crossing_denominator_report.md` |
| Folded window location and Efron-Stein (E8, E12) | `level2/window_efronstein.py` | `level2/level2_window_efronstein_results.csv` | `level2/level2_window_efronstein_report.md` |
| Small-noise window location (E8) | `level2/p10_smallnoise.py` | `level2/level2_p10_smallnoise_results.csv` | `level2/level2_p10_smallnoise_report.md` |

## Results

### Finite-shot laws

The exact-density-matrix runs have `210` aggregate rows (10 instances, 3 methods, 100
repetitions per cell), and every instance reaches at least `10 B_den`. The MSE shows the
expected structure: a method-dependent bias floor plus a sampling term that decreases
with `B`. Median absolute bias is `0.104397` (unmitigated), `0.0144562` (SV) and
`0.0549494` (optimistic VD); median MSE is `0.0110173`, `0.00036541` and `0.0332066`.

The denominator differs strongly between sizes: `D_2` is about `0.11` to `0.15` for n=6
(`B_den` about `2.6e3` to `4.5e3`) and about `0.0067` to `0.0072` for n=8 (`B_den` about
`1.1e6` to `1.25e6`), so n=8 is close to maximally mixed.

### Realistic VD, n=6

With 64 repetitions per cell, all five n=6 instances reach `10 B_den`. Realistic VD never
beats SV: bias-floor wins `0/5`, large-B MSE wins at paired-sample resource `0/5`, and
large-B MSE wins under the two-qubit-gate proxy `0/5`. The interferometry raises the VD
bias by a factor `2.80` for `g6_k2_c000` and by a median `3.31` over the five instances
(range `2.70` to `5.50`); the median added absolute bias is `0.0252`.

### Denominator concentration (E5, P7)

Median exact probability of a bad denominator, `P(D_hat < D/2)`, against `B/B_den`:

| `B/B_den` | exact probability | Bernstein bound |
| ---: | ---: | ---: |
| 0.1 | `0.119279` | `0.501173` |
| 0.25 | `0.0311531` | `0.17782` |
| 0.5 | `0.00409866` | `0.0316209` |
| 1 | `9.20795e-05` | `0.000999954` |
| 2 | `6.16929e-08` | `9.99912e-07` |
| 5 | `3.1987e-17` | `9.99901e-16` |
| 10 | `1.76109e-32` | `9.99805e-31` |

Below `B_den` the quotient is unstable and often clipped; above it the denominator
concentrates quickly, below the Bernstein bound.

### Crossings (E7, P9)

The MSE-versus-resource curves use the Level 1 resource conventions (paired sample and
two-qubit-gate proxy).

- SV is the large-resource winner over unmitigated in `10/10` instances.
- Selected VD versus SV is SV-dominant or SV-winning at large resource in `10/10`
  instances under the two-qubit-gate proxy.
- The optimistic n=6 VD has a large-resource window over SV in `2/5` comparisons; it
  disappears once the interferometry overhead is included.

This is the central Level 2 result: the ideal VD window exists in moderate-noise cases
and is removed by the implementation overhead.

### Window location (E8, P10)

Global unitary folding of the state preparation (`lambda` in `{1,3,5,7}`) amplifies
circuit depth rather than the small noise parameter of the theory, and readout floors and
base noise dominate. The folded SV-versus-unmitigated median slope is `0.062894` against
the predicted `-1`, and optimistic VD versus SV has too few positive crossings for a
slope.

A small-noise variant, added after the folded sweep, switches readout error off and
scales only the gate depolarizing errors (`p_cx` in `{1e-5,2e-5,4e-5,8e-5,1.6e-4}`,
`p_u = p_cx/30`). Bias is linear in the noise scale in `20/20` cases (median slope
`0.999147`), so this is the small-noise regime. There:

- optimistic VD versus unmitigated has median exponent `-1.9536` (predicted `-2`),
  median `R^2 = 0.999898`;
- SV versus unmitigated has a fit only in the `2/10` instances with positive crossings,
  with exponents `-0.99` and `-0.89` (median `-0.941424`, predicted `-1`).

### Efron-Stein threshold (E12, P13)

The Efron-Stein bound gives no practical VD-over-SV operating point. Selected VD has a
finite two-qubit-gate-proxy `R_ES` in `0/10` instances and dominates at `R_ES` in `0/10`;
the optimistic VD reaches a finite `R_ES` in `2/10` rows, the largest being
`5.23141e+09`. The constants are large: about `1.55e6` to `3.93e6` for realistic n=6 and
`4.83e10` to `6.54e10` for the n=8 optimistic rows.

## Summary by prediction

| Prediction | Level 2 result | Status | Key numbers | Source |
| --- | --- | --- | --- | --- |
| Finite-shot MSE shape | bias floors plus decreasing sampling term | in form | median bias `0.104` / `0.0145` / `0.0549`; median MSE `0.0110` / `3.65e-4` / `0.0332` (unmitigated / SV / optimistic VD) | `level2_highpower_report.md` |
| P7, denominator concentration | bad-denominator probability collapses around `B_den` | in form | `0.119` at `0.1 B_den`, `9.2e-5` at `B_den`, `1.8e-32` at `10 B_den` | `level2_crossing_denominator_report.md` |
| P9, crossings | SV beats selected VD; the ideal n=6 window is removed by overhead | in form | `10/10`, `10/10`, optimistic window `2/5` | `level2_crossing_denominator_report.md`, `level2_vd_realistic_n6_report.md` |
| P10, folded sweep | outside the small-noise regime | not tested by this sweep | median slope `0.063` against `-1` | `level2_window_efronstein_report.md` |
| P10, small-noise variant (added afterwards) | exponents recovered | in form | `-1.95` (VD), `-0.99` and `-0.89` (SV, 2/10) | `level2_p10_smallnoise_report.md` |
| P13, Efron-Stein | no practical VD-over-SV point | in form | selected finite `R_ES` `0/10`; optimistic max `5.2e9` | `level2_window_efronstein_report.md` |

## Limits

- Level 2 checks the form of the laws, not the Level 1 coefficients.
- The optimistic VD omits all circuit overhead; it is a contrast for the distillation
  mechanism, not a device estimate. Where it already loses (n=8), the conclusion holds a
  fortiori; where it wins (n=6), the realistic circuit settles the comparison (`0/5`).
- n=8 has `D_2` about `0.007`, a strongly decohered regime; the n=8 results say that SV
  stays stable where the VD denominator is tiny, not more.

## Provenance

Level 2 is not part of the frozen analysis plan; after these additions,
`pap/verify_freeze.py` still reports v1 `INTACT_WITH_EXPECTED_DRIFT` and v2
`INTACT_ZERO_DRIFT` (v2 hash prefix `8ca588e73f32`). Each step uses fixed Aer seeds and
stable per-instance, per-method and per-cell seeds.

| Commit | Change |
| --- | --- |
| `d131602`, `50d56fe` | circuit and noise model |
| `7da45a5` | freeze verifier, provenance notes, QAOA depth cleanup |
| `9b6482f` | sampling check (unmitigated, SV) |
| `444d0b7`, `98c18c6` | VD Hadamard/SWAP check |
| `b4cec9a` | unitary folding |
| `4433f2e`, `61663c4` | exact-density-matrix sampling |
| `39d7f0c` | realistic VD, n=6 |
| `220812c` | denominator concentration and crossings (E5, E7) |
| `e270c0b` | folded window location and Efron-Stein (E8, E12) |
| `aed2ab1` | small-noise window location (E8) |
