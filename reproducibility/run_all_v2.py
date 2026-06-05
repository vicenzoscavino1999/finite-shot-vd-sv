"""Level 1 reproduction driver (REPRODUCIBILITY_PLAN: run_all.py).

Runs the white-box experiments E1-E4, E7, writes their canonical CSVs and a
provenance manifest.  Level 1 has no Qiskit dependency.  Levels 2 (Aer) and 3
(hardware analysis-from-counts) are Phase B and not implemented here.
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

LOG = logging.getLogger("run_all")
CONFIG = REPO_ROOT / "reproducibility" / "config"

EXPERIMENTS = [
    "experiments.e1_quotient_decomposition",
    "experiments.e2_c_sv_zero",
    "experiments.e3_delta_vd_generator",
    "experiments.e4_delta_sv_firstorder",
    "experiments.e5_denominator_concentration",
    "experiments.e7_certified_crossing",
    "experiments.e7_resource_observable_sensitivity",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def _git_commit() -> tuple[str, bool]:
    try:
        sha = subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                                      text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
            text=True, stderr=subprocess.DEVNULL).strip())
        return sha, dirty
    except Exception:
        return "unknown", True


def _pap_hash() -> str:
    f = REPO_ROOT / "PAP_HASH.txt"
    if not f.exists():
        return "absent"
    first = f.read_text(encoding="utf-8").splitlines()[0] if f.read_text(encoding="utf-8") else ""
    return first.strip()


def _rng_policy(path: Path | None = None) -> dict:
    path = path or (CONFIG / "rng_policy.yaml")
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def preflight(level: int, output: Path) -> list[str]:
    """Lightweight pre-flight checks. Returns a list of warning strings."""
    import numpy as np
    import scipy

    warnings = []
    for var in ("PYTHONHASHSEED", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        if os.environ.get(var) is None:
            warnings.append(f"env {var} not set (tight cross-platform tolerances may not hold)")
    if platform.machine().lower() not in ("x86_64", "amd64"):
        warnings.append(f"architecture {platform.machine()} is not x86_64 (ULP differences possible)")
    output.mkdir(parents=True, exist_ok=True)
    if not os.access(output, os.W_OK):
        raise SystemExit(f"output directory not writable: {output}")
    if _pap_hash() == "absent":
        warnings.append("PAP hash absent: outputs are development/exploratory, not confirmatory")
    LOG.info("numpy %s, scipy %s, python %s", np.__version__, scipy.__version__,
             platform.python_version())
    for w in warnings:
        LOG.warning(w)
    return warnings


def run(mode: str, level: int, output: Path, rng_policy_path: Path | None = None) -> Path:
    import importlib

    if level != 1:
        raise SystemExit(f"level {level} not implemented in the Phase A MVP (Level 1 only)")
    output.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    outputs = {}
    rng_policy = _rng_policy(rng_policy_path)
    seeds = rng_policy.get("per_experiment_seed", {})
    for modname in EXPERIMENTS:
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

    sha, dirty = _git_commit()
    import numpy as np
    import scipy

    manifest = {
        "git_commit_sha": sha,
        "git_dirty": dirty,
        "pap_hash": _pap_hash(),
        "level": level,
        "mode": mode,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dependencies": {"numpy": np.__version__, "scipy": scipy.__version__},
        "rng_policy": {
            "path": str(rng_policy_path or (CONFIG / "rng_policy.yaml")),
            "per_experiment_seed": seeds,
        },
        "runtime_seconds": round(time.time() - t0, 3),
        "execution_mode": "clean",
        "recovered_blocks": 0,
        "outputs": outputs,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    LOG.info("wrote manifest.json (%.1fs, %d outputs)", manifest["runtime_seconds"], len(outputs))
    return output


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Level 1 VD/SV reproduction driver")
    ap.add_argument("--mode", choices=["fast", "full"], default="fast")
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--output", default=str(REPO_ROOT / "results"))
    ap.add_argument("--rng-policy", default=str(CONFIG / "rng_policy_v2.yaml"))
    ap.add_argument("--check-env-only", action="store_true")
    ap.add_argument("--from-archived-counts", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    output = Path(args.output)
    preflight(args.level, output)
    if args.check_env_only:
        LOG.info("environment check complete")
        return 0
    run(args.mode, args.level, output, Path(args.rng_policy))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
