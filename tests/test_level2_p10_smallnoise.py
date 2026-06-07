import csv
import math
from pathlib import Path

from level2 import p10_smallnoise


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_p10_smallnoise_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_p10_smallnoise_report.md"


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


def test_level2_p10_smallnoise_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert {row["row_kind"] for row in rows} == {
        "curve",
        "crossing",
        "bias_linearity",
        "exponent_fit",
    }
    assert len([row for row in rows if row["row_kind"] == "curve"]) == 150
    assert len([row for row in rows if row["row_kind"] == "crossing"]) == 300
    assert len([row for row in rows if row["row_kind"] == "bias_linearity"]) == 30
    assert len([row for row in rows if row["row_kind"] == "exponent_fit"]) == 60
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "small gate-noise asymptotic variant" in report
    assert "p_cx in {1e-5,2e-5,4e-5,8e-5,1.6e-4}" in report


def test_level2_p10_smallnoise_bias_is_linear_in_p_for_unmit_and_sv():
    rows = [
        row for row in _rows()
        if row["row_kind"] == "bias_linearity" and row["method"] in {"unmitigated", "sv_mitigated"}
    ]
    assert len(rows) == 20
    assert all(row["bias_linearity_status"] == "linear_asymptotic" for row in rows)
    for row in rows:
        assert 0.85 <= float(row["bias_linearity_slope"]) <= 1.15
        assert float(row["bias_linearity_r2"]) >= 0.98


def test_level2_p10_smallnoise_vd_unmit_recovers_minus_two():
    rows = [
        row for row in _rows()
        if row["row_kind"] == "exponent_fit"
        and row["method_pair"] == "vd_optimal_vs_unmit"
        and row["resource_definition"] == "paired_sample"
    ]
    assert len(rows) == 10
    for row in rows:
        assert int(row["finite_R0_points"]) == len(p10_smallnoise.P_CX_VALUES)
        assert row["scaling_status"] == "recovers_expected_exponent"
        assert abs(float(row["measured_exponent"]) + 2.0) <= 0.25
        assert float(row["fit_r2"]) >= 0.98


def test_level2_p10_smallnoise_sv_unmit_matched_crossings_recover_minus_one_when_present():
    rows = [
        row for row in _rows()
        if row["row_kind"] == "exponent_fit"
        and row["method_pair"] == "sv_vs_unmit"
        and row["resource_definition"] == "paired_sample"
        and row["measured_exponent"]
    ]
    assert rows
    for row in rows:
        assert row["scaling_status"] == "recovers_expected_exponent"
        assert abs(float(row["measured_exponent"]) + 1.0) <= 0.25


def test_level2_p10_smallnoise_small_run_is_deterministic():
    cfg = p10_smallnoise.SmallNoiseConfig(
        instance_ids=("g6_k2_c000",),
        p_cx_values=(1.0e-5, 2.0e-5, 4.0e-5),
    )
    rows_a, _report_a = p10_smallnoise.run_p10_smallnoise(cfg, started_at=0.0)
    rows_b, _report_b = p10_smallnoise.run_p10_smallnoise(cfg, started_at=0.0)
    assert _normalize(rows_a) == _normalize(rows_b)
