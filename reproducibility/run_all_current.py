"""Current reproducibility driver for the post-freeze repository.

The PAP-frozen drivers (``run_all.py`` and ``run_all_v2.py``) are intentionally
left unchanged so the registered freeze manifests remain auditable. This driver
is the active pre-release command used by Makefile, Docker, and CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LOG = logging.getLogger("run_all_current")
CONFIG = REPO_ROOT / "reproducibility" / "config"

LEVEL1_EXPERIMENTS = [
    "experiments.e1_quotient_decomposition",
    "experiments.e2_c_sv_zero",
    "experiments.e3_delta_vd_generator",
    "experiments.e4_delta_sv_firstorder",
    "experiments.e5_denominator_concentration",
    "experiments.e7_certified_crossing",
    "experiments.e7_resource_observable_sensitivity",
]

DETERMINISTIC_ENV_VARS = (
    "PYTHONHASHSEED",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
)
EXPECTED_DETERMINISTIC_ENV = {
    "PYTHONHASHSEED": "0",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _git_commit(exclude_paths: tuple[Path, ...] = ()) -> tuple[str, bool, list[str]]:
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=all"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
    except Exception:
        override = os.environ.get("REPRO_GIT_COMMIT_SHA")
        if override:
            dirty = os.environ.get("REPRO_GIT_DIRTY", "false").lower() in {"1", "true", "yes"}
            paths = os.environ.get("REPRO_GIT_DIRTY_PATHS", "")
            return override, dirty, [p for p in paths.split(";") if p]
        return "unknown", True, ["git unavailable"]

    relevant = []
    for line in status:
        if len(line) < 4:
            continue
        status_path = line[3:].strip().strip('"')
        if " -> " in status_path:
            status_path = status_path.split(" -> ", 1)[1].strip().strip('"')
        abs_path = REPO_ROOT / status_path.replace("/", os.sep)
        if any(_is_under(abs_path, excluded) for excluded in exclude_paths):
            continue
        relevant.append(line)
    return sha, bool(relevant), relevant


def _hash_file_value(path: Path, key: str) -> str:
    if not path.exists():
        return "absent"
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        lhs, rhs = line.split("=", 1)
        if lhs.strip() == key:
            return rhs.strip()
    return "absent"


def _file_hash_record(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    return {"path": _repo_relative(path), "sha256": _sha256(path)}


def _rng_policy(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def preflight(output: Path, strict_env: bool = False) -> list[str]:
    """Run lightweight environment checks and return warnings."""
    import numpy as np
    import scipy

    warnings = []
    for var, expected in EXPECTED_DETERMINISTIC_ENV.items():
        actual = os.environ.get(var)
        if actual is None:
            warnings.append(f"env {var} not set (tight cross-platform tolerances may not hold)")
        elif actual != expected:
            warnings.append(
                f"env {var}={actual!r}, expected {expected!r} "
                "(canonical exact reproduction may not hold)"
            )
    if platform.machine().lower() not in ("x86_64", "amd64"):
        warnings.append(f"architecture {platform.machine()} is not x86_64 (ULP differences possible)")
    if strict_env and warnings:
        raise SystemExit("strict environment check failed:\n" + "\n".join(warnings))
    output.mkdir(parents=True, exist_ok=True)
    if not os.access(output, os.W_OK):
        raise SystemExit(f"output directory not writable: {output}")
    LOG.info("numpy %s, scipy %s, python %s", np.__version__, scipy.__version__,
             platform.python_version())
    for warning in warnings:
        LOG.warning(warning)
    return warnings


def run_level1(
    mode: str,
    output: Path,
    rng_policy_path: Path,
    include_volatile_provenance: bool = False,
) -> Path:
    import importlib
    import numpy as np
    import scipy

    output.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    outputs = {}
    rng_policy = _rng_policy(rng_policy_path)
    seeds = rng_policy.get("per_experiment_seed", {})

    for modname in LEVEL1_EXPERIMENTS:
        mod = importlib.import_module(modname)
        short_name = modname.rsplit(".", 1)[-1]
        seed = seeds.get(short_name)
        LOG.info("running %s (mode=%s)", modname, mode)
        kwargs = {"mode": mode}
        if seed is not None:
            kwargs["seed"] = int(seed)
        path = Path(mod.run(output, **kwargs))
        outputs[path.name] = _sha256(path)
        LOG.info("  -> %s", path.name)

    sha, dirty, dirty_paths = _git_commit(exclude_paths=(output,))
    manifest = {
        "schema_version": "current-run-manifest-v1",
        "git_commit_sha": sha,
        "git_dirty_excluding_output": dirty,
        "git_dirty_paths_excluding_output": dirty_paths,
        "pap_freezes": {
            "v1": {
                "pap_hash": _hash_file_value(REPO_ROOT / "PAP_HASH.txt", "PAP_HASH"),
                "frozen_commit_sha": _hash_file_value(REPO_ROOT / "PAP_HASH.txt", "FROZEN_COMMIT_SHA"),
            },
            "v2": {
                "pap_hash": _hash_file_value(REPO_ROOT / "PAP_HASH_v2.txt", "PAP_HASH"),
                "frozen_commit_sha": _hash_file_value(REPO_ROOT / "PAP_HASH_v2.txt", "FROZEN_COMMIT_SHA"),
            },
        },
        "level": 1,
        "mode": mode,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {"numpy": np.__version__, "scipy": scipy.__version__},
        "deterministic_environment": {
            var: os.environ.get(var) for var in DETERMINISTIC_ENV_VARS
        },
        "environment_lock": {
            "requirements_lock": _file_hash_record(REPO_ROOT / "requirements.lock"),
        },
        "canonical_container": {
            "base_image": os.environ.get("REPRO_DOCKER_BASE_IMAGE"),
            "base_digest": os.environ.get("REPRO_DOCKER_BASE_DIGEST"),
            "platform": os.environ.get("REPRO_DOCKER_PLATFORM"),
            "image_digest": os.environ.get("REPRO_DOCKER_IMAGE_DIGEST"),
        },
        "rng_policy": {
            "path": _repo_relative(rng_policy_path),
            "per_experiment_seed": seeds,
        },
        "outputs": outputs,
    }
    if include_volatile_provenance:
        manifest["volatile_provenance"] = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "runtime_seconds": round(time.time() - t0, 3),
        }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    LOG.info("wrote manifest.json (%d outputs)", len(outputs))
    return output


def run_level3_from_archives(bootstrap_reps: int) -> int:
    from scripts.reanalyze_level3_archives import main as reanalyze_main

    return int(reanalyze_main(["--bootstrap-reps", str(int(bootstrap_reps)), "--quiet"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Current VD/SV reproducibility driver")
    parser.add_argument("--mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--level", type=int, choices=[1, 3], default=1)
    parser.add_argument("--output", default=str(REPO_ROOT / "results"))
    parser.add_argument("--rng-policy", default=str(CONFIG / "rng_policy.yaml"))
    parser.add_argument("--check-env-only", action="store_true")
    parser.add_argument("--strict-env", action="store_true")
    parser.add_argument("--from-archived-counts", action="store_true")
    parser.add_argument("--level3-bootstrap-reps", type=int, default=2000)
    parser.add_argument("--include-volatile-provenance", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    output = Path(args.output)
    preflight(output, strict_env=bool(args.strict_env))
    if args.check_env_only:
        LOG.info("environment check complete")
        return 0

    if args.from_archived_counts or args.level == 3:
        return run_level3_from_archives(args.level3_bootstrap_reps)
    run_level1(
        args.mode,
        output,
        Path(args.rng_policy),
        include_volatile_provenance=bool(args.include_volatile_provenance),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
