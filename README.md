# Finite-Shot Operating Windows for VD and SV — reproduction package

Reproduction package for the numerical experiments accompanying the paper
*Finite-Shot Operating Windows for Virtual Distillation (VD) and Symmetry
Verification (SV)*.  This is the **Phase A (Level 1 white-box) MVP**: the exact
density-matrix core that carries the paper's coefficient-validation claims
(`delta_VD`, `delta_SV`, `c_SV = 0`) and the certified crossing.

> **Pre-analysis-plan status.** `EXPERIMENTAL_PLAN.md` is a pre-registered
> pre-analysis plan (PAP). It is frozen under the SHA-256 value recorded in
> `PAP_HASH.txt`, together with the required `[PRE-CONGELADO]` artifacts in
> `freeze_manifest.json`. Confirmatory adjudication of P1-P13 starts from this
> frozen design; reference outputs already in the repository are reproduction
> fixtures unless explicitly promoted through the adjudication table.

## What this reproduces

The Level 1 core is **plain NumPy/SciPy — no Qiskit**. A skeptical reviewer can
check that the closed-form coefficients and the certified crossing match the
theory without any quantum-cloud account.

| Experiment | Predictions | Theory anchor | Output |
| --- | --- | --- | --- |
| E1 quotient MSE decomposition | P1, P2 | `vd_quotient_certified_v4` | `e1_quotient_decomposition.csv` |
| E2 `c_SV = 0` vs `c_VD != 0` | P3, P4 | `vd_c_v4`, `sv_quotient_bias_zero_v14` | `e2_c_sv_zero.csv` |
| E3 `delta_VD` from generator | P5 | `vd_delta_generator` | `e3_delta_vd_generator.csv` |
| E4 `delta_SV` first order | P6 | `sv_delta_precise` | `e4_delta_sv_firstorder.csv` |
| E5 denominator concentration | P7 | `denom_bernstein_v4` | `e5_denominator_concentration.csv` |
| E7 crossing diagnostic | P9 | `certified_crossing` | `e7_certified_crossing.csv` |
| E7 resource/O sensitivity | §10 | `resource_normalization_v13` | `e7_resource_observable_sensitivity.csv` |

## Quick start

```bash
pip install -e .                      # Level 1 core (numpy, scipy, pyyaml)
python reproducibility/run_all.py --mode fast    # generate Level 1 outputs (~2 s)
python reproducibility/verify.py --reference reproducibility/reference/
pytest tests/ -q                      # scientific-correctness + determinism + verify guard
```

With `make` (Docker / Linux is the supported path):

- `make reproduce-level1` — recompute the white-box coefficient & crossing claims, then verify.
- `make reproduce-fast` — small deterministic subset (minutes), verify.
- `make reproduce-full` — recompute all Level 1 (and, in Phase B, Level 2) outputs.
- `make verify` — schema + numerical verification against `reproducibility/reference/`.
- `make test` — run the test suite.

The official environment is the Docker image (`Dockerfile`, `linux/amd64`) with
pinned BLAS/OpenMP thread counts for tight numerical tolerances. Native
Windows/macOS is fine for development.

## Key scientific results (fast reference mode)

- **E1/P1–P2** — VD MSE intercept `beta0 ≈ b^2`; `beta1 ≈ v + 2bc`; the `1/B^2`
  curvature is needed for VD (ΔAIC ≈ 19 > 2) but not for the unmitigated control
  (ΔAIC < 0). `beta2` is **not** claimed to equal the certified remainder `C`.
- **E2/P3–P4** — `c_SV = 0` exactly; `c_VD` matches `mu_VD (1-D^2)/D^2`. The
  confirmatory full run uses the frozen `T_full=70000` setting fixed by the
  pre-freeze pilot; fast-mode outputs are compact reference checks.
- **E3/P5, E4/P6** — measured `delta_VD`, `delta_SV` slopes match the closed-form
  generators to ~2–4 % (O(p^2) slope-fit truncation).
- **E5/P7** — for the VD cell `(p=0.20, M=3)`, the exact and empirical
  bad-denominator probability drops sharply around `B_den`, and the clipped and
  ordinary quotient tails become indistinguishable above the threshold.
- **E7/P9** — an operational crossing diagnostic for **VD vs unmitigated**: the
  empirical root lies inside the fitted-remainder band (`eta_operational < 1/2`).
  This is not yet the formal certified P9 claim because the Phase-A MVP estimates
  the remainder constant from sampled MSE rather than using a pre-registered
  conservative bound. *Finding:* for this instance family SV uniformly dominates
  VD at operational budgets (selection trichotomy regime II).
- **Sensitivity (§10)** — the VD-vs-unmitigated leading crossing persists under
  four `kappa` definitions and two observable normalizations; `R0` shifts with
  the convention and is reported explicitly rather than hidden.

## Three-level architecture (what is reproducible)

- **Level 1 (here)** — white-box density matrix; coefficients validated; tight,
  deterministic, no Qiskit.
- **Level 2 (Phase B)** — Aer device-simulation; laws validated *in form* only;
  needs the `[level2]` extras.
- **Level 3 (Phase B)** — hardware; **analysis-from-archived-counts only**, the
  device is never re-executed.

## Data policy & licensing

Code is MIT (`LICENSE`). Archived numerical outputs and figures are CC-BY-4.0
(`LICENSE-DATA`). Level 1/2 numerical outputs are recomputable and verifiable;
Level 3 is analysis-reproducible only. See `METHODS.md` for the full methodology.

## Limitations

Figures are regenerated from verified numerical data and are not required to be
bit-identical. Out of scope: GPU reproduction, native Windows/macOS as the
archival path, re-execution of quantum hardware, future unpinned dependency
versions.
