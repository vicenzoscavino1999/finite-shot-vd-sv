"""E9 secondary descriptive endpoint: selection trichotomy.

This additive runner checks Thm selection_trichotomy_v10 at the leading-law
level. It classifies every frozen instance / p / method-pair cell from the
white-box signs of ``g = b_j^2 - b_i^2`` and ``Delta s = s_i - s_j`` with
``i`` the lower-bias method, then independently checks the observed sign pattern
of ``F(R) = MSE_i(R) - MSE_j(R) = -g + Delta s / R`` on a wide resource grid.
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

from experiments._common import KAPPA_SV, KAPPA_UNMIT, KAPPA_VD, frozen_models  # noqa: E402
from vd_sv.crossing import MethodLaw, certified_crossing  # noqa: E402

OUTDIR = REPO_ROOT / "results" / "secondary"
CSV_PATH = OUTDIR / "e9_selection_trichotomy.csv"
REPORT_PATH = OUTDIR / "e9_selection_trichotomy_report.md"

M_VD = 2
P_MIN = 0.02
P_MAX = 0.25
N_P = 10
R_MIN = 1e-6
R_MAX = 1e12
N_R = 900
SIGN_TOL = 1e-12

PAIRS = [
    ("vd_vs_sv", "vd", "sv"),
    ("vd_vs_unmitigated", "vd", "unmitigated"),
    ("sv_vs_unmitigated", "sv", "unmitigated"),
]

REGIMES = ["tie", "dom_i", "dom_j", "crossing"]

FIELDS = [
    "instance_id",
    "pair",
    "noise_strength",
    "method_i",
    "method_j",
    "b_i2",
    "b_j2",
    "s_i",
    "s_j",
    "g",
    "delta_s",
    "regime_predicted",
    "regime_observed",
    "predicted_eq_observed",
    "R0",
    "eta",
    "eta_below_half",
    "winner",
    "observed_sign_changes",
    "p_min",
    "p_max",
    "n_p",
    "r_min",
    "r_max",
    "n_r",
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
    for model in frozen_models():
        for p in p_grid:
            coeffs = _coefficients_at_p(model, float(p))
            for pair_name, method_a, method_b in PAIRS:
                rows.append(
                    _classify_cell(
                        instance_id=model.inst.name,
                        pair_name=pair_name,
                        method_a=method_a,
                        method_b=method_b,
                        p=float(p),
                        coeffs=coeffs,
                        r_grid=r_grid,
                    )
                )
    return rows


def _coefficients_at_p(model, p: float) -> dict[str, tuple[float, float]]:
    vd = model.vd(p, M_VD)
    sv = model.sv(p)
    unmit = model.unmitigated(p)
    return {
        "vd": (float(vd["b_VD"] ** 2), float(KAPPA_VD * vd["v_tilde_VD"])),
        "sv": (float(sv["b_SV"] ** 2), float(KAPPA_SV * sv["v_tilde_SV"])),
        "unmitigated": (float(unmit["b_0"] ** 2), float(KAPPA_UNMIT * unmit["v_tilde_0"])),
    }


def _classify_cell(
    instance_id: str,
    pair_name: str,
    method_a: str,
    method_b: str,
    p: float,
    coeffs: dict[str, tuple[float, float]],
    r_grid: np.ndarray,
) -> dict:
    b2_a, s_a = coeffs[method_a]
    b2_b, s_b = coeffs[method_b]
    if b2_a <= b2_b:
        method_i, method_j = method_a, method_b
        b_i2, b_j2, s_i, s_j = b2_a, b2_b, s_a, s_b
    else:
        method_i, method_j = method_b, method_a
        b_i2, b_j2, s_i, s_j = b2_b, b2_a, s_b, s_a

    law_a = MethodLaw(method_a, b2_a, s_a, 0.0)
    law_b = MethodLaw(method_b, b2_b, s_b, 0.0)
    certificate = certified_crossing(law_a, law_b)

    g = b_j2 - b_i2
    delta_s = s_i - s_j
    regime_predicted = _predicted_regime_from_certificate(certificate, method_i, method_j)
    regime_observed, sign_changes = _observed_regime(g, delta_s, r_grid)
    r0 = certificate.R0 if certificate.R0 is not None else float("nan")
    eta = certificate.eta if certificate.eta is not None else float("nan")
    eta_below_half = bool(np.isfinite(eta) and eta < 0.5)
    winner = _winner_label(regime_predicted, method_i, method_j)

    return {
        "instance_id": instance_id,
        "pair": pair_name,
        "noise_strength": p,
        "method_i": method_i,
        "method_j": method_j,
        "b_i2": b_i2,
        "b_j2": b_j2,
        "s_i": s_i,
        "s_j": s_j,
        "g": g,
        "delta_s": delta_s,
        "regime_predicted": regime_predicted,
        "regime_observed": regime_observed,
        "predicted_eq_observed": regime_predicted == regime_observed,
        "R0": r0,
        "eta": eta,
        "eta_below_half": eta_below_half,
        "winner": winner,
        "observed_sign_changes": sign_changes,
        "p_min": P_MIN,
        "p_max": P_MAX,
        "n_p": N_P,
        "r_min": R_MIN,
        "r_max": R_MAX,
        "n_r": N_R,
    }


def _predicted_regime_from_certificate(certificate, method_i: str, method_j: str) -> str:
    if certificate.regime == "degenerate_tie":
        return "tie"
    if certificate.regime == "certified_crossing":
        return "crossing"
    if certificate.regime == "uniform_dominance":
        return "dom_i" if certificate.winner_large_R == method_i else "dom_j"
    raise ValueError(f"unknown crossing certificate regime: {certificate.regime}")


def _observed_regime(g: float, delta_s: float, r_grid: np.ndarray) -> tuple[str, int]:
    values = -g + delta_s / r_grid
    # Do not scale by max(|F(R)|): at small R the Delta_s/R term can be huge and
    # would mask the large-R sign that distinguishes dominance from crossing.
    tol = SIGN_TOL * max(abs(g), abs(delta_s / float(np.max(r_grid))), 1e-300)
    signs = np.asarray([_sign(value, tol) for value in values], dtype=np.int64)
    nonzero = signs[signs != 0]
    if nonzero.size == 0:
        return "tie", 0
    changes = int(np.sum(nonzero[:-1] * nonzero[1:] < 0))
    if changes > 0:
        return "crossing", changes
    if np.all(nonzero < 0):
        return "dom_i", 0
    if np.all(nonzero > 0):
        return "dom_j", 0
    return "ambiguous", changes


def _sign(value: float, tol: float) -> int:
    if abs(value) <= tol:
        return 0
    return -1 if value < 0.0 else 1


def _winner_label(regime: str, method_i: str, method_j: str) -> str:
    if regime == "tie":
        return "tie"
    if regime == "dom_i":
        return method_i
    if regime == "dom_j":
        return method_j
    if regime == "crossing":
        return f"{method_j}_small_R__{method_i}_large_R"
    return "unknown"


def render_report(rows: list[dict]) -> str:
    distributions = _distribution_by_pair(rows)
    match_rate = _match_rate(rows)
    lines = [
        "# E9 Selection Trichotomy",
        "",
        "Status: secondary descriptive endpoint (family P7-P13, not primary FWER). Additive layer, does not modify any frozen/hashed artifact.",
        "",
        "## Design",
        "",
        f"- p grid: `{P_MIN:g}` to `{P_MAX:g}` with `{N_P}` log-spaced points.",
        f"- R grid for observed leading-law signs: `{R_MIN:g}` to `{R_MAX:g}` with `{N_R}` log-spaced points.",
        "- Method i is the lower-bias method in each cell.",
        "- `certified_crossing` is called with C=0 because E9 tests the leading law itself; hence every leading crossing has eta=0.",
        "",
        "## Regime Distribution",
        "",
        "| pair | cells | tie | dom_i | dom_j | crossing | match rate | eta<1/2 among crossings | winners |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for pair in [item[0] for item in PAIRS]:
        item = distributions[pair]
        lines.append(
            f"| {pair} | {item['n']} | {item['tie']} | {item['dom_i']} | "
            f"{item['dom_j']} | {item['crossing']} | {item['match_rate']:.3f} | "
            f"{item['eta_crossing_fraction']:.3f} | {item['winners']} |"
        )
    lines.extend([
        "",
        "## Global Match",
        "",
        f"Predicted-vs-observed match rate: `{match_rate:.3f}` over `{len(rows)}` cells.",
        "",
        "## Descriptive Conclusion",
        "",
        _conclusion(distributions, match_rate),
    ])
    return "\n".join(lines) + "\n"


def _distribution_by_pair(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for pair in [item[0] for item in PAIRS]:
        sub = [row for row in rows if row["pair"] == pair]
        counts = {regime: sum(row["regime_predicted"] == regime for row in sub) for regime in REGIMES}
        matches = sum(bool(row["predicted_eq_observed"]) for row in sub)
        crossing = [row for row in sub if row["regime_predicted"] == "crossing"]
        eta_ok = sum(bool(row["eta_below_half"]) for row in crossing)
        winners = {}
        for row in sub:
            winners[row["winner"]] = winners.get(row["winner"], 0) + 1
        out[pair] = {
            "n": len(sub),
            **counts,
            "match_rate": matches / len(sub) if sub else float("nan"),
            "eta_crossing_fraction": eta_ok / len(crossing) if crossing else float("nan"),
            "winners": ", ".join(f"{winner}:{count}" for winner, count in sorted(winners.items())),
        }
    return out


def _match_rate(rows: list[dict]) -> float:
    return sum(bool(row["predicted_eq_observed"]) for row in rows) / len(rows)


def _conclusion(distributions: dict[str, dict], match_rate: float) -> str:
    vd_unmit = distributions["vd_vs_unmitigated"]
    sv_unmit = distributions["sv_vs_unmitigated"]
    vd_sv = distributions["vd_vs_sv"]
    return (
        "The leading-law sign trichotomy matches the observed sign pattern on the "
        f"resource grid in {match_rate:.3f} of cells. VD vs unmitigated is classified "
        f"as a genuine crossing in {vd_unmit['crossing']}/{vd_unmit['n']} cells. "
        f"SV vs unmitigated is classified as uniform dominance of the lower-bias method "
        f"in {sv_unmit['dom_i']}/{sv_unmit['n']} cells and crossing in "
        f"{sv_unmit['crossing']}/{sv_unmit['n']} cells. VD vs SV is classified as "
        f"uniform dominance in {vd_sv['dom_i'] + vd_sv['dom_j']}/{vd_sv['n']} cells "
        f"and crossing in {vd_sv['crossing']}/{vd_sv['n']} cells. "
        "This is descriptive evidence for O9 and does not enter primary FWER gatekeeping."
    )


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
