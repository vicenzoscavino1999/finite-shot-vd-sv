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

from ._common import frozen_models, p_grid, write_csv

FIELDS = [
    "instance_id",
    "noise_strength",
    "b_sv",
    "delta_sv_measured",
    "delta_sv_closed_form",
    "ensemble_delta_sv_measured_mean",
    "ensemble_delta_sv_measured_std",
    "ensemble_delta_sv_closed_form_mean",
    "ensemble_delta_sv_closed_form_std",
]


def run(outdir: str | Path, mode: str = "fast", seed: int = 404) -> Path:
    npts = 8 if mode == "fast" else 14
    ps = p_grid(0.01, 0.12, npts)
    rows = []
    for m in frozen_models():
        delta_closed = m.delta_sv()
        b_sv = np.array([m.sv(float(p))["b_SV"] for p in ps])
        X = np.column_stack([ps, ps**2])
        coeffs, *_ = np.linalg.lstsq(X, b_sv, rcond=None)
        delta_measured = float(coeffs[0])

        rows.extend({
            "instance_id": m.inst.name,
            "noise_strength": float(p),
            "b_sv": float(bi),
            "delta_sv_measured": delta_measured,
            "delta_sv_closed_form": delta_closed,
        } for p, bi in zip(ps, b_sv))
    _add_ensemble_stats(rows)
    return write_csv(Path(outdir) / "e4_delta_sv_firstorder.csv", FIELDS, rows)


def _add_ensemble_stats(rows: list[dict]) -> None:
    by_instance = {}
    for row in rows:
        by_instance[row["instance_id"]] = (
            float(row["delta_sv_measured"]),
            float(row["delta_sv_closed_form"]),
        )
    measured = np.array([vals[0] for vals in by_instance.values()], dtype=np.float64)
    closed = np.array([vals[1] for vals in by_instance.values()], dtype=np.float64)
    stats = {
        "ensemble_delta_sv_measured_mean": float(np.mean(measured)),
        "ensemble_delta_sv_measured_std": float(np.std(measured, ddof=1)) if measured.size > 1 else 0.0,
        "ensemble_delta_sv_closed_form_mean": float(np.mean(closed)),
        "ensemble_delta_sv_closed_form_std": float(np.std(closed, ddof=1)) if closed.size > 1 else 0.0,
    }
    for row in rows:
        row.update(stats)


if __name__ == "__main__":
    print(run("results", mode="fast"))
