"""Read and write versioned Level 3 archived-count artifacts."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "level3.counts.v1"


def write_archive(path: str | Path, payload: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {"schema_version": SCHEMA_VERSION, **payload}
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        indent=2,
        separators=(",", ": "),
    ).encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(encoded)
    return path


def read_archive(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported archive schema: {payload.get('schema_version')!r}")
    return payload


def counts_by_label(payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for item in payload.get("circuits", []):
        out[str(item["label"])] = {str(k): int(v) for k, v in item["counts"].items()}
    return out

