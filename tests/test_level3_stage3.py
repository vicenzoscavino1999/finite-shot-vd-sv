from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PATH = REPO_ROOT / "level3" / "archive" / "stage3_g6_k2_c000_ibm_marrakesh_full_analysis.json"
REPORT_PATH = REPO_ROOT / "level3" / "level3_full_p7p9_report.md"


def _analysis():
    with ANALYSIS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _row(method: str, b: int) -> dict:
    for row in _analysis()["rows"]:
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


def result_method_order_labels() -> list[str]:
    result = _analysis()
    return [
        item["method"]
        for item in result["qualitative"]["mse_order_at_largest_B"]
    ]

