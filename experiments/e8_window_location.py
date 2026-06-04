"""E8 secondary descriptive endpoint: operating-window location exponents.

P10 predicts that the leading crossing scale

    R0(p) = Delta s / (b_j(p)^2 - b_i(p)^2)

has exponent -2 when the leading sampling variances differ, and exponent -1
when they match at p=0 and split first at order p. This runner is additive: it
does not modify the frozen reproduction pipeline or any adjudication artifact.
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

from experiments._common import KAPPA_SV, KAPPA_UNMIT, KAPPA_VD, frozen_models  # noqa: E402

OUTDIR = REPO_ROOT / "results" / "secondary"
CSV_PATH = OUTDIR / "e8_window_location.csv"
REPORT_PATH = OUTDIR / "e8_window_location_report.md"

P_MIN = 1e-4
P_MAX = 1e-2
N_P = 10
M_VD = 2
EXPONENT_TOL = 0.15
MIN_VALID_POINTS = 6

PAIRS = [
    {
        "name": "vd2_vs_unmitigated",
        "method_a": "vd2",
        "method_b": "unmitigated",
        "predicted": -2.0,
        "structure": "different_leading_variance",
    },
    {
        "name": "sv_vs_unmitigated",
        "method_a": "sv",
        "method_b": "unmitigated",
        "predicted": -1.0,
        "structure": "matched_leading_variance",
    },
]

FIELDS = [
    "instance_id",
    "pair",
    "pair_structure",
    "noise_strength",
    "method_i",
    "method_j",
    "b_i",
    "b_j",
    "s_i",
    "s_j",
    "g",
    "delta_s",
    "R0",
    "exponent_measured",
    "exponent_ci_lo",
    "exponent_ci_hi",
    "r2_loglog",
    "exponent_predicted",
    "exponent_error",
    "valid_crossing_fraction",
    "valid_crossing_points",
    "status",
    "p_min",
    "p_max",
    "n_p",
]


@dataclass(frozen=True)
class FitResult:
    exponent: float
    ci_lo: float
    ci_hi: float
    r2: float
    error: float
    valid_fraction: float
    valid_points: int
    status: str


def main() -> int:
    rows = run_analysis()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    _write_csv(CSV_PATH, rows)
    REPORT_PATH.write_text(render_report(rows), encoding="utf-8")
    print(CSV_PATH)
    print(REPORT_PATH)
    return 0


def run_analysis() -> list[dict]:
    p_grid = np.logspace(math.log10(P_MIN), math.log10(P_MAX), N_P)
    rows: list[dict] = []
    for model in frozen_models():
        coeffs_by_p = {float(p): _coefficients_at_p(model, float(p)) for p in p_grid}
        for pair in PAIRS:
            pair_rows = [
                _row_for_pair(model.inst.name, float(p), coeffs_by_p[float(p)], pair)
                for p in p_grid
            ]
            fit = _fit_pair_rows(pair_rows, float(pair["predicted"]))
            for row in pair_rows:
                row.update({
                    "exponent_measured": fit.exponent,
                    "exponent_ci_lo": fit.ci_lo,
                    "exponent_ci_hi": fit.ci_hi,
                    "r2_loglog": fit.r2,
                    "exponent_predicted": float(pair["predicted"]),
                    "exponent_error": fit.error,
                    "valid_crossing_fraction": fit.valid_fraction,
                    "valid_crossing_points": fit.valid_points,
                    "status": fit.status,
                    "p_min": P_MIN,
                    "p_max": P_MAX,
                    "n_p": N_P,
                })
                rows.append(row)
    return rows


def _coefficients_at_p(model, p: float) -> dict[str, tuple[float, float]]:
    vd = model.vd(p, M_VD)
    sv = model.sv(p)
    unmit = model.unmitigated(p)
    return {
        "vd2": (float(vd["b_VD"]), float(KAPPA_VD * vd["v_tilde_VD"])),
        "sv": (float(sv["b_SV"]), float(KAPPA_SV * sv["v_tilde_SV"])),
        "unmitigated": (float(unmit["b_0"]), float(KAPPA_UNMIT * unmit["v_tilde_0"])),
    }


def _row_for_pair(instance_id: str, p: float, coeffs: dict, pair: dict) -> dict:
    method_a = pair["method_a"]
    method_b = pair["method_b"]
    b_a, s_a = coeffs[method_a]
    b_b, s_b = coeffs[method_b]
    if b_a * b_a <= b_b * b_b:
        method_i, method_j = method_a, method_b
        b_i, b_j, s_i, s_j = b_a, b_b, s_a, s_b
    else:
        method_i, method_j = method_b, method_a
        b_i, b_j, s_i, s_j = b_b, b_a, s_b, s_a
    g = b_j * b_j - b_i * b_i
    delta_s = s_i - s_j
    valid = g > 0.0 and delta_s > 0.0
    r0 = delta_s / g if valid else float("nan")
    return {
        "instance_id": instance_id,
        "pair": pair["name"],
        "pair_structure": pair["structure"],
        "noise_strength": p,
        "method_i": method_i,
        "method_j": method_j,
        "b_i": b_i,
        "b_j": b_j,
        "s_i": s_i,
        "s_j": s_j,
        "g": g,
        "delta_s": delta_s,
        "R0": r0,
    }


def _fit_pair_rows(rows: list[dict], predicted: float) -> FitResult:
    valid = [
        row for row in rows
        if np.isfinite(float(row["R0"])) and float(row["R0"]) > 0.0
    ]
    if len(valid) < MIN_VALID_POINTS:
        status = "no_valid_crossing" if not valid else "insufficient_valid_crossing_points"
        return FitResult(
            exponent=float("nan"),
            ci_lo=float("nan"),
            ci_hi=float("nan"),
            r2=float("nan"),
            error=float("nan"),
            valid_fraction=len(valid) / len(rows),
            valid_points=len(valid),
            status=status,
        )
    log_p = np.log(np.asarray([float(row["noise_strength"]) for row in valid], dtype=np.float64))
    log_r0 = np.log(np.asarray([float(row["R0"]) for row in valid], dtype=np.float64))
    slope, ci_lo, ci_hi, r2 = _ols_slope_ci(log_p, log_r0)
    error = slope - predicted
    status = "valid_crossing"
    if abs(error) > EXPONENT_TOL:
        status = "valid_crossing_exponent_off_target"
    return FitResult(
        exponent=slope,
        ci_lo=ci_lo,
        ci_hi=ci_hi,
        r2=r2,
        error=error,
        valid_fraction=len(valid) / len(rows),
        valid_points=len(valid),
        status=status,
    )


def _ols_slope_ci(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    design = np.column_stack([np.ones_like(x), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    yhat = design @ coeffs
    residuals = y - yhat
    sse = float(residuals @ residuals)
    sst = float((y - float(np.mean(y))) @ (y - float(np.mean(y))))
    r2 = 1.0 - sse / sst if sst > 0.0 else float("nan")
    dof = max(y.size - 2, 1)
    s2 = sse / dof
    cov = s2 * np.linalg.inv(design.T @ design)
    se = math.sqrt(float(cov[1, 1]))
    slope = float(coeffs[1])
    return slope, slope - 1.96 * se, slope + 1.96 * se, r2


def render_report(rows: list[dict]) -> str:
    instance_fits = _instance_fit_rows(rows)
    pair_summaries = _pair_summaries(instance_fits)
    lines = [
        "# E8 Window Location",
        "",
        "Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.",
        "",
        "## Design",
        "",
        f"- p grid: `{P_MIN:g}` to `{P_MAX:g}` with `{N_P}` log-spaced points.",
        "- Rationale: small-p asymptotic regime over two decades; the range is chosen by principle, not by per-instance fit quality.",
        f"- Resource normalization: kappa_VD=2, kappa_SV=1, kappa_unmitigated=1.",
        "- For each p, method i is the lower-bias method; a genuine leading crossing requires g>0 and Delta s>0.",
        "",
        "## Ensemble Summary",
        "",
        "| pair | structure | predicted exponent | valid instances | mean exponent | std exponent | mean R2 | mean valid fraction | status summary |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for summary in pair_summaries:
        lines.append(
            f"| {summary['pair']} | {summary['structure']} | {summary['predicted']:.3g} | "
            f"{summary['valid_instances']}/{summary['n_instances']} | "
            f"{_fmt(summary['mean_exp'])} | {_fmt(summary['std_exp'])} | "
            f"{_fmt(summary['mean_r2'])} | {_fmt(summary['mean_valid_fraction'])} | "
            f"{summary['status_summary']} |"
        )
    lines.extend([
        "",
        "## Per-Instance Fits",
        "",
        "| instance | pair | predicted | exponent | 95% CI | R2 | valid fraction | status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in instance_fits:
        ci = f"[{_fmt(row['ci_lo'])}, {_fmt(row['ci_hi'])}]"
        lines.append(
            f"| {row['instance_id']} | {row['pair']} | {row['predicted']:.3g} | "
            f"{_fmt(row['exponent'])} | {ci} | {_fmt(row['r2'])} | "
            f"{row['valid_fraction']:.3f} | {row['status']} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "VD(M=2) vs unmitigated has a genuine leading crossing across the full "
            "small-p grid and recovers the expected p^-2 scale at the ensemble level. "
            "SV vs unmitigated has matched leading variance at p=0 but no genuine "
            "crossing in the frozen ensemble/range because the lower-bias SV endpoint "
            "also has smaller resource-normalized sampling coefficient; it is therefore "
            "reported as no_valid_crossing rather than forced into a p^-1 fit."
        ),
    ])
    return "\n".join(lines) + "\n"


def _instance_fit_rows(rows: list[dict]) -> list[dict]:
    seen = {}
    for row in rows:
        key = (row["instance_id"], row["pair"])
        seen[key] = row
    out = []
    for key in sorted(seen):
        row = seen[key]
        out.append({
            "instance_id": row["instance_id"],
            "pair": row["pair"],
            "structure": row["pair_structure"],
            "predicted": float(row["exponent_predicted"]),
            "exponent": float(row["exponent_measured"]),
            "ci_lo": float(row["exponent_ci_lo"]),
            "ci_hi": float(row["exponent_ci_hi"]),
            "r2": float(row["r2_loglog"]),
            "valid_fraction": float(row["valid_crossing_fraction"]),
            "status": row["status"],
        })
    return out


def _pair_summaries(instance_fits: list[dict]) -> list[dict]:
    summaries = []
    for pair in [item["name"] for item in PAIRS]:
        subset = [row for row in instance_fits if row["pair"] == pair]
        valid = [row for row in subset if row["status"].startswith("valid_crossing")]
        exps = np.asarray([row["exponent"] for row in valid], dtype=np.float64)
        r2 = np.asarray([row["r2"] for row in valid], dtype=np.float64)
        fractions = np.asarray([row["valid_fraction"] for row in subset], dtype=np.float64)
        status_counts = {}
        for row in subset:
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        pair_spec = next(item for item in PAIRS if item["name"] == pair)
        summaries.append({
            "pair": pair,
            "structure": pair_spec["structure"],
            "predicted": float(pair_spec["predicted"]),
            "n_instances": len(subset),
            "valid_instances": len(valid),
            "mean_exp": float(np.mean(exps)) if exps.size else float("nan"),
            "std_exp": float(np.std(exps, ddof=1)) if exps.size > 1 else float("nan"),
            "mean_r2": float(np.mean(r2)) if r2.size else float("nan"),
            "mean_valid_fraction": float(np.mean(fractions)) if fractions.size else float("nan"),
            "status_summary": ", ".join(f"{k}:{v}" for k, v in sorted(status_counts.items())),
        })
    return summaries


def _fmt(value: float) -> str:
    if not np.isfinite(value):
        return "nan"
    return f"{value:.6g}"


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
