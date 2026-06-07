"""Budget guard for Level 3 hardware submission."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceeded(RuntimeError):
    """Raised when a planned run exceeds the configured shot or time caps."""


@dataclass(frozen=True)
class BudgetEstimate:
    circuit_count: int
    shots_per_circuit: int
    total_shots: int
    max_total_shots: int
    near_cap_fraction: float
    max_circuit_depth: int
    estimated_qpu_seconds: float
    near_cap: bool


def estimate_budget(
    circuit_depths: list[int],
    shots_per_circuit: int,
    max_total_shots: int,
    near_cap_fraction: float,
) -> BudgetEstimate:
    circuit_count = len(circuit_depths)
    total_shots = int(circuit_count * int(shots_per_circuit))
    max_depth = max((int(depth) for depth in circuit_depths), default=0)
    # This is deliberately conservative and transparent, not a device SLA.
    estimated_qpu_seconds = float(total_shots * max(max_depth, 1) * 1.0e-6)
    near_cap = total_shots >= float(max_total_shots) * float(near_cap_fraction)
    return BudgetEstimate(
        circuit_count=circuit_count,
        shots_per_circuit=int(shots_per_circuit),
        total_shots=total_shots,
        max_total_shots=int(max_total_shots),
        near_cap_fraction=float(near_cap_fraction),
        max_circuit_depth=max_depth,
        estimated_qpu_seconds=estimated_qpu_seconds,
        near_cap=bool(near_cap),
    )


def enforce_budget(
    estimate: BudgetEstimate,
    require_near_cap_confirmation: bool,
    near_cap_confirmed: bool,
) -> None:
    if estimate.total_shots > estimate.max_total_shots:
        raise BudgetExceeded(
            "planned total shots exceed cap: "
            f"{estimate.total_shots} > {estimate.max_total_shots}"
        )
    if require_near_cap_confirmation and estimate.near_cap and not near_cap_confirmed:
        threshold = int(estimate.max_total_shots * estimate.near_cap_fraction)
        raise BudgetExceeded(
            "planned total shots are near the cap and require --confirm-near-cap: "
            f"{estimate.total_shots} >= {threshold}"
        )


def render_budget_estimate(estimate: BudgetEstimate) -> str:
    return (
        "BUDGET_ESTIMATE "
        f"circuits={estimate.circuit_count} "
        f"shots_per_circuit={estimate.shots_per_circuit} "
        f"total_shots={estimate.total_shots} "
        f"max_total_shots={estimate.max_total_shots} "
        f"near_cap={str(estimate.near_cap).lower()} "
        f"max_circuit_depth={estimate.max_circuit_depth} "
        f"estimated_qpu_seconds={estimate.estimated_qpu_seconds:.6g}"
    )

