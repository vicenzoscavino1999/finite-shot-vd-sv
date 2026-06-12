import csv
import math
from pathlib import Path

from experiments import channel_sensitivity_delta as channel
from experiments import clipping_threshold_sensitivity as clipping


REPO_ROOT = Path(__file__).resolve().parents[1]
CLIPPING_CSV = REPO_ROOT / "results" / "secondary" / "clipping_threshold_sensitivity.csv"
CLIPPING_REPORT = REPO_ROOT / "results" / "secondary" / "clipping_threshold_sensitivity_report.md"
CHANNEL_CSV = REPO_ROOT / "results" / "secondary" / "channel_sensitivity_delta.csv"
CHANNEL_REPORT = REPO_ROOT / "results" / "secondary" / "channel_sensitivity_delta_report.md"


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_registered_clipping_threshold_sensitivity_outputs_are_present():
    assert CLIPPING_CSV.exists()
    assert CLIPPING_REPORT.exists()
    rows = _rows(CLIPPING_CSV)
    assert len(rows) == 10 * len(clipping.CLIP_FRACTIONS) * clipping.N_B
    assert {int(row["B"]) for row in rows} == set(
        int(value) for value in clipping.log_grid(clipping.B_MIN, clipping.B_MAX, clipping.N_B)
    )
    observed_fractions = sorted({float(row["clip_fraction"]) for row in rows})
    expected_fractions = sorted(clipping.CLIP_FRACTIONS)
    assert len(observed_fractions) == len(expected_fractions)
    for observed, expected in zip(observed_fractions, expected_fractions, strict=True):
        assert math.isclose(observed, expected, rel_tol=1e-14, abs_tol=1e-14)


def test_registered_clipping_threshold_leading_law_is_stable():
    rows = _rows(CLIPPING_CSV)
    refs = {}
    for row in rows:
        if float(row["clip_fraction"]) == clipping.REFERENCE_CLIP_FRACTION:
            refs[row["instance_id"]] = float(row["beta1"])
    assert len(refs) == 10

    max_rel = 0.0
    for row in rows:
        ref = refs[row["instance_id"]]
        rel = abs(float(row["beta1_minus_ref"])) / max(abs(ref), 1e-300)
        max_rel = max(max_rel, rel)
    assert max_rel < clipping.RELATIVE_BETA1_TOL


def test_registered_depolarizing_channel_sensitivity_outputs_are_present_and_accurate():
    assert CHANNEL_CSV.exists()
    assert CHANNEL_REPORT.exists()
    rows = _rows(CHANNEL_CSV)
    assert len(rows) == 10
    for row in rows:
        assert float(row["delta_vd_abs_err"]) <= channel.ABS_ERR_TOL
        assert float(row["delta_sv_abs_err"]) <= channel.ABS_ERR_TOL
