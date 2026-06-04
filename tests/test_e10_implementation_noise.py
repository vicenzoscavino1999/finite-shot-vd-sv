import csv
from pathlib import Path

from experiments import e10_implementation_noise as e10


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "results" / "secondary" / "e10_implementation_noise.csv"
REPORT_PATH = REPO_ROOT / "results" / "secondary" / "e10_implementation_noise_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _se_from_ci(row):
    return (float(row["b_hat_ci_hi"]) - float(row["b_hat_ci_lo"])) / (2.0 * e10.CI_Z)


def test_e10_outputs_are_present_and_cases_are_declared():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == 10 * len(e10.CASES)
    assert {row["case"] for row in rows} == {case[0] for case in e10.CASES}
    assert {float(row["noise_strength"]) for row in rows} == {e10.P_FIXED}
    assert {int(row["copies_M"]) for row in rows} == {e10.M_COPIES}


def test_e10_common_contraction_preserves_bias_and_inflates_variance():
    rows = _rows()
    common = [row for row in rows if row["case"].startswith("common_eta")]
    assert common
    for row in common:
        assert row["b_invariant_check"] == "true"
        assert row["v_formula_check"] == "true"
        assert float(row["v_inflation_ratio"]) > 1.0
        rel = abs(float(row["v_hat"]) - float(row["v_impl_predicted"])) / float(row["v_impl_predicted"])
        assert rel <= e10.V_REL_TOL


def test_e10_asymmetric_contraction_recovers_bias_shift():
    rows = _rows()
    asym = [row for row in rows if row["case"].startswith("asymmetric")]
    assert len(asym) == 10
    for row in asym:
        assert row["bias_shift_check"] == "true"
        se = _se_from_ci(row)
        assert abs(float(row["b_hat"]) - float(row["b_impl_predicted"])) <= e10.BIAS_Z_TOL * se
        assert not (float(row["b_hat_ci_lo"]) <= float(row["b_VD"]) <= float(row["b_hat_ci_hi"]))


def test_e10_variance_formula_holds_for_all_declared_cases():
    rows = _rows()
    assert all(row["v_formula_check"] == "true" for row in rows)
    for row in rows:
        rel = abs(float(row["v_hat"]) - float(row["v_impl_predicted"])) / float(row["v_impl_predicted"])
        assert rel <= e10.V_REL_TOL
