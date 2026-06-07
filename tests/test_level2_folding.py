import csv
from pathlib import Path

from level2 import folding


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_folding_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_folding_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_level2_folding_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == len(folding.NOISE_SCALES)
    assert {row["method"] for row in rows} == {"unmitigated_density_matrix_population"}
    assert {int(row["mixer_trotter_steps"]) for row in rows} == {1}
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "foundation de amplificacion de ruido para E8" in report
    assert "VD c-SWAP/interferometry is not folded here" in report


def test_level2_folding_noiseless_invariance():
    for row in _rows():
        assert float(row["noiseless_abs_error"]) <= folding.NOISELESS_INVARIANCE_TOL


def test_level2_folding_noisy_bias_is_monotone():
    rows = _rows()
    assert folding.abs_bias_is_monotone(rows)
    abs_bias = [float(row["abs_bias_population"]) for row in rows]
    assert abs_bias[-1] > abs_bias[0]


def test_level2_folding_cx_count_grows_with_lambda():
    rows = _rows()
    assert folding.cx_count_is_monotone(rows)
    cx_counts = [int(row["cx_count"]) for row in rows]
    assert cx_counts == sorted(cx_counts)
    assert cx_counts[-1] > cx_counts[0]


def test_level2_folding_small_run_is_deterministic():
    cfg = folding.FoldingConfig(noise_scales=(1, 3), base_seed=777)
    rows_a, _report_a = folding.run_folding(cfg, started_at=0.0)
    rows_b, _report_b = folding.run_folding(cfg, started_at=0.0)
    scrubbed_a = [{**row, "runtime_seconds": 0.0} for row in rows_a]
    scrubbed_b = [{**row, "runtime_seconds": 0.0} for row in rows_b]
    assert scrubbed_a == scrubbed_b
