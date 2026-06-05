"""Adjudicate Level 1 outputs against the PAP or amendment criteria."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models, wls_fit, write_csv

PILOT_CSV = REPO_ROOT / "results" / "pilot" / "pilot_power_report.csv"

FIELDS = [
    "prediction_id",
    "family",
    "level_of_evidence",
    "experiment",
    "predicted_value_or_scale",
    "estimator",
    "criterion",
    "verdict",
    "result_summary",
    "source_outputs",
    "notes",
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--version", choices=["v1", "v2"], default="v2")
    args = ap.parse_args(argv)

    rows = adjudicate(args.results, args.version)
    write_csv(args.output, FIELDS, rows)
    print(args.output)
    return 0


def adjudicate(results: Path, version: str) -> list[dict]:
    pilot = _pilot_values()
    models = {model.inst.name: model for model in frozen_models()}
    e1 = _adjudicate_e1(results, version)
    p1_confirmed = e1["p1_verdict"].startswith("CONFIRMA")

    rows = [
        _row(
            "P1",
            "primary",
            1,
            "E1",
            "v+2bc (beta1) and curvature needed",
            "WLS beta1, beta2, and Delta AIC",
            e1["p1_criterion"],
            e1["p1_verdict"],
            e1["p1_summary"],
            results / "e1_quotient_decomposition.csv",
            e1["p1_notes"],
        ),
        _gate_row(
            "P2",
            "E1",
            "b^2 (beta0)",
            "WLS beta0",
            "b2_closed in WLS 95% CI of intercept",
            e1["p2_pass"],
            e1["p2_summary"],
            results / "e1_quotient_decomposition.csv",
            p1_confirmed,
        ),
    ]

    e2 = _adjudicate_e2(results, models, pilot)
    rows.extend([
        _gate_row(
            "P3",
            "E2",
            "c_VD",
            "slope of bias vs 1/B",
            "CI excludes 0 and within tau of c_VD",
            e2["p3_pass"],
            e2["p3_summary"],
            results / "e2_c_sv_zero.csv",
            p1_confirmed,
        ),
        _gate_row(
            "P4",
            "E2",
            "0",
            "TOST on c_SV",
            "equivalence within margin delta_c",
            e2["p4_pass"],
            e2["p4_summary"],
            results / "e2_c_sv_zero.csv",
            p1_confirmed,
        ),
    ])

    e3 = _adjudicate_delta(results, "e3_delta_vd_generator.csv", "delta_vd")
    e4 = _adjudicate_delta(results, "e4_delta_sv_firstorder.csv", "delta_sv")
    rows.extend([
        _gate_row(
            "P5",
            "E3",
            "delta_VD",
            "slope of b_VD_inf(p) white-box",
            "delta_fit_abs_error <= delta_consistency_abs_tol; INCONCLUSO if |delta| < delta_abs_floor",
            e3["pass"],
            e3["summary"],
            results / "e3_delta_vd_generator.csv",
            p1_confirmed,
            near_zero=e3["near_zero"],
        ),
        _gate_row(
            "P6",
            "E4",
            "delta_SV",
            "slope of b_SV(p) white-box",
            "delta_fit_abs_error <= delta_consistency_abs_tol; INCONCLUSO if |delta| < delta_abs_floor",
            e4["pass"],
            e4["summary"],
            results / "e4_delta_sv_firstorder.csv",
            p1_confirmed,
            near_zero=e4["near_zero"],
        ),
    ])

    e5 = _adjudicate_e5(results)
    e7 = _adjudicate_e7(results)
    rows.extend([
        _row(
            "P7",
            "secondary",
            1,
            "E5",
            "denominator regime change at B_den",
            "tail/kurtosis of mu_hat",
            "regime change within factor 2 of B_den",
            "CONFIRMA_SECUNDARIO" if e5["pass"] else "NO_CONFIRMA_SECUNDARIO",
            e5["summary"],
            results / "e5_denominator_concentration.csv",
            "Secondary descriptive endpoint; does not affect primary FWER gatekeeping.",
        ),
        _row(
            "P8",
            "secondary",
            2,
            "E6",
            "1/(2|log lambda2|)",
            "slope of M*(B) vs log B",
            "predicted slope in CI (lambda2 gap pre-verified)",
            "NO_EJECUTADO_PHASE_A",
            "The lambda2 gap pre-freeze artifact is present and passes, but E6/M*(B) is not implemented in run_all.py and no confirmatory E6 CSV was generated.",
            REPO_ROOT / "results" / "frozen" / "lambda2_gap_table.csv",
            "Secondary endpoint remains unadjudicated until E6 is implemented and run.",
        ),
        _row(
            "P9",
            "secondary",
            1,
            "E7",
            "R0 certified band",
            "empirical crossing root",
            "R* in [R0(1-eta),R0(1+eta)] and eta<1/2",
            "CONFIRMA_SECUNDARIO" if e7["pass"] else "NO_CONFIRMA_SECUNDARIO",
            e7["summary"],
            results / "e7_certified_crossing.csv",
            "E7 uses remainder_source=fit_from_sampled_mse, so this is not the formal conservative-C P9 certificate.",
        ),
    ])
    return rows


def _adjudicate_e1(results: Path, version: str) -> dict:
    rows = _read_csv(results / "e1_quotient_decomposition.csv")
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["instance_id"], row["method"])].append(row)

    stats = {"vd": [], "unmitigated": []}
    for (instance_id, method), group in grouped.items():
        fit = _e1_fit(group)
        fit["instance_id"] = instance_id
        stats[method].append(fit)

    vd_beta1_ok = sum(f["beta1_ci_contains"] for f in stats["vd"])
    vd_beta0_ok = sum(f["beta0_ci_contains"] for f in stats["vd"])
    vd_beta2_nonzero = sum(not f["beta2_ci_contains_zero"] for f in stats["vd"])
    vd_aic_ok = sum(f["delta_aic"] > 2.0 for f in stats["vd"])
    unmit_aic_old_ok = sum(f["delta_aic"] <= 2.0 for f in stats["unmitigated"])
    unmit_beta2_zero = sum(f["beta2_ci_contains_zero"] for f in stats["unmitigated"])

    n_vd = len(stats["vd"])
    n_unmit = len(stats["unmitigated"])
    vd_delta_aic = [f["delta_aic"] for f in stats["vd"]]
    unmit_delta_aic = [f["delta_aic"] for f in stats["unmitigated"]]

    if version == "v1":
        p1_pass = vd_beta1_ok == n_vd and vd_aic_ok == n_vd and unmit_aic_old_ok == n_unmit
        criterion = "beta1 in 95% CI and Delta AIC>2 for VD not unmitigated"
        notes = "v1 frozen criterion uses all-instances AIC gate for the unmitigated control."
    else:
        p1_pass = (
            vd_beta1_ok == n_vd
            and vd_aic_ok == n_vd
            and vd_beta2_nonzero == n_vd
            and unmit_beta2_zero == n_unmit
        )
        criterion = (
            "VD beta1 in 95% CI; VD Delta AIC>2 and beta2 CI excludes 0; "
            "unmitigated beta2 CI includes 0"
        )
        notes = "v2 amended criterion replaces the unmitigated AIC gate with the direct beta2=0 coefficient test."

    return {
        "p1_verdict": "CONFIRMA" if p1_pass else "REFUTA",
        "p1_criterion": criterion,
        "p1_summary": (
            f"VD beta1 recovered {vd_beta1_ok}/{n_vd}; VD Delta AIC>2 "
            f"{vd_aic_ok}/{n_vd} (range {min(vd_delta_aic):.3f}-{max(vd_delta_aic):.3f}); "
            f"VD beta2 CI excludes 0 {vd_beta2_nonzero}/{n_vd}; "
            f"unmitigated beta2 CI includes 0 {unmit_beta2_zero}/{n_unmit}; "
            f"unmitigated Delta AIC<=2 under v1 gate {unmit_aic_old_ok}/{n_unmit} "
            f"(median {float(np.median(unmit_delta_aic)):.3f})."
        ),
        "p1_notes": notes,
        "p2_pass": vd_beta0_ok == n_vd,
        "p2_summary": f"VD beta0 closed form lies in the WLS 95% CI in {vd_beta0_ok}/{n_vd} instances.",
    }


def _e1_fit(group: list[dict]) -> dict:
    b_grid = np.asarray([float(row["B"]) for row in group], dtype=np.float64)
    y = np.asarray([float(row["mse"]) for row in group], dtype=np.float64)
    se = np.asarray([max(float(row["mse_se"]), 1e-12) for row in group], dtype=np.float64)
    x = np.column_stack([np.ones_like(b_grid), 1.0 / b_grid, 1.0 / b_grid**2])
    coeffs, cov = wls_fit(x, y, 1.0 / se**2)
    ses = np.sqrt(np.diag(cov))
    ci = [(float(c - 1.96 * s), float(c + 1.96 * s)) for c, s in zip(coeffs, ses)]
    beta0_closed = float(group[0]["b2_closed_form"])
    beta1_closed = float(group[0]["vtilde_closed_form"])
    return {
        "beta0_ci_contains": ci[0][0] <= beta0_closed <= ci[0][1],
        "beta1_ci_contains": ci[1][0] <= beta1_closed <= ci[1][1],
        "beta2_ci_contains_zero": ci[2][0] <= 0.0 <= ci[2][1],
        "delta_aic": float(group[0]["delta_aic"]),
    }


def _adjudicate_e2(results: Path, models: dict, pilot: dict) -> dict:
    rows = _read_csv(results / "e2_c_sv_zero.csv")
    grouped = {}
    for row in rows:
        grouped[(row["instance_id"], float(row["noise_strength"]), row["method"])] = row
    tau = float(pilot["tau_value"])
    margin_fraction = 0.1
    vd_ok = sv_ok = vd_total = sv_total = 0
    for (instance_id, p, method), row in grouped.items():
        c_hat = float(row["c_slope_estimate"])
        lo = float(row["c_slope_ci_lower"])
        hi = float(row["c_slope_ci_upper"])
        vd = models[instance_id].vd(p, 2)
        c_vd = vd["mu_VD"] * (1.0 - vd["D_M"] ** 2) / (vd["D_M"] ** 2)
        if method == "vd":
            vd_total += 1
            vd_ok += (lo > 0.0 or hi < 0.0) and abs(c_hat - c_vd) <= tau * abs(c_vd)
        else:
            sv_total += 1
            margin = margin_fraction * abs(c_vd)
            sv_ok += lo >= -margin and hi <= margin
    return {
        "p3_pass": vd_ok == vd_total,
        "p3_summary": f"VD c_slope CI excludes zero and estimate is within tau in {vd_ok}/{vd_total} instance-p cells.",
        "p4_pass": sv_ok == sv_total,
        "p4_summary": f"SV c_slope CI lies within the frozen TOST margin in {sv_ok}/{sv_total} instance-p cells.",
    }


def _adjudicate_delta(results: Path, filename: str, prefix: str) -> dict:
    rows = _read_csv(results / filename)
    by_instance = {row["instance_id"]: row for row in rows}
    pilot = _pilot_values()
    floor = float(pilot["delta_abs_floor"])
    tol = float(pilot["delta_consistency_abs_tol"])
    ok = near = bad = 0
    measured_col = f"{prefix}_measured"
    closed_col = f"{prefix}_closed_form"
    for row in by_instance.values():
        measured = float(row[measured_col])
        closed = float(row[closed_col])
        err = abs(measured - closed)
        if abs(closed) < floor:
            near += 1
        elif err <= tol:
            ok += 1
        else:
            bad += 1
    return {
        "pass": bad == 0,
        "near_zero": near,
        "summary": (
            f"Non-near-zero consistency passes {ok}/{ok + bad}; "
            f"{near} instances are INCONCLUSIVE_BY_DESIGN_NEAR_ZERO under delta_abs_floor={floor:g}."
        ),
    }


def _adjudicate_e5(results: Path) -> dict:
    rows = _read_csv(results / "e5_denominator_concentration.csv")
    by_factor = {}
    for target in (0.125, 0.5, 1.0, 2.0, 8.0):
        vals = [
            float(row["bad_denominator_prob_empirical"])
            for row in rows
            if abs(float(row["B_over_Bden"]) / target - 1.0) < 0.02
        ]
        rel = [
            float(row["relative_deviation_clipped"])
            for row in rows
            if abs(float(row["B_over_Bden"]) / target - 1.0) < 0.02
        ]
        by_factor[target] = (float(np.median(vals)), float(np.median(rel)))
    return {
        "pass": by_factor[0.5][0] > by_factor[1.0][0] and by_factor[1.0][0] >= by_factor[2.0][0],
        "summary": (
            "Median empirical bad-denominator probability drops from "
            f"{by_factor[0.125][0]:.5f} at 0.125 B_den to {by_factor[1.0][0]:.5f} "
            f"at B_den and {by_factor[2.0][0]:.5f} at 2 B_den; clipped relative "
            f"deviation median drops from {by_factor[0.125][1]:.3f} to "
            f"{by_factor[1.0][1]:.3f} to {by_factor[2.0][1]:.3f}."
        ),
    }


def _adjudicate_e7(results: Path) -> dict:
    rows = _read_csv(results / "e7_certified_crossing.csv")
    by_instance = {row["instance_id"]: row for row in rows}
    inside = eta_ok = 0
    ratios = []
    etas = []
    for row in by_instance.values():
        r_star = float(row["crossing_R_empirical"])
        r0 = float(row["crossing_R0_leading"])
        eta = float(row["eta_operational"])
        etas.append(eta)
        ratios.append(r_star / r0)
        eta_ok += eta < 0.5
        inside += r0 * (1.0 - eta) <= r_star <= r0 * (1.0 + eta)
    n = len(by_instance)
    return {
        "pass": inside == n and eta_ok == n,
        "summary": (
            f"Operational eta<0.5 in {eta_ok}/{n} instances; R* lies inside the "
            f"operational band in {inside}/{n}; R*/R0 range "
            f"{min(ratios):.3f}-{max(ratios):.3f}; eta range {min(etas):.3f}-{max(etas):.3f}."
        ),
    }


def _pilot_values() -> dict:
    with PILOT_CSV.open(newline="", encoding="utf-8") as fh:
        return next(csv.DictReader(fh))


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _gate_row(
    prediction_id: str,
    experiment: str,
    predicted: str,
    estimator: str,
    criterion: str,
    passed: bool,
    summary: str,
    source: Path,
    gate_open: bool,
    near_zero: int = 0,
) -> dict:
    if not gate_open:
        verdict = "NO_ADJUDICADO_GATEKEEPING"
        notes = "Not counted as confirmatory because an earlier primary endpoint failed in the gatekeeping sequence."
    elif passed and near_zero:
        verdict = "CONFIRMA_CON_INCONCLUSOS_PREESPECIFICADOS"
        notes = "Near-zero cases are handled by the frozen delta_abs_floor rule."
    else:
        verdict = "CONFIRMA" if passed else "REFUTA"
        notes = "Primary endpoint adjudicated under fixed-sequence gatekeeping."
    return _row(
        prediction_id,
        "primary",
        1,
        experiment,
        predicted,
        estimator,
        criterion,
        verdict,
        summary,
        source,
        notes,
    )


def _row(
    prediction_id: str,
    family: str,
    level: int,
    experiment: str,
    predicted: str,
    estimator: str,
    criterion: str,
    verdict: str,
    summary: str,
    source: Path,
    notes: str,
) -> dict:
    return {
        "prediction_id": prediction_id,
        "family": family,
        "level_of_evidence": level,
        "experiment": experiment,
        "predicted_value_or_scale": predicted,
        "estimator": estimator,
        "criterion": criterion,
        "verdict": verdict,
        "result_summary": summary,
        "source_outputs": source.as_posix(),
        "notes": notes,
    }


if __name__ == "__main__":
    raise SystemExit(main())
