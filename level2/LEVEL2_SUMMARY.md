# Level 2 Consolidated Summary

Status: Phase B robustness layer. Laws validated EN FORMA under Aer/device simulation; not a coefficient match to Level 1, not a freeze, and not an adjudication.

## Scope And Method

Level 2 is an additive device-simulation layer over the frozen Level 1 analysis. Its role is to check whether the Level 1 laws survive in form under a gate-level Qiskit/Aer model. The reference value is the noiseless Level 2 circuit itself, not the Level 1 exact dense-mixer state. The Level 2 circuit is a realistic Trotterized QAOA state-preparation circuit with `mixer_trotter_steps=1`; the Level 1/Level 2 Trotter gap is reported as informative only.

The noise model is `AerSyntheticThermalReadoutV1`, with Qiskit `2.4.1`, Qiskit Aer `0.17.2`, seed `20260604`, basis gates `u/cx/measure`, depolarizing probabilities `u=0.0002`, `cx=0.006`, and readout matrix `[[0.985,0.015],[0.025,0.975]]`. This is a synthetic Aer snapshot because the installed `[level2]` extra did not expose a `FakeBackendV2` provider.

The high-power ensemble uses the frozen Level 1 firewall instances `g6_k2_c000`-`g6_k2_c004` and `g8_k3_c000`-`g8_k3_c004`. Step 5a uses the exact-rho Option A harness: the noisy state-preparation circuit is simulated once as an exact density matrix per instance, and finite-shot estimators are sampled on top of that rho. Unmitigated and SV are therefore exact device models for state-prep plus readout. VD is represented in two ways: an optimistic state-noise-only `VD M=2` contrast from exact `Tr(rho^2)` and `Tr(O rho^2)`, and a realistic n=6 VD follow-up with the Hadamard/SWAP interferometry circuit, c-SWAP decomposition, gate noise, and readout included.

This asymmetry is deliberate and explicit. The optimistic VD is a best-case benchmark for the distillation mechanism; the realistic n=6 VD resolves whether that best-case window survives the interferometry overhead. For n=8, even optimistic VD loses, so realistic VD would lose a fortiori.

Primary sources for this summary are existing artifacts only:

| Step | Script | CSV | Report |
|---|---|---|---|
| Foundation circuit/noise | `level2/circuits.py`, `level2/noise_model.py` | n/a | `level2/level2_foundation_report.md` |
| Step 2 sampling smoke | `level2/sampling.py` | `level2/level2_sampling_results.csv` | `level2/level2_sampling_report.md` |
| Step 3 VD smoke | `level2/vd.py` | `level2/level2_vd_results.csv` | `level2/level2_vd_report.md` |
| Step 4 folding smoke | `level2/folding.py` | `level2/level2_folding_results.csv` | `level2/level2_folding_report.md` |
| Step 5a exact-rho harness | `level2/highpower.py` | `level2/level2_highpower_results.csv` | `level2/level2_highpower_report.md` |
| Realistic VD n=6 | `level2/vd_realistic_n6.py` | `level2/level2_vd_realistic_n6_results.csv` | `level2/level2_vd_realistic_n6_report.md` |
| Step 5b E5/E7 | `level2/crossing_denominator.py` | `level2/level2_crossing_denominator_results.csv` | `level2/level2_crossing_denominator_report.md` |
| Step 5c folded E8/E12 | `level2/window_efronstein.py` | `level2/level2_window_efronstein_results.csv` | `level2/level2_window_efronstein_report.md` |
| P10 small-noise E8 | `level2/p10_smallnoise.py` | `level2/level2_p10_smallnoise_results.csv` | `level2/level2_p10_smallnoise_report.md` |

## Endpoint Results

### Finite-Shot Laws, Step 5a

The exact-rho high-power table has `210` aggregate rows over 10 frozen instances, 3 methods, and 100 repetitions per cell. Every instance reaches at least `10x B_den`; no budget rows remain.

The observed structure is the expected finite-shot decomposition: method-dependent population bias floors plus a sampling contribution that decreases with B. In the Step 5a large-resource summary, median absolute empirical bias is `0.104397` for unmitigated, `0.0144562` for SV, and `0.0549494` for optimistic VD. Median MSE is `0.0110173` for unmitigated, `0.00036541` for SV, and `0.0332066` for optimistic VD. Thus SV strongly reduces the device-sim bias relative to unmitigated in this ensemble.

For denominator scale, optimistic VD has `D_2` about `0.11`-`0.15` for n=6 (`B_den ~= 2.6e3`-`4.5e3`) and about `0.0067`-`0.0072` for n=8 (`B_den ~= 1.1e6`-`1.25e6`). The n=8 window is therefore an extreme-decoherence, almost-maximally-mixed regime.

### Realistic VD n=6

The realistic n=6 VD follow-up tests the missing overhead: full two-copy Hadamard/SWAP interferometry, decomposed c-SWAP, Aer gate noise, and readout. It uses 64 repetitions per cell and reaches `10x B_den` for all five n=6 instances.

Result: realistic VD does not beat SV in n=6. Bias-floor wins for realistic VD vs SV are `0/5`; large-B MSE wins at paired-sample resource are `0/5`; large-B MSE wins at two-qubit-gate-proxy resource are `0/5`.

The mechanism is visible in the overhead columns. The representative `g6_k2_c000` ratio `abs_bias(VD realistic) / abs_bias(VD optimistic)` is `2.80x`; over all five n=6 instances the median ratio is `3.31x` (range about `2.70x` to `5.50x`). The median absolute-bias delta added by interferometry is `0.0252`. The optimistic VD distillation effect is real in the state-noise-only model, but the device-circuit overhead erases that window in this noise model.

### E5/P7 Denominator Concentration

Step 5b computes exact bad-denominator probabilities for VD as a function of `B/B_den`. The median exact probability `P(D_hat < D/2)` drops sharply at the predicted scale:

| `B/B_den` | median exact bad-denominator probability | median Bernstein bound |
|---:|---:|---:|
| 0.1 | `0.119279` | `0.501173` |
| 0.25 | `0.0311531` | `0.17782` |
| 0.5 | `0.00409866` | `0.0316209` |
| 1 | `9.20795e-05` | `0.000999954` |
| 2 | `6.16929e-08` | `9.99912e-07` |
| 5 | `3.1987e-17` | `9.99901e-16` |
| 10 | `1.76109e-32` | `9.99805e-31` |

This validates P7 in form: below `B_den`, the quotient is high-variance and clip-sensitive; around and above `B_den`, the denominator concentrates rapidly and stays under the Bernstein scale.

### E7/P9 Crossings

Step 5b builds MSE-vs-resource curves using the same resource conventions as Level 1: paired-sample and two-qubit-gate proxy. The selected VD convention is realistic VD for n=6 and optimistic VD for n=8.

Key results:

- SV is the large-resource winner over unmitigated in `10/10` instances.
- Selected VD vs SV under the two-qubit proxy is SV-dominant or large-resource SV-winning in `10/10` instances.
- The n=6 optimistic VD contrast has a VD large-resource window in `2/5` two-qubit-proxy comparisons, but that window disappears when realistic interferometry overhead is included.

This is the central operating-window result. SV dominates the realistic device VD across the ensemble, but the optimistic n=6 contrast shows why this is not because VD distillation is intrinsically weak: the ideal VD window exists in moderate-noise cases and is removed by implementation overhead.

### E8/P10 Window Location

Step 5c first uses global unitary folding on state preparation with `lambda in {1,3,5,7}`. Folding preserves the noiseless reference, but the folded device sweep is not in the Level 1 small-p asymptotic regime because readout floors, base noise, and global depth amplification dominate. The measured folded-noise slopes therefore do not recover the P10 exponents: SV-vs-unmit median slope is `0.062894` vs expected `-1`, and VD-optimal-vs-SV has insufficient positive crossings for a median slope.

The small-noise P10 variant then turns readout off and scales only gate depolarizing errors with `p_cx in {1e-5,2e-5,4e-5,8e-5,1.6e-4}` and `p_u=p_cx/30`. The asymptotic sanity gate passes: unmit/SV bias-linearity is `20/20`, with median slope `0.999147`.

In that asymptotic regime, P10 is recovered in form:

- Central VD-optimal-vs-unmit exponent median: `-1.9536` vs expected `-2`.
- Central median `R^2`: `0.999898`.
- SV-vs-unmit finite-crossing exponent median: `-0.941424` vs expected `-1`, only where positive matched crossings exist.

Absent crossings are reported as absent; they are not forced into the fit.

### E12/P13 Efron-Stein Operational Bound

Step 5c computes the Efron-Stein VD variance bound and asks whether it creates an operational resource point where selected VD beats SV.

For selected VD, finite two-qubit-proxy `R_ES` rows are `0/10`, and selected VD dominates at `R_ES` on an operational scale in `0/10` instances. For the optimistic VD contrast, finite non-operational `R_ES` appears in `2/10` rows; the largest two-qubit-proxy value is `5.23141e+09`. Thus the Efron-Stein bound does not create a practical VD-over-SV window under the Level 2 device-sim conditions.

The ES constants are also large in the device context: selected realistic n=6 constants are about `1.55e6`-`3.93e6`, and selected n=8 optimistic/a-fortiori constants are about `4.83e10`-`6.54e10`. The qualitative P13 message is therefore preserved in form: the certificate is mathematically meaningful, but the operational threshold is not a practical route to VD dominance in this device-sim regime.

## Central Findings

1. SV is operationally dominant over the realistic VD device circuit in this ensemble. This reproduces the Level 1 operating-window narrative in form: symmetry verification is the practical winner under the chosen resource accounting and Aer noise model.

2. VD distillation still helps in the idealized state-noise-only model. The optimistic n=6 VD contrast beats SV in `2/5` moderate-noise n=6 cases, but the realistic interferometry overhead raises the VD bias floor by median `3.31x` and removes those wins.

3. There is no universal winner independent of regime. The ordering depends on noise, denominator scale, size, and resource accounting. n=6 moderate-noise cases reveal an ideal VD window; n=8 is close to maximally mixed with `D_2 ~= 0.007`; realistic VD overhead makes SV dominate operationally.

4. The finite-shot quotient law is visible in the device-sim data. Denominator concentration turns on around `B_den`, matching P7 in form and explaining why low-B VD smoke tests were unstable.

5. P10 scaling is a regime statement. The realistic folded device sweep is outside the asymptotic small-noise regime, but the controlled small-gate-noise variant recovers the expected exponents with high `R^2`.

## Caveats And Limitations

- Level 2 validates laws in form, not Level 1 coefficients. The noiseless reference is the Trotterized Level 2 circuit, and the Level 1/Level 2 Trotter gap is diagnostic only.
- The noise model is synthetic (`AerSyntheticThermalReadoutV1`) because no `FakeBackendV2` provider was available in the installed extra.
- The optimistic VD rows are best-case state-noise-only rows. They omit c-SWAP/interferometry/readout overhead and therefore should not be read as a real device VD estimate. They are useful as a mechanism contrast.
- For selected comparisons, the asymmetry is conservative for SV dominance only when the selected VD already loses with optimistic assumptions, as in n=8. In n=6, the optimistic VD window required the realistic follow-up; that follow-up showed `0/5` VD wins against SV.
- The folded E8/P10 sweep is not asymptotic. It is a device-depth noise-amplification diagnostic, not the small-p analytic knob. The small-noise variant is the appropriate asymptotic P10 check.
- n=8 is an extreme-decoherence regime (`D_2 ~= 0.007`), so conclusions about n=8 are best read as "SV remains stable where VD denominator concentration is severe", not as a claim about all n=8 devices.

## Relation To Level 1

Level 1 remains the frozen coefficient-level and formal-statistical analysis. Level 2 is a Phase B robustness layer that checks whether the same laws appear under a gate-level device simulation:

- P7 appears as denominator concentration around `B_den`.
- P9 appears as operating crossings and SV dominance over realistic VD.
- P10 appears only in the small-noise asymptotic variant, not in the folded realistic sweep.
- P13 appears as an Efron-Stein resource threshold that is not operationally useful for VD dominance here.

This is consistent with the paper framing: Level 1 establishes the theory and coefficients; Level 2 shows that the operating-window mechanism survives realistic circuit structure and exposes the implementation overhead that makes SV dominate.

## Prediction-To-Result Map

| Endpoint | Level 2 result | State | Key number | Source |
|---|---|---|---|---|
| Finite-shot MSE shape | Bias floors plus finite-shot variance are visible; SV reduces bias vs unmitigated. | validated in form | median abs empirical bias: unmit `0.104397`, SV `0.0144562`; median MSE: unmit `0.0110173`, SV `0.00036541` | `level2/level2_highpower_report.md` |
| P7/E5 denominator concentration | Bad-denominator probability collapses around `B_den`. | validated in form | median exact `P(D_hat<D/2)`: `0.119279` at `0.1x`, `9.20795e-05` at `1x`, `1.76109e-32` at `10x` | `level2/level2_crossing_denominator_report.md` |
| P9/E7 crossings | SV dominates selected realistic/a-fortiori VD across the ensemble; ideal VD n=6 window exists but is erased by overhead. | validated in form with operating-window caveat | SV large-resource winner vs unmit `10/10`; selected VD-vs-SV SV-dominant/large-resource SV-winning `10/10`; optimistic n=6 VD window `2/5` | `level2/level2_crossing_denominator_report.md`, `level2/level2_vd_realistic_n6_report.md` |
| P10/E8 folded device sweep | Realistic folded sweep is outside the asymptotic regime. | limitation reported | folded SV-vs-unmit median slope `0.062894` vs `-1`; VD-optimal-vs-SV insufficient crossings | `level2/level2_window_efronstein_report.md` |
| P10/E8 small-noise variant | Direct small gate-noise scaling recovers asymptotic P10 exponents. | validated in form | VD-opt-vs-unmit exponent median `-1.9536`, median `R^2=0.999898`; matched SV-vs-unmit median `-0.941424` where crossings exist | `level2/level2_p10_smallnoise_report.md` |
| P13/E12 Efron-Stein | ES bound does not yield an operational VD-over-SV window. | validated in form as non-operational | selected finite two-qubit-proxy `R_ES` rows `0/10`; optimistic contrast max finite `R_ES=5.23141e+09`; selected VD dominates at `R_ES` in `0/10` | `level2/level2_window_efronstein_report.md` |

## Provenance And Reproducibility

Level 2 is additive and outside the frozen Level 1/Level 1-v2 manifests. The freeze state after these additions is checked by `pap/verify_freeze.py`: v1 is `INTACT_WITH_EXPECTED_DRIFT` and v2 is `INTACT_ZERO_DRIFT`; v2 aggregate hash prefix is `8ca588e73f32`.

Relevant commits for this Level 2 sequence:

| Commit | Meaning |
|---|---|
| `d131602` / `50d56fe` | Initial Level 2 foundation circuit/noise-model work |
| `7da45a5` | Freeze verifier, provenance docs, realistic QAOA depth cleanup |
| `9b6482f` | Step 2 unmitigated/SV sampling smoke |
| `444d0b7`, `98c18c6` | Step 3 VD Hadamard/SWAP smoke and denominator-framing doc fix |
| `b4cec9a` | Step 4 unitary folding foundation |
| `4433f2e`, `61663c4` | Step 5a high-power harness, then exact-rho Option A redo |
| `39d7f0c` | Realistic VD n=6 and 5a framing fix |
| `220812c` | Step 5b E5 denominator concentration + E7 crossings |
| `e270c0b` | Step 5c folded E8 + E12 |
| `aed2ab1` | P10 small-noise asymptotic E8 |

Determinism is documented per step through fixed Aer seeds and stable per-instance/per-method/per-cell seeding. The final Level 2 summary does not run or resample any experiment; it consolidates existing CSVs and reports only.
