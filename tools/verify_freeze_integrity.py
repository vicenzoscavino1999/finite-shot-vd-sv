"""Verify PAP freeze manifests against their declared frozen commits.

This is intentionally different from ``pap/hash_pap.py --check-only``:

- ``hash_pap.py --check-only`` validates the *current* clean checkout and prints
  the hash that would be generated today.
- This tool validates an existing manifest historically, by reading every target
  from the manifest's own ``frozen_commit_sha`` via git and comparing bytes,
  sha256, and aggregate PAP hash.

That distinction matters after append-only amendments: HEAD may contain later
tools and analyses, while the original freeze remains auditable at its archived
commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFESTS = (
    REPO_ROOT / "freeze_manifest.json",
    REPO_ROOT / "freeze_manifest_v2.json",
)
DEFAULT_HASH_FILES = {
    "freeze_manifest.json": REPO_ROOT / "PAP_HASH.txt",
    "freeze_manifest_v2.json": REPO_ROOT / "PAP_HASH_v2.txt",
}


@dataclass(frozen=True)
class VerificationResult:
    manifest_path: Path
    frozen_commit_sha: str
    pap_hash: str
    target_count: int
    mismatches: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifests",
        nargs="*",
        type=Path,
        help="Manifest(s) to verify. Defaults to freeze_manifest.json and freeze_manifest_v2.json.",
    )
    parser.add_argument(
        "--hash-file",
        type=Path,
        help="Optional PAP_HASH*.txt file for a single manifest verification.",
    )
    args = parser.parse_args(argv)

    manifests = args.manifests or list(DEFAULT_MANIFESTS)
    if args.hash_file and len(manifests) != 1:
        parser.error("--hash-file can only be used with exactly one manifest")

    failures: list[VerificationResult] = []
    for manifest_path in manifests:
        manifest_path = _resolve_path(manifest_path)
        hash_file = args.hash_file
        if hash_file is None:
            hash_file = DEFAULT_HASH_FILES.get(manifest_path.name)
        result = verify_manifest(manifest_path, hash_file=hash_file)
        _print_result(result)
        if not result.passed:
            failures.append(result)

    return 1 if failures else 0


def verify_manifest(manifest_path: str | Path, hash_file: str | Path | None = None) -> VerificationResult:
    manifest_path = _resolve_path(Path(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frozen_commit = str(manifest["frozen_commit_sha"])
    recorded_pap_hash = str(manifest["pap_hash"])
    mismatches: list[str] = []

    recomputed_manifest_hash = _aggregate_hash(manifest)
    if recomputed_manifest_hash != recorded_pap_hash:
        mismatches.append(
            "aggregate pap_hash mismatch: "
            f"manifest={recorded_pap_hash} recomputed={recomputed_manifest_hash}"
        )

    if hash_file is not None:
        mismatches.extend(_verify_hash_file(_resolve_path(Path(hash_file)), recorded_pap_hash, frozen_commit))

    for entry in manifest["targets"]:
        relpath = str(entry["path"])
        try:
            data = _git_show_bytes(frozen_commit, relpath)
        except subprocess.CalledProcessError as exc:
            mismatches.append(f"{relpath}: missing at commit {frozen_commit} ({exc.returncode})")
            continue
        if not _entry_matches_any_candidate(entry, data):
            candidates = [
                f"{label}:bytes={len(candidate)}:sha256={hashlib.sha256(candidate).hexdigest()}"
                for label, candidate in _candidate_bytes(data, relpath)
            ]
            mismatches.append(
                f"{relpath}: no byte representation matches manifest "
                f"bytes={entry['bytes']} sha256={entry['sha256']} "
                f"candidates=[{'; '.join(candidates)}]"
            )

    return VerificationResult(
        manifest_path=manifest_path,
        frozen_commit_sha=frozen_commit,
        pap_hash=recorded_pap_hash,
        target_count=len(manifest["targets"]),
        mismatches=tuple(mismatches),
    )


def _verify_hash_file(path: Path, pap_hash: str, frozen_commit: str) -> list[str]:
    if not path.exists():
        return [f"{path.name}: hash file missing"]
    values = _parse_hash_file(path)
    mismatches = []
    if values.get("PAP_HASH") != pap_hash:
        mismatches.append(f"{path.name}: PAP_HASH mismatch")
    if values.get("FROZEN_COMMIT_SHA") != frozen_commit:
        mismatches.append(f"{path.name}: FROZEN_COMMIT_SHA mismatch")
    return mismatches


def _parse_hash_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _entry_matches_any_candidate(entry: dict[str, Any], blob_data: bytes) -> bool:
    expected_bytes = int(entry["bytes"])
    expected_sha = str(entry["sha256"])
    for _label, candidate in _candidate_bytes(blob_data, str(entry["path"])):
        if len(candidate) == expected_bytes and hashlib.sha256(candidate).hexdigest() == expected_sha:
            return True
    return False


def _candidate_bytes(blob_data: bytes, relpath: str) -> list[tuple[str, bytes]]:
    candidates: list[tuple[str, bytes]] = []
    current_path = REPO_ROOT / relpath
    if current_path.is_file():
        candidates.append(("current_worktree", current_path.read_bytes()))
    candidates.append(("git_blob", blob_data))
    if _is_text_path(relpath) and b"\n" in blob_data and b"\r\n" not in blob_data:
        candidates.append(("windows_crlf_checkout", blob_data.replace(b"\n", b"\r\n")))
    return candidates


def _is_text_path(relpath: str) -> bool:
    suffix = Path(relpath).suffix.lower()
    return suffix in {
        ".csv",
        ".json",
        ".md",
        ".py",
        ".txt",
        ".yaml",
        ".yml",
    }


def _aggregate_hash(payload: dict[str, Any]) -> str:
    stable = {
        "schema_version": payload["schema_version"],
        "hash_algorithm": payload["hash_algorithm"],
        "frozen_commit_sha": payload["frozen_commit_sha"],
        "targets": [
            {
                "category": entry["category"],
                "path": entry["path"],
                "bytes": entry["bytes"],
                "sha256": entry["sha256"],
            }
            for entry in payload["targets"]
        ],
    }
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_show_bytes(commit: str, relpath: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "show", f"{commit}:{relpath}"],
        stderr=subprocess.STDOUT,
    )


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _print_result(result: VerificationResult) -> None:
    if result.passed:
        print(
            "FREEZE INTEGRITY PASS: "
            f"{result.manifest_path.name} commit={result.frozen_commit_sha} "
            f"targets={result.target_count} pap_hash={result.pap_hash}"
        )
        return
    print(
        "FREEZE INTEGRITY FAIL: "
        f"{result.manifest_path.name} commit={result.frozen_commit_sha} "
        f"targets={result.target_count} pap_hash={result.pap_hash}",
        file=sys.stderr,
    )
    for mismatch in result.mismatches:
        print(f"  - {mismatch}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
