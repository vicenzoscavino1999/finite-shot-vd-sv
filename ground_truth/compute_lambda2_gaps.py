"""Compute lambda2 gap table for the frozen Level-1 ensemble.

Output: results/frozen/lambda2_gap_table.csv

This Fase-0 diagnostic checks the spectral data needed by the copy-log-scale
prediction (P8/E6). It uses only white-box ground truth, declared p grids, and
the pinned pre-freeze instance/angle artifacts.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ground_truth import compute_frozen_model_specs as frozen_specs  # noqa: E402
from vd_sv.density_matrix import spectral_gap  # noqa: E402

CONFIG = REPO_ROOT / "config" / "grids.yaml"
FROZEN_INSTANCES = REPO_ROOT / "results" / "frozen" / "frozen_instances.csv"
FROZEN_ANGLES = REPO_ROOT / "results" / "frozen" / "frozen_qaoa_angles.csv"
OUT = REPO_ROOT / "results" / "frozen" / "lambda2_gap_table.csv"
FLOAT_DIGITS = 15

FIELDS = [
    "instance_id",
    "size_n",
    "n_qubits",
    "sector_weight",
    "candidate_index",
    "noise_strength",
    "lambda1",
    "lambda2",
    "spectral_gap",
    "relative_gap",
    "min_relative_gap",
    "abs_log_lambda2",
    "gap_status",
    "e6_candidate",
]


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    instance_rows = _read_csv(FROZEN_INSTANCES)
    angle_rows = _read_csv(FROZEN_ANGLES)
    rows = compute_rows(config, instance_rows, angle_rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT, FIELDS, rows)
    print(OUT)
    return 0


def compute_rows(config: dict, instance_rows: list[dict], angle_rows: list[dict]) -> list[dict]:
    ps = frozen_specs._declared_p_values(config)
    min_relative_gap = float(config["lambda2_gap"]["min_relative_gap"])
    rows = []
    for instance_row in instance_rows:
        if instance_row["selection_status"] != "included":
            continue
        model = frozen_specs.reconstruct_model(instance_row, angle_rows)
        for p in ps:
            lam1, lam2 = spectral_gap(model.rho_p(float(p)))
            gap = lam1 - lam2
            relative_gap = gap / lam1 if lam1 > 0 else 0.0
            gap_ok = relative_gap >= min_relative_gap and 0.0 < lam2 < lam1
            rows.append({
                "instance_id": model.inst.name,
                "size_n": model.inst.n,
                "n_qubits": model.inst.n,
                "sector_weight": model.inst.weight,
                "candidate_index": int(instance_row["candidate_index"]),
                "noise_strength": float(p),
                "lambda1": lam1,
                "lambda2": lam2,
                "spectral_gap": gap,
                "relative_gap": relative_gap,
                "min_relative_gap": min_relative_gap,
                "abs_log_lambda2": abs(float(np.log(lam2))) if lam2 > 0 else float("inf"),
                "gap_status": "PASS" if gap_ok else "WARN",
                "e6_candidate": "no",
            })
    _mark_e6_candidate(rows)
    return rows


def _mark_e6_candidate(rows: list[dict]) -> None:
    worst_by_instance = {}
    for row in rows:
        instance_id = row["instance_id"]
        rel_gap = float(row["relative_gap"])
        worst_by_instance[instance_id] = min(worst_by_instance.get(instance_id, rel_gap), rel_gap)
    if not worst_by_instance:
        return
    selected = max(sorted(worst_by_instance), key=lambda instance_id: worst_by_instance[instance_id])
    for row in rows:
        row["e6_candidate"] = "yes" if row["instance_id"] == selected else "no"


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: _stable_csv_cell(row[key]) for key in fieldnames} for row in rows])


def _stable_csv_cell(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        if not np.isfinite(value):
            return str(value)
        return f"{value:.{FLOAT_DIGITS}g}"
    return value


if __name__ == "__main__":
    raise SystemExit(main())
