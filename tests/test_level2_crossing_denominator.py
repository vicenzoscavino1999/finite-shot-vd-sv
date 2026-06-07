import csv
import math
from pathlib import Path

from level2 import crossing_denominator as analysis


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_crossing_denominator_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_crossing_denominator_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _normalize(rows):
    return [{**row, "runtime_seconds": 0.0} for row in rows]


def test_level2_crossing_denominator_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert {row["row_kind"] for row in rows} == {"denominator", "curve", "crossing"}
    assert len([row for row in rows if row["row_kind"] == "denominator"]) == 70
    assert len([row for row in rows if row["row_kind"] == "curve"]) == 560
    assert len([row for row in rows if row["row_kind"] == "crossing"]) == 70
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "EN FORMA" in report
    assert "not a Level 1 formal certificate" in report
    assert "SV dominates the realistic VD device circuit" in report


def test_level2_e5_denominator_drop_occurs_around_bden():
    denom = [row for row in _rows() if row["row_kind"] == "denominator"]
    for instance_id in sorted({row["instance_id"] for row in denom}):
        inst = sorted(
            [row for row in denom if row["instance_id"] == instance_id],
            key=lambda row: float(row["B_over_B_den"]),
        )
        probs = [float(row["bad_denominator_prob_exact"]) for row in inst]
        ratios = [float(row["B_over_B_den"]) for row in inst]
        assert ratios[0] < 0.2
        assert ratios[-1] >= 10.0
        assert probs[0] > probs[2] > probs[3] > probs[-1]
        assert probs[3] < 1.0e-3
        assert probs[-1] < 1.0e-20
        for row in inst:
            assert float(row["bernstein_bound"]) >= float(row["bad_denominator_prob_exact"])


def test_level2_e7_curves_are_resource_laws_with_positive_resources():
    curves = [row for row in _rows() if row["row_kind"] == "curve"]
    assert {row["resource_definition"] for row in curves} == {"paired_sample", "two_qubit_gate_proxy"}
    for row in curves:
        assert float(row["B"]) > 0.0
        assert float(row["R"]) > 0.0
        assert float(row["mse_law"]) >= 0.0
        assert float(row["mse_empirical"]) >= 0.0
        assert math.isfinite(float(row["bias_floor"]))
        assert math.isfinite(float(row["sampling_s"]))


def test_level2_e7_vd_realistic_does_not_cross_below_sv_in_n6():
    crossings = [
        row for row in _rows()
        if row["row_kind"] == "crossing"
        and row["method_pair"] == "vd_selected_vs_sv"
        and row["resource_definition"] == "two_qubit_gate_proxy"
        and int(row["n_qubits"]) == 6
    ]
    assert len(crossings) == 5
    assert {row["vd_variant"] for row in crossings} == {"vd_realistic_interference_n6"}
    assert all(row["regime"] == "uniform_sv_mitigated" for row in crossings)
    assert all(row["winner_high_R"] == "sv_mitigated" for row in crossings)


def test_level2_e7_sv_large_resource_winner_against_unmitigated():
    crossings = [
        row for row in _rows()
        if row["row_kind"] == "crossing"
        and row["method_pair"] == "sv_vs_unmit"
        and row["resource_definition"] == "paired_sample"
    ]
    assert len(crossings) == 10
    assert all(row["winner_high_R"] == "sv_mitigated" for row in crossings)


def test_level2_crossing_denominator_analysis_is_deterministic():
    rows_a, _report_a = analysis.run_analysis(started_at=0.0)
    rows_b, _report_b = analysis.run_analysis(started_at=0.0)
    assert _normalize(rows_a) == _normalize(rows_b)
