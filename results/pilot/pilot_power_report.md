# Pilot power report

This pre-freeze pilot uses the frozen Level-1 ensemble, declared grids,
white-box Level-1 quantities, and pilot-only RNG streams for the
near-`B_den` kurtosis check. It does not read `results/e*.csv`.

## Design decision

- Mode: `full`.
- Instances: 10.
- Minimum P3 power (`c_VD != 0`): 0.946822.
- Minimum P4 TOST power (`c_SV = 0`): 0.939072.
- Required primary power: 0.9.
- `tau_value`: 0.685349.
- `tau_delta_value`: 0.0003023 (precision_only_not_p5_p6_pass_criterion).
- `delta_abs_floor`: 0.01.
- `delta_consistency_abs_tol`: 0.01.
- Max deterministic delta truncation error: 0.000779778.
- Pilot decisions: `PASS_FOR_FREEZE, PASS_WITH_NEAR_ZERO_INCONCLUSIVE`.
- Total estimated effective shots: 745764000000.
- Total estimated walltime seconds: 9943.52.
- Max required `T_full` for P3/P4 power: 61180.

## Anti-circularity

- `tau_value` is derived from pilot precision plus the pre-registered
  safety factor.
- `tau_delta_value` uses only deterministic Level-1 fit precision:
  regression halfwidth on the declared `p` grid plus the
  pre-registered safety factor. It is not a P5/P6 pass criterion in
  the current white-box route.
- P5/P6 consistency uses `delta_fit_abs_error <= delta_consistency_abs_tol`;
  the tolerance is pre-registered and does not include the observed
  truncation discrepancy.
- P4 TOST margins use `f * |c_VD^white-box|`; they never use observed
  `c_hat` values.
- P5/P6 use the current deterministic Level-1 white-box route for
  `b_VD,inf(p)` and `b_SV(p)`. A finite-shot `beta0` route would require
  bootstrap propagation before freeze.
- Near-zero deltas are not used to exclude or replace instances.

## Near-zero delta policy

Instances marked `INCONCLUSIVE_BY_DESIGN_NEAR_ZERO`: `g8_k3_c001`, `g8_k3_c002`, `g8_k3_c003`.

## Per-instance status

| instance_id | P3 | P4 | VD consistency | SV consistency | P5/VD delta | P6/SV delta | kurtosis | decision |
|---|---|---|---|---|---|---|---|---|
| g6_k2_c000 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_FOR_FREEZE |
| g6_k2_c001 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_FOR_FREEZE |
| g6_k2_c002 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_FOR_FREEZE |
| g6_k2_c003 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_FOR_FREEZE |
| g6_k2_c004 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_FOR_FREEZE |
| g8_k3_c000 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_FOR_FREEZE |
| g8_k3_c001 | PASS | PASS | PASS | PASS | INCONCLUSIVE_BY_DESIGN_NEAR_ZERO | INCONCLUSIVE_BY_DESIGN_NEAR_ZERO | PASS | PASS_WITH_NEAR_ZERO_INCONCLUSIVE |
| g8_k3_c002 | PASS | PASS | PASS | PASS | INCONCLUSIVE_BY_DESIGN_NEAR_ZERO | PASS | PASS | PASS_WITH_NEAR_ZERO_INCONCLUSIVE |
| g8_k3_c003 | PASS | PASS | PASS | PASS | INCONCLUSIVE_BY_DESIGN_NEAR_ZERO | PASS | PASS | PASS_WITH_NEAR_ZERO_INCONCLUSIVE |
| g8_k3_c004 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_FOR_FREEZE |
