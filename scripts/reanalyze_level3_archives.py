"""Re-run Level 3 analyses from archived hardware counts only.

This script does not connect to IBM Runtime and does not submit QPU jobs. It
only reads the committed `level3/archive/stage3_*.json.gz` archives and rewrites
the consolidated JSON summaries used by the reports.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = REPO_ROOT / "level3" / "archive"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from level3.analyze_full import analyze_archives, render_summary

CASES = {
    "g6_k2_c000": {
        "pattern": "stage3_g6_k2_c000_ibm_marrakesh_epoch*.json.gz",
        "json_out": "stage3_g6_k2_c000_ibm_marrakesh_full_analysis.json",
    },
    "g6_k2_c001": {
        "pattern": "stage3_g6_k2_c001_ibm_marrakesh_epoch*.json.gz",
        "json_out": "stage3_g6_k2_c001_ibm_marrakesh_full_analysis.json",
    },
    "g8_k3_c000": {
        "pattern": "stage3_g8_k3_c000_ibm_marrakesh_epoch*.json.gz",
        "json_out": "stage3_g8_k3_c000_ibm_marrakesh_full_analysis.json",
    },
    "g6_k2_c000_kingston_fixed14": {
        "pattern": "stage3_g6_k2_c000_ibm_kingston_epoch*.json.gz",
        "json_out": "stage3_g6_k2_c000_ibm_kingston_fixed14_analysis.json",
        "selector": "first_14_unique_jobs_by_ibm_created_timestamp",
    },
}


def _case_names(selected: str) -> list[str]:
    if selected == "all":
        return list(CASES)
    if selected not in CASES:
        raise SystemExit(f"unknown instance {selected!r}; choose one of {', '.join(CASES)}")
    return [selected]


def _archive_created_at(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    return str(payload.get("created_at_utc", path.name))


def _archive_job_key(path: Path) -> tuple[str, str, Path]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    job_id = str(payload["submission"]["job_id"])
    created = (
        payload.get("submission", {})
        .get("metrics", {})
        .get("timestamps", {})
        .get("created")
    )
    return str(created or payload.get("created_at_utc", path.name)), job_id, path


def _select_archives(case: dict[str, str]) -> tuple[list[Path], list[Path]]:
    archives = sorted(ARCHIVE_DIR.glob(case["pattern"]), key=_archive_created_at)
    if case.get("selector") != "first_14_unique_jobs_by_ibm_created_timestamp":
        return archives, []

    selected: list[Path] = []
    extras: list[Path] = []
    seen_jobs: set[str] = set()
    for _created, job_id, path in sorted((_archive_job_key(path) for path in archives)):
        if job_id in seen_jobs:
            continue
        seen_jobs.add(job_id)
        if len(selected) < 14:
            selected.append(path)
        else:
            extras.append(path)
    if len(selected) != 14:
        raise SystemExit(f"expected 14 fixed Kingston archives, found {len(selected)}")
    return selected, extras


def _repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default="all", choices=["all", *CASES])
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    for name in _case_names(args.instance):
        case = CASES[name]
        archives, extras = _select_archives(case)
        if not archives:
            raise SystemExit(f"no archives found for {name}: {case['pattern']}")
        result = analyze_archives(archives, bootstrap_reps=int(args.bootstrap_reps))
        if extras:
            result["analysis_inputs"]["selection_rule"] = (
                "first_14_unique_jobs_by_ibm_created_timestamp_pre_registered_fixed_epoch_stop"
            )
            result["analysis_inputs"]["extra_unique_archives_excluded_count"] = len(extras)
            result["analysis_inputs"]["extra_unique_archives_excluded"] = [
                _repo_relative(path) for path in extras
            ]
        out = ARCHIVE_DIR / case["json_out"]
        out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(f"LEVEL3_ANALYSIS_WRITTEN instance={name} archives={len(archives)} json_out={out}")
        if not args.quiet:
            print(render_summary(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
