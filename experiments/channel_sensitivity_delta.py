"""Registered S10 robustness check: depolarizing-channel delta sensitivity.

This additive runner repeats the E3/E4 first-order delta checks under the
registered depolarizing sensitivity channel.  It is a Level 1 white-box endpoint
and does not modify any frozen reproduction path.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models, stable_seed  # noqa: E402
from vd_sv import coefficients, noise  # noqa: E402

OUTDIR = REPO_ROOT / "results" / "secondary"
CSV_PATH = OUTDIR / "channel_sensitivity_delta.csv"
REPORT_PATH = OUTDIR / "channel_sensitivity_delta_report.md"

BASE_SEED = 14_014
RATE_MIN = 0.4
RATE_MAX = 1.3
RICHARDSON_H = 1e-5
ABS_ERR_TOL = 1e-4

FIELDS = [
    "instance_id",
    "delta_vd_closed",
    "delta_vd_fd",
    "delta_vd_abs_err",
    "delta_sv_closed",
    "delta_sv_fd",
    "delta_sv_abs_err",
    "channel_seed",
    "rates_json",
]


def main() -> int:
    rows = run_analysis()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    _write_csv(CSV_PATH, rows)
    REPORT_PATH.write_text(render_report(rows), encoding="utf-8")
    print(CSV_PATH)
    print(REPORT_PATH)
    return 0


def run_analysis() -> list[dict]:
    rows: list[dict] = []
    for frozen in frozen_models():
        seed = stable_seed(BASE_SEED, frozen.inst.name, "depol")
        rng = np.random.Generator(np.random.PCG64(seed))
        rates = rng.uniform(RATE_MIN, RATE_MAX, size=frozen.inst.n)
        channel = noise.depolarizing(frozen.inst.n, rates)
        model = coefficients.build_model(frozen.inst, frozen.gammas, frozen.betas, channel)
        noise.assert_delta_consistency(channel, model.rho_star)

        delta_vd_closed = model.delta_vd()
        delta_sv_closed = model.delta_sv()
        delta_vd_fd = _richardson_vd_slope(model)
        delta_sv_fd = _richardson_sv_slope(model)
        delta_vd_abs_err = abs(delta_vd_closed - delta_vd_fd)
        delta_sv_abs_err = abs(delta_sv_closed - delta_sv_fd)
        if delta_vd_abs_err > ABS_ERR_TOL or delta_sv_abs_err > ABS_ERR_TOL:
            raise RuntimeError(
                f"delta consistency failed for {frozen.inst.name}: "
                f"VD err={delta_vd_abs_err:.3e}, SV err={delta_sv_abs_err:.3e}"
            )

        rows.append({
            "instance_id": frozen.inst.name,
            "delta_vd_closed": delta_vd_closed,
            "delta_vd_fd": delta_vd_fd,
            "delta_vd_abs_err": delta_vd_abs_err,
            "delta_sv_closed": delta_sv_closed,
            "delta_sv_fd": delta_sv_fd,
            "delta_sv_abs_err": delta_sv_abs_err,
            "channel_seed": seed,
            "rates_json": json.dumps([float(x) for x in rates], separators=(",", ":")),
        })
    return rows


def _richardson_vd_slope(model) -> float:
    h = RICHARDSON_H
    b_h = float(model.vd_floor(h)["b_VD_inf"])
    b_2h = float(model.vd_floor(2.0 * h)["b_VD_inf"])
    return 2.0 * b_h / h - b_2h / (2.0 * h)


def _richardson_sv_slope(model) -> float:
    h = RICHARDSON_H
    b_h = float(model.sv(h)["b_SV"])
    b_2h = float(model.sv(2.0 * h)["b_SV"])
    return 2.0 * b_h / h - b_2h / (2.0 * h)


def render_report(rows: list[dict]) -> str:
    max_vd_err = max(float(row["delta_vd_abs_err"]) for row in rows)
    max_sv_err = max(float(row["delta_sv_abs_err"]) for row in rows)
    max_abs_delta_sv = max(abs(float(row["delta_sv_closed"])) for row in rows)
    generator_pass = len(rows)
    lines = [
        "# Depolarizing-Channel Delta Sensitivity",
        "",
        "Status: secondary descriptive endpoint (registered robustness check, EXPERIMENTAL_PLAN sec. 10; not primary FWER).",
        "",
        "## Design",
        "",
        f"- Channel: heterogeneous depolarizing with per-qubit c_i ~ Uniform({RATE_MIN:g}, {RATE_MAX:g}).",
        f"- RNG: numpy Generator/PCG64 with base seed `{BASE_SEED}` and per-instance stable_seed.",
        f"- Richardson h: `{RICHARDSON_H:g}`; absolute-error tolerance: `{ABS_ERR_TOL:g}`.",
        "",
        "## Per-Instance Delta Checks",
        "",
        "| instance | delta_VD closed | delta_VD fd | VD abs err | delta_SV closed | delta_SV fd | SV abs err |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['instance_id']} | {float(row['delta_vd_closed']):.6g} | "
            f"{float(row['delta_vd_fd']):.6g} | {float(row['delta_vd_abs_err']):.3e} | "
            f"{float(row['delta_sv_closed']):.6g} | {float(row['delta_sv_fd']):.6g} | "
            f"{float(row['delta_sv_abs_err']):.3e} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusions",
        "",
        (
            f"Generator consistency passes {generator_pass}/{len(rows)} instances; the "
            f"maximum Richardson absolute error is {max(max_vd_err, max_sv_err):.3e} "
            f"(VD max {max_vd_err:.3e}, SV max {max_sv_err:.3e})."
        ),
        "",
        (
            "Empirically on the frozen ensemble under heterogeneous depolarizing "
            f"channels, delta_SV is zero to machine precision (max |delta_SV| = "
            f"{max_abs_delta_sv:.3e}), while delta_VD remains generic. This is an "
            "ensemble observation, not a theorem."
        ),
    ])
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_cell(row.get(field, "")) for field in FIELDS})


def _csv_cell(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        if not math.isfinite(value):
            return "nan"
        return f"{value:.15g}"
    return value


if __name__ == "__main__":
    raise SystemExit(main())
