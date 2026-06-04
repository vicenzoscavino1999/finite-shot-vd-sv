# E9 Selection Trichotomy

Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.

## Design

- p grid: `0.02` to `0.25` with `10` log-spaced points.
- R grid for observed leading-law signs: `1e-06` to `1e+12` with `900` log-spaced points.
- Method i is the lower-bias method in each cell.
- `certified_crossing` is called with C=0 because E9 tests the leading law itself; hence every leading crossing has eta=0.

## Regime Distribution

| pair | cells | tie | dom_i | dom_j | crossing | match rate | eta<1/2 among crossings | winners |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| vd_vs_sv | 100 | 0 | 73 | 0 | 27 | 1.000 | 1.000 | sv:73, sv_small_R__vd_large_R:27 |
| vd_vs_unmitigated | 100 | 0 | 0 | 0 | 100 | 1.000 | 1.000 | unmitigated_small_R__vd_large_R:100 |
| sv_vs_unmitigated | 100 | 0 | 99 | 0 | 1 | 1.000 | 1.000 | sv:99, unmitigated_small_R__sv_large_R:1 |

## Global Match

Predicted-vs-observed match rate: `1.000` over `300` cells.

## Descriptive Conclusion

The leading-law sign trichotomy matches the observed sign pattern on the resource grid in 1.000 of cells. VD vs unmitigated is classified as a genuine crossing in 100/100 cells. SV vs unmitigated is classified as uniform dominance of the lower-bias method in 99/100 cells and crossing in 1/100 cells. VD vs SV is classified as uniform dominance in 73/100 cells and crossing in 27/100 cells. This is descriptive evidence for O9 and does not enter primary FWER gatekeeping.
