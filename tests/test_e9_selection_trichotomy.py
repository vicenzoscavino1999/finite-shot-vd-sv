import csv
from pathlib import Path

from experiments import e9_selection_trichotomy as e9


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "results" / "secondary" / "e9_selection_trichotomy.csv"
REPORT_PATH = REPO_ROOT / "results" / "secondary" / "e9_selection_trichotomy_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_e9_outputs_are_present_and_on_declared_grid():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == 10 * len(e9.PAIRS) * e9.N_P
    assert {row["pair"] for row in rows} == {pair[0] for pair in e9.PAIRS}
    assert {int(row["n_p"]) for row in rows} == {e9.N_P}
    assert {int(row["n_r"]) for row in rows} == {e9.N_R}
    assert {float(row["p_min"]) for row in rows} == {e9.P_MIN}
    assert {float(row["p_max"]) for row in rows} == {e9.P_MAX}


def test_e9_each_cell_has_exactly_one_valid_regime():
    rows = _rows()
    valid_regimes = set(e9.REGIMES)
    for row in rows:
        assert row["regime_predicted"] in valid_regimes
        assert row["regime_observed"] in valid_regimes
        assert row["regime_predicted"] != "ambiguous"
        if row["regime_predicted"] == "crossing":
            assert float(row["R0"]) > 0.0
            assert row["eta_below_half"] == "true"
        else:
            assert row["R0"] == "nan"


def test_e9_predicted_matches_observed_in_all_cells():
    rows = _rows()
    assert rows
    assert all(row["predicted_eq_observed"] == "true" for row in rows)


def test_e9_expected_regime_families_are_present():
    rows = _rows()
    by_pair = {}
    for row in rows:
        by_pair.setdefault(row["pair"], set()).add(row["regime_predicted"])
    assert by_pair["vd_vs_unmitigated"] == {"crossing"}
    assert by_pair["sv_vs_unmitigated"].issubset(set(e9.REGIMES))
    assert by_pair["vd_vs_sv"].issubset(set(e9.REGIMES))
