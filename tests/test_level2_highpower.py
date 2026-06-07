import csv
import math
from pathlib import Path

from level2 import highpower


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_highpower_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_highpower_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
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
    assert {row["instance_id"] for row in rows} == set(highpower.INSTANCE_IDS)
    assert {row["method"] for row in rows} == set(highpower.METHODS)
    assert {int(row["mixer_trotter_steps"]) for row in rows} == {1}
    assert {int(row["repetitions"]) for row in rows} == {highpower.REPETITIONS}
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "validacion EN FORMA" in report
    assert "Analyses E5/E7/E8/E12 are deferred" in report


def test_level2_highpower_noiseless_vd_crosschecks_pass_for_all_instances():
    vd_rows = [row for row in _rows() if row["method"] == "vd_m2_hadamard_swap"]
    assert {row["instance_id"] for row in vd_rows} == set(highpower.INSTANCE_IDS)
    for row in vd_rows:
        assert abs(float(row["noiseless_D_hat"]) - 1.0) <= highpower.NOISELESS_D_TOL
        assert float(row["noiseless_mu_abs_error"]) <= highpower.NOISELESS_MU_TOL


def test_level2_highpower_b_grid_and_budget_flags_are_consistent():
    rows = _rows()
    saw_crossed = False
    saw_budget_limited = False
    for instance_id in highpower.INSTANCE_IDS:
        inst_rows = [row for row in rows if row["instance_id"] == instance_id]
        b_values = sorted({int(row["B"]) for row in inst_rows})
        assert len(b_values) >= 1
        b_max = max(b_values)
        for row in inst_rows:
            b_den = float(row["B_den_impl_estimate"])
            if math.isfinite(b_den) and b_den > 0:
                assert _bool_cell(row["grid_crosses_B_den"]) == (b_max >= b_den)
                assert _bool_cell(row["grid_reaches_10x_B_den"]) == (b_max >= 10.0 * b_den)
            assert int(row["B_max_instance"]) == b_max
        vd_rows = [row for row in inst_rows if row["method"] == "vd_m2_hadamard_swap"]
        assert vd_rows
        saw_crossed = saw_crossed or any(_bool_cell(row["grid_crosses_B_den"]) for row in vd_rows)
        saw_budget_limited = saw_budget_limited or any(
            row["sample_status"] == "budget_exceeded_not_sampled" for row in vd_rows
        )
    assert saw_crossed
    assert saw_budget_limited


def test_level2_highpower_resource_columns_and_direct_samples_present():
    rows = _rows()
    direct_rows = [row for row in rows if row["method"] in {"unmitigated", "sv_mitigated"}]
    assert direct_rows
    for row in rows:
        assert float(row["B_den_impl_estimate"]) > 0.0
        assert float(row["resource_R_paired_sample"]) > 0.0
        assert float(row["resource_R_two_qubit_gate_proxy"]) > 0.0
        assert float(row["kappa_paired_sample"]) > 0.0
        assert float(row["kappa_two_qubit_gate_proxy"]) > 0.0
    for row in direct_rows:
        assert row["sample_status"] == "sampled"
        assert math.isfinite(float(row["bias_empirical"]))
        assert math.isfinite(float(row["variance_empirical"]))
        assert math.isfinite(float(row["mse_empirical"]))


def test_level2_highpower_small_harness_is_deterministic(monkeypatch):
    fixed_meta = {
        "noiseless_D_hat": 1.0,
        "noiseless_N_hat": -0.25,
        "noiseless_mu_hat": -0.25,
        "noiseless_mu_abs_error": 0.0,
        "noisy_D_reference": 0.05,
        "denominator_clip_value": 0.025,
        "B_den_impl_estimate": 1000.0,
        "vd_circuit_qubits": 13.0,
        "cswap_cx_count": 42.0,
        "numerator_cx_count": 100.0,
        "denominator_cx_count": 100.0,
        "kappa_paired_sample_vd": 1.0,
        "kappa_two_qubit_gate_proxy_vd": 14.0,
    }

    monkeypatch.setattr(highpower, "vd_metadata_for_instance", lambda model, cfg, mu: fixed_meta)
    cfg = highpower.HighPowerConfig(
        instance_ids=("g6_k2_c000",),
        repetitions=2,
        b_min=64,
        b_max_cap=64,
        base_seed=909,
        vd_trajectory_shot_cap_per_circuit=1,
        sv_acceptance_reference_shots=32,
    )
    rows_a, _report_a = highpower.run_highpower(cfg, started_at=0.0)
    rows_b, _report_b = highpower.run_highpower(cfg, started_at=0.0)
    assert _normalize_for_compare(rows_a) == _normalize_for_compare(rows_b)
    assert any(row["sample_status"] == "budget_exceeded_not_sampled" for row in rows_a)
    assert any(not bool(row["grid_crosses_B_den"]) for row in rows_a)
