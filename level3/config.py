"""Pinned defaults for the additive Level 3 hardware feasibility pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = REPO_ROOT / "level3" / "archive"

DEFAULT_INSTANCE_ID = "g6_k2_c000"
DEFAULT_BACKEND_NAME = "ibm_marrakesh"
DEFAULT_IBM_CHANNEL = "ibm_quantum_platform"
DEFAULT_IBM_REGION = "us-east"

DEFAULT_SEED_TRANSPILE = 20260607
DEFAULT_SEED_SIMULATOR = 20260607
DEFAULT_OPTIMIZATION_LEVEL = 1
DEFAULT_SHOTS_PER_CIRCUIT = 4096
DEFAULT_MAX_TOTAL_SHOTS = 3 * DEFAULT_SHOTS_PER_CIRCUIT
DEFAULT_NEAR_CAP_FRACTION = 0.85


@dataclass(frozen=True)
class Stage1Config:
    """Runtime knobs for Stage 1.

    All circuits are sampled with the same shot count so the real SamplerV2
    submission can batch the QAOA and calibration circuits in one job.
    """

    instance_id: str = DEFAULT_INSTANCE_ID
    backend_name: str = DEFAULT_BACKEND_NAME
    ibm_channel: str = DEFAULT_IBM_CHANNEL
    ibm_region: str = DEFAULT_IBM_REGION
    optimization_level: int = DEFAULT_OPTIMIZATION_LEVEL
    seed_transpiler: int = DEFAULT_SEED_TRANSPILE
    seed_simulator: int = DEFAULT_SEED_SIMULATOR
    shots_per_circuit: int = DEFAULT_SHOTS_PER_CIRCUIT
    max_total_shots: int = DEFAULT_MAX_TOTAL_SHOTS
    near_cap_fraction: float = DEFAULT_NEAR_CAP_FRACTION
    archive_dir: Path = ARCHIVE_DIR
    mu_ideal_hint: float = -0.243
    initial_layout: tuple[int, ...] | None = None
