"""Level 2 Step 3: VD M=2 Hadamard/SWAP sampling.

This additive Phase B runner implements the gate-level M=2 VD quotient estimator
on the realistic Level 2 QAOA circuit. It is a smoke/foundation layer: laws are
checked in form, not matched to Level 1 coefficients, and no folding or Level 2
E5/E7/E8/E12 ensemble run is performed here.
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
from experiments.e7_resource_observable_sensitivity import resource_definitions  # noqa: E402
from level2.circuits import (  # noqa: E402
    MIXER_TROTTER_STEPS,
    build_xy_qaoa_circuit,
    observable_expectation,
    simulate_noiseless_statevector,
)
from level2.noise_model import build_aer_simulator  # noqa: E402
from vd_sv import qaoa  # noqa: E402


OUT_CSV = REPO_ROOT / "level2" / "level2_vd_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_vd_report.md"
STEP2_CSV = REPO_ROOT / "level2" / "level2_sampling_results.csv"

PRIMARY_INSTANCE_ID = "g6_k2_c000"
B_VALUES = (128, 256, 512)
REPETITIONS = 2
NOISELESS_CHECK_SHOTS = 4_096
NOISY_DENOMINATOR_REFERENCE_SHOTS = 1_024
BASE_SEED = 23003
DENOMINATOR_CLIP_FRACTION = 0.5
DENOMINATOR_CLIP_MIN = 1.0e-6
NOISELESS_D_TOL = 0.02
NOISELESS_MU_TOL = 0.025
VD_BIAS_REDUCTION_TOL = 0.02
M_COPIES = 2

FIELDS = [
    "row_kind",
    "instance_id",
    "method",
    "B",
    "repetitions",
    "num_shots_per_rep",
    "den_shots_per_rep",
    "raw_hadamard_calls_per_rep",
    "resource_paired_sample",
    "resource_two_qubit_gate_proxy",
    "kappa_paired_sample_vd",
    "kappa_two_qubit_gate_proxy_vd",
    "n_qubits_system",
    "vd_circuit_qubits",
    "copies_M",
    "cswap_cx_count",
    "numerator_cx_count",
    "denominator_cx_count",
    "mu_ideal_l2",
    "noiseless_D_hat",
    "noiseless_N_hat",
    "noiseless_mu_hat",
    "noiseless_mu_abs_error",
    "noisy_D_reference",
    "denominator_clip_value",
    "mean_estimate",
    "mean_N_hat",
    "mean_D_hat",
    "mean_D_clipped",
    "bias_empirical",
    "variance_empirical",
    "mse_empirical",
    "var_times_B",
    "bias_floor_fit",
    "variance_slope_fit",
    "mse_fit_r2",
    "vd_bias_reduces_vs_unmitigated_context",
    "unmitigated_context_abs_bias",
    "sv_mitigated_context_abs_bias",
    "denominator_clip_fraction",
    "mixer_trotter_steps",
    "runtime_seconds",
]


@dataclass(frozen=True)
class VDSamplingConfig:
    b_values: tuple[int, ...] = B_VALUES
    repetitions: int = REPETITIONS
    noiseless_check_shots: int = NOISELESS_CHECK_SHOTS
    noisy_denominator_reference_shots: int = NOISY_DENOMINATOR_REFERENCE_SHOTS
    base_seed: int = BASE_SEED
    instance_id: str = PRIMARY_INSTANCE_ID


def main() -> int:
    t0 = time.time()
    rows, report = run_vd_sampling(VDSamplingConfig(), started_at=t0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CSV, rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(OUT_CSV)
    print(REPORT_PATH)
    return 0


def run_vd_sampling(
    config: VDSamplingConfig,
    started_at: float | None = None,
) -> tuple[list[dict], str]:
    t0 = time.time() if started_at is None else started_at
    model = _select_model(config.instance_id)
    inst = model.inst
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        inst,
    )
    circuits = build_vd_circuits(model)
    metadata = vd_circuit_metadata(circuits, inst.n)
    noiseless = noiseless_vd_crosscheck(
        circuits,
        inst,
        shots=config.noiseless_check_shots,
        seed=stable_seed(config.base_seed, inst.name, "noiseless_crosscheck"),
        mu_ideal=mu_ideal,
    )
    if (
        abs(noiseless["D_hat"] - 1.0) > NOISELESS_D_TOL
        or abs(noiseless["mu_hat"] - mu_ideal) > NOISELESS_MU_TOL
    ):
        raise RuntimeError(
            "VD noiseless cross-check failed: "
            f"D_hat={noiseless['D_hat']:.6g}, mu_hat={noiseless['mu_hat']:.6g}, "
            f"mu_ideal={mu_ideal:.6g}"
        )

    noisy_d_reference = noisy_denominator_reference(
        circuits,
        inst,
        shots=config.noisy_denominator_reference_shots,
        seed=stable_seed(config.base_seed, inst.name, "noisy_denominator_reference"),
    )
    denominator_clip_value = max(
        DENOMINATOR_CLIP_FRACTION * noisy_d_reference,
        DENOMINATOR_CLIP_MIN,
    )

    samples: list[dict] = []
    for b in config.b_values:
        for rep in range(config.repetitions):
            samples.append(
                noisy_vd_sample(
                    circuits,
                    inst,
                    b=int(b),
                    rep=int(rep),
                    base_seed=config.base_seed,
                    mu_ideal=mu_ideal,
                    denominator_clip_value=denominator_clip_value,
                )
            )

    context = load_step2_context()
    runtime_seconds = round(time.time() - t0, 3)
    rows = aggregate_samples(
        samples,
        config,
        inst,
        mu_ideal,
        noiseless,
        noisy_d_reference,
        denominator_clip_value,
        metadata,
        context,
        runtime_seconds,
    )
    report = render_report(rows, config, noiseless, noisy_d_reference, denominator_clip_value, metadata, context)
    return rows, report


def build_vd_circuits(model) -> dict[str, QuantumCircuit]:
    """Build numerator and denominator circuits for M=2 VD."""
    n = int(model.inst.n)
    total_qubits = 2 * n + 1
    ancilla = 2 * n
    prep = build_xy_qaoa_circuit(
        model,
        mixer_trotter_steps=MIXER_TROTTER_STEPS,
        decompose_for_aer=False,
    ).to_instruction()

    base = QuantumCircuit(total_qubits, total_qubits)
    base.append(prep, list(range(n)))
    base.append(prep, list(range(n, 2 * n)))
    base.h(ancilla)
    for qubit in range(n):
        base.cswap(ancilla, qubit, n + qubit)
    base.h(ancilla)

    denominator = base.copy(name=f"vd_m2_den_{model.inst.name}")
    denominator.measure(range(total_qubits), range(total_qubits))

    numerator = base.copy(name=f"vd_m2_num_{model.inst.name}")
    numerator.measure(range(total_qubits), range(total_qubits))

    return {
        "denominator": decompose_for_aer(denominator),
        "numerator": decompose_for_aer(numerator),
    }


def decompose_for_aer(circuit: QuantumCircuit) -> QuantumCircuit:
    return circuit.decompose(reps=10)


def vd_circuit_metadata(circuits: dict[str, QuantumCircuit], n_qubits: int) -> dict[str, float]:
    cswap_layer = QuantumCircuit(2 * n_qubits + 1)
    ancilla = 2 * n_qubits
    for qubit in range(n_qubits):
        cswap_layer.cswap(ancilla, qubit, n_qubits + qubit)
    cswap_decomposed = decompose_for_aer(cswap_layer)
    res_defs = resource_definitions(n_qubits)
    return {
        "vd_circuit_qubits": float(2 * n_qubits + 1),
        "cswap_cx_count": float(cswap_decomposed.count_ops().get("cx", 0)),
        "numerator_cx_count": float(circuits["numerator"].count_ops().get("cx", 0)),
        "denominator_cx_count": float(circuits["denominator"].count_ops().get("cx", 0)),
        "kappa_paired_sample_vd": float(res_defs["paired_sample"]["vd"]),
        "kappa_two_qubit_gate_proxy_vd": float(res_defs["two_qubit_gate_proxy"]["vd"]),
    }


def noiseless_vd_crosscheck(
    circuits: dict[str, QuantumCircuit],
    inst: qaoa.QAOAInstance,
    shots: int,
    seed: int,
    mu_ideal: float,
) -> dict[str, float]:
    d_counts = run_counts(circuits["denominator"], shots=shots, seed=seed, noisy=False)
    n_counts = run_counts(circuits["numerator"], shots=shots, seed=seed + 1, noisy=False)
    d_hat = estimate_denominator(d_counts, inst.n)
    n_hat = estimate_numerator(n_counts, inst)
    mu_hat = n_hat / max(d_hat, DENOMINATOR_CLIP_FRACTION)
    return {
        "shots": float(shots),
        "D_hat": float(d_hat),
        "N_hat": float(n_hat),
        "mu_hat": float(mu_hat),
        "mu_abs_error": float(abs(mu_hat - mu_ideal)),
    }


def noisy_denominator_reference(
    circuits: dict[str, QuantumCircuit],
    inst: qaoa.QAOAInstance,
    shots: int,
    seed: int,
) -> float:
    counts = run_counts(circuits["denominator"], shots=shots, seed=seed, noisy=True)
    return estimate_denominator(counts, inst.n)


def noisy_vd_sample(
    circuits: dict[str, QuantumCircuit],
    inst: qaoa.QAOAInstance,
    b: int,
    rep: int,
    base_seed: int,
    mu_ideal: float,
    denominator_clip_value: float,
) -> dict:
    den_seed = stable_seed(base_seed, inst.name, int(b), int(rep), "denominator")
    num_seed = stable_seed(base_seed, inst.name, int(b), int(rep), "numerator")
    d_counts = run_counts(circuits["denominator"], shots=b, seed=den_seed, noisy=True)
    n_counts = run_counts(circuits["numerator"], shots=b, seed=num_seed, noisy=True)
    d_hat = estimate_denominator(d_counts, inst.n)
    n_hat = estimate_numerator(n_counts, inst)
    d_clipped = max(d_hat, denominator_clip_value)
    estimate = n_hat / d_clipped
    error = estimate - mu_ideal
    return {
        "B": int(b),
        "rep": int(rep),
        "N_hat": float(n_hat),
        "D_hat": float(d_hat),
        "D_clipped": float(d_clipped),
        "estimate": float(estimate),
        "squared_error": float(error * error),
    }


def run_counts(circuit: QuantumCircuit, shots: int, seed: int, noisy: bool) -> dict[str, int]:
    simulator = build_aer_simulator(noisy=noisy)
    result = simulator.run(circuit, shots=int(shots), seed_simulator=int(seed)).result()
    counts = result.get_counts()
    return {str(key).replace(" ", ""): int(value) for key, value in counts.items()}


def estimate_denominator(counts: dict[str, int], n: int) -> float:
    total = float(sum(counts.values()))
    ancilla_index = 2 * n
    acc = 0.0
    for key, count in counts.items():
        bits_by_qubit = key[::-1]
        anc_bit = int(bits_by_qubit[ancilla_index])
        acc += z_from_bit(anc_bit) * float(count)
    return float(acc / total)


def estimate_numerator(counts: dict[str, int], inst: qaoa.QAOAInstance) -> float:
    total = float(sum(counts.values()))
    observable = observable_values(inst)
    ancilla_index = 2 * inst.n
    acc = 0.0
    for key, count in counts.items():
        bits_by_qubit = key[::-1]
        anc_bit = int(bits_by_qubit[ancilla_index])
        a_bits = bits_by_qubit[: inst.n]
        a_index = int(a_bits, 2)
        acc += z_from_bit(anc_bit) * float(observable[a_index]) * float(count)
    return float(acc / total)


def z_from_bit(bit: int) -> float:
    return 1.0 if int(bit) == 0 else -1.0


def observable_values(inst: qaoa.QAOAInstance) -> np.ndarray:
    diag = qaoa.cost_diagonal(inst)
    scale = float(np.max(np.abs(diag)))
    if scale == 0.0:
        raise ValueError("zero observable scale")
    return diag / scale


def aggregate_samples(
    samples: list[dict],
    config: VDSamplingConfig,
    inst: qaoa.QAOAInstance,
    mu_ideal: float,
    noiseless: dict[str, float],
    noisy_d_reference: float,
    denominator_clip_value: float,
    metadata: dict[str, float],
    context: dict[str, float],
    runtime_seconds: float,
) -> list[dict]:
    by_b: dict[int, list[dict]] = {}
    for sample in samples:
        by_b.setdefault(int(sample["B"]), []).append(sample)
    fit = fit_mse_law(by_b)
    rows: list[dict] = []
    unmit_bias = context.get("unmitigated_abs_bias", float("nan"))
    sv_bias = context.get("sv_mitigated_abs_bias", float("nan"))
    for b in sorted(by_b):
        group = by_b[b]
        estimates = np.asarray([sample["estimate"] for sample in group], dtype=np.float64)
        n_hats = np.asarray([sample["N_hat"] for sample in group], dtype=np.float64)
        d_hats = np.asarray([sample["D_hat"] for sample in group], dtype=np.float64)
        d_clips = np.asarray([sample["D_clipped"] for sample in group], dtype=np.float64)
        mse_values = np.asarray([sample["squared_error"] for sample in group], dtype=np.float64)
        variance = float(np.var(estimates, ddof=1)) if estimates.size > 1 else 0.0
        bias = float(np.mean(estimates) - mu_ideal)
        rows.append({
            "row_kind": "aggregate",
            "instance_id": config.instance_id,
            "method": "vd_m2_hadamard_swap",
            "B": int(b),
            "repetitions": int(config.repetitions),
            "num_shots_per_rep": int(b),
            "den_shots_per_rep": int(b),
            "raw_hadamard_calls_per_rep": int(2 * b),
            "resource_paired_sample": float(metadata["kappa_paired_sample_vd"] * b),
            "resource_two_qubit_gate_proxy": float(metadata["kappa_two_qubit_gate_proxy_vd"] * b),
            "kappa_paired_sample_vd": metadata["kappa_paired_sample_vd"],
            "kappa_two_qubit_gate_proxy_vd": metadata["kappa_two_qubit_gate_proxy_vd"],
            "n_qubits_system": int(inst.n),
            "vd_circuit_qubits": int(metadata["vd_circuit_qubits"]),
            "copies_M": M_COPIES,
            "cswap_cx_count": int(metadata["cswap_cx_count"]),
            "numerator_cx_count": int(metadata["numerator_cx_count"]),
            "denominator_cx_count": int(metadata["denominator_cx_count"]),
            "mu_ideal_l2": float(mu_ideal),
            "noiseless_D_hat": noiseless["D_hat"],
            "noiseless_N_hat": noiseless["N_hat"],
            "noiseless_mu_hat": noiseless["mu_hat"],
            "noiseless_mu_abs_error": noiseless["mu_abs_error"],
            "noisy_D_reference": float(noisy_d_reference),
            "denominator_clip_value": float(denominator_clip_value),
            "mean_estimate": float(np.mean(estimates)),
            "mean_N_hat": float(np.mean(n_hats)),
            "mean_D_hat": float(np.mean(d_hats)),
            "mean_D_clipped": float(np.mean(d_clips)),
            "bias_empirical": bias,
            "variance_empirical": variance,
            "mse_empirical": float(np.mean(mse_values)),
            "var_times_B": float(variance * b),
            "bias_floor_fit": fit["intercept"],
            "variance_slope_fit": fit["slope"],
            "mse_fit_r2": fit["r2"],
            "vd_bias_reduces_vs_unmitigated_context": bool(abs(bias) < unmit_bias),
            "unmitigated_context_abs_bias": unmit_bias,
            "sv_mitigated_context_abs_bias": sv_bias,
            "denominator_clip_fraction": DENOMINATOR_CLIP_FRACTION,
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


def load_step2_context(path: Path = STEP2_CSV) -> dict[str, float]:
    if not path.exists():
        return {
            "context_b": float("nan"),
            "unmitigated_abs_bias": float("nan"),
            "sv_mitigated_abs_bias": float("nan"),
            "sv_raw_postselect_abs_bias": float("nan"),
        }
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {}
    largest_b = max(int(row["B"]) for row in rows)

    def abs_bias(method: str) -> float:
        for row in rows:
            if row["method"] == method and int(row["B"]) == largest_b:
                return abs(float(row["bias_empirical"]))
        return float("nan")

    return {
        "context_b": float(largest_b),
        "unmitigated_abs_bias": abs_bias("unmitigated"),
        "sv_mitigated_abs_bias": abs_bias("sv_mitigated"),
        "sv_raw_postselect_abs_bias": abs_bias("sv_raw_postselect_diagnostic"),
    }


def render_report(
    rows: list[dict],
    config: VDSamplingConfig,
    noiseless: dict[str, float],
    noisy_d_reference: float,
    denominator_clip_value: float,
    metadata: dict[str, float],
    context: dict[str, float],
) -> str:
    largest_b = max(config.b_values)
    largest = _row_for(rows, largest_b)
    lines = [
        "# Level 2 Step 3 VD M=2",
        "",
        "Status: validacion EN FORMA, no matcheo de coeficientes de Nivel 1. Additive Phase B smoke/foundation layer; not a freeze and not an adjudication.",
        "",
        "## Scope",
        "",
        "- Method: VD M=2 via separate Hadamard/SWAP numerator and denominator circuits.",
        "- Instance: `g6_k2_c000` only, matching Level 2 Step 2.",
        "- Circuit depth: realistic Level 2 QAOA with `mixer_trotter_steps=1`.",
        "- Reference: noiseless Level 2 value of the same realistic circuit.",
        "- Not implemented here: M>2, folding, ensemble run, Level 2 E5/E7/E8/E12, hardware.",
        "",
        "## Noiseless Cross-Check",
        "",
        f"- Cross-check shots: `{config.noiseless_check_shots}`.",
        f"- `D_hat`: `{noiseless['D_hat']:.6g}`; expected `1` for a pure noiseless state.",
        f"- `N_hat`: `{noiseless['N_hat']:.6g}`.",
        f"- `N_hat / max(D_hat, {DENOMINATOR_CLIP_FRACTION})`: `{noiseless['mu_hat']:.6g}`.",
        f"- `mu_ideal_L2`: `{largest['mu_ideal_l2']:.6g}`.",
        f"- Absolute noiseless error: `{noiseless['mu_abs_error']:.6g}`.",
        "",
        "## Denominator Clip",
        "",
        f"- Noisy denominator reference shots: `{config.noisy_denominator_reference_shots}`.",
        f"- Noisy implementation denominator reference: `{noisy_d_reference:.6g}`.",
        f"- Clip rule: `max(D_hat, {DENOMINATOR_CLIP_FRACTION} * D_impl_reference)`.",
        f"- Clip value used: `{denominator_clip_value:.6g}`.",
        "- Rationale: this is the Level 2 implementation analogue of the Level 1 clipped quotient `max(D_hat, 0.5*D_M)`. The noisy c-SWAP implementation has its own population denominator, which is not the pure-state noiseless value 1.",
        "",
        "## Resource Accounting",
        "",
        f"- System qubits: `{largest['n_qubits_system']}`.",
        f"- VD circuit qubits: `{largest['vd_circuit_qubits']}` (`2n+1`).",
        f"- Numerator/denominator split: `B` numerator shots and `B` denominator shots per repetition.",
        f"- Raw Hadamard calls per repetition: `2B`.",
        f"- Decomposed c-SWAP layer CX count: `{int(metadata['cswap_cx_count'])}`.",
        f"- Numerator circuit CX count: `{int(metadata['numerator_cx_count'])}`.",
        f"- Denominator circuit CX count: `{int(metadata['denominator_cx_count'])}`.",
        f"- Paired-sample kappa from E7 sensitivity: `{metadata['kappa_paired_sample_vd']:.6g}`.",
        f"- Two-qubit-gate-proxy kappa from E7 sensitivity: `{metadata['kappa_two_qubit_gate_proxy_vd']:.6g}`.",
        "",
        "## Shape Summary",
        "",
        "| B | bias | variance | MSE | var*B | mean N | mean D | mean clipped D | R paired | R two-qubit proxy |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['B']} | {row['bias_empirical']:.6g} "
            f"| {row['variance_empirical']:.6g} | {row['mse_empirical']:.6g} "
            f"| {row['var_times_B']:.6g} | {row['mean_N_hat']:.6g} "
            f"| {row['mean_D_hat']:.6g} | {row['mean_D_clipped']:.6g} "
            f"| {row['resource_paired_sample']:.6g} | {row['resource_two_qubit_gate_proxy']:.6g} |"
        )
    lines.extend([
        "",
        "## Step 2 Context",
        "",
        f"- Step 2 context B: `{context.get('context_b', float('nan')):.6g}`.",
        f"- Unmitigated abs bias from Step 2: `{context.get('unmitigated_abs_bias', float('nan')):.6g}`.",
        f"- SV mitigated abs bias from Step 2: `{context.get('sv_mitigated_abs_bias', float('nan')):.6g}`.",
        f"- Raw SV postselection diagnostic abs bias from Step 2: `{context.get('sv_raw_postselect_abs_bias', float('nan')):.6g}`.",
        "",
        "## Descriptive Conclusion",
        "",
    ])
    reduction_text = (
        "VD reduces the absolute bias relative to the Step 2 unmitigated context "
        if largest["vd_bias_reduces_vs_unmitigated_context"]
        else "VD does not reduce the absolute bias relative to the Step 2 unmitigated context "
    )
    lines.append(
        f"At B={largest_b}, VD has absolute bias `{abs(float(largest['bias_empirical'])):.6g}`. "
        f"{reduction_text}(`{context.get('unmitigated_abs_bias', float('nan')):.6g}`). "
        "The noise of the two-copy interferometric VD circuit is included, so this is a "
        "Level 2 form check rather than a Level 1 coefficient recovery claim. With only "
        f"`{config.repetitions}` repetitions, variance estimates and `var*B` are expected "
        "to be noisy; the high-power multi-method ensemble run is intentionally deferred."
    )
    return "\n".join(lines) + "\n"


def _row_for(rows: Iterable[dict], b: int) -> dict:
    for row in rows:
        if int(row["B"]) == int(b):
            return row
    raise KeyError(b)


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
