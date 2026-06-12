"""Generate the anchored Level 1 figures from the canonical CSV outputs.

Each figure corresponds to a prediction in EXPERIMENTAL_PLAN sec. 15.  Reads from
``results/`` and writes PDFs to ``figures/``.  Requires the ``figures`` extra.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
FIGURES = REPO / "figures"

sys.path.insert(0, str(REPO / "src"))
from vd_sv.plotting import _col, _require_mpl, load_csv  # noqa: E402


def fig_e1(plt):
    rows = _primary_rows(load_csv(RESULTS / "e1_quotient_decomposition.csv"))
    fig, ax = plt.subplots(figsize=(5, 4))
    for method, mk in (("vd", "o"), ("unmitigated", "s")):
        sub = [r for r in rows if r["method"] == method]
        invB = [1.0 / float(r["B"]) for r in sub]
        ax.plot(invB, _col(sub, "mse"), mk, label=f"{method} MSE")
    ax.set_xlabel("1/B"); ax.set_ylabel("MSE"); ax.legend()
    ax.set_title("E1: VD quotient MSE law (P1, P2)")
    fig.tight_layout(); fig.savefig(FIGURES / "e1_quotient_law.pdf"); plt.close(fig)


def fig_e2(plt):
    rows = _primary_rows(load_csv(RESULTS / "e2_c_sv_zero.csv"))
    p0 = sorted({float(r["noise_strength"]) for r in rows})[-1]
    fig, ax = plt.subplots(figsize=(5, 4))
    for method, mk in (("vd", "o"), ("sv", "s")):
        sub = [r for r in rows if r["method"] == method and abs(float(r["noise_strength"]) - p0) < 1e-9]
        invB = [1.0 / float(r["B"]) for r in sub]
        ax.plot(invB, _col(sub, "bias_minus_pop"), mk, label=f"{method}")
    ax.axhline(0.0, color="k", lw=0.5)
    ax.set_xlabel("1/B"); ax.set_ylabel("E[mu_hat] - mu_pop")
    ax.set_title(f"E2: c_SV=0 vs c_VD!=0 (p={p0})"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES / "e2_c_sv.pdf"); plt.close(fig)


def fig_delta(plt, name, fname, title):
    rows = _primary_rows(load_csv(RESULTS / name))
    bcol = "b_vd_inf" if "vd" in name else "b_sv"
    mcol = "delta_vd_measured" if "vd" in name else "delta_sv_measured"
    ccol = "delta_vd_closed_form" if "vd" in name else "delta_sv_closed_form"
    ps = _col(rows, "noise_strength"); b = _col(rows, bcol)
    slope = float(rows[0][mcol]); closed = float(rows[0][ccol])
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(ps, b, "o", label="b(p) white-box")
    ax.plot(ps, [closed * x for x in ps], "-", label=f"generator slope {closed:.4g}")
    ax.plot(ps, [slope * x for x in ps], "--", label=f"measured slope {slope:.4g}")
    ax.set_xlabel("p"); ax.set_ylabel("bias floor"); ax.set_title(title); ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES / fname); plt.close(fig)


def fig_e5(plt):
    rows = _primary_rows(load_csv(RESULTS / "e5_denominator_concentration.csv"))
    x = _col(rows, "B_over_Bden")
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.loglog(x, _col(rows, "bernstein_bound"), "-o", ms=3, label="Bernstein bound")
    ax.loglog(x, _col(rows, "bad_denominator_prob_exact"), "-s", ms=3, label="exact tail")
    empirical = [max(v, 1e-8) for v in _col(rows, "bad_denominator_prob_empirical")]
    ax.loglog(x, empirical, "^", ms=4, label="empirical (zeros floored)")
    ax.axvline(1.0, color="k", lw=0.7, ls="--")
    ax.set_xlabel("B / B_den"); ax.set_ylabel("Pr(D_hat < D_M/2)")
    ax.set_title("E5: denominator concentration (P7)"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES / "e5_denominator_concentration.pdf"); plt.close(fig)


def fig_e7(plt):
    rows = _primary_rows(load_csv(RESULTS / "e7_certified_crossing.csv"))
    R = _col(rows, "resource_R")
    fig, ax = plt.subplots(figsize=(5, 4))
    for col, lab in (("mse_vd", "VD"), ("mse_sv", "SV"), ("mse_unmit", "unmitigated")):
        ax.loglog(R, _col(rows, col), "-o", ms=3, label=lab)
    r0 = float(rows[0]["crossing_R0_leading"]); eta = float(rows[0]["eta_operational"])
    ax.axvspan(r0 * (1 - eta), r0 * (1 + eta), color="gray", alpha=0.3,
               label="fitted-remainder band")
    ax.set_xlabel("resource R"); ax.set_ylabel("MSE")
    ax.set_title(f"E7: crossing diagnostic (eta={eta:.3g})"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES / "e7_crossing.pdf"); plt.close(fig)


def fig_e7_sensitivity(plt):
    rows = [
        r for r in _primary_rows(load_csv(RESULTS / "e7_resource_observable_sensitivity.csv"))
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
    ax.set_xticks(x); ax.set_xticklabels(resource_defs, rotation=25, ha="right")
    ax.set_ylabel("leading R0"); ax.set_title("E7 sensitivity: resource and O normalization")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "e7_resource_observable_sensitivity.pdf")
    plt.close(fig)


def main() -> int:
    plt = _require_mpl()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig_e1(plt)
    fig_e2(plt)
    fig_delta(plt, "e3_delta_vd_generator.csv", "e3_delta_vd.pdf", "E3: delta_VD from generator (P5)")
    fig_delta(plt, "e4_delta_sv_firstorder.csv", "e4_delta_sv.pdf", "E4: delta_SV first order (P6)")
    fig_e5(plt)
    fig_e7(plt)
    fig_e7_sensitivity(plt)
    print(f"wrote figures to {FIGURES}")
    return 0


def _primary_rows(rows):
    instance_ids = sorted({r.get("instance_id", "") for r in rows if r.get("instance_id")})
    if not instance_ids:
        return rows
    primary = instance_ids[0]
    return [r for r in rows if r.get("instance_id") == primary]


if __name__ == "__main__":
    raise SystemExit(main())
