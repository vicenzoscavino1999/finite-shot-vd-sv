"""E6 secondary descriptive endpoint: logarithmic copy scale for VD.

This additive runner implements P8 without modifying the frozen reproduction
pipeline. It reads the frozen lambda2-gap table, selects the E6 candidate by the
precondition specified there, and writes its own secondary output files.

Status: secondary descriptive endpoint (family P7-P13, not primary FWER).
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402

LAMBDA2_TABLE = REPO_ROOT / "results" / "frozen" / "lambda2_gap_table.csv"
OUTDIR = REPO_ROOT / "results" / "secondary"
CSV_PATH = OUTDIR / "e6_copy_log_scale.csv"
REPORT_PATH = OUTDIR / "e6_copy_log_scale_report.md"

D_M_FLOOR = 1e-3
B_GRID_N = 240
MIN_UNIQUE_MSTAR_FOR_RESOLVED = 4
SLOPE_REL_TOL = 0.35
Q_DECAY_REL_TOL = 0.15
V_GROWTH_REL_TOL = 0.05

FIELDS = [
    "row_kind",
    "instance_id",
    "noise_strength",
    "selection_basis",
    "copies_M",
    "D_M",
    "b_VD",
    "b_VD_minus_b_inf",
    "v_tilde_VD",
    "B",
    "log_B",
    "m_star",
    "mse_min",
    "lambda1",
    "lambda2",
    "q_lambda2_over_lambda1",
    "slope_measured",
    "slope_ci_lo",
    "slope_ci_hi",
    "slope_predicted",
    "rel_error",
    "mstar_unique_count",
    "mstar_status",
    "q_decay_slope_measured",
    "q_decay_slope_predicted",
    "q_decay_rel_error",
    "q_decay_check",
    "q_decay_fit_n",
    "v_growth_slope_measured",
    "v_growth_slope_predicted",
    "v_growth_rel_error",
    "v_growth_check",
    "v_growth_fit_n",
    "d_m_floor",
]


@dataclass(frozen=True)
class Selection:
    instance_id: str
    p: float
    lambda1: float
    lambda2: float
    relative_gap: float
    basis: str


@dataclass(frozen=True)
class Summary:
    selection: Selection
    m_max: int
    b_inf: float
    slope_measured: float
    slope_ci_lo: float
    slope_ci_hi: float
    slope_predicted: float
    rel_error: float
    mstar_unique_count: int
    mstar_status: str
    q_decay_slope_measured: float
    q_decay_slope_predicted: float
    q_decay_rel_error: float
    q_decay_check: str
    q_decay_fit_n: int
    v_growth_slope_measured: float
    v_growth_slope_predicted: float
    v_growth_rel_error: float
    v_growth_check: str
    v_growth_fit_n: int


def main() -> int:
    selection = select_e6_candidate()
    model = _model_by_instance(selection.instance_id)
    copy_rows = compute_copy_rows(model, selection.p)
    b_rows, summary = compute_b_grid_rows(selection, copy_rows, model)
    rows = copy_rows + b_rows

    OUTDIR.mkdir(parents=True, exist_ok=True)
    _write_csv(CSV_PATH, rows)
    REPORT_PATH.write_text(render_report(summary, copy_rows, b_rows), encoding="utf-8")
    print(CSV_PATH)
    print(REPORT_PATH)
    return 0


def select_e6_candidate() -> Selection:
    rows = _read_csv(LAMBDA2_TABLE)
    candidates = [row for row in rows if row["e6_candidate"].strip().lower() == "yes"]
    if not candidates:
        raise RuntimeError("lambda2_gap_table.csv has no e6_candidate=yes rows")
    best = max(candidates, key=lambda row: float(row["relative_gap"]))
    return Selection(
        instance_id=best["instance_id"],
        p=float(best["noise_strength"]),
        lambda1=float(best["lambda1"]),
        lambda2=float(best["lambda2"]),
        relative_gap=float(best["relative_gap"]),
        basis=(
            "e6_candidate=yes in frozen lambda2_gap_table.csv; selected p with "
            "maximum relative_gap for that frozen instance"
        ),
    )


def compute_copy_rows(model, p: float) -> list[dict]:
    b_inf = float(model.vd_floor(p)["b_VD_inf"])
    rows: list[dict] = []
    for m in range(2, 1000):
        coeff = model.vd(p, m)
        d_m = float(coeff["D_M"])
        if d_m < D_M_FLOOR:
            break
        rows.append({
            "row_kind": "copy",
            "instance_id": model.inst.name,
            "noise_strength": p,
            "selection_basis": "",
            "copies_M": m,
            "D_M": d_m,
            "b_VD": float(coeff["b_VD"]),
            "b_VD_minus_b_inf": float(coeff["b_VD"] - b_inf),
            "v_tilde_VD": float(coeff["v_tilde_VD"]),
            "B": "",
            "log_B": "",
            "m_star": "",
            "mse_min": "",
        })
    if not rows:
        raise RuntimeError(f"no M>=2 has D_M >= {D_M_FLOOR:g}")
    return rows


def compute_b_grid_rows(selection: Selection, copy_rows: list[dict], model) -> tuple[list[dict], Summary]:
    abs_log_l2 = abs(math.log(selection.lambda2))
    slope_pred = 1.0 / (2.0 * abs_log_l2)
    m_values = np.asarray([int(row["copies_M"]) for row in copy_rows], dtype=np.int64)
    b_values = np.asarray([float(row["b_VD"]) for row in copy_rows], dtype=np.float64)
    v_values = np.asarray([float(row["v_tilde_VD"]) for row in copy_rows], dtype=np.float64)

    # The theoretical scale is M_B = log(B)/(2|log lambda2|). The grid spans
    # targets from M=2 to the D_M floor-limited M_max, capped below exp overflow.
    target_m_lo = float(m_values.min())
    target_m_hi = float(min(m_values.max(), 68))
    log_b_lo = 2.0 * abs_log_l2 * target_m_lo
    log_b_hi = min(2.0 * abs_log_l2 * target_m_hi, 700.0)
    log_b = np.linspace(log_b_lo, log_b_hi, B_GRID_N, dtype=np.float64)
    b_grid = np.exp(log_b)
    mse = b_values[:, None] ** 2 + v_values[:, None] / b_grid[None, :]
    winner = np.argmin(mse, axis=0)
    m_star = m_values[winner]
    mse_min = mse[winner, np.arange(log_b.size)]

    slope, slope_ci_lo, slope_ci_hi = _ols_slope_ci(log_b, m_star.astype(np.float64))
    rel_error = _relative_error(slope, slope_pred)
    unique_count = int(np.unique(m_star).size)
    mstar_status = (
        "resolved"
        if unique_count >= MIN_UNIQUE_MSTAR_FOR_RESOLVED and abs(rel_error) <= SLOPE_REL_TOL
        else "not_resolvable"
    )

    b_inf = float(model.vd_floor(selection.p)["b_VD_inf"])
    q_decay = _q_decay_check(copy_rows, selection.lambda1, selection.lambda2)
    v_growth = _v_growth_check(copy_rows, selection.lambda1)
    summary = Summary(
        selection=selection,
        m_max=int(m_values.max()),
        b_inf=b_inf,
        slope_measured=slope,
        slope_ci_lo=slope_ci_lo,
        slope_ci_hi=slope_ci_hi,
        slope_predicted=slope_pred,
        rel_error=rel_error,
        mstar_unique_count=unique_count,
        mstar_status=mstar_status,
        q_decay_slope_measured=q_decay["slope"],
        q_decay_slope_predicted=q_decay["predicted"],
        q_decay_rel_error=q_decay["rel_error"],
        q_decay_check=q_decay["check"],
        q_decay_fit_n=q_decay["n"],
        v_growth_slope_measured=v_growth["slope"],
        v_growth_slope_predicted=v_growth["predicted"],
        v_growth_rel_error=v_growth["rel_error"],
        v_growth_check=v_growth["check"],
        v_growth_fit_n=v_growth["n"],
    )

    common = _summary_fields(summary)
    rows = []
    for b, lb, m, mm in zip(b_grid, log_b, m_star, mse_min):
        row = {
            "row_kind": "B_grid",
            "instance_id": selection.instance_id,
            "noise_strength": selection.p,
            "selection_basis": selection.basis,
            "copies_M": "",
            "D_M": "",
            "b_VD": "",
            "b_VD_minus_b_inf": "",
            "v_tilde_VD": "",
            "B": float(b),
            "log_B": float(lb),
            "m_star": int(m),
            "mse_min": float(mm),
        }
        row.update(common)
        rows.append(row)

    for row in copy_rows:
        row.update(common)
        row["selection_basis"] = selection.basis
    return rows, summary


def _q_decay_check(copy_rows: list[dict], lambda1: float, lambda2: float) -> dict:
    m = np.asarray([int(row["copies_M"]) for row in copy_rows], dtype=np.float64)
    diff = np.abs(np.asarray([float(row["b_VD_minus_b_inf"]) for row in copy_rows], dtype=np.float64))
    threshold = max(1e-14, 1e-10 * float(np.max(diff)))
    mask = diff > threshold
    predicted = math.log(lambda2 / lambda1)
    if int(mask.sum()) < 4:
        return {
            "slope": float("nan"),
            "predicted": predicted,
            "rel_error": float("nan"),
            "check": "NOT_RESOLVABLE_NUMERICAL_FLOOR",
            "n": int(mask.sum()),
        }
    slope = float(np.polyfit(m[mask], np.log(diff[mask]), 1)[0])
    rel = _relative_error(slope, predicted)
    return {
        "slope": slope,
        "predicted": predicted,
        "rel_error": rel,
        "check": "PASS" if abs(rel) <= Q_DECAY_REL_TOL else "FAIL",
        "n": int(mask.sum()),
    }


def _v_growth_check(copy_rows: list[dict], lambda1: float) -> dict:
    m = np.asarray([int(row["copies_M"]) for row in copy_rows], dtype=np.float64)
    values = np.asarray([float(row["v_tilde_VD"]) for row in copy_rows], dtype=np.float64)
    mask = values > 0.0
    predicted = -2.0 * math.log(lambda1)
    if int(mask.sum()) < 4:
        return {
            "slope": float("nan"),
            "predicted": predicted,
            "rel_error": float("nan"),
            "check": "NOT_RESOLVABLE",
            "n": int(mask.sum()),
        }
    slope = float(np.polyfit(m[mask], np.log(values[mask]), 1)[0])
    rel = _relative_error(slope, predicted)
    return {
        "slope": slope,
        "predicted": predicted,
        "rel_error": rel,
        "check": "PASS" if abs(rel) <= V_GROWTH_REL_TOL else "FAIL",
        "n": int(mask.sum()),
    }


def _ols_slope_ci(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    design = np.column_stack([np.ones_like(x), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ coeffs
    dof = max(y.size - 2, 1)
    s2 = float(residuals @ residuals) / dof
    cov = s2 * np.linalg.inv(design.T @ design)
    se = math.sqrt(float(cov[1, 1]))
    slope = float(coeffs[1])
    return slope, slope - 1.96 * se, slope + 1.96 * se


def render_report(summary: Summary, copy_rows: list[dict], b_rows: list[dict]) -> str:
    selected = summary.selection
    observed_m = sorted({int(row["m_star"]) for row in b_rows})
    if summary.mstar_status == "resolved":
        conclusion = (
            "The integer M*(B) path spans enough values to estimate the log-copy "
            "slope descriptively."
        )
    else:
        conclusion = (
            "The frozen E6 candidate/p is not resolvable for the total MSE curve: "
            "the infinite-copy floor is reached within a few copies, so M*(B) does "
            "not span enough integers to support the advertised slope regression."
        )
    lines = [
        "# E6 Copy Log Scale",
        "",
        "Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.",
        "",
        "## Selection",
        "",
        f"- Instance: `{selected.instance_id}`",
        f"- p: `{selected.p:.6g}`",
        f"- Selection basis: {selected.basis}.",
        f"- lambda1: `{selected.lambda1:.15g}`",
        f"- lambda2: `{selected.lambda2:.15g}`",
        f"- relative_gap: `{selected.relative_gap:.6g}`",
        f"- D_M floor: `{D_M_FLOOR:g}`; M_max: `{summary.m_max}`",
        "",
        "## P8 Slope",
        "",
        "| measured slope | 95% CI | predicted slope | relative error | unique M*(B) | status |",
        "|---:|---:|---:|---:|---:|---|",
        (
            f"| {summary.slope_measured:.6g} | "
            f"[{summary.slope_ci_lo:.6g}, {summary.slope_ci_hi:.6g}] | "
            f"{summary.slope_predicted:.6g} | {summary.rel_error:.6g} | "
            f"{summary.mstar_unique_count} | {summary.mstar_status} |"
        ),
        "",
        conclusion,
        "",
        "## Theorem Hypothesis Checks",
        "",
        "| check | measured slope | predicted slope | relative error | fit n | status |",
        "|---|---:|---:|---:|---:|---|",
        (
            f"| copy leakage b_M-b_inf ~ q^M | {summary.q_decay_slope_measured:.6g} | "
            f"{summary.q_decay_slope_predicted:.6g} | {summary.q_decay_rel_error:.6g} | "
            f"{summary.q_decay_fit_n} | {summary.q_decay_check} |"
        ),
        (
            f"| v_tilde_M ~ lambda1^(-2M) | {summary.v_growth_slope_measured:.6g} | "
            f"{summary.v_growth_slope_predicted:.6g} | {summary.v_growth_rel_error:.6g} | "
            f"{summary.v_growth_fit_n} | {summary.v_growth_check} |"
        ),
        "",
        "## D_M Copy Range",
        "",
        "| first M | last M | D_M(first) | D_M(last) | observed M*(B) values |",
        "|---:|---:|---:|---:|---|",
        (
            f"| {int(copy_rows[0]['copies_M'])} | {int(copy_rows[-1]['copies_M'])} | "
            f"{float(copy_rows[0]['D_M']):.6g} | {float(copy_rows[-1]['D_M']):.6g} | "
            f"{', '.join(str(m) for m in observed_m)} |"
        ),
        "",
        "## Descriptive Conclusion",
        "",
        (
            "P8 is reported descriptively only. For the frozen gap-selected E6 "
            f"configuration, the measured slope is {summary.slope_measured:.6g} "
            f"versus predicted {summary.slope_predicted:.6g}. The leakage and "
            "variance hypothesis checks are shown above; the M*(B) slope should not "
            "be promoted to a primary gate or a freeze amendment."
        ),
    ]
    return "\n".join(lines) + "\n"


def _summary_fields(summary: Summary) -> dict:
    return {
        "lambda1": summary.selection.lambda1,
        "lambda2": summary.selection.lambda2,
        "q_lambda2_over_lambda1": summary.selection.lambda2 / summary.selection.lambda1,
        "slope_measured": summary.slope_measured,
        "slope_ci_lo": summary.slope_ci_lo,
        "slope_ci_hi": summary.slope_ci_hi,
        "slope_predicted": summary.slope_predicted,
        "rel_error": summary.rel_error,
        "mstar_unique_count": summary.mstar_unique_count,
        "mstar_status": summary.mstar_status,
        "q_decay_slope_measured": summary.q_decay_slope_measured,
        "q_decay_slope_predicted": summary.q_decay_slope_predicted,
        "q_decay_rel_error": summary.q_decay_rel_error,
        "q_decay_check": summary.q_decay_check,
        "q_decay_fit_n": summary.q_decay_fit_n,
        "v_growth_slope_measured": summary.v_growth_slope_measured,
        "v_growth_slope_predicted": summary.v_growth_slope_predicted,
        "v_growth_rel_error": summary.v_growth_rel_error,
        "v_growth_check": summary.v_growth_check,
        "v_growth_fit_n": summary.v_growth_fit_n,
        "d_m_floor": D_M_FLOOR,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _model_by_instance(instance_id: str):
    models = {model.inst.name: model for model in frozen_models()}
    try:
        return models[instance_id]
    except KeyError as exc:
        raise RuntimeError(f"frozen_models() does not contain {instance_id}") from exc


def _relative_error(measured: float, predicted: float) -> float:
    return (measured - predicted) / predicted


if __name__ == "__main__":
    raise SystemExit(main())
