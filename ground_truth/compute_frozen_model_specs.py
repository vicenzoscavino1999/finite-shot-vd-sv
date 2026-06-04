"""Generate pre-freeze Level-1 ensemble and QAOA-angle artifacts.

Outputs:
- results/frozen/frozen_instances.csv
- results/frozen/frozen_qaoa_angles.csv
- results/frozen/instance_selection_diagnostics.md

The selector evaluates only white-box preconditions I1-I4 from the frozen model
specification. It does not consume finite-shot estimates or adjudication data.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ground_truth.instance_ensemble import (  # noqa: E402
    edge_tuple,
    generate_candidate,
    sector_weight_for_size,
)
from vd_sv import coefficients as cf  # noqa: E402
from vd_sv import noise, qaoa  # noqa: E402
from vd_sv.density_matrix import ordered_eigenvalues, spectral_gap  # noqa: E402

CONFIG = REPO_ROOT / "config" / "grids.yaml"
OUT_INSTANCES = REPO_ROOT / "results" / "frozen" / "frozen_instances.csv"
OUT_ANGLES = REPO_ROOT / "results" / "frozen" / "frozen_qaoa_angles.csv"
OUT_DIAGNOSTICS = REPO_ROOT / "results" / "frozen" / "instance_selection_diagnostics.md"
FREEZE_FLOAT_DIGITS = 15

INSTANCE_FIELDS = [
    "instance_id",
    "size_n",
    "sector_weight",
    "candidate_index",
    "master_seed",
    "selection_status",
    "failing_criterion",
    "graph_family",
    "edge_count",
    "edges_json",
    "weights_json",
    "mixer_edges_json",
    "qaoa_depth",
    "qaoa_angle_seed",
    "qaoa_angle_restarts",
    "noise_channel_seed",
    "mu_star",
    "noiseless_cost",
    "symmetry_commutator_max_abs",
    "ideal_sector_leakage",
    "entanglement_entropy_bits",
    "min_entanglement_entropy_bits",
    "min_relative_lambda2_gap",
    "min_required_relative_lambda2_gap",
    "min_spectral_gap",
    "max_noise_strength",
    "max_channel_parameter",
    "min_density_eigenvalue",
    "max_trace_error",
    "reason",
]

ANGLE_FIELDS = [
    "instance_id",
    "size_n",
    "sector_weight",
    "candidate_index",
    "depth",
    "layer",
    "gamma",
    "beta",
    "noiseless_cost",
    "optimizer",
    "angle_seed",
    "angle_restarts",
    "bounds",
    "selection_status",
]


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    instance_rows, angle_rows = generate_frozen_specs(config)

    OUT_INSTANCES.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_INSTANCES, INSTANCE_FIELDS, instance_rows)
    _write_csv(OUT_ANGLES, ANGLE_FIELDS, angle_rows)
    OUT_DIAGNOSTICS.write_text(_diagnostics_markdown(config, instance_rows), encoding="utf-8")
    print(OUT_INSTANCES)
    print(OUT_ANGLES)
    print(OUT_DIAGNOSTICS)
    return 0


def generate_frozen_specs(config: dict) -> tuple[list[dict], list[dict]]:
    ps = _declared_p_values(config)
    model_config = config["model"]
    selection = config["instance_selection"]
    depth = int(model_config["qaoa_depth"])
    angle_seed = int(model_config["qaoa_angle_seed"])
    angle_restarts = int(model_config["qaoa_angle_restarts"])
    channel_seed = int(model_config["noise_channel_seed"])
    target = int(selection["n_target_per_size"])
    max_candidates = int(selection["max_candidates_per_size"])

    instance_rows: list[dict] = []
    angle_rows: list[dict] = []
    for n_raw in selection["sizes"]:
        n = int(n_raw)
        sector_weight = sector_weight_for_size(n, str(selection["sector_weight_rule"]))
        included = 0
        for candidate_index in range(max_candidates):
            inst = _pinned_instance(
                generate_candidate_from_config(config, n, sector_weight, candidate_index)
            )
            gammas, betas, _opt_cost = qaoa.optimize_angles(
                inst,
                depth=depth,
                seed=angle_seed,
                restarts=angle_restarts,
            )
            gammas = _pinned_array(gammas)
            betas = _pinned_array(betas)
            channel = noise.heterogeneous_ad_pd(n, seed=channel_seed)
            model = cf.build_model(inst, gammas, betas, channel)
            row = _instance_row(config, model, ps, candidate_index)
            instance_rows.append(row)
            angle_rows.extend(_angle_rows(model, row))
            if row["selection_status"] == "included":
                included += 1
            if included >= target:
                break
        if included < target:
            raise RuntimeError(
                f"n={n}: only {included} candidates passed I1-I4 before max_candidates"
            )
    return instance_rows, angle_rows


def generate_candidate_from_config(
    config: dict,
    n: int,
    sector_weight: int,
    candidate_index: int,
) -> qaoa.QAOAInstance:
    selection = config["instance_selection"]
    weights = selection["weight_distribution"]
    return generate_candidate(
        n=n,
        sector_weight=sector_weight,
        candidate_index=candidate_index,
        master_seed=int(selection["master_seed"]),
        extra_edge_prob=float(selection["extra_edge_prob"]),
        weight_low=float(weights["low"]),
        weight_high=float(weights["high"]),
    )


def _instance_row(config: dict, model, ps: list[float], candidate_index: int) -> dict:
    values = evaluate_i1_to_i4(model, ps, config)
    status = "included" if values["failing_criterion"] == "none" else "rejected"
    reason = (
        "passes I1 symmetry, I2 entanglement, I3 lambda2 gap, I4 p-range"
        if status == "included"
        else f"first failing precondition: {values['failing_criterion']}"
    )
    selection = config["instance_selection"]
    model_config = config["model"]
    return {
        "instance_id": model.inst.name,
        "size_n": model.inst.n,
        "sector_weight": model.inst.weight,
        "candidate_index": candidate_index,
        "master_seed": int(selection["master_seed"]),
        "selection_status": status,
        "failing_criterion": values["failing_criterion"],
        "graph_family": selection["graph_family"],
        "edge_count": len(model.inst.edges),
        "edges_json": _json(model.inst.edges),
        "weights_json": _json(model.inst.weights),
        "mixer_edges_json": _json(model.inst.mixer_edges),
        "qaoa_depth": int(model.gammas.size),
        "qaoa_angle_seed": int(model_config["qaoa_angle_seed"]),
        "qaoa_angle_restarts": int(model_config["qaoa_angle_restarts"]),
        "noise_channel_seed": int(model_config["noise_channel_seed"]),
        "mu_star": model.mu_star,
        "noiseless_cost": _noiseless_cost(model),
        **values,
        "reason": reason,
    }


def evaluate_i1_to_i4(model, ps: list[float], config: dict) -> dict:
    min_required_gap = float(config["lambda2_gap"]["min_relative_gap"])
    min_required_entropy = float(config["instance_selection"]["min_entanglement_entropy_bits"])
    min_relative_gap, min_spectral_gap = _lambda2_gap_summary(model, ps)
    min_density_eig, max_trace_error = _density_summary(model, ps)
    max_noise_strength = max(ps)
    max_channel_parameter = _max_channel_parameter(model, max_noise_strength)
    commutator = model.projector @ model.observable - model.observable @ model.projector
    commutator_max = float(np.max(np.abs(commutator)))
    ideal_sector_leakage = 1.0 - float(np.real(np.trace(model.projector @ model.rho_star)))
    entropy = qaoa.entanglement_entropy(model.psi, model.inst.n)

    checks = [
        ("I1", commutator_max <= 1e-12 and abs(ideal_sector_leakage) <= 1e-12),
        ("I2", entropy >= min_required_entropy),
        ("I3", min_relative_gap >= min_required_gap),
        (
            "I4",
            min_density_eig >= -1e-10
            and max_trace_error <= 1e-10
            and max_channel_parameter <= 1.0,
        ),
    ]
    failing = next((name for name, ok in checks if not ok), "none")
    return {
        "failing_criterion": failing,
        "symmetry_commutator_max_abs": commutator_max,
        "ideal_sector_leakage": ideal_sector_leakage,
        "entanglement_entropy_bits": entropy,
        "min_entanglement_entropy_bits": min_required_entropy,
        "min_relative_lambda2_gap": min_relative_gap,
        "min_required_relative_lambda2_gap": min_required_gap,
        "min_spectral_gap": min_spectral_gap,
        "max_noise_strength": max_noise_strength,
        "max_channel_parameter": max_channel_parameter,
        "min_density_eigenvalue": min_density_eig,
        "max_trace_error": max_trace_error,
    }


def reconstruct_model(instance_row: dict, angle_rows: list[dict]):
    matching = sorted(
        (row for row in angle_rows if row["instance_id"] == instance_row["instance_id"]),
        key=lambda row: int(row["layer"]),
    )
    if not matching:
        raise ValueError(f"missing angle rows for {instance_row['instance_id']}")
    inst = qaoa.QAOAInstance(
        n=int(instance_row["size_n"]),
        weight=int(instance_row["sector_weight"]),
        edges=edge_tuple(json.loads(instance_row["edges_json"])),
        weights=tuple(float(x) for x in json.loads(instance_row["weights_json"])),
        mixer_edges=edge_tuple(json.loads(instance_row["mixer_edges_json"])),
        name=str(instance_row["instance_id"]),
    )
    gammas = np.asarray([float(row["gamma"]) for row in matching], dtype=np.float64)
    betas = np.asarray([float(row["beta"]) for row in matching], dtype=np.float64)
    channel = noise.heterogeneous_ad_pd(inst.n, seed=int(instance_row["noise_channel_seed"]))
    return cf.build_model(inst, gammas, betas, channel)


def _angle_rows(model, instance_row: dict) -> list[dict]:
    rows = []
    depth = int(model.gammas.size)
    noiseless_cost = _noiseless_cost(model)
    for idx, (gamma, beta) in enumerate(zip(model.gammas, model.betas), start=1):
        rows.append({
            "instance_id": model.inst.name,
            "size_n": model.inst.n,
            "sector_weight": model.inst.weight,
            "candidate_index": instance_row["candidate_index"],
            "depth": depth,
            "layer": idx,
            "gamma": float(gamma),
            "beta": float(beta),
            "noiseless_cost": noiseless_cost,
            "optimizer": "scipy.optimize.minimize:L-BFGS-B",
            "angle_seed": instance_row["qaoa_angle_seed"],
            "angle_restarts": instance_row["qaoa_angle_restarts"],
            "bounds": "[0,2*pi]",
            "selection_status": instance_row["selection_status"],
        })
    return rows


def _lambda2_gap_summary(model, ps: list[float]) -> tuple[float, float]:
    relative_gaps = []
    spectral_gaps = []
    for p in ps:
        lam1, lam2 = spectral_gap(model.rho_p(float(p)))
        gap = lam1 - lam2
        relative_gaps.append(gap / lam1 if lam1 > 0 else 0.0)
        spectral_gaps.append(gap)
    return float(min(relative_gaps)), float(min(spectral_gaps))


def _density_summary(model, ps: list[float]) -> tuple[float, float]:
    min_eig = float("inf")
    max_trace_error = 0.0
    for p in ps:
        rho = model.rho_p(float(p))
        eigs = ordered_eigenvalues(rho)
        min_eig = min(min_eig, float(np.min(eigs)))
        max_trace_error = max(max_trace_error, float(abs(np.trace(rho) - 1.0)))
    return min_eig, max_trace_error


def _max_channel_parameter(model, max_noise_strength: float) -> float:
    params = []
    for _proc, rates in model.channel.processes:
        params.extend(float(rate) * max_noise_strength for rate in rates)
    return float(max(params))


def _noiseless_cost(model) -> float:
    diag = qaoa.cost_diagonal(model.inst)
    return float(np.real(np.sum(diag * (np.abs(model.psi) ** 2))))


def _declared_p_values(config: dict) -> list[float]:
    values: set[float] = set()
    for spec in config["experiments"].values():
        if "p_fixed" in spec:
            values.add(float(spec["p_fixed"]))
        for key, val in spec.items():
            if key.startswith("p_grid") and isinstance(val, list):
                values.update(float(x) for x in val)
    return sorted(values)


def _diagnostics_markdown(config: dict, rows: list[dict]) -> str:
    threshold = float(config["instance_selection"]["min_entanglement_entropy_bits"])
    target = int(config["instance_selection"]["n_target_per_size"])
    lines = [
        "# Instance selection diagnostics",
        "",
        "Status: pap_freeze_ready.",
        "",
        f"Entropy threshold I2: {threshold} bits.",
        f"Included target per size: {target}.",
        "",
    ]
    for n in [int(x) for x in config["instance_selection"]["sizes"]]:
        size_rows = [row for row in rows if int(row["size_n"]) == n]
        entropies = [float(row["entanglement_entropy_bits"]) for row in size_rows]
        included = [row for row in size_rows if row["selection_status"] == "included"]
        rejected = [row for row in size_rows if row["selection_status"] == "rejected"]
        i2_rejected = [row for row in rejected if row["failing_criterion"] == "I2"]
        lines.extend([
            f"## n={n}",
            "",
            f"- evaluated: {len(size_rows)}",
            f"- included: {len(included)}",
            f"- rejected: {len(rejected)}",
            f"- entropy range: [{min(entropies):.12g}, {max(entropies):.12g}]",
            f"- I2 entropy rejections: {len(i2_rejected)}",
        ])
        if i2_rejected:
            lines.append("- I2 threshold bites in the evaluated candidate set.")
        else:
            lines.append(
                "- I2 threshold did not reject any evaluated candidate before the target "
                "included count was reached."
            )
        lines.append("")
    return "\n".join(lines)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: _stable_csv_cell(row[key]) for key in fieldnames} for row in rows])


def _json(value) -> str:
    return json.dumps(_stable_json_value(value), separators=(",", ":"))


def _pinned_instance(inst: qaoa.QAOAInstance) -> qaoa.QAOAInstance:
    return qaoa.QAOAInstance(
        n=inst.n,
        weight=inst.weight,
        edges=inst.edges,
        weights=tuple(_freeze_float(w) for w in inst.weights),
        mixer_edges=inst.mixer_edges,
        name=inst.name,
    )


def _pinned_array(values) -> np.ndarray:
    return np.asarray([_freeze_float(x) for x in np.asarray(values).ravel()], dtype=np.float64)


def _stable_csv_cell(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return f"{_freeze_float(value):.{FREEZE_FLOAT_DIGITS}g}"
    return value


def _stable_json_value(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return _freeze_float(value)
    if isinstance(value, tuple):
        return [_stable_json_value(x) for x in value]
    if isinstance(value, list):
        return [_stable_json_value(x) for x in value]
    return value


def _freeze_float(value: float) -> float:
    value = float(value)
    if not np.isfinite(value):
        return value
    return float(f"{value:.{FREEZE_FLOAT_DIGITS}g}")


if __name__ == "__main__":
    raise SystemExit(main())
