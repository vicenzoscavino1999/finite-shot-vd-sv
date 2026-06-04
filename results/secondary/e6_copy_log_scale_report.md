# E6 Copy Log Scale

Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.

## Selection

- Instance: `g8_k3_c000`
- p: `0.01`
- Selection basis: e6_candidate=yes in frozen lambda2_gap_table.csv; selected p with maximum relative_gap for that frozen instance.
- lambda1: `0.949708732481708`
- lambda2: `0.00612841784243526`
- relative_gap: `0.993547`
- D_M floor: `0.001`; M_max: `133`

## P8 Slope

| measured slope | 95% CI | predicted slope | relative error | unique M*(B) | status |
|---:|---:|---:|---:|---:|---|
| -2.03346e-20 | [-2.04622e-18, 2.00555e-18] | 0.0981389 | -1 | 1 | not_resolvable |

The frozen E6 candidate/p is not resolvable for the total MSE curve: the infinite-copy floor is reached within a few copies, so M*(B) does not span enough integers to support the advertised slope regression.

## Theorem Hypothesis Checks

| check | measured slope | predicted slope | relative error | fit n | status |
|---|---:|---:|---:|---:|---|
| copy leakage b_M-b_inf ~ q^M | -5.23154 | -5.04322 | 0.0373406 | 5 | PASS |
| v_tilde_M ~ lambda1^(-2M) | 0.103316 | 0.1032 | 0.00112199 | 132 | PASS |

## D_M Copy Range

| first M | last M | D_M(first) | D_M(last) | observed M*(B) values |
|---:|---:|---:|---:|---|
| 2 | 133 | 0.902149 | 0.00104599 | 2 |

## Descriptive Conclusion

P8 is reported descriptively only. For the frozen gap-selected E6 configuration, the measured slope is -2.03346e-20 versus predicted 0.0981389. The leakage and variance hypothesis checks are shown above; the M*(B) slope should not be promoted to a primary gate or a freeze amendment.
