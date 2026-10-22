# What is reproducible, and how it is kept that way

The steps themselves are in [REPRODUCING.md](REPRODUCING.md). This page states what each
level guarantees and the rules that keep those guarantees valid.

## What each level guarantees

| Level | Guarantee | Checked by |
| --- | --- | --- |
| 1 | In the Docker image, a full run reproduces the reference outputs digit for digit; on other platforms, within the registered tolerances. The v2 run reported in the paper is reproduced the same way with the v2 seeds. | `reproducibility/verify_current.py` |
| Plan | The files of both frozen plan versions are unchanged. | `pap/verify_freeze.py` |
| 2 | The committed outputs are those used in the paper, and each step can be rerun with its fixed seeds. Aer results are not compared digit by digit, because they may change with the Aer version. | the tests in `tests/test_level2_*.py` |
| 3 | The archived counts are unchanged, and re-analysing them reproduces the committed summaries. No hardware access is needed. | `scripts/verify_level3_archives.py` |
| Figures | Regenerated from the committed numerical outputs. The PDF bytes can differ (embedded metadata); the plotted data do not. | `scripts/generate_manuscript_figures.py` |

The Level 1 reference package (`reproducibility/reference/`) records the platform,
Python, NumPy and SciPy versions, the deterministic environment variables, the SHA-256
of `requirements.lock`, the random seed of each experiment, and the checksums of every
output.

## Rules for maintainers

- Do not edit files listed in `freeze_manifest.json` or `freeze_manifest_v2.json`.
  A change to the analysis plan needs a new, documented freeze.
- Regenerate `reproducibility/reference/` only inside the Docker image
  (`run_all_current.py --mode full --output reproducibility/reference`), then refresh its
  manifest and checksums with `make reference-manifest`.
- Rewrite the Level 3 summaries only on purpose, with
  `make analysis-from-hardware-update`; the archived counts themselves are never changed.
- After any change, run `python pap/verify_freeze.py` with a clean `git status` and
  confirm the v2 verdict `INTACT_ZERO_DRIFT`.
