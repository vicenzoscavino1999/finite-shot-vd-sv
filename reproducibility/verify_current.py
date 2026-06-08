"""Current verifier for generated Level 1 outputs and reference integrity.

The original ``verify.py`` is part of the PAP freeze. This wrapper keeps that
logic intact, adds checksum verification for ``reproducibility/reference/``, and
provides clearer failure messages for clean-checkout usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reproducibility.verify import CONFIG, HERE, Report, verify_file


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def _verify_reference_manifest(ref_dir: Path, rep: Report) -> None:
    manifest_path = ref_dir / "reference_manifest.json"
    if not manifest_path.exists():
        rep.fail(f"{manifest_path}: reference manifest missing")
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        rep.fail(f"{manifest_path}: invalid JSON ({exc})")
        return

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        rep.fail(f"{manifest_path}: missing non-empty 'files' mapping")
        return
    for name, expected in sorted(files.items()):
        path = ref_dir / str(name)
        if not path.exists():
            rep.fail(f"{name}: reference listed in manifest but missing")
            continue
        actual = _sha256(path)
        if actual != str(expected):
            rep.fail(f"{name}: reference SHA mismatch {actual} != {expected}")


def _verify_checksums_file(ref_dir: Path, rep: Report) -> None:
    checksums_path = ref_dir / "checksums.sha256"
    if not checksums_path.exists():
        rep.fail(f"{checksums_path}: checksums file missing")
        return
    for lineno, raw in enumerate(checksums_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            rep.fail(f"{checksums_path}:{lineno}: expected '<sha256>  <filename>'")
            continue
        expected_hex, name = parts
        expected_hex = expected_hex.lstrip("\ufeff")
        path = ref_dir / name
        if not path.exists():
            rep.fail(f"{name}: reference listed in checksums.sha256 but missing")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected_hex:
            rep.fail(f"{name}: checksums.sha256 mismatch {actual} != {expected_hex}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify current VD/SV Level 1 outputs")
    parser.add_argument("--reference", default=str(HERE / "reference"))
    parser.add_argument("--generated", default=str(HERE.parent / "results"))
    parser.add_argument("--exact-numeric", action="store_true")
    parser.add_argument("--skip-reference-checksums", action="store_true")
    args = parser.parse_args(argv)

    gen_dir = Path(args.generated)
    ref_dir = Path(args.reference)
    schemas = yaml.safe_load((CONFIG / "schemas.yaml").read_text(encoding="utf-8"))
    tolerances = yaml.safe_load((CONFIG / "tolerances.yaml").read_text(encoding="utf-8"))

    rep = Report()
    if not args.skip_reference_checksums:
        _verify_reference_manifest(ref_dir, rep)
        _verify_checksums_file(ref_dir, rep)
    if not gen_dir.exists():
        rep.fail(
            f"{gen_dir}: generated directory missing; run "
            "'python reproducibility/run_all_current.py --output results' first "
            "or pass --generated explicitly"
        )
    else:
        for name, schema in schemas.items():
            if schema.get("format") != "csv":
                continue
            verify_file(name, schema, tolerances, gen_dir, ref_dir, rep, args.exact_numeric)

    if rep.ok():
        print(
            f"VERIFY PASS: {rep.checked} numeric comparisons within tolerance "
            f"across {len(schemas)} files; reference checksums OK"
        )
        return 0
    print(f"VERIFY FAIL: {len(rep.failures)} problem(s):", file=sys.stderr)
    for failure in rep.failures[:80]:
        print("  - " + failure, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
