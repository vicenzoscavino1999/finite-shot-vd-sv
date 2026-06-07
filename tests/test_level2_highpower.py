import csv
import math
from pathlib import Path

from level2 import highpower


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_highpower_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_highpower_report.md"
STEP2_CSV_PATH = REPO_ROOT / "level2" / "level2_sampling_results.csv"


def _rows(path=CSV_PATH):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _bool_cell(value: str) -> bool:
    return value.lower() == "true"


def _normalize_for_compare(rows):
    normalized = []
    for row in rows:
        clean = {**row, "runtime_seconds": 0.0}
        for key, value in list(clean.items()):
            if isinstance(value, float) and math.isnan(value):
                clean[key] = "nan"
        normalized.append(clean)
    return normalized


def test_level2_highpower_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == len(highpower.INSTANCE_IDS) * len(highpower.METHODS) * len(highpower.B_GRID_FACTORS)
    assert {row["instance_id"] for row in rows} == set(highpower.INSTANCE_IDS)
    assert {row["method"] for row in rows} == set(highpower.METHODS)
    assert {row["sample_status"] for row in rows} == {"sampled"}
    assert {int(row["mixer_trotter_steps"]) for row in rows} == {1}
    assert {int(row["repetitions"]) for row in rows} == {highpower.REPETITIONS}
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "validacion EN FORMA" in report
    assert "exact-rho Option A" in report
    assert "operating-window dependent" in report
    assert "conservative direction" not in report
    assert "Analyses E5/E7/E8/E12 are deferred" in report


def test_level2_highpower_noiseless_vd_crosschecks_pass_for_all_instances():
    vd_rows = [row for row in _rows() if row["method"] == "vd_m2_hadamard_binomial"]
    assert {row["instance_id"] for row in vd_rows} == set(highpower.INSTANCE_IDS)
    for row in vd_rows:
        assert abs(float(row["noiseless_D_hat"]) - 1.0) <= highpower.NOISELESS_D_TOL
        assert float(row["noiseless_mu_abs_error"]) <= highpower.NOISELESS_MU_TOL


def test_level2_highpower_vd_is_sampled_and_grid_reaches_10x_bden():
    rows = _rows()
    for instance_id in highpower.INSTANCE_IDS:
        vd_rows = [
            row for row in rows
            if row["instance_id"] == instance_id and row["method"] == "vd_m2_hadamard_binomial"
        ]
        assert len(vd_rows) == len(highpower.B_GRID_FACTORS)
        assert {row["sample_status"] for row in vd_rows} == {"sampled"}
        b_values = sorted(int(row["B"]) for row in vd_rows)
        b_max = max(b_values)
        b_over = [float(row["B_over_B_den"]) for row in vd_rows]
        assert min(b_over) < 1.0
        assert max(b_over) >= 10.0
        for row in vd_rows:
            b_den = float(row["B_den_impl_estimate"])
            assert b_den > 0.0
            assert int(row["B_max_instance"]) == b_max
            assert _bool_cell(row["grid_crosses_B_den"])
            assert _bool_cell(row["grid_reaches_10x_B_den"])
            assert b_max >= 10.0 * b_den


def test_level2_highpower_resource_bden_and_model_columns_are_present():
    rows = _rows()
    for row in rows:
        assert float(row["B_den_impl_estimate"]) > 0.0
        assert float(row["D_2_exact"]) > 0.0
        assert float(row["resource_R_paired_sample"]) > 0.0
        assert float(row["resource_R_two_qubit_gate_proxy"]) > 0.0
        assert float(row["kappa_paired_sample"]) > 0.0
        assert float(row["kappa_two_qubit_gate_proxy"]) > 0.0
        assert math.isfinite(float(row["bias_empirical"]))
        assert math.isfinite(float(row["variance_empirical"]))
        assert math.isfinite(float(row["mse_empirical"]))
        if row["method"] == "vd_m2_hadamard_binomial":
            assert row["estimator_model"] == highpower.VD_MODEL
            assert math.isfinite(float(row["mean_N_hat"]))
            assert math.isfinite(float(row["mean_D_hat"]))
            assert math.isfinite(float(row["mean_D_clipped"]))
        else:
            assert row["estimator_model"] == highpower.UNMIT_SV_MODEL


def test_level2_highpower_unmitigated_matches_step2_trajectory_context():
    step_rows = [row for row in _rows(STEP2_CSV_PATH) if row["method"] == "unmitigated"]
    step_b = max(int(row["B"]) for row in step_rows)
    step_row = next(row for row in step_rows if int(row["B"]) == step_b)
    high_rows = [
        row for row in _rows()
        if row["instance_id"] == "g6_k2_c000" and row["method"] == "unmitigated"
    ]
    nearest = min(high_rows, key=lambda row: abs(int(row["B"]) - step_b))
    assert abs(float(nearest["population_mean"]) - float(step_row["mean_estimate"])) < 0.03
    assert abs(float(nearest["mean_estimate"]) - float(step_row["mean_estimate"])) < 0.03


def test_level2_highpower_small_harness_is_deterministic():
    cfg = highpower.HighPowerConfig(
        instance_ids=("g6_k2_c000",),
        repetitions=4,
        b_min=64,
        absolute_b_ceiling=100_000,
        base_seed=909,
    )
    rows_a, _report_a = highpower.run_highpower(cfg, started_at=0.0)
    rows_b, _report_b = highpower.run_highpower(cfg, started_at=0.0)
    assert _normalize_for_compare(rows_a) == _normalize_for_compare(rows_b)
    assert {row["sample_status"] for row in rows_a} == {"sampled"}
    assert any(row["method"] == "vd_m2_hadamard_binomial" for row in rows_a)
