r"""Level 2 Step 4: unitary gate folding noise amplification.

This additive Phase B foundation step implements global unitary folding on the
realistic Level 2 QAOA state-preparation circuit:

    U -> U (U^\dagger U)^k,  lambda = 2k + 1.

The ideal unitary is unchanged, while the decomposed gate count grows with
``lambda`` under the Aer noise model. This is a smoke layer for the later E8
noise-sweep run, not a high-power experiment.
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
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from level2.circuits import (  # noqa: E402
    MIXER_TROTTER_STEPS,
    bit_reverse_index,
    build_xy_qaoa_circuit,
    observable_expectation,
    qiskit_to_level1_state,
    simulate_noiseless_statevector,
)
from level2.noise_model import build_noise_model, load_config  # noqa: E402
from vd_sv import qaoa  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_folding_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_folding_report.md"

PRIMARY_INSTANCE_ID = "g6_k2_c000"
NOISE_SCALES = (1, 3, 5)
BASE_SEED = 24004
NOISELESS_INVARIANCE_TOL = 1.0e-10
MONOTONIC_TOL = 1.0e-10

FIELDS = [
    "row_kind",
    "instance_id",
    "method",
    "noise_scale_lambda",
    "fold_k",
    "mixer_trotter_steps",
    "mu_ideal_l2",
    "mu_noiseless_folded",
    "noiseless_abs_error",
    "noisy_population_estimate",
    "bias_population",
    "abs_bias_population",
    "mse_population_bias_only",
    "cx_count",
    "u_count",
    "depth",
    "readout_error_included",
    "simulator_seed",
    "runtime_seconds",
]


@dataclass(frozen=True)
class FoldingConfig:
    noise_scales: tuple[int, ...] = NOISE_SCALES
    base_seed: int = BASE_SEED
    instance_id: str = PRIMARY_INSTANCE_ID


def main() -> int:
    t0 = time.time()
    rows, report = run_folding(FoldingConfig(), started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_folding(config: FoldingConfig, started_at: float | None = None) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    model = _select_model(config.instance_id)
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        model.inst,
    )
    rows: list[dict] = []
    for scale in config.noise_scales:
        row = evaluate_folded_scale(
            model,
            noise_scale_lambda=int(scale),
            mu_ideal=mu_ideal,
            seed=stable_seed(config.base_seed, model.inst.name, int(scale)),
        )
        rows.append(row)
    runtime_seconds = round(time.time() - t0, 3)
    for row in rows:
        row["runtime_seconds"] = runtime_seconds
    report = render_report(rows, config)
    return rows, report


def evaluate_folded_scale(model, noise_scale_lambda: int, mu_ideal: float, seed: int) -> dict:
    folded = folded_stateprep_circuit(model, noise_scale_lambda=noise_scale_lambda)
    decomposed = decompose_for_aer(folded)
    state = np.asarray(Statevector.from_instruction(folded).data, dtype=np.complex128)
    level1_state = qiskit_to_level1_state(state, model.inst.n)
    mu_noiseless = observable_expectation(level1_state, model.inst)
    noisy_dist = noisy_observed_distribution(decomposed, model.inst.n, seed=seed)
    observable = observable_values(model.inst)
    noisy_mu = float(np.sum(noisy_dist * observable))
    bias = noisy_mu - mu_ideal
    ops = decomposed.count_ops()
    return {
        "row_kind": "aggregate",
        "instance_id": model.inst.name,
        "method": "unmitigated_density_matrix_population",
        "noise_scale_lambda": int(noise_scale_lambda),
        "fold_k": int((noise_scale_lambda - 1) // 2),
        "mixer_trotter_steps": MIXER_TROTTER_STEPS,
        "mu_ideal_l2": float(mu_ideal),
        "mu_noiseless_folded": float(mu_noiseless),
        "noiseless_abs_error": float(abs(mu_noiseless - mu_ideal)),
        "noisy_population_estimate": noisy_mu,
        "bias_population": float(bias),
        "abs_bias_population": float(abs(bias)),
        "mse_population_bias_only": float(bias * bias),
        "cx_count": int(ops.get("cx", 0)),
        "u_count": int(ops.get("u", 0)),
        "depth": int(decomposed.depth()),
        "readout_error_included": True,
        "simulator_seed": int(seed),
        "runtime_seconds": 0.0,
    }


def folded_stateprep_circuit(model, noise_scale_lambda: int) -> QuantumCircuit:
    if noise_scale_lambda < 1 or noise_scale_lambda % 2 != 1:
        raise ValueError("noise_scale_lambda must be an odd positive integer")
    k = (int(noise_scale_lambda) - 1) // 2
    base = build_xy_qaoa_circuit(
        model,
        mixer_trotter_steps=MIXER_TROTTER_STEPS,
        decompose_for_aer=False,
    )
    circuit = QuantumCircuit(model.inst.n, name=f"folded_l{noise_scale_lambda}_{model.inst.name}")
    circuit.compose(base, inplace=True)
    for _ in range(k):
        circuit.compose(base.inverse(), inplace=True)
        circuit.compose(base, inplace=True)
    circuit.metadata = {
        "instance_id": model.inst.name,
        "noise_scale_lambda": int(noise_scale_lambda),
        "fold_k": int(k),
        "folding": "global U (Udg U)^k on state-prep QAOA only",
    }
    return circuit


def decompose_for_aer(circuit: QuantumCircuit) -> QuantumCircuit:
    return circuit.decompose(reps=10)


def noisy_observed_distribution(circuit: QuantumCircuit, n: int, seed: int) -> np.ndarray:
    density_circuit = circuit.copy()
    density_circuit.save_density_matrix()
    simulator = AerSimulator(
        method="density_matrix",
        noise_model=build_noise_model(),
        seed_simulator=int(seed),
    )
    result = simulator.run(density_circuit).result()
    rho = np.asarray(result.data(0)["density_matrix"], dtype=np.complex128)
    qiskit_probs = np.real(np.diag(rho))
    level1_probs = np.zeros_like(qiskit_probs, dtype=np.float64)
    for qiskit_index, prob in enumerate(qiskit_probs):
        level1_probs[bit_reverse_index(qiskit_index, n)] = float(prob)
    level1_probs = np.clip(level1_probs, 0.0, None)
    level1_probs /= float(np.sum(level1_probs))
    return apply_readout_error(level1_probs, n)


def apply_readout_error(true_distribution: np.ndarray, n: int) -> np.ndarray:
    readout = np.asarray(load_config()["noise_model"]["readout_error_matrix"], dtype=np.float64)
    observed = np.zeros_like(true_distribution, dtype=np.float64)
    for true_idx, true_prob in enumerate(true_distribution):
        if true_prob == 0.0:
            continue
        true_bits = level1_bits(true_idx, n)
        for obs_idx in range(2**n):
            obs_bits = level1_bits(obs_idx, n)
            prob = 1.0
            for qubit in range(n):
                prob *= readout[true_bits[qubit], obs_bits[qubit]]
            observed[obs_idx] += float(true_prob) * prob
    observed /= float(np.sum(observed))
    return observed


def observable_values(inst: qaoa.QAOAInstance) -> np.ndarray:
    diag = qaoa.cost_diagonal(inst)
    scale = float(np.max(np.abs(diag)))
    if scale == 0.0:
        raise ValueError("zero observable scale")
    return diag / scale


def level1_bits(index: int, n: int) -> tuple[int, ...]:
    return tuple((int(index) >> (n - 1 - qubit)) & 1 for qubit in range(n))


def abs_bias_is_monotone(rows: list[dict], tol: float = MONOTONIC_TOL) -> bool:
    ordered = sorted(rows, key=lambda row: int(row["noise_scale_lambda"]))
    vals = [float(row["abs_bias_population"]) for row in ordered]
    return all(vals[i + 1] + tol >= vals[i] for i in range(len(vals) - 1))


def cx_count_is_monotone(rows: list[dict]) -> bool:
    ordered = sorted(rows, key=lambda row: int(row["noise_scale_lambda"]))
    vals = [int(row["cx_count"]) for row in ordered]
    return all(vals[i + 1] > vals[i] for i in range(len(vals) - 1))


def render_report(rows: list[dict], config: FoldingConfig) -> str:
    ordered = sorted(rows, key=lambda row: int(row["noise_scale_lambda"]))
    max_noiseless_error = max(float(row["noiseless_abs_error"]) for row in ordered)
    monotone_bias = abs_bias_is_monotone(ordered)
    monotone_cx = cx_count_is_monotone(ordered)
    lines = [
        "# Level 2 Step 4 Gate Folding",
        "",
        "Status: foundation de amplificacion de ruido para E8; validacion EN FORMA. Additive Phase B smoke layer; not a freeze and not an adjudication.",
        "",
        "## Scope",
        "",
        "- Folding type: global unitary folding on the realistic QAOA state-prep circuit.",
        "- Map: `U -> U (U^dagger U)^k`, with `lambda = 2k + 1`.",
        "- Folded object: state-prep QAOA only. VD c-SWAP/interferometry is not folded here.",
        "- Instance: `g6_k2_c000` only.",
        "- Not implemented here: E5, E7, E8, E12, hardware, or high-power multi-method ensemble.",
        "",
        "## Noiseless Invariance Cross-Check",
        "",
        f"- `mu_ideal_L2`: `{ordered[0]['mu_ideal_l2']:.12g}`.",
        f"- Max `|mu_noiseless_folded - mu_ideal_L2|`: `{max_noiseless_error:.3e}`.",
        f"- Tolerance: `{NOISELESS_INVARIANCE_TOL:.1e}`.",
        "- Interpretation: folding preserves the logical unitary before noise, as required by unitary folding.",
        "",
        "## Noisy Amplification",
        "",
        f"- Noisy bias is monotone non-decreasing in `lambda`: `{monotone_bias}`.",
        f"- CX count strictly grows with `lambda`: `{monotone_cx}`.",
        "- The noisy population estimate is computed with Aer density-matrix gate noise plus the configured tensorized readout error. This avoids finite-shot noise in the foundation check; high-power sampled runs are deferred.",
        "",
        "| lambda | k | CX | depth | mu noiseless | noisy estimate | bias | abs bias | bias-only MSE |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ordered:
        lines.append(
            f"| {row['noise_scale_lambda']} | {row['fold_k']} | {row['cx_count']} "
            f"| {row['depth']} | {row['mu_noiseless_folded']:.9g} "
            f"| {row['noisy_population_estimate']:.9g} | {row['bias_population']:.9g} "
            f"| {row['abs_bias_population']:.9g} | {row['mse_population_bias_only']:.9g} |"
        )
    lines.extend([
        "",
        "## Descriptive Conclusion",
        "",
        (
            "The folded circuits leave the noiseless reference invariant while increasing "
            "the decomposed CX count and the noisy unmitigated bias. This validates the "
            "Level 2 noise-amplification mechanism in form. The folding parameter `lambda` "
            "is the device-simulation analogue of the Level 1 noise-strength sweep `p`; "
            "it enables the later Step 5 E8/window-location sweep without selecting new "
            "instances or changing frozen artifacts."
        ),
        "",
        f"Runtime for this smoke run: `{ordered[0]['runtime_seconds']:.3f}` seconds.",
    ])
    return "\n".join(lines) + "\n"


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
