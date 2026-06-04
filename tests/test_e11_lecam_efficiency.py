import csv
import math
from pathlib import Path

from experiments import e11_lecam_efficiency as e11


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "results" / "secondary" / "e11_lecam_efficiency.csv"
REPORT_PATH = REPO_ROOT / "results" / "secondary" / "e11_lecam_efficiency_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_e11_outputs_are_present_and_on_declared_grid():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == e11.N_P * e11.N_R
    p_values = sorted({float(row["noise_strength"]) for row in rows})
    r_values = sorted({float(row["R"]) for row in rows})
    assert len(p_values) == e11.N_P
    assert len(r_values) == e11.N_R
    assert math.isclose(p_values[0], e11.P_MIN, rel_tol=1e-12)
    assert math.isclose(p_values[-1], e11.P_MAX, rel_tol=1e-12)
    assert math.isclose(r_values[0], e11.R_MIN, rel_tol=1e-12)
    assert math.isclose(r_values[-1], e11.R_MAX, rel_tol=1e-12)


def test_e11_lecam_ratios_are_within_declared_limits():
    for row in _rows():
        assert row["ratio_cons_within_64"] == "true"
        assert row["ratio_loc_within_32"] == "true"
        assert float(row["ratio_conservative"]) <= e11.RATIO_CONSERVATIVE_LIMIT
        assert float(row["ratio_local"]) <= e11.RATIO_LOCAL_LIMIT


def test_e11_fisher_saturation_identity_holds():
    for row in _rows():
        product = float(row["fisher_saturation_product"])
        assert abs(product - 1.0) <= e11.FISHER_TOL
        assert math.isclose(
            float(row["fisher_s"]) * float(row["fisher_J"]),
            product,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
