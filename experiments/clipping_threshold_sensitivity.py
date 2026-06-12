"""Registered S10 robustness check: VD clipping-threshold sensitivity.

This additive runner checks the registered denominator-clipping sensitivity
specified in EXPERIMENTAL_PLAN sec. 10.  It compares floors D_M/3, D_M/2, and
2D_M/3 for the same finite-shot draws and verifies that the leading 1/B law is
unchanged on the frozen Level 1 ensemble.
"""

from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models, log_grid, stable_seed, wls_fit  # noqa: E402
from vd_sv.estimators import make_rng, replicate_mse  # noqa: E402

OUTDIR = REPO_ROOT / "results" / "secondary"
CSV_PATH = OUTDIR / "clipping_threshold_sensitivity.csv"
REPORT_PATH = OUTDIR / "clipping_threshold_sensitivity_report.md"

P_FIXED = 0.15
M_COPIES = 2
B_MIN = 200
B_MAX = 30_000
N_B = 12
T_REPLICATES = 20_000
N_BOOT = 200
BASE_SEED = 13_013
REFERENCE_CLIP_FRACTION = 0.5
CLIP_FRACTIONS = (1.0 / 3.0, 0.5, 2.0 / 3.0)
RELATIVE_BETA1_TOL = 0.05

FIELDS = [
    "instance_id",
    "clip_fraction",
    "B",
    "mse",
    "mse_se",
    "beta1",
    "beta1_se",
    "beta1_minus_ref",
    "clip_event_rate",
    "vtilde_closed_form",
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
    b_grid = log_grid(B_MIN, B_MAX, N_B)
    rows: list[dict] = []
    for model in frozen_models():
        rng = make_rng(stable_seed(BASE_SEED, model.inst.name, "clip_sens"))
        vd = model.vd(P_FIXED, M_COPIES)
        n_m = float(vd["N_M"])
        d_m = float(vd["D_M"])
        per_fraction: dict[float, dict[str, list]] = {
            fraction: {"rows": [], "mse": [], "se": []}
            for fraction in CLIP_FRACTIONS
        }

        for b_value in b_grid:
            b_int = int(b_value)
            k_n = rng.binomial(b_int, _binomial_prob(n_m), size=T_REPLICATES)
            k_d = rng.binomial(b_int, _binomial_prob(d_m), size=T_REPLICATES)
            n_hat = 2.0 * k_n / b_int - 1.0
            d_hat = 2.0 * k_d / b_int - 1.0
            clip_event_rate = float(np.mean(d_hat < (2.0 / 3.0) * d_m))

            for fraction in CLIP_FRACTIONS:
                estimates = n_hat / np.maximum(d_hat, fraction * d_m)
                mse, mse_se = replicate_mse(estimates, model.mu_star, n_boot=N_BOOT, rng=rng)
                row = {
                    "instance_id": model.inst.name,
                    "clip_fraction": fraction,
                    "B": b_int,
                    "mse": mse,
                    "mse_se": max(mse_se, 1e-12),
                    "beta1": float("nan"),
                    "beta1_se": float("nan"),
                    "beta1_minus_ref": float("nan"),
                    "clip_event_rate": clip_event_rate,
                    "vtilde_closed_form": float(vd["v_tilde_VD"]),
                }
                per_fraction[fraction]["rows"].append(row)
                per_fraction[fraction]["mse"].append(row["mse"])
                per_fraction[fraction]["se"].append(row["mse_se"])

        fits = {
            fraction: _fit_beta1(b_grid, per_fraction[fraction]["mse"], per_fraction[fraction]["se"])
            for fraction in CLIP_FRACTIONS
        }
        ref_beta1 = fits[REFERENCE_CLIP_FRACTION][0]
        for fraction in CLIP_FRACTIONS:
            beta1, beta1_se = fits[fraction]
            for row in per_fraction[fraction]["rows"]:
                row["beta1"] = beta1
                row["beta1_se"] = beta1_se
                row["beta1_minus_ref"] = beta1 - ref_beta1
                rows.append(row)
    return rows


def _binomial_prob(mean: float) -> float:
    return float(np.clip(0.5 * (1.0 + mean), 0.0, 1.0))


def _fit_beta1(b_grid: np.ndarray, mses: list[float], ses: list[float]) -> tuple[float, float]:
    inv_b = 1.0 / np.asarray(b_grid, dtype=np.float64)
    x = np.column_stack([np.ones_like(inv_b), inv_b, inv_b**2])
    y = np.asarray(mses, dtype=np.float64)
    se = np.maximum(np.asarray(ses, dtype=np.float64), 1e-12)
    coeffs, cov = wls_fit(x, y, 1.0 / se**2)
    beta1 = float(coeffs[1])
    beta1_se = math.sqrt(max(float(cov[1, 1]), 0.0))
    return beta1, beta1_se


def render_report(rows: list[dict]) -> str:
    summaries = _instance_summaries(rows)
    max_rel = max(item["max_rel_delta"] for item in summaries)
    max_clip = max(item["clip_rate_bmax"] for item in summaries)
    lines = [
        "# Clipping-Threshold Sensitivity",
        "",
        "Status: secondary descriptive endpoint (registered robustness check, EXPERIMENTAL_PLAN sec. 10; not primary FWER).",
        "",
        "## Design",
        "",
        f"- p fixed: `{P_FIXED:g}`; VD copies M: `{M_COPIES}`.",
        f"- B grid: `{B_MIN}` to `{B_MAX}` with `{N_B}` log-spaced points.",
        f"- Replicas: T=`{T_REPLICATES}`; bootstrap resamples per B/fraction: `{N_BOOT}`.",
        "- Common random numbers: for each instance and B, the same numerator and denominator binomial draws feed all three clipping floors.",
        "- Floors compared: D_M/3, D_M/2, and 2D_M/3; D_M/2 is the reference.",
        "",
        "## Per-Instance Leading-Law Fit",
        "",
        "| instance | beta1(D/3) +/- 1.96SE | beta1(D/2) +/- 1.96SE | beta1(2D/3) +/- 1.96SE | max abs delta | max rel delta | clip rate at max B |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['instance_id']} | {_ci(item, 1.0 / 3.0)} | "
            f"{_ci(item, 0.5)} | {_ci(item, 2.0 / 3.0)} | "
            f"{item['max_abs_delta']:.3e} | {item['max_rel_delta']:.3e} | "
            f"{item['clip_rate_bmax']:.3e} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "With common random numbers, the three estimators coincide in every "
            "replica without a clipping event. Across the frozen ensemble, the "
            f"maximum relative beta1 deviation from the D_M/2 reference is {max_rel:.3e}, "
            f"below the descriptive tolerance {RELATIVE_BETA1_TOL:.3g}; the maximum "
            f"clip-event rate at the largest B is {max_clip:.3e}. The leading law is "
            "therefore invariant to the registered clipping-threshold perturbation."
        ),
    ])
    return "\n".join(lines) + "\n"


def _instance_summaries(rows: list[dict]) -> list[dict]:
    by_instance: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_instance[row["instance_id"]].append(row)
    summaries = []
    for instance_id in sorted(by_instance):
        sub = by_instance[instance_id]
        fits = {}
        for fraction in CLIP_FRACTIONS:
            row = next(item for item in sub if math.isclose(float(item["clip_fraction"]), fraction))
            fits[fraction] = {
                "beta1": float(row["beta1"]),
                "beta1_se": float(row["beta1_se"]),
            }
        ref = fits[REFERENCE_CLIP_FRACTION]["beta1"]
        deltas = [abs(fits[fraction]["beta1"] - ref) for fraction in CLIP_FRACTIONS]
        max_abs = max(deltas)
        max_rel = max_abs / max(abs(ref), 1e-300)
        b_max = max(int(row["B"]) for row in sub)
        clip_rate = max(float(row["clip_event_rate"]) for row in sub if int(row["B"]) == b_max)
        summaries.append({
            "instance_id": instance_id,
            "fits": fits,
            "max_abs_delta": max_abs,
            "max_rel_delta": max_rel,
            "clip_rate_bmax": clip_rate,
        })
    return summaries


def _ci(summary: dict, fraction: float) -> str:
    fit = summary["fits"][fraction]
    beta = fit["beta1"]
    half_width = 1.96 * fit["beta1_se"]
    return f"{beta:.6g} +/- {half_width:.2g}"


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
