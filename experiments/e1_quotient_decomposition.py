"""E1 - VD quotient MSE decomposition (validates P1, P2).

Theory anchor: Thm vd_quotient_certified_v4, eq. vd_mse_certified_v4.
At fixed (p, M=2) the empirical MSE over a B grid is fit by WLS to
``MSE = beta0 + beta1/B + beta2/B^2``.  P1/P2 check (i) intercept beta0 ~ b^2 > 0,
(ii) beta1 ~ v + 2 b c (leading coefficient), (iii) the 1/B^2 term is needed for
VD (Delta AIC > 2) but not for the unmitigated control (beta2 ~ 0).  Per EXP. PLAN
sec. 7.1, beta2 is NOT claimed to equal the certified remainder constant C.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from vd_sv import sv as sv_mod
from vd_sv import vd as vd_mod
from vd_sv.estimators import make_rng, replicate_mse

from ._common import (
    KAPPA_VD,
    aic_gaussian,
    default_model,
    log_grid,
    wls_fit,
    write_csv,
)

P_FIXED = 0.15
M_COPIES = 2
FIELDS = ["noise_strength", "B", "method", "mse", "mse_se",
          "beta0", "beta1", "beta2", "b2_closed_form", "vtilde_closed_form", "delta_aic"]


def run(outdir: str | Path, mode: str = "fast", seed: int = 101) -> Path:
    t = 2000 if mode == "fast" else 20000
    b_grid = log_grid(200, 8000 if mode == "fast" else 30000, 9 if mode == "fast" else 12)
    rng = make_rng(seed)
    m = default_model()
    vdc = m.vd(P_FIXED, M_COPIES)
    u = m.unmitigated(P_FIXED)

    rows = []
    for method in ("vd", "unmitigated"):
        mses, ses = [], []
        for B in b_grid:
            Bi = int(B)
            if method == "vd":
                est = vd_mod.sample_vd_quotient(vdc["N_M"], vdc["D_M"], Bi, t, rng)
            else:
                pz, _acc, val, _a = sv_mod.sv_measurement_data(m, P_FIXED)
                from vd_sv.estimators import sample_direct_mean
                est = sample_direct_mean(pz, val, Bi, t, rng)
            point, se = replicate_mse(est, m.mu_star, n_boot=200, rng=rng)
            mses.append(point)
            ses.append(max(se, 1e-12))
        mses, ses = np.array(mses), np.array(ses)

        # WLS fit MSE ~ beta0 + beta1/B + beta2/B^2
        invB = 1.0 / b_grid
        X2 = np.column_stack([np.ones_like(invB), invB, invB**2])
        X1 = np.column_stack([np.ones_like(invB), invB])
        w = 1.0 / ses**2
        (b0, b1, b2), _cov = wls_fit(X2, mses, w)
        c1, _ = wls_fit(X1, mses, w)
        d_aic = aic_gaussian(mses, X1 @ c1, 2) - aic_gaussian(mses, X2 @ np.array([b0, b1, b2]), 3)

        if method == "vd":
            b2_cf, vt_cf = vdc["b_VD"] ** 2, vdc["v_tilde_VD"]
        else:
            b2_cf, vt_cf = u["b_0"] ** 2, u["v_tilde_0"]

        for B, ms, se in zip(b_grid, mses, ses):
            rows.append({
                "noise_strength": P_FIXED, "B": int(B), "method": method,
                "mse": ms, "mse_se": se,
                "beta0": b0, "beta1": b1, "beta2": b2,
                "b2_closed_form": b2_cf, "vtilde_closed_form": vt_cf, "delta_aic": d_aic,
            })
    return write_csv(Path(outdir) / "e1_quotient_decomposition.csv", FIELDS, rows)


if __name__ == "__main__":
    print(run("results", mode="fast"))
