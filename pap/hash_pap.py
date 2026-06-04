"""Generate the PAP freeze manifest and aggregate hash.

The script hashes the explicit design-freeze checklist artifacts, executable
scripts/code used to produce them, and the frozen git commit SHA. It must be run
from a clean worktree after the pre-freeze commit has been created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "freeze_manifest.json"
DEFAULT_HASH_TXT = REPO_ROOT / "PAP_HASH.txt"

EXPLICIT_TARGETS: list[tuple[str, str]] = [
    ("pap", "EXPERIMENTAL_PLAN.md"),
    ("pap", "REPRODUCIBILITY_PLAN.md"),
    ("pap", "METHODS.md"),
    ("pap", "pap/failure_protocol.md"),
    ("configs", "config/grids.yaml"),
    ("configs", "config/noise_channel_spec.json"),
    ("configs", "config/readout_mitigation_spec.yaml"),
    ("artifacts_pinned", "results/frozen/frozen_instances.csv"),
    ("artifacts_pinned", "results/frozen/frozen_qaoa_angles.csv"),
    ("artifacts_pinned", "results/frozen/instance_selection_diagnostics.md"),
    ("artifacts_pinned", "results/frozen/lambda2_gap_table.csv"),
    ("artifacts_pinned", "results/frozen/wls_condition_report.csv"),
    ("artifacts_pinned", "results/frozen/compute_budget_table.csv"),
    ("artifacts_pinned", "results/frozen/hardware_feasibility_note.md"),
    ("artifacts_pinned", "results/pilot/pilot_power_report.csv"),
    ("artifacts_pinned", "results/pilot/pilot_power_report.md"),
    ("artifacts_pinned", "analysis/adjudication_template.csv"),
    ("hashing", "pap/hash_pap.py"),
]

GLOB_TARGETS: list[tuple[str, str]] = [
    ("configs", "reproducibility/config/*.yaml"),
    ("scripts", "src/vd_sv/*.py"),
    ("scripts", "experiments/*.py"),
    ("scripts", "ground_truth/*.py"),
    ("scripts", "pilot/*.py"),
    ("scripts", "reproducibility/*.py"),
    ("scripts", "scripts/*.py"),
    ("tests", "tests/test_freeze_specs.py"),
    ("tests", "tests/test_power_pilot.py"),
]

CHECKLIST_0_1 = {
    "pap": ["EXPERIMENTAL_PLAN.md", "REPRODUCIBILITY_PLAN.md"],
    "configs": [
        "config/grids.yaml",
        "config/noise_channel_spec.json",
        "config/readout_mitigation_spec.yaml",
    ],
    "instances": ["results/frozen/frozen_instances.csv"],
    "angles": ["results/frozen/frozen_qaoa_angles.csv"],
    "lambda2": ["results/frozen/lambda2_gap_table.csv"],
    "wls": ["results/frozen/wls_condition_report.csv"],
    "budget": ["results/frozen/compute_budget_table.csv"],
    "hardware": ["results/frozen/hardware_feasibility_note.md"],
    "pilot": [
        "results/pilot/pilot_power_report.csv",
        "results/pilot/pilot_power_report.md",
    ],
    "adjudication_template": ["analysis/adjudication_template.csv"],
    "failure_protocol": ["pap/failure_protocol.md"],
}

UNIVERSAL_PENDING_MARKERS = [
    "T" + "BD",
    "NOT" + "_FROZEN",
    "development" + "_not_frozen",
    "to be" + " decided",
    "replace this" + " section",
]

STRUCTURED_PENDING_MARKERS = [
    "provisional",
    "placeholder",
    "p.ej.",
    "example",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--hash-file", type=Path, default=DEFAULT_HASH_TXT)
    parser.add_argument("--allow-dirty", action="store_true", help="development-only bypass")
    parser.add_argument("--check-only", action="store_true", help="validate targets without writing")
    args = parser.parse_args(argv)

    if not args.allow_dirty:
        _require_clean_worktree()

    commit = _git(["rev-parse", "HEAD"])
    targets = _collect_targets()
    _verify_targets_exist(targets)
    if not args.allow_dirty:
        _verify_targets_tracked(targets)
    _verify_no_pending_markers(targets)
    _verify_checklist_coverage(targets)

    entries = [_entry_for(category, relpath) for category, relpath in targets]
    payload = {
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "frozen_commit_sha": commit,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root_name": REPO_ROOT.name,
        "checklist_0_1": CHECKLIST_0_1,
        "targets": entries,
    }
    pap_hash = _aggregate_hash(payload)
    manifest = {**payload, "pap_hash": pap_hash}

    if args.check_only:
        print(f"CHECK PASS: {len(entries)} targets, commit {commit}")
        print(f"PAP_HASH would be {pap_hash}")
        return 0

    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.hash_file.write_text(
        "\n".join([
            f"PAP_HASH={pap_hash}",
            f"FROZEN_COMMIT_SHA={commit}",
            f"MANIFEST={args.manifest.name}",
            "HASH_ALGORITHM=sha256",
            "",
        ]),
        encoding="utf-8",
    )
    print(args.manifest)
    print(args.hash_file)
    print(f"PAP_HASH={pap_hash}")
    return 0


def _collect_targets() -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = list(EXPLICIT_TARGETS)
    for category, pattern in GLOB_TARGETS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file():
                targets.append((category, path.relative_to(REPO_ROOT).as_posix()))
    seen = set()
    unique = []
    for category, relpath in targets:
        key = relpath.replace("\\", "/")
        if key in seen:
            continue
        seen.add(key)
        unique.append((category, key))
    return sorted(unique, key=lambda item: (item[0], item[1]))


def _entry_for(category: str, relpath: str) -> dict:
    path = REPO_ROOT / relpath
    data = path.read_bytes()
    return {
        "category": category,
        "path": relpath,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _aggregate_hash(payload: dict) -> str:
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


def _verify_targets_exist(targets: list[tuple[str, str]]) -> None:
    missing = [relpath for _category, relpath in targets if not (REPO_ROOT / relpath).is_file()]
    if missing:
        raise SystemExit("missing hash targets:\n" + "\n".join(missing))


def _verify_targets_tracked(targets: list[tuple[str, str]]) -> None:
    untracked = []
    for _category, relpath in targets:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", relpath],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            untracked.append(relpath)
    if untracked:
        raise SystemExit("hash targets are not tracked by git:\n" + "\n".join(untracked))


def _verify_no_pending_markers(targets: list[tuple[str, str]]) -> None:
    violations = []
    for category, relpath in targets:
        if relpath == "pap/hash_pap.py":
            continue
        path = REPO_ROOT / relpath
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        markers = list(UNIVERSAL_PENDING_MARKERS)
        if category in {"configs", "artifacts_pinned"} and path.suffix.lower() in {
            ".csv",
            ".json",
            ".yaml",
            ".yml",
        }:
            markers.extend(STRUCTURED_PENDING_MARKERS)
        lowered = text.lower()
        for marker in markers:
            if marker.lower() in lowered:
                violations.append(f"{relpath}: contains marker {marker!r}")
    if violations:
        raise SystemExit("pending freeze markers found:\n" + "\n".join(violations))


def _verify_checklist_coverage(targets: list[tuple[str, str]]) -> None:
    relpaths = {relpath for _category, relpath in targets}
    missing = []
    for item, paths in CHECKLIST_0_1.items():
        for relpath in paths:
            if relpath not in relpaths:
                missing.append(f"{item}: {relpath}")
    if missing:
        raise SystemExit("checklist coverage missing:\n" + "\n".join(missing))


def _require_clean_worktree() -> None:
    status = _git(["status", "--porcelain"])
    if status.strip():
        raise SystemExit("git worktree must be clean before PAP hash generation")


def _git(args: list[str]) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


if __name__ == "__main__":
    raise SystemExit(main())
