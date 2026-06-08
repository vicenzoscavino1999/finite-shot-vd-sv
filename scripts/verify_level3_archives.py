"""Verify Level 3 consolidated analyses from archived counts without rewriting.

This is the archive-only Level 3 verifier: it reads committed ``*.json.gz``
count archives, recomputes the consolidated analyses in memory, and compares
them against the committed JSON summaries with tight numeric tolerances.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.reanalyze_level3_archives import CASES, analysis_for_case


ARCHIVE_DIR = REPO_ROOT / "level3" / "archive"
MANIFEST = ARCHIVE_DIR / "level3_archive_manifest.json"
CHECKSUMS = ARCHIVE_DIR / "checksums.sha256"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def archive_files() -> dict[str, Path]:
    excluded = {MANIFEST.name, CHECKSUMS.name}
    return {
        path.name: path
        for path in ARCHIVE_DIR.iterdir()
        if path.is_file()
        and path.name not in excluded
        and (path.suffix == ".json" or path.suffixes[-2:] == [".json", ".gz"])
    }


def verify_archive_manifest() -> list[str]:
    if not MANIFEST.exists():
        return [f"{MANIFEST}: Level 3 archive manifest missing"]
    if not CHECKSUMS.exists():
        return [f"{CHECKSUMS}: Level 3 checksums file missing"]

    failures: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = manifest.get("files")
    if not isinstance(records, dict) or not records:
        failures.append(f"{MANIFEST}: missing non-empty files mapping")
        return failures

    current = archive_files()
    extra = sorted(set(current) - set(records))
    missing = sorted(set(records) - set(current))
    if extra:
        failures.append(f"{MANIFEST}: unregistered archive files {extra}")
    if missing:
        failures.append(f"{MANIFEST}: registered files missing {missing}")

    for name, record in sorted(records.items()):
        path = current.get(name)
        if path is None:
            continue
        expected_hash = str(record.get("sha256"))
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            failures.append(f"{name}: manifest SHA mismatch {actual_hash} != {expected_hash}")
        expected_bytes = int(record.get("bytes", -1))
        actual_bytes = path.stat().st_size
        if actual_bytes != expected_bytes:
            failures.append(f"{name}: manifest byte count {actual_bytes} != {expected_bytes}")

    checksum_records: dict[str, str] = {}
    for lineno, raw in enumerate(CHECKSUMS.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            failures.append(f"{CHECKSUMS}:{lineno}: expected '<sha256>  <filename>'")
            continue
        checksum_records[parts[1]] = "sha256:" + parts[0].lstrip("\ufeff")
    if set(checksum_records) != set(records):
        failures.append(f"{CHECKSUMS}: file set does not match {MANIFEST.name}")
    for name, expected in sorted(checksum_records.items()):
        path = current.get(name)
        if path is None:
            continue
        actual = sha256(path)
        if actual != expected:
            failures.append(f"{name}: checksums.sha256 mismatch {actual} != {expected}")

    if not failures:
        print(f"LEVEL3_ARCHIVE_MANIFEST_PASS files={len(records)}")
    return failures


def compare_values(path: str, actual: Any, expected: Any, failures: list[str], atol: float, rtol: float) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            failures.append(f"{path}: expected dict, got {type(actual).__name__}")
            return
        extra = sorted(set(actual) - set(expected))
        missing = sorted(set(expected) - set(actual))
        if extra:
            failures.append(f"{path}: unexpected keys {extra}")
        if missing:
            failures.append(f"{path}: missing keys {missing}")
        for key in sorted(set(actual) & set(expected)):
            compare_values(f"{path}.{key}", actual[key], expected[key], failures, atol, rtol)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list):
            failures.append(f"{path}: expected list, got {type(actual).__name__}")
            return
        if len(actual) != len(expected):
            failures.append(f"{path}: length {len(actual)} != {len(expected)}")
            return
        for idx, (a_item, e_item) in enumerate(zip(actual, expected, strict=True)):
            compare_values(f"{path}[{idx}]", a_item, e_item, failures, atol, rtol)
        return
    if isinstance(expected, float):
        if not isinstance(actual, (int, float)):
            failures.append(f"{path}: expected float, got {type(actual).__name__}")
            return
        if not math.isclose(float(actual), float(expected), rel_tol=rtol, abs_tol=atol):
            failures.append(f"{path}: {actual!r} != {expected!r}")
        return
    if actual != expected:
        failures.append(f"{path}: {actual!r} != {expected!r}")


def verify_case(name: str, bootstrap_reps: int, atol: float, rtol: float) -> list[str]:
    actual, archives, out = analysis_for_case(name, bootstrap_reps)
    if not out.exists():
        return [f"{name}: expected analysis JSON missing: {out}"]
    expected = json.loads(out.read_text(encoding="utf-8"))
    failures: list[str] = []
    compare_values(name, actual, expected, failures, atol, rtol)
    if failures:
        return [f"{name}: archives={len(archives)} json={out.name}", *failures]
    print(f"LEVEL3_VERIFY_PASS instance={name} archives={len(archives)} json={out.name}")
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default="all", choices=["all", *CASES])
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    parser.add_argument("--atol", type=float, default=1.0e-12)
    parser.add_argument("--rtol", type=float, default=1.0e-12)
    args = parser.parse_args(argv)

    names = list(CASES) if args.instance == "all" else [args.instance]
    failures: list[str] = verify_archive_manifest()
    for name in names:
        failures.extend(
            verify_case(name, int(args.bootstrap_reps), float(args.atol), float(args.rtol))
        )
    if not failures:
        print(f"LEVEL3_VERIFY_ALL_PASS cases={len(names)}")
        return 0
    print(f"LEVEL3_VERIFY_FAIL problems={len(failures)}", file=sys.stderr)
    for failure in failures[:80]:
        print("  - " + failure, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
