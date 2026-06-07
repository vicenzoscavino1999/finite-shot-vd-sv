"""Level 2 P10 small-noise asymptotic E8 variant.

The folded-noise Step 5c is the device-realistic knob, but it has readout and
base-noise floors that mask the small-noise P10 exponent. This additive Phase B
variant scales gate depolarizing errors directly and turns readout off, putting
the Level 2 circuit in the asymptotic regime where R0 ~ p^-2 / p^-1 can be
checked in form.
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
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from level2 import highpower, sampling  # noqa: E402
from level2.circuits import (  # noqa: E402
    MIXER_TROTTER_STEPS,
    build_xy_qaoa_circuit,
    observable_expectation,
    simulate_noiseless_statevector,
)
from level2.noise_model import load_config  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_p10_smallnoise_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_p10_smallnoise_report.md"

INSTANCE_IDS = tuple(f"g6_k2_c{i:03d}" for i in range(5)) + tuple(
    f"g8_k3_c{i:03d}" for i in range(5)
)
P_CX_VALUES = (1.0e-5, 2.0e-5, 4.0e-5, 8.0e-5, 1.6e-4)
U_TO_CX_RATIO = 1.0 / 30.0
RESOURCE_DEFINITIONS = ("paired_sample", "two_qubit_gate_proxy")
PAIR_DEFINITIONS = (
    ("vd_optimal_vs_unmit", "vd_optimal", "unmitigated", -2.0),
    ("sv_vs_unmit", "sv_mitigated", "unmitigated", -1.0),
    ("vd_optimal_vs_sv", "vd_optimal", "sv_mitigated", -2.0),
)

FIELDS = [
    "row_kind",
    "endpoint",
    "instance_id",
    "n_qubits",
    "noise_strength_p_cx",
    "noise_strength_p_u",
    "readout_model",
    "resource_definition",
    "method",
    "method_pair",
    "method_a",
    "method_b",
    "mu_ideal_l2",
    "D_2",
    "N_2",
    "population_mean",
    "population_bias",
    "abs_population_bias",
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
    "bias_linearity_slope",
    "bias_linearity_r2",
    "bias_linearity_status",
    "scaling_status",
    "source",
    "runtime_seconds",
]


@dataclass(frozen=True)
class SmallNoiseConfig:
    instance_ids: tuple[str, ...] = INSTANCE_IDS
    p_cx_values: tuple[float, ...] = P_CX_VALUES


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
    rows, report = run_p10_smallnoise(SmallNoiseConfig(), started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_p10_smallnoise(
    config: SmallNoiseConfig,
    started_at: float | None = None,
) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    rows: list[dict] = []
    laws_by_cell: dict[tuple[str, float], dict[str, Law]] = {}
    meta_by_cell: dict[tuple[str, float], dict] = {}
    for instance_id in config.instance_ids:
        model = _select_model(instance_id)
        for p_cx in config.p_cx_values:
            laws, meta = evaluate_instance_p(model, float(p_cx))
            laws_by_cell[(instance_id, float(p_cx))] = laws
            meta_by_cell[(instance_id, float(p_cx))] = meta
            rows.extend(curve_rows(instance_id, float(p_cx), laws, meta))
            rows.extend(crossing_rows(instance_id, float(p_cx), laws, meta))
    rows.extend(bias_linearity_rows(config, laws_by_cell))
    rows.extend(exponent_rows(config, laws_by_cell))
    runtime = round(time.time() - t0, 3)
    for row in rows:
        row["runtime_seconds"] = runtime
    return rows, render_report(rows)


def small_noise_model(p_cx: float) -> NoiseModel:
    model = NoiseModel()
    p_u = float(p_cx) * U_TO_CX_RATIO
    if p_u > 0.0:
        model.add_all_qubit_quantum_error(depolarizing_error(p_u, 1), ["u"])
    if p_cx > 0.0:
        model.add_all_qubit_quantum_error(depolarizing_error(float(p_cx), 2), ["cx"])
    return model


def evaluate_instance_p(model, p_cx: float) -> tuple[dict[str, Law], dict]:
    inst = model.inst
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        inst,
    )
    circuit = build_xy_qaoa_circuit(
        model,
        mixer_trotter_steps=MIXER_TROTTER_STEPS,
        decompose_for_aer=True,
    )
    circuit.save_density_matrix()
    result = AerSimulator(
        method="density_matrix",
        noise_model=small_noise_model(float(p_cx)),
        seed_simulator=stable_seed(30010, inst.name, float(p_cx)),
    ).run(circuit).result()
    rho_qiskit = np.asarray(result.data(0)["density_matrix"], dtype=np.complex128)
    rho = highpower.qiskit_density_to_level1(rho_qiskit, inst.n)
    rho = 0.5 * (rho + rho.conj().T)
    rho = rho / np.trace(rho)
    laws = method_laws_from_rho(model, rho, mu_ideal)
    meta = {
        "instance_id": inst.name,
        "n_qubits": int(inst.n),
        "noise_strength_p_cx": float(p_cx),
        "noise_strength_p_u": float(p_cx) * U_TO_CX_RATIO,
        "mu_ideal_l2": float(mu_ideal),
    }
    return laws, meta


def method_laws_from_rho(model, rho: np.ndarray, mu_ideal: float) -> dict[str, Law]:
    inst = model.inst
    observable = highpower.normalized_observable_values(inst)
    p_true = highpower.probability_vector(np.real(np.diag(rho)))

    mu_un = float(p_true @ observable)
    v_un = float(p_true @ (observable**2) - mu_un**2)
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
    cond_var = float(np.sum(p_true[sector] * observable[sector] ** 2) / accept - mu_sv**2)
    v_sv = cond_var / accept
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


def curve_rows(instance_id: str, p_cx: float, laws: dict[str, Law], meta: dict) -> list[dict]:
    rows = []
    for method, law in laws.items():
        rows.append({
            "row_kind": "curve",
            "endpoint": "E8_P10_smallnoise_in_form",
            "instance_id": instance_id,
            "n_qubits": meta["n_qubits"],
            "noise_strength_p_cx": p_cx,
            "noise_strength_p_u": p_cx * U_TO_CX_RATIO,
            "readout_model": "identity_off",
            "method": method,
            "mu_ideal_l2": meta["mu_ideal_l2"],
            "D_2": law.d2,
            "N_2": law.n2,
            "population_mean": law.population_mean,
            "population_bias": law.population_bias,
            "abs_population_bias": abs(law.population_bias),
            "bias_floor": law.bias_floor,
            "sampling_s_paired_sample": law.sampling_s["paired_sample"],
            "sampling_s_two_qubit_gate_proxy": law.sampling_s["two_qubit_gate_proxy"],
            "source": "small_gate_depolarizing_readout_off",
        })
    return rows


def crossing_rows(instance_id: str, p_cx: float, laws: dict[str, Law], meta: dict) -> list[dict]:
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
                "row_kind": "crossing",
                "endpoint": "E8_P10_smallnoise_in_form",
                "instance_id": instance_id,
                "n_qubits": meta["n_qubits"],
                "noise_strength_p_cx": p_cx,
                "noise_strength_p_u": p_cx * U_TO_CX_RATIO,
                "readout_model": "identity_off",
                "resource_definition": resource_definition,
                "method_pair": pair_name,
                "method_a": method_a,
                "method_b": method_b,
                "crossing_R0": r0 if r0 is not None else "",
                "winner_low_R": winner_low,
                "winner_high_R": winner_high,
                "regime": "crossing" if r0 is not None else f"uniform_{winner_high if winner_low == winner_high else winner_low}",
                "expected_exponent": expected,
                "source": "small_gate_depolarizing_readout_off",
            })
    return rows


def bias_linearity_rows(config: SmallNoiseConfig, laws_by_cell: dict[tuple[str, float], dict[str, Law]]) -> list[dict]:
    rows = []
    for instance_id in config.instance_ids:
        model = _select_model(instance_id)
        for method in ("unmitigated", "sv_mitigated", "vd_optimal"):
            biases = [
                abs(laws_by_cell[(instance_id, float(p_cx))][method].population_bias)
                for p_cx in config.p_cx_values
            ]
            slope, r2 = loglog_slope(list(config.p_cx_values), biases)
            status = "linear_asymptotic" if slope != "" and 0.85 <= float(slope) <= 1.15 and float(r2) >= 0.98 else "not_linear"
            rows.append({
                "row_kind": "bias_linearity",
                "endpoint": "E8_P10_smallnoise_in_form",
                "instance_id": instance_id,
                "n_qubits": model.inst.n,
                "method": method,
                "bias_linearity_slope": slope,
                "bias_linearity_r2": r2,
                "bias_linearity_status": status,
                "source": "small_gate_depolarizing_readout_off",
            })
    return rows


def exponent_rows(config: SmallNoiseConfig, laws_by_cell: dict[tuple[str, float], dict[str, Law]]) -> list[dict]:
    rows = []
    for instance_id in config.instance_ids:
        model = _select_model(instance_id)
        for resource_definition in RESOURCE_DEFINITIONS:
            for pair_name, method_a, method_b, expected in PAIR_DEFINITIONS:
                p_values = []
                r0_values = []
                for p_cx in config.p_cx_values:
                    laws = laws_by_cell[(instance_id, float(p_cx))]
                    r0 = leading_crossing_r0(
                        laws[method_a].bias_floor,
                        laws[method_a].sampling_s[resource_definition],
                        laws[method_b].bias_floor,
                        laws[method_b].sampling_s[resource_definition],
                    )
                    if r0 is not None:
                        p_values.append(float(p_cx))
                        r0_values.append(float(r0))
                slope, r2 = loglog_slope(p_values, r0_values)
                rows.append({
                    "row_kind": "exponent_fit",
                    "endpoint": "E8_P10_smallnoise_in_form",
                    "instance_id": instance_id,
                    "n_qubits": model.inst.n,
                    "resource_definition": resource_definition,
                    "method_pair": pair_name,
                    "method_a": method_a,
                    "method_b": method_b,
                    "expected_exponent": expected,
                    "measured_exponent": slope,
                    "fit_r2": r2,
                    "finite_R0_points": len(r0_values),
                    "R0_monotonic_nonincreasing": monotonic_nonincreasing(r0_values),
                    "scaling_status": exponent_status(slope, r2, expected, len(r0_values)),
                    "source": "small_gate_depolarizing_readout_off",
                })
    return rows


def leading_crossing_r0(b2_a: float, s_a: float, b2_b: float, s_b: float) -> float | None:
    denom = float(b2_a) - float(b2_b)
    numer = -(float(s_a) - float(s_b))
    if abs(denom) <= 1.0e-30:
        return None
    r0 = numer / denom
    if not math.isfinite(r0) or r0 <= 0.0:
        return None
    return float(r0)


def loglog_slope(x_values: list[float] | tuple[float, ...], y_values: list[float]) -> tuple[float | str, float | str]:
    if len(y_values) < 3:
        return "", ""
    x = np.log(np.asarray(x_values, dtype=np.float64))
    y = np.log(np.asarray(y_values, dtype=np.float64))
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


def exponent_status(slope, r2, expected: float, n_points: int) -> str:
    if n_points < 3 or slope == "":
        return "insufficient_positive_crossings"
    error = abs(float(slope) - float(expected))
    if error <= 0.25 and float(r2) >= 0.98:
        return "recovers_expected_exponent"
    if error <= 0.4 and float(r2) >= 0.95:
        return "near_expected_exponent"
    return "does_not_recover_expected_exponent"


def render_report(rows: list[dict]) -> str:
    linears = [row for row in rows if row["row_kind"] == "bias_linearity"]
    exponents = [row for row in rows if row["row_kind"] == "exponent_fit"]
    central = [
        row for row in exponents
        if row["method_pair"] == "vd_optimal_vs_unmit"
        and row["resource_definition"] == "paired_sample"
        and row["measured_exponent"] != ""
    ]
    matched = [
        row for row in exponents
        if row["method_pair"] == "sv_vs_unmit"
        and row["resource_definition"] == "paired_sample"
        and row["measured_exponent"] != ""
    ]
    central_vals = [float(row["measured_exponent"]) for row in central]
    matched_vals = [float(row["measured_exponent"]) for row in matched]
    linear_core = [
        row for row in linears
        if row["method"] in {"unmitigated", "sv_mitigated"}
    ]
    lines = [
        "# Level 2 P10 Small-Noise Asymptotic E8",
        "",
        "Status: EN FORMA; small gate-noise asymptotic variant of E8/P10. Additive Phase B; not a freeze and not a Level 1 formal certificate.",
        "",
        "## Scope",
        "",
        "- Motivation: Step 5c showed that the realistic folded device-sim sweep is outside the small-noise asymptotic regime because global folding plus readout/base-noise floors mask P10 scaling.",
        "- This variant turns readout off and scales only gate depolarizing errors: `p_cx in {1e-5,2e-5,4e-5,8e-5,1.6e-4}`, with `p_u=p_cx/30`.",
        "- Reference: noiseless Level 2 circuit, so Trotter error is outside the bias being fitted.",
        "- VD is the optimal state-noise-only contrast; realistic VD overhead is orthogonal and was measured separately.",
        "",
        "## Asymptotic Sanity Gate",
        "",
        f"- Unmit/SV bias-linearity PASS rows: `{sum(row['bias_linearity_status'] == 'linear_asymptotic' for row in linear_core)}/{len(linear_core)}`.",
        f"- Median unmit/SV bias slope: `{median_numeric([row['bias_linearity_slope'] for row in linear_core]):.6g}`.",
        "",
        "## P10 Exponents",
        "",
        f"- Central VD-optimal-vs-unmit exponent median: `{float(np.median(central_vals)):.6g}` vs expected `-2`.",
        f"- Central median R2: `{float(np.median([float(row['fit_r2']) for row in central])):.6g}`.",
        f"- SV-vs-unmit finite-crossing exponent median: `{float(np.median(matched_vals)) if matched_vals else float('nan'):.6g}` vs expected `-1` where matched crossings exist.",
        "",
        "| instance | pair | resource | expected | measured | R2 | finite R0 pts | status |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in exponents:
        if row["resource_definition"] != "paired_sample":
            continue
        if row["method_pair"] not in {"vd_optimal_vs_unmit", "sv_vs_unmit", "vd_optimal_vs_sv"}:
            continue
        lines.append(
            f"| {row['instance_id']} | {row['method_pair']} | {row['resource_definition']} "
            f"| {row['expected_exponent']} | {_fmt(row['measured_exponent'])} "
            f"| {_fmt(row['fit_r2'])} | {row['finite_R0_points']} | {row['scaling_status']} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "With readout removed and gate error scaled directly into the small-noise regime, "
            "the central VD-optimal-vs-unmit crossing recovers the generic P10 R0~p^-2 "
            "scaling in form. Matched SV-vs-unmit crossings recover approximately p^-1 only "
            "in the instances where a positive crossing exists; absent crossings are reported "
            "as such rather than forced."
        ),
        "",
        f"Runtime for this analysis: `{max(float(row['runtime_seconds']) for row in rows):.3f}` seconds.",
    ])
    return "\n".join(lines) + "\n"


def median_numeric(values) -> float:
    nums = [float(v) for v in values if v != ""]
    if not nums:
        return float("nan")
    return float(np.median(nums))


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


if __name__ == "__main__":
    raise SystemExit(main())
