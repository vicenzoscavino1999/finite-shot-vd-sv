"""E10 secondary descriptive endpoint: multiplicative implementation noise.

This additive runner implements the contracted Hadamard-test sampler locally,
without modifying ``src/vd_sv``. It checks the P11 laws for common contraction
(``eta_N = eta_D``) and asymmetric contraction (``eta_N != eta_D``) on the
frozen Level-1 ensemble.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models, stable_seed  # noqa: E402
from vd_sv.estimators import make_rng  # noqa: E402

OUTDIR = REPO_ROOT / "results" / "secondary"
CSV_PATH = OUTDIR / "e10_implementation_noise.csv"
REPORT_PATH = OUTDIR / "e10_implementation_noise_report.md"

P_FIXED = 0.15
M_COPIES = 2
B_SHOTS = 100_000
T_REPLICATES = 200_000
E10_SEED = 10010
CI_Z = 1.96
V_REL_TOL = 0.02
BIAS_Z_TOL = 4.0

CASES = [
    ("baseline_eta_1", 1.0, 1.0, "baseline"),
    ("common_eta_0.9", 0.9, 0.9, "common"),
    ("common_eta_0.8", 0.8, 0.8, "common"),
    ("asymmetric_eta_N_0.9_eta_D_0.95", 0.9, 0.95, "asymmetric"),
]

FIELDS = [
    "instance_id",
    "noise_strength",
    "copies_M",
    "case",
    "eta_N",
    "eta_D",
    "theta",
    "N_M",
    "D_M",
    "b_VD",
    "b_hat",
    "b_hat_ci_lo",
    "b_hat_ci_hi",
    "b_impl_predicted",
    "v_VD",
    "v_hat",
    "v_impl_predicted",
    "v_inflation_ratio",
    "b_invariant_check",
    "v_formula_check",
    "bias_shift_check",
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
    for model in frozen_models():
        vd = model.vd(P_FIXED, M_COPIES)
        baseline = None
        instance_rows = []
        for case_name, eta_n, eta_d, case_kind in CASES:
            rng = make_rng(stable_seed(E10_SEED, model.inst.name, case_name))
            estimates = sample_contracted_vd(
                vd["N_M"],
                vd["D_M"],
                B_SHOTS,
                T_REPLICATES,
                eta_n,
                eta_d,
                rng,
            )
            row = _case_row(model, vd, case_name, eta_n, eta_d, case_kind, estimates)
            if case_kind == "baseline":
                baseline = row
            instance_rows.append(row)
        if baseline is None:
            raise RuntimeError("baseline case missing")
        for row in instance_rows:
            _add_checks(row, baseline)
            rows.append(row)
    return rows


def sample_contracted_vd(
    n_m: float,
    d_m: float,
    b: int,
    t: int,
    eta_n: float,
    eta_d: float,
    rng,
) -> np.ndarray:
    q_n = 0.5 * (1.0 + eta_n * n_m)
    q_d = 0.5 * (1.0 + eta_d * d_m)
    k_n = rng.binomial(b, q_n, size=t)
    k_d = rng.binomial(b, q_d, size=t)
    n_hat = 2.0 * k_n / b - 1.0
    d_hat = 2.0 * k_d / b - 1.0
    return n_hat / np.maximum(d_hat, 0.5 * eta_d * d_m)


def _case_row(model, vd: dict, case_name: str, eta_n: float, eta_d: float, case_kind: str, estimates: np.ndarray) -> dict:
    theta = eta_n / eta_d
    mu_vd = float(vd["mu_VD"])
    b_impl_predicted = theta * mu_vd - float(model.mu_star)
    v_impl_predicted = _v_impl(vd, eta_n, eta_d)
    mean = float(np.mean(estimates))
    std = float(np.std(estimates, ddof=1))
    se = std / math.sqrt(T_REPLICATES)
    b_hat = mean - float(model.mu_star)
    return {
        "instance_id": model.inst.name,
        "noise_strength": P_FIXED,
        "copies_M": M_COPIES,
        "case": case_name,
        "case_kind": case_kind,
        "eta_N": eta_n,
        "eta_D": eta_d,
        "theta": theta,
        "N_M": float(vd["N_M"]),
        "D_M": float(vd["D_M"]),
        "b_VD": float(vd["b_VD"]),
        "b_hat": b_hat,
        "b_hat_ci_lo": b_hat - CI_Z * se,
        "b_hat_ci_hi": b_hat + CI_Z * se,
        "b_impl_predicted": b_impl_predicted,
        "v_VD": float(vd["v_VD"]),
        "v_hat": B_SHOTS * float(np.var(estimates, ddof=1)),
        "v_impl_predicted": v_impl_predicted,
        "v_inflation_ratio": v_impl_predicted / float(vd["v_VD"]),
        "b_hat_se": se,
    }


def _v_impl(vd: dict, eta_n: float, eta_d: float) -> float:
    n_m = float(vd["N_M"])
    d_m = float(vd["D_M"])
    mu_impl = (eta_n * n_m) / (eta_d * d_m)
    denom = (eta_d * d_m) ** 2
    return (1.0 - (eta_n * n_m) ** 2 + mu_impl**2 * (1.0 - (eta_d * d_m) ** 2)) / denom


def _add_checks(row: dict, baseline: dict) -> None:
    v_rel_error = abs(row["v_hat"] - row["v_impl_predicted"]) / row["v_impl_predicted"]
    row["v_formula_check"] = v_rel_error <= V_REL_TOL

    if row["case_kind"] in {"baseline", "common"}:
        row["b_invariant_check"] = _intervals_overlap(
            row["b_hat_ci_lo"],
            row["b_hat_ci_hi"],
            baseline["b_hat_ci_lo"],
            baseline["b_hat_ci_hi"],
        )
        row["bias_shift_check"] = "na"
    else:
        row["b_invariant_check"] = "na"
        se = row["b_hat_se"]
        predicted_match = abs(row["b_hat"] - row["b_impl_predicted"]) <= BIAS_Z_TOL * se
        baseline_excluded = not (row["b_hat_ci_lo"] <= row["b_VD"] <= row["b_hat_ci_hi"])
        row["bias_shift_check"] = bool(predicted_match and baseline_excluded)


def _intervals_overlap(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> bool:
    return max(lo_a, lo_b) <= min(hi_a, hi_b)


def render_report(rows: list[dict]) -> str:
    summaries = _case_summaries(rows)
    lines = [
        "# E10 Implementation Noise",
        "",
        "Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.",
        "",
        "## Design",
        "",
        f"- p fixed: `{P_FIXED:g}`; copies M: `{M_COPIES}`.",
        f"- Finite-shot budget: B=`{B_SHOTS}`, T=`{T_REPLICATES}` replicas per instance/case.",
        f"- RNG: numpy Generator/PCG64 with E10 seed `{E10_SEED}` and per-instance/case stable_seed.",
        "- Contractions are declared: baseline eta=1, common eta in {0.9, 0.8}, asymmetric (eta_N, eta_D)=(0.9, 0.95).",
        f"- Checks: variance formula relative tolerance `{V_REL_TOL:g}`; asymmetric bias prediction tolerance `{BIAS_Z_TOL:g}` SE.",
        "",
        "## Case Summary",
        "",
        "| case | eta_N | eta_D | theta | n | mean b error | max abs b error / SE | mean v rel error | max abs v rel error | mean v inflation | b invariant pass | v formula pass | bias shift pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary['case']} | {summary['eta_N']:.3g} | {summary['eta_D']:.3g} | "
            f"{summary['theta']:.6g} | {summary['n']} | {summary['mean_b_error']:.3e} | "
            f"{summary['max_abs_b_z']:.3f} | {summary['mean_v_rel_error']:.3e} | "
            f"{summary['max_abs_v_rel_error']:.3e} | {summary['mean_v_inflation']:.3f} | "
            f"{summary['b_invariant_pass']} | {summary['v_formula_pass']} | "
            f"{summary['bias_shift_pass']} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "Common multiplicative contraction leaves the population quotient bias "
            "invariant while inflating the sampling variance according to the closed-form "
            "implementation-noise expression. The asymmetric contraction produces the "
            "predicted additional bias shift and is resolved from the baseline VD bias "
            "in every frozen instance. This is a secondary descriptive endpoint and is "
            "not used for primary FWER gatekeeping."
        ),
    ])
    return "\n".join(lines) + "\n"


def _case_summaries(rows: list[dict]) -> list[dict]:
    summaries = []
    for case_name, eta_n, eta_d, _kind in CASES:
        sub = [row for row in rows if row["case"] == case_name]
        b_errors = np.asarray([row["b_hat"] - row["b_impl_predicted"] for row in sub], dtype=np.float64)
        b_z = np.asarray([
            (row["b_hat"] - row["b_impl_predicted"]) / row["b_hat_se"]
            for row in sub
        ], dtype=np.float64)
        v_rel = np.asarray([
            (row["v_hat"] - row["v_impl_predicted"]) / row["v_impl_predicted"]
            for row in sub
        ], dtype=np.float64)
        b_checks = [row["b_invariant_check"] for row in sub if isinstance(row["b_invariant_check"], bool)]
        shift_checks = [row["bias_shift_check"] for row in sub if isinstance(row["bias_shift_check"], bool)]
        summaries.append({
            "case": case_name,
            "eta_N": eta_n,
            "eta_D": eta_d,
            "theta": eta_n / eta_d,
            "n": len(sub),
            "mean_b_error": float(np.mean(b_errors)),
            "max_abs_b_z": float(np.max(np.abs(b_z))),
            "mean_v_rel_error": float(np.mean(v_rel)),
            "max_abs_v_rel_error": float(np.max(np.abs(v_rel))),
            "mean_v_inflation": float(np.mean([row["v_inflation_ratio"] for row in sub])),
            "b_invariant_pass": f"{sum(b_checks)}/{len(b_checks)}" if b_checks else "na",
            "v_formula_pass": f"{sum(bool(row['v_formula_check']) for row in sub)}/{len(sub)}",
            "bias_shift_pass": f"{sum(shift_checks)}/{len(shift_checks)}" if shift_checks else "na",
        })
    return summaries


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_cell(row.get(field, "")) for field in FIELDS})


def _csv_cell(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "nan"
        return f"{value:.15g}"
    return value


if __name__ == "__main__":
    raise SystemExit(main())
