"""Level 3 Stage 3 hardware pipeline: VD + B sweep + calibration epochs."""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, transpile

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from experiments.e7_resource_observable_sensitivity import resource_definitions
from level2.circuits import MIXER_TROTTER_STEPS, observable_expectation, simulate_noiseless_statevector
from level2.vd import build_vd_circuits
from level3.archive import write_archive
from level3.budget import BudgetExceeded, estimate_budget, render_budget_estimate
from level3.circuits import (
    build_stage1_circuits,
    calibration_circuit,
    circuit_summary,
    layout_candidate_from_physical_qubits,
    select_model,
    _final_physical_layout,
)
from level3.config import ARCHIVE_DIR, DEFAULT_BACKEND_NAME, DEFAULT_SEED_TRANSPILE
from level3.submit import backend_metadata, backend_status, load_ibm_backend, parse_initial_layout


B_GRID = (512, 1024, 2048, 4096, 8192)
DEFAULT_B_MAX = 8192
DEFAULT_TARGET_QPU_SECONDS = 540.0
DEFAULT_HARD_QPU_SECONDS = 600.0
DEFAULT_MAX_EPOCHS = 12
DEFAULT_OPTIMIZATION_LEVEL = 3
DEFAULT_STAGE3_SHOT_CAP = 5 * DEFAULT_B_MAX


@dataclass(frozen=True)
class Stage3Config:
    instance_id: str = "g6_k2_c000"
    backend_name: str = DEFAULT_BACKEND_NAME
    optimization_level: int = DEFAULT_OPTIMIZATION_LEVEL
    seed_transpiler: int = DEFAULT_SEED_TRANSPILE
    b_max: int = DEFAULT_B_MAX
    b_grid: tuple[int, ...] = B_GRID
    max_total_shots_per_epoch: int = DEFAULT_STAGE3_SHOT_CAP
    target_qpu_seconds: float = DEFAULT_TARGET_QPU_SECONDS
    hard_qpu_seconds: float = DEFAULT_HARD_QPU_SECONDS
    max_epochs: int = DEFAULT_MAX_EPOCHS
    archive_dir: Path = ARCHIVE_DIR
    vd_initial_layout: tuple[int, ...] | None = None


@dataclass(frozen=True)
class Stage3TranspiledBundle:
    instance_id: str
    n: int
    vd_qubits: int
    sector_weight: int
    mu_ideal_noiseless_l2: float
    observable_values_level1_order: tuple[float, ...]
    labels: tuple[str, ...]
    circuits: tuple[QuantumCircuit, ...]
    calibration_physical_qubits: tuple[int, ...]
    qaoa_logical_to_calibration_index: tuple[int, ...]
    vd_numerator_logical_to_calibration_index: tuple[int, ...]
    vd_denominator_logical_to_calibration_index: tuple[int, ...]
    metadata: dict[str, Any]


def build_stage3_bundle(config: Stage3Config, backend: Any) -> Stage3TranspiledBundle:
    model = select_model(config.instance_id)
    n = int(model.inst.n)
    vd_total = 2 * n + 1
    stage1 = build_stage1_circuits(config.instance_id)
    vd_logical = build_vd_circuits(model)

    vd_initial = (
        layout_candidate_from_physical_qubits(backend, config.vd_initial_layout)
        if config.vd_initial_layout is not None
        else None
    )
    vd_den = transpile(
        vd_logical["denominator"],
        backend=backend,
        initial_layout=list(vd_initial.physical_qubits) if vd_initial else None,
        optimization_level=int(config.optimization_level),
        seed_transpiler=int(config.seed_transpiler),
    )
    vd_physical = tuple(_final_physical_layout(vd_den, vd_total))
    vd_num = transpile(
        vd_logical["numerator"],
        backend=backend,
        initial_layout=list(vd_physical),
        optimization_level=int(config.optimization_level),
        seed_transpiler=int(config.seed_transpiler),
    )
    vd_num_physical = tuple(_final_physical_layout(vd_num, vd_total))
    qaoa_z = transpile(
        stage1.logical_circuits[0],
        backend=backend,
        initial_layout=list(vd_physical[:n]),
        optimization_level=int(config.optimization_level),
        seed_transpiler=int(config.seed_transpiler),
    )
    qaoa_physical = tuple(_final_physical_layout(qaoa_z, n))

    calibration_physical = _ordered_union(vd_physical, vd_num_physical, qaoa_physical)
    cal0 = transpile(
        calibration_circuit(len(calibration_physical), prepared_bit=0),
        backend=backend,
        initial_layout=list(calibration_physical),
        optimization_level=int(config.optimization_level),
        seed_transpiler=int(config.seed_transpiler),
    )
    cal1 = transpile(
        calibration_circuit(len(calibration_physical), prepared_bit=1),
        backend=backend,
        initial_layout=list(calibration_physical),
        optimization_level=int(config.optimization_level),
        seed_transpiler=int(config.seed_transpiler),
    )

    physical_to_cal = {int(q): idx for idx, q in enumerate(calibration_physical)}
    qaoa_to_cal = tuple(physical_to_cal[int(q)] for q in qaoa_physical)
    vd_num_to_cal = tuple(physical_to_cal[int(q)] for q in vd_num_physical)
    vd_den_to_cal = tuple(physical_to_cal[int(q)] for q in vd_physical)
    resources = resource_definitions(n)
    labels = (
        "readout_calib_0",
        "qaoa_z",
        "vd_m2_numerator",
        "vd_m2_denominator",
        "readout_calib_1",
    )
    circuits = (cal0, qaoa_z, vd_num, vd_den, cal1)
    for label, circuit in zip(labels, circuits, strict=True):
        circuit.metadata = {
            **dict(circuit.metadata or {}),
            "level3_stage3_label": label,
        }
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(model, mixer_trotter_steps=MIXER_TROTTER_STEPS),
        model.inst,
    )
    return Stage3TranspiledBundle(
        instance_id=config.instance_id,
        n=n,
        vd_qubits=vd_total,
        sector_weight=int(model.inst.weight),
        mu_ideal_noiseless_l2=float(mu_ideal),
        observable_values_level1_order=stage1.observable_values_level1_order,
        labels=labels,
        circuits=circuits,
        calibration_physical_qubits=calibration_physical,
        qaoa_logical_to_calibration_index=qaoa_to_cal,
        vd_numerator_logical_to_calibration_index=vd_num_to_cal,
        vd_denominator_logical_to_calibration_index=vd_den_to_cal,
        metadata={
            "optimization_level": int(config.optimization_level),
            "seed_transpiler": int(config.seed_transpiler),
            "initial_layout_strategy": "user_initial_layout" if vd_initial else "transpiler_default",
            "selected_vd_initial_layout": (
                [int(q) for q in vd_initial.physical_qubits] if vd_initial else None
            ),
            "selected_vd_initial_layout_score": float(vd_initial.score) if vd_initial else None,
            "selected_vd_initial_layout_readout_errors": (
                vd_initial.readout_errors if vd_initial else None
            ),
            "selected_vd_initial_layout_twoq_edges": (
                list(vd_initial.twoq_edges) if vd_initial else None
            ),
            "calibration_physical_qubits": [int(q) for q in calibration_physical],
            "qaoa_logical_to_physical": {
                str(i): int(q) for i, q in enumerate(qaoa_physical)
            },
            "vd_numerator_logical_to_physical": {
                str(i): int(q) for i, q in enumerate(vd_num_physical)
            },
            "vd_denominator_logical_to_physical": {
                str(i): int(q) for i, q in enumerate(vd_physical)
            },
            "qaoa_logical_to_calibration_index": {
                str(i): int(idx) for i, idx in enumerate(qaoa_to_cal)
            },
            "vd_numerator_logical_to_calibration_index": {
                str(i): int(idx) for i, idx in enumerate(vd_num_to_cal)
            },
            "vd_denominator_logical_to_calibration_index": {
                str(i): int(idx) for i, idx in enumerate(vd_den_to_cal)
            },
            "resource_kappas": {
                "paired_sample": {
                    "unmitigated": float(resources["paired_sample"]["unmitigated"]),
                    "sv": float(resources["paired_sample"]["sv"]),
                    "vd": float(resources["paired_sample"]["vd"]),
                },
                "two_qubit_gate_proxy": {
                    "unmitigated": float(resources["two_qubit_gate_proxy"]["unmitigated"]),
                    "sv": float(resources["two_qubit_gate_proxy"]["sv"]),
                    "vd": float(resources["two_qubit_gate_proxy"]["vd"]),
                },
            },
            "circuit_summaries": [
                circuit_summary(label, circuit)
                for label, circuit in zip(labels, circuits, strict=True)
            ],
        },
    )


def dry_run(config: Stage3Config, backend: Any | None = None) -> dict[str, Any]:
    backend = load_ibm_backend_for_stage3(config) if backend is None else backend
    bundle = build_stage3_bundle(config, backend)
    estimate = estimate_budget(
        [circuit.depth() for circuit in bundle.circuits],
        shots_per_circuit=config.b_max,
        max_total_shots=config.max_total_shots_per_epoch,
        near_cap_fraction=0.85,
    )
    if estimate.total_shots > estimate.max_total_shots:
        raise BudgetExceeded(
            f"stage3 epoch shots exceed cap: {estimate.total_shots} > {estimate.max_total_shots}"
        )
    return {
        "backend_name": getattr(backend, "name", config.backend_name),
        "backend_status": backend_status(backend),
        "bundle": bundle,
        "budget": estimate,
    }


def submit_epoch(
    config: Stage3Config,
    backend: Any,
    epoch_index: int,
    bundle: Stage3TranspiledBundle | None = None,
) -> tuple[Path, dict[str, Any]]:
    from qiskit_ibm_runtime import SamplerV2

    bundle = build_stage3_bundle(config, backend) if bundle is None else bundle
    estimate = estimate_budget(
        [circuit.depth() for circuit in bundle.circuits],
        shots_per_circuit=config.b_max,
        max_total_shots=config.max_total_shots_per_epoch,
        near_cap_fraction=0.85,
    )
    if estimate.total_shots > estimate.max_total_shots:
        raise BudgetExceeded(
            f"stage3 epoch shots exceed cap: {estimate.total_shots} > {estimate.max_total_shots}"
        )
    sampler = SamplerV2(mode=backend)
    job = sampler.run(list(bundle.circuits), shots=int(config.b_max))
    result = job.result()
    job_id = job.job_id() if hasattr(job, "job_id") else str(job)
    metrics = _job_metrics(job)
    payload = archive_payload(
        config=config,
        backend=backend,
        bundle=bundle,
        result=result,
        epoch_index=epoch_index,
        job_id=job_id,
        budget_estimate=estimate,
        metrics=metrics,
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_name = (
        f"stage3_{config.instance_id}_{config.backend_name}_epoch{epoch_index:02d}_"
        f"{stamp}_{job_id}.json.gz"
    )
    archive_path = Path(config.archive_dir) / archive_name
    write_archive(archive_path, payload)
    return archive_path, payload


def run_adaptive(config: Stage3Config) -> list[Path]:
    backend = load_ibm_backend_for_stage3(config)
    dry = dry_run(config, backend=backend)
    print(
        "STAGE3_REAL_BACKEND_DRY_RUN "
        f"backend={dry['backend_name']} "
        f"operational={str(dry['backend_status'].get('operational')).lower()} "
        f"pending_jobs={dry['backend_status'].get('pending_jobs')} "
        f"status_msg={dry['backend_status'].get('status_msg')}"
    )
    print(render_budget_estimate(dry["budget"]))
    print(json.dumps(dry["bundle"].metadata, indent=2, sort_keys=True))

    archives: list[Path] = []
    accumulated = 0.0
    predicted_next = max(float(dry["budget"].estimated_qpu_seconds), 1.0)
    epoch = 1
    bundle = dry["bundle"]
    while epoch <= int(config.max_epochs):
        if accumulated > 0.0:
            if accumulated + predicted_next > float(config.target_qpu_seconds):
                break
            if accumulated + predicted_next >= float(config.hard_qpu_seconds):
                break
        archive_path, payload = submit_epoch(config, backend, epoch, bundle=bundle)
        archives.append(archive_path)
        usage = quantum_seconds_from_payload(payload)
        accumulated += usage
        predicted_next = max(usage, float(dry["budget"].estimated_qpu_seconds), 1.0)
        print(
            "STAGE3_EPOCH_DONE "
            f"epoch={epoch} "
            f"archive={archive_path} "
            f"job_id={payload['submission']['job_id']} "
            f"quantum_seconds={usage:.6g} "
            f"accumulated_quantum_seconds={accumulated:.6g}"
        )
        if accumulated + predicted_next > float(config.target_qpu_seconds):
            break
        if accumulated + predicted_next >= float(config.hard_qpu_seconds):
            break
        epoch += 1
    print(
        "STAGE3_ADAPTIVE_DONE "
        f"epochs={len(archives)} "
        f"accumulated_quantum_seconds={accumulated:.6g} "
        f"target_qpu_seconds={config.target_qpu_seconds:.6g} "
        f"hard_qpu_seconds={config.hard_qpu_seconds:.6g}"
    )
    return archives


def archive_payload(
    config: Stage3Config,
    backend: Any,
    bundle: Stage3TranspiledBundle,
    result: Any,
    epoch_index: int,
    job_id: str,
    budget_estimate: Any,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    circuit_data = sampler_circuit_data(result, bundle.labels)
    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "created_at_utc": created,
        "backend": {
            "name": config.backend_name,
            "metadata": backend_metadata(backend),
        },
        "submission": {
            "mode": "ibm_runtime_sampler_v2_stage3",
            "job_id": job_id,
            "sampler": "SamplerV2",
            "epoch_index": int(epoch_index),
            "metrics": metrics,
        },
        "experiment": {
            "stage": "level3_stage3_full_p7p9",
            "instance_id": bundle.instance_id,
            "n": int(bundle.n),
            "vd_qubits": int(bundle.vd_qubits),
            "sector_weight": int(bundle.sector_weight),
            "mu_ideal_noiseless_l2": float(bundle.mu_ideal_noiseless_l2),
            "mixer_trotter_steps": int(MIXER_TROTTER_STEPS),
            "b_max": int(config.b_max),
            "b_grid": [int(b) for b in config.b_grid],
            "observable_values_level1_order": [
                float(value) for value in bundle.observable_values_level1_order
            ],
        },
        "shots": {
            "shots_per_circuit": int(config.b_max),
            "total_shots": int(budget_estimate.total_shots),
            "max_total_shots_per_epoch": int(config.max_total_shots_per_epoch),
        },
        "budget": {
            "estimated_qpu_seconds": float(budget_estimate.estimated_qpu_seconds),
            "max_circuit_depth": int(budget_estimate.max_circuit_depth),
            "circuit_count": int(budget_estimate.circuit_count),
        },
        "transpile": bundle.metadata,
        "provenance": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "qiskit": _version("qiskit"),
            "qiskit_aer": _version("qiskit_aer"),
            "qiskit_ibm_runtime": _version("qiskit_ibm_runtime"),
        },
        "circuits": [
            {
                "label": label,
                "role": role_for_label(label),
                "shots": int(sum(circuit_data[label]["counts"].values())),
                "counts": circuit_data[label]["counts"],
                "bitstrings": circuit_data[label]["bitstrings"],
            }
            for label in bundle.labels
        ],
    }


def sampler_circuit_data(result: Any, labels: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for label, pub_result in zip(labels, result, strict=True):
        data = pub_result.data
        bit_arrays = list(data.values())
        if len(bit_arrays) != 1:
            raise ValueError(f"expected one classical register, got {list(data.keys())}")
        bit_array = bit_arrays[0]
        counts = {str(k).replace(" ", ""): int(v) for k, v in bit_array.get_counts().items()}
        bitstrings = [str(item).replace(" ", "") for item in bit_array.get_bitstrings()]
        out[label] = {
            "counts": dict(sorted(counts.items())),
            "bitstrings": bitstrings,
        }
    return out


def load_ibm_backend_for_stage3(config: Stage3Config) -> Any:
    class _Config:
        backend_name = config.backend_name

    return load_ibm_backend(_Config())


def quantum_seconds_from_payload(payload: dict[str, Any]) -> float:
    metrics = payload.get("submission", {}).get("metrics", {})
    usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
    for key in ("quantum_seconds", "seconds"):
        if key in usage:
            return float(usage[key])
    bss = metrics.get("bss", {}) if isinstance(metrics, dict) else {}
    if "seconds" in bss:
        return float(bss["seconds"])
    usage_est = payload.get("submission", {}).get("usage_estimation", {})
    if isinstance(usage_est, dict) and "quantum_seconds" in usage_est:
        return float(usage_est["quantum_seconds"])
    return float(payload.get("budget", {}).get("estimated_qpu_seconds", 0.0))


def role_for_label(label: str) -> str:
    if label.startswith("readout_calib_"):
        return "readout_calibration"
    if label == "qaoa_z":
        return "qaoa_z"
    if label.startswith("vd_m2_"):
        return "vd_m2_hadamard_swap"
    return label


def _job_metrics(job: Any) -> dict[str, Any]:
    try:
        metrics = job.metrics()
    except Exception:
        metrics = {}
    try:
        usage_estimation = getattr(job, "usage_estimation", None)
    except Exception:
        usage_estimation = None
    if usage_estimation is not None:
        metrics = {**metrics, "usage_estimation": usage_estimation}
    return _jsonable(metrics)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            return str(value)
        return value
    return str(value)


def _ordered_union(*items: tuple[int, ...]) -> tuple[int, ...]:
    out: list[int] = []
    seen: set[int] = set()
    for seq in items:
        for item in seq:
            value = int(item)
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
    return tuple(out)


def _version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return str(getattr(module, "__version__", "unknown"))


def _parse_b_grid(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def build_config_from_args(args: argparse.Namespace) -> Stage3Config:
    return Stage3Config(
        instance_id=args.instance_id,
        backend_name=args.backend,
        optimization_level=args.optimization_level,
        seed_transpiler=args.seed_transpiler,
        b_max=args.b_max,
        b_grid=_parse_b_grid(args.b_grid),
        max_total_shots_per_epoch=args.max_total_shots_per_epoch,
        target_qpu_seconds=args.target_qpu_seconds,
        hard_qpu_seconds=args.hard_qpu_seconds,
        max_epochs=args.max_epochs,
        archive_dir=args.archive_dir,
        vd_initial_layout=parse_initial_layout(args.vd_initial_layout),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-id", default=Stage3Config().instance_id)
    parser.add_argument("--backend", default=Stage3Config().backend_name)
    parser.add_argument("--optimization-level", type=int, default=Stage3Config().optimization_level)
    parser.add_argument("--seed-transpiler", type=int, default=Stage3Config().seed_transpiler)
    parser.add_argument("--b-max", type=int, default=Stage3Config().b_max)
    parser.add_argument("--b-grid", default=",".join(str(x) for x in B_GRID))
    parser.add_argument(
        "--max-total-shots-per-epoch",
        type=int,
        default=Stage3Config().max_total_shots_per_epoch,
    )
    parser.add_argument("--target-qpu-seconds", type=float, default=Stage3Config().target_qpu_seconds)
    parser.add_argument("--hard-qpu-seconds", type=float, default=Stage3Config().hard_qpu_seconds)
    parser.add_argument("--max-epochs", type=int, default=Stage3Config().max_epochs)
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVE_DIR)
    parser.add_argument("--vd-initial-layout")
    parser.add_argument("--real-backend-dry-run", action="store_true")
    parser.add_argument("--submit-adaptive", action="store_true")
    args = parser.parse_args(argv)

    config = build_config_from_args(args)
    if args.real_backend_dry_run:
        result = dry_run(config)
        print(
            "STAGE3_REAL_BACKEND_DRY_RUN "
            f"backend={result['backend_name']} "
            f"operational={str(result['backend_status'].get('operational')).lower()} "
            f"pending_jobs={result['backend_status'].get('pending_jobs')} "
            f"status_msg={result['backend_status'].get('status_msg')}"
        )
        print(render_budget_estimate(result["budget"]))
        print(json.dumps(result["bundle"].metadata, indent=2, sort_keys=True))
        return 0
    if args.submit_adaptive:
        archives = run_adaptive(config)
        for archive in archives:
            print(f"ARCHIVE_WRITTEN {archive}")
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
