# E11 Le Cam Efficiency

Status: secondary CONSISTENCY CHECK on the toy where the bound is derived (family P7-P13, section 17). NOT an independent empirical test. Additive layer, does not modify any frozen/hashed artifact.

## Design

- p grid: `0.05` to `0.4` with `8` log-spaced points.
- R grid: `10` to `100000` with `9` log-spaced points.
- Toy: one-qubit Bernoulli transcript with E[X]=(1-p)t and hypotheses t=+-h.
- h_opt uses the conservative information constant `I_p^Bern = 4(1-p)^2` via `vd_sv.lecam.ip_bernoulli`.

## Summary

| quantity | min | median | max | pass count |
|---|---:|---:|---:|---:|
| MSE / conservative lower bound | 31.6 | 31.996 | 32 | 72/72 <= 64 |
| MSE / local lower bound | 15.8 | 15.998 | 16 | 72/72 <= 32 |
| Fisher saturation s*J | 1 | 1 | 1 | 72/72 within 1e-12 |

## Descriptive Conclusion

E11 is an arithmetic consistency check on the toy used to derive the Le Cam lower bound. Across the declared grid, the selected transcript's MSE remains within the stated conservative and local ratio limits, and the transcript sampling coefficient saturates the Fisher identity s*J=1 to numerical precision. This is not independent discriminating evidence for the QAOA VD/SV experiments.
