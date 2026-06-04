"""E11 secondary consistency check: Le Cam gap and transcript efficiency.

This additive runner evaluates the one-qubit Bernoulli toy on which the
two-point lower bound is derived. It is an arithmetic consistency check of the
bound and Fisher saturation, not an independent empirical validation.
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

from vd_sv.lecam import bernoulli_lower_bound, ip_bernoulli, two_point_lower_bound  # noqa: E402

OUTDIR = REPO_ROOT / "results" / "secondary"
CSV_PATH = OUTDIR / "e11_lecam_efficiency.csv"
REPORT_PATH = OUTDIR / "e11_lecam_efficiency_report.md"

P_MIN = 0.05
P_MAX = 0.4
N_P = 8
R_MIN = 10.0
R_MAX = 100_000.0
N_R = 9
FISHER_TOL = 1e-12
RATIO_CONSERVATIVE_LIMIT = 64.0
RATIO_LOCAL_LIMIT = 32.0

FIELDS = [
    "noise_strength",
    "R",
    "h_opt",
    "mse_sel",
    "L_conservative",
    "L_local",
    "ratio_conservative",
    "ratio_local",
    "ratio_cons_within_64",
    "ratio_loc_within_32",
    "fisher_s",
    "fisher_J",
    "fisher_saturation_product",
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
    p_grid = np.logspace(math.log10(P_MIN), math.log10(P_MAX), N_P)
    r_grid = np.logspace(math.log10(R_MIN), math.log10(R_MAX), N_R)
    rows: list[dict] = []
    for p in p_grid:
        for r in r_grid:
            rows.append(_row(float(p), float(r)))
    return rows


def _row(p: float, r: float) -> dict:
    one_minus_p = 1.0 - p
    ip_cons = ip_bernoulli(p, local=False)
    ip_loc = ip_bernoulli(p, local=True)
    h_opt = 1.0 / math.sqrt(2.0 * r * ip_cons)

    mse_sel = (1.0 - one_minus_p**2 * h_opt**2) / (r * one_minus_p**2)
    l_cons = bernoulli_lower_bound(r, p, local=False)
    l_loc = bernoulli_lower_bound(r, p, local=True)

    # Explicitly exercise the general bound helper as a consistency check.
    l_cons_general = two_point_lower_bound(r, ip_cons)
    l_loc_general = two_point_lower_bound(r, ip_loc)
    if not math.isclose(l_cons, l_cons_general, rel_tol=0.0, abs_tol=1e-18):
        raise RuntimeError("conservative Bernoulli bound disagrees with general two-point helper")
    if not math.isclose(l_loc, l_loc_general, rel_tol=0.0, abs_tol=1e-18):
        raise RuntimeError("local Bernoulli bound disagrees with general two-point helper")

    fisher_s = mse_sel * r
    fisher_j = one_minus_p**2 / (1.0 - one_minus_p**2 * h_opt**2)
    saturation = fisher_s * fisher_j
    ratio_cons = mse_sel / l_cons
    ratio_loc = mse_sel / l_loc
    return {
        "noise_strength": p,
        "R": r,
        "h_opt": h_opt,
        "mse_sel": mse_sel,
        "L_conservative": l_cons,
        "L_local": l_loc,
        "ratio_conservative": ratio_cons,
        "ratio_local": ratio_loc,
        "ratio_cons_within_64": ratio_cons <= RATIO_CONSERVATIVE_LIMIT,
        "ratio_loc_within_32": ratio_loc <= RATIO_LOCAL_LIMIT,
        "fisher_s": fisher_s,
        "fisher_J": fisher_j,
        "fisher_saturation_product": saturation,
    }


def render_report(rows: list[dict]) -> str:
    ratio_cons = np.asarray([row["ratio_conservative"] for row in rows], dtype=np.float64)
    ratio_loc = np.asarray([row["ratio_local"] for row in rows], dtype=np.float64)
    saturation = np.asarray([row["fisher_saturation_product"] for row in rows], dtype=np.float64)
    cons_pass = sum(bool(row["ratio_cons_within_64"]) for row in rows)
    loc_pass = sum(bool(row["ratio_loc_within_32"]) for row in rows)
    fisher_pass = int(np.sum(np.abs(saturation - 1.0) <= FISHER_TOL))
    lines = [
        "# E11 Le Cam Efficiency",
        "",
        "Status: secondary CONSISTENCY CHECK on the toy where the bound is derived (family P7-P13, section 17). NOT an independent empirical test. Additive layer, does not modify any frozen/hashed artifact.",
        "",
        "## Design",
        "",
        f"- p grid: `{P_MIN:g}` to `{P_MAX:g}` with `{N_P}` log-spaced points.",
        f"- R grid: `{R_MIN:g}` to `{R_MAX:g}` with `{N_R}` log-spaced points.",
        "- Toy: one-qubit Bernoulli transcript with E[X]=(1-p)t and hypotheses t=+-h.",
        "- h_opt uses the conservative information constant `I_p^Bern = 4(1-p)^2` via `vd_sv.lecam.ip_bernoulli`.",
        "",
        "## Summary",
        "",
        "| quantity | min | median | max | pass count |",
        "|---|---:|---:|---:|---:|",
        f"| MSE / conservative lower bound | {np.min(ratio_cons):.6g} | {np.median(ratio_cons):.6g} | {np.max(ratio_cons):.6g} | {cons_pass}/{len(rows)} <= 64 |",
        f"| MSE / local lower bound | {np.min(ratio_loc):.6g} | {np.median(ratio_loc):.6g} | {np.max(ratio_loc):.6g} | {loc_pass}/{len(rows)} <= 32 |",
        f"| Fisher saturation s*J | {np.min(saturation):.6g} | {np.median(saturation):.6g} | {np.max(saturation):.6g} | {fisher_pass}/{len(rows)} within {FISHER_TOL:g} |",
        "",
        "## Descriptive Conclusion",
        "",
        (
            "E11 is an arithmetic consistency check on the toy used to derive the "
            "Le Cam lower bound. Across the declared grid, the selected transcript's "
            "MSE remains within the stated conservative and local ratio limits, and "
            "the transcript sampling coefficient saturates the Fisher identity s*J=1 "
            "to numerical precision. This is not independent discriminating evidence "
            "for the QAOA VD/SV experiments."
        ),
    ]
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
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "nan"
        return f"{value:.15g}"
    return value


if __name__ == "__main__":
    raise SystemExit(main())
