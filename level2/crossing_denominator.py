"""Level 2 Step 5b: denominator concentration and operating crossings.

This is an additive Phase B analysis over existing Step 5a CSV artifacts. It
does not run new device simulations and does not adjudicate the Level 1 formal
P7/P9 gates. The goal is to check the laws in form for the Aer/device-sim
setting and expose operating windows honestly.
"""

from __future__ import annotations

import csv
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import binom

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vd_sv.crossing import fit_remainder_constant  # noqa: E402


HIGHPOWER_CSV = REPO_ROOT / "level2" / "level2_highpower_results.csv"
REALISTIC_VD_N6_CSV = REPO_ROOT / "level2" / "level2_vd_realistic_n6_results.csv"
OUT_CSV = REPO_ROOT / "level2" / "level2_crossing_denominator_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_crossing_denominator_report.md"

RESOURCE_DEFINITIONS = ("paired_sample", "two_qubit_gate_proxy")
CURVE_METHODS = ("unmitigated", "sv_mitigated", "vd_selected", "vd_optimal_contrast")
PAIR_DEFINITIONS = (
    ("sv_vs_unmit", "sv_mitigated", "unmitigated"),
    ("vd_selected_vs_sv", "vd_selected", "sv_mitigated"),
    ("vd_selected_vs_unmit", "vd_selected", "unmitigated"),
    ("vd_optimal_vs_sv_contrast", "vd_optimal_contrast", "sv_mitigated"),
)

FIELDS = [
    "row_kind",
    "endpoint",
    "instance_id",
    "n_qubits",
    "vd_variant",
    "resource_definition",
    "method",
    "method_pair",
    "method_a",
    "method_b",
    "B",
    "R",
    "R_min",
    "R_max",
    "B_den",
    "B_over_B_den",
    "D_value",
    "bad_denominator_prob_exact",
    "bernstein_bound",
    "clip_activation_rate",
    "bias_floor",
    "sampling_s",
    "mse_empirical",
    "mse_law",
    "population_bias",
    "population_mean",
    "regime",
    "winner_low_R",
    "winner_high_R",
    "uniform_winner",
    "crossing_R0",
    "crossing_in_observed_grid",
    "R0_over_Rmax",
    "eta_operational",
    "eta_status",
    "g_bias_gap",
    "delta_s_lower_minus_other",
    "source_csv",
    "runtime_seconds",
]


@dataclass(frozen=True)
class MethodCurve:
    instance_id: str
    n_qubits: int
    method: str
    vd_variant: str
    source_csv: str
    b: np.ndarray
    r_by_resource: dict[str, np.ndarray]
    mse: np.ndarray
    var_times_b: np.ndarray
    bias_floor: float
    population_bias: float
    population_mean: float

    def sampling_s(self, resource_definition: str) -> float:
        kappa = self.r_by_resource[resource_definition] / self.b
        return float(np.median(self.var_times_b) * np.median(kappa))


def main() -> int:
    t0 = time.time()
    rows, report = run_analysis(started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_analysis(started_at: float | None = None) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    highpower = read_csv(HIGHPOWER_CSV)
    realistic = read_csv(REALISTIC_VD_N6_CSV)
    curves = build_method_curves(highpower, realistic)
    rows: list[dict] = []
    rows.extend(denominator_rows(curves))
    rows.extend(curve_rows(curves))
    rows.extend(crossing_rows(curves))
    runtime = round(time.time() - t0, 3)
    for row in rows:
        row["runtime_seconds"] = runtime
    return rows, render_report(rows)


def build_method_curves(
    highpower_rows: list[dict[str, str]],
    realistic_rows: list[dict[str, str]],
) -> dict[str, dict[str, MethodCurve]]:
    curves: dict[str, dict[str, MethodCurve]] = {}
    instance_ids = sorted({row["instance_id"] for row in highpower_rows})
    for instance_id in instance_ids:
        inst_curves: dict[str, MethodCurve] = {}
        for method in ("unmitigated", "sv_mitigated"):
            source = [row for row in highpower_rows if row["instance_id"] == instance_id and row["method"] == method]
            inst_curves[method] = curve_from_highpower(source, method, "none")
        n_qubits = int(inst_curves["unmitigated"].n_qubits)
        optimal_source = [
            row for row in highpower_rows
            if row["instance_id"] == instance_id and row["method"] == "vd_m2_hadamard_binomial"
        ]
        optimal = curve_from_highpower(optimal_source, "vd_optimal_contrast", "vd_optimal_state_noise_only")
        inst_curves["vd_optimal_contrast"] = optimal
        if n_qubits == 6:
            real_source = [row for row in realistic_rows if row["instance_id"] == instance_id]
            inst_curves["vd_selected"] = curve_from_realistic(real_source)
        else:
            inst_curves["vd_selected"] = MethodCurve(
                instance_id=optimal.instance_id,
                n_qubits=optimal.n_qubits,
                method="vd_selected",
                vd_variant="vd_optimal_state_noise_only_n8_a_fortiori",
                source_csv=optimal.source_csv,
                b=optimal.b,
                r_by_resource=optimal.r_by_resource,
                mse=optimal.mse,
                var_times_b=optimal.var_times_b,
                bias_floor=optimal.bias_floor,
                population_bias=optimal.population_bias,
                population_mean=optimal.population_mean,
            )
        curves[instance_id] = inst_curves
    return curves


def curve_from_highpower(rows: list[dict[str, str]], method: str, vd_variant: str) -> MethodCurve:
    if not rows:
        raise ValueError(f"missing highpower rows for {method}")
    ordered = sorted(rows, key=lambda row: int(row["B"]))
    b = np.asarray([int(row["B"]) for row in ordered], dtype=np.float64)
    paired = np.asarray([float(row["resource_R_paired_sample"]) for row in ordered], dtype=np.float64)
    twoq = np.asarray([float(row["resource_R_two_qubit_gate_proxy"]) for row in ordered], dtype=np.float64)
    pop_bias = float(ordered[0]["population_bias"])
    return MethodCurve(
        instance_id=ordered[0]["instance_id"],
        n_qubits=int(ordered[0]["n_qubits"]),
        method=method,
        vd_variant=vd_variant,
        source_csv=HIGHPOWER_CSV.name,
        b=b,
        r_by_resource={"paired_sample": paired, "two_qubit_gate_proxy": twoq},
        mse=np.asarray([float(row["mse_empirical"]) for row in ordered], dtype=np.float64),
        var_times_b=np.asarray([float(row["var_times_B"]) for row in ordered], dtype=np.float64),
        bias_floor=pop_bias * pop_bias,
        population_bias=pop_bias,
        population_mean=float(ordered[0]["population_mean"]),
    )


def curve_from_realistic(rows: list[dict[str, str]]) -> MethodCurve:
    if not rows:
        raise ValueError("missing realistic VD rows")
    ordered = sorted(rows, key=lambda row: int(row["B"]))
    b = np.asarray([int(row["B"]) for row in ordered], dtype=np.float64)
    paired = np.asarray([float(row["resource_R_paired_sample"]) for row in ordered], dtype=np.float64)
    twoq = np.asarray([float(row["resource_R_two_qubit_gate_proxy"]) for row in ordered], dtype=np.float64)
    pop_bias = float(ordered[0]["vd_realistic_population_bias"])
    return MethodCurve(
        instance_id=ordered[0]["instance_id"],
        n_qubits=int(ordered[0]["n_qubits"]),
        method="vd_selected",
        vd_variant="vd_realistic_interference_n6",
        source_csv=REALISTIC_VD_N6_CSV.name,
        b=b,
        r_by_resource={"paired_sample": paired, "two_qubit_gate_proxy": twoq},
        mse=np.asarray([float(row["mse_empirical"]) for row in ordered], dtype=np.float64),
        var_times_b=np.asarray([float(row["var_times_B"]) for row in ordered], dtype=np.float64),
        bias_floor=pop_bias * pop_bias,
        population_bias=pop_bias,
        population_mean=float(ordered[0]["vd_realistic_population_mean"]),
    )


def denominator_rows(curves: dict[str, dict[str, MethodCurve]]) -> list[dict]:
    rows = []
    for instance_id, inst_curves in curves.items():
        vd_curve = inst_curves["vd_selected"]
        d_value, b_den = vd_denominator_metadata(instance_id, vd_curve.vd_variant)
        for b in vd_curve.b.astype(int):
            rows.append({
                "row_kind": "denominator",
                "endpoint": "E5_P7_in_form",
                "instance_id": instance_id,
                "n_qubits": vd_curve.n_qubits,
                "vd_variant": vd_curve.vd_variant,
                "method": "vd_selected",
                "B": int(b),
                "R": int(b),
                "B_den": b_den,
                "B_over_B_den": float(b / b_den),
                "D_value": d_value,
                "bad_denominator_prob_exact": bad_denominator_prob_exact(d_value, int(b)),
                "bernstein_bound": bernstein_bound(d_value, int(b)),
                "clip_activation_rate": clip_rate_from_source(instance_id, vd_curve.vd_variant, int(b)),
                "source_csv": vd_curve.source_csv,
            })
    return rows


def curve_rows(curves: dict[str, dict[str, MethodCurve]]) -> list[dict]:
    rows = []
    for instance_id, inst_curves in curves.items():
        for resource_definition in RESOURCE_DEFINITIONS:
            for method in CURVE_METHODS:
                if method not in inst_curves:
                    continue
                curve = inst_curves[method]
                s = curve.sampling_s(resource_definition)
                for b, r, mse in zip(curve.b, curve.r_by_resource[resource_definition], curve.mse):
                    rows.append({
                        "row_kind": "curve",
                        "endpoint": "E7_P9_in_form",
                        "instance_id": instance_id,
                        "n_qubits": curve.n_qubits,
                        "vd_variant": curve.vd_variant,
                        "resource_definition": resource_definition,
                        "method": method,
                        "B": int(b),
                        "R": float(r),
                        "bias_floor": curve.bias_floor,
                        "sampling_s": s,
                        "mse_empirical": float(mse),
                        "mse_law": float(curve.bias_floor + s / float(r)),
                        "population_bias": curve.population_bias,
                        "population_mean": curve.population_mean,
                        "source_csv": curve.source_csv,
                    })
    return rows


def crossing_rows(curves: dict[str, dict[str, MethodCurve]]) -> list[dict]:
    rows = []
    for instance_id, inst_curves in curves.items():
        for resource_definition in RESOURCE_DEFINITIONS:
            for pair_name, method_a, method_b in PAIR_DEFINITIONS:
                if method_a not in inst_curves or method_b not in inst_curves:
                    continue
                a = inst_curves[method_a]
                b = inst_curves[method_b]
                if pair_name == "vd_optimal_vs_sv_contrast" and a.n_qubits == 8:
                    # For n=8 selected VD already is the optimistic VD; avoid duplicate contrast.
                    continue
                rows.append(crossing_row(pair_name, a, b, resource_definition))
    return rows


def crossing_row(pair_name: str, a: MethodCurve, b: MethodCurve, resource_definition: str) -> dict:
    s_a = a.sampling_s(resource_definition)
    s_b = b.sampling_s(resource_definition)
    r_all = np.concatenate([a.r_by_resource[resource_definition], b.r_by_resource[resource_definition]])
    r_min = float(np.min(r_all))
    r_max = float(np.max(r_all))
    winner_low = a.method if s_a <= s_b else b.method
    winner_high = a.method if a.bias_floor <= b.bias_floor else b.method
    r0 = leading_crossing_r0(a.bias_floor, s_a, b.bias_floor, s_b)
    uniform_winner = "" if r0 is not None else winner_high if winner_low == winner_high else winner_low
    regime = "crossing" if r0 is not None else f"uniform_{uniform_winner}"
    eta, eta_status, g, delta_s = eta_operational(a, b, s_a, s_b, resource_definition, r0)
    return {
        "row_kind": "crossing",
        "endpoint": "E7_P9_in_form",
        "instance_id": a.instance_id,
        "n_qubits": a.n_qubits,
        "vd_variant": a.vd_variant if a.method.startswith("vd") else b.vd_variant,
        "resource_definition": resource_definition,
        "method_pair": pair_name,
        "method_a": a.method,
        "method_b": b.method,
        "R_min": r_min,
        "R_max": r_max,
        "bias_floor": "",
        "sampling_s": "",
        "regime": regime,
        "winner_low_R": winner_low,
        "winner_high_R": winner_high,
        "uniform_winner": uniform_winner,
        "crossing_R0": float(r0) if r0 is not None else "",
        "crossing_in_observed_grid": bool(r0 is not None and r_min <= r0 <= r_max),
        "R0_over_Rmax": float(r0 / r_max) if r0 is not None else "",
        "eta_operational": eta,
        "eta_status": eta_status,
        "g_bias_gap": g,
        "delta_s_lower_minus_other": delta_s,
        "source_csv": f"{a.source_csv};{b.source_csv}",
    }


def leading_crossing_r0(b2_a: float, s_a: float, b2_b: float, s_b: float) -> float | None:
    denom = b2_a - b2_b
    numer = -(s_a - s_b)
    if abs(denom) <= 1.0e-18:
        return None
    r0 = numer / denom
    if not math.isfinite(r0) or r0 <= 0.0:
        return None
    return float(r0)


def eta_operational(
    a: MethodCurve,
    b: MethodCurve,
    s_a: float,
    s_b: float,
    resource_definition: str,
    r0: float | None,
) -> tuple[float | str, str, float, float]:
    if a.bias_floor <= b.bias_floor:
        lower, upper, s_lower, s_upper = a, b, s_a, s_b
    else:
        lower, upper, s_lower, s_upper = b, a, s_b, s_a
    g = upper.bias_floor - lower.bias_floor
    delta_s = s_lower - s_upper
    if r0 is None or g <= 0.0:
        return "", "not_applicable_no_positive_crossing", float(g), float(delta_s)
    c_lower = fit_remainder_constant(
        lower.r_by_resource[resource_definition],
        lower.mse,
        lower.bias_floor,
        s_lower,
    )
    c_upper = fit_remainder_constant(
        upper.r_by_resource[resource_definition],
        upper.mse,
        upper.bias_floor,
        s_upper,
    )
    eta = float(4.0 * (c_lower + c_upper) / (g * r0 * r0))
    status = "operational_eta_below_half" if eta < 0.5 else "operational_eta_above_half"
    return eta, status, float(g), float(delta_s)


def vd_denominator_metadata(instance_id: str, vd_variant: str) -> tuple[float, float]:
    if vd_variant == "vd_realistic_interference_n6":
        rows = [row for row in read_csv(REALISTIC_VD_N6_CSV) if row["instance_id"] == instance_id]
        row = rows[0]
        return float(row["D_2_realistic"]), float(row["B_den_realistic"])
    rows = [
        row for row in read_csv(HIGHPOWER_CSV)
        if row["instance_id"] == instance_id and row["method"] == "vd_m2_hadamard_binomial"
    ]
    row = rows[0]
    return float(row["D_2_exact"]), float(row["B_den_impl_estimate"])


def clip_rate_from_source(instance_id: str, vd_variant: str, b: int) -> float | str:
    if vd_variant != "vd_realistic_interference_n6":
        return ""
    for row in read_csv(REALISTIC_VD_N6_CSV):
        if row["instance_id"] == instance_id and int(row["B"]) == int(b):
            return float(row["clip_activation_rate"])
    return ""


def bad_denominator_prob_exact(d_value: float, b: int) -> float:
    q_d = 0.5 * (1.0 + float(d_value))
    cutoff = int(math.ceil(float(b) * (1.0 + 0.5 * float(d_value)) / 2.0) - 1)
    if cutoff < 0:
        return 0.0
    return float(binom.cdf(cutoff, int(b), q_d))


def bernstein_bound(d_value: float, b: int) -> float:
    sigma_d2 = max(1.0 - float(d_value) ** 2, 0.0)
    denom = 8.0 * sigma_d2 + (8.0 / 3.0) * float(d_value)
    return float(math.exp(-float(b) * float(d_value) ** 2 / denom))


def render_report(rows: list[dict]) -> str:
    denom = [row for row in rows if row["row_kind"] == "denominator"]
    crossings = [row for row in rows if row["row_kind"] == "crossing"]
    selected_sv = [
        row for row in crossings
        if row["method_pair"] == "vd_selected_vs_sv"
        and row["resource_definition"] == "two_qubit_gate_proxy"
    ]
    selected_sv_sv_dominates = [
        row for row in selected_sv
        if row["regime"] == "uniform_sv_mitigated" or row["winner_high_R"] == "sv_mitigated"
    ]
    opt_contrast = [
        row for row in crossings
        if row["method_pair"] == "vd_optimal_vs_sv_contrast"
        and row["resource_definition"] == "two_qubit_gate_proxy"
    ]
    opt_windows = [row for row in opt_contrast if row["regime"] == "crossing" and row["winner_high_R"] == "vd_optimal_contrast"]
    sv_unmit = [
        row for row in crossings
        if row["method_pair"] == "sv_vs_unmit" and row["resource_definition"] == "paired_sample"
    ]
    denom_summary = denominator_summary(denom)
    lines = [
        "# Level 2 Step 5b Crossing And Denominator Analysis",
        "",
        "Status: EN FORMA; denominator concentration (E5/P7) and operating crossings (E7/P9) over existing Level 2 CSVs. Additive Phase B analysis; not a freeze and not a Level 1 formal certificate.",
        "",
        "## Inputs And VD Convention",
        "",
        f"- High-power 5a CSV: `{HIGHPOWER_CSV.name}`.",
        f"- Realistic VD n=6 CSV: `{REALISTIC_VD_N6_CSV.name}`.",
        "- n=6: selected VD is the realistic c-SWAP/interference-including device circuit.",
        "- n=8: selected VD is the optimistic state-noise-only VD from 5a; since it already loses, realistic VD would lose a fortiori.",
        "",
        "## E5/P7 Denominator Concentration In Form",
        "",
        "| ratio B/B_den | median exact P(D_hat<D/2) | median Bernstein bound |",
        "|---:|---:|---:|",
    ]
    for ratio, exact, bound in denom_summary:
        lines.append(f"| {ratio:.3g} | {exact:.6g} | {bound:.6g} |")
    lines.extend([
        "",
        "The exact bad-denominator probability drops sharply around the B_den scale and is negligible by 10x B_den. Below the scale, the quotient is clip-sensitive and high-variance, matching the P7 law in form for the Aer/device-sim setting.",
        "",
        "## E7/P9 Operating Crossings In Form",
        "",
        f"- SV vs unmitigated has SV as the large-resource winner in `{sum(row['winner_high_R'] == 'sv_mitigated' for row in sv_unmit)}/{len(sv_unmit)}` instances.",
        f"- Selected VD vs SV under the two-qubit proxy is SV-dominant or large-resource SV-winning in `{len(selected_sv_sv_dominates)}/{len(selected_sv)}` instances.",
        f"- The n=6 optimistic VD contrast has a VD large-resource window in `{len(opt_windows)}/{len(opt_contrast)}` two-qubit-proxy comparisons, showing the ideal VD window that the realistic interference overhead erases.",
        "",
        "| instance | n | resource | pair | regime | low-R winner | high-R winner | R0 | R0/Rmax | eta status |",
        "|---|---:|---|---|---|---|---|---:|---:|---|",
    ])
    for row in crossings:
        if row["method_pair"] not in {"sv_vs_unmit", "vd_selected_vs_sv", "vd_optimal_vs_sv_contrast"}:
            continue
        if row["resource_definition"] != "two_qubit_gate_proxy":
            continue
        lines.append(
            f"| {row['instance_id']} | {row['n_qubits']} | {row['resource_definition']} "
            f"| {row['method_pair']} | {row['regime']} | {row['winner_low_R']} "
            f"| {row['winner_high_R']} | {_fmt(row['crossing_R0'])} "
            f"| {_fmt(row['R0_over_Rmax'])} | {row['eta_status']} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "The denominator analysis shows the expected P7 concentration transition at B/B_den ~ 1. "
            "The crossing analysis supports an operating-window narrative rather than a universal winner: "
            "SV beats unmitigated at large resource; SV dominates the realistic VD device circuit across "
            "the ensemble; and the optimistic n=6 VD window exists only when the c-SWAP/interference "
            "overhead is removed."
        ),
        "",
        f"Runtime for this analysis: `{max(float(row['runtime_seconds']) for row in rows):.3f}` seconds.",
    ])
    return "\n".join(lines) + "\n"


def denominator_summary(denom_rows: list[dict]) -> list[tuple[float, float, float]]:
    targets = (0.10, 0.25, 0.50, 1.0, 2.0, 5.0, 10.0)
    out = []
    for target in targets:
        near = [
            row for row in denom_rows
            if abs(float(row["B_over_B_den"]) - target) < max(0.015, target * 0.02)
        ]
        if not near:
            continue
        out.append((
            target,
            float(np.median([float(row["bad_denominator_prob_exact"]) for row in near])),
            float(np.median([float(row["bernstein_bound"]) for row in near])),
        ))
    return out


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


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


def _fmt(value) -> str:
    if value == "" or value is None:
        return ""
    return f"{float(value):.6g}"


if __name__ == "__main__":
    raise SystemExit(main())
