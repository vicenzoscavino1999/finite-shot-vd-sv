# Failure Protocol

Status: pap_freeze_ready. This file is a pre-freeze artifact required by
`EXPERIMENTAL_PLAN.md` section 0.1. It defines actions before any confirmatory
adjudication is allowed.

## Verdict Vocabulary

Allowed prediction states are exactly:

- `CONFIRMA`
- `REFUTA`
- `INCONCLUSO`
- `EXPLORATORIO`

No new state may be introduced after PAP freeze.

## Primary Family Gatekeeping

Primary predictions are P1-P6. They are adjudicated in fixed order:

P1 -> P2 -> P3 -> P4 -> P5 -> P6

A `REFUTA` verdict in this chain stops the primary confirmatory claim. Later
analyses may continue only as exploratory diagnostics until the theory, code,
or design is corrected and a new frozen plan is produced.

## Required Actions

| Failure | Primary interpretation | Required action |
| --- | --- | --- |
| P1 fails in Level 1 | Quotient MSE law, simulator, or estimator is misspecified | Stop primary chain; audit quotient formula, density-matrix simulation, WLS design, clipping, and bootstrap. |
| P2 fails in Level 1 | Population bias or intercept extraction is inconsistent | Audit `mu_star`, `mu_VD`, clipping threshold, B range, and intercept CI. |
| P3 fails in Level 1 | `c_VD` formula or numerator/denominator covariance implementation is wrong | Audit Hadamard streams, `sigma_ND`, denominator variance, and quotient-bias fit. |
| P4 fails in Level 1 | SV quotient-bias cancellation is not observed | Audit postselection, `Z=A W`, acceptance denominator, TOST margin, and readout assumptions for non-Level-1 data. |
| P5 or P6 fails in Level 1 | Generator, finite-difference, or beta0 propagation issue | Audit `Delta`, signs of bias, WLS condition, profile likelihood, and propagated CI. |
| P7-P13 fail | Hypothesis break, low power, or operational limit | Report as secondary/descriptive; do not alter the primary chain unless a code bug is exposed. |
| Level 3 cannot resolve crossing | Hardware budget, queue drift, or calibration dominates | Degrade Level 3 to qualitative figure or omit from confirmatory narrative before freeze. |
| Kappa or O-normalization sensitivity reverses conclusion | Real convention dependence | Report every convention; do not select a favorable normalization post hoc. |

## Post-Freeze Change Rule

After PAP freeze, changes to instances, grids, thresholds, clipping, normalization,
or adjudication criteria make the affected analysis exploratory unless a new PAP
hash and freeze manifest are produced.
