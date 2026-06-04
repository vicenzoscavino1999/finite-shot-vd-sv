"""Pre-freeze power pilot for the Level-1 frozen ensemble.

The pilot is a design artifact, not a confirmatory analysis. It uses only:
declared grids, the pinned frozen ensemble, white-box Level-1 quantities, and
pilot-only RNG streams for the denominator-tail kurtosis check. It must not read
``results/e*.csv`` or any confirmatory output.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models, stable_seed  # noqa: E402
from vd_sv.estimators import make_rng  # noqa: E402

CONFIG = REPO_ROOT / "config" / "grids.yaml"
OUTDIR = REPO_ROOT / "results" / "pilot"
CSV_OUT = OUTDIR / "pilot_power_report.csv"
MD_OUT = OUTDIR / "pilot_power_report.md"
FLOAT_DIGITS = 15
NORMAL = NormalDist()

FIELDS = [
    "instance_id",
    "size_n",
    "sector_weight",
    "mode",
    "T_c_slope",
    "T_kurtosis",
    "n_p_c_slope",
    "n_B_c_slope",
    "B_min_c_slope",
    "B_max_c_slope",
    "wls_condition_number",
    "delta_vd_whitebox",
    "delta_sv_whitebox",
    "delta_vd_fit_slope",
    "delta_sv_fit_slope",
    "delta_vd_fit_abs_error",
    "delta_sv_fit_abs_error",
    "delta_regression_halfwidth_vd",
    "delta_regression_halfwidth_sv",
    "delta_halfwidth_vd",
    "delta_halfwidth_sv",
    "tau_delta_value",
    "tau_delta_role",
    "delta_abs_floor",
    "delta_consistency_abs_tol",
    "delta_near_zero_policy",
    "delta_vd_consistency_status",
    "delta_sv_consistency_status",
    "delta_vd_rule_status",
    "delta_sv_rule_status",
    "c_vd_whitebox_min_abs",
    "c_vd_halfwidth_max",
    "c_sv_halfwidth_max",
    "tau_value",
    "tost_margin_c_sv_min",
    "power_c_vd",
    "power_tost_c_sv",
    "worst_power_c_vd_p",
    "worst_power_tost_c_sv_p",
    "required_T_c_vd_for_power",
    "required_T_tost_c_sv_for_power",
    "required_T_c_slope",
    "B_den_near",
    "B_kurtosis",
    "kurtosis_near_bden",
    "kurtosis_ordinary_near_bden",
    "ordinary_nonfinite_rate_near_bden",
    "kurtosis_status",
    "estimated_shots",
    "estimated_walltime",
    "p3_design_status",
    "p4_design_status",
    "pilot_decision",
    "anti_circularity_basis",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--outdir", type=Path, default=OUTDIR)
    parser.add_argument(
        "--skip-kurtosis",
        action="store_true",
        help="Skip pilot-only denominator sampling; intended for fast unit tests.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    rows, summary = compute_pilot_rows(config, simulate_kurtosis=not args.skip_kurtosis)
    args.outdir.mkdir(parents=True, exist_ok=True)
    csv_path = args.outdir / CSV_OUT.name
    md_path = args.outdir / MD_OUT.name
    write_csv(csv_path, FIELDS, rows)
    write_markdown(md_path, rows, summary)
    print(csv_path)
    print(md_path)
    return 0


def load_config(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def compute_pilot_rows(config: dict, simulate_kurtosis: bool = True) -> tuple[list[dict], dict]:
    pilot = config["pilot_power"]
    mode = str(pilot.get("mode", "full"))
    safety = float(pilot["precision_safety_factor"])
    min_power = float(pilot["min_primary_power"])
    delta_abs_floor_min = float(pilot["delta_abs_floor_min"])
    delta_consistency_abs_tol = float(pilot["delta_consistency_abs_tol"])
    kurtosis_warn_threshold = float(pilot["kurtosis_warn_threshold"])
    shots_per_second = float(pilot["shots_per_second_estimate"])
    seed = int(pilot["seed"])

    exps = config["experiments"]
    e2 = exps["e2_c_sv_zero"]
    e3 = exps["e3_delta_vd_generator"]
    e4 = exps["e4_delta_sv_firstorder"]
    e5 = exps["e5_denominator_concentration"]

    b_grid = np.asarray(e2[f"B_{mode}"], dtype=np.float64)
    ps_c = np.asarray(e2["p_grid"], dtype=np.float64)
    ps_vd_delta = np.asarray(e3[f"p_grid_{mode}"], dtype=np.float64)
    ps_sv_delta = np.asarray(e4[f"p_grid_{mode}"], dtype=np.float64)
    t_c = int(e2[f"T_{mode}"])
    t_kurtosis = int(e5[f"T_{mode}"])
    p_kurtosis = float(e5["p_fixed"])
    m_kurtosis = int(e5["copies_M"])
    tost_fraction = float(config["adjudication"]["tost_margin_fraction_of_c_vd"])
    condition_number = _column_scaled_condition(b_grid)

    z95 = NORMAL.inv_cdf(0.975)
    z_tost = NORMAL.inv_cdf(0.95)
    raw_rows: list[dict] = []

    for model in frozen_models():
        p3_cells = []
        p4_cells = []
        c_vd_relative_halfwidths = []
        c_vd_halfwidths = []
        c_sv_halfwidths = []
        c_vd_abs = []
        tost_margins = []
        required_t_c_vd = []
        required_t_tost_c_sv = []

        for p in ps_c:
            vdc = model.vd(float(p), 2)
            c_vd = float(vdc["c_VD"])
            se_vd = _slope_standard_error(b_grid, float(vdc["v_VD"]), t_c)
            half_vd = z95 * se_vd
            power_vd = _two_sided_power(c_vd, se_vd, z95)
            required_t_c_vd.append(
                _required_t_two_sided(c_vd, se_vd, t_c, z95, min_power)
            )

            svc = model.sv(float(p))
            se_sv = _slope_standard_error(b_grid, float(svc["v_SV"]), t_c)
            half_sv = z95 * se_sv
            margin = tost_fraction * abs(c_vd)
            power_tost = _tost_equivalence_power(se_sv, margin, z_tost)
            required_t_tost_c_sv.append(
                _required_t_tost(se_sv, margin, t_c, z_tost, min_power)
            )

            p3_cells.append((float(p), power_vd))
            p4_cells.append((float(p), power_tost))
            c_vd_relative_halfwidths.append(half_vd / max(abs(c_vd), 1e-300))
            c_vd_halfwidths.append(half_vd)
            c_sv_halfwidths.append(half_sv)
            c_vd_abs.append(abs(c_vd))
            tost_margins.append(margin)

        vd_delta = _delta_fit(model, "vd", ps_vd_delta, z95)
        sv_delta = _delta_fit(model, "sv", ps_sv_delta, z95)
        kurtosis = _kurtosis_near_bden(
            model=model,
            p=p_kurtosis,
            m=m_kurtosis,
            t=t_kurtosis,
            seed=stable_seed(seed, model.inst.name, "pilot", "kurtosis"),
            simulate=simulate_kurtosis,
        )

        e2_shots = int(len(ps_c) * t_c * int(np.sum(b_grid)) * 3)
        e5_shots = int(t_kurtosis * int(kurtosis["B_kurtosis"]) * 2)
        estimated_shots = e2_shots + e5_shots

        raw_rows.append({
            "instance_id": model.inst.name,
            "size_n": int(model.inst.n),
            "sector_weight": int(model.inst.weight),
            "mode": mode,
            "T_c_slope": t_c,
            "T_kurtosis": t_kurtosis,
            "n_p_c_slope": int(len(ps_c)),
            "n_B_c_slope": int(len(b_grid)),
            "B_min_c_slope": int(np.min(b_grid)),
            "B_max_c_slope": int(np.max(b_grid)),
            "wls_condition_number": condition_number,
            "delta_vd_whitebox": vd_delta["closed_form"],
            "delta_sv_whitebox": sv_delta["closed_form"],
            "delta_vd_fit_slope": vd_delta["fit_slope"],
            "delta_sv_fit_slope": sv_delta["fit_slope"],
            "delta_vd_fit_abs_error": vd_delta["fit_abs_error"],
            "delta_sv_fit_abs_error": sv_delta["fit_abs_error"],
            "delta_regression_halfwidth_vd": vd_delta["regression_halfwidth"],
            "delta_regression_halfwidth_sv": sv_delta["regression_halfwidth"],
            "delta_halfwidth_vd": vd_delta["halfwidth"],
            "delta_halfwidth_sv": sv_delta["halfwidth"],
            "_delta_vd_precision_ci_contains": vd_delta["precision_ci_contains"],
            "_delta_sv_precision_ci_contains": sv_delta["precision_ci_contains"],
            "_c_vd_relative_halfwidth_max": max(c_vd_relative_halfwidths),
            "c_vd_whitebox_min_abs": min(c_vd_abs),
            "c_vd_halfwidth_max": max(c_vd_halfwidths),
            "c_sv_halfwidth_max": max(c_sv_halfwidths),
            "tost_margin_c_sv_min": min(tost_margins),
            "power_c_vd": min(power for _p, power in p3_cells),
            "power_tost_c_sv": min(power for _p, power in p4_cells),
            "worst_power_c_vd_p": min(p3_cells, key=lambda item: item[1])[0],
            "worst_power_tost_c_sv_p": min(p4_cells, key=lambda item: item[1])[0],
            "required_T_c_vd_for_power": max(required_t_c_vd),
            "required_T_tost_c_sv_for_power": max(required_t_tost_c_sv),
            "required_T_c_slope": max(max(required_t_c_vd), max(required_t_tost_c_sv)),
            "B_den_near": kurtosis["B_den_near"],
            "B_kurtosis": kurtosis["B_kurtosis"],
            "kurtosis_near_bden": kurtosis["kurtosis_clipped"],
            "kurtosis_ordinary_near_bden": kurtosis["kurtosis_ordinary"],
            "ordinary_nonfinite_rate_near_bden": kurtosis["ordinary_nonfinite_rate"],
            "estimated_shots": estimated_shots,
            "estimated_walltime": estimated_shots / shots_per_second,
            "anti_circularity_basis": (
                "precision_pilot_plus_white_box_tost_margin; "
                "no_confirmatory_results_read"
            ),
        })

    tau_value = safety * max(row["_c_vd_relative_halfwidth_max"] for row in raw_rows)
    tau_delta_value = safety * max(
        max(float(row["delta_halfwidth_vd"]), float(row["delta_halfwidth_sv"]))
        for row in raw_rows
    )
    delta_abs_floor = max(tau_delta_value, delta_abs_floor_min)

    rows = []
    for row in raw_rows:
        p3_status = "PASS" if float(row["power_c_vd"]) >= min_power else "ADJUST_T_OR_B_GRID"
        p4_status = "PASS" if float(row["power_tost_c_sv"]) >= min_power else "ADJUST_T_OR_B_GRID"
        kurtosis_status = _kurtosis_status(
            float(row["kurtosis_near_bden"]),
            kurtosis_warn_threshold,
            simulate_kurtosis,
        )
        vd_consistency_status = _delta_consistency_status(
            float(row["delta_vd_fit_abs_error"]),
            delta_consistency_abs_tol,
        )
        sv_consistency_status = _delta_consistency_status(
            float(row["delta_sv_fit_abs_error"]),
            delta_consistency_abs_tol,
        )
        vd_delta_status = _delta_rule_status(
            float(row["delta_vd_whitebox"]),
            delta_abs_floor,
            vd_consistency_status,
        )
        sv_delta_status = _delta_rule_status(
            float(row["delta_sv_whitebox"]),
            delta_abs_floor,
            sv_consistency_status,
        )
        blocking_statuses = {p3_status, p4_status, kurtosis_status, vd_consistency_status, sv_consistency_status}
        pilot_decision = (
            "PASS_FOR_FREEZE"
            if blocking_statuses == {"PASS"}
            else "DESIGN_ADJUSTMENT_REQUIRED"
        )
        if vd_delta_status.startswith("INCONCLUSIVE") or sv_delta_status.startswith("INCONCLUSIVE"):
            pilot_decision = (
                "PASS_WITH_NEAR_ZERO_INCONCLUSIVE"
                if pilot_decision == "PASS_FOR_FREEZE"
                else pilot_decision
            )

        clean = {key: value for key, value in row.items() if not key.startswith("_")}
        clean.update({
            "tau_value": tau_value,
            "tau_delta_value": tau_delta_value,
            "tau_delta_role": "precision_only_not_p5_p6_pass_criterion",
            "delta_abs_floor": delta_abs_floor,
            "delta_consistency_abs_tol": delta_consistency_abs_tol,
            "delta_near_zero_policy": str(config["pilot_power"]["delta_near_zero_policy"]),
            "delta_vd_consistency_status": vd_consistency_status,
            "delta_sv_consistency_status": sv_consistency_status,
            "delta_vd_rule_status": vd_delta_status,
            "delta_sv_rule_status": sv_delta_status,
            "kurtosis_status": kurtosis_status,
            "p3_design_status": p3_status,
            "p4_design_status": p4_status,
            "pilot_decision": pilot_decision,
        })
        rows.append(clean)

    summary = {
        "mode": mode,
        "instances": len(rows),
        "min_power_c_vd": min(float(row["power_c_vd"]) for row in rows),
        "min_power_tost_c_sv": min(float(row["power_tost_c_sv"]) for row in rows),
        "max_delta_halfwidth": max(
            max(float(row["delta_halfwidth_vd"]), float(row["delta_halfwidth_sv"]))
            for row in rows
        ),
        "tau_value": tau_value,
        "tau_delta_value": tau_delta_value,
        "tau_delta_role": "precision_only_not_p5_p6_pass_criterion",
        "delta_abs_floor": delta_abs_floor,
        "delta_consistency_abs_tol": delta_consistency_abs_tol,
        "max_delta_fit_abs_error": max(
            max(float(row["delta_vd_fit_abs_error"]), float(row["delta_sv_fit_abs_error"]))
            for row in rows
        ),
        "near_zero_instances": [
            row["instance_id"]
            for row in rows
            if str(row["delta_vd_rule_status"]).startswith("INCONCLUSIVE")
            or str(row["delta_sv_rule_status"]).startswith("INCONCLUSIVE")
        ],
        "pilot_decisions": sorted({row["pilot_decision"] for row in rows}),
        "total_estimated_shots": sum(int(row["estimated_shots"]) for row in rows),
        "total_estimated_walltime": sum(float(row["estimated_walltime"]) for row in rows),
        "max_required_T_c_slope": max(int(row["required_T_c_slope"]) for row in rows),
        "simulate_kurtosis": simulate_kurtosis,
        "kurtosis_warn_threshold": kurtosis_warn_threshold,
        "min_primary_power": min_power,
    }
    return rows, summary


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _stable_csv_cell(row[key]) for key in fieldnames})


def write_markdown(path: Path, rows: list[dict], summary: dict) -> None:
    near_zero = summary["near_zero_instances"]
    decisions = ", ".join(summary["pilot_decisions"])
    lines = [
        "# Pilot power report",
        "",
        "This pre-freeze pilot uses the frozen Level-1 ensemble, declared grids,",
        "white-box Level-1 quantities, and pilot-only RNG streams for the",
        "near-`B_den` kurtosis check. It does not read `results/e*.csv`.",
        "",
        "## Design decision",
        "",
        f"- Mode: `{summary['mode']}`.",
        f"- Instances: {summary['instances']}.",
        f"- Minimum P3 power (`c_VD != 0`): {summary['min_power_c_vd']:.6g}.",
        f"- Minimum P4 TOST power (`c_SV = 0`): {summary['min_power_tost_c_sv']:.6g}.",
        f"- Required primary power: {summary['min_primary_power']:.6g}.",
        f"- `tau_value`: {summary['tau_value']:.6g}.",
        f"- `tau_delta_value`: {summary['tau_delta_value']:.6g} "
        f"({summary['tau_delta_role']}).",
        f"- `delta_abs_floor`: {summary['delta_abs_floor']:.6g}.",
        f"- `delta_consistency_abs_tol`: {summary['delta_consistency_abs_tol']:.6g}.",
        f"- Max deterministic delta truncation error: {summary['max_delta_fit_abs_error']:.6g}.",
        f"- Pilot decisions: `{decisions}`.",
        f"- Total estimated effective shots: {summary['total_estimated_shots']}.",
        f"- Total estimated walltime seconds: {summary['total_estimated_walltime']:.6g}.",
        f"- Max required `T_full` for P3/P4 power: {summary['max_required_T_c_slope']}.",
        "",
        "## Anti-circularity",
        "",
        "- `tau_value` is derived from pilot precision plus the pre-registered",
        "  safety factor.",
        "- `tau_delta_value` uses only deterministic Level-1 fit precision:",
        "  regression halfwidth on the declared `p` grid plus the",
        "  pre-registered safety factor. It is not a P5/P6 pass criterion in",
        "  the current white-box route.",
        "- P5/P6 consistency uses `delta_fit_abs_error <= delta_consistency_abs_tol`;",
        "  the tolerance is pre-registered and does not include the observed",
        "  truncation discrepancy.",
        "- P4 TOST margins use `f * |c_VD^white-box|`; they never use observed",
        "  `c_hat` values.",
        "- P5/P6 use the current deterministic Level-1 white-box route for",
        "  `b_VD,inf(p)` and `b_SV(p)`. A finite-shot `beta0` route would require",
        "  bootstrap propagation before freeze.",
        "- Near-zero deltas are not used to exclude or replace instances.",
        "",
        "## Near-zero delta policy",
        "",
    ]
    if near_zero:
        lines.append(
            "Instances marked `INCONCLUSIVE_BY_DESIGN_NEAR_ZERO`: "
            + ", ".join(f"`{name}`" for name in near_zero)
            + "."
        )
    else:
        lines.append("No instance falls below `delta_abs_floor`.")
    lines.extend([
        "",
        "## Per-instance status",
        "",
        "| instance_id | P3 | P4 | VD consistency | SV consistency | P5/VD delta | P6/SV delta | kurtosis | decision |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            "| {instance_id} | {p3_design_status} | {p4_design_status} | "
            "{delta_vd_consistency_status} | {delta_sv_consistency_status} | "
            "{delta_vd_rule_status} | {delta_sv_rule_status} | {kurtosis_status} | "
            "{pilot_decision} |".format(**row)
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _slope_standard_error(b_grid: np.ndarray, variance_coeff: float, t: int) -> float:
    inv_b = 1.0 / b_grid
    design = np.column_stack([inv_b, inv_b**2])
    mean_variance = np.maximum(float(variance_coeff) / (b_grid * int(t)), 1e-300)
    weights = 1.0 / mean_variance
    xtwx = (design * weights[:, None]).T @ design
    cov = np.linalg.inv(xtwx)
    return float(math.sqrt(max(cov[0, 0], 0.0)))


def _two_sided_power(effect: float, se: float, z95: float) -> float:
    if se <= 0.0:
        return 1.0
    upper = NORMAL.cdf((z95 * se - effect) / se)
    lower = NORMAL.cdf((-z95 * se - effect) / se)
    return float(max(0.0, min(1.0, 1.0 - upper + lower)))


def _tost_equivalence_power(se: float, margin: float, z_tost: float) -> float:
    if se <= 0.0:
        return 1.0
    threshold = float(margin) - z_tost * se
    if threshold <= 0.0:
        return 0.0
    return float(max(0.0, min(1.0, 2.0 * NORMAL.cdf(threshold / se) - 1.0)))


def _required_t_two_sided(
    effect: float,
    se_at_t: float,
    t_current: int,
    z95: float,
    target_power: float,
) -> int:
    effect_abs = abs(float(effect))
    if effect_abs <= 0.0:
        return math.inf
    target_h = _required_noncentral_two_sided(z95, target_power)
    required_se = effect_abs / target_h
    return int(math.ceil(t_current * (se_at_t / required_se) ** 2))


def _required_t_tost(
    se_at_t: float,
    margin: float,
    t_current: int,
    z_tost: float,
    target_power: float,
) -> int:
    if margin <= 0.0:
        return math.inf
    central_mass_z = NORMAL.inv_cdf((1.0 + target_power) / 2.0)
    required_se = float(margin) / (z_tost + central_mass_z)
    return int(math.ceil(t_current * (se_at_t / required_se) ** 2))


def _required_noncentral_two_sided(z95: float, target_power: float) -> float:
    lo, hi = 0.0, 8.0
    while _two_sided_power(hi, 1.0, z95) < target_power:
        hi *= 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _two_sided_power(mid, 1.0, z95) >= target_power:
            hi = mid
        else:
            lo = mid
    return hi


def _delta_fit(model, method: str, ps: np.ndarray, z95: float) -> dict:
    if method == "vd":
        values = np.array([model.vd_floor(float(p))["b_VD_inf"] for p in ps], dtype=np.float64)
        closed = float(model.delta_vd())
    elif method == "sv":
        values = np.array([model.sv(float(p))["b_SV"] for p in ps], dtype=np.float64)
        closed = float(model.delta_sv())
    else:
        raise ValueError(f"unknown delta method: {method}")

    design = np.column_stack([ps, ps**2])
    coeffs, *_ = np.linalg.lstsq(design, values, rcond=None)
    fit_slope = float(coeffs[0])
    residual = values - design @ coeffs
    dof = max(int(values.size - design.shape[1]), 1)
    sigma2 = float(np.sum(residual**2) / dof)
    cov = sigma2 * np.linalg.inv(design.T @ design)
    regression_halfwidth = float(z95 * math.sqrt(max(cov[0, 0], 0.0)))
    fit_abs_error = abs(fit_slope - closed)
    return {
        "closed_form": closed,
        "fit_slope": fit_slope,
        "fit_abs_error": fit_abs_error,
        "regression_halfwidth": regression_halfwidth,
        "halfwidth": regression_halfwidth,
        "precision_ci_contains": fit_abs_error <= regression_halfwidth,
    }


def _kurtosis_near_bden(model, p: float, m: int, t: int, seed: int, simulate: bool) -> dict:
    vdc = model.vd(float(p), int(m))
    d_m = float(vdc["D_M"])
    n_m = float(vdc["N_M"])
    b_den = float(vdc["B_den"])
    b = max(2, int(round(b_den)))
    if not simulate:
        return {
            "B_den_near": b_den,
            "B_kurtosis": b,
            "kurtosis_clipped": float("nan"),
            "kurtosis_ordinary": float("nan"),
            "ordinary_nonfinite_rate": float("nan"),
        }

    rng = make_rng(int(seed))
    n_hat, d_hat = _sample_vd_stream_means(n_m, d_m, b, int(t), rng)
    clipped = n_hat / np.maximum(d_hat, 0.5 * d_m)
    with np.errstate(divide="ignore", invalid="ignore"):
        ordinary = n_hat / d_hat
    finite = np.isfinite(ordinary)
    ordinary_finite = ordinary[finite]
    return {
        "B_den_near": b_den,
        "B_kurtosis": b,
        "kurtosis_clipped": _excess_kurtosis(clipped),
        "kurtosis_ordinary": _excess_kurtosis(ordinary_finite),
        "ordinary_nonfinite_rate": float(1.0 - np.mean(finite)),
    }


def _sample_vd_stream_means(
    n_m: float,
    d_m: float,
    b: int,
    t: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    q_n = 0.5 * (1.0 + n_m)
    q_d = 0.5 * (1.0 + d_m)
    k_n = rng.binomial(b, q_n, size=t)
    k_d = rng.binomial(b, q_d, size=t)
    return 2.0 * k_n / b - 1.0, 2.0 * k_d / b - 1.0


def _excess_kurtosis(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return float("nan")
    centered = arr - float(np.mean(arr))
    var = float(np.mean(centered**2))
    if var <= 0.0:
        return 0.0
    return float(np.mean(centered**4) / (var * var) - 3.0)


def _column_scaled_condition(b_grid: np.ndarray) -> float:
    inv_b = 1.0 / b_grid
    design = np.column_stack([np.ones_like(inv_b), inv_b, inv_b**2])
    norms = np.linalg.norm(design, axis=0)
    return float(np.linalg.cond(design / norms))


def _delta_consistency_status(fit_abs_error: float, abs_tol: float) -> str:
    return "PASS" if fit_abs_error <= abs_tol else "ADJUST_P_GRID_OR_DELTA_MODEL"


def _delta_rule_status(
    delta_whitebox: float,
    abs_floor: float,
    consistency_status: str,
) -> str:
    if abs(delta_whitebox) < abs_floor:
        return "INCONCLUSIVE_BY_DESIGN_NEAR_ZERO"
    return consistency_status


def _kurtosis_status(kurtosis: float, threshold: float, simulated: bool) -> str:
    if not simulated:
        return "SKIPPED"
    if not math.isfinite(kurtosis):
        return "WARN_NONFINITE"
    return "PASS" if kurtosis <= threshold else "INCREASE_T_NEAR_BDEN"


def _stable_csv_cell(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return f"{value:.{FLOAT_DIGITS}g}"
    return value


if __name__ == "__main__":
    raise SystemExit(main())
