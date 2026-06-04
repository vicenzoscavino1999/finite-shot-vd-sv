"""E2 - c_SV = 0 versus c_VD != 0 (validates P3, P4).

Theory anchor: eq. vd_c_v4 / hadamard_c_v4 and eq. sv_quotient_bias_zero_v14.
The statistical quotient-bias coefficient is the slope of ``E[mu_hat] - mu_pop``
against ``1/B``.  For VD this slope is nonzero and matches c_VD; for SV it is
exactly zero (Bernoulli postselection).  This is the cheapest structural
discriminator between the two methods.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from vd_sv import sv as sv_mod
from vd_sv import vd as vd_mod
from vd_sv.estimators import make_rng

from ._common import frozen_models, log_grid, p_grid, stable_seed, wls_fit, write_csv

FIELDS = [
    "instance_id",
    "noise_strength",
    "B",
    "method",
    "bias_minus_pop",
    "c_slope_estimate",
    "c_slope_ci_lower",
    "c_slope_ci_upper",
    "ensemble_c_slope_mean",
    "ensemble_c_slope_std",
]
T_BY_MODE = {"fast": 4000, "full": 70000}


def run(outdir: str | Path, mode: str = "fast", seed: int = 202) -> Path:
    t = T_BY_MODE[mode]
    b_grid = log_grid(500, 12000 if mode == "fast" else 40000, 8 if mode == "fast" else 11)
    ps = p_grid(0.12, 0.25, 3)

    rows = []
    for m in frozen_models():
        rng = make_rng(stable_seed(seed, m.inst.name, "e2"))
        for p in ps:
            vdc = m.vd(float(p), 2)
            svc = m.sv(float(p))
            pz, acc, val, a = sv_mod.sv_measurement_data(m, float(p))
            for method in ("vd", "sv"):
                mu_pop = vdc["mu_VD"] if method == "vd" else svc["mu_SV"]
                biases, ses = [], []
                for B in b_grid:
                    Bi = int(B)
                    if method == "vd":
                        est = vd_mod.sample_vd_quotient(vdc["N_M"], vdc["D_M"], Bi, t, rng)
                    else:
                        est = sv_mod.sample_sv_quotient(pz, acc, val, a, Bi, t, rng)
                    biases.append(float(est.mean()) - mu_pop)
                    ses.append(max(float(est.std(ddof=1) / np.sqrt(t)), 1e-12))
                biases, ses = np.array(biases), np.array(ses)

                # WLS fit of bias ~ c/B + d/B^2 (no intercept: bias -> 0 as B -> inf).
                # The 1/B^2 term absorbs the certified remainder so c isolates the
                # leading quotient-bias coefficient (eq. vd_c_v4).
                invB = 1.0 / b_grid
                X = np.column_stack([invB, invB**2])
                (c, _d), cov = wls_fit(X, biases, 1.0 / ses**2)
                c_se = float(np.sqrt(cov[0, 0]))
                lo, hi = c - 1.96 * c_se, c + 1.96 * c_se

                for B, bm in zip(b_grid, biases):
                    rows.append({
                        "instance_id": m.inst.name,
                        "noise_strength": float(p),
                        "B": int(B),
                        "method": method,
                        "bias_minus_pop": float(bm),
                        "c_slope_estimate": float(c),
                        "c_slope_ci_lower": float(lo),
                        "c_slope_ci_upper": float(hi),
                    })
    _add_ensemble_stats(rows)
    return write_csv(Path(outdir) / "e2_c_sv_zero.csv", FIELDS, rows)


def _add_ensemble_stats(rows: list[dict]) -> None:
    groups = sorted({(float(row["noise_strength"]), row["method"]) for row in rows})
    for p, method in groups:
        sub = [
            row for row in rows
            if abs(float(row["noise_strength"]) - p) <= 1e-12 and row["method"] == method
        ]
        by_instance = {row["instance_id"]: float(row["c_slope_estimate"]) for row in sub}
        vals = np.array(list(by_instance.values()), dtype=np.float64)
        stats = {
            "ensemble_c_slope_mean": float(np.mean(vals)),
            "ensemble_c_slope_std": float(np.std(vals, ddof=1)) if vals.size > 1 else 0.0,
        }
        for row in sub:
            row.update(stats)


if __name__ == "__main__":
    print(run("results", mode="fast"))
