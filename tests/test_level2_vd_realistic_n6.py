import csv
import math
from pathlib import Path

import numpy as np

from level2 import vd_realistic_n6 as realistic
from vd_sv.estimators import make_rng


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_vd_realistic_n6_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_vd_realistic_n6_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _bool_cell(value: str) -> bool:
    return value.lower() == "true"


def test_level2_realistic_vd_n6_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == len(realistic.INSTANCE_IDS) * len(realistic.B_GRID_FACTORS)
    assert {row["instance_id"] for row in rows} == set(realistic.INSTANCE_IDS)
    assert {int(row["n_qubits"]) for row in rows} == {6}
    assert {row["sample_status"] for row in rows} == {"sampled"}
    assert {row["estimator_model"] for row in rows} == {realistic.ESTIMATOR_MODEL}
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "EN FORMA; device-circuit VD con interferencia, n=6" in report
    assert "c-SWAP/interference overhead" in report


def test_level2_realistic_vd_n6_noiseless_crosschecks_pass():
    for row in _rows():
        assert abs(float(row["noiseless_D_hat"]) - 1.0) <= realistic.NOISELESS_D_TOL
        assert float(row["noiseless_mu_abs_error"]) <= realistic.NOISELESS_MU_TOL


def test_level2_realistic_vd_n6_grid_crosses_10x_bden():
    rows = _rows()
    for instance_id in realistic.INSTANCE_IDS:
        inst_rows = [row for row in rows if row["instance_id"] == instance_id]
        assert len(inst_rows) == len(realistic.B_GRID_FACTORS)
        b_values = sorted(int(row["B"]) for row in inst_rows)
        b_max = max(b_values)
        ratios = [float(row["B_over_B_den"]) for row in inst_rows]
        assert min(ratios) < 1.0
        assert max(ratios) >= 10.0
        for row in inst_rows:
            b_den = float(row["B_den_realistic"])
            assert b_den > 0.0
            assert int(row["B_max_instance"]) == b_max
            assert _bool_cell(row["grid_reaches_10x_B_den"])
            assert b_max >= 10.0 * b_den


def test_level2_realistic_vd_n6_overhead_and_comparison_columns_are_present():
    for row in _rows():
        for field in (
            "vd_interference_overhead_abs_bias_delta",
            "vd_interference_overhead_abs_bias_ratio",
            "sv_matched_paired_mse",
            "sv_matched_twoqubit_mse",
            "vd_bias_floor_mse",
            "sv_bias_floor_mse",
        ):
            assert math.isfinite(float(row[field]))
        assert row["vd_bias_floor_beats_sv"] in {"true", "false"}
        assert row["vd_mse_beats_sv_paired"] in {"true", "false"}
        assert row["vd_mse_beats_sv_twoqubit"] in {"true", "false"}
        assert float(row["resource_R_paired_sample"]) > 0.0
        assert float(row["resource_R_two_qubit_gate_proxy"]) > 0.0
        assert int(row["sv_matched_paired_B"]) > 0
        assert int(row["sv_matched_twoqubit_B"]) > 0


def test_level2_realistic_vd_n6_sampling_helper_is_deterministic():
    probabilities = np.asarray([0.20, 0.30, 0.10, 0.40], dtype=np.float64)
    numerator = np.asarray([1.0, -0.5, 0.25, -1.0], dtype=np.float64)
    denominator = np.asarray([1.0, 1.0, 1.0, -1.0], dtype=np.float64)
    d_value = float(probabilities @ denominator)
    rng_a = make_rng(1234)
    rng_b = make_rng(1234)
    sample_a = realistic.sample_vd_from_distribution(
        probabilities, numerator, denominator, abs(d_value), 32, 8, rng_a
    )
    sample_b = realistic.sample_vd_from_distribution(
        probabilities, numerator, denominator, abs(d_value), 32, 8, rng_b
    )
    for a, b in zip(sample_a, sample_b):
        np.testing.assert_allclose(a, b, rtol=0, atol=0)
