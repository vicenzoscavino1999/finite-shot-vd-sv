import csv
import math
from pathlib import Path

from experiments import e8_window_location as e8


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "results" / "secondary" / "e8_window_location.csv"
REPORT_PATH = REPO_ROOT / "results" / "secondary" / "e8_window_location_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_e8_outputs_are_present_and_have_fixed_grid():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == 10 * len(e8.PAIRS) * e8.N_P

    assert {row["pair"] for row in rows} == {pair["name"] for pair in e8.PAIRS}
    assert {float(row["p_min"]) for row in rows} == {e8.P_MIN}
    assert {float(row["p_max"]) for row in rows} == {e8.P_MAX}
    assert {int(row["n_p"]) for row in rows} == {e8.N_P}

    p_values = sorted({float(row["noise_strength"]) for row in rows})
    assert len(p_values) == e8.N_P
    assert math.isclose(p_values[0], e8.P_MIN, rel_tol=1e-12)
    assert math.isclose(p_values[-1], e8.P_MAX, rel_tol=1e-12)


def test_e8_valid_crossing_exponents_are_close_to_prediction():
    rows = _rows()
    fits = {}
    for row in rows:
        fits[(row["instance_id"], row["pair"])] = row

    valid_fits = [row for row in fits.values() if row["status"].startswith("valid_crossing")]
    assert valid_fits
    for row in valid_fits:
        measured = float(row["exponent_measured"])
        predicted = float(row["exponent_predicted"])
        assert abs(measured - predicted) <= e8.EXPONENT_TOL
        assert float(row["valid_crossing_fraction"]) == 1.0
        assert float(row["r2_loglog"]) > 0.99


def test_e8_sv_unmitigated_pair_reports_no_valid_crossing():
    rows = _rows()
    fits = {
        (row["instance_id"], row["pair"]): row
        for row in rows
    }
    sv_fits = [
        row for (instance_id, pair), row in fits.items()
        if pair == "sv_vs_unmitigated"
    ]
    assert len(sv_fits) == 10
    for row in sv_fits:
        assert row["status"] == "no_valid_crossing"
        assert int(row["valid_crossing_points"]) == 0
        assert float(row["valid_crossing_fraction"]) == 0.0
        assert row["exponent_measured"] == "nan"
