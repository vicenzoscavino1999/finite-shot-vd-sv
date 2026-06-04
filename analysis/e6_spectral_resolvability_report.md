# E6 Spectral Resolvability Diagnostic

Status: post_E6_diagnostic_only. Not a gate, not an adjudication, not a freeze.

This diagnostic leaves E6 and all frozen artifacts unchanged. It checks whether the pre-frozen lambda2 gap criterion used for E6 selection also provides the lambda2-vs-lambda3 isolation needed for a clean single-exponential copy-leakage regime.

## Existing E6 Selection

| instance | selected p | frozen relative gap (lambda1-lambda2)/lambda1 | lambda2 | lambda3 | (lambda2-lambda3)/lambda2 | lambda3/lambda2 | isolation status |
|---|---:|---:|---:|---:|---:|---:|---|
| g8_k3_c000 | 0.01 | 0.994 | 0.00612842 | 0.00598407 | 0.024 | 0.976 | near-degenerate |

Interpretation: the frozen criterion confirms lambda1 dominance over lambda2. P8 additionally needs the subdominant leakage to be effectively single-mode, which is probed by lambda2 isolation from lambda3.

## Candidate Instance Representative p Values

B path for M*(B): 1e+02, 1e+04, 1e+06, 1e+08, 1e+10, 1e+12.

| p | lambda1 | lambda2 | lambda3 | lambda4 | lambda3/lambda2 | lambda4/lambda2 | lambda2 isolation gap | M_max | predicted slope | M*(B) path | unique M* |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 0.01 | 0.949709 | 0.00612842 | 0.00598407 | 0.00545943 | 0.976 | 0.891 | 0.024 | 133 | 0.0981389 | 2, 2, 2, 2, 2, 2 | 1 |
| 0.099121 | 0.597778 | 0.0459338 | 0.0402211 | 0.0378584 | 0.876 | 0.824 | 0.124 | 13 | 0.162308 | 2, 2, 2, 2, 2, 2 | 1 |
| 0.25 | 0.268701 | 0.0734422 | 0.0619542 | 0.0445739 | 0.844 | 0.607 | 0.156 | 5 | 0.191479 | 2, 2, 2, 3, 3, 3 | 2 |

## Ensemble-Wide Isolation Summary

Diagnostic isolation threshold: `(lambda2-lambda3)/lambda2 >= 0.1`. This threshold is not a frozen gate; it is a scale-matched diagnostic for the missing theorem precondition.

| scope | rows | isolated rows | min gap | median gap | max gap | best row |
|---|---:|---:|---:|---:|---:|---|
| full frozen lambda2 table | 240 | 227 | 0.024 | 0.367 | 0.760 | g8_k3_c001@p=0.173205 gap=0.760 |
| E6 candidate `g8_k3_c000` | 24 | 11 | 0.024 | 0.083 | 0.156 | g8_k3_c000@p=0.25 gap=0.156 |

## Conclusion

The E6 not_resolvable result is best explained as an operational-regime issue, not as a primary theory/code failure. The frozen selection rule optimized `(lambda1-lambda2)/lambda1`, but the clean P8 slope requires lambda2 to be isolated from lambda3. For the selected E6 p, lambda3 is close to lambda2, and M*(B) does not traverse enough copy numbers to estimate the predicted logarithmic slope. Higher p values improve lambda2 isolation somewhat, but the compact B path still shows at most a small number of integer steps.

Recommended framing: report P8 as a secondary descriptive endpoint that is not resolvable for the frozen E6 selection because the chosen row satisfies the frozen lambda1-dominance criterion but not the stronger lambda2-isolation condition. The ensemble-wide table is diagnostic only; using it to reselect an instance or p after observing E6 would be exploratory. A clean demonstration of the P8 law would require a separate toy/supplemental example with deliberately isolated lambda2, marked as illustrative rather than confirmatory.

Linked E6 output: `D:/paper fisica 4/finite-shot-vd-sv/results/secondary/e6_copy_log_scale_report.md`.
