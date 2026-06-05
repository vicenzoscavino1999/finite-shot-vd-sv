"""Pinned Level 2 Aer noise model.

The installed project extra provides Qiskit/Aer but no IBM fake-provider package.
For this foundation step we therefore pin a reproducible Aer-native thermal,
depolarizing, and readout snapshot in ``config_level2.yaml``. Later Level 2
experiments can swap this for an archived FakeBackend artifact without touching
Level 1 frozen files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, thermal_relaxation_error


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(__file__).resolve().with_name("config_level2.yaml")


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_noise_model(config: dict[str, Any] | None = None) -> NoiseModel:
    cfg = load_config() if config is None else config
    noise_cfg = cfg["noise_model"]

    t1 = float(noise_cfg["t1_ns"])
    t2 = float(noise_cfg["t2_ns"])
    gate_times = noise_cfg["gate_times_ns"]
    depol = noise_cfg["depolarizing_probabilities"]

    single = thermal_relaxation_error(t1, t2, float(gate_times["u"]))
    single = single.compose(depolarizing_error(float(depol["u"]), 1))

    cx_thermal = thermal_relaxation_error(t1, t2, float(gate_times["cx"]))
    two_qubit = cx_thermal.tensor(cx_thermal)
    two_qubit = two_qubit.compose(depolarizing_error(float(depol["cx"]), 2))

    readout = ReadoutError(noise_cfg["readout_error_matrix"])

    model = NoiseModel()
    model.add_all_qubit_quantum_error(single, ["u"])
    model.add_all_qubit_quantum_error(two_qubit, ["cx"])
    model.add_all_qubit_readout_error(readout)
    return model


def build_aer_simulator(config: dict[str, Any] | None = None, noisy: bool = True) -> AerSimulator:
    cfg = load_config() if config is None else config
    seed = int(cfg["noise_model"]["seed_simulator"])
    if noisy:
        return AerSimulator(noise_model=build_noise_model(cfg), seed_simulator=seed)
    return AerSimulator(method="statevector", seed_simulator=seed)


def noise_model_summary(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config() if config is None else config
    model = build_noise_model(cfg)
    noise_cfg = cfg["noise_model"]
    return {
        "backend_label": noise_cfg["backend_label"],
        "source": noise_cfg["source"],
        "seed_simulator": int(noise_cfg["seed_simulator"]),
        "basis_gates": list(model.basis_gates),
        "noise_instructions": sorted(str(item) for item in model.noise_instructions),
        "noise_qubits": list(model.noise_qubits),
        "is_ideal": bool(model.is_ideal()),
        "has_readout_error": "measure" in {str(item) for item in model.noise_instructions},
    }


if __name__ == "__main__":
    summary = noise_model_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")

