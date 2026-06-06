"""Level 2 Qiskit foundation circuits and noiseless diagnostics.

The Level 2 circuit is a Trotterized gate-level implementation of the frozen
Level 1 XY-mixer QAOA instance. Its ideal reference is its own noiseless
statevector. The dense Level 1 state is used only as an informative convention
diagnostic: ``|mu_L2 - mu_L1|`` is not a gate because Level 2 is gate-level and
Trotterized, while Level 1 uses the exact dense XY mixer exponential.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, StatePreparation, XXPlusYYGate
from qiskit.quantum_info import Statevector

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from vd_sv import qaoa  # noqa: E402

from level2.noise_model import build_aer_simulator, load_config, noise_model_summary  # noqa: E402


REPORT_PATH = Path(__file__).resolve().with_name("level2_foundation_report.md")
CONFIG = load_config()
MIXER_TROTTER_STEPS = int(CONFIG["noiseless_reference"]["mixer_trotter_steps"])
HIGH_FIDELITY_TROTTER_STEPS = int(CONFIG["noiseless_reference"]["high_fidelity_mixer_trotter_steps"])
SECTOR_LEAKAGE_TOL = float(CONFIG["noiseless_reference"]["sector_leakage_tol"])
AER_SEED_SIMULATOR = int(CONFIG["noiseless_reference"]["aer_seed_simulator"])


def main() -> int:
    rows = foundation_diagnostics(engine="aer")
    high_fidelity_rows = foundation_diagnostics(
        mixer_trotter_steps=HIGH_FIDELITY_TROTTER_STEPS,
        engine="statevector",
    )
    failures = [row for row in rows if row["sector_leakage"] > SECTOR_LEAKAGE_TOL]
    REPORT_PATH.write_text(render_foundation_report(rows, high_fidelity_rows), encoding="utf-8")
    print(REPORT_PATH)
    if failures:
        for row in failures:
            print(
                "FOUNDATION CHECK FAIL "
                f"{row['instance_id']}: leakage={row['sector_leakage']:.3e}"
            )
        return 1
    return 0


def build_xy_qaoa_circuit(
    model,
    mixer_trotter_steps: int = MIXER_TROTTER_STEPS,
    decompose_for_aer: bool = False,
) -> QuantumCircuit:
    """Build the frozen-angle Trotterized XY QAOA circuit.

    Angle conventions:
    - ``RZZGate(theta) = exp(-i theta ZZ / 2)``, so cost edge ``exp(-i gamma w ZZ)``
      uses ``theta = 2 gamma w``.
    - ``XXPlusYYGate(theta, 0) = exp(-i theta (XX+YY) / 4)``, so a Trotter mixer
      substep ``exp(-i (beta/s) (XX+YY))`` uses ``theta = 4 beta / s``.
    """
    if mixer_trotter_steps < 1:
        raise ValueError("mixer_trotter_steps must be >= 1")

    inst = model.inst
    circuit = QuantumCircuit(inst.n, name=f"level2_{inst.name}")
    circuit.append(StatePreparation(dicke_state_qiskit(inst.n, inst.weight), normalize=True), range(inst.n))

    for gamma, beta in zip(model.gammas, model.betas):
        gamma = float(gamma)
        beta = float(beta)
        for (i, j), weight in zip(inst.edges, inst.weights):
            circuit.append(RZZGate(2.0 * gamma * float(weight)), [i, j])
        beta_step = beta / float(mixer_trotter_steps)
        for _ in range(mixer_trotter_steps):
            for i, j in inst.mixer_edges:
                circuit.append(XXPlusYYGate(4.0 * beta_step), [i, j])

    circuit.metadata = {
        "instance_id": inst.name,
        "mixer_trotter_steps": mixer_trotter_steps,
        "ordering": "logical qubit i maps to Qiskit qubit i; statevectors are bit-reversed",
    }
    if decompose_for_aer:
        return circuit.decompose(reps=10)
    return circuit


def dicke_state_qiskit(n: int, weight: int) -> np.ndarray:
    """Dicke state vector in Qiskit's little-endian statevector indexing."""
    return level1_to_qiskit_state(qaoa.dicke_state(n, weight), n)


def bit_reverse_index(index: int, n: int) -> int:
    out = 0
    for i in range(n):
        out = (out << 1) | ((int(index) >> i) & 1)
    return out


def level1_to_qiskit_state(state: np.ndarray, n: int) -> np.ndarray:
    state = np.asarray(state, dtype=np.complex128).reshape(-1)
    if state.size != 2**n:
        raise ValueError("state size does not match n")
    out = np.empty_like(state)
    for qiskit_index in range(2**n):
        out[qiskit_index] = state[bit_reverse_index(qiskit_index, n)]
    return out


def qiskit_to_level1_state(state: np.ndarray, n: int) -> np.ndarray:
    state = np.asarray(state, dtype=np.complex128).reshape(-1)
    if state.size != 2**n:
        raise ValueError("state size does not match n")
    out = np.empty_like(state)
    for qiskit_index, amp in enumerate(state):
        out[bit_reverse_index(qiskit_index, n)] = amp
    return out


def simulate_noiseless_statevector(
    model,
    mixer_trotter_steps: int = MIXER_TROTTER_STEPS,
    engine: str = "statevector",
) -> np.ndarray:
    """Return the noiseless Level 2 state in Level 1 big-endian ordering."""
    if engine == "statevector":
        circuit = build_xy_qaoa_circuit(model, mixer_trotter_steps=mixer_trotter_steps)
        state = np.asarray(Statevector.from_instruction(circuit).data, dtype=np.complex128)
    elif engine == "aer":
        circuit = build_xy_qaoa_circuit(
            model,
            mixer_trotter_steps=mixer_trotter_steps,
            decompose_for_aer=True,
        )
        circuit.save_statevector()
        result = build_aer_simulator(noisy=False).run(circuit).result()
        state = np.asarray(result.get_statevector(), dtype=np.complex128)
    else:
        raise ValueError(f"unknown statevector engine: {engine}")
    return qiskit_to_level1_state(state, model.inst.n)


def foundation_diagnostics(
    models: Iterable | None = None,
    mixer_trotter_steps: int = MIXER_TROTTER_STEPS,
    engine: str = "statevector",
) -> list[dict]:
    rows = []
    for model in frozen_models() if models is None else models:
        psi_l2 = simulate_noiseless_statevector(
            model,
            mixer_trotter_steps=mixer_trotter_steps,
            engine=engine,
        )
        mu_l2 = observable_expectation(psi_l2, model.inst)
        leakage = sector_leakage(psi_l2, model.inst)
        rows.append({
            "instance_id": model.inst.name,
            "n": model.inst.n,
            "weight": model.inst.weight,
            "depth": len(model.gammas),
            "mixer_trotter_steps": mixer_trotter_steps,
            "statevector_engine": engine,
            "mu_star_L1": float(model.mu_star),
            "mu_star_L2": float(mu_l2),
            "trotter_gap_abs": float(abs(mu_l2 - model.mu_star)),
            "sector_leakage": float(leakage),
            "in_sector_pass": bool(leakage <= SECTOR_LEAKAGE_TOL),
            "gap_trotter_status": "informative_only",
        })
    return rows


def observable_expectation(psi_level1_order: np.ndarray, inst: qaoa.QAOAInstance) -> float:
    diag = qaoa.cost_diagonal(inst)
    scale = float(np.max(np.abs(diag)))
    if scale == 0.0:
        raise ValueError("zero observable scale")
    probs = np.abs(np.asarray(psi_level1_order, dtype=np.complex128)) ** 2
    return float(np.real(np.sum((diag / scale) * probs)))


def sector_leakage(psi_level1_order: np.ndarray, inst: qaoa.QAOAInstance) -> float:
    probs = np.abs(np.asarray(psi_level1_order, dtype=np.complex128)) ** 2
    weights = np.fromiter((int(z).bit_count() for z in range(2**inst.n)), dtype=np.int64)
    return float(np.sum(probs[weights != inst.weight]))


def render_foundation_report(rows: list[dict], high_fidelity_rows: list[dict] | None = None) -> str:
    summary = noise_model_summary()
    max_gap = max(row["trotter_gap_abs"] for row in rows)
    max_leakage = max(row["sector_leakage"] for row in rows)
    high_fidelity_rows = high_fidelity_rows or []
    hf_max_gap = max((row["trotter_gap_abs"] for row in high_fidelity_rows), default=float("nan"))
    lines = [
        "# Level 2 Foundation",
        "",
        "Status: Level 2 foundation (Phase B robustness layer). Trotterized gate-level circuit; ideal reference is its own noiseless state, not Level 1. Additive layer, does not modify any frozen/hashed artifact.",
        "",
        "## Circuit And Ordering",
        "",
        "- Initial state: Qiskit `StatePreparation` of the Dicke vector `|D^n_k>`.",
        "- Cost convention: `RZZGate(theta)=exp(-i theta ZZ/2)`, so each cost edge uses `theta=2*gamma*w`.",
        "- Mixer convention: `XXPlusYYGate(theta,0)=exp(-i theta(XX+YY)/4)`, so each Trotter substep uses `theta=4*beta/s`.",
        f"- Mixer Trotter substeps per QAOA layer: `{MIXER_TROTTER_STEPS}` (realistic gate-level default).",
        f"- Optional high-fidelity diagnostic substeps: `{HIGH_FIDELITY_TROTTER_STEPS}` (not a realistic noisy-circuit depth).",
        "- Ordering: Level 1 is big-endian; Qiskit statevectors are little-endian. Logical qubit labels are kept the same and statevectors are bit-reversed for comparison.",
        "",
        "## Noiseless Cross-Check",
        "",
        f"- Max sector leakage: `{max_leakage:.3e}` with tolerance `{SECTOR_LEAKAGE_TOL:.1e}`.",
        f"- Max `|mu_L2-mu_L1|` at realistic depth: `{max_gap:.6g}`. This is informative only, not a PASS/FAIL gate.",
        f"- Optional high-fidelity max `|mu_L2-mu_L1|`: `{hf_max_gap:.6g}` at `{HIGH_FIDELITY_TROTTER_STEPS}` substeps.",
        "",
        "| instance | n | k | engine | substeps | mu_L1 | mu_L2 | abs gap | sector leakage | in-sector | gap status |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['instance_id']} | {row['n']} | {row['weight']} | {row['statevector_engine']} "
            f"| {row['mixer_trotter_steps']} "
            f"| {row['mu_star_L1']:.12g} | {row['mu_star_L2']:.12g} "
            f"| {row['trotter_gap_abs']:.6g} | {row['sector_leakage']:.3e} "
            f"| {_pass(row['in_sector_pass'])} | {row['gap_trotter_status']} |"
        )
    lines.extend([
        "",
        "## Noise Model Snapshot",
        "",
        f"- Backend label: `{summary['backend_label']}`.",
        f"- Source: {summary['source']}",
        f"- Seed simulator: `{summary['seed_simulator']}`.",
        f"- Basis gates: `{summary['basis_gates']}`.",
        f"- Noise instructions: `{summary['noise_instructions']}`.",
        f"- Includes readout error: `{summary['has_readout_error']}`.",
        "",
        "This step only establishes the circuit, noiseless Level 2 reference, ordering cross-check, and loadable Aer noise model. It does not implement noisy sampling, folding, readout mitigation, or Level 2 E5/E7/E12 experiments.",
    ])
    return "\n".join(lines) + "\n"


def _pass(value: bool) -> str:
    return "PASS" if value else "FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
