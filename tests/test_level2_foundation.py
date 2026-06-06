from pathlib import Path

import numpy as np

from experiments._common import frozen_models
from level2 import circuits
from level2 import noise_model


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "level2" / "level2_foundation_report.md"
CONFIG_PATH = REPO_ROOT / "level2" / "config_level2.yaml"


def test_level2_report_and_config_are_present():
    assert CONFIG_PATH.exists()
    assert REPORT_PATH.exists()
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "Status: Level 2 foundation" in text
    assert "does not implement noisy sampling" in text


def test_level2_bit_reversal_roundtrip_is_exact():
    for n in (1, 2, 3, 6, 8):
        state = np.arange(2**n, dtype=np.float64).astype(np.complex128)
        qiskit_state = circuits.level1_to_qiskit_state(state, n)
        recovered = circuits.qiskit_to_level1_state(qiskit_state, n)
        assert np.array_equal(recovered, state)


def test_level2_all_instances_are_in_sector_and_gap_is_informative():
    rows = circuits.foundation_diagnostics(engine="statevector")
    assert len(rows) == 10
    for row in rows:
        assert row["in_sector_pass"] is True
        assert row["sector_leakage"] <= circuits.SECTOR_LEAKAGE_TOL
        assert row["gap_trotter_status"] == "informative_only"
        assert row["trotter_gap_abs"] >= 0.0


def test_level2_realistic_depth_is_default_and_high_fidelity_is_optional():
    assert circuits.MIXER_TROTTER_STEPS == 1
    assert circuits.HIGH_FIDELITY_TROTTER_STEPS > circuits.MIXER_TROTTER_STEPS


def test_level2_noiseless_statevector_is_deterministic():
    model = frozen_models()[0]
    state_a = circuits.simulate_noiseless_statevector(model, engine="statevector")
    state_b = circuits.simulate_noiseless_statevector(model, engine="statevector")
    assert np.array_equal(state_a, state_b)


def test_level2_aer_statevector_matches_qiskit_statevector_for_first_instance():
    model = frozen_models()[0]
    state_qiskit = circuits.simulate_noiseless_statevector(model, engine="statevector")
    state_aer = circuits.simulate_noiseless_statevector(model, engine="aer")
    overlap = np.vdot(state_qiskit, state_aer)
    assert abs(overlap) > 1.0 - 1e-10
    assert circuits.sector_leakage(state_aer, model.inst) <= circuits.SECTOR_LEAKAGE_TOL
    assert abs(
        circuits.observable_expectation(state_aer, model.inst)
        - circuits.observable_expectation(state_qiskit, model.inst)
    ) <= 1e-10


def test_level2_noise_model_loads_with_readout_error():
    summary = noise_model.noise_model_summary()
    assert summary["backend_label"] == "AerSyntheticThermalReadoutV1"
    assert summary["is_ideal"] is False
    assert summary["has_readout_error"] is True
    assert {"u", "cx", "measure"}.issubset(set(summary["noise_instructions"]))
    simulator = noise_model.build_aer_simulator(noisy=True)
    assert simulator is not None
