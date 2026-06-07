"""Circuit construction and transpilation for Level 3 Stage 1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, transpile

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from experiments._common import frozen_models
from level2.circuits import (
    MIXER_TROTTER_STEPS,
    build_xy_qaoa_circuit,
    observable_expectation,
    simulate_noiseless_statevector,
)


@dataclass(frozen=True)
class CircuitBundle:
    instance_id: str
    n: int
    sector_weight: int
    mu_ideal_noiseless_l2: float
    observable_values_level1_order: tuple[float, ...]
    logical_circuits: tuple[QuantumCircuit, ...]
    labels: tuple[str, ...]


@dataclass(frozen=True)
class TranspiledBundle:
    instance_id: str
    n: int
    sector_weight: int
    mu_ideal_noiseless_l2: float
    observable_values_level1_order: tuple[float, ...]
    circuits: tuple[QuantumCircuit, ...]
    labels: tuple[str, ...]
    physical_qubits: tuple[int, ...]
    transpile_metadata: dict[str, Any]


def build_stage1_circuits(instance_id: str) -> CircuitBundle:
    """Build the QAOA Z-measurement circuit and tensorized readout calibration."""

    model = select_model(instance_id)
    n = int(model.inst.n)
    qaoa = build_xy_qaoa_circuit(
        model,
        mixer_trotter_steps=MIXER_TROTTER_STEPS,
        decompose_for_aer=False,
    )
    qaoa.name = f"level3_{instance_id}_qaoa_z"
    _measure_all_to_c(qaoa, n)
    qaoa.metadata = {
        **dict(qaoa.metadata or {}),
        "level3_role": "qaoa_z",
        "instance_id": instance_id,
        "sector_weight": int(model.inst.weight),
    }

    cal0 = calibration_circuit(n, prepared_bit=0)
    cal1 = calibration_circuit(n, prepared_bit=1)
    mu_ideal = observable_expectation(
        simulate_noiseless_statevector(
            model,
            mixer_trotter_steps=MIXER_TROTTER_STEPS,
        ),
        model.inst,
    )
    return CircuitBundle(
        instance_id=instance_id,
        n=n,
        sector_weight=int(model.inst.weight),
        mu_ideal_noiseless_l2=float(mu_ideal),
        observable_values_level1_order=tuple(float(x) for x in _observable_values(model)),
        logical_circuits=(qaoa, cal0, cal1),
        labels=("qaoa_z", "readout_calib_0", "readout_calib_1"),
    )


def transpile_stage1_bundle(
    bundle: CircuitBundle,
    backend: Any,
    optimization_level: int,
    seed_transpiler: int,
) -> TranspiledBundle:
    """Transpile QAOA first, then pin calibration to the same physical qubits."""

    qaoa = transpile(
        bundle.logical_circuits[0],
        backend=backend,
        optimization_level=int(optimization_level),
        seed_transpiler=int(seed_transpiler),
    )
    physical_qubits = tuple(_final_physical_layout(qaoa, bundle.n))
    calibration = tuple(
        transpile(
            circuit,
            backend=backend,
            initial_layout=list(physical_qubits),
            optimization_level=int(optimization_level),
            seed_transpiler=int(seed_transpiler),
        )
        for circuit in bundle.logical_circuits[1:]
    )
    circuits = (qaoa, *calibration)
    return TranspiledBundle(
        instance_id=bundle.instance_id,
        n=bundle.n,
        sector_weight=bundle.sector_weight,
        mu_ideal_noiseless_l2=bundle.mu_ideal_noiseless_l2,
        observable_values_level1_order=bundle.observable_values_level1_order,
        circuits=circuits,
        labels=bundle.labels,
        physical_qubits=physical_qubits,
        transpile_metadata={
            "optimization_level": int(optimization_level),
            "seed_transpiler": int(seed_transpiler),
            "logical_to_physical": {
                str(logical): int(physical)
                for logical, physical in enumerate(physical_qubits)
            },
            "circuit_summaries": [
                circuit_summary(label, circuit)
                for label, circuit in zip(bundle.labels, circuits, strict=True)
            ],
        },
    )


def calibration_circuit(n: int, prepared_bit: int) -> QuantumCircuit:
    if prepared_bit not in (0, 1):
        raise ValueError("prepared_bit must be 0 or 1")
    circuit = QuantumCircuit(n, n, name=f"level3_readout_calib_{prepared_bit}")
    if prepared_bit == 1:
        circuit.x(range(n))
    circuit.measure(range(n), range(n))
    circuit.metadata = {
        "level3_role": "readout_calibration",
        "prepared_bit": int(prepared_bit),
    }
    return circuit


def circuit_summary(label: str, circuit: QuantumCircuit) -> dict[str, Any]:
    return {
        "label": label,
        "name": circuit.name,
        "num_qubits": int(circuit.num_qubits),
        "num_clbits": int(circuit.num_clbits),
        "depth": int(circuit.depth()),
        "size": int(circuit.size()),
        "count_ops": {str(key): int(value) for key, value in circuit.count_ops().items()},
    }


def select_model(instance_id: str):
    for model in frozen_models():
        if model.inst.name == instance_id:
            return model
    raise ValueError(f"instance not found: {instance_id}")


def _measure_all_to_c(circuit: QuantumCircuit, n: int) -> None:
    if circuit.num_clbits:
        raise ValueError("expected an unmeasured circuit")
    creg = ClassicalRegister(n, "c")
    circuit.add_register(creg)
    circuit.measure(range(n), range(n))


def _final_physical_layout(circuit: QuantumCircuit, n: int) -> list[int]:
    layout = getattr(circuit, "layout", None)
    if layout is None:
        return list(range(n))
    if hasattr(layout, "final_index_layout"):
        final_layout = layout.final_index_layout()
        if final_layout is not None and len(final_layout) >= n:
            return [int(item) for item in final_layout[:n]]
    initial = getattr(layout, "initial_layout", None)
    if initial is not None and hasattr(initial, "get_virtual_bits"):
        by_virtual = initial.get_virtual_bits()
        out: list[int | None] = [None] * n
        for qbit, physical in by_virtual.items():
            index = _qubit_index(qbit)
            if index is not None and index < n:
                out[index] = int(physical)
        if all(item is not None for item in out):
            return [int(item) for item in out if item is not None]
    return list(range(n))


def _qubit_index(qbit: Any) -> int | None:
    index = getattr(qbit, "index", None)
    if index is not None:
        return int(index)
    private_index = getattr(qbit, "_index", None)
    if private_index is not None:
        return int(private_index)
    return None


def observable_values_for_instance(instance_id: str) -> np.ndarray:
    model = select_model(instance_id)
    return _observable_values(model)


def _observable_values(model) -> np.ndarray:
    diag = np.real(np.diag(model.observable)).astype(np.float64)
    scale = float(np.max(np.abs(diag)))
    if scale == 0.0:
        raise ValueError("zero observable scale")
    return diag / scale
