"""Post-adjudication sensitivity analysis for the c_VD slope SE.

This script replays E2 with the frozen v1/v2 finite-shot seeds, checks that the
recomputed VD c_slope matches each confirmatory CSV, and compares the analytic
WLS SE with the nonparametric bootstrap SE implied by resampling the T estimator
replicas at each B.

Status: sensitivity only. This is not a gate, not an adjudication, and not a
freeze.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import chi2

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models, stable_seed, wls_fit  # noqa: E402
from vd_sv import sv as sv_mod  # noqa: E402
from vd_sv import vd as vd_mod  # noqa: E402
from vd_sv.estimators import make_rng  # noqa: E402

REPORT_PATH = REPO_ROOT / "analysis" / "c_vd_se_sensitivity_report.md"
GRID_PATH = REPO_ROOT / "config" / "grids.yaml"
N_BOOT = 2000
BOOTSTRAP_SEED = 731029
SELF_CHECK_ATOL = 1e-9

DATASETS = {
    "v1": {
        "results": REPO_ROOT / "results" / "confirmatory_full",
        "rng_policy": REPO_ROOT / "reproducibility" / "config" / "rng_policy.yaml",
    },
    "v2": {
        "results": REPO_ROOT / "results" / "confirmatory_v2",
        "rng_policy": REPO_ROOT / "reproducibility" / "config" / "rng_policy_v2.yaml",
    },
}


@dataclass(frozen=True)
class CellResult:
    dataset: str
    instance_id: str
    noise_strength: float
    c_hat: float
    c_closed: float
    analytic_se: float
    bootstrap_se: float
    se_ratio: float
    z_analytic: float
    z_bootstrap: float
    c_slope_abs_diff: float
    analytic_se_abs_diff: float


@dataclass(frozen=True)
class DatasetResult:
    label: str
    seed: int
    cells: list[CellResult]
    analytic_chi2: float
    analytic_p: float
    analytic_mean_z: float
    bootstrap_chi2: float
    bootstrap_p: float
    bootstrap_mean_z: float
    median_se_ratio: float
    min_se_ratio: float
    max_se_ratio: float
    instance_analytic_chi2: float
    instance_analytic_p: float
    instance_analytic_mean_z: float
    instance_bootstrap_chi2: float
    instance_bootstrap_p: float
    instance_bootstrap_mean_z: float
    max_c_slope_abs_diff: float
    max_analytic_se_abs_diff: float


def main() -> int:
    grid = _load_e2_grid()
    models = frozen_models()
    results = []
    for label, spec in DATASETS.items():
        seed = _load_e2_seed(spec["rng_policy"])
        csv_cells = _load_confirmatory_c_vd(spec["results"] / "e2_c_sv_zero.csv")
        result = _analyze_dataset(label, seed, spec["results"], csv_cells, models, grid)
        results.append(result)
    REPORT_PATH.write_text(_render_report(results), encoding="utf-8")
    print(REPORT_PATH)
    return 0


def _analyze_dataset(
    label: str,
    seed: int,
    results_path: Path,
    csv_cells: dict[tuple[str, str], dict],
    models: list,
    grid: dict,
) -> DatasetResult:
    del results_path
    rng_boot = make_rng(stable_seed(BOOTSTRAP_SEED, label, "c_vd_se_sensitivity"))
    del rng_boot  # The exact linear bootstrap moment is deterministic; seed is documented.

    cells: list[CellResult] = []
    for model in models:
        rng = make_rng(stable_seed(seed, model.inst.name, "e2"))
        for p in grid["p_grid"]:
            p_float = float(p)
            vd_coeffs = model.vd(p_float, 2)
            sv_coeffs = model.sv(p_float)
            pz, accept, value, a = sv_mod.sv_measurement_data(model, p_float)

            estimates_by_b = []
            for b in grid["B_full"]:
                estimates_by_b.append(
                    vd_mod.sample_vd_quotient(
                        vd_coeffs["N_M"],
                        vd_coeffs["D_M"],
                        int(b),
                        grid["T_full"],
                        rng,
                    )
                )

            cell = _fit_vd_cell(
                label=label,
                model=model,
                p=p_float,
                b_grid=grid["B_full"],
                t=grid["T_full"],
                estimates_by_b=estimates_by_b,
                csv_cell=csv_cells[(model.inst.name, _p_key(p_float))],
                vd_coeffs=vd_coeffs,
            )
            cells.append(cell)

            # E2 consumes the SV stream before moving to the next p. These draws
            # are not analyzed here, but they are required for faithful RNG replay.
            for b in grid["B_full"]:
                sv_mod.sample_sv_quotient(
                    pz,
                    accept,
                    value,
                    sv_coeffs["mu_SV"] * 0.0 + a,
                    int(b),
                    grid["T_full"],
                    rng,
                )

    _check_all_cells_seen(label, csv_cells, cells)
    _abort_on_self_check_failure(label, cells)
    return _summarize_dataset(label, seed, cells)


def _fit_vd_cell(
    label: str,
    model,
    p: float,
    b_grid: np.ndarray,
    t: int,
    estimates_by_b: list[np.ndarray],
    csv_cell: dict,
    vd_coeffs: dict,
) -> CellResult:
    means = np.asarray([float(est.mean()) for est in estimates_by_b], dtype=np.float64)
    sample_stds = np.asarray([float(est.std(ddof=1)) for est in estimates_by_b], dtype=np.float64)
    ses = np.maximum(sample_stds / np.sqrt(t), 1e-12)
    biases = means - float(vd_coeffs["mu_VD"])

    inv_b = 1.0 / np.asarray(b_grid, dtype=np.float64)
    design = np.column_stack([inv_b, inv_b**2])
    weights = 1.0 / ses**2
    coeffs, cov = wls_fit(design, biases, weights)
    c_hat = float(coeffs[0])
    analytic_se = float(np.sqrt(cov[0, 0]))

    c_hat_csv = float(csv_cell["c_slope_estimate"])
    analytic_se_csv = _se_from_ci(
        float(csv_cell["c_slope_ci_lower"]),
        float(csv_cell["c_slope_ci_upper"]),
    )
    c_closed = float(vd_coeffs["mu_VD"] * (1.0 - vd_coeffs["D_M"] ** 2) / vd_coeffs["D_M"] ** 2)

    bootstrap_se = _fixed_weight_linear_bootstrap_se(design, weights, sample_stds, t)
    z_analytic = (c_hat_csv - c_closed) / analytic_se_csv
    z_bootstrap = (c_hat_csv - c_closed) / bootstrap_se

    return CellResult(
        dataset=label,
        instance_id=model.inst.name,
        noise_strength=p,
        c_hat=c_hat_csv,
        c_closed=c_closed,
        analytic_se=analytic_se_csv,
        bootstrap_se=bootstrap_se,
        se_ratio=bootstrap_se / analytic_se_csv,
        z_analytic=z_analytic,
        z_bootstrap=z_bootstrap,
        c_slope_abs_diff=abs(c_hat - c_hat_csv),
        analytic_se_abs_diff=abs(analytic_se - analytic_se_csv),
    )


def _fixed_weight_linear_bootstrap_se(
    design: np.ndarray,
    weights: np.ndarray,
    sample_stds: np.ndarray,
    t: int,
) -> float:
    """Exact SE of the fixed-weight WLS slope under replica resampling.

    The confirmatory c estimator fixes the WLS weights at the per-B empirical SE.
    With those weights fixed, the fitted slope is linear in the B-level means:

        c = l @ (mean_B - mu_pop).

    For the nonparametric bootstrap that resamples T replicas with replacement at
    each B, Var(mean_B*) = var_empirical_B / T = ((T - 1) / T) * s_B^2 / T, where
    s_B is the ddof=1 sample standard deviation. This is the exact bootstrap
    moment corresponding to the requested replica resampling, without Monte Carlo
    index materialization.
    """
    xtwx_inv = np.linalg.inv((design * weights[:, None]).T @ design)
    linear_weights = (xtwx_inv @ (design.T * weights))[0, :]
    boot_mean_vars = ((t - 1.0) / t) * (sample_stds**2 / t)
    return float(np.sqrt(np.sum((linear_weights**2) * boot_mean_vars)))


def _summarize_dataset(label: str, seed: int, cells: list[CellResult]) -> DatasetResult:
    z_analytic = np.asarray([cell.z_analytic for cell in cells], dtype=np.float64)
    z_bootstrap = np.asarray([cell.z_bootstrap for cell in cells], dtype=np.float64)
    ratios = np.asarray([cell.se_ratio for cell in cells], dtype=np.float64)

    inst_analytic = _instance_average_z(cells, "analytic")
    inst_bootstrap = _instance_average_z(cells, "bootstrap")

    return DatasetResult(
        label=label,
        seed=seed,
        cells=cells,
        analytic_chi2=float(np.sum(z_analytic**2)),
        analytic_p=float(chi2.sf(np.sum(z_analytic**2), z_analytic.size)),
        analytic_mean_z=float(np.mean(z_analytic)),
        bootstrap_chi2=float(np.sum(z_bootstrap**2)),
        bootstrap_p=float(chi2.sf(np.sum(z_bootstrap**2), z_bootstrap.size)),
        bootstrap_mean_z=float(np.mean(z_bootstrap)),
        median_se_ratio=float(np.median(ratios)),
        min_se_ratio=float(np.min(ratios)),
        max_se_ratio=float(np.max(ratios)),
        instance_analytic_chi2=float(np.sum(inst_analytic**2)),
        instance_analytic_p=float(chi2.sf(np.sum(inst_analytic**2), inst_analytic.size)),
        instance_analytic_mean_z=float(np.mean(inst_analytic)),
        instance_bootstrap_chi2=float(np.sum(inst_bootstrap**2)),
        instance_bootstrap_p=float(chi2.sf(np.sum(inst_bootstrap**2), inst_bootstrap.size)),
        instance_bootstrap_mean_z=float(np.mean(inst_bootstrap)),
        max_c_slope_abs_diff=max(cell.c_slope_abs_diff for cell in cells),
        max_analytic_se_abs_diff=max(cell.analytic_se_abs_diff for cell in cells),
    )


def _instance_average_z(cells: list[CellResult], kind: str) -> np.ndarray:
    grouped: dict[str, list[float]] = defaultdict(list)
    for cell in cells:
        value = cell.z_analytic if kind == "analytic" else cell.z_bootstrap
        grouped[cell.instance_id].append(value)
    return np.asarray(
        [float(np.mean(grouped[instance_id])) for instance_id in sorted(grouped)],
        dtype=np.float64,
    )


def _load_confirmatory_c_vd(path: Path) -> dict[tuple[str, str], dict]:
    rows = _read_csv(path)
    cells: dict[tuple[str, str], dict] = {}
    for row in rows:
        if row["method"] != "vd":
            continue
        key = (row["instance_id"], _p_key(float(row["noise_strength"])))
        cells[key] = row
    return cells


def _load_e2_grid() -> dict:
    with GRID_PATH.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    e2 = cfg["experiments"]["e2_c_sv_zero"]
    return {
        "p_grid": np.asarray(e2["p_grid"], dtype=np.float64),
        "B_full": np.asarray(e2["B_full"], dtype=np.float64),
        "T_full": int(e2["T_full"]),
    }


def _load_e2_seed(path: Path) -> int:
    with path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return int(cfg["per_experiment_seed"]["e2_c_sv_zero"])


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _se_from_ci(lo: float, hi: float) -> float:
    return (hi - lo) / (2.0 * 1.96)


def _p_key(p: float) -> str:
    return f"{p:.6f}"


def _check_all_cells_seen(label: str, csv_cells: dict, cells: list[CellResult]) -> None:
    seen = {(cell.instance_id, _p_key(cell.noise_strength)) for cell in cells}
    expected = set(csv_cells)
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing or extra:
        raise SystemExit(
            f"{label}: VD cell mismatch. missing={missing[:5]} extra={extra[:5]}"
        )


def _abort_on_self_check_failure(label: str, cells: list[CellResult]) -> None:
    bad = [
        cell for cell in cells
        if cell.c_slope_abs_diff > SELF_CHECK_ATOL
        or cell.analytic_se_abs_diff > SELF_CHECK_ATOL
    ]
    if not bad:
        return
    lines = [
        "# c_VD SE Sensitivity",
        "",
        "Status: post_adjudication_sensitivity_only. Not a gate, not an adjudication, not a freeze.",
        "",
        "ABORTED: E2 replay self-check failed; bootstrap was not run on nonmatching data.",
        "",
        "| Dataset | Instance | p | abs c_slope diff | abs analytic SE diff |",
        "|---|---|---:|---:|---:|",
    ]
    for cell in bad[:20]:
        lines.append(
            f"| {cell.dataset} | {cell.instance_id} | {cell.noise_strength:.6g} | "
            f"{cell.c_slope_abs_diff:.3e} | {cell.analytic_se_abs_diff:.3e} |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    raise SystemExit(f"{label}: E2 replay self-check failed for {len(bad)} cells")


def _render_report(results: list[DatasetResult]) -> str:
    lines = [
        "# c_VD SE Sensitivity",
        "",
        "Status: post_adjudication_sensitivity_only. Not a gate, not an adjudication, not a freeze.",
        "",
        f"Bootstrap target: N_boot={N_BOOT}, bootstrap_seed={BOOTSTRAP_SEED}.",
        "",
        "Implementation note: the confirmatory WLS slope is linear in the per-B means when the original WLS weights are fixed. The script therefore reports the exact nonparametric bootstrap SE implied by resampling the T estimator replicas at each B, instead of materializing Monte Carlo index draws. This removes bootstrap Monte Carlo noise while preserving the requested replica-resampling variance for the fixed-weight estimator.",
        "",
        "Causal interpretation is intentionally open: any residual flag is described as probable miscalibration of the analytic SE under the fitted design / dependent finite-shot structure, not as a closed claim about collinearity alone.",
        "",
        "## Replay Self-Check",
        "",
        "| Dataset | E2 seed | cells | max abs c_slope diff | max abs analytic SE diff |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| {result.label} | {result.seed} | {len(result.cells)} | "
            f"{result.max_c_slope_abs_diff:.3e} | {result.max_analytic_se_abs_diff:.3e} |"
        )
    lines.extend([
        "",
        "## Cell-Level Pooled c_VD",
        "",
        "| Dataset | n cells | median SE_boot/SE_analytic | ratio range | analytic chi2_30 | analytic p | bootstrap chi2_30 | bootstrap p | analytic mean(z) | bootstrap mean(z) | Conclusion |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ])
    for result in results:
        lines.append(
            f"| {result.label} | {len(result.cells)} | {result.median_se_ratio:.6f} | "
            f"{result.min_se_ratio:.6f}-{result.max_se_ratio:.6f} | "
            f"{result.analytic_chi2:.3f} | {result.analytic_p:.4g} | "
            f"{result.bootstrap_chi2:.3f} | {result.bootstrap_p:.4g} | "
            f"{result.analytic_mean_z:.3f} | {result.bootstrap_mean_z:.3f} | "
            f"{_dataset_conclusion(result)} |"
        )
    lines.extend([
        "",
        "## Instance-Aggregated Pooled c_VD",
        "",
        "Aggregation: one z per instance, computed as the unscaled average of its three p-cell z values. This is a conservative dependence check because it does not treat the three p cells as fully independent evidence.",
        "",
        "| Dataset | n instances | analytic chi2_10 | analytic p | bootstrap chi2_10 | bootstrap p | analytic mean(instance z) | bootstrap mean(instance z) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for result in results:
        n_instances = len({cell.instance_id for cell in result.cells})
        lines.append(
            f"| {result.label} | {n_instances} | "
            f"{result.instance_analytic_chi2:.3f} | {result.instance_analytic_p:.4g} | "
            f"{result.instance_bootstrap_chi2:.3f} | {result.instance_bootstrap_p:.4g} | "
            f"{result.instance_analytic_mean_z:.3f} | {result.instance_bootstrap_mean_z:.3f} |"
        )
    lines.extend([
        "",
        "## Dataset Conclusions",
        "",
    ])
    for result in results:
        lines.append(f"- {result.label}: {_long_conclusion(result)}")
    return "\n".join(lines) + "\n"


def _dataset_conclusion(result: DatasetResult) -> str:
    if result.bootstrap_p > 0.05 and result.median_se_ratio > 1.0:
        return "bootstrap SE quantifies analytic-SE miscalibration; cell-level flag attenuates"
    if result.bootstrap_p > 0.05:
        return "bootstrap pooled statistic is consistent; no gate interpretation"
    return "cell-level inconsistency remains under this sensitivity"


def _long_conclusion(result: DatasetResult) -> str:
    no_bias = abs(result.bootstrap_mean_z) < 0.5
    if result.bootstrap_p > 0.05 and result.median_se_ratio > 1.0:
        bias_text = "mean(z) remains close to zero" if no_bias else "mean(z) is not negligible"
        return (
            "SE_boot is larger than SE_analytic and the bootstrap pooled statistic is "
            f"consistent at p={result.bootstrap_p:.4g}; {bias_text}. This supports the "
            "interpretation that the original flag is attributable to probable "
            "miscalibration of the analytic SE under the fitted design / dependent "
            "finite-shot structure."
        )
    if result.bootstrap_p > 0.05:
        return (
            "the bootstrap pooled statistic is consistent, but the SE ratio does not "
            "show inflation of the analytic SE. Treat this as a sensitivity statistic, "
            "not a new adjudication."
        )
    bias_text = "mean(z) remains close to zero" if no_bias else "mean(z) is not negligible"
    return (
        "the fixed-weight replica bootstrap does not resolve the cell-level pooled "
        f"flag (p={result.bootstrap_p:.4g}); {bias_text}. This leaves a residual "
        "SE/dependence calibration issue to investigate rather than evidence of a "
        "systematic c_VD extraction bias or theory failure."
    )


if __name__ == "__main__":
    raise SystemExit(main())
