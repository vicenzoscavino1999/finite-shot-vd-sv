"""Compute a Phase-0 compute-budget table from declared grids.

Output: results/frozen/compute_budget_table.csv

The table is an audit artifact: it makes cell counts and shot counts explicit so
grids can be adjusted before PAP freeze, not after observing confirmatory data.
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "grids.yaml"
FROZEN_INSTANCES = REPO_ROOT / "results" / "frozen" / "frozen_instances.csv"
OUT = REPO_ROOT / "results" / "frozen" / "compute_budget_table.csv"

FIELDS = [
    "level",
    "block",
    "mode",
    "experiments",
    "instances",
    "n_qubits",
    "n_p",
    "n_B_or_R",
    "n_M",
    "methods",
    "T",
    "streams",
    "cells",
    "effective_shots",
    "ram_peak_mb_estimate",
    "walltime_seconds_estimate",
    "decision",
    "notes",
]


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    rows = []
    for mode in ("fast", "full"):
        rows.append(_level1_core(config, mode))
        rows.append(_level1_structural(config, mode))
    rows.extend(_phase_b_placeholders(config))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(OUT)
    return 0


def _level1_core(config: dict, mode: str) -> dict:
    exps = config["experiments"]
    instances, n_qubits = _ensemble_size_and_max_n(config)
    e1 = exps["e1_quotient_decomposition"]
    e2 = exps["e2_c_sv_zero"]
    e3 = exps["e3_delta_vd_generator"]
    e4 = exps["e4_delta_sv_firstorder"]
    b1 = e1[f"B_{mode}"]
    b2 = e2[f"B_{mode}"]
    t1 = int(e1[f"T_{mode}"])
    t2 = int(e2[f"T_{mode}"])
    p2 = e2["p_grid"]
    p_delta = e3[f"p_grid_{mode}"]

    e1_shots = t1 * sum(int(b) for b in b1) * (2 + 1)  # VD two streams + unmitigated.
    e2_shots = len(p2) * t2 * sum(int(b) for b in b2) * (2 + 1)  # VD + SV.
    cells = 2 * len(b1) + len(p2) * 2 * len(b2) + len(p_delta) + len(p_delta)
    return {
        "level": "Level 1",
        "block": "core",
        "mode": mode,
        "experiments": "E1-E4",
        "instances": instances,
        "n_qubits": n_qubits,
        "n_p": 1 + len(p2) + len(p_delta),
        "n_B_or_R": len(b1) + len(b2),
        "n_M": 1,
        "methods": 3,
        "T": max(t1, t2),
        "streams": 3,
        "cells": cells * instances,
        "effective_shots": int((e1_shots + e2_shots) * instances),
        "ram_peak_mb_estimate": _density_matrix_ram_mb(n_qubits),
        "walltime_seconds_estimate": _walltime_estimate((e1_shots + e2_shots) * instances),
        "decision": "confirmatorio",
        "notes": "E3/E4 are white-box slope fits and add negligible shot-level cost.",
    }


def _level1_structural(config: dict, mode: str) -> dict:
    exps = config["experiments"]
    instances, n_qubits = _ensemble_size_and_max_n(config)
    e5 = exps["e5_denominator_concentration"]
    e7 = exps["e7_certified_crossing"]
    sens = exps["e7_resource_observable_sensitivity"]
    e5_grid = e5[f"B_over_Bden_{mode}"]
    e7_grid = e7[f"R_{mode}"]
    t5 = int(e5[f"T_{mode}"])
    t7 = int(e7[f"T_{mode}"])
    e5_bden_estimate = 4776.144541252746
    e5_shots = t5 * sum(int(round(e5_bden_estimate * float(f))) for f in e5_grid) * 2
    e7_shots = t7 * sum(int(r) for r in e7_grid) * (2 + 1 + 1)
    sens_cells = (
        len(sens["resource_definitions"])
        * len(sens["observable_normalizations"])
        * len(sens["method_pairs"])
    )
    cells = len(e5_grid) + len(e7_grid) * 3 + sens_cells
    return {
        "level": "Level 1",
        "block": "structural",
        "mode": mode,
        "experiments": "E5,E7,sensitivity",
        "instances": instances,
        "n_qubits": n_qubits,
        "n_p": 2,
        "n_B_or_R": len(e5_grid) + len(e7_grid),
        "n_M": 2,
        "methods": 3,
        "T": max(t5, t7),
        "streams": 4,
        "cells": cells * instances,
        "effective_shots": int((e5_shots + e7_shots) * instances),
        "ram_peak_mb_estimate": _density_matrix_ram_mb(n_qubits),
        "walltime_seconds_estimate": _walltime_estimate((e5_shots + e7_shots) * instances),
        "decision": "secundario",
        "notes": "Sensitivity is white-box leading-law arithmetic and adds negligible shot-level cost.",
    }


def _phase_b_placeholders(config: dict) -> list[dict]:
    _instances, n_qubits = _ensemble_size_and_max_n(config)
    return [
        {
            "level": "Level 2",
            "block": "device_sim",
            "mode": "phase_b",
            "experiments": "E5,E7,E8,E12",
            "instances": 0,
            "n_qubits": n_qubits,
            "n_p": 0,
            "n_B_or_R": 0,
            "n_M": 0,
            "methods": 0,
            "T": 0,
            "streams": 0,
            "cells": 0,
            "effective_shots": 0,
            "ram_peak_mb_estimate": 0,
            "walltime_seconds_estimate": 0,
            "decision": "omitido",
            "notes": "Deferred to Phase B; requires Aer/noise-model calibration.",
        },
        {
            "level": "Level 3",
            "block": "hardware_feasibility",
            "mode": "phase_b",
            "experiments": "E5,E7",
            "instances": 0,
            "n_qubits": n_qubits,
            "n_p": 0,
            "n_B_or_R": 0,
            "n_M": 0,
            "methods": 0,
            "T": 0,
            "streams": 0,
            "cells": 0,
            "effective_shots": 0,
            "ram_peak_mb_estimate": 0,
            "walltime_seconds_estimate": 0,
            "decision": "omitido",
            "notes": "No hardware execution in Phase A; feasibility note remains a separate pre-freeze artifact.",
        },
    ]


def _density_matrix_ram_mb(n_qubits: int) -> int:
    dim = 2**n_qubits
    bytes_complex128_matrix = dim * dim * 16
    return int(max(1, round(8 * bytes_complex128_matrix / 1_000_000)))


def _walltime_estimate(effective_shots: float) -> int:
    # Conservative development estimate for vectorized NumPy sufficient-statistic sampling.
    return int(max(1, round(effective_shots / 75_000_000)))


def _ensemble_size_and_max_n(config: dict) -> tuple[int, int]:
    if FROZEN_INSTANCES.exists():
        with FROZEN_INSTANCES.open(newline="", encoding="utf-8") as fh:
            included = [row for row in csv.DictReader(fh) if row["selection_status"] == "included"]
        if included:
            return len(included), max(int(row["size_n"]) for row in included)
    selection = config["instance_selection"]
    return (
        int(selection["n_target_per_size"]) * len(selection["sizes"]),
        max(int(n) for n in selection["sizes"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
