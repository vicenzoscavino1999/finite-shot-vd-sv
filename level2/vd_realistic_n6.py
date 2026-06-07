"""Level 2 realistic VD n=6 follow-up.

This additive Phase B runner measures the full M=2 VD device circuit for the
five frozen n=6 instances. Unlike the Step 5a optimistic VD rows, this includes
the decomposed c-SWAP/interference circuit noise and configured readout. The
finite-shot layer is sampled from the exact outcome distribution of the noisy
13-qubit circuit, so B can cross the denominator scale without running millions
of Aer trajectories.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from experiments.e7_resource_observable_sensitivity import resource_definitions  # noqa: E402
from level2 import highpower, sampling, vd as level2_vd  # noqa: E402
from level2.circuits import MIXER_TROTTER_STEPS, observable_expectation, simulate_noiseless_statevector  # noqa: E402
from level2.noise_model import build_noise_model, load_config  # noqa: E402
from vd_sv.estimators import make_rng  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_vd_realistic_n6_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_vd_realistic_n6_report.md"

INSTANCE_IDS = tuple(f"g6_k2_c{i:03d}" for i in range(5))
REPETITIONS = 64
BASE_SEED = 27007
B_MIN = 64
B_GRID_FACTORS = (0.10, 0.25, 0.50, 1.0, 2.0, 5.0, 10.0)
NOISELESS_D_TOL = 1.0e-10
NOISELESS_MU_TOL = 1.0e-10
DENOMINATOR_CLIP_FRACTION = 0.5
ESTIMATOR_MODEL = "exact_outcome_distribution_full_vd_circuit_with_readout"

FIELDS = [
    "row_kind",
    "instance_id",
    "n_qubits",
    "B",
    "repetitions",
    "B_max_instance",
    "B_den_realistic",
    "B_over_B_den",
    "grid_reaches_10x_B_den",
    "sample_status",
    "estimator_model",
    "mu_ideal_l2",
    "D_2_realistic",
    "N_2_realistic",
    "vd_realistic_population_mean",
    "vd_realistic_population_bias",
    "mean_estimate",
    "bias_empirical",
    "variance_empirical",
    "mse_empirical",
    "var_times_B",
    "clip_activation_rate",
    "mean_N_hat",
    "mean_D_hat",
    "mean_D_clipped",
    "denominator_clip_value",
    "resource_R_paired_sample",
    "resource_R_two_qubit_gate_proxy",
    "kappa_paired_sample",
    "kappa_two_qubit_gate_proxy",
    "vd_optimal_population_mean_5a",
    "vd_optimal_population_bias_5a",
    "vd_interference_overhead_abs_bias_delta",
    "vd_interference_overhead_abs_bias_ratio",
    "sv_population_mean_5a",
    "sv_population_bias_5a",
    "vd_bias_floor_mse",
    "sv_bias_floor_mse",
    "vd_bias_floor_beats_sv",
    "sv_matched_paired_B",
    "sv_matched_paired_mse",
    "vd_mse_beats_sv_paired",
    "sv_matched_twoqubit_B",
    "sv_matched_twoqubit_mse",
    "vd_mse_beats_sv_twoqubit",
    "noiseless_D_hat",
    "noiseless_N_hat",
    "noiseless_mu_hat",
    "noiseless_mu_abs_error",
    "mixer_trotter_steps",
    "runtime_seconds",
]


@dataclass(frozen=True)
class RealisticVDConfig:
    instance_ids: tuple[str, ...] = INSTANCE_IDS
    repetitions: int = REPETITIONS
    b_min: int = B_MIN
    base_seed: int = BASE_SEED


@dataclass(frozen=True)
class RealisticVDContext:
    model: object
    mu_ideal: float
    outcome_probabilities: np.ndarray
    numerator_values: np.ndarray
    denominator_values: np.ndarray
    d_realistic: float
    n_realistic: float
    vd_population_mean: float
    b_den: float
    noiseless: dict[str, float]
    highpower_context: highpower.InstanceContext
    sv_population_mean: float
    sv_population_bias: float
    vd_optimal_population_mean: float
    vd_optimal_population_bias: float


def main() -> int:
    t0 = time.time()
    rows, report = run_realistic_vd_n6(RealisticVDConfig(), started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_realistic_vd_n6(
    config: RealisticVDConfig,
    started_at: float | None = None,
) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    rows: list[dict] = []
    for instance_id in config.instance_ids:
        rows.extend(run_instance(_select_model(instance_id), config))
    runtime_seconds = round(time.time() - t0, 3)
    for row in rows:
        row["runtime_seconds"] = runtime_seconds
    return rows, render_report(rows, config)


def run_instance(model, config: RealisticVDConfig) -> list[dict]:
    context = build_context(model)
    b_grid = b_grid_for_bden(context.b_den, config.b_min)
    b_max = max(b_grid)
    rows = []
    for b in b_grid:
        rows.append(run_cell(context, config, int(b), b_max))
    return rows


def build_context(model) -> RealisticVDContext:
    inst = model.inst
    if inst.n != 6:
        raise ValueError(f"realistic VD follow-up is scoped to n=6, got {inst.name}")
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        inst,
    )
    numerator_values, denominator_values = vd_value_vectors(inst)

    noiseless_prob = exact_vd_outcome_distribution(model, noisy=False, include_readout=False)
    d0 = float(noiseless_prob @ denominator_values)
    n0 = float(noiseless_prob @ numerator_values)
    mu0 = n0 / d0
    noiseless = {
        "D_hat": d0,
        "N_hat": n0,
        "mu_hat": mu0,
        "mu_abs_error": abs(mu0 - mu_ideal),
    }
    if abs(d0 - 1.0) > NOISELESS_D_TOL or noiseless["mu_abs_error"] > NOISELESS_MU_TOL:
        raise RuntimeError(
            f"realistic VD noiseless cross-check failed for {inst.name}: "
            f"D={d0:.12g}, mu_abs_error={noiseless['mu_abs_error']:.12g}"
        )

    outcome_prob = exact_vd_outcome_distribution(model, noisy=True, include_readout=True)
    d_realistic = float(outcome_prob @ denominator_values)
    n_realistic = float(outcome_prob @ numerator_values)
    vd_population_mean = n_realistic / d_realistic
    b_den = denominator_sample_threshold(d_realistic)

    hp_context = highpower.build_instance_context(model)
    sv_num = float(np.sum(
        hp_context.p_true[hp_context.sector_mask]
        * hp_context.observable_values[hp_context.sector_mask]
    ))
    sv_population = sv_num / hp_context.sv_acceptance_reference
    return RealisticVDContext(
        model=model,
        mu_ideal=mu_ideal,
        outcome_probabilities=outcome_prob,
        numerator_values=numerator_values,
        denominator_values=denominator_values,
        d_realistic=d_realistic,
        n_realistic=n_realistic,
        vd_population_mean=vd_population_mean,
        b_den=b_den,
        noiseless=noiseless,
        highpower_context=hp_context,
        sv_population_mean=sv_population,
        sv_population_bias=sv_population - mu_ideal,
        vd_optimal_population_mean=hp_context.vd_population_mean,
        vd_optimal_population_bias=hp_context.vd_population_mean - mu_ideal,
    )


def exact_vd_outcome_distribution(model, noisy: bool, include_readout: bool) -> np.ndarray:
    circuit = level2_vd.build_vd_circuits(model)["denominator"].remove_final_measurements(inplace=False)
    circuit.save_probabilities()
    simulator = AerSimulator(
        method="density_matrix" if noisy else "statevector",
        noise_model=build_noise_model() if noisy else None,
        seed_simulator=int(load_config()["noise_model"]["seed_simulator"]),
    )
    result = simulator.run(circuit).result()
    probabilities = np.asarray(result.data(0)["probabilities"], dtype=np.float64)
    probabilities = probability_vector(probabilities)
    if include_readout:
        matrix = np.asarray(load_config()["noise_model"]["readout_error_matrix"], dtype=np.float64)
        probabilities = apply_tensor_readout(probabilities, matrix, circuit.num_qubits)
    return probability_vector(probabilities)


def vd_value_vectors(inst) -> tuple[np.ndarray, np.ndarray]:
    n = int(inst.n)
    total_qubits = 2 * n + 1
    size = 2**total_qubits
    indices = np.arange(size, dtype=np.int64)
    ancilla_bit = (indices >> (2 * n)) & 1
    z_ancilla = 1.0 - 2.0 * ancilla_bit.astype(np.float64)
    a_index = np.zeros(size, dtype=np.int64)
    for qubit in range(n):
        a_index = (a_index << 1) | ((indices >> qubit) & 1)
    observable = highpower.normalized_observable_values(inst)
    numerator = z_ancilla * observable[a_index]
    return numerator.astype(np.float64), z_ancilla.astype(np.float64)


def run_cell(
    context: RealisticVDContext,
    config: RealisticVDConfig,
    b: int,
    b_max: int,
) -> dict:
    rng = make_rng(stable_seed(config.base_seed, context.model.inst.name, "vd_realistic", int(b)))
    estimates, n_hat, d_hat, d_clipped = sample_vd_from_distribution(
        context.outcome_probabilities,
        context.numerator_values,
        context.denominator_values,
        context.d_realistic,
        int(b),
        int(config.repetitions),
        rng,
    )
    sv_paired = sample_sv_matched(context, config, int(round(kappas(context)[0] * b)), "paired", int(b))
    sv_twoq = sample_sv_matched(context, config, int(round(kappas(context)[1] * b)), "twoqubit", int(b))
    errors = estimates - context.mu_ideal
    variance = float(np.var(estimates, ddof=1)) if estimates.size > 1 else 0.0
    k_paired, k_twoq = kappas(context)
    vd_bias_floor_mse = float(context.vd_population_mean - context.mu_ideal) ** 2
    sv_bias_floor_mse = float(context.sv_population_bias) ** 2
    return {
        "row_kind": "aggregate",
        "instance_id": context.model.inst.name,
        "n_qubits": int(context.model.inst.n),
        "B": int(b),
        "repetitions": int(config.repetitions),
        "B_max_instance": int(b_max),
        "B_den_realistic": float(context.b_den),
        "B_over_B_den": float(b / context.b_den),
        "grid_reaches_10x_B_den": bool(b_max >= 10.0 * context.b_den),
        "sample_status": "sampled",
        "estimator_model": ESTIMATOR_MODEL,
        "mu_ideal_l2": float(context.mu_ideal),
        "D_2_realistic": float(context.d_realistic),
        "N_2_realistic": float(context.n_realistic),
        "vd_realistic_population_mean": float(context.vd_population_mean),
        "vd_realistic_population_bias": float(context.vd_population_mean - context.mu_ideal),
        "mean_estimate": float(np.mean(estimates)),
        "bias_empirical": float(np.mean(estimates) - context.mu_ideal),
        "variance_empirical": variance,
        "mse_empirical": float(np.mean(errors**2)),
        "var_times_B": float(variance * b),
        "clip_activation_rate": float(np.mean(d_hat < DENOMINATOR_CLIP_FRACTION * context.d_realistic)),
        "mean_N_hat": float(np.mean(n_hat)),
        "mean_D_hat": float(np.mean(d_hat)),
        "mean_D_clipped": float(np.mean(d_clipped)),
        "denominator_clip_value": float(DENOMINATOR_CLIP_FRACTION * context.d_realistic),
        "resource_R_paired_sample": float(k_paired * b),
        "resource_R_two_qubit_gate_proxy": float(k_twoq * b),
        "kappa_paired_sample": float(k_paired),
        "kappa_two_qubit_gate_proxy": float(k_twoq),
        "vd_optimal_population_mean_5a": float(context.vd_optimal_population_mean),
        "vd_optimal_population_bias_5a": float(context.vd_optimal_population_bias),
        "vd_interference_overhead_abs_bias_delta": float(
            abs(context.vd_population_mean - context.mu_ideal)
            - abs(context.vd_optimal_population_bias)
        ),
        "vd_interference_overhead_abs_bias_ratio": safe_ratio(
            abs(context.vd_population_mean - context.mu_ideal),
            abs(context.vd_optimal_population_bias),
        ),
        "sv_population_mean_5a": float(context.sv_population_mean),
        "sv_population_bias_5a": float(context.sv_population_bias),
        "vd_bias_floor_mse": vd_bias_floor_mse,
        "sv_bias_floor_mse": sv_bias_floor_mse,
        "vd_bias_floor_beats_sv": bool(vd_bias_floor_mse < sv_bias_floor_mse),
        "sv_matched_paired_B": int(round(k_paired * b)),
        "sv_matched_paired_mse": float(np.mean((sv_paired - context.mu_ideal) ** 2)),
        "vd_mse_beats_sv_paired": bool(float(np.mean(errors**2)) < float(np.mean((sv_paired - context.mu_ideal) ** 2))),
        "sv_matched_twoqubit_B": int(round(k_twoq * b)),
        "sv_matched_twoqubit_mse": float(np.mean((sv_twoq - context.mu_ideal) ** 2)),
        "vd_mse_beats_sv_twoqubit": bool(float(np.mean(errors**2)) < float(np.mean((sv_twoq - context.mu_ideal) ** 2))),
        "noiseless_D_hat": float(context.noiseless["D_hat"]),
        "noiseless_N_hat": float(context.noiseless["N_hat"]),
        "noiseless_mu_hat": float(context.noiseless["mu_hat"]),
        "noiseless_mu_abs_error": float(context.noiseless["mu_abs_error"]),
        "mixer_trotter_steps": MIXER_TROTTER_STEPS,
        "runtime_seconds": 0.0,
    }


def sample_vd_from_distribution(
    probabilities: np.ndarray,
    numerator_values: np.ndarray,
    denominator_values: np.ndarray,
    d_realistic: float,
    b: int,
    repetitions: int,
    rng,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    counts_n = rng.multinomial(int(b), probabilities, size=int(repetitions))
    counts_d = rng.multinomial(int(b), probabilities, size=int(repetitions))
    n_hat = counts_n @ numerator_values / float(b)
    d_hat = counts_d @ denominator_values / float(b)
    d_clipped = np.maximum(d_hat, DENOMINATOR_CLIP_FRACTION * float(d_realistic))
    return n_hat / d_clipped, n_hat, d_hat, d_clipped


def sample_sv_matched(
    context: RealisticVDContext,
    config: RealisticVDConfig,
    b: int,
    resource_label: str,
    vd_b: int,
) -> np.ndarray:
    b = max(2, int(b))
    hp = context.highpower_context
    rng = make_rng(stable_seed(config.base_seed, context.model.inst.name, "sv_match", resource_label, int(vd_b), int(b)))
    counts = rng.multinomial(b, hp.p_observed, size=int(config.repetitions))
    estimates = []
    for sample_counts in counts:
        observed = sample_counts.astype(np.float64) / float(b)
        mitigated, _neg = sampling.mitigate_distribution(observed, hp.assignment)
        accept = float(np.sum(mitigated[hp.sector_mask]))
        numerator = float(np.sum(mitigated[hp.sector_mask] * hp.observable_values[hp.sector_mask]))
        denom = max(accept, sampling.SV_CLIP_FRACTION * hp.sv_acceptance_reference)
        estimates.append(numerator / denom)
    return np.asarray(estimates, dtype=np.float64)


def apply_tensor_readout(probabilities: np.ndarray, readout_matrix: np.ndarray, n_qubits: int) -> np.ndarray:
    arr = np.asarray(probabilities, dtype=np.float64).copy()
    size = arr.size
    for qubit in range(int(n_qubits)):
        mask = 1 << qubit
        updated = np.zeros_like(arr)
        for base in range(size):
            if base & mask:
                continue
            one = base | mask
            p0 = arr[base]
            p1 = arr[one]
            updated[base] = p0 * readout_matrix[0, 0] + p1 * readout_matrix[1, 0]
            updated[one] = p0 * readout_matrix[0, 1] + p1 * readout_matrix[1, 1]
        arr = updated
    return probability_vector(arr)


def b_grid_for_bden(b_den: float, b_min: int) -> tuple[int, ...]:
    if not math.isfinite(float(b_den)) or float(b_den) <= 0.0:
        raise ValueError(f"invalid B_den={b_den}")
    values = [max(int(b_min), int(math.ceil(float(b_den) * factor))) for factor in B_GRID_FACTORS]
    values.append(int(math.ceil(10.0 * float(b_den))))
    return tuple(sorted(set(values)))


def denominator_sample_threshold(d_value: float, eps: float = 1.0e-3) -> float:
    d_abs = abs(float(d_value))
    if d_abs <= 0.0:
        return float("inf")
    sigma_d2 = max(1.0 - d_abs**2, 0.0)
    return float((8.0 * sigma_d2 / d_abs**2 + 8.0 / (3.0 * d_abs)) * math.log(1.0 / eps))


def probability_vector(values: np.ndarray) -> np.ndarray:
    arr = np.clip(np.asarray(values, dtype=np.float64), 0.0, None)
    total = float(np.sum(arr))
    if total <= 0.0:
        raise ValueError("non-positive probability vector")
    return arr / total


def kappas(context: RealisticVDContext) -> tuple[float, float]:
    defs = resource_definitions(context.model.inst.n)
    return float(defs["paired_sample"]["vd"]), float(defs["two_qubit_gate_proxy"]["vd"])


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return float("inf")
    return float(numerator / denominator)


def render_report(rows: list[dict], config: RealisticVDConfig) -> str:
    large_rows = largest_b_rows(rows)
    bias_wins = sum(1 for row in large_rows if row["vd_bias_floor_beats_sv"])
    paired_wins = sum(1 for row in large_rows if row["vd_mse_beats_sv_paired"])
    twoq_wins = sum(1 for row in large_rows if row["vd_mse_beats_sv_twoqubit"])
    lines = [
        "# Level 2 Realistic VD n=6",
        "",
        "Status: EN FORMA; device-circuit VD con interferencia, n=6. Additive Phase B follow-up; not a freeze and not an adjudication.",
        "",
        "## Scope",
        "",
        f"- Instances: `{', '.join(config.instance_ids)}`.",
        f"- Repetitions per cell: `{config.repetitions}`.",
        "- Circuit: full Step 3 VD M=2 Hadamard/SWAP circuit with decomposed c-SWAP, Aer gate noise, and configured readout.",
        "- Sampling: exact density-matrix outcome distribution of the 13-qubit circuit, followed by multinomial finite-shot sampling.",
        "- Comparison baseline: Step 5a exact-rho optimistic VD and SV conventions; SV is sampled at matched paired-sample and two-qubit-proxy resources.",
        "",
        "## Per-Instance Large-B Summary",
        "",
        "| instance | B_max | D realistic | B_den | abs bias VD realistic | abs bias VD opt 5a | abs bias SV 5a | VD floor beats SV | VD MSE beats SV paired | VD MSE beats SV twoq |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in large_rows:
        lines.append(
            f"| {row['instance_id']} | {int(row['B'])} | {float(row['D_2_realistic']):.6g} "
            f"| {float(row['B_den_realistic']):.6g} | {abs(float(row['vd_realistic_population_bias'])):.6g} "
            f"| {abs(float(row['vd_optimal_population_bias_5a'])):.6g} "
            f"| {abs(float(row['sv_population_bias_5a'])):.6g} "
            f"| {_bool_word(bool(row['vd_bias_floor_beats_sv']))} "
            f"| {_bool_word(bool(row['vd_mse_beats_sv_paired']))} "
            f"| {_bool_word(bool(row['vd_mse_beats_sv_twoqubit']))} |"
        )
    lines.extend([
        "",
        "## Aggregate Readout",
        "",
        f"- Bias-floor wins for VD realistic vs SV: `{bias_wins}/5`.",
        f"- Large-B MSE wins for VD realistic vs SV at paired-sample resource: `{paired_wins}/5`.",
        f"- Large-B MSE wins for VD realistic vs SV at two-qubit-gate-proxy resource: `{twoq_wins}/5`.",
        "",
        "## Descriptive Conclusion",
        "",
        (
            "This follow-up measures whether the n=6 optimistic VD operating window survives "
            "the realistic c-SWAP/interference overhead. The table reports the result as "
            "measured: no universal winner is assumed. Bias floors, overhead relative to the "
            "Step 5a optimistic VD model, and resource-matched SV comparisons are all exposed "
            "per instance for the downstream Level 2 analyses."
        ),
        "",
        f"Runtime for this harness run: `{max(float(row['runtime_seconds']) for row in rows):.3f}` seconds.",
    ])
    return "\n".join(lines) + "\n"


def largest_b_rows(rows: list[dict]) -> list[dict]:
    out = []
    for instance_id in sorted({row["instance_id"] for row in rows}):
        inst_rows = [row for row in rows if row["instance_id"] == instance_id]
        out.append(max(inst_rows, key=lambda row: int(row["B"])))
    return out


def _select_model(instance_id: str):
    for model in frozen_models():
        if model.inst.name == instance_id:
            return model
    raise ValueError(f"instance not found: {instance_id}")


def stable_seed(base_seed: int, *parts: object) -> int:
    payload = "|".join([str(int(base_seed)), *(str(part) for part in parts)]).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1)


def _bool_word(value: bool) -> str:
    return "yes" if value else "no"


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
