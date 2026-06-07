"""Level 2 Step 5c: folded-noise windows and Efron-Stein bounds.

This additive Phase B analysis closes the Level 2 layer. It checks P10/P13 in
form for the device-simulation setting, without changing any frozen Level 1
artifact and without claiming the formal Level 1 certificates.
"""

from __future__ import annotations

import csv
import hashlib
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from level2 import folding, highpower, sampling  # noqa: E402
from level2.circuits import (  # noqa: E402
    MIXER_TROTTER_STEPS,
    observable_expectation,
    qiskit_to_level1_state,
    simulate_noiseless_statevector,
)
from level2.noise_model import build_noise_model, load_config  # noqa: E402
from vd_sv.coefficients import efron_stein_bound  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_window_efronstein_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_window_efronstein_report.md"
REALISTIC_VD_N6_CSV = REPO_ROOT / "level2" / "level2_vd_realistic_n6_results.csv"

INSTANCE_IDS = tuple(f"g6_k2_c{i:03d}" for i in range(5)) + tuple(
    f"g8_k3_c{i:03d}" for i in range(5)
)
NOISE_SCALES = (1, 3, 5, 7)
RESOURCE_DEFINITIONS = ("paired_sample", "two_qubit_gate_proxy")
PAIR_DEFINITIONS = (
    ("sv_vs_unmit", "sv_mitigated", "unmitigated", -1.0),
    ("vd_optimal_vs_sv_contrast", "vd_optimal", "sv_mitigated", -2.0),
)
NOISELESS_INVARIANCE_TOL = folding.NOISELESS_INVARIANCE_TOL

FIELDS = [
    "row_kind",
    "endpoint",
    "instance_id",
    "n_qubits",
    "noise_scale_lambda",
    "resource_definition",
    "method",
    "method_pair",
    "method_a",
    "method_b",
    "vd_variant",
    "mu_ideal_l2",
    "mu_noiseless_folded",
    "noiseless_abs_error",
    "D_2",
    "N_2",
    "population_mean",
    "population_bias",
    "bias_floor",
    "sampling_s_paired_sample",
    "sampling_s_two_qubit_gate_proxy",
    "crossing_R0",
    "winner_low_R",
    "winner_high_R",
    "regime",
    "expected_exponent",
    "measured_exponent",
    "fit_r2",
    "finite_R0_points",
    "R0_monotonic_nonincreasing",
    "scaling_status",
    "es_constant",
    "R_ES",
    "R_ES_status",
    "vd_bound_mse_at_R_ES",
    "sv_mse_at_R_ES",
    "vd_dominates_at_R_ES",
    "source",
    "runtime_seconds",
]


@dataclass(frozen=True)
class WindowESConfig:
    instance_ids: tuple[str, ...] = INSTANCE_IDS
    noise_scales: tuple[int, ...] = NOISE_SCALES


@dataclass(frozen=True)
class Law:
    population_mean: float
    population_bias: float
    bias_floor: float
    sampling_s: dict[str, float]
    d2: float = float("nan")
    n2: float = float("nan")


def main() -> int:
    t0 = time.time()
    rows, report = run_window_efronstein(WindowESConfig(), started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_window_efronstein(
    config: WindowESConfig,
    started_at: float | None = None,
) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    rows: list[dict] = []
    folded_laws: dict[tuple[str, int], dict[str, Law]] = {}
    folded_meta: dict[tuple[str, int], dict] = {}
    for instance_id in config.instance_ids:
        model = _select_model(instance_id)
        for scale in config.noise_scales:
            laws, meta = evaluate_folded_instance(model, int(scale))
            folded_laws[(instance_id, int(scale))] = laws
            folded_meta[(instance_id, int(scale))] = meta
            rows.extend(e8_curve_rows(instance_id, int(scale), laws, meta))
            rows.extend(e8_crossing_rows(instance_id, int(scale), laws, meta))
    rows.extend(e8_slope_rows(config, folded_laws))
    rows.extend(e12_rows(config, folded_laws))
    runtime = round(time.time() - t0, 3)
    for row in rows:
        row["runtime_seconds"] = runtime
    return rows, render_report(rows)


def evaluate_folded_instance(model, noise_scale_lambda: int) -> tuple[dict[str, Law], dict]:
    inst = model.inst
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        inst,
    )
    folded = folding.folded_stateprep_circuit(model, noise_scale_lambda)
    noiseless_state = qiskit_to_level1_state(
        np.asarray(Statevector.from_instruction(folded).data, dtype=np.complex128),
        inst.n,
    )
    mu_noiseless = observable_expectation(noiseless_state, inst)

    decomposed = folding.decompose_for_aer(folded)
    decomposed.save_density_matrix()
    result = AerSimulator(
        method="density_matrix",
        noise_model=build_noise_model(),
        seed_simulator=stable_seed(29009, inst.name, noise_scale_lambda),
    ).run(decomposed).result()
    rho_qiskit = np.asarray(result.data(0)["density_matrix"], dtype=np.complex128)
    rho = highpower.qiskit_density_to_level1(rho_qiskit, inst.n)
    rho = 0.5 * (rho + rho.conj().T)
    rho = rho / np.trace(rho)
    laws = method_laws_from_rho(model, rho, mu_ideal)
    meta = {
        "instance_id": inst.name,
        "n_qubits": int(inst.n),
        "noise_scale_lambda": int(noise_scale_lambda),
        "mu_ideal_l2": float(mu_ideal),
        "mu_noiseless_folded": float(mu_noiseless),
        "noiseless_abs_error": float(abs(mu_noiseless - mu_ideal)),
    }
    return laws, meta


def method_laws_from_rho(model, rho: np.ndarray, mu_ideal: float) -> dict[str, Law]:
    inst = model.inst
    observable = highpower.normalized_observable_values(inst)
    p_true = highpower.probability_vector(np.real(np.diag(rho)))
    assignment = sampling.assignment_matrix(highpower.configured_readout_matrices(inst.n))
    p_observed = highpower.probability_vector(assignment @ p_true)

    mu_un = float(p_observed @ observable)
    v_un = float(p_observed @ (observable**2) - mu_un**2)
    unmit = Law(
        population_mean=mu_un,
        population_bias=mu_un - mu_ideal,
        bias_floor=(mu_un - mu_ideal) ** 2,
        sampling_s={"paired_sample": v_un, "two_qubit_gate_proxy": v_un},
    )

    sector = sampling.hamming_weights(inst.n) == inst.weight
    accept = float(np.sum(p_true[sector]))
    num = float(np.sum(p_true[sector] * observable[sector]))
    mu_sv = num / accept
    v_sv = sv_delta_variance(p_observed, assignment, sector, observable, mu_sv, accept)
    sv = Law(
        population_mean=mu_sv,
        population_bias=mu_sv - mu_ideal,
        bias_floor=(mu_sv - mu_ideal) ** 2,
        sampling_s={"paired_sample": v_sv, "two_qubit_gate_proxy": v_sv},
    )

    rho2 = rho @ rho
    d2 = float(np.real(np.trace(rho2)))
    n2 = float(np.real(np.trace(np.diag(observable) @ rho2)))
    mu_vd = n2 / d2
    v_vd = float((1.0 - n2 * n2 + mu_vd * mu_vd * (1.0 - d2 * d2)) / (d2 * d2))
    k_twoq = 2.0 * (1.0 + inst.n)
    vd = Law(
        population_mean=mu_vd,
        population_bias=mu_vd - mu_ideal,
        bias_floor=(mu_vd - mu_ideal) ** 2,
        sampling_s={"paired_sample": v_vd, "two_qubit_gate_proxy": k_twoq * v_vd},
        d2=d2,
        n2=n2,
    )
    return {"unmitigated": unmit, "sv_mitigated": sv, "vd_optimal": vd}


def sv_delta_variance(
    p_observed: np.ndarray,
    assignment: np.ndarray,
    sector: np.ndarray,
    observable: np.ndarray,
    mu_sv: float,
    accept: float,
) -> float:
    assignment_inv = np.linalg.inv(assignment)
    num_weights = assignment_inv.T @ (sector * observable)
    den_weights = assignment_inv.T @ sector.astype(np.float64)
    gradient = (num_weights - mu_sv * den_weights) / accept
    mean_gradient = float(p_observed @ gradient)
    return float(p_observed @ (gradient**2) - mean_gradient**2)


def e8_curve_rows(instance_id: str, scale: int, laws: dict[str, Law], meta: dict) -> list[dict]:
    rows = []
    for method, law in laws.items():
        rows.append({
            "row_kind": "e8_curve",
            "endpoint": "E8_P10_in_form",
            "instance_id": instance_id,
            "n_qubits": meta["n_qubits"],
            "noise_scale_lambda": int(scale),
            "method": method,
            "vd_variant": "vd_optimal_state_noise_only_contrast" if method == "vd_optimal" else "",
            "mu_ideal_l2": meta["mu_ideal_l2"],
            "mu_noiseless_folded": meta["mu_noiseless_folded"],
            "noiseless_abs_error": meta["noiseless_abs_error"],
            "D_2": law.d2,
            "N_2": law.n2,
            "population_mean": law.population_mean,
            "population_bias": law.population_bias,
            "bias_floor": law.bias_floor,
            "sampling_s_paired_sample": law.sampling_s["paired_sample"],
            "sampling_s_two_qubit_gate_proxy": law.sampling_s["two_qubit_gate_proxy"],
            "source": "folded_exact_density_matrix",
        })
    return rows


def e8_crossing_rows(instance_id: str, scale: int, laws: dict[str, Law], meta: dict) -> list[dict]:
    rows = []
    for resource_definition in RESOURCE_DEFINITIONS:
        for pair_name, method_a, method_b, expected in PAIR_DEFINITIONS:
            a = laws[method_a]
            b = laws[method_b]
            r0 = leading_crossing_r0(
                a.bias_floor,
                a.sampling_s[resource_definition],
                b.bias_floor,
                b.sampling_s[resource_definition],
            )
            winner_low = method_a if a.sampling_s[resource_definition] <= b.sampling_s[resource_definition] else method_b
            winner_high = method_a if a.bias_floor <= b.bias_floor else method_b
            rows.append({
                "row_kind": "e8_crossing",
                "endpoint": "E8_P10_in_form",
                "instance_id": instance_id,
                "n_qubits": meta["n_qubits"],
                "noise_scale_lambda": int(scale),
                "resource_definition": resource_definition,
                "method_pair": pair_name,
                "method_a": method_a,
                "method_b": method_b,
                "vd_variant": "vd_optimal_state_noise_only_contrast" if "vd" in pair_name else "",
                "crossing_R0": r0 if r0 is not None else "",
                "winner_low_R": winner_low,
                "winner_high_R": winner_high,
                "regime": "crossing" if r0 is not None else f"uniform_{winner_high if winner_low == winner_high else winner_low}",
                "expected_exponent": expected,
                "source": "folded_exact_density_matrix",
            })
    return rows


def e8_slope_rows(config: WindowESConfig, folded_laws: dict[tuple[str, int], dict[str, Law]]) -> list[dict]:
    rows = []
    for instance_id in config.instance_ids:
        model = _select_model(instance_id)
        for resource_definition in RESOURCE_DEFINITIONS:
            for pair_name, method_a, method_b, expected in PAIR_DEFINITIONS:
                scales = []
                r0_values = []
                for scale in config.noise_scales:
                    laws = folded_laws[(instance_id, int(scale))]
                    r0 = leading_crossing_r0(
                        laws[method_a].bias_floor,
                        laws[method_a].sampling_s[resource_definition],
                        laws[method_b].bias_floor,
                        laws[method_b].sampling_s[resource_definition],
                    )
                    if r0 is not None:
                        scales.append(float(scale))
                        r0_values.append(float(r0))
                slope, r2 = loglog_slope(scales, r0_values)
                rows.append({
                    "row_kind": "e8_slope",
                    "endpoint": "E8_P10_in_form",
                    "instance_id": instance_id,
                    "n_qubits": model.inst.n,
                    "resource_definition": resource_definition,
                    "method_pair": pair_name,
                    "method_a": method_a,
                    "method_b": method_b,
                    "vd_variant": "vd_optimal_state_noise_only_contrast" if "vd" in pair_name else "",
                    "expected_exponent": expected,
                    "measured_exponent": slope,
                    "fit_r2": r2,
                    "finite_R0_points": len(r0_values),
                    "R0_monotonic_nonincreasing": monotonic_nonincreasing(r0_values),
                    "scaling_status": scaling_status(slope, len(r0_values)),
                    "source": "folded_exact_density_matrix",
                })
    return rows


def e12_rows(config: WindowESConfig, folded_laws: dict[tuple[str, int], dict[str, Law]]) -> list[dict]:
    realistic_n6 = read_realistic_n6_large_rows()
    rows = []
    for instance_id in config.instance_ids:
        model = _select_model(instance_id)
        sv = folded_laws[(instance_id, 1)]["sv_mitigated"]
        vd_opt = folded_laws[(instance_id, 1)]["vd_optimal"]
        variants: list[tuple[str, Law]] = [("vd_optimal_contrast", vd_opt)]
        if model.inst.n == 6:
            variants.insert(0, ("vd_selected_realistic_interference_n6", law_from_realistic_row(realistic_n6[instance_id])))
        else:
            variants.insert(0, ("vd_selected_optimal_n8_a_fortiori", vd_opt))
        for vd_variant, vd_law in variants:
            for resource_definition in RESOURCE_DEFINITIONS:
                rows.append(e12_row(instance_id, model.inst.n, vd_variant, vd_law, sv, resource_definition))
    return rows


def e12_row(
    instance_id: str,
    n_qubits: int,
    vd_variant: str,
    vd_law: Law,
    sv_law: Law,
    resource_definition: str,
) -> dict:
    if resource_definition == "two_qubit_gate_proxy":
        vd_kappa = 2.0 * (1.0 + n_qubits)
    else:
        vd_kappa = 1.0
    es_const = float(efron_stein_bound(vd_law.d2))
    vd_s_es = vd_kappa * es_const
    sv_s = sv_law.sampling_s[resource_definition]
    r_es = leading_crossing_r0(vd_law.bias_floor, vd_s_es, sv_law.bias_floor, sv_s)
    if r_es is None:
        status = "no_finite_R_ES_bias_or_variance_dominated"
        vd_mse = float("nan")
        sv_mse = float("nan")
        dominates = False
    else:
        status = "finite_R_ES_nonoperational" if r_es > 1.0e6 else "finite_R_ES_operational_scale"
        vd_mse = vd_law.bias_floor + vd_s_es / r_es
        sv_mse = sv_law.bias_floor + sv_s / r_es
        dominates = bool(vd_mse <= sv_mse and r_es <= 1.0e6)
    return {
        "row_kind": "e12_efron_stein",
        "endpoint": "E12_P13_in_form",
        "instance_id": instance_id,
        "n_qubits": int(n_qubits),
        "resource_definition": resource_definition,
        "method_pair": f"{vd_variant}_vs_sv",
        "method_a": vd_variant,
        "method_b": "sv_mitigated",
        "vd_variant": vd_variant,
        "D_2": vd_law.d2,
        "N_2": vd_law.n2,
        "bias_floor": vd_law.bias_floor,
        "sampling_s_paired_sample": vd_law.sampling_s.get("paired_sample", ""),
        "sampling_s_two_qubit_gate_proxy": vd_s_es,
        "es_constant": es_const,
        "R_ES": r_es if r_es is not None else "",
        "R_ES_status": status,
        "vd_bound_mse_at_R_ES": vd_mse,
        "sv_mse_at_R_ES": sv_mse,
        "vd_dominates_at_R_ES": dominates,
        "source": "efron_stein_bound_read_only",
    }


def law_from_realistic_row(row: dict[str, str]) -> Law:
    d2 = float(row["D_2_realistic"])
    n2 = float(row["N_2_realistic"])
    mean = float(row["vd_realistic_population_mean"])
    bias = float(row["vd_realistic_population_bias"])
    var_b = median_instance_var_times_b(row["instance_id"])
    return Law(
        population_mean=mean,
        population_bias=bias,
        bias_floor=bias * bias,
        sampling_s={"paired_sample": var_b, "two_qubit_gate_proxy": float(row["kappa_two_qubit_gate_proxy"]) * var_b},
        d2=d2,
        n2=n2,
    )


def median_instance_var_times_b(instance_id: str) -> float:
    rows = [row for row in read_csv(REALISTIC_VD_N6_CSV) if row["instance_id"] == instance_id]
    return float(np.median([float(row["var_times_B"]) for row in rows]))


def read_realistic_n6_large_rows() -> dict[str, dict[str, str]]:
    rows = read_csv(REALISTIC_VD_N6_CSV)
    out = {}
    for instance_id in sorted({row["instance_id"] for row in rows}):
        inst_rows = [row for row in rows if row["instance_id"] == instance_id]
        out[instance_id] = max(inst_rows, key=lambda row: int(row["B"]))
    return out


def leading_crossing_r0(b2_a: float, s_a: float, b2_b: float, s_b: float) -> float | None:
    denom = float(b2_a) - float(b2_b)
    numer = -(float(s_a) - float(s_b))
    if abs(denom) <= 1.0e-18:
        return None
    r0 = numer / denom
    if not math.isfinite(r0) or r0 <= 0.0:
        return None
    return float(r0)


def loglog_slope(scales: list[float], values: list[float]) -> tuple[float | str, float | str]:
    if len(values) < 3:
        return "", ""
    x = np.log(np.asarray(scales, dtype=np.float64))
    y = np.log(np.asarray(values, dtype=np.float64))
    coeff = np.polyfit(x, y, 1)
    yhat = np.polyval(coeff, x)
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r2 = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return float(coeff[0]), float(r2)


def monotonic_nonincreasing(values: list[float]) -> bool | str:
    if len(values) < 2:
        return ""
    return all(values[i + 1] <= values[i] * (1.0 + 1.0e-9) for i in range(len(values) - 1))


def scaling_status(slope, finite_points: int) -> str:
    if finite_points < 3 or slope == "":
        return "insufficient_positive_crossings"
    if float(slope) < 0.0:
        return "decreasing_with_folded_noise"
    return "not_asymptotic_or_readout_floor_dominated"


def render_report(rows: list[dict]) -> str:
    slopes = [row for row in rows if row["row_kind"] == "e8_slope"]
    e12 = [row for row in rows if row["row_kind"] == "e12_efron_stein"]
    sv_un = [
        row for row in slopes
        if row["method_pair"] == "sv_vs_unmit"
        and row["resource_definition"] == "paired_sample"
        and row["measured_exponent"] != ""
    ]
    vd_sv = [
        row for row in slopes
        if row["method_pair"] == "vd_optimal_vs_sv_contrast"
        and row["resource_definition"] == "two_qubit_gate_proxy"
        and row["measured_exponent"] != ""
    ]
    selected_e12 = [
        row for row in e12
        if str(row["method_a"]).startswith("vd_selected")
        and row["resource_definition"] == "two_qubit_gate_proxy"
    ]
    finite_es = [row for row in selected_e12 if row["R_ES"] != ""]
    contrast_e12 = [
        row for row in e12
        if row["method_a"] == "vd_optimal_contrast"
        and row["resource_definition"] == "two_qubit_gate_proxy"
    ]
    finite_contrast = [row for row in contrast_e12 if row["R_ES"] != ""]
    lines = [
        "# Level 2 Step 5c Window Location And Efron-Stein",
        "",
        "Status: EN FORMA; E8/P10 folded-noise window-location and E12/P13 Efron-Stein operational analysis. Additive Phase B; not a freeze and not a Level 1 formal certificate.",
        "",
        "## E8/P10 Folded-Noise Window Location",
        "",
        "- Noise knob: global unitary folding on state preparation with lambda in `{1, 3, 5, 7}`.",
        "- Methods: unmitigated and SV use exact folded rho plus configured readout; VD is the optimistic state-noise-only contrast.",
        "- Important caveat: lambda is a device-depth noise-amplification knob with readout/base-noise floors, not the small-p analytic parameter of Level 1.",
        "",
        f"- SV-vs-unmit measured slope median: `{median_slope(sv_un):.6g}` vs expected `-1` matched-leading-variance scaling.",
        f"- VD-optimal-vs-SV measured slope median: `{median_slope(vd_sv):.6g}` vs expected `-2` generic scaling.",
        "",
        "| instance | pair | resource | expected | measured | R2 | finite R0 pts | monotone nonincreasing | status |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in slopes:
        if row["resource_definition"] not in {"paired_sample", "two_qubit_gate_proxy"}:
            continue
        if row["method_pair"] == "sv_vs_unmit" and row["resource_definition"] != "paired_sample":
            continue
        if row["method_pair"] == "vd_optimal_vs_sv_contrast" and row["resource_definition"] != "two_qubit_gate_proxy":
            continue
        lines.append(
            f"| {row['instance_id']} | {row['method_pair']} | {row['resource_definition']} "
            f"| {row['expected_exponent']} | {_fmt(row['measured_exponent'])} "
            f"| {_fmt(row['fit_r2'])} | {row['finite_R0_points']} "
            f"| {row['R0_monotonic_nonincreasing']} | {row['scaling_status']} |"
        )
    lines.extend([
        "",
        "## E12/P13 Efron-Stein Operational Bound",
        "",
        "- Selected VD convention: n=6 realistic-interference VD; n=8 optimistic VD as an a-fortiori upper benchmark.",
        f"- Selected VD finite two-qubit-proxy R_ES rows: `{len(finite_es)}/{len(selected_e12)}`.",
        f"- Largest finite selected R_ES: `{_fmt_or_none(max(float(row['R_ES']) for row in finite_es) if finite_es else '')}`.",
        f"- Optimistic-contrast finite two-qubit-proxy R_ES rows: `{len(finite_contrast)}/{len(contrast_e12)}`.",
        f"- Largest finite optimistic-contrast R_ES: `{_fmt_or_none(max(float(row['R_ES']) for row in finite_contrast) if finite_contrast else '')}`.",
        f"- Selected VD dominates at R_ES on operational scale: `{sum(bool(row['vd_dominates_at_R_ES']) for row in selected_e12)}/{len(selected_e12)}`.",
        "",
        "| instance | n | VD variant | resource | R_ES | status | ES constant | VD dominates at R_ES |",
        "|---|---:|---|---|---:|---|---:|---|",
    ])
    for row in selected_e12:
        lines.append(
            f"| {row['instance_id']} | {row['n_qubits']} | {row['vd_variant']} "
            f"| {row['resource_definition']} | {_fmt(row['R_ES'])} | {row['R_ES_status']} "
            f"| {_fmt(row['es_constant'])} | {row['vd_dominates_at_R_ES']} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "E8 in the folded device-simulation setting does not cleanly recover the small-p "
            "Level 1 exponents; the measured slopes are reported with explicit statuses because "
            "readout/base-noise floors and global folding move the sweep outside the asymptotic "
            "regime. E12 shows that the Efron-Stein VD variance bound does not create an "
            "operational resource window where selected VD dominates SV."
        ),
        "",
        f"Runtime for this analysis: `{max(float(row['runtime_seconds']) for row in rows):.3f}` seconds.",
    ])
    return "\n".join(lines) + "\n"


def median_slope(rows: list[dict]) -> float:
    vals = [float(row["measured_exponent"]) for row in rows if row["measured_exponent"] != ""]
    if not vals:
        return float("nan")
    return float(np.median(vals))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _select_model(instance_id: str):
    for model in frozen_models():
        if model.inst.name == instance_id:
            return model
    raise ValueError(f"instance not found: {instance_id}")


def stable_seed(base_seed: int, *parts: object) -> int:
    payload = "|".join([str(int(base_seed)), *(str(part) for part in parts)]).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1)


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


def _fmt_or_none(value) -> str:
    if value == "" or value is None:
        return "none"
    return _fmt(value)


if __name__ == "__main__":
    raise SystemExit(main())
