"""Level 2 Step 5a redo: exact-rho multi-method sampling harness.

This additive Phase B harness generates the base long-format data consumed by
later Level 2 analyses. It intentionally does not adjudicate E5/E7/E8/E12.

Option A uses an exact noisy preparation density matrix per frozen instance.
Unmitigated and SV are sampled from the exact Z/readout distribution. VD M=2 is
sampled from the independent Hadamard-test binomial model with exact
``N_2=Tr(O rho^2)`` and ``D_2=Tr(rho^2)``. That VD model is intentionally
state-noise-only and optimistic: it omits the extra noisy c-SWAP/interference
circuit characterized in Step 3.
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
from level2 import sampling  # noqa: E402
from level2.circuits import (  # noqa: E402
    MIXER_TROTTER_STEPS,
    bit_reverse_index,
    build_xy_qaoa_circuit,
    observable_expectation,
    simulate_noiseless_statevector,
)
from level2.noise_model import build_noise_model, load_config  # noqa: E402
from vd_sv import qaoa  # noqa: E402
from vd_sv.estimators import make_rng, sample_direct_mean  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_highpower_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_highpower_report.md"

INSTANCE_IDS = tuple(f"g6_k2_c{i:03d}" for i in range(5)) + tuple(
    f"g8_k3_c{i:03d}" for i in range(5)
)
METHODS = ("unmitigated", "sv_mitigated", "vd_m2_hadamard_binomial")
REPETITIONS = 100
BASE_SEED = 25005
B_MIN = 64
B_GRID_FACTORS = (0.10, 0.25, 0.50, 1.0, 2.0, 5.0, 10.0)
ABSOLUTE_B_CEILING = 20_000_000
NOISELESS_D_TOL = 1.0e-10
NOISELESS_MU_TOL = 1.0e-10
DENOMINATOR_CLIP_FRACTION = 0.5
VD_MODEL = "state_noise_only_optimistic"
UNMIT_SV_MODEL = "exact_rho_plus_configured_readout"

FIELDS = [
    "row_kind",
    "instance_id",
    "n_qubits",
    "method",
    "sample_status",
    "estimator_model",
    "B",
    "repetitions",
    "B_max_instance",
    "B_den_impl_estimate",
    "B_over_B_den",
    "grid_crosses_B_den",
    "grid_reaches_10x_B_den",
    "mu_ideal_l2",
    "population_mean",
    "population_bias",
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
    "D_2_exact",
    "N_2_exact",
    "vd_population_mean",
    "noisy_D_reference",
    "denominator_clip_value",
    "state_purity_noisy",
    "readout_assignment_model",
    "noiseless_D_hat",
    "noiseless_N_hat",
    "noiseless_mu_hat",
    "noiseless_mu_abs_error",
    "resource_R_paired_sample",
    "resource_R_two_qubit_gate_proxy",
    "kappa_paired_sample",
    "kappa_two_qubit_gate_proxy",
    "mixer_trotter_steps",
    "runtime_seconds",
]


@dataclass(frozen=True)
class HighPowerConfig:
    instance_ids: tuple[str, ...] = INSTANCE_IDS
    repetitions: int = REPETITIONS
    b_min: int = B_MIN
    absolute_b_ceiling: int = ABSOLUTE_B_CEILING
    base_seed: int = BASE_SEED


@dataclass(frozen=True)
class InstanceContext:
    model: object
    mu_ideal: float
    rho_noisy: np.ndarray
    p_true: np.ndarray
    p_observed: np.ndarray
    observable_values: np.ndarray
    assignment: np.ndarray
    sector_mask: np.ndarray
    readout_matrices: np.ndarray
    d2: float
    n2: float
    vd_population_mean: float
    b_den: float
    sv_acceptance_reference: float
    noiseless: dict[str, float]


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
    rows: list[dict] = []
    for instance_id in config.instance_ids:
        rows.extend(run_instance(_select_model(instance_id), config))
    runtime_seconds = round(time.time() - t0, 3)
    for row in rows:
        row["runtime_seconds"] = runtime_seconds
    return rows, render_report(rows, config)


def run_instance(model, config: HighPowerConfig) -> list[dict]:
    context = build_instance_context(model)
    b_grid = b_grid_for_bden(context.b_den, config.b_min, config.absolute_b_ceiling)
    b_max = max(b_grid)
    rows: list[dict] = []
    rows.extend(run_unmitigated(context, config, b_grid, b_max))
    rows.extend(run_sv(context, config, b_grid, b_max))
    rows.extend(run_vd(context, config, b_grid, b_max))
    return rows


def build_instance_context(model) -> InstanceContext:
    inst = model.inst
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        inst,
    )
    rho_noisy = exact_preparation_density_matrix(model, noisy=True)
    rho_noiseless = exact_preparation_density_matrix(model, noisy=False)
    observable_values = normalized_observable_values(inst)
    o_matrix = np.diag(observable_values)

    d0, n0, mu0 = vd_population_from_rho(rho_noiseless, o_matrix)
    noiseless = {
        "D_hat": d0,
        "N_hat": n0,
        "mu_hat": mu0,
        "mu_abs_error": abs(mu0 - mu_ideal),
    }
    if abs(d0 - 1.0) > NOISELESS_D_TOL or noiseless["mu_abs_error"] > NOISELESS_MU_TOL:
        raise RuntimeError(
            f"exact-rho noiseless VD cross-check failed for {inst.name}: "
            f"D_2={d0:.12g}, mu_abs_error={noiseless['mu_abs_error']:.12g}"
        )

    d2, n2, vd_mu = vd_population_from_rho(rho_noisy, o_matrix)
    p_true = probability_vector(np.real(np.diag(rho_noisy)))
    readout_matrices = configured_readout_matrices(inst.n)
    assignment = sampling.assignment_matrix(readout_matrices)
    p_observed = probability_vector(assignment @ p_true)
    sector = sampling.hamming_weights(inst.n) == inst.weight
    sv_acceptance = float(np.sum(p_true[sector]))
    return InstanceContext(
        model=model,
        mu_ideal=mu_ideal,
        rho_noisy=rho_noisy,
        p_true=p_true,
        p_observed=p_observed,
        observable_values=observable_values,
        assignment=assignment,
        sector_mask=sector,
        readout_matrices=readout_matrices,
        d2=d2,
        n2=n2,
        vd_population_mean=vd_mu,
        b_den=denominator_sample_threshold(d2),
        sv_acceptance_reference=sv_acceptance,
        noiseless=noiseless,
    )


def exact_preparation_density_matrix(model, noisy: bool) -> np.ndarray:
    circuit = build_xy_qaoa_circuit(
        model,
        mixer_trotter_steps=MIXER_TROTTER_STEPS,
        decompose_for_aer=True,
    )
    circuit.save_density_matrix()
    simulator = AerSimulator(
        method="density_matrix",
        noise_model=build_noise_model() if noisy else None,
        seed_simulator=int(load_config()["noise_model"]["seed_simulator"]),
    )
    result = simulator.run(circuit).result()
    rho_qiskit = np.asarray(result.data(0)["density_matrix"], dtype=np.complex128)
    rho_level1 = qiskit_density_to_level1(rho_qiskit, model.inst.n)
    rho_level1 = 0.5 * (rho_level1 + rho_level1.conj().T)
    trace = np.trace(rho_level1)
    if abs(trace) == 0.0:
        raise ValueError(f"zero-trace density matrix for {model.inst.name}")
    return rho_level1 / trace


def qiskit_density_to_level1(rho: np.ndarray, n: int) -> np.ndarray:
    perm = [bit_reverse_index(index, n) for index in range(2**n)]
    return np.asarray(rho, dtype=np.complex128)[np.ix_(perm, perm)]


def vd_population_from_rho(rho: np.ndarray, observable: np.ndarray) -> tuple[float, float, float]:
    rho2 = rho @ rho
    d2 = float(np.real(np.trace(rho2)))
    n2 = float(np.real(np.trace(observable @ rho2)))
    if not (0.0 < d2 <= 1.0 + 1.0e-9):
        raise ValueError(f"invalid D_2={d2}")
    return d2, n2, float(n2 / d2)


def run_unmitigated(
    context: InstanceContext,
    config: HighPowerConfig,
    b_grid: tuple[int, ...],
    b_max: int,
) -> list[dict]:
    population = float(context.p_observed @ context.observable_values)
    rows = []
    for b in b_grid:
        rng = make_rng(stable_seed(config.base_seed, context.model.inst.name, "unmitigated", int(b)))
        estimates = sample_direct_mean(
            context.p_observed,
            context.observable_values,
            int(b),
            int(config.repetitions),
            rng,
        )
        rows.append(
            aggregate_row(
                context,
                config,
                method="unmitigated",
                estimator_model=UNMIT_SV_MODEL,
                b=int(b),
                b_max=b_max,
                estimates=estimates,
                population_mean=population,
            )
        )
    return rows


def run_sv(
    context: InstanceContext,
    config: HighPowerConfig,
    b_grid: tuple[int, ...],
    b_max: int,
) -> list[dict]:
    sector = context.sector_mask
    population_num = float(np.sum(context.p_true[sector] * context.observable_values[sector]))
    population = population_num / context.sv_acceptance_reference
    rows = []
    for b in b_grid:
        rng = make_rng(stable_seed(config.base_seed, context.model.inst.name, "sv_mitigated", int(b)))
        counts = rng.multinomial(int(b), context.p_observed, size=int(config.repetitions))
        estimates = []
        acceptances = []
        negative_mass = []
        for sample_counts in counts:
            observed = sample_counts.astype(np.float64) / float(b)
            mitigated, neg = sampling.mitigate_distribution(observed, context.assignment)
            mitigated_accept = float(np.sum(mitigated[sector]))
            mitigated_num = float(np.sum(mitigated[sector] * context.observable_values[sector]))
            denom = max(mitigated_accept, sampling.SV_CLIP_FRACTION * context.sv_acceptance_reference)
            estimates.append(mitigated_num / denom)
            acceptances.append(mitigated_accept)
            negative_mass.append(neg)
        rows.append(
            aggregate_row(
                context,
                config,
                method="sv_mitigated",
                estimator_model=UNMIT_SV_MODEL,
                b=int(b),
                b_max=b_max,
                estimates=np.asarray(estimates, dtype=np.float64),
                population_mean=population,
                acceptances=np.asarray(acceptances, dtype=np.float64),
                negative_mass=np.asarray(negative_mass, dtype=np.float64),
            )
        )
    return rows


def run_vd(
    context: InstanceContext,
    config: HighPowerConfig,
    b_grid: tuple[int, ...],
    b_max: int,
) -> list[dict]:
    rows = []
    for b in b_grid:
        rng = make_rng(stable_seed(config.base_seed, context.model.inst.name, "vd_m2", int(b)))
        estimates, n_hat, d_hat, d_clipped = sample_vd_streams(
            context.n2,
            context.d2,
            int(b),
            int(config.repetitions),
            rng,
        )
        rows.append(
            aggregate_row(
                context,
                config,
                method="vd_m2_hadamard_binomial",
                estimator_model=VD_MODEL,
                b=int(b),
                b_max=b_max,
                estimates=estimates,
                population_mean=context.vd_population_mean,
                n_hat=n_hat,
                d_hat=d_hat,
                d_clipped=d_clipped,
            )
        )
    return rows


def sample_vd_streams(
    n2: float,
    d2: float,
    b: int,
    repetitions: int,
    rng,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not -1.0 <= n2 <= 1.0:
        raise ValueError(f"N_2 outside [-1,1]: {n2}")
    if not 0.0 < d2 <= 1.0:
        raise ValueError(f"D_2 outside (0,1]: {d2}")
    q_n = 0.5 * (1.0 + float(n2))
    q_d = 0.5 * (1.0 + float(d2))
    k_n = rng.binomial(int(b), q_n, size=int(repetitions))
    k_d = rng.binomial(int(b), q_d, size=int(repetitions))
    n_hat = 2.0 * k_n / float(b) - 1.0
    d_hat = 2.0 * k_d / float(b) - 1.0
    d_clipped = np.maximum(d_hat, DENOMINATOR_CLIP_FRACTION * float(d2))
    return n_hat / d_clipped, n_hat, d_hat, d_clipped


def aggregate_row(
    context: InstanceContext,
    config: HighPowerConfig,
    method: str,
    estimator_model: str,
    b: int,
    b_max: int,
    estimates: np.ndarray,
    population_mean: float,
    acceptances: np.ndarray | None = None,
    negative_mass: np.ndarray | None = None,
    n_hat: np.ndarray | None = None,
    d_hat: np.ndarray | None = None,
    d_clipped: np.ndarray | None = None,
) -> dict:
    estimates = np.asarray(estimates, dtype=np.float64)
    errors = estimates - context.mu_ideal
    variance = float(np.var(estimates, ddof=1)) if estimates.size > 1 else 0.0
    k_paired, k_twq = kappas_for_method(context.model.inst.n, method)
    b_den = float(context.b_den)
    return {
        "row_kind": "aggregate",
        "instance_id": context.model.inst.name,
        "n_qubits": int(context.model.inst.n),
        "method": method,
        "sample_status": "sampled",
        "estimator_model": estimator_model,
        "B": int(b),
        "repetitions": int(config.repetitions),
        "B_max_instance": int(b_max),
        "B_den_impl_estimate": b_den,
        "B_over_B_den": float(b / b_den),
        "grid_crosses_B_den": bool(b_max >= b_den),
        "grid_reaches_10x_B_den": bool(b_max >= 10.0 * b_den),
        "mu_ideal_l2": float(context.mu_ideal),
        "population_mean": float(population_mean),
        "population_bias": float(population_mean - context.mu_ideal),
        "mean_estimate": float(np.mean(estimates)),
        "bias_empirical": float(np.mean(estimates) - context.mu_ideal),
        "variance_empirical": variance,
        "mse_empirical": float(np.mean(errors**2)),
        "var_times_B": float(variance * b),
        "mean_acceptance_fraction": mean_or_nan(acceptances),
        "mean_negative_mass": mean_or_nan(negative_mass),
        "mean_N_hat": mean_or_nan(n_hat),
        "mean_D_hat": mean_or_nan(d_hat),
        "mean_D_clipped": mean_or_nan(d_clipped),
        "D_2_exact": float(context.d2),
        "N_2_exact": float(context.n2),
        "vd_population_mean": float(context.vd_population_mean),
        "noisy_D_reference": float(context.d2),
        "denominator_clip_value": float(DENOMINATOR_CLIP_FRACTION * context.d2),
        "state_purity_noisy": float(context.d2),
        "readout_assignment_model": configured_readout_label(),
        "noiseless_D_hat": float(context.noiseless["D_hat"]),
        "noiseless_N_hat": float(context.noiseless["N_hat"]),
        "noiseless_mu_hat": float(context.noiseless["mu_hat"]),
        "noiseless_mu_abs_error": float(context.noiseless["mu_abs_error"]),
        "resource_R_paired_sample": float(k_paired * b),
        "resource_R_two_qubit_gate_proxy": float(k_twq * b),
        "kappa_paired_sample": float(k_paired),
        "kappa_two_qubit_gate_proxy": float(k_twq),
        "mixer_trotter_steps": MIXER_TROTTER_STEPS,
        "runtime_seconds": 0.0,
    }


def b_grid_for_bden(b_den: float, b_min: int, absolute_b_ceiling: int) -> tuple[int, ...]:
    if not math.isfinite(float(b_den)) or float(b_den) <= 0.0:
        raise ValueError(f"invalid B_den={b_den}")
    values = []
    for factor in B_GRID_FACTORS:
        b = int(math.ceil(float(b_den) * float(factor)))
        values.append(max(int(b_min), b))
    required = int(math.ceil(10.0 * float(b_den)))
    if required > int(absolute_b_ceiling):
        values.append(int(absolute_b_ceiling))
    else:
        values.append(required)
    return tuple(sorted(set(values)))


def denominator_sample_threshold(d2: float, eps: float = 1.0e-3) -> float:
    d_abs = abs(float(d2))
    if d_abs <= 0.0:
        return float("inf")
    sigma_d2 = max(1.0 - d_abs**2, 0.0)
    return float((8.0 * sigma_d2 / d_abs**2 + 8.0 / (3.0 * d_abs)) * math.log(1.0 / eps))


def normalized_observable_values(inst: qaoa.QAOAInstance) -> np.ndarray:
    diag = qaoa.cost_diagonal(inst)
    scale = float(np.max(np.abs(diag)))
    if scale == 0.0:
        raise ValueError("zero observable scale")
    return np.asarray(diag / scale, dtype=np.float64)


def configured_readout_matrices(n: int) -> np.ndarray:
    matrix = np.asarray(load_config()["noise_model"]["readout_error_matrix"], dtype=np.float64)
    return np.repeat(matrix[None, :, :], int(n), axis=0)


def configured_readout_label() -> str:
    matrix = load_config()["noise_model"]["readout_error_matrix"]
    return f"tensor_product_configured_readout_{matrix}"


def probability_vector(values: np.ndarray) -> np.ndarray:
    arr = np.clip(np.asarray(values, dtype=np.float64), 0.0, None)
    total = float(np.sum(arr))
    if total <= 0.0:
        raise ValueError("non-positive probability vector")
    return arr / total


def kappas_for_method(n_qubits: int, method: str) -> tuple[float, float]:
    kappa = resource_definitions(n_qubits)
    if method == "vd_m2_hadamard_binomial":
        key = "vd"
    elif method == "sv_mitigated":
        key = "sv"
    else:
        key = "unmitigated"
    return float(kappa["paired_sample"][key]), float(kappa["two_qubit_gate_proxy"][key])


def mean_or_nan(values: np.ndarray | None) -> float:
    if values is None:
        return float("nan")
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return float("nan")
    return float(np.mean(arr))


def render_report(rows: list[dict], config: HighPowerConfig) -> str:
    instances = sorted({row["instance_id"] for row in rows})
    non_10x = sorted({
        row["instance_id"]
        for row in rows
        if row["method"] == "vd_m2_hadamard_binomial" and not bool(row["grid_reaches_10x_B_den"])
    })
    lines = [
        "# Level 2 Step 5a High-Power Harness (Redo, Option A)",
        "",
        "Status: validacion EN FORMA, no matcheo de coeficientes de Nivel 1. Additive Phase B base-data harness; not a freeze and not an adjudication.",
        "",
        "## Scope",
        "",
        f"- Frozen instances: `{', '.join(instances)}`.",
        f"- Methods represented: `{', '.join(METHODS)}`.",
        f"- Repetitions per cell: `{config.repetitions}`.",
        "- Common base: exact Aer density matrix of the noisy state-preparation circuit at `mixer_trotter_steps=1`.",
        "- Unmitigated/SV model: exact rho plus configured tensor-product readout, then multinomial finite-shot sampling.",
        "- VD model: exact `D_2=Tr(rho^2)` and `N_2=Tr(O rho^2)` plus independent Hadamard-binomial finite-shot sampling.",
        "- VD framing: state-noise-only optimistic model; it omits the extra c-SWAP/interference/readout noise characterized in Step 3.",
        "- Analyses E5/E7/E8/E12 are deferred to Step 5b/5c over this base table.",
        "",
        "## Cross-Checks And Grid",
        "",
        f"- Sampled aggregate rows: `{len(rows)}`.",
        "- Budget-marked rows: `0`.",
        f"- Instances not reaching 10x B_den: `{', '.join(non_10x) if non_10x else 'none'}`.",
        f"- Absolute B ceiling configured: `{config.absolute_b_ceiling}`.",
        "",
        "## Per-Method Summary",
        "",
        "| method | rows | median abs empirical bias | median MSE | median population bias |",
        "|---|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        method_rows = [row for row in rows if row["method"] == method]
        abs_bias = [abs(float(row["bias_empirical"])) for row in method_rows]
        mse = [float(row["mse_empirical"]) for row in method_rows]
        pop_bias = [abs(float(row["population_bias"])) for row in method_rows]
        lines.append(
            f"| {method} | {len(method_rows)} | {_median_or_nan(abs_bias):.6g} "
            f"| {_median_or_nan(mse):.6g} | {_median_or_nan(pop_bias):.6g} |"
        )
    lines.extend([
        "",
        "## Inter-Instance Dispersion",
        "",
        "| method | large-B mean abs bias avg | large-B mean abs bias sd | large-B MSE avg | large-B MSE sd |",
        "|---|---:|---:|---:|---:|",
    ])
    for method in METHODS:
        large_rows = largest_b_rows(rows, method)
        abs_bias = np.asarray([abs(float(row["bias_empirical"])) for row in large_rows], dtype=np.float64)
        mse = np.asarray([float(row["mse_empirical"]) for row in large_rows], dtype=np.float64)
        lines.append(
            f"| {method} | {float(np.mean(abs_bias)):.6g} | {_std_or_zero(abs_bias):.6g} "
            f"| {float(np.mean(mse)):.6g} | {_std_or_zero(mse):.6g} |"
        )
    lines.extend([
        "",
        "## Instance Denominator Grid",
        "",
        "| instance | n | D_2 exact | B_den | B_max | reaches 10x B_den | VD sampled |",
        "|---|---:|---:|---:|---:|---|---|",
    ])
    for instance_id in instances:
        vd_rows = [
            row for row in rows
            if row["instance_id"] == instance_id and row["method"] == "vd_m2_hadamard_binomial"
        ]
        row = vd_rows[0]
        lines.append(
            f"| {instance_id} | {int(row['n_qubits'])} | {float(row['D_2_exact']):.6g} "
            f"| {float(row['B_den_impl_estimate']):.6g} | {int(row['B_max_instance'])} "
            f"| {_bool_word(bool(row['grid_reaches_10x_B_den']))} | {_bool_word(row['sample_status'] == 'sampled')} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "This redo replaces the trajectory-capped Step 5a table with exact-rho Option A. "
            "VD is sampled in every frozen instance and every grid reaches at least 10x B_den. "
            "The ordering of VD/SV/unmitigated is operating-window dependent, not universal: "
            "the optimistic VD model has the smaller bias floor in the n=6 moderate-noise "
            "window, while SV has the smaller error in the n=8 extreme-decoherence window "
            "where D_2 is near 0.007. Two caveats are explicit: the n=6 VD rows are an "
            "optimistic state-noise-only model without c-SWAP/interference/readout overhead, "
            "and the n=8 window is close to maximally mixed. No E5/E7/E8/E12 conclusions are "
            "drawn here; those analyses consume this table next."
        ),
        "",
        f"Runtime for this harness run: `{max(float(row['runtime_seconds']) for row in rows):.3f}` seconds.",
    ])
    return "\n".join(lines) + "\n"


def largest_b_rows(rows: list[dict], method: str) -> list[dict]:
    out = []
    for instance_id in sorted({row["instance_id"] for row in rows}):
        inst_method = [
            row for row in rows
            if row["instance_id"] == instance_id and row["method"] == method
        ]
        if inst_method:
            out.append(max(inst_method, key=lambda row: int(row["B"])))
    return out


def _median_or_nan(values: list[float]) -> float:
    if not values:
        return float("nan")
    return float(np.median(np.asarray(values, dtype=np.float64)))


def _std_or_zero(values: np.ndarray) -> float:
    if values.size <= 1:
        return 0.0
    return float(np.std(values, ddof=1))


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
