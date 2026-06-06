"""Level 2 Step 2: noisy direct-Z sampling for unmitigated and SV estimators.

This additive Phase B runner validates finite-shot laws in form on the
Trotterized Level 2 circuit. It does not match Level 1 coefficients and does not
implement VD, folding, readout mitigation beyond tensorized assignment inversion,
or Level 2 E5/E7/E12.
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
from qiskit import QuantumCircuit

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from level2.circuits import (  # noqa: E402
    MIXER_TROTTER_STEPS,
    build_xy_qaoa_circuit,
    observable_expectation,
    qiskit_to_level1_state,
    simulate_noiseless_statevector,
)
from level2.noise_model import build_aer_simulator, load_config  # noqa: E402
from vd_sv import qaoa  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_sampling_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_sampling_report.md"

PRIMARY_INSTANCE_ID = "g6_k2_c000"
B_VALUES = (512, 2048, 8192)
REPETITIONS = 12
CALIBRATION_SHOTS = 20_000
ACCEPTANCE_REFERENCE_SHOTS = 20_000
BASE_SEED = 22002
SV_CLIP_FRACTION = 0.5
CALIBRATION_ABS_TOL = 0.02

FIELDS = [
    "row_kind",
    "instance_id",
    "method",
    "B",
    "repetitions",
    "resource_shots_per_rep",
    "mu_ideal_l2",
    "mean_estimate",
    "bias_empirical",
    "variance_empirical",
    "mse_empirical",
    "var_times_B",
    "mean_acceptance_fraction",
    "mean_negative_mass",
    "bias_floor_fit",
    "variance_slope_fit",
    "mse_fit_r2",
    "calibration_max_abs_error",
    "false_accept_mean_nonsector",
    "false_accept_max_nonsector",
    "false_reject_mean_sector",
    "false_reject_max_sector",
    "mixer_trotter_steps",
    "runtime_seconds",
]


@dataclass(frozen=True)
class SamplingConfig:
    b_values: tuple[int, ...] = B_VALUES
    repetitions: int = REPETITIONS
    calibration_shots: int = CALIBRATION_SHOTS
    acceptance_reference_shots: int = ACCEPTANCE_REFERENCE_SHOTS
    base_seed: int = BASE_SEED
    instance_id: str = PRIMARY_INSTANCE_ID


def main() -> int:
    t0 = time.time()
    rows, report = run_sampling(SamplingConfig(), started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_sampling(config: SamplingConfig, started_at: float | None = None) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    model = _select_model(config.instance_id)
    circuit = measured_noisy_qaoa_circuit(model)
    ideal_mu = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        model.inst,
    )
    observable_values = _observable_values(model.inst)

    readout_matrices = calibrate_readout_matrices(
        model.inst.n,
        shots=config.calibration_shots,
        seed=stable_seed(config.base_seed, model.inst.name, "calibration"),
    )
    calibration_max_abs_error = _calibration_error(readout_matrices)
    assignment = assignment_matrix(readout_matrices)
    contamination = postselection_contamination(readout_matrices, model.inst.weight)

    acceptance_reference = estimate_mitigated_acceptance_reference(
        circuit,
        model.inst,
        readout_matrices,
        assignment,
        shots=config.acceptance_reference_shots,
        seed=stable_seed(config.base_seed, model.inst.name, "acceptance_reference"),
    )

    samples: list[dict] = []
    for b in config.b_values:
        for rep in range(config.repetitions):
            seed = stable_seed(config.base_seed, model.inst.name, int(b), int(rep))
            counts = run_counts(circuit, shots=int(b), seed=seed)
            samples.extend(
                estimator_samples_from_counts(
                    counts,
                    model.inst,
                    observable_values,
                    readout_matrices,
                    assignment,
                    ideal_mu,
                    b=int(b),
                    rep=rep,
                    acceptance_reference=acceptance_reference,
                )
            )

    runtime_seconds = round(time.time() - t0, 3)
    rows = aggregate_samples(
        samples,
        config,
        ideal_mu,
        calibration_max_abs_error,
        contamination,
        runtime_seconds,
    )
    report = render_report(rows, config, readout_matrices, contamination, acceptance_reference)
    return rows, report


def measured_noisy_qaoa_circuit(model) -> QuantumCircuit:
    circuit = build_xy_qaoa_circuit(
        model,
        mixer_trotter_steps=MIXER_TROTTER_STEPS,
        decompose_for_aer=True,
    )
    circuit.measure_all()
    return circuit


def run_counts(circuit: QuantumCircuit, shots: int, seed: int) -> dict[str, int]:
    simulator = build_aer_simulator(noisy=True)
    result = simulator.run(circuit, shots=int(shots), seed_simulator=int(seed)).result()
    counts = result.get_counts()
    return {str(key).replace(" ", ""): int(value) for key, value in counts.items()}


def calibrate_readout_matrices(n: int, shots: int, seed: int) -> np.ndarray:
    matrices = np.zeros((n, 2, 2), dtype=np.float64)
    simulator = build_aer_simulator(noisy=True)
    for true_bit in (0, 1):
        circuit = QuantumCircuit(n, n)
        if true_bit == 1:
            circuit.x(range(n))
        circuit.measure(range(n), range(n))
        result = simulator.run(circuit, shots=int(shots), seed_simulator=int(seed + true_bit)).result()
        counts = {str(key).replace(" ", ""): int(value) for key, value in result.get_counts().items()}
        for key, count in counts.items():
            logical_bits = qiskit_key_to_logical_bits(key, n)
            for qubit, observed in enumerate(logical_bits):
                matrices[qubit, true_bit, int(observed)] += count
    matrices /= float(shots)
    return matrices


def estimator_samples_from_counts(
    counts: dict[str, int],
    inst: qaoa.QAOAInstance,
    observable_values: np.ndarray,
    readout_matrices: np.ndarray,
    assignment: np.ndarray,
    ideal_mu: float,
    b: int,
    rep: int,
    acceptance_reference: float,
) -> list[dict]:
    observed = observed_distribution_from_counts(counts, inst.n)
    mitigated, negative_mass = mitigate_distribution(observed, assignment)
    weights = hamming_weights(inst.n)
    sector = weights == inst.weight

    unmit = float(np.sum(observed * observable_values))
    raw_accept = float(np.sum(observed[sector]))
    raw_num = float(np.sum(observed[sector] * observable_values[sector]))
    raw_sv = raw_num / raw_accept if raw_accept > 0.0 else float("nan")

    mitigated_accept = float(np.sum(mitigated[sector]))
    mitigated_num = float(np.sum(mitigated[sector] * observable_values[sector]))
    denom = max(mitigated_accept, SV_CLIP_FRACTION * acceptance_reference)
    sv = mitigated_num / denom

    return [
        _sample_row("unmitigated", b, rep, unmit, ideal_mu, 1.0, 0.0),
        _sample_row("sv_mitigated", b, rep, sv, ideal_mu, mitigated_accept, negative_mass),
        _sample_row("sv_raw_postselect_diagnostic", b, rep, raw_sv, ideal_mu, raw_accept, 0.0),
    ]


def _sample_row(
    method: str,
    b: int,
    rep: int,
    estimate: float,
    ideal_mu: float,
    acceptance_fraction: float,
    negative_mass: float,
) -> dict:
    err = estimate - ideal_mu
    return {
        "method": method,
        "B": int(b),
        "rep": int(rep),
        "estimate": float(estimate),
        "squared_error": float(err * err),
        "acceptance_fraction": float(acceptance_fraction),
        "negative_mass": float(negative_mass),
    }


def aggregate_samples(
    samples: list[dict],
    config: SamplingConfig,
    ideal_mu: float,
    calibration_max_abs_error: float,
    contamination: dict[str, float],
    runtime_seconds: float,
) -> list[dict]:
    rows: list[dict] = []
    methods = sorted({sample["method"] for sample in samples})
    for method in methods:
        method_samples = [sample for sample in samples if sample["method"] == method]
        by_b = {}
        for sample in method_samples:
            by_b.setdefault(int(sample["B"]), []).append(sample)
        fit = fit_mse_law(by_b)
        for b in sorted(by_b):
            group = by_b[b]
            estimates = np.asarray([sample["estimate"] for sample in group], dtype=np.float64)
            mse_values = np.asarray([sample["squared_error"] for sample in group], dtype=np.float64)
            accept = np.asarray([sample["acceptance_fraction"] for sample in group], dtype=np.float64)
            neg_mass = np.asarray([sample["negative_mass"] for sample in group], dtype=np.float64)
            variance = float(np.var(estimates, ddof=1)) if estimates.size > 1 else 0.0
            rows.append({
                "row_kind": "aggregate",
                "instance_id": config.instance_id,
                "method": method,
                "B": int(b),
                "repetitions": config.repetitions,
                "resource_shots_per_rep": int(b),
                "mu_ideal_l2": ideal_mu,
                "mean_estimate": float(np.mean(estimates)),
                "bias_empirical": float(np.mean(estimates) - ideal_mu),
                "variance_empirical": variance,
                "mse_empirical": float(np.mean(mse_values)),
                "var_times_B": float(variance * b),
                "mean_acceptance_fraction": float(np.mean(accept)),
                "mean_negative_mass": float(np.mean(neg_mass)),
                "bias_floor_fit": fit["intercept"],
                "variance_slope_fit": fit["slope"],
                "mse_fit_r2": fit["r2"],
                "calibration_max_abs_error": calibration_max_abs_error,
                **contamination,
                "mixer_trotter_steps": MIXER_TROTTER_STEPS,
                "runtime_seconds": runtime_seconds,
            })
    return rows


def fit_mse_law(by_b: dict[int, list[dict]]) -> dict[str, float]:
    b_values = np.asarray(sorted(by_b), dtype=np.float64)
    variances = []
    bias_floor_terms = []
    for b in b_values:
        group = by_b[int(b)]
        estimates = np.asarray([sample["estimate"] for sample in group], dtype=np.float64)
        squared_errors = np.asarray([sample["squared_error"] for sample in group], dtype=np.float64)
        variance = float(np.var(estimates, ddof=1)) if estimates.size > 1 else 0.0
        variances.append(variance)
        bias_floor_terms.append(max(float(np.mean(squared_errors)) - variance, 0.0))
    variances = np.asarray(variances, dtype=np.float64)
    x = 1.0 / b_values
    slope = float(np.mean(variances * b_values))
    yhat = slope * x
    ss_res = float(np.sum((variances - yhat) ** 2))
    ss_tot = float(np.sum((variances - float(np.mean(variances))) ** 2))
    r2 = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return {
        "intercept": float(np.mean(bias_floor_terms)),
        "slope": slope,
        "r2": float(r2),
    }


def observed_distribution_from_counts(counts: dict[str, int], n: int) -> np.ndarray:
    total = float(sum(counts.values()))
    dist = np.zeros(2**n, dtype=np.float64)
    for key, count in counts.items():
        dist[qiskit_key_to_level1_index(key, n)] += float(count) / total
    return dist


def mitigate_distribution(observed: np.ndarray, assignment: np.ndarray) -> tuple[np.ndarray, float]:
    estimate = np.linalg.solve(assignment, observed)
    negative_mass = float(-np.sum(estimate[estimate < 0.0]))
    clipped = np.clip(estimate, 0.0, None)
    norm = float(np.sum(clipped))
    if norm == 0.0:
        return np.full_like(clipped, 1.0 / clipped.size), negative_mass
    return clipped / norm, negative_mass


def assignment_matrix(readout_matrices: np.ndarray) -> np.ndarray:
    n = int(readout_matrices.shape[0])
    size = 2**n
    matrix = np.zeros((size, size), dtype=np.float64)
    for true_idx in range(size):
        true_bits = level1_bits(true_idx, n)
        for obs_idx in range(size):
            obs_bits = level1_bits(obs_idx, n)
            prob = 1.0
            for qubit in range(n):
                prob *= readout_matrices[qubit, true_bits[qubit], obs_bits[qubit]]
            matrix[obs_idx, true_idx] = prob
    return matrix


def postselection_contamination(readout_matrices: np.ndarray, weight: int) -> dict[str, float]:
    n = int(readout_matrices.shape[0])
    assignment = assignment_matrix(readout_matrices)
    weights = hamming_weights(n)
    sector = weights == weight
    obs_sector = sector
    false_accept = np.sum(assignment[obs_sector, :][:, ~sector], axis=0)
    false_reject = np.sum(assignment[~obs_sector, :][:, sector], axis=0)
    return {
        "false_accept_mean_nonsector": float(np.mean(false_accept)) if false_accept.size else 0.0,
        "false_accept_max_nonsector": float(np.max(false_accept)) if false_accept.size else 0.0,
        "false_reject_mean_sector": float(np.mean(false_reject)) if false_reject.size else 0.0,
        "false_reject_max_sector": float(np.max(false_reject)) if false_reject.size else 0.0,
    }


def estimate_mitigated_acceptance_reference(
    circuit: QuantumCircuit,
    inst: qaoa.QAOAInstance,
    readout_matrices: np.ndarray,
    assignment: np.ndarray,
    shots: int,
    seed: int,
) -> float:
    counts = run_counts(circuit, shots=shots, seed=seed)
    observed = observed_distribution_from_counts(counts, inst.n)
    mitigated, _negative_mass = mitigate_distribution(observed, assignment)
    return float(np.sum(mitigated[hamming_weights(inst.n) == inst.weight]))


def qiskit_key_to_logical_bits(key: str, n: int) -> str:
    key = key.replace(" ", "")
    if len(key) != n:
        raise ValueError(f"expected {n} measured bits, got {key!r}")
    return key[::-1]


def qiskit_key_to_level1_index(key: str, n: int) -> int:
    bits = qiskit_key_to_logical_bits(key, n)
    return int(bits, 2)


def level1_bits(index: int, n: int) -> tuple[int, ...]:
    return tuple((int(index) >> (n - 1 - qubit)) & 1 for qubit in range(n))


def hamming_weights(n: int) -> np.ndarray:
    return np.fromiter((int(idx).bit_count() for idx in range(2**n)), dtype=np.int64)


def _observable_values(inst: qaoa.QAOAInstance) -> np.ndarray:
    diag = qaoa.cost_diagonal(inst)
    scale = float(np.max(np.abs(diag)))
    return diag / scale


def _calibration_error(matrices: np.ndarray) -> float:
    expected = np.asarray(load_config()["noise_model"]["readout_error_matrix"], dtype=np.float64)
    return float(np.max(np.abs(matrices - expected[None, :, :])))


def _select_model(instance_id: str):
    for model in frozen_models():
        if model.inst.name == instance_id:
            return model
    raise ValueError(f"instance not found: {instance_id}")


def stable_seed(base_seed: int, *parts: object) -> int:
    payload = "|".join([str(int(base_seed)), *(str(part) for part in parts)]).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1)


def render_report(
    rows: list[dict],
    config: SamplingConfig,
    readout_matrices: np.ndarray,
    contamination: dict[str, float],
    acceptance_reference: float,
) -> str:
    methods = sorted({row["method"] for row in rows})
    by_method = {
        method: [row for row in rows if row["method"] == method]
        for method in methods
    }
    largest_b = max(config.b_values)
    unmit_large = _row_for(by_method["unmitigated"], largest_b)
    sv_large = _row_for(by_method["sv_mitigated"], largest_b)
    raw_large = _row_for(by_method["sv_raw_postselect_diagnostic"], largest_b)
    lines = [
        "# Level 2 Step 2 Sampling",
        "",
        "Status: Phase B additive validation. Laws validated EN FORMA, not matched to Level 1 coefficients.",
        "",
        "## Scope",
        "",
        "- Circuit: realistic Level 2 QAOA depth with `mixer_trotter_steps=1`.",
        "- Reference: noiseless Level 2 statevector of that same circuit.",
        "- Methods: direct-Z unmitigated and readout-mitigated SV only.",
        "- Not implemented here: VD Hadamard tests, gate folding, readout-mitigation variants, Level 2 E5/E7/E12.",
        "",
        "## Readout Calibration",
        "",
        f"- Calibration shots per prepared state: `{config.calibration_shots}`.",
        f"- Max absolute calibration error vs configured matrix: `{_calibration_error(readout_matrices):.6g}`.",
        f"- Configured readout matrix: `{load_config()['noise_model']['readout_error_matrix']}`.",
        "- Mitigation: tensorized assignment inversion on the full distribution, followed by clipping negative quasi-probabilities to zero and renormalizing. Postselection is applied after mitigation.",
        "",
        "## Raw Postselection Contamination",
        "",
        f"- False-accept mean over non-sector states: `{contamination['false_accept_mean_nonsector']:.6g}`.",
        f"- False-accept max over non-sector states: `{contamination['false_accept_max_nonsector']:.6g}`.",
        f"- False-reject mean over sector states: `{contamination['false_reject_mean_sector']:.6g}`.",
        f"- False-reject max over sector states: `{contamination['false_reject_max_sector']:.6g}`.",
        f"- Mitigated SV acceptance reference: `{acceptance_reference:.6g}`.",
        "",
        "## Shape Summary",
        "",
        "| method | B | bias | variance | MSE | var*B | acceptance | fit floor | fit slope | fit R2 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method in methods:
        for row in by_method[method]:
            lines.append(
                f"| {method} | {row['B']} | {row['bias_empirical']:.6g} "
                f"| {row['variance_empirical']:.6g} | {row['mse_empirical']:.6g} "
                f"| {row['var_times_B']:.6g} | {row['mean_acceptance_fraction']:.6g} "
                f"| {row['bias_floor_fit']:.6g} | {row['variance_slope_fit']:.6g} "
                f"| {row['mse_fit_r2']:.6g} |"
            )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            f"At B={largest_b}, `sv_mitigated` has absolute bias "
            f"`{abs(float(sv_large['bias_empirical'])):.6g}` versus unmitigated "
            f"`{abs(float(unmit_large['bias_empirical'])):.6g}`. The raw postselection "
            f"diagnostic bias is `{abs(float(raw_large['bias_empirical'])):.6g}`, showing why "
            "readout mitigation before postselection is part of the Level 2 workflow. "
            "The empirical variances decrease with B in the reported sweep, while fitted "
            "MSE floors remain method-dependent bias floors under the Aer noise model."
        ),
    ])
    return "\n".join(lines) + "\n"


def _row_for(rows: Iterable[dict], b: int) -> dict:
    for row in rows:
        if int(row["B"]) == int(b):
            return row
    raise KeyError(b)


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
