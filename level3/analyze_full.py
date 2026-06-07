"""Analyze Level 3 Stage 3 archives with epoch-cluster bootstrap."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from level3.analyze import (
    assignment_matrix,
    hamming_weights,
    mitigate_distribution,
    observed_distribution_from_counts,
    qiskit_key_to_logical_bits,
    readout_matrices_from_counts,
)
from level3.archive import read_archive


BOOTSTRAP_SEED = 33033
BOOTSTRAP_REPS = 2000
DENOMINATOR_CLIP_FRACTION = 0.5
DENOMINATOR_EPS = 1.0e-3


def analyze_archives(
    paths: list[str | Path],
    bootstrap_reps: int = BOOTSTRAP_REPS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    epoch_rows: list[dict[str, Any]] = []
    metadata = []
    for epoch_index, path in enumerate(paths, start=1):
        payload = read_archive(path)
        epoch_rows.extend(analyze_epoch(payload, Path(path), epoch_index))
        metadata.append(epoch_metadata(payload, Path(path), epoch_index))
    if not epoch_rows:
        raise ValueError("no epoch rows")
    aggregate = aggregate_epoch_rows(epoch_rows, bootstrap_reps=bootstrap_reps, seed=seed)
    return {
        "schema_version": "level3.stage3.analysis.v1",
        "analysis_inputs": {
            "source": "archived_counts_only",
            "archive_count": len(paths),
            "bootstrap_reps": int(bootstrap_reps),
            "bootstrap_seed": int(seed),
            "denominator_clip_fraction": DENOMINATOR_CLIP_FRACTION,
        },
        "epochs": metadata,
        "rows": aggregate,
        "qualitative": qualitative_summary(aggregate),
    }


def analyze_epoch(payload: dict[str, Any], path: Path, epoch_index: int) -> list[dict[str, Any]]:
    experiment = payload["experiment"]
    transpile = payload["transpile"]
    n = int(experiment["n"])
    vd_qubits = int(experiment["vd_qubits"])
    sector_weight = int(experiment["sector_weight"])
    mu_ideal = float(experiment["mu_ideal_noiseless_l2"])
    b_grid = [int(b) for b in experiment["b_grid"]]
    observable = np.asarray(experiment["observable_values_level1_order"], dtype=np.float64)
    circuits = {item["label"]: item for item in payload["circuits"]}

    calibration = readout_matrices_from_counts(
        circuits["readout_calib_0"]["counts"],
        circuits["readout_calib_1"]["counts"],
        n=len(transpile["calibration_physical_qubits"]),
    )
    qaoa_cal_indices = [
        int(transpile["qaoa_logical_to_calibration_index"][str(i)])
        for i in range(n)
    ]
    vd_num_cal_indices = [
        int(transpile["vd_numerator_logical_to_calibration_index"][str(i)])
        for i in range(vd_qubits)
    ]
    vd_den_cal_indices = [
        int(transpile["vd_denominator_logical_to_calibration_index"][str(i)])
        for i in range(vd_qubits)
    ]
    qaoa_readout = calibration[qaoa_cal_indices, :, :]
    vd_num_readout = calibration[vd_num_cal_indices, :, :]
    vd_den_readout = calibration[vd_den_cal_indices, :, :]
    qaoa_bits = list(circuits["qaoa_z"]["bitstrings"])
    numerator_bits = list(circuits["vd_m2_numerator"]["bitstrings"])
    denominator_bits = list(circuits["vd_m2_denominator"]["bitstrings"])
    d_reference = vd_denominator_from_bitstrings(
        denominator_bits,
        vd_den_readout,
        vd_qubits,
    )
    d_clip = max(DENOMINATOR_CLIP_FRACTION * d_reference, 1.0e-6)
    resources = transpile["resource_kappas"]

    rows = []
    for b in b_grid:
        qaoa_counts = counts_from_first(qaoa_bits, b)
        numerator_counts = counts_from_first(numerator_bits, b)
        denominator_counts = counts_from_first(denominator_bits, b)

        unmit = unmitigated_from_counts(qaoa_counts, n, observable)
        sv, sv_acceptance = sv_from_counts(qaoa_counts, qaoa_readout, n, sector_weight, observable)
        d_hat = vd_denominator_from_counts(denominator_counts, vd_den_readout, vd_qubits)
        n_hat = vd_numerator_from_counts(numerator_counts, vd_num_readout, n, vd_qubits, observable)
        vd = n_hat / max(d_hat, d_clip)

        rows.extend([
            method_row(
                payload,
                path,
                epoch_index,
                "unmitigated",
                b,
                unmit,
                mu_ideal,
                resources,
                extra={"sv_acceptance": None, "vd_numerator": None, "vd_denominator": None},
            ),
            method_row(
                payload,
                path,
                epoch_index,
                "sv_readout_mitigated_weight_postselect",
                b,
                sv,
                mu_ideal,
                resources,
                extra={"sv_acceptance": sv_acceptance, "vd_numerator": None, "vd_denominator": None},
            ),
            method_row(
                payload,
                path,
                epoch_index,
                "vd_m2_readout_mitigated",
                b,
                vd,
                mu_ideal,
                resources,
                extra={
                    "sv_acceptance": None,
                    "vd_numerator": n_hat,
                    "vd_denominator": d_hat,
                    "vd_denominator_reference": d_reference,
                    "vd_denominator_clip": d_clip,
                    "B_den_estimate": denominator_sample_threshold(abs(d_reference)),
                },
            ),
        ])
    return rows


def method_row(
    payload: dict[str, Any],
    path: Path,
    epoch_index: int,
    method: str,
    b: int,
    estimate: float,
    mu_ideal: float,
    resources: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    if method == "vd_m2_readout_mitigated":
        paired = float(resources["paired_sample"]["vd"]) * float(b)
        twoq = float(resources["two_qubit_gate_proxy"]["vd"]) * float(b)
    elif method.startswith("sv"):
        paired = float(resources["paired_sample"]["sv"]) * float(b)
        twoq = float(resources["two_qubit_gate_proxy"]["sv"]) * float(b)
    else:
        paired = float(resources["paired_sample"]["unmitigated"]) * float(b)
        twoq = float(resources["two_qubit_gate_proxy"]["unmitigated"]) * float(b)
    err = float(estimate - mu_ideal)
    return {
        "archive": str(path),
        "epoch_index": int(epoch_index),
        "job_id": payload["submission"]["job_id"],
        "backend": payload["backend"]["name"],
        "instance_id": payload["experiment"]["instance_id"],
        "method": method,
        "B": int(b),
        "resource_paired_sample": paired,
        "resource_two_qubit_gate_proxy": twoq,
        "estimate": float(estimate),
        "mu_ideal_noiseless_l2": float(mu_ideal),
        "error": err,
        "squared_error": float(err * err),
        **extra,
    }


def aggregate_epoch_rows(
    rows: list[dict[str, Any]],
    bootstrap_reps: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    out = []
    methods = sorted({row["method"] for row in rows})
    b_values = sorted({int(row["B"]) for row in rows})
    for method in methods:
        for b in b_values:
            group = [row for row in rows if row["method"] == method and int(row["B"]) == b]
            if not group:
                continue
            estimates = np.asarray([row["estimate"] for row in group], dtype=np.float64)
            errors = np.asarray([row["error"] for row in group], dtype=np.float64)
            squared = np.asarray([row["squared_error"] for row in group], dtype=np.float64)
            bias = float(np.mean(errors))
            variance = float(np.var(estimates, ddof=1)) if estimates.size > 1 else 0.0
            mse = float(np.mean(squared))
            boot = bootstrap_metrics(group, bootstrap_reps, rng)
            row0 = group[0]
            out.append({
                "method": method,
                "B": int(b),
                "epochs": len(group),
                "mean_estimate": float(np.mean(estimates)),
                "bias": bias,
                "variance_between_epochs": variance,
                "mse": mse,
                "bias_ci95": boot["bias_ci95"],
                "mse_ci95": boot["mse_ci95"],
                "resource_paired_sample": float(row0["resource_paired_sample"]),
                "resource_two_qubit_gate_proxy": float(row0["resource_two_qubit_gate_proxy"]),
                "mean_vd_denominator": mean_optional(group, "vd_denominator"),
                "mean_vd_denominator_reference": mean_optional(group, "vd_denominator_reference"),
                "mean_vd_denominator_clip": mean_optional(group, "vd_denominator_clip"),
                "B_den_estimate": mean_optional(group, "B_den_estimate"),
                "B_over_B_den_estimate": b / mean_optional(group, "B_den_estimate")
                if mean_optional(group, "B_den_estimate") not in (0.0, None)
                and math.isfinite(mean_optional(group, "B_den_estimate"))
                else None,
            })
    return out


def bootstrap_metrics(group: list[dict[str, Any]], reps: int, rng: np.random.Generator) -> dict[str, Any]:
    errors = np.asarray([row["error"] for row in group], dtype=np.float64)
    squared = np.asarray([row["squared_error"] for row in group], dtype=np.float64)
    n = len(group)
    if n == 1:
        bias_values = np.asarray([float(errors[0])])
        mse_values = np.asarray([float(squared[0])])
    else:
        choices = rng.integers(0, n, size=(int(reps), n))
        bias_values = np.mean(errors[choices], axis=1)
        mse_values = np.mean(squared[choices], axis=1)
    return {
        "bias_ci95": quantile_pair(bias_values),
        "mse_ci95": quantile_pair(mse_values),
    }


def qualitative_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    b_max = max(int(row["B"]) for row in rows)
    largest = [row for row in rows if int(row["B"]) == b_max]
    mse_order = sorted(
        ((row["method"], float(row["mse"])) for row in largest),
        key=lambda item: item[1],
    )
    vd_rows = [row for row in rows if row["method"] == "vd_m2_readout_mitigated"]
    sv_rows = [row for row in rows if row["method"] == "sv_readout_mitigated_weight_postselect"]
    vd_beats_sv_same_b = []
    for vd in vd_rows:
        matches = [sv for sv in sv_rows if int(sv["B"]) == int(vd["B"])]
        if matches:
            vd_beats_sv_same_b.append(float(vd["mse"]) < float(matches[0]["mse"]))
    return {
        "largest_B": b_max,
        "mse_order_at_largest_B": [
            {"method": method, "mse": mse} for method, mse in mse_order
        ],
        "vd_beats_sv_at_any_same_B": bool(any(vd_beats_sv_same_b)),
        "interpretation": (
            "qualitative_sv_dominance_vd_overhead_degraded"
            if not any(vd_beats_sv_same_b)
            else "crossing_or_vd_window_observed_same_B"
        ),
    }


def epoch_metadata(payload: dict[str, Any], path: Path, epoch_index: int) -> dict[str, Any]:
    metrics = payload.get("submission", {}).get("metrics", {})
    usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
    bss = metrics.get("bss", {}) if isinstance(metrics, dict) else {}
    quantum_seconds = usage.get("quantum_seconds", bss.get("seconds"))
    return {
        "epoch_index": int(epoch_index),
        "archive": str(path),
        "job_id": payload["submission"]["job_id"],
        "backend": payload["backend"]["name"],
        "created_at_utc": payload["created_at_utc"],
        "quantum_seconds": float(quantum_seconds) if quantum_seconds is not None else None,
        "shots_per_circuit": int(payload["shots"]["shots_per_circuit"]),
        "total_shots": int(payload["shots"]["total_shots"]),
    }


def unmitigated_from_counts(counts: dict[str, int], n: int, observable: np.ndarray) -> float:
    observed = observed_distribution_from_counts(counts, n)
    return float(np.sum(observed * observable))


def sv_from_counts(
    counts: dict[str, int],
    readout: np.ndarray,
    n: int,
    sector_weight: int,
    observable: np.ndarray,
) -> tuple[float, float]:
    observed = observed_distribution_from_counts(counts, n)
    assignment = assignment_matrix(readout)
    mitigated, _negative_mass = mitigate_distribution(observed, assignment)
    sector = hamming_weights(n) == int(sector_weight)
    acceptance = float(np.sum(mitigated[sector]))
    if acceptance <= 0.0:
        return float("nan"), acceptance
    estimate = float(np.sum(mitigated[sector] * observable[sector]) / acceptance)
    return estimate, acceptance


def vd_denominator_from_bitstrings(bitstrings: list[str], readout: np.ndarray, vd_qubits: int) -> float:
    return vd_denominator_from_counts(Counter(bitstrings), readout, vd_qubits)


def vd_denominator_from_counts(
    counts: dict[str, int],
    readout: np.ndarray,
    vd_qubits: int,
) -> float:
    ancilla = int(vd_qubits) - 1
    observed = subset_distribution_from_counts(counts, vd_qubits, [ancilla])
    assignment = assignment_matrix(readout[[ancilla], :, :])
    true = np.linalg.solve(assignment, observed)
    return float(true[0] - true[1])


def vd_numerator_from_counts(
    counts: dict[str, int],
    readout: np.ndarray,
    n: int,
    vd_qubits: int,
    observable: np.ndarray,
) -> float:
    ancilla = int(vd_qubits) - 1
    subset = list(range(n)) + [ancilla]
    observed = subset_distribution_from_counts(counts, vd_qubits, subset)
    assignment = assignment_matrix(readout[subset, :, :])
    true = np.linalg.solve(assignment, observed)
    values = np.zeros(2 ** (n + 1), dtype=np.float64)
    for idx in range(values.size):
        bits = format(idx, f"0{n + 1}b")
        obs_idx = int(bits[:n], 2)
        anc_bit = int(bits[-1])
        values[idx] = observable[obs_idx] * (1.0 if anc_bit == 0 else -1.0)
    return float(np.sum(true * values))


def subset_distribution_from_counts(
    counts: dict[str, int],
    total_qubits: int,
    subset: list[int],
) -> np.ndarray:
    size = 2 ** len(subset)
    dist = np.zeros(size, dtype=np.float64)
    total = float(sum(counts.values()))
    if total <= 0:
        raise ValueError("zero-shot counts")
    for key, count in counts.items():
        bits = qiskit_key_to_logical_bits(str(key), total_qubits)
        subset_bits = "".join(bits[i] for i in subset)
        dist[int(subset_bits, 2)] += float(count) / total
    return dist


def counts_from_first(bitstrings: list[str], b: int) -> dict[str, int]:
    if int(b) > len(bitstrings):
        raise ValueError(f"requested B={b} exceeds archived shots={len(bitstrings)}")
    return {str(k): int(v) for k, v in Counter(bitstrings[: int(b)]).items()}


def denominator_sample_threshold(d_m: float, eps: float = DENOMINATOR_EPS) -> float:
    d_abs = abs(float(d_m))
    if d_abs <= 0.0:
        return float("inf")
    sigma_d2 = max(1.0 - d_abs**2, 0.0)
    return float((8.0 * sigma_d2 / d_abs**2 + 8.0 / (3.0 * d_abs)) * math.log(1.0 / eps))


def mean_optional(group: list[dict[str, Any]], key: str) -> float | None:
    values = [row.get(key) for row in group if row.get(key) is not None]
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def quantile_pair(values: np.ndarray) -> list[float]:
    return [
        float(np.quantile(values, 0.025)),
        float(np.quantile(values, 0.975)),
    ]


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        f"archives={result['analysis_inputs']['archive_count']}",
        f"bootstrap_reps={result['analysis_inputs']['bootstrap_reps']}",
        f"qualitative={result['qualitative']['interpretation']}",
        "method,B,epochs,mean_estimate,bias,variance_between_epochs,mse,mse_ci95_low,mse_ci95_high,resource_paired_sample,resource_two_qubit_gate_proxy,mean_vd_denominator,B_over_B_den_estimate",
    ]
    for row in result["rows"]:
        ci = row["mse_ci95"]
        lines.append(
            ",".join([
                str(row["method"]),
                str(row["B"]),
                str(row["epochs"]),
                f"{row['mean_estimate']:.12g}",
                f"{row['bias']:.12g}",
                f"{row['variance_between_epochs']:.12g}",
                f"{row['mse']:.12g}",
                f"{ci[0]:.12g}",
                f"{ci[1]:.12g}",
                f"{row['resource_paired_sample']:.12g}",
                f"{row['resource_two_qubit_gate_proxy']:.12g}",
                "" if row["mean_vd_denominator"] is None else f"{row['mean_vd_denominator']:.12g}",
                "" if row["B_over_B_den_estimate"] is None else f"{row['B_over_B_den_estimate']:.12g}",
            ])
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--bootstrap-reps", type=int, default=BOOTSTRAP_REPS)
    args = parser.parse_args(argv)

    result = analyze_archives(args.archives, bootstrap_reps=args.bootstrap_reps)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(render_summary(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
