"""E7 - Operating-window crossing diagnostic (P9 development run).

Theory anchor: Thm certified_crossing, eqs. eta_crossing_condition, crossing_interval.
MSE is sampled over a resource grid R = kappa * B for VD, SV, and the unmitigated
baseline.  The leading indifference budget R0 is computed from the white-box laws;
the empirical crossing R* is the root of the sampled MSE difference.

The current Phase-A MVP reports an *operational* eta diagnostic using a residual
fit for C.  That is useful for scale-setting, but it is not the formal proof
certificate required for confirmatory P9.  A frozen/confirmatory E7 must supply a
pre-registered conservative C bound instead of the fitted constant below.

Note (instance-dependent finding): for this instance family SV uniformly dominates
VD at operational budgets (regime II of the selection trichotomy), so the *operational*
certified crossing is the mitigation-vs-unmitigated window (here VD vs unmitigated),
which is what E7 demonstrates.  The VD<->SV comparison is reported as a trichotomy
classification.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from vd_sv import sv as sv_mod
from vd_sv import vd as vd_mod
from vd_sv.crossing import (
    MethodLaw,
    certified_crossing,
    empirical_crossing,
    fit_remainder_constant,
)
from vd_sv.estimators import make_rng, mse, sample_direct_mean

from ._common import KAPPA_SV, KAPPA_UNMIT, KAPPA_VD, default_model, log_grid, write_csv

P_FIXED = 0.15
M_COPIES = 2
REMAINDER_SOURCE = "fit_from_sampled_mse"
FIELDS = ["noise_strength", "resource_R", "mse_vd", "mse_sv", "mse_unmit",
          "crossing_R_empirical", "crossing_R0_leading", "eta_operational",
          "remainder_C_vd_operational", "remainder_C_unmit_operational",
          "remainder_source", "method_pair"]


def run(outdir: str | Path, mode: str = "fast", seed: int = 707) -> Path:
    t = 4000 if mode == "fast" else 20000
    r_grid = log_grid(50, 8000, 12 if mode == "fast" else 18)
    rng = make_rng(seed)
    m = default_model()
    vdc, svc, u = m.vd(P_FIXED, M_COPIES), m.sv(P_FIXED), m.unmitigated(P_FIXED)
    pz, acc, val, a = sv_mod.sv_measurement_data(m, P_FIXED)

    mse_vd, mse_sv, mse_unmit = [], [], []
    for R in r_grid:
        bv, bs, b0 = max(2, int(R / KAPPA_VD)), max(2, int(R / KAPPA_SV)), max(2, int(R / KAPPA_UNMIT))
        mse_vd.append(mse(vd_mod.sample_vd_quotient(vdc["N_M"], vdc["D_M"], bv, t, rng), m.mu_star))
        mse_sv.append(mse(sv_mod.sample_sv_quotient(pz, acc, val, a, bs, t, rng), m.mu_star))
        mse_unmit.append(mse(sample_direct_mean(pz, val, b0, t, rng), m.mu_star))
    mse_vd, mse_sv, mse_unmit = map(np.array, (mse_vd, mse_sv, mse_unmit))

    # white-box leading laws (resource-normalized)
    b2_vd, s_vd = vdc["b_VD"] ** 2, KAPPA_VD * vdc["v_tilde_VD"]
    b2_u, s_u = u["b_0"] ** 2, KAPPA_UNMIT * u["v_0"]
    c_vd = fit_remainder_constant(r_grid, mse_vd, b2_vd, s_vd)
    c_u = fit_remainder_constant(r_grid, mse_unmit, b2_u, s_u)

    diag = certified_crossing(MethodLaw("vd", b2_vd, s_vd, c_vd),
                              MethodLaw("unmitigated", b2_u, s_u, c_u))
    r_star = empirical_crossing(r_grid, mse_vd, mse_unmit)
    r0 = diag.R0 if diag.R0 is not None else float("nan")
    eta = diag.eta if diag.eta is not None else float("nan")

    rows = [{
        "noise_strength": P_FIXED, "resource_R": float(R),
        "mse_vd": float(mv), "mse_sv": float(ms), "mse_unmit": float(mu),
        "crossing_R_empirical": float(r_star) if r_star is not None else float("nan"),
        "crossing_R0_leading": float(r0), "eta_operational": float(eta),
        "remainder_C_vd_operational": float(c_vd),
        "remainder_C_unmit_operational": float(c_u),
        "remainder_source": REMAINDER_SOURCE,
        "method_pair": "vd_vs_unmitigated",
    } for R, mv, ms, mu in zip(r_grid, mse_vd, mse_sv, mse_unmit)]
    return write_csv(Path(outdir) / "e7_certified_crossing.csv", FIELDS, rows)


if __name__ == "__main__":
    print(run("results", mode="fast"))
