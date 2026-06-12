"""Generate manuscript figures from confirmatory v2 and Level 3 artifacts.

This script generates the manuscript figures from ``results/confirmatory_v2``
and ``level3/archive``.  The frozen ``scripts/generate_all_figures.py`` entry
point is intentionally left intact as part of the PAP freeze audit.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results" / "confirmatory_v2"
LEGACY_RESULTS = REPO / "results"
V1_RESULTS = REPO / "results" / "confirmatory_full"
FIGURES = REPO / "figures"
LEVEL3_ARCHIVE = REPO / "level3" / "archive"
LEVEL2_RESULTS = REPO / "level2" / "level2_crossing_denominator_results.csv"

sys.path.insert(0, str(REPO / "src"))
from vd_sv.plotting import _col, _require_mpl, load_csv  # noqa: E402


def _require_mpl_styled():
    import matplotlib

    plt = _require_mpl()
    matplotlib.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 9,
        "axes.prop_cycle": matplotlib.cycler(color=[
            "#0072B2", "#D55E00", "#009E73",
            "#CC79A7", "#E69F00", "#56B4E9",
        ]),
    })
    return plt


def fig_e1(plt):
    rows = _primary_rows(load_csv(RESULTS / "e1_quotient_decomposition.csv"))
    fig, ax = plt.subplots(figsize=(5, 4))
    for method, mk in (("vd", "o"), ("unmitigated", "s")):
        sub = [r for r in rows if r["method"] == method]
        invB = [1.0 / float(r["B"]) for r in sub]
        ax.plot(invB, _col(sub, "mse"), mk, label=f"{method} MSE")
    ax.set_xlabel("1/B")
    ax.set_ylabel("MSE")
    ax.legend(frameon=False)
    ax.set_title("E1: VD quotient MSE law (P1, P2)")
    _save(fig, plt, "e1_quotient_law.pdf")


def fig_e2(plt):
    rows = _primary_rows(load_csv(RESULTS / "e2_c_sv_zero.csv"))
    p0 = sorted({float(r["noise_strength"]) for r in rows})[-1]
    fig, ax = plt.subplots(figsize=(5, 4))
    for method, mk in (("vd", "o"), ("sv", "s")):
        sub = [
            r
            for r in rows
            if r["method"] == method and abs(float(r["noise_strength"]) - p0) < 1e-9
        ]
        invB = [1.0 / float(r["B"]) for r in sub]
        ax.plot(invB, _col(sub, "bias_minus_pop"), mk, label=method)
    ax.axhline(0.0, color="0.2", lw=0.7)
    ax.set_xlabel("1/B")
    ax.set_ylabel("E[mu_hat] - mu_pop")
    ax.set_title(f"E2: c_SV=0 vs c_VD!=0 (p={p0:g})")
    ax.legend(frameon=False)
    _save(fig, plt, "e2_c_sv.pdf")


def fig_delta(plt, name, fname, title):
    rows = _primary_rows(load_csv(RESULTS / name))
    bcol = "b_vd_inf" if "vd" in name else "b_sv"
    mcol = "delta_vd_measured" if "vd" in name else "delta_sv_measured"
    ccol = "delta_vd_closed_form" if "vd" in name else "delta_sv_closed_form"
    ps = _col(rows, "noise_strength")
    b = _col(rows, bcol)
    slope = float(rows[0][mcol])
    closed = float(rows[0][ccol])
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(ps, b, "o", label="white-box bias floor")
    ax.plot(ps, [closed * x for x in ps], "-", label=f"closed slope {closed:.3g}")
    ax.plot(ps, [slope * x for x in ps], "--", label=f"measured slope {slope:.3g}")
    ax.set_xlabel("p")
    ax.set_ylabel("bias floor")
    ax.set_title(title)
    ax.legend(frameon=False)
    _save(fig, plt, fname)


def fig_e5(plt):
    rows = _primary_rows(load_csv(RESULTS / "e5_denominator_concentration.csv"))
    x = _col(rows, "B_over_Bden")
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.loglog(x, _col(rows, "bernstein_bound"), "-o", ms=3, label="Bernstein bound")
    ax.loglog(x, _col(rows, "bad_denominator_prob_exact"), "-s", ms=3, label="exact tail")
    empirical = [max(v, 1e-8) for v in _col(rows, "bad_denominator_prob_empirical")]
    ax.loglog(x, empirical, "^", ms=4, label="empirical (zeros floored)")
    ax.axvline(1.0, color="0.2", lw=0.7, ls="--")
    ax.set_xlabel("B / B_den")
    ax.set_ylabel("Pr(D_hat < D_M/2)")
    ax.set_title("E5: denominator concentration (P7)")
    ax.legend(frameon=False)
    _save(fig, plt, "e5_denominator_concentration.pdf")


def fig_e7(plt):
    rows = _primary_rows(load_csv(RESULTS / "e7_certified_crossing.csv"))
    R = _col(rows, "resource_R")
    fig, ax = plt.subplots(figsize=(5, 4))
    for col, lab in (("mse_vd", "VD"), ("mse_sv", "SV"), ("mse_unmit", "unmitigated")):
        ax.loglog(R, _col(rows, col), "-o", ms=3, label=lab)
    r0 = float(rows[0]["crossing_R0_leading"])
    eta = float(rows[0]["eta_operational"])
    ax.axvspan(
        r0 * (1 - eta),
        r0 * (1 + eta),
        color="0.75",
        alpha=0.4,
        label="fitted-remainder band",
    )
    ax.set_xlabel("resource R")
    ax.set_ylabel("MSE")
    ax.set_title(f"E7: crossing diagnostic (eta={eta:.3g})")
    ax.legend(frameon=False)
    _save(fig, plt, "e7_crossing.pdf")


def fig_coverage_beta1(plt):
    v2 = _beta1_records(RESULTS)
    v1_source = V1_RESULTS if V1_RESULTS.exists() else LEGACY_RESULTS
    v1 = _beta1_records(v1_source)
    v1_covered = sum(r["covered"] for r in v1)
    v2_covered = sum(r["covered"] for r in v2)

    fig, (ax, ax_count) = plt.subplots(
        1,
        2,
        figsize=(7.2, 4.6),
        gridspec_kw={"width_ratios": [3.4, 1.15]},
    )
    y = np.arange(len(v2))
    ok_color = "#009E73"
    miss_color = "#D55E00"

    for yi, record in zip(y, v2, strict=True):
        lo = record["measured"] - 1.96 * record["se"]
        hi = record["measured"] + 1.96 * record["se"]
        color = ok_color if record["covered"] else miss_color
        ax.hlines(yi, lo, hi, color=color, lw=2.0)
        ax.plot(record["measured"], yi, "|", color="0.15", ms=10)
        ax.plot(record["closed"], yi, "o", color=color, ms=4.5)
        if not record["covered"]:
            ax.text(
                hi + 0.02 * _span(v2),
                yi,
                f"z={abs(record['z']):.1f}",
                va="center",
                fontsize=8,
                color=miss_color,
            )

    ax.set_yticks(y)
    ax.set_yticklabels([r["instance_id"] for r in v2], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel(r"VD $\beta_1$ coefficient")
    ax.set_title(r"P1 coverage of closed $\tilde v$")
    ax.grid(axis="x", color="0.9", lw=0.6)
    ax.plot([], [], "o", color=ok_color, label="closed coefficient inside CI")
    ax.plot([], [], "o", color=miss_color, label="outside CI")
    ax.plot([], [], "|", color="0.15", ms=10, label="WLS estimate")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.18), frameon=False, fontsize=7, ncol=3)

    ax_count.bar(["v1", "v2"], [v1_covered, v2_covered], color=[ok_color, miss_color], width=0.65)
    ax_count.set_ylim(0, 10.8)
    ax_count.set_ylabel("covered / 10")
    ax_count.set_title("fresh seeds")
    for x, value in enumerate([v1_covered, v2_covered]):
        ax_count.text(x, value + 0.25, f"{value}/10", ha="center", va="bottom", fontsize=9)
    ax_count.text(
        0.5,
        0.88,
        "v2 binomial\np=0.086",
        transform=ax_count.transAxes,
        ha="center",
        va="top",
        fontsize=8,
    )
    _save(fig, plt, "coverage_beta1.pdf")


def fig_level2_operating_window(plt):
    rows = [
        row
        for row in _load_level2_rows()
        if row["row_kind"] == "curve"
        and row["instance_id"] == "g6_k2_c000"
        and row["resource_definition"] == "two_qubit_gate_proxy"
        and row["method"] in {"unmitigated", "sv_mitigated", "vd_selected"}
    ]
    if not rows:
        raise SystemExit("missing Level 2 operating-window rows for g6_k2_c000")

    methods = [
        ("unmitigated", "unmitigated", "#999999"),
        ("sv_mitigated", "SV (readout-mitigated)", "#0072B2"),
        ("vd_selected", "VD selected (realistic n=6)", "#D55E00"),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for method, label, color in methods:
        sub = sorted((row for row in rows if row["method"] == method), key=lambda row: float(row["R"]))
        if not sub:
            raise SystemExit(f"missing Level 2 operating-window rows for {method}")
        r_values = _col(sub, "R")
        ax.loglog(r_values, _col(sub, "mse_law"), "-", color=color, lw=1.5, label=label)
        ax.loglog(r_values, _col(sub, "mse_empirical"), "o", color=color, ms=4, label=None)

    ax.set_xlabel("resource R (two-qubit-gate proxy)")
    ax.set_ylabel("MSE")
    ax.set_title("Level 2 operating window (g6_k2_c000)")
    ax.grid(axis="both", which="both", color="0.9", lw=0.6)
    ax.legend(frameon=False)
    _save(fig, plt, "level2_operating_window.pdf")


def fig_level2_denominator(plt):
    groups: dict[float, dict[str, list[float]]] = defaultdict(
        lambda: {"exact": [], "bernstein": []}
    )
    for row in _load_level2_rows():
        if row["row_kind"] != "denominator":
            continue
        ratio = float(row["B_over_B_den"])
        key = float(np.round(ratio, 3))
        exact = float(row["bad_denominator_prob_exact"])
        bound = float(row["bernstein_bound"])
        if exact > 0.0 and bound > 0.0:
            groups[key]["exact"].append(exact)
            groups[key]["bernstein"].append(bound)

    if not groups:
        raise SystemExit("missing Level 2 denominator rows")

    ratios = []
    exact_medians = []
    bound_medians = []
    for ratio in sorted(groups):
        values = groups[ratio]
        if not values["exact"] or not values["bernstein"]:
            continue
        ratios.append(ratio)
        exact_medians.append(float(np.median(values["exact"])))
        bound_medians.append(float(np.median(values["bernstein"])))

    fig, ax = plt.subplots(figsize=(5.8, 4.1))
    ax.loglog(ratios, exact_medians, "-o", ms=4, label="median exact probability")
    ax.loglog(ratios, bound_medians, "--s", ms=4, label="one-sided Bernstein bound")
    ax.set_xlabel("B / B_den")
    ax.set_ylabel("probability")
    ax.set_title("Level 2 denominator concentration")
    ax.set_ylim(bottom=1e-34)
    ax.grid(axis="both", which="both", color="0.9", lw=0.6)
    ax.legend(frameon=False)
    _save(fig, plt, "level2_denominator.pdf")


def fig_level3_hardware_mse(plt):
    paths = [
        LEVEL3_ARCHIVE / "stage3_g6_k2_c000_ibm_marrakesh_full_analysis.json",
        LEVEL3_ARCHIVE / "stage3_g6_k2_c001_ibm_marrakesh_full_analysis.json",
        LEVEL3_ARCHIVE / "stage3_g8_k3_c000_ibm_marrakesh_full_analysis.json",
    ]
    rows = [_hardware_largest_b(path) for path in paths]
    methods = [
        ("sv_readout_mitigated_weight_postselect", "SV", "#0072B2"),
        ("unmitigated", "unmit.", "#999999"),
        ("vd_m2_readout_mitigated", "VD M=2", "#D55E00"),
    ]
    x = np.arange(len(rows), dtype=float)
    width = 0.24

    fig, ax = plt.subplots(figsize=(6.7, 4.2))
    for j, (method, label, color) in enumerate(methods):
        xpos = x + (j - 1) * width
        vals = [row["mse"][method] for row in rows]
        draw_vals = vals.copy()
        diverge_idx = None
        if method == "vd_m2_readout_mitigated":
            diverge_idx = 2
            draw_vals[diverge_idx] = np.nan
        ax.bar(xpos, draw_vals, width=width, label=label, color=color, alpha=0.88)
        if diverge_idx is not None:
            raw = vals[diverge_idx]
            ax.plot(xpos[diverge_idx], raw, marker="^", ms=8, color=color, clip_on=False)
            ax.annotate(
                "VD diverges\nD~0",
                xy=(xpos[diverge_idx], raw),
                xytext=(-35, -10),
                textcoords="offset points",
                arrowprops={"arrowstyle": "->", "lw": 0.8, "color": color},
                fontsize=8,
                color=color,
                ha="right",
                va="top",
            )

    ax.set_yscale("log")
    ax.set_ylabel("MSE at B=8192")
    ax.set_xticks(x)
    ax.set_xticklabels([row["instance"] for row in rows], rotation=18, ha="right")
    ax.set_title("Level 3 hardware MSE ordering")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.grid(axis="y", which="both", color="0.9", lw=0.6)
    ax.set_ylim(8e-5, 2e7)
    _save(fig, plt, "level3_hardware_mse.pdf")


def fig_e7_sensitivity(plt):
    rows = [
        r
        for r in _primary_rows(load_csv(RESULTS / "e7_resource_observable_sensitivity.csv"))
        if r["method_pair"] == "vd_vs_unmitigated"
    ]
    resource_defs = list(dict.fromkeys(r["resource_definition"] for r in rows))
    obs_defs = list(dict.fromkeys(r["observable_normalization"] for r in rows))
    x = list(range(len(resource_defs)))
    width = 0.35
    fig, ax = plt.subplots(figsize=(6.2, 4))
    for j, obs in enumerate(obs_defs):
        sub = {r["resource_definition"]: r for r in rows if r["observable_normalization"] == obs}
        y = [float(sub[name]["leading_R0"]) for name in resource_defs]
        offset = (j - (len(obs_defs) - 1) / 2.0) * width
        ax.bar([xx + offset for xx in x], y, width=width, label=obs)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(resource_defs, rotation=25, ha="right")
    ax.set_ylabel("leading R0")
    ax.set_title("E7 sensitivity: resource and O normalization")
    ax.legend(frameon=False)
    _save(fig, plt, "e7_resource_observable_sensitivity.pdf")


def main() -> int:
    global RESULTS
    args = _parse_args()
    RESULTS = _resolve_results(args.results_dir)
    plt = _require_mpl_styled()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig_e1(plt)
    fig_e2(plt)
    fig_delta(plt, "e3_delta_vd_generator.csv", "e3_delta_vd.pdf", "E3: delta_VD from generator (P5)")
    fig_delta(plt, "e4_delta_sv_firstorder.csv", "e4_delta_sv.pdf", "E4: delta_SV first order (P6)")
    fig_e5(plt)
    fig_e7(plt)
    fig_coverage_beta1(plt)
    fig_level2_operating_window(plt)
    fig_level2_denominator(plt)
    fig_level3_hardware_mse(plt)
    if args.include_sensitivity:
        fig_e7_sensitivity(plt)
    print(f"read Level 1 results from {RESULTS}")
    print(f"wrote figures to {FIGURES}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        default=str(RESULTS.relative_to(REPO)),
        help="Level 1 results directory, relative to repo or absolute. Use 'results' for the legacy figures.",
    )
    parser.add_argument(
        "--include-sensitivity",
        action="store_true",
        help="Also regenerate the E7 resource/observable sensitivity side-check.",
    )
    return parser.parse_args()


def _resolve_results(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO / path
    path = path.resolve()
    required = [
        "e1_quotient_decomposition.csv",
        "e2_c_sv_zero.csv",
        "e3_delta_vd_generator.csv",
        "e4_delta_sv_firstorder.csv",
        "e5_denominator_concentration.csv",
        "e7_certified_crossing.csv",
    ]
    missing = [name for name in required if not (path / name).exists()]
    if missing:
        raise SystemExit(f"missing figure inputs under {path}: {', '.join(missing)}")
    return path


def _primary_rows(rows):
    instance_ids = sorted({r.get("instance_id", "") for r in rows if r.get("instance_id")})
    if not instance_ids:
        return rows
    primary = instance_ids[0]
    return [r for r in rows if r.get("instance_id") == primary]


def _beta1_records(results_dir: Path) -> list[dict]:
    rows = load_csv(results_dir / "e1_quotient_decomposition.csv")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["method"] == "vd":
            grouped[row["instance_id"]].append(row)
    records = []
    for instance_id, group in sorted(grouped.items()):
        b_grid = np.asarray([float(row["B"]) for row in group], dtype=float)
        y = np.asarray([float(row["mse"]) for row in group], dtype=float)
        se = np.asarray([max(float(row["mse_se"]), 1e-12) for row in group], dtype=float)
        x = np.column_stack([np.ones_like(b_grid), 1.0 / b_grid, 1.0 / b_grid**2])
        coeffs, cov = _wls_fit(x, y, 1.0 / se**2)
        beta1 = float(coeffs[1])
        beta1_se = float(np.sqrt(np.diag(cov))[1])
        closed = float(group[0]["vtilde_closed_form"])
        covered = beta1 - 1.96 * beta1_se <= closed <= beta1 + 1.96 * beta1_se
        records.append(
            {
                "instance_id": instance_id,
                "measured": beta1,
                "closed": closed,
                "se": beta1_se,
                "z": (beta1 - closed) / beta1_se,
                "covered": covered,
            }
        )
    return records


def _wls_fit(x_cols: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sw = np.sqrt(w)
    coeffs, *_ = np.linalg.lstsq(x_cols * sw[:, None], y * sw, rcond=None)
    xtwx = (x_cols * w[:, None]).T @ x_cols
    return coeffs, np.linalg.inv(xtwx)


def _hardware_largest_b(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    largest = int(data["qualitative"]["largest_B"])
    rows = [row for row in data["rows"] if int(row["B"]) == largest]
    mse = {row["method"]: float(row["mse"]) for row in rows}
    den = {
        row["method"]: (
            None
            if row.get("mean_vd_denominator") is None
            else float(row["mean_vd_denominator"])
        )
        for row in rows
    }
    return {"instance": path.name.split("_ibm_marrakesh")[0].replace("stage3_", ""), "mse": mse, "den": den}


def _load_level2_rows() -> list[dict]:
    if not LEVEL2_RESULTS.exists():
        raise SystemExit(f"missing Level 2 figure input: {LEVEL2_RESULTS}")
    return load_csv(LEVEL2_RESULTS)


def _span(records: list[dict]) -> float:
    vals = []
    for record in records:
        vals.extend([record["measured"] - 1.96 * record["se"], record["measured"] + 1.96 * record["se"]])
    return max(vals) - min(vals)


def _save(fig, plt, fname: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES / fname, metadata={"Creator": "finite-shot-vd-sv"})
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
