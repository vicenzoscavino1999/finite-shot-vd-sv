# Level 2 P10 Small-Noise Asymptotic E8

Status: EN FORMA; small gate-noise asymptotic variant of E8/P10. Additive Phase B; not a freeze and not a Level 1 formal certificate.

## Scope

- Motivation: Step 5c showed that the realistic folded device-sim sweep is outside the small-noise asymptotic regime because global folding plus readout/base-noise floors mask P10 scaling.
- This variant turns readout off and scales only gate depolarizing errors: `p_cx in {1e-5,2e-5,4e-5,8e-5,1.6e-4}`, with `p_u=p_cx/30`.
- Reference: noiseless Level 2 circuit, so Trotter error is outside the bias being fitted.
- VD is the optimal state-noise-only contrast; realistic VD overhead is orthogonal and was measured separately.

## Asymptotic Sanity Gate

- Unmit/SV bias-linearity PASS rows: `20/20`.
- Median unmit/SV bias slope: `0.999147`.

## P10 Exponents

- Central VD-optimal-vs-unmit exponent median: `-1.9536` vs expected `-2`.
- Central median R2: `0.999898`.
- SV-vs-unmit finite-crossing exponent median: `-0.941424` vs expected `-1` where matched crossings exist.

| instance | pair | resource | expected | measured | R2 | finite R0 pts | status |
|---|---|---|---:|---:|---:|---:|---|
| g6_k2_c000 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.97462 | 0.999976 | 5 | recovers_expected_exponent |
| g6_k2_c000 | sv_vs_unmit | paired_sample | -1.0 |  |  | 0 | insufficient_positive_crossings |
| g6_k2_c000 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.97836 | 0.999982 | 5 | recovers_expected_exponent |
| g6_k2_c001 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.97644 | 0.999979 | 5 | recovers_expected_exponent |
| g6_k2_c001 | sv_vs_unmit | paired_sample | -1.0 |  |  | 0 | insufficient_positive_crossings |
| g6_k2_c001 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.98019 | 0.999985 | 5 | recovers_expected_exponent |
| g6_k2_c002 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.97956 | 0.999984 | 5 | recovers_expected_exponent |
| g6_k2_c002 | sv_vs_unmit | paired_sample | -1.0 |  |  | 0 | insufficient_positive_crossings |
| g6_k2_c002 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.98101 | 0.999986 | 5 | recovers_expected_exponent |
| g6_k2_c003 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.98037 | 0.999985 | 5 | recovers_expected_exponent |
| g6_k2_c003 | sv_vs_unmit | paired_sample | -1.0 | -0.991443 | 0.999989 | 5 | recovers_expected_exponent |
| g6_k2_c003 | vd_optimal_vs_sv | paired_sample | -2.0 |  |  | 0 | insufficient_positive_crossings |
| g6_k2_c004 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.98029 | 0.999985 | 5 | recovers_expected_exponent |
| g6_k2_c004 | sv_vs_unmit | paired_sample | -1.0 |  |  | 0 | insufficient_positive_crossings |
| g6_k2_c004 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.98068 | 0.999986 | 5 | recovers_expected_exponent |
| g8_k3_c000 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.93182 | 0.999816 | 5 | recovers_expected_exponent |
| g8_k3_c000 | sv_vs_unmit | paired_sample | -1.0 |  |  | 0 | insufficient_positive_crossings |
| g8_k3_c000 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.9409 | 0.999863 | 5 | recovers_expected_exponent |
| g8_k3_c001 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.93258 | 0.999821 | 5 | recovers_expected_exponent |
| g8_k3_c001 | sv_vs_unmit | paired_sample | -1.0 |  |  | 1 | insufficient_positive_crossings |
| g8_k3_c001 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.94649 | 0.999888 | 5 | recovers_expected_exponent |
| g8_k3_c002 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.92982 | 0.999805 | 5 | recovers_expected_exponent |
| g8_k3_c002 | sv_vs_unmit | paired_sample | -1.0 |  |  | 0 | insufficient_positive_crossings |
| g8_k3_c002 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.93885 | 0.999854 | 5 | recovers_expected_exponent |
| g8_k3_c003 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.93004 | 0.999806 | 5 | recovers_expected_exponent |
| g8_k3_c003 | sv_vs_unmit | paired_sample | -1.0 |  |  | 0 | insufficient_positive_crossings |
| g8_k3_c003 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.93746 | 0.999846 | 5 | recovers_expected_exponent |
| g8_k3_c004 | vd_optimal_vs_unmit | paired_sample | -2.0 | -1.93011 | 0.999807 | 5 | recovers_expected_exponent |
| g8_k3_c004 | sv_vs_unmit | paired_sample | -1.0 | -0.891406 | 0.998239 | 5 | recovers_expected_exponent |
| g8_k3_c004 | vd_optimal_vs_sv | paired_sample | -2.0 | -1.93772 | 0.999848 | 5 | recovers_expected_exponent |

## Descriptive Conclusion

With readout removed and gate error scaled directly into the small-noise regime, the central VD-optimal-vs-unmit crossing recovers the generic P10 R0~p^-2 scaling in form. Matched SV-vs-unmit crossings recover approximately p^-1 only in the instances where a positive crossing exists; absent crossings are reported as such rather than forced.

Runtime for this analysis: `127.339` seconds.
