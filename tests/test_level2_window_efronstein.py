import csv
import math
from pathlib import Path

from level2 import window_efronstein as analysis


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_window_efronstein_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_window_efronstein_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _normalize(rows):
    out = []
    for row in rows:
        clean = {**row, "runtime_seconds": 0.0}
        for key, value in list(clean.items()):
            if isinstance(value, float) and math.isnan(value):
                clean[key] = "nan"
        out.append(clean)
    return out


def test_level2_window_efronstein_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert {row["row_kind"] for row in rows} == {
        "e8_curve",
        "e8_crossing",
        "e8_slope",
        "e12_efron_stein",
    }
    assert len([row for row in rows if row["row_kind"] == "e8_curve"]) == 120
    assert len([row for row in rows if row["row_kind"] == "e8_crossing"]) == 160
    assert len([row for row in rows if row["row_kind"] == "e8_slope"]) == 40
    assert len([row for row in rows if row["row_kind"] == "e12_efron_stein"]) == 40
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "EN FORMA" in report
    assert "not a freeze and not a Level 1 formal certificate" in report
    assert "Largest finite selected R_ES: `none`" in report


def test_level2_window_folding_noiseless_invariance():
    for row in _rows():
        if row["row_kind"] == "e8_curve":
            assert float(row["noiseless_abs_error"]) <= analysis.NOISELESS_INVARIANCE_TOL


def test_level2_e8_r0_scaling_rows_are_constructed():
    slope_rows = [row for row in _rows() if row["row_kind"] == "e8_slope"]
    sv_rows = [
        row for row in slope_rows
        if row["method_pair"] == "sv_vs_unmit" and row["resource_definition"] == "paired_sample"
    ]
    vd_rows = [
        row for row in slope_rows
        if row["method_pair"] == "vd_optimal_vs_sv_contrast"
        and row["resource_definition"] == "two_qubit_gate_proxy"
    ]
    assert len(sv_rows) == 10
    assert len(vd_rows) == 10
    assert any(row["measured_exponent"] for row in sv_rows)
    for row in sv_rows:
        if row["measured_exponent"]:
            assert math.isfinite(float(row["measured_exponent"]))
            assert int(row["finite_R0_points"]) >= 3
            assert row["scaling_status"] in {
                "decreasing_with_folded_noise",
                "not_asymptotic_or_readout_floor_dominated",
            }
    assert all(row["scaling_status"] == "insufficient_positive_crossings" for row in vd_rows)


def test_level2_e12_es_rows_are_computed_and_selected_vd_has_no_operational_window():
    e12_rows = [row for row in _rows() if row["row_kind"] == "e12_efron_stein"]
    selected = [
        row for row in e12_rows
        if row["method_a"].startswith("vd_selected")
        and row["resource_definition"] == "two_qubit_gate_proxy"
    ]
    assert len(selected) == 10
    assert all(float(row["es_constant"]) > 0.0 for row in selected)
    assert all(row["R_ES_status"] == "no_finite_R_ES_bias_or_variance_dominated" for row in selected)
    assert all(row["R_ES"] == "" for row in selected)
    assert all(row["vd_dominates_at_R_ES"] == "false" for row in selected)


def test_level2_window_efronstein_small_analysis_is_deterministic():
    cfg = analysis.WindowESConfig(instance_ids=("g6_k2_c000",), noise_scales=(1, 3, 5))
    rows_a, _report_a = analysis.run_window_efronstein(cfg, started_at=0.0)
    rows_b, _report_b = analysis.run_window_efronstein(cfg, started_at=0.0)
    assert _normalize(rows_a) == _normalize(rows_b)
