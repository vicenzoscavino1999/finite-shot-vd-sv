"""Stage 1 submission, dry-run, offline fixture, and archive builder."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qiskit_aer.primitives import SamplerV2 as AerSamplerV2

from level2.noise_model import build_noise_model, build_aer_simulator, noise_model_summary
from level3.archive import write_archive
from level3.budget import (
    BudgetExceeded,
    enforce_budget,
    estimate_budget,
    render_budget_estimate,
)
from level3.circuits import MIXER_TROTTER_STEPS, build_stage1_circuits, transpile_stage1_bundle
from level3.config import ARCHIVE_DIR, Stage1Config


def dry_run(config: Stage1Config, backend: Any | None = None) -> dict[str, Any]:
    backend = build_aer_simulator(noisy=True) if backend is None else backend
    bundle = build_stage1_circuits(config.instance_id)
    transpiled = transpile_stage1_bundle(
        bundle,
        backend=backend,
        optimization_level=config.optimization_level,
        seed_transpiler=config.seed_transpiler,
    )
    estimate = estimate_budget(
        [circuit.depth() for circuit in transpiled.circuits],
        shots_per_circuit=config.shots_per_circuit,
        max_total_shots=config.max_total_shots,
        near_cap_fraction=config.near_cap_fraction,
    )
    enforce_budget(
        estimate,
        require_near_cap_confirmation=False,
        near_cap_confirmed=False,
    )
    return {
        "mode": "dry_run",
        "budget": estimate,
        "bundle": transpiled,
    }


def run_offline_pipeline(
    config: Stage1Config,
    archive_name: str = "example_offline_counts.json.gz",
    created_at_utc: str | None = None,
    confirm_near_cap: bool = False,
) -> tuple[Path, dict[str, Any]]:
    backend = build_aer_simulator(noisy=True)
    bundle = build_stage1_circuits(config.instance_id)
    transpiled = transpile_stage1_bundle(
        bundle,
        backend=backend,
        optimization_level=config.optimization_level,
        seed_transpiler=config.seed_transpiler,
    )
    estimate = estimate_budget(
        [circuit.depth() for circuit in transpiled.circuits],
        shots_per_circuit=config.shots_per_circuit,
        max_total_shots=config.max_total_shots,
        near_cap_fraction=config.near_cap_fraction,
    )
    enforce_budget(
        estimate,
        require_near_cap_confirmation=True,
        near_cap_confirmed=confirm_near_cap,
    )
    sampler = AerSamplerV2(
        seed=config.seed_simulator,
        options={
            "backend_options": {
                "noise_model": build_noise_model(),
                "seed_simulator": config.seed_simulator,
            }
        },
    )
    job = sampler.run(list(transpiled.circuits), shots=config.shots_per_circuit)
    result = job.result()
    counts = sampler_counts(result)
    payload = archive_payload(
        config=config,
        transpiled=transpiled,
        counts=counts,
        mode="offline_aer_sampler_v2",
        backend_name="AerSyntheticThermalReadoutV1",
        job_id=f"offline-aer-seed-{config.seed_simulator}",
        created_at_utc=created_at_utc,
        budget_estimate=estimate,
        extra_backend_metadata={"noise_model": noise_model_summary()},
    )
    archive_path = Path(config.archive_dir) / archive_name
    write_archive(archive_path, payload)
    return archive_path, payload


def submit_to_ibm(
    config: Stage1Config,
    archive_name: str | None = None,
    confirm_near_cap: bool = False,
    confirm_submit: bool = False,
) -> tuple[Path, dict[str, Any]]:
    if not confirm_submit:
        raise BudgetExceeded("real QPU submission requires --confirm-submit")
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService(channel=config.ibm_channel, region=config.ibm_region)
    backend = service.backend(config.backend_name)
    bundle = build_stage1_circuits(config.instance_id)
    transpiled = transpile_stage1_bundle(
        bundle,
        backend=backend,
        optimization_level=config.optimization_level,
        seed_transpiler=config.seed_transpiler,
    )
    estimate = estimate_budget(
        [circuit.depth() for circuit in transpiled.circuits],
        shots_per_circuit=config.shots_per_circuit,
        max_total_shots=config.max_total_shots,
        near_cap_fraction=config.near_cap_fraction,
    )
    enforce_budget(
        estimate,
        require_near_cap_confirmation=True,
        near_cap_confirmed=confirm_near_cap,
    )
    sampler = SamplerV2(mode=backend)
    job = sampler.run(list(transpiled.circuits), shots=config.shots_per_circuit)
    result = job.result()
    counts = sampler_counts(result)
    job_id = job.job_id() if hasattr(job, "job_id") else str(job)
    if archive_name is None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        archive_name = f"ibm_marrakesh_{config.instance_id}_{stamp}_{job_id}.json.gz"
    payload = archive_payload(
        config=config,
        transpiled=transpiled,
        counts=counts,
        mode="ibm_runtime_sampler_v2",
        backend_name=config.backend_name,
        job_id=job_id,
        created_at_utc=None,
        budget_estimate=estimate,
        extra_backend_metadata=backend_metadata(backend),
    )
    archive_path = Path(config.archive_dir) / archive_name
    write_archive(archive_path, payload)
    return archive_path, payload


def sampler_counts(result: Any) -> list[dict[str, int]]:
    out: list[dict[str, int]] = []
    for pub_result in result:
        data = pub_result.data
        bit_arrays = list(data.values())
        if len(bit_arrays) != 1:
            raise ValueError(f"expected exactly one classical register, got {list(data.keys())}")
        counts = bit_arrays[0].get_counts()
        out.append({str(key).replace(" ", ""): int(value) for key, value in counts.items()})
    return out


def archive_payload(
    config: Stage1Config,
    transpiled: Any,
    counts: list[dict[str, int]],
    mode: str,
    backend_name: str,
    job_id: str,
    created_at_utc: str | None,
    budget_estimate: Any,
    extra_backend_metadata: dict[str, Any],
) -> dict[str, Any]:
    if len(counts) != len(transpiled.labels):
        raise ValueError("counts length does not match circuit labels")
    created = created_at_utc or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "created_at_utc": created,
        "backend": {
            "name": backend_name,
            "metadata": extra_backend_metadata,
        },
        "submission": {
            "mode": mode,
            "job_id": job_id,
            "sampler": "SamplerV2",
            "dry_run_default": True,
        },
        "experiment": {
            "instance_id": transpiled.instance_id,
            "n": int(transpiled.n),
            "sector_weight": int(transpiled.sector_weight),
            "mu_ideal_noiseless_l2": float(transpiled.mu_ideal_noiseless_l2),
            "mu_ideal_hint": float(config.mu_ideal_hint),
            "mixer_trotter_steps": int(MIXER_TROTTER_STEPS),
            "observable_values_level1_order": [
                float(value)
                for value in transpiled.observable_values_level1_order
            ],
        },
        "shots": {
            "shots_per_circuit": int(config.shots_per_circuit),
            "total_shots": int(budget_estimate.total_shots),
            "max_total_shots": int(config.max_total_shots),
        },
        "budget": {
            "circuit_count": int(budget_estimate.circuit_count),
            "near_cap_fraction": float(budget_estimate.near_cap_fraction),
            "near_cap": bool(budget_estimate.near_cap),
            "max_circuit_depth": int(budget_estimate.max_circuit_depth),
            "estimated_qpu_seconds": float(budget_estimate.estimated_qpu_seconds),
        },
        "transpile": transpiled.transpile_metadata,
        "provenance": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "qiskit": _version("qiskit"),
            "qiskit_aer": _version("qiskit_aer"),
            "qiskit_ibm_runtime": _version("qiskit_ibm_runtime"),
        },
        "circuits": [
            {
                "label": label,
                "role": _role_for_label(label),
                "prepared_bit": _prepared_bit_for_label(label),
                "shots": int(sum(circuit_counts.values())),
                "counts": dict(sorted(circuit_counts.items())),
            }
            for label, circuit_counts in zip(transpiled.labels, counts, strict=True)
        ],
    }


def backend_metadata(backend: Any) -> dict[str, Any]:
    provider = getattr(backend, "provider", None)
    if callable(provider):
        try:
            provider = provider()
        except TypeError:
            provider = str(provider)
    return {
        "name": getattr(backend, "name", None),
        "num_qubits": getattr(backend, "num_qubits", None),
        "version": getattr(backend, "version", None),
        "provider": str(provider),
    }


def _role_for_label(label: str) -> str:
    if label == "qaoa_z":
        return "qaoa_z"
    if label.startswith("readout_calib_"):
        return "readout_calibration"
    raise ValueError(f"unknown circuit label: {label}")


def _prepared_bit_for_label(label: str) -> int | None:
    if label.endswith("_0"):
        return 0
    if label.endswith("_1"):
        return 1
    return None


def _version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return str(getattr(module, "__version__", "unknown"))


def build_config_from_args(args: argparse.Namespace) -> Stage1Config:
    return Stage1Config(
        instance_id=args.instance_id,
        backend_name=args.backend,
        ibm_channel=args.ibm_channel,
        ibm_region=args.ibm_region,
        optimization_level=args.optimization_level,
        seed_transpiler=args.seed_transpiler,
        seed_simulator=args.seed_simulator,
        shots_per_circuit=args.shots_per_circuit,
        max_total_shots=args.max_total_shots,
        near_cap_fraction=args.near_cap_fraction,
        archive_dir=args.archive_dir,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-id", default=Stage1Config().instance_id)
    parser.add_argument("--backend", default=Stage1Config().backend_name)
    parser.add_argument("--ibm-channel", default=Stage1Config().ibm_channel)
    parser.add_argument("--ibm-region", default=Stage1Config().ibm_region)
    parser.add_argument("--optimization-level", type=int, default=Stage1Config().optimization_level)
    parser.add_argument("--seed-transpiler", type=int, default=Stage1Config().seed_transpiler)
    parser.add_argument("--seed-simulator", type=int, default=Stage1Config().seed_simulator)
    parser.add_argument("--shots-per-circuit", type=int, default=Stage1Config().shots_per_circuit)
    parser.add_argument("--max-total-shots", type=int, default=Stage1Config().max_total_shots)
    parser.add_argument("--near-cap-fraction", type=float, default=Stage1Config().near_cap_fraction)
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVE_DIR)
    parser.add_argument("--archive-name", default="example_offline_counts.json.gz")
    parser.add_argument("--offline-execute", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--confirm-near-cap", action="store_true")
    parser.add_argument("--confirm-submit", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args(argv)

    config = build_config_from_args(args)
    try:
        if args.submit:
            archive_path, payload = submit_to_ibm(
                config,
                archive_name=None if args.archive_name == "example_offline_counts.json.gz" else args.archive_name,
                confirm_near_cap=args.confirm_near_cap,
                confirm_submit=args.confirm_submit,
            )
            print(f"ARCHIVE_WRITTEN {archive_path}")
            if args.print_json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.offline_execute:
            archive_path, payload = run_offline_pipeline(
                config,
                archive_name=args.archive_name,
                confirm_near_cap=args.confirm_near_cap,
            )
            print(f"ARCHIVE_WRITTEN {archive_path}")
            if args.print_json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        result = dry_run(config)
        print(render_budget_estimate(result["budget"]))
        print("DRY_RUN no submission; use --offline-execute for fake backend or --submit --confirm-submit for QPU")
        if args.print_json:
            print(json.dumps(result["bundle"].transpile_metadata, indent=2, sort_keys=True))
        return 0
    except BudgetExceeded as exc:
        print(f"BUDGET_ABORT {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
