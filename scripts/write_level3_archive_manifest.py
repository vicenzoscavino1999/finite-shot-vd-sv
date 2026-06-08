"""Write checksums for committed Level 3 archive and analysis artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = REPO_ROOT / "level3" / "archive"
MANIFEST_NAME = "level3_archive_manifest.json"
CHECKSUMS_NAME = "checksums.sha256"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def file_role(path: Path) -> str:
    if path.suffixes[-2:] == [".json", ".gz"]:
        return "raw_counts_archive"
    if path.suffix == ".json":
        return "consolidated_analysis_json"
    return "other"


def created_utc(explicit: str | None) -> str:
    if explicit:
        return explicit
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def archive_files(archive_dir: Path) -> list[Path]:
    excluded = {MANIFEST_NAME, CHECKSUMS_NAME}
    return sorted(
        path
        for path in archive_dir.iterdir()
        if path.is_file()
        and path.name not in excluded
        and (path.suffix == ".json" or path.suffixes[-2:] == [".json", ".gz"])
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVE_DIR)
    parser.add_argument("--created-utc")
    args = parser.parse_args(argv)

    archive_dir = args.archive_dir.resolve()
    files = archive_files(archive_dir)
    if not files:
        raise SystemExit(f"no Level 3 archive files found in {archive_dir}")

    records = {
        path.name: {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "role": file_role(path),
        }
        for path in files
    }
    checksum_lines = [
        f"{record['sha256'].removeprefix('sha256:')}  {name}"
        for name, record in sorted(records.items())
    ]
    (archive_dir / CHECKSUMS_NAME).write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "level3-archive-manifest-v1",
        "created_utc": created_utc(args.created_utc),
        "scope": (
            "Committed Level 3 raw-count JSON.GZ archives and consolidated "
            "analysis JSON files. Public DOI archives should preserve these "
            "checksums or supersede them with a DOI-time manifest."
        ),
        "files": records,
    }
    (archive_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"LEVEL3_ARCHIVE_MANIFEST_WRITTEN files={len(records)} archive_dir={archive_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
