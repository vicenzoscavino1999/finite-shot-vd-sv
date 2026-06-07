"""Level 2 Step 5a: multi-method high-power sampling harness.

This additive Phase B harness generates the base long-format data consumed by
later Level 2 analyses. It intentionally does not adjudicate E5/E7/E8/E12.

The direct-Z methods (unmitigated and SV) are sampled with noisy Aer trajectories
at T=64. VD M=2 is wired through the Step 3 Hadamard/SWAP circuits and receives
per-instance noiseless cross-checks plus noisy-denominator/B_den sizing. If the
requested VD trajectory budget is infeasible, rows are emitted with an explicit
``budget_exceeded_not_sampled`` status instead of silently faking data.
"""

from __future__ import annotations

import csv
import hashlib
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from experiments.e7_resource_observable_sensitivity import resource_definitions  # noqa: E402
from level2 import sampling, vd  # noqa: E402
from level2.circuits import MIXER_TROTTER_STEPS, observable_expectation, simulate_noiseless_statevector  # noqa: E402
from level2.noise_model import build_aer_simulator, load_config  # noqa: E402
from vd_sv import qaoa  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_highpower_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_highpower_report.md"

INSTANCE_IDS = tuple(f"g6_k2_c{i:03d}" for i in range(5)) + tuple(
    f"g8_k3_c{i:03d}" for i in range(5)
)
METHODS = ("unmitigated", "sv_mitigated", "vd_m2_hadamard_swap")
REPETITIONS = 64
BASE_SEED = 25005
B_MAX_CAP = 8192
B_MIN = 64
GRID_FACTORS = (0.25, 0.5, 1.0, 2.0, 10.0)
VD_NOISELESS_CHECK_SHOTS = 4096
VD_D_REFERENCE_SHOTS_N6 = 512
VD_D_REFERENCE_SHOTS_N8 = 128
VD_TRAJECTORY_SHOT_CAP_PER_CIRCUIT = 4096
SV_ACCEPTANCE_REFERENCE_SHOTS = 4096
DIRECT_METHOD_MEMORY = True
NOISELESS_D_TOL = vd.NOISELESS_D_TOL
NOISELESS_MU_TOL = vd.NOISELESS_MU_TOL

FIELDS = [
    "row_kind",
    "instance_id",
    "n_qubits",
    "method",
    "sample_status",
    "B",
    "repetitions",
    "B_max_instance",
    "B_den_impl_estimate",
    "B_over_B_den",
    "grid_crosses_B_den",
    "grid_reaches_10x_B_den",
    "mu_ideal_l2",
    "mean_estimate",
    "bias_empirical",
    "variance_empirical",
    "mse_empirical",
    "var_times_B",
    "mean_acceptance_fraction",
    "mean_negative_mass",
    "mean_N_hat",
    "mean_D_hat",
    "mean_D_clipped",
    "noisy_D_reference",
    "denominator_clip_value",
    "noiseless_D_hat",
    "noiseless_N_hat",
    "noiseless_mu_hat",
    "noiseless_mu_abs_error",
    "resource_R_paired_sample",
    "resource_R_two_qubit_gate_proxy",
    "kappa_paired_sample",
    "kappa_two_qubit_gate_proxy",
    "vd_estimated_shots_per_circuit",
    "vd_trajectory_shot_cap_per_circuit",
    "mixer_trotter_steps",
    "runtime_seconds",
]


@dataclass(frozen=True)
class HighPowerConfig:
    instance_ids: tuple[str, ...] = INSTANCE_IDS
    repetitions: int = REPETITIONS
    b_max_cap: int = B_MAX_CAP
    b_min: int = B_MIN
    base_seed: int = BASE_SEED
    vd_trajectory_shot_cap_per_circuit: int = VD_TRAJECTORY_SHOT_CAP_PER_CIRCUIT
    sv_acceptance_reference_shots: int = SV_ACCEPTANCE_REFERENCE_SHOTS
    vd_noiseless_check_shots: int = VD_NOISELESS_CHECK_SHOTS
    vd_d_reference_shots_n6: int = VD_D_REFERENCE_SHOTS_N6
    vd_d_reference_shots_n8: int = VD_D_REFERENCE_SHOTS_N8


def main() -> int:
    t0 = time.time()
    rows, report = run_highpower(HighPowerConfig(), started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_highpower(
    config: HighPowerConfig,
    started_at: float | None = None,
) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    models = [_select_model(instance_id) for instance_id in config.instance_ids]
    rows: list[dict] = []
    for model in models:
        rows.extend(run_instance(model, config))
    runtime_seconds = round(time.time() - t0, 3)
    for row in rows:
        row["runtime_seconds"] = runtime_seconds
    report = render_report(rows, config)
    return rows, report


def run_instance(model, config: HighPowerConfig) -> list[dict]:
    inst = model.inst
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        inst,
    )
    vd_meta = vd_metadata_for_instance(model, config, mu_ideal)
    b_grid = b_grid_for_bden(vd_meta["B_den_impl_estimate"], config.b_min, config.b_max_cap)
    b_max = max(b_grid)
    direct_rows = run_direct_methods(model, config, b_grid, mu_ideal, vd_meta)
    vd_rows = run_or_mark_vd(model, config, b_grid, mu_ideal, vd_meta, b_max)
    return direct_rows + vd_rows


def vd_metadata_for_instance(model, config: HighPowerConfig, mu_ideal: float) -> dict[str, float | str]:
    inst = model.inst
    circuits = vd.build_vd_circuits(model)
    noiseless = vd.noiseless_vd_crosscheck(
        circuits,
        inst,
        shots=config.vd_noiseless_check_shots,
        seed=stable_seed(config.base_seed, inst.name, "vd_noiseless_crosscheck"),
        mu_ideal=mu_ideal,
    )
    if (
        abs(noiseless["D_hat"] - 1.0) > NOISELESS_D_TOL
        or noiseless["mu_abs_error"] > NOISELESS_MU_TOL
    ):
        raise RuntimeError(
            f"VD noiseless cross-check failed for {inst.name}: "
            f"D_hat={noiseless['D_hat']:.6g}, mu_abs_error={noiseless['mu_abs_error']:.6g}"
        )
    ref_shots = (
        config.vd_d_reference_shots_n6 if inst.n <= 6 else config.vd_d_reference_shots_n8
    )
    noisy_d = vd.noisy_denominator_reference(
        circuits,
        inst,
        shots=ref_shots,
        seed=stable_seed(config.base_seed, inst.name, "vd_noisy_denominator_reference"),
    )
    b_den = vd.denominator_sample_threshold(noisy_d)
    clip_value = max(vd.DENOMINATOR_CLIP_FRACTION * noisy_d, vd.DENOMINATOR_CLIP_MIN)
    metadata = vd.vd_circuit_metadata(circuits, inst.n)
    return {
        "noiseless_D_hat": noiseless["D_hat"],
        "noiseless_N_hat": noiseless["N_hat"],
        "noiseless_mu_hat": noiseless["mu_hat"],
        "noiseless_mu_abs_error": noiseless["mu_abs_error"],
        "noisy_D_reference": float(noisy_d),
        "denominator_clip_value": float(clip_value),
        "B_den_impl_estimate": float(b_den),
        **metadata,
    }


def b_grid_for_bden(b_den: float, b_min: int, b_max_cap: int) -> tuple[int, ...]:
    if not math.isfinite(float(b_den)) or float(b_den) <= 0.0:
        base = [b_min, 2 * b_min, 4 * b_min, 8 * b_min, min(b_max_cap, 16 * b_min)]
    else:
        base = [int(round(float(b_den) * factor)) for factor in GRID_FACTORS]
        base.extend([b_min, b_max_cap])
    cleaned = []
    for value in base:
        value = max(int(b_min), min(int(b_max_cap), int(value)))
        value = int(max(1, round(value / 64.0)) * 64)
        value = max(int(b_min), min(int(b_max_cap), value))
        cleaned.append(value)
    unique = sorted(set(cleaned))
    while len(unique) < 5:
        candidate = min(int(b_max_cap), unique[-1] * 2)
        if candidate == unique[-1]:
            break
        unique.append(candidate)
    return tuple(unique)


def run_direct_methods(model, config: HighPowerConfig, b_grid: tuple[int, ...], mu_ideal: float, vd_meta: dict) -> list[dict]:
    inst = model.inst
    b_max = max(b_grid)
    total_shots = int(config.repetitions * b_max)
    circuit = sampling.measured_noisy_qaoa_circuit(model)
    memory = run_memory(
        circuit,
        shots=total_shots,
        seed=stable_seed(config.base_seed, inst.name, "direct_methods", b_max, config.repetitions),
    )
    observable_values = sampling._observable_values(inst)
    readout_matrices = configured_readout_matrices(inst.n)
    assignment = sampling.assignment_matrix(readout_matrices)
    acceptance_reference = estimate_acceptance_from_memory(
        memory,
        inst,
        assignment,
        shots=min(config.sv_acceptance_reference_shots, len(memory)),
    )
    samples = {"unmitigated": {b: [] for b in b_grid}, "sv_mitigated": {b: [] for b in b_grid}}
    for rep in range(config.repetitions):
        rep_memory = memory[rep * b_max : (rep + 1) * b_max]
        for b in b_grid:
            prefix = rep_memory[:b]
            observed = observed_distribution_from_memory(prefix, inst.n)
            unmit = float(np.sum(observed * observable_values))
            mitigated, negative_mass = sampling.mitigate_distribution(observed, assignment)
            sector = sampling.hamming_weights(inst.n) == inst.weight
            mitigated_accept = float(np.sum(mitigated[sector]))
            mitigated_num = float(np.sum(mitigated[sector] * observable_values[sector]))
            sv_denom = max(mitigated_accept, sampling.SV_CLIP_FRACTION * acceptance_reference)
            sv_estimate = mitigated_num / sv_denom
            samples["unmitigated"][b].append({
                "estimate": unmit,
                "acceptance": 1.0,
                "negative_mass": 0.0,
            })
            samples["sv_mitigated"][b].append({
                "estimate": sv_estimate,
                "acceptance": mitigated_accept,
                "negative_mass": negative_mass,
            })
    rows: list[dict] = []
    for method in ("unmitigated", "sv_mitigated"):
        rows.extend(aggregate_direct_rows(method, samples[method], config, model, mu_ideal, vd_meta, b_max))
    return rows


def run_or_mark_vd(model, config: HighPowerConfig, b_grid: tuple[int, ...], mu_ideal: float, vd_meta: dict, b_max: int) -> list[dict]:
    estimated_shots = int(config.repetitions * b_max)
    if estimated_shots > config.vd_trajectory_shot_cap_per_circuit:
        return [
            base_row(
                model,
                method="vd_m2_hadamard_swap",
                b=b,
                repetitions=config.repetitions,
                mu_ideal=mu_ideal,
                vd_meta=vd_meta,
                sample_status="budget_exceeded_not_sampled",
                vd_estimated_shots_per_circuit=estimated_shots,
                config=config,
                b_max=b_max,
            )
            for b in b_grid
        ]
    circuits = vd.build_vd_circuits(model)
    den_memory = run_memory(
        circuits["denominator"],
        shots=estimated_shots,
        seed=stable_seed(config.base_seed, model.inst.name, "vd_den", b_max, config.repetitions),
    )
    num_memory = run_memory(
        circuits["numerator"],
        shots=estimated_shots,
        seed=stable_seed(config.base_seed, model.inst.name, "vd_num", b_max, config.repetitions),
    )
    samples: dict[int, list[dict]] = {b: [] for b in b_grid}
    for rep in range(config.repetitions):
        den_rep = den_memory[rep * b_max : (rep + 1) * b_max]
        num_rep = num_memory[rep * b_max : (rep + 1) * b_max]
        for b in b_grid:
            d_hat = estimate_denominator_from_memory(den_rep[:b], model.inst.n)
            n_hat = estimate_numerator_from_memory(num_rep[:b], model.inst)
            d_clipped = max(d_hat, float(vd_meta["denominator_clip_value"]))
            estimate = n_hat / d_clipped
            samples[b].append({
                "estimate": estimate,
                "N_hat": n_hat,
                "D_hat": d_hat,
                "D_clipped": d_clipped,
            })
    return aggregate_vd_rows(samples, config, model, mu_ideal, vd_meta, estimated_shots, b_max)


def aggregate_direct_rows(method: str, samples_by_b: dict[int, list[dict]], config: HighPowerConfig, model, mu_ideal: float, vd_meta: dict, b_max: int) -> list[dict]:
    rows = []
    for b in sorted(samples_by_b):
        samples_for_b = samples_by_b[b]
        estimates = np.asarray([sample["estimate"] for sample in samples_for_b], dtype=np.float64)
        errors = estimates - mu_ideal
        row = base_row(
            model,
            method=method,
            b=b,
            repetitions=config.repetitions,
            mu_ideal=mu_ideal,
            vd_meta=vd_meta,
            sample_status="sampled",
            vd_estimated_shots_per_circuit=0,
            config=config,
            b_max=b_max,
        )
        row.update({
            "mean_estimate": float(np.mean(estimates)),
            "bias_empirical": float(np.mean(estimates) - mu_ideal),
            "variance_empirical": float(np.var(estimates, ddof=1)),
            "mse_empirical": float(np.mean(errors**2)),
            "var_times_B": float(np.var(estimates, ddof=1) * b),
            "mean_acceptance_fraction": float(np.mean([sample["acceptance"] for sample in samples_for_b])),
            "mean_negative_mass": float(np.mean([sample["negative_mass"] for sample in samples_for_b])),
        })
        rows.append(row)
    return rows


def aggregate_vd_rows(samples_by_b: dict[int, list[dict]], config: HighPowerConfig, model, mu_ideal: float, vd_meta: dict, estimated_shots: int, b_max: int) -> list[dict]:
    rows = []
    for b in sorted(samples_by_b):
        samples_for_b = samples_by_b[b]
        estimates = np.asarray([sample["estimate"] for sample in samples_for_b], dtype=np.float64)
        errors = estimates - mu_ideal
        row = base_row(
            model,
            method="vd_m2_hadamard_swap",
            b=b,
            repetitions=config.repetitions,
            mu_ideal=mu_ideal,
            vd_meta=vd_meta,
            sample_status="sampled",
            vd_estimated_shots_per_circuit=estimated_shots,
            config=config,
            b_max=b_max,
        )
        row.update({
            "mean_estimate": float(np.mean(estimates)),
            "bias_empirical": float(np.mean(estimates) - mu_ideal),
            "variance_empirical": float(np.var(estimates, ddof=1)),
            "mse_empirical": float(np.mean(errors**2)),
            "var_times_B": float(np.var(estimates, ddof=1) * b),
            "mean_N_hat": float(np.mean([sample["N_hat"] for sample in samples_for_b])),
            "mean_D_hat": float(np.mean([sample["D_hat"] for sample in samples_for_b])),
            "mean_D_clipped": float(np.mean([sample["D_clipped"] for sample in samples_for_b])),
        })
        rows.append(row)
    return rows


def base_row(
    model,
    method: str,
    b: int,
    repetitions: int,
    mu_ideal: float,
    vd_meta: dict,
    sample_status: str,
    vd_estimated_shots_per_circuit: int,
    config: HighPowerConfig,
    b_max: int,
) -> dict:
    inst = model.inst
    kappa = resource_definitions(inst.n)
    if method == "vd_m2_hadamard_swap":
        k_paired = kappa["paired_sample"]["vd"]
        k_twq = kappa["two_qubit_gate_proxy"]["vd"]
    elif method == "sv_mitigated":
        k_paired = kappa["paired_sample"]["sv"]
        k_twq = kappa["two_qubit_gate_proxy"]["sv"]
    else:
        k_paired = kappa["paired_sample"]["unmitigated"]
        k_twq = kappa["two_qubit_gate_proxy"]["unmitigated"]
    b_den = float(vd_meta["B_den_impl_estimate"])
    return {
        "row_kind": "aggregate",
        "instance_id": inst.name,
        "n_qubits": int(inst.n),
        "method": method,
        "sample_status": sample_status,
        "B": int(b),
        "repetitions": int(repetitions),
        "B_max_instance": int(b_max),
        "B_den_impl_estimate": b_den,
        "B_over_B_den": float(b / b_den) if math.isfinite(b_den) and b_den > 0 else 0.0,
        "grid_crosses_B_den": bool(math.isfinite(b_den) and b_max >= b_den),
        "grid_reaches_10x_B_den": bool(math.isfinite(b_den) and b_max >= 10.0 * b_den),
        "mu_ideal_l2": float(mu_ideal),
        "mean_estimate": float("nan"),
        "bias_empirical": float("nan"),
        "variance_empirical": float("nan"),
        "mse_empirical": float("nan"),
        "var_times_B": float("nan"),
        "mean_acceptance_fraction": float("nan"),
        "mean_negative_mass": float("nan"),
        "mean_N_hat": float("nan"),
        "mean_D_hat": float("nan"),
        "mean_D_clipped": float("nan"),
        "noisy_D_reference": float(vd_meta["noisy_D_reference"]),
        "denominator_clip_value": float(vd_meta["denominator_clip_value"]),
        "noiseless_D_hat": float(vd_meta["noiseless_D_hat"]),
        "noiseless_N_hat": float(vd_meta["noiseless_N_hat"]),
        "noiseless_mu_hat": float(vd_meta["noiseless_mu_hat"]),
        "noiseless_mu_abs_error": float(vd_meta["noiseless_mu_abs_error"]),
        "resource_R_paired_sample": float(k_paired * b),
        "resource_R_two_qubit_gate_proxy": float(k_twq * b),
        "kappa_paired_sample": float(k_paired),
        "kappa_two_qubit_gate_proxy": float(k_twq),
        "vd_estimated_shots_per_circuit": int(vd_estimated_shots_per_circuit),
        "vd_trajectory_shot_cap_per_circuit": int(config.vd_trajectory_shot_cap_per_circuit),
        "mixer_trotter_steps": MIXER_TROTTER_STEPS,
        "runtime_seconds": 0.0,
    }


def run_memory(circuit, shots: int, seed: int) -> list[str]:
    simulator = build_aer_simulator(noisy=True)
    simulator.set_options(
        seed_simulator=int(seed),
        max_parallel_threads=1,
        max_parallel_experiments=1,
        max_parallel_shots=1,
    )
    result = simulator.run(
        circuit,
        shots=int(shots),
        seed_simulator=int(seed),
        memory=DIRECT_METHOD_MEMORY,
    ).result()
    return [str(item).replace(" ", "") for item in result.get_memory()]


def observed_distribution_from_memory(memory: list[str], n: int) -> np.ndarray:
    total = float(len(memory))
    dist = np.zeros(2**n, dtype=np.float64)
    for key in memory:
        dist[sampling.qiskit_key_to_level1_index(key, n)] += 1.0 / total
    return dist


def estimate_acceptance_from_memory(memory: list[str], inst: qaoa.QAOAInstance, assignment: np.ndarray, shots: int) -> float:
    observed = observed_distribution_from_memory(memory[:shots], inst.n)
    mitigated, _negative_mass = sampling.mitigate_distribution(observed, assignment)
    return float(np.sum(mitigated[sampling.hamming_weights(inst.n) == inst.weight]))


def estimate_denominator_from_memory(memory: list[str], n: int) -> float:
    counts = {}
    for key in memory:
        counts[key] = counts.get(key, 0) + 1
    return vd.estimate_denominator(counts, n)


def estimate_numerator_from_memory(memory: list[str], inst: qaoa.QAOAInstance) -> float:
    counts = {}
    for key in memory:
        counts[key] = counts.get(key, 0) + 1
    return vd.estimate_numerator(counts, inst)


def configured_readout_matrices(n: int) -> np.ndarray:
    matrix = np.asarray(load_config()["noise_model"]["readout_error_matrix"], dtype=np.float64)
    return np.repeat(matrix[None, :, :], int(n), axis=0)


def render_report(rows: list[dict], config: HighPowerConfig) -> str:
    sampled = [row for row in rows if row["sample_status"] == "sampled"]
    budget = [row for row in rows if row["sample_status"] == "budget_exceeded_not_sampled"]
    instances = sorted({row["instance_id"] for row in rows})
    vd_budget_instances = sorted({row["instance_id"] for row in budget if row["method"] == "vd_m2_hadamard_swap"})
    non_crossing = sorted({
        row["instance_id"]
        for row in rows
        if row["method"] == "vd_m2_hadamard_swap" and not bool(row["grid_reaches_10x_B_den"])
    })
    lines = [
        "# Level 2 Step 5a High-Power Harness",
        "",
        "Status: validacion EN FORMA, no matcheo de coeficientes de Nivel 1. Additive Phase B base-data harness; not a freeze and not an adjudication.",
        "",
        "## Scope",
        "",
        f"- Frozen instances: `{', '.join(instances)}`.",
        f"- Methods represented: `{', '.join(METHODS)}`.",
        f"- Direct-Z methods use T=`{config.repetitions}` noisy Aer trajectory repetitions by splitting a single B_max shot pool per instance.",
        "- VD M=2 uses Step 3 Hadamard/SWAP cross-checks and B_den sizing. Cells whose requested trajectory budget exceeds the cap are marked, not imputed.",
        f"- B cap: `{config.b_max_cap}`; VD trajectory cap per numerator/denominator circuit: `{config.vd_trajectory_shot_cap_per_circuit}`.",
        "- Analyses E5/E7/E8/E12 are deferred to Step 5b/5c over this base table.",
        "",
        "## Cross-Checks And Budget",
        "",
        f"- Sampled aggregate rows: `{len(sampled)}`.",
        f"- Budget-marked rows: `{len(budget)}`.",
        f"- VD budget-marked instances: `{', '.join(vd_budget_instances) if vd_budget_instances else 'none'}`.",
        f"- Instances not reaching 10x B_den within cap: `{', '.join(non_crossing) if non_crossing else 'none'}`.",
        "",
        "## Per-Method Summary",
        "",
        "| method | sampled rows | budget rows | median abs bias sampled | median MSE sampled |",
        "|---|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        method_rows = [row for row in rows if row["method"] == method]
        method_sampled = [row for row in method_rows if row["sample_status"] == "sampled"]
        abs_bias = [abs(float(row["bias_empirical"])) for row in method_sampled if math.isfinite(float(row["bias_empirical"]))]
        mse = [float(row["mse_empirical"]) for row in method_sampled if math.isfinite(float(row["mse_empirical"]))]
        lines.append(
            f"| {method} | {len(method_sampled)} | {len(method_rows) - len(method_sampled)} "
            f"| {_median_or_nan(abs_bias):.6g} | {_median_or_nan(mse):.6g} |"
        )
    lines.extend([
        "",
        "## Instance Denominator Budget",
        "",
        "| instance | n | B_den | B_max | crosses B_den | reaches 10x B_den | VD status | noisy D reference |",
        "|---|---:|---:|---:|---|---|---|---:|",
    ])
    for instance_id in instances:
        vd_rows = [
            row for row in rows
            if row["instance_id"] == instance_id and row["method"] == "vd_m2_hadamard_swap"
        ]
        if not vd_rows:
            continue
        row = vd_rows[0]
        lines.append(
            f"| {instance_id} | {int(row['n_qubits'])} | {float(row['B_den_impl_estimate']):.6g} "
            f"| {int(row['B_max_instance'])} | {_bool_word(bool(row['grid_crosses_B_den']))} "
            f"| {_bool_word(bool(row['grid_reaches_10x_B_den']))} | {row['sample_status']} "
            f"| {float(row['noisy_D_reference']):.6g} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "This file is the base long-format harness output for later Level 2 analyses. "
            "Direct-Z unmitigated and SV rows are sampled at T=64 across the frozen ensemble "
            "using noisy Aer trajectories and configured tensor-product readout mitigation. "
            "VD M=2 rows carry the same B grid, resource columns, noiseless cross-checks, and "
            "B_den sizing; however, the noisy VD trajectory budget needed for T=64 at B_max "
            "exceeds the current cap, so those cells are explicitly marked as budget-limited "
            "rather than treated as evidence. Step 5b/5c should either raise the VD simulation "
            "budget or keep the VD limitation as an operational finding."
        ),
        "",
        f"Runtime for this harness run: `{max(float(row['runtime_seconds']) for row in rows):.3f}` seconds.",
    ])
    return "\n".join(lines) + "\n"


def _median_or_nan(values: list[float]) -> float:
    if not values:
        return float("nan")
    return float(np.median(np.asarray(values, dtype=np.float64)))


def _bool_word(value: bool) -> str:
    return "yes" if value else "no"


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


if __name__ == "__main__":
    raise SystemExit(main())
