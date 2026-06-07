from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PATH = REPO_ROOT / "level3" / "archive" / "stage3_g6_k2_c000_ibm_marrakesh_full_analysis.json"
REPORT_PATH = REPO_ROOT / "level3" / "level3_full_p7p9_report.md"
ROBUSTNESS_ANALYSIS_PATH = (
    REPO_ROOT / "level3" / "archive" / "stage3_g6_k2_c001_ibm_marrakesh_full_analysis.json"
)
ROBUSTNESS_REPORT_PATH = REPO_ROOT / "level3" / "level3_robustness_g6c001_report.md"
G8_ANALYSIS_PATH = REPO_ROOT / "level3" / "archive" / "stage3_g8_k3_c000_ibm_marrakesh_full_analysis.json"
G8_REPORT_PATH = REPO_ROOT / "level3" / "level3_g8c000_hardware_report.md"
ROBUSTNESS_SUMMARY_PATH = REPO_ROOT / "level3" / "level3_hardware_robustness_summary.md"


def _analysis():
    with ANALYSIS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _robustness_analysis():
    with ROBUSTNESS_ANALYSIS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _g8_analysis():
    with G8_ANALYSIS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _row(method: str, b: int) -> dict:
    for row in _analysis()["rows"]:
        if row["method"] == method and int(row["B"]) == int(b):
            return row
    raise KeyError((method, b))


def _robustness_row(method: str, b: int) -> dict:
    for row in _robustness_analysis()["rows"]:
        if row["method"] == method and int(row["B"]) == int(b):
            return row
    raise KeyError((method, b))


def _g8_row(method: str, b: int) -> dict:
    for row in _g8_analysis()["rows"]:
        if row["method"] == method and int(row["B"]) == int(b):
            return row
    raise KeyError((method, b))


def test_level3_stage3_full_analysis_is_present_and_scoped():
    result = _analysis()
    assert REPORT_PATH.exists()
    assert result["analysis_inputs"]["source"] == "archived_counts_only"
    assert result["analysis_inputs"]["archive_count"] == 38
    assert len(result["epochs"]) == 38
    assert sum(epoch["quantum_seconds"] for epoch in result["epochs"]) == 532.0
    assert result["qualitative"]["interpretation"] == "qualitative_sv_dominance_vd_overhead_degraded"


def test_level3_stage3_sv_dominates_largest_b_mse():
    b = 8192
    sv = _row("sv_readout_mitigated_weight_postselect", b)
    unmit = _row("unmitigated", b)
    vd = _row("vd_m2_readout_mitigated", b)
    assert sv["mse"] < unmit["mse"] < vd["mse"]
    assert result_method_order_labels() == [
        "sv_readout_mitigated_weight_postselect",
        "unmitigated",
        "vd_m2_readout_mitigated",
    ]


def test_level3_stage3_vd_denominator_is_below_concentration_scale():
    vd_rows = [
        row for row in _analysis()["rows"]
        if row["method"] == "vd_m2_readout_mitigated"
    ]
    assert vd_rows
    assert all(row["B_over_B_den_estimate"] < 1.0 for row in vd_rows)
    assert _row("vd_m2_readout_mitigated", 8192)["mean_vd_denominator"] < 0.1


def test_level3_robustness_g6c001_analysis_is_present_and_scoped():
    result = _robustness_analysis()
    assert ROBUSTNESS_REPORT_PATH.exists()
    assert ROBUSTNESS_SUMMARY_PATH.exists()
    assert result["analysis_inputs"]["source"] == "archived_counts_only"
    assert result["analysis_inputs"]["archive_count"] == 16
    assert len(result["epochs"]) == 16
    assert sum(epoch["quantum_seconds"] for epoch in result["epochs"]) == 224.0
    assert result["qualitative"]["interpretation"] == "qualitative_sv_dominance_vd_overhead_degraded"


def test_level3_robustness_g6c001_sv_dominates_largest_b_mse():
    b = 8192
    sv = _robustness_row("sv_readout_mitigated_weight_postselect", b)
    unmit = _robustness_row("unmitigated", b)
    vd = _robustness_row("vd_m2_readout_mitigated", b)
    assert sv["mse"] < unmit["mse"] < vd["mse"]
    assert robustness_method_order_labels() == [
        "sv_readout_mitigated_weight_postselect",
        "unmitigated",
        "vd_m2_readout_mitigated",
    ]


def test_level3_robustness_g6c001_vd_denominator_is_below_concentration_scale():
    vd_rows = [
        row for row in _robustness_analysis()["rows"]
        if row["method"] == "vd_m2_readout_mitigated"
    ]
    assert vd_rows
    assert all(row["B_over_B_den_estimate"] < 1.0 for row in vd_rows)
    assert _robustness_row("vd_m2_readout_mitigated", 8192)["mean_vd_denominator"] < 0.1


def test_level3_g8c000_analysis_is_present_and_scoped():
    result = _g8_analysis()
    assert G8_REPORT_PATH.exists()
    assert ROBUSTNESS_SUMMARY_PATH.exists()
    assert result["analysis_inputs"]["source"] == "archived_counts_only"
    assert result["analysis_inputs"]["archive_count"] == 12
    assert len(result["epochs"]) == 12
    assert sum(epoch["quantum_seconds"] for epoch in result["epochs"]) == 180.0
    assert result["qualitative"]["interpretation"] == "qualitative_sv_dominance_vd_overhead_degraded"


def test_level3_g8c000_sv_dominates_largest_b_mse():
    b = 8192
    sv = _g8_row("sv_readout_mitigated_weight_postselect", b)
    unmit = _g8_row("unmitigated", b)
    vd = _g8_row("vd_m2_readout_mitigated", b)
    assert sv["mse"] < unmit["mse"] < vd["mse"]
    assert g8_method_order_labels() == [
        "sv_readout_mitigated_weight_postselect",
        "unmitigated",
        "vd_m2_readout_mitigated",
    ]


def test_level3_g8c000_vd_denominator_is_unconcentrated():
    vd_rows = [
        row for row in _g8_analysis()["rows"]
        if row["method"] == "vd_m2_readout_mitigated"
    ]
    assert vd_rows
    assert all(row["B_over_B_den_estimate"] < 0.001 for row in vd_rows)
    assert abs(_g8_row("vd_m2_readout_mitigated", 8192)["mean_vd_denominator"]) < 0.01


def result_method_order_labels() -> list[str]:
    result = _analysis()
    return [
        item["method"]
        for item in result["qualitative"]["mse_order_at_largest_B"]
    ]


def robustness_method_order_labels() -> list[str]:
    result = _robustness_analysis()
    return [
        item["method"]
        for item in result["qualitative"]["mse_order_at_largest_B"]
    ]


def g8_method_order_labels() -> list[str]:
    result = _g8_analysis()
    return [
        item["method"]
        for item in result["qualitative"]["mse_order_at_largest_B"]
    ]
