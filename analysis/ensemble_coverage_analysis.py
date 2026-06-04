"""Coverage-level ensemble audit for the v1 and v2 confirmatory runs.

This is a post-adjudication analysis layer. It does not modify either frozen PAP
record, either adjudication table, or any confirmatory output.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import binom, chi2

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models, wls_fit  # noqa: E402

REPORT_PATH = REPO_ROOT / "analysis" / "ensemble_coverage_report.md"
PILOT_CSV = REPO_ROOT / "results" / "pilot" / "pilot_power_report.csv"

DATASETS = {
    "v1": REPO_ROOT / "results" / "confirmatory_full",
    "v2": REPO_ROOT / "results" / "confirmatory_v2",
}

NEAR_MISS_INSTANCES = {"g6_k2_c000", "g6_k2_c002"}


@dataclass(frozen=True)
class CoverageResult:
    dataset: str
    coefficient: str
    n: int
    k: int
    binom_p_lower: float
    chi2_stat: float
    chi2_p: float
    mean_z: float
    conclusion: str


def main() -> int:
    pilot = _pilot_values()
    models = {model.inst.name: model for model in frozen_models()}
    sections = []
    summary_rows: list[CoverageResult] = []

    for label, path in DATASETS.items():
        result = analyze_dataset(label, path, models, pilot)
        summary_rows.extend(result["coverage"])
        sections.append(_dataset_section(result))

    REPORT_PATH.write_text(_render_report(summary_rows, sections), encoding="utf-8")
    print(REPORT_PATH)
    return 0


def analyze_dataset(label: str, path: Path, models: dict, pilot: dict) -> dict:
    e1 = _e1_fits(path)
    coverage = [
        _coverage_result(label, "VD beta0 (E1)", e1["vd_beta0"]),
        _coverage_result(label, "VD beta1 (E1)", e1["vd_beta1"]),
    ]
    e2 = _e2_fits(path, models)
    coverage.append(_coverage_result(label, "c_VD (E2 instance-p cells)", e2["c_vd"]))

    c_sv = _csv_equivalence(path, models)
    delta_vd = _delta_consistency(path, "e3_delta_vd_generator.csv", "delta_vd", pilot)
    delta_sv = _delta_consistency(path, "e4_delta_sv_firstorder.csv", "delta_sv", pilot)
    near_miss = _near_miss_beta1(label, e1["vd_beta1"])

    return {
        "label": label,
        "path": path,
        "coverage": coverage,
        "c_sv": c_sv,
        "delta_vd": delta_vd,
        "delta_sv": delta_sv,
        "near_miss": near_miss,
    }


def _e1_fits(path: Path) -> dict[str, list[dict]]:
    rows = _read_csv(path / "e1_quotient_decomposition.csv")
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["instance_id"], row["method"])].append(row)

    vd_beta0 = []
    vd_beta1 = []
    for (instance_id, method), group in sorted(grouped.items()):
        if method != "vd":
            continue
        b_grid = np.asarray([float(row["B"]) for row in group], dtype=np.float64)
        y = np.asarray([float(row["mse"]) for row in group], dtype=np.float64)
        se_y = np.asarray([max(float(row["mse_se"]), 1e-12) for row in group], dtype=np.float64)
        design = np.column_stack([np.ones_like(b_grid), 1.0 / b_grid, 1.0 / b_grid**2])
        coeffs, cov = wls_fit(design, y, 1.0 / se_y**2)
        ses = np.sqrt(np.diag(cov))
        closed = [float(group[0]["b2_closed_form"]), float(group[0]["vtilde_closed_form"])]
        for name, idx, target, sink in [
            ("beta0", 0, closed[0], vd_beta0),
            ("beta1", 1, closed[1], vd_beta1),
        ]:
            measured = float(coeffs[idx])
            se = float(ses[idx])
            sink.append({
                "instance_id": instance_id,
                "coefficient": name,
                "measured": measured,
                "closed": target,
                "se": se,
                "z": (measured - target) / se,
                "covered": _covered(measured, target, se),
            })
    return {"vd_beta0": vd_beta0, "vd_beta1": vd_beta1}


def _e2_fits(path: Path, models: dict) -> dict[str, list[dict]]:
    rows = _read_csv(path / "e2_c_sv_zero.csv")
    seen = {}
    for row in rows:
        key = (row["instance_id"], float(row["noise_strength"]), row["method"])
        seen[key] = row

    c_vd = []
    for (instance_id, p, method), row in sorted(seen.items()):
        if method != "vd":
            continue
        measured = float(row["c_slope_estimate"])
        se = _se_from_ci(float(row["c_slope_ci_lower"]), float(row["c_slope_ci_upper"]))
        vd = models[instance_id].vd(p, 2)
        closed = float(vd["mu_VD"] * (1.0 - vd["D_M"] ** 2) / (vd["D_M"] ** 2))
        c_vd.append({
            "instance_id": instance_id,
            "noise_strength": p,
            "measured": measured,
            "closed": closed,
            "se": se,
            "z": (measured - closed) / se,
            "covered": _covered(measured, closed, se),
        })
    return {"c_vd": c_vd}


def _csv_equivalence(path: Path, models: dict) -> dict:
    rows = _read_csv(path / "e2_c_sv_zero.csv")
    seen = {}
    for row in rows:
        key = (row["instance_id"], float(row["noise_strength"]), row["method"])
        seen[key] = row

    records = []
    for (instance_id, p, method), row in sorted(seen.items()):
        if method != "sv":
            continue
        vd = models[instance_id].vd(p, 2)
        c_vd = float(vd["mu_VD"] * (1.0 - vd["D_M"] ** 2) / (vd["D_M"] ** 2))
        margin = 0.1 * abs(c_vd)
        lo = float(row["c_slope_ci_lower"])
        hi = float(row["c_slope_ci_upper"])
        measured = float(row["c_slope_estimate"])
        records.append({
            "instance_id": instance_id,
            "noise_strength": p,
            "measured": measured,
            "lo": lo,
            "hi": hi,
            "margin": margin,
            "within_tost": lo >= -margin and hi <= margin,
            "contains_zero": lo <= 0.0 <= hi,
        })
    n = len(records)
    k = sum(record["within_tost"] for record in records)
    contains_zero = sum(record["contains_zero"] for record in records)
    estimates = np.asarray([record["measured"] for record in records], dtype=np.float64)
    margins = np.asarray([record["margin"] for record in records], dtype=np.float64)
    failures = [
        f"{record['instance_id']}@p={record['noise_strength']:.6g}"
        for record in records
        if not record["within_tost"]
    ]
    return {
        "n": n,
        "k": k,
        "fraction": k / n if n else float("nan"),
        "contains_zero": contains_zero,
        "mean": float(np.mean(estimates)),
        "max_abs": float(np.max(np.abs(estimates))),
        "median_abs": float(np.median(np.abs(estimates))),
        "min_margin": float(np.min(margins)),
        "median_margin": float(np.median(margins)),
        "failures": failures,
    }


def _delta_consistency(path: Path, filename: str, prefix: str, pilot: dict) -> dict:
    rows = _read_csv(path / filename)
    by_instance = {row["instance_id"]: row for row in rows}
    floor = float(pilot["delta_abs_floor"])
    tol = float(pilot["delta_consistency_abs_tol"])
    measured_col = f"{prefix}_measured"
    closed_col = f"{prefix}_closed_form"

    nonzero = []
    near = []
    for row in sorted(by_instance.values(), key=lambda item: item["instance_id"]):
        measured = float(row[measured_col])
        closed = float(row[closed_col])
        err = abs(measured - closed)
        record = {
            "instance_id": row["instance_id"],
            "measured": measured,
            "closed": closed,
            "abs_error": err,
            "passes": err <= tol,
        }
        if abs(closed) < floor:
            near.append(record)
        else:
            nonzero.append(record)
    k = sum(record["passes"] for record in nonzero)
    n = len(nonzero)
    return {
        "n": n,
        "k": k,
        "fraction": k / n if n else float("nan"),
        "near_zero_n": len(near),
        "tol": tol,
        "floor": floor,
        "max_abs_error_nonzero": max((record["abs_error"] for record in nonzero), default=0.0),
        "failures": [record["instance_id"] for record in nonzero if not record["passes"]],
        "near_zero": [record["instance_id"] for record in near],
    }


def _near_miss_beta1(dataset: str, beta1_records: list[dict]) -> list[dict]:
    by_instance = {record["instance_id"]: record for record in beta1_records}
    rows = []
    for instance_id in sorted(NEAR_MISS_INSTANCES):
        record = by_instance.get(instance_id)
        if record is None:
            continue
        abs_z = abs(float(record["z"]))
        if abs_z < 2.5:
            interpretation = "coverage_noise_band"
        elif abs_z < 3.0:
            interpretation = "borderline_coverage_noise"
        else:
            interpretation = "exceeds_3_se_audit_extraction"
        rows.append({
            "dataset": dataset,
            "instance_id": instance_id,
            "measured": float(record["measured"]),
            "closed": float(record["closed"]),
            "se": float(record["se"]),
            "abs_z": abs_z,
            "interpretation": interpretation,
        })
    return rows


def _coverage_result(dataset: str, coefficient: str, records: list[dict]) -> CoverageResult:
    n = len(records)
    k = sum(record["covered"] for record in records)
    z = np.asarray([record["z"] for record in records], dtype=np.float64)
    stat = float(np.sum(z**2))
    p_chi2 = float(chi2.sf(stat, n)) if n else float("nan")
    p_binom = float(binom.cdf(k, n, 0.95)) if n else float("nan")
    conclusion = "consistent" if p_binom > 0.05 and p_chi2 > 0.05 else "not_consistent"
    return CoverageResult(
        dataset=dataset,
        coefficient=coefficient,
        n=n,
        k=int(k),
        binom_p_lower=p_binom,
        chi2_stat=stat,
        chi2_p=p_chi2,
        mean_z=float(np.mean(z)) if n else float("nan"),
        conclusion=conclusion,
    )


def _covered(measured: float, closed: float, se: float) -> bool:
    return measured - 1.96 * se <= closed <= measured + 1.96 * se


def _se_from_ci(lo: float, hi: float) -> float:
    return (hi - lo) / (2.0 * 1.96)


def _pilot_values() -> dict:
    with PILOT_CSV.open(newline="", encoding="utf-8") as fh:
        return next(csv.DictReader(fh))


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _render_report(summary_rows: list[CoverageResult], sections: list[str]) -> str:
    parts = [
        "# Ensemble Coverage Analysis",
        "",
        "Status: post_adjudication_analysis_only.",
        "",
        "This report analyzes coverage and pooled residual behavior on the existing v1 and v2 confirmatory outputs. It does not define a new PAP freeze, does not retry seeds, and does not change either adjudication table.",
        "",
        "## Coverage Summary",
        "",
        "| Dataset | Coefficient | k/n covered | Binomial P(K<=k; p=0.95) | chi2_n | chi2 p-value | mean(z) | Conclusion |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary_rows:
        parts.append(
            "| {dataset} | {coef} | {k}/{n} | {bp:.4g} | {chi:.3f} | {cp:.4g} | {mz:.3f} | {conclusion} |".format(
                dataset=row.dataset,
                coef=row.coefficient,
                k=row.k,
                n=row.n,
                bp=row.binom_p_lower,
                chi=row.chi2_stat,
                cp=row.chi2_p,
                mz=row.mean_z,
                conclusion=_human_conclusion(row.conclusion),
            )
        )
    parts.extend(["", *sections])
    return "\n".join(parts) + "\n"


def _dataset_section(result: dict) -> str:
    label = result["label"]
    c_sv = result["c_sv"]
    delta_vd = result["delta_vd"]
    delta_sv = result["delta_sv"]
    near = result["near_miss"]
    lines = [
        f"## Dataset {label}",
        "",
        f"Path: `{result['path'].as_posix()}`",
        "",
        "### c_SV Equivalence",
        "",
        "| Cells within TOST margin | CIs containing zero | mean(c_hat) | median abs(c_hat) | max abs(c_hat) | min margin | median margin | Failures |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
        "| {k}/{n} ({frac:.3f}) | {cz}/{n} | {mean:.4g} | {med:.4g} | {maxabs:.4g} | {minm:.4g} | {medm:.4g} | {failures} |".format(
            k=c_sv["k"],
            n=c_sv["n"],
            frac=c_sv["fraction"],
            cz=c_sv["contains_zero"],
            mean=c_sv["mean"],
            med=c_sv["median_abs"],
            maxabs=c_sv["max_abs"],
            minm=c_sv["min_margin"],
            medm=c_sv["median_margin"],
            failures=", ".join(c_sv["failures"]) if c_sv["failures"] else "none",
        ),
        "",
        "Conclusion: c_SV remains numerically centered near zero and is evaluated as an equivalence endpoint, not as closed-form point recovery.",
        "",
        "### Delta Consistency",
        "",
        "| Coefficient | Non-near-zero pass count | Near-zero count | Max abs error (non-near-zero) | Tolerance | Near-zero instances | Failures |",
        "|---|---:|---:|---:|---:|---|---|",
        _delta_row("delta_VD", delta_vd),
        _delta_row("delta_SV", delta_sv),
        "",
        "Conclusion: the delta checks are deterministic white-box consistency checks on non-near-zero instances; no binomial or pooled-SE test applies.",
        "",
        "### Specified Beta1 Near-Miss Check",
        "",
        "| Instance | measured beta1 | closed vtilde | SE | abs(z) | Interpretation |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in near:
        lines.append(
            f"| {row['instance_id']} | {row['measured']:.6g} | {row['closed']:.6g} | "
            f"{row['se']:.6g} | {row['abs_z']:.3f} | {row['interpretation']} |"
        )
    if not near:
        lines.append("| none |  |  |  |  |  |")
    lines.extend([
        "",
        "Interpretation rule: |z| below roughly 2.5-3 SE is treated as coverage noise; larger values motivate extraction/model-audit work.",
        "",
    ])
    return "\n".join(lines)


def _delta_row(name: str, data: dict) -> str:
    return (
        f"| {name} | {data['k']}/{data['n']} ({data['fraction']:.3f}) | "
        f"{data['near_zero_n']} | {data['max_abs_error_nonzero']:.4g} | "
        f"{data['tol']:.4g} | "
        f"{', '.join(data['near_zero']) if data['near_zero'] else 'none'} | "
        f"{', '.join(data['failures']) if data['failures'] else 'none'} |"
    )


def _human_conclusion(conclusion: str) -> str:
    if conclusion == "consistent":
        return "consistent with nominal ensemble coverage"
    return "not consistent with nominal ensemble coverage"


if __name__ == "__main__":
    raise SystemExit(main())
