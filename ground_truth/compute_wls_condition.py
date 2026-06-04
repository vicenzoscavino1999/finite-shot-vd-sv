"""Compute WLS design-matrix condition numbers for pre-freeze B grids.

Output: results/frozen/wls_condition_report.csv

This is a Fase-0 pre-freeze artifact. It does not consume experimental outcomes;
it only inspects declared B grids and the fixed design [1, 1/B, 1/B^2].
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "grids.yaml"
OUT = REPO_ROOT / "results" / "frozen" / "wls_condition_report.csv"

FIELDS = [
    "experiment",
    "grid_name",
    "n_points",
    "B_min",
    "B_max",
    "raw_condition",
    "column_scaled_condition",
    "threshold",
    "status",
]


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    threshold = float(config["wls_condition"]["max_column_scaled_condition"])
    rows = []
    for experiment, spec in config["experiments"].items():
        for grid_name, values in spec.items():
            if grid_name not in {"B_fast", "B_full"}:
                continue
            b_grid = np.asarray(values, dtype=np.float64)
            if b_grid.size < 3:
                continue
            raw, scaled = _conditions(b_grid)
            rows.append({
                "experiment": experiment,
                "grid_name": grid_name,
                "n_points": int(b_grid.size),
                "B_min": int(np.min(b_grid)),
                "B_max": int(np.max(b_grid)),
                "raw_condition": raw,
                "column_scaled_condition": scaled,
                "threshold": threshold,
                "status": "PASS" if scaled <= threshold else "WARN",
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(OUT)
    return 0


def _conditions(b_grid: np.ndarray) -> tuple[float, float]:
    inv_b = 1.0 / b_grid
    design = np.column_stack([np.ones_like(inv_b), inv_b, inv_b**2])
    raw = float(np.linalg.cond(design))
    norms = np.linalg.norm(design, axis=0)
    scaled = float(np.linalg.cond(design / norms))
    return raw, scaled


if __name__ == "__main__":
    raise SystemExit(main())
