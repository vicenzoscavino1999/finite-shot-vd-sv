import csv
import math
from pathlib import Path

from experiments import e6_copy_log_scale as e6


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "results" / "secondary" / "e6_copy_log_scale.csv"
REPORT_PATH = REPO_ROOT / "results" / "secondary" / "e6_copy_log_scale_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_e6_outputs_are_deterministic_and_frozen_selection_is_used():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert rows

    selection = e6.select_e6_candidate()
    assert selection.instance_id == "g8_k3_c000"
    assert math.isclose(selection.p, 0.01)

    summary_rows = [row for row in rows if row["row_kind"] == "B_grid"]
    assert len(summary_rows) == e6.B_GRID_N
    assert {row["instance_id"] for row in rows} == {selection.instance_id}
    assert {float(row["noise_strength"]) for row in rows} == {selection.p}
    assert len({row["slope_measured"] for row in rows}) == 1
    assert len({row["slope_predicted"] for row in rows}) == 1

    predicted = 1.0 / (2.0 * abs(math.log(selection.lambda2)))
    assert math.isclose(float(rows[0]["slope_predicted"]), predicted, rel_tol=1e-12)


def test_e6_slope_is_close_when_resolvable_or_explicitly_marked_not_resolvable():
    rows = _rows()
    first = rows[0]
    measured = float(first["slope_measured"])
    predicted = float(first["slope_predicted"])
    rel_error = abs((measured - predicted) / predicted)
    status = first["mstar_status"]

    if status == "resolved":
        assert rel_error <= e6.SLOPE_REL_TOL
        assert int(first["mstar_unique_count"]) >= e6.MIN_UNIQUE_MSTAR_FOR_RESOLVED
    else:
        assert status == "not_resolvable"
        assert int(first["mstar_unique_count"]) < e6.MIN_UNIQUE_MSTAR_FOR_RESOLVED


def test_e6_theorem_hypothesis_checks_are_recorded():
    first = _rows()[0]
    assert first["q_decay_check"] in {"PASS", "FAIL", "NOT_RESOLVABLE_NUMERICAL_FLOOR"}
    assert first["v_growth_check"] in {"PASS", "FAIL", "NOT_RESOLVABLE"}
    assert int(first["q_decay_fit_n"]) >= 4
    assert int(first["v_growth_fit_n"]) >= 4
