"""verify.py passes on clean reference data and hard-fails on perturbation / NaN /
missing columns -- the guard against a false-positive verifier."""

import csv
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REF = REPO / "reproducibility" / "reference"
VERIFY = REPO / "reproducibility" / "verify.py"


def _run(generated: Path, reference: Path) -> int:
    return subprocess.run(
        [sys.executable, str(VERIFY), "--reference", str(reference), "--generated", str(generated)],
        capture_output=True, text=True,
    ).returncode


def _copy_ref(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for f in REF.glob("*"):
        shutil.copy(f, dst / f.name)


def _rewrite(path: Path, mutate) -> None:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    mutate(rows)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def test_verify_clean_passes():
    assert _run(REF, REF) == 0


def test_verify_perturbed_fails(tmp_path):
    _copy_ref(tmp_path)
    _rewrite(tmp_path / "e3_delta_vd_generator.csv",
             lambda rows: rows[0].__setitem__(
                 "delta_vd_closed_form", str(float(rows[0]["delta_vd_closed_form"]) + 1.0)))
    assert _run(tmp_path, REF) != 0


def test_verify_nan_fails(tmp_path):
    _copy_ref(tmp_path)
    _rewrite(tmp_path / "e7_certified_crossing.csv",
             lambda rows: rows[0].__setitem__("mse_vd", "nan"))
    assert _run(tmp_path, REF) != 0


def test_verify_missing_column_fails(tmp_path):
    _copy_ref(tmp_path)
    _rewrite(tmp_path / "e4_delta_sv_firstorder.csv",
             lambda rows: [r.pop("b_sv") for r in rows])
    assert _run(tmp_path, REF) != 0


def test_verify_disallowed_string_fails(tmp_path):
    _copy_ref(tmp_path)
    _rewrite(tmp_path / "e7_certified_crossing.csv",
             lambda rows: rows[0].__setitem__("method_pair", "vd_vs_sv"))
    assert _run(tmp_path, REF) != 0


def test_verify_duplicate_key_fails(tmp_path):
    _copy_ref(tmp_path)
    path = tmp_path / "e2_c_sv_zero.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[1] = dict(rows[0])
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    assert _run(tmp_path, REF) != 0
