"""Numerical + schema verification (REPRODUCIBILITY_PLAN: verify.py).

Loads generated outputs and reference outputs, validates structure against
``config/schemas.yaml``, matches rows by explicit keys, and compares numeric
columns using ``config/tolerances.yaml`` (tier selected by the ``level`` field).
Hard-fail semantics for canonical numerical outputs; exits nonzero on any failure.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config"


def _load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _key(row: dict, key_cols: list[str]) -> tuple:
    return tuple(row[c] for c in key_cols)


def _coerce(value: str, typ: str):
    if value is None:
        raise ValueError("missing value")
    if typ == "int":
        v = float(value)
        if not v.is_integer():
            raise ValueError(f"non-integer value '{value}'")
        return int(v)
    if typ == "float":
        return float(value)
    return value


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checked = 0

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def ok(self) -> bool:
        return not self.failures


def _validate_columns(name: str, rows: list[dict], cols: dict, rep: Report,
                      label: str) -> bool:
    if not rows:
        rep.fail(f"{name}: {label} output is empty")
        return False
    ok = True
    expected = set(cols)
    for idx, row in enumerate(rows, start=2):  # CSV header is line 1
        actual = set(row)
        missing = expected - actual
        extra = actual - expected
        if missing:
            rep.fail(f"{name}: {label} row {idx} missing columns {sorted(missing)}")
            ok = False
        if extra:
            rep.fail(f"{name}: {label} row {idx} unexpected columns {sorted(map(str, extra))}")
            ok = False
    return ok


def _index_by_key(name: str, rows: list[dict], key_cols: list[str], rep: Report,
                  label: str) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for idx, row in enumerate(rows, start=2):
        try:
            k = _key(row, key_cols)
        except KeyError as exc:
            rep.fail(f"{name}: {label} row {idx} missing key column {exc.args[0]!r}")
            continue
        if k in out:
            rep.fail(f"{name}: duplicate {label} key {k}")
            continue
        out[k] = row
    return out


def _validate_schema_value(name: str, key: tuple, col: str, spec: dict, value: str,
                           rep: Report, label: str):
    typ = spec["type"]
    if typ in ("int", "float"):
        try:
            coerced = _coerce(value, typ)
        except ValueError:
            rep.fail(f"{name}[{key}].{col}: {label} non-{typ} '{value}'")
            return None
        if coerced != coerced or coerced in (float("inf"), float("-inf")):
            rep.fail(f"{name}[{key}].{col}: {label} NaN/Inf")
            return None
        if "min" in spec and coerced < float(spec["min"]):
            rep.fail(f"{name}[{key}].{col}: {label} {coerced!r} < min {spec['min']}")
        if "max" in spec and coerced > float(spec["max"]):
            rep.fail(f"{name}[{key}].{col}: {label} {coerced!r} > max {spec['max']}")
        return coerced
    if typ == "string":
        allowed = spec.get("allowed")
        if allowed is not None and value not in {str(x) for x in allowed}:
            rep.fail(f"{name}[{key}].{col}: {label} '{value}' not in allowed {allowed}")
    return value


def verify_file(name: str, schema: dict, tol: dict, gen_dir: Path, ref_dir: Path,
                rep: Report, exact: bool) -> None:
    gen_path, ref_path = gen_dir / name, ref_dir / name
    if not ref_path.exists():
        rep.fail(f"{name}: reference missing")
        return
    if not gen_path.exists():
        rep.fail(f"{name}: generated missing")
        return
    gen, ref = _load_csv(gen_path), _load_csv(ref_path)
    cols = schema["columns"]
    key_cols = schema["row_matching_key"]

    # column presence and duplicate-key checks
    if not _validate_columns(name, gen, cols, rep, "generated"):
        return
    if not _validate_columns(name, ref, cols, rep, "reference"):
        return
    if len(gen) != len(ref):
        rep.fail(f"{name}: row count {len(gen)} != reference {len(ref)}")

    gen_by_key = _index_by_key(name, gen, key_cols, rep, "generated")
    ref_by_key = _index_by_key(name, ref, key_cols, rep, "reference")
    for k in ref_by_key:
        if k not in gen_by_key:
            rep.fail(f"{name}: reference key {k} missing from generated")

    col_tol = tol.get(name, {}).get("columns", {})
    for grow in gen:
        k = _key(grow, key_cols)
        rrow = ref_by_key.get(k)
        if rrow is None:
            rep.fail(f"{name}: generated key {k} not in reference")
            continue
        for col, spec in cols.items():
            typ = spec["type"]
            gval, rval = grow[col], rrow[col]
            if typ in ("int", "float"):
                g = _validate_schema_value(name, k, col, spec, gval, rep, "generated")
                r = _validate_schema_value(name, k, col, spec, rval, rep, "reference")
                if g is None or r is None:
                    continue
                ct = col_tol.get(col, {})
                atol = 0.0 if exact else float(ct.get("atol", 1e-10))
                rtol = 0.0 if exact else float(ct.get("rtol", 1e-8))
                if abs(g - r) > atol + rtol * abs(r):
                    rep.fail(f"{name}[{k}].{col}: {g!r} vs ref {r!r} "
                             f"(|d|={abs(g-r):.3e} > atol+rtol*|ref|)")
                rep.checked += 1
            else:
                _validate_schema_value(name, k, col, spec, gval, rep, "generated")
                _validate_schema_value(name, k, col, spec, rval, rep, "reference")
                if gval != rval:
                    rep.fail(f"{name}[{k}].{col}: '{gval}' != ref '{rval}'")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify VD/SV Level 1 outputs")
    ap.add_argument("--reference", default=str(HERE / "reference"))
    ap.add_argument("--generated", default=str(HERE.parent / "results"))
    ap.add_argument("--exact-numeric", action="store_true")
    args = ap.parse_args(argv)

    schemas = yaml.safe_load((CONFIG / "schemas.yaml").read_text(encoding="utf-8"))
    tolerances = yaml.safe_load((CONFIG / "tolerances.yaml").read_text(encoding="utf-8"))
    gen_dir, ref_dir = Path(args.generated), Path(args.reference)

    rep = Report()
    for name, schema in schemas.items():
        if schema.get("format") != "csv":
            continue
        verify_file(name, schema, tolerances, gen_dir, ref_dir, rep, args.exact_numeric)

    if rep.ok():
        print(f"VERIFY PASS: {rep.checked} numeric comparisons within tolerance "
              f"across {len(schemas)} files")
        return 0
    print(f"VERIFY FAIL: {len(rep.failures)} problem(s):", file=sys.stderr)
    for f in rep.failures[:50]:
        print("  - " + f, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
