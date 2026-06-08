"""Refresh the canonical Level 1 reference manifest and checksum file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = REPO_ROOT / "reproducibility" / "reference"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def created_utc(explicit: str | None) -> str:
    if explicit:
        return explicit
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(epoch)))
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_run_manifest(reference: Path) -> dict[str, Any]:
    path = reference / "manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--created-utc")
    args = parser.parse_args(argv)

    reference = args.reference.resolve()
    run_manifest = read_run_manifest(reference)
    csv_files = sorted(path for path in reference.glob("*.csv") if path.is_file())
    if not csv_files:
        raise SystemExit(f"no CSV reference files found in {reference}")

    files = {path.name: sha256(path) for path in csv_files}
    checksum_lines = [
        f"{digest.removeprefix('sha256:')}  {name}" for name, digest in sorted(files.items())
    ]
    (reference / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "linux-canonical-reference-v1",
        "reference_role": "canonical_linux_amd64_docker_level1",
        "numeric_identity_contract": (
            "Canonical linux/amd64 Docker runs are expected to match these CSV "
            "references with --exact-numeric. Non-canonical platforms are "
            "verified with the tolerances in reproducibility/config/tolerances.yaml."
        ),
        "created_utc": created_utc(args.created_utc),
        "generator": {
            "driver": "reproducibility/run_all_current.py",
            "level": run_manifest.get("level"),
            "mode": run_manifest.get("mode"),
            "run_manifest": "manifest.json" if run_manifest else None,
            "run_manifest_sha256": sha256(reference / "manifest.json") if run_manifest else None,
        },
        "source_state": {
            "git_commit_sha": run_manifest.get("git_commit_sha"),
            "git_dirty_excluding_output": run_manifest.get("git_dirty_excluding_output"),
            "git_dirty_paths_excluding_output": run_manifest.get(
                "git_dirty_paths_excluding_output"
            ),
        },
        "pap_freezes": run_manifest.get("pap_freezes"),
        "canonical_platform": {
            "platform": run_manifest.get("platform"),
            "python_version": run_manifest.get("python_version"),
            "dependencies": run_manifest.get("dependencies"),
            "deterministic_environment": run_manifest.get("deterministic_environment"),
            "environment_lock": run_manifest.get("environment_lock"),
            "canonical_container": run_manifest.get("canonical_container"),
            "rng_policy": run_manifest.get("rng_policy"),
        },
        "files": files,
    }
    (reference / "reference_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"REFERENCE_MANIFEST_WRITTEN files={len(files)} reference={repo_relative(reference)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
