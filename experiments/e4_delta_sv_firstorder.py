"""E4 - SV first-order bias coefficient (validates P6).

Theory anchor: Prop. sv_delta_precise, eq. delta_sv_precise.
``b_SV(p) = delta_SV * p + O(p^2)`` with ``delta_SV = Tr(O P Delta P) - mu_star Tr(P Delta P)``.
At Level 1 ``b_SV(p)`` is exact; its slope through the origin is contrasted with the
closed form.  (Coefficient claim only at Level 1: with readout error, Levels 2-3
require the mitigation-before-postselection protocol of EXP. PLAN sec. 4.3.)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ._common import default_model, p_grid, write_csv

FIELDS = ["noise_strength", "b_sv", "delta_sv_measured", "delta_sv_closed_form"]


def run(outdir: str | Path, mode: str = "fast", seed: int = 404) -> Path:
    npts = 8 if mode == "fast" else 14
    ps = p_grid(0.01, 0.12, npts)
    m = default_model()
    delta_closed = m.delta_sv()

    b_sv = np.array([m.sv(float(p))["b_SV"] for p in ps])
    X = np.column_stack([ps, ps**2])
    coeffs, *_ = np.linalg.lstsq(X, b_sv, rcond=None)
    delta_measured = float(coeffs[0])

    rows = [{
        "noise_strength": float(p), "b_sv": float(bi),
        "delta_sv_measured": delta_measured, "delta_sv_closed_form": delta_closed,
    } for p, bi in zip(ps, b_sv)]
    return write_csv(Path(outdir) / "e4_delta_sv_firstorder.csv", FIELDS, rows)


if __name__ == "__main__":
    print(run("results", mode="fast"))
