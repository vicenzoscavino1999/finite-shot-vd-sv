"""Verify registered PAP freeze manifests against the current checkout.

This is the audit check that compares recorded hashes with the files present in
the working tree. It is intentionally separate from ``hash_pap.py --check-only``,
which only recomputes a hypothetical hash for the current tree.

Exit code is nonzero for any aggregate/hash-file mismatch, missing target, or
unexpected content drift. v1 allows only paths listed in
``pap/known_v1_drift.txt``. v2 is expected to have zero drift.
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
KNOWN_V1_DRIFT = REPO_ROOT / "pap" / "known_v1_drift.txt"
CHECKS = (
    {
        "label": "v1",
        "manifest": REPO_ROOT / "freeze_manifest.json",
        "hash_file": REPO_ROOT / "PAP_HASH.txt",
        "allowlist": KNOWN_V1_DRIFT,
        "expect_zero_drift": False,
    },
    {
        "label": "v2",
        "manifest": REPO_ROOT / "freeze_manifest_v2.json",
        "hash_file": REPO_ROOT / "PAP_HASH_v2.txt",
        "allowlist": None,
        "expect_zero_drift": True,
    },
)


@dataclass
class ManifestResult:
    label: str
    manifest_name: str
    frozen_commit: str
    pap_hash: str
    target_count: int
    ok: int
    expected_drift: int
    changed: int
    missing: int
    aggregate_ok: bool
    hash_file_ok: bool
    details: list[str]

    @property
    def passed(self) -> bool:
        return self.aggregate_ok and self.hash_file_ok and self.changed == 0 and self.missing == 0

    @property
    def verdict(self) -> str:
        if not self.passed:
            return "FAIL"
        if self.expected_drift:
            return "INTACT_WITH_EXPECTED_DRIFT"
        return "INTACT_ZERO_DRIFT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="print per-target non-OK detail")
    args = parser.parse_args(argv)

    results = [verify_manifest_spec(spec) for spec in CHECKS]
    _print_summary(results)
    if args.verbose:
        _print_details(results)
    return 0 if all(result.passed for result in results) else 1


def verify_manifest_spec(spec: dict[str, Any]) -> ManifestResult:
    label = str(spec["label"])
    manifest_path = Path(spec["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hash_file = Path(spec["hash_file"])
    allowlist = _load_allowlist(spec.get("allowlist"))

    aggregate = _aggregate_hash(manifest)
    aggregate_ok = aggregate == manifest["pap_hash"]
    hash_file_ok = _hash_file_matches(hash_file, manifest["pap_hash"], manifest["frozen_commit_sha"])

    ok = expected_drift = changed = missing = 0
    details: list[str] = []
    for entry in manifest["targets"]:
        path = str(entry["path"])
        target = REPO_ROOT / path
        if not target.is_file():
            missing += 1
            details.append(f"{label} | MISSING | {path}")
            continue

        raw = target.read_bytes()
        raw_matches = _matches_entry(entry, raw)
        logical_matches = raw_matches or _logical_checkout_matches(entry, path)

        if raw_matches or (logical_matches and path not in allowlist):
            ok += 1
            continue

        if path in allowlist:
            if logical_matches or _recoverable_at_frozen_commit(entry, manifest["frozen_commit_sha"], path):
                expected_drift += 1
                details.append(f"{label} | EXPECTED-DRIFT | {path} | {allowlist[path]}")
            else:
                changed += 1
                details.append(f"{label} | CHANGED | {path} | allowlisted path no longer matches any recoverable representation")
            continue

        changed += 1
        details.append(f"{label} | CHANGED | {path}")

    return ManifestResult(
        label=label,
        manifest_name=manifest_path.name,
        frozen_commit=str(manifest["frozen_commit_sha"]),
        pap_hash=str(manifest["pap_hash"]),
        target_count=len(manifest["targets"]),
        ok=ok,
        expected_drift=expected_drift,
        changed=changed,
        missing=missing,
        aggregate_ok=aggregate_ok,
        hash_file_ok=hash_file_ok,
        details=details,
    )


def _load_allowlist(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    allowlist: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        item, _, reason = line.partition("|")
        allowlist[item.strip()] = reason.strip() or "expected drift"
    return allowlist


def _hash_file_matches(path: Path, pap_hash: str, frozen_commit: str) -> bool:
    if not path.is_file():
        return False
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values.get("PAP_HASH") == pap_hash and values.get("FROZEN_COMMIT_SHA") == frozen_commit


def _matches_entry(entry: dict[str, Any], data: bytes) -> bool:
    return len(data) == int(entry["bytes"]) and hashlib.sha256(data).hexdigest() == str(entry["sha256"])


def _logical_checkout_matches(entry: dict[str, Any], path: str) -> bool:
    try:
        blob = _git_show_bytes("HEAD", path)
    except subprocess.CalledProcessError:
        return False
    return any(_matches_entry(entry, candidate) for _label, candidate in _candidate_bytes(blob, path))


def _recoverable_at_frozen_commit(entry: dict[str, Any], commit: str, path: str) -> bool:
    try:
        blob = _git_show_bytes(commit, path)
    except subprocess.CalledProcessError:
        return False
    return any(_matches_entry(entry, candidate) for _label, candidate in _candidate_bytes(blob, path))


def _candidate_bytes(blob: bytes, path: str) -> list[tuple[str, bytes]]:
    candidates = [("git_blob", blob)]
    if _is_text_path(path) and b"\n" in blob and b"\r\n" not in blob:
        crlf = blob.replace(b"\n", b"\r\n")
        candidates.append(("windows_crlf_checkout", crlf))
        newline_positions = [idx for idx, byte in enumerate(crlf) if byte == 10]
        if len(newline_positions) <= 200:
            for occurrence, lf_index in enumerate(newline_positions):
                if lf_index > 0 and crlf[lf_index - 1] == 13:
                    mixed = crlf[: lf_index - 1] + crlf[lf_index:]
                    candidates.append((f"legacy_mixed_crlf_one_lf_{occurrence}", mixed))
    return candidates


def _is_text_path(path: str) -> bool:
    return Path(path).suffix.lower() in {".csv", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}


def _git_show_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "show", f"{commit}:{path}"],
        stderr=subprocess.STDOUT,
    )


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


def _print_summary(results: list[ManifestResult]) -> None:
    print("| manifest | frozen_commit | pap_hash | targets | OK | EXPECTED-DRIFT | CHANGED | MISSING | aggregate | hash_file | verdict |")
    print("|---|---|---|---:|---:|---:|---:|---:|---|---|---|")
    for result in results:
        print(
            f"| {result.manifest_name} ({result.label}) "
            f"| {result.frozen_commit[:12]} "
            f"| {result.pap_hash[:12]} "
            f"| {result.target_count} "
            f"| {result.ok} "
            f"| {result.expected_drift} "
            f"| {result.changed} "
            f"| {result.missing} "
            f"| {'OK' if result.aggregate_ok else 'FAIL'} "
            f"| {'OK' if result.hash_file_ok else 'FAIL'} "
            f"| {result.verdict} |"
        )


def _print_details(results: list[ManifestResult]) -> None:
    for result in results:
        if not result.details:
            continue
        print(f"\n{result.manifest_name} details:")
        for detail in result.details:
            print(detail)


if __name__ == "__main__":
    raise SystemExit(main())
