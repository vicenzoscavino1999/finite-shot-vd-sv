"""Analyze Level 3 hardware data strictly from archived counts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from level3.archive import counts_by_label, read_archive


def analyze_archive(path: str | Path) -> dict[str, Any]:
    payload = read_archive(path)
    labels = counts_by_label(payload)
    experiment = payload["experiment"]
    instance_id = str(experiment["instance_id"])
    n = int(experiment["n"])
    sector_weight = int(experiment["sector_weight"])
    mu_ideal = float(experiment["mu_ideal_noiseless_l2"])
    observable_values = np.asarray(
        experiment["observable_values_level1_order"],
        dtype=np.float64,
    )
    if observable_values.size != 2**n:
        raise ValueError("archived observable length does not match n")

    qaoa_counts = labels["qaoa_z"]
    readout = readout_matrices_from_counts(
        labels["readout_calib_0"],
        labels["readout_calib_1"],
        n=n,
    )
    assignment = assignment_matrix(readout)
    observed = observed_distribution_from_counts(qaoa_counts, n)
    mitigated, negative_mass = mitigate_distribution(observed, assignment)
    weights = hamming_weights(n)
    sector = weights == sector_weight

    unmitigated = float(np.sum(observed * observable_values))
    acceptance = float(np.sum(mitigated[sector]))
    if acceptance <= 0.0:
        sv = float("nan")
    else:
        sv = float(np.sum(mitigated[sector] * observable_values[sector]) / acceptance)

    unmit_bias = float(unmitigated - mu_ideal)
    sv_bias = float(sv - mu_ideal)
    sv_reduces = bool(abs(sv_bias) < abs(unmit_bias))
    return {
        "schema_version": "level3.analysis.v1",
        "archive_path": str(Path(path)),
        "instance_id": instance_id,
        "backend_name": payload["backend"]["name"],
        "job_id": payload["submission"].get("job_id"),
        "n": n,
        "sector_weight": sector_weight,
        "mu_ideal_noiseless_l2": mu_ideal,
        "estimators": {
            "unmitigated": unmitigated,
            "sv_readout_mitigated_weight_postselect": sv,
        },
        "bias": {
            "unmitigated": unmit_bias,
            "sv_readout_mitigated_weight_postselect": sv_bias,
        },
        "abs_bias": {
            "unmitigated": abs(unmit_bias),
            "sv_readout_mitigated_weight_postselect": abs(sv_bias),
        },
        "sv_reduces_abs_bias_vs_unmitigated": sv_reduces,
        "readout_matrices": readout.tolist(),
        "sv_acceptance_after_readout_mitigation": acceptance,
        "negative_mass_before_clip": negative_mass,
        "analysis_inputs": {
            "source": "archived_counts_only",
            "qaoa_shots": int(sum(qaoa_counts.values())),
            "calibration_shots_each": int(sum(labels["readout_calib_0"].values())),
        },
    }


def readout_matrices_from_counts(
    counts0: dict[str, int],
    counts1: dict[str, int],
    n: int,
) -> np.ndarray:
    matrices = np.zeros((n, 2, 2), dtype=np.float64)
    for true_bit, counts in ((0, counts0), (1, counts1)):
        shots = float(sum(counts.values()))
        if shots <= 0.0:
            raise ValueError("calibration counts have zero shots")
        for key, count in counts.items():
            bits = qiskit_key_to_logical_bits(key, n)
            for qubit, observed in enumerate(bits):
                matrices[qubit, true_bit, int(observed)] += float(count)
        matrices[:, true_bit, :] /= shots
    return matrices


def observed_distribution_from_counts(counts: dict[str, int], n: int) -> np.ndarray:
    total = float(sum(counts.values()))
    if total <= 0.0:
        raise ValueError("counts have zero shots")
    dist = np.zeros(2**n, dtype=np.float64)
    for key, count in counts.items():
        dist[qiskit_key_to_level1_index(key, n)] += float(count) / total
    return dist


def mitigate_distribution(observed: np.ndarray, assignment: np.ndarray) -> tuple[np.ndarray, float]:
    estimate = np.linalg.solve(assignment, observed)
    negative_mass = float(-np.sum(estimate[estimate < 0.0]))
    clipped = np.clip(estimate, 0.0, None)
    norm = float(np.sum(clipped))
    if norm <= 0.0:
        return np.full_like(clipped, 1.0 / clipped.size), negative_mass
    return clipped / norm, negative_mass


def assignment_matrix(readout_matrices: np.ndarray) -> np.ndarray:
    n = int(readout_matrices.shape[0])
    size = 2**n
    matrix = np.zeros((size, size), dtype=np.float64)
    for true_idx in range(size):
        true_bits = level1_bits(true_idx, n)
        for obs_idx in range(size):
            obs_bits = level1_bits(obs_idx, n)
            prob = 1.0
            for qubit in range(n):
                prob *= readout_matrices[qubit, true_bits[qubit], obs_bits[qubit]]
            matrix[obs_idx, true_idx] = prob
    return matrix


def qiskit_key_to_logical_bits(key: str, n: int) -> str:
    key = key.replace(" ", "")
    if len(key) != n:
        raise ValueError(f"expected {n} measured bits, got {key!r}")
    return key[::-1]


def qiskit_key_to_level1_index(key: str, n: int) -> int:
    return int(qiskit_key_to_logical_bits(key, n), 2)


def level1_bits(index: int, n: int) -> tuple[int, ...]:
    return tuple((int(index) >> (n - 1 - qubit)) & 1 for qubit in range(n))


def hamming_weights(n: int) -> np.ndarray:
    return np.fromiter((int(idx).bit_count() for idx in range(2**n)), dtype=np.int64)


def render_analysis_summary(result: dict[str, Any]) -> str:
    flag = "YES" if result["sv_reduces_abs_bias_vs_unmitigated"] else "NO"
    return "\n".join([
        f"archive={result['archive_path']}",
        f"backend={result['backend_name']}",
        f"job_id={result['job_id']}",
        f"instance={result['instance_id']}",
        f"mu_ideal_noiseless_l2={result['mu_ideal_noiseless_l2']:.12g}",
        f"unmitigated={result['estimators']['unmitigated']:.12g}",
        (
            "sv_readout_mitigated_weight_postselect="
            f"{result['estimators']['sv_readout_mitigated_weight_postselect']:.12g}"
        ),
        f"abs_bias_unmitigated={result['abs_bias']['unmitigated']:.12g}",
        (
            "abs_bias_sv_readout_mitigated_weight_postselect="
            f"{result['abs_bias']['sv_readout_mitigated_weight_postselect']:.12g}"
        ),
        f"sv_reduces_abs_bias_vs_unmitigated={flag}",
    ]) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    result = analyze_archive(args.archive)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(render_analysis_summary(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
