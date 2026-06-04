"""E3 - VD first-order floor coefficient from the noise generator (validates P5).

Theory anchor: Prop. vd_delta_generator, eq. delta_vd_explicit.
The infinite-copy floor obeys ``b_VD,inf(p) = delta_VD * p + O(p^2)``.  At Level 1
``b_VD,inf(p)`` is computed exactly from the dominant eigenvector of rho_p; its slope
through the origin (delta_vd_measured) is contrasted with the closed-form generator
``delta_VD = 2 Re <psi| O Q_star Delta |psi>`` (delta_vd_closed_form).  Both are
white-box, so they agree up to the O(p^2) truncation of the slope fit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ._common import default_model, p_grid, write_csv

FIELDS = ["noise_strength", "b_vd_inf", "delta_vd_measured", "delta_vd_closed_form"]


def run(outdir: str | Path, mode: str = "fast", seed: int = 303) -> Path:
    npts = 8 if mode == "fast" else 14
    ps = p_grid(0.01, 0.12, npts)
    m = default_model()
    delta_closed = m.delta_vd()

    b_inf = np.array([m.vd_floor(float(p))["b_VD_inf"] for p in ps])
    # slope through origin: b(p) ~ delta*p + kappa*p^2
    X = np.column_stack([ps, ps**2])
    coeffs, *_ = np.linalg.lstsq(X, b_inf, rcond=None)
    delta_measured = float(coeffs[0])

    rows = [{
        "noise_strength": float(p), "b_vd_inf": float(bi),
        "delta_vd_measured": delta_measured, "delta_vd_closed_form": delta_closed,
    } for p, bi in zip(ps, b_inf)]
    return write_csv(Path(outdir) / "e3_delta_vd_generator.csv", FIELDS, rows)


if __name__ == "__main__":
    print(run("results", mode="fast"))
