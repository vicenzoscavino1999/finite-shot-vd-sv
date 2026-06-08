"""Verify Level 3 consolidated analyses from archived counts without rewriting.

This is the archive-only Level 3 verifier: it reads committed ``*.json.gz``
count archives, recomputes the consolidated analyses in memory, and compares
them against the committed JSON summaries with tight numeric tolerances.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.reanalyze_level3_archives import CASES, analysis_for_case


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
    failures: list[str] = []
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
