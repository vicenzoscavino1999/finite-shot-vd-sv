import csv
from pathlib import Path

from level2 import sampling


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_sampling_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_sampling_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _row(method, b):
    for row in _rows():
        if row["method"] == method and int(row["B"]) == int(b):
            return row
    raise KeyError((method, b))


def test_level2_sampling_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == 3 * len(sampling.B_VALUES)
    assert {row["method"] for row in rows} == {
        "unmitigated",
        "sv_mitigated",
        "sv_raw_postselect_diagnostic",
    }
    assert {int(row["mixer_trotter_steps"]) for row in rows} == {1}


def test_level2_sampling_small_run_is_deterministic():
    cfg = sampling.SamplingConfig(
        b_values=(64,),
        repetitions=2,
        calibration_shots=512,
        acceptance_reference_shots=512,
        base_seed=12345,
    )
    rows_a, _report_a = sampling.run_sampling(cfg, started_at=0.0)
    rows_b, _report_b = sampling.run_sampling(cfg, started_at=0.0)
    scrubbed_a = [{**row, "runtime_seconds": 0.0} for row in rows_a]
    scrubbed_b = [{**row, "runtime_seconds": 0.0} for row in rows_b]
    assert scrubbed_a == scrubbed_b


def test_level2_readout_calibration_matches_configured_matrix():
    for row in _rows():
        assert float(row["calibration_max_abs_error"]) <= sampling.CALIBRATION_ABS_TOL


def test_level2_sv_mitigated_reduces_bias_against_unmitigated():
    largest_b = max(sampling.B_VALUES)
    sv = abs(float(_row("sv_mitigated", largest_b)["bias_empirical"]))
    unmit = abs(float(_row("unmitigated", largest_b)["bias_empirical"]))
    assert sv < unmit


def test_level2_variance_decreases_with_resource_shots():
    for method in ("unmitigated", "sv_mitigated"):
        variances = [
            float(_row(method, b)["variance_empirical"])
            for b in sampling.B_VALUES
        ]
        assert variances[0] > variances[-1]
        assert float(_row(method, max(sampling.B_VALUES))["variance_slope_fit"]) > 0.0


def test_level2_resource_accounting_uses_all_shots_for_sv():
    for row in _rows():
        b = int(row["B"])
        assert int(row["resource_shots_per_rep"]) == b
        assert int(row["repetitions"]) == sampling.REPETITIONS
