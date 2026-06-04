"""Power pilot must stay pre-freeze and anti-circular."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot import run_power_pilot

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pilot_rows_without_kurtosis():
    config = run_power_pilot.load_config()
    rows, summary = run_power_pilot.compute_pilot_rows(config, simulate_kurtosis=False)
    return config, rows, summary


def test_pilot_report_rows_cover_frozen_ensemble_without_kurtosis_sampling(
    pilot_rows_without_kurtosis,
):
    config, rows, summary = pilot_rows_without_kurtosis

    assert len(rows) == 10
    assert summary["instances"] == 10
    assert summary["tau_value"] > 0.0
    assert summary["tau_delta_value"] > 0.0
    assert summary["delta_abs_floor"] >= float(config["pilot_power"]["delta_abs_floor_min"])
    assert summary["delta_consistency_abs_tol"] == float(
        config["pilot_power"]["delta_consistency_abs_tol"]
    )

    required = {
        "delta_halfwidth_vd",
        "delta_halfwidth_sv",
        "delta_consistency_abs_tol",
        "delta_vd_consistency_status",
        "delta_sv_consistency_status",
        "power_c_vd",
        "power_tost_c_sv",
        "kurtosis_near_bden",
        "estimated_shots",
        "estimated_walltime",
        "tau_value",
        "tau_delta_value",
        "delta_abs_floor",
    }
    for row in rows:
        assert required <= set(row)
        assert row["anti_circularity_basis"].endswith("no_confirmatory_results_read")
        assert row["tau_delta_role"] == "precision_only_not_p5_p6_pass_criterion"


def test_delta_consistency_is_not_self_fulfilling(pilot_rows_without_kurtosis):
    config, rows, summary = pilot_rows_without_kurtosis
    safety = float(config["pilot_power"]["precision_safety_factor"])
    max_precision_halfwidth = max(
        max(float(row["delta_halfwidth_vd"]), float(row["delta_halfwidth_sv"]))
        for row in rows
    )

    assert abs(summary["tau_delta_value"] - safety * max_precision_halfwidth) <= 1e-15
    assert any(float(row["delta_vd_fit_abs_error"]) > float(row["delta_halfwidth_vd"]) for row in rows)
    assert any(float(row["delta_sv_fit_abs_error"]) > float(row["delta_halfwidth_sv"]) for row in rows)
    for row in rows:
        assert float(row["delta_halfwidth_vd"]) == float(row["delta_regression_halfwidth_vd"])
        assert float(row["delta_halfwidth_sv"]) == float(row["delta_regression_halfwidth_sv"])
        assert row["delta_vd_consistency_status"] == "PASS"
        assert row["delta_sv_consistency_status"] == "PASS"


def test_delta_near_zero_policy_is_preregistered_for_known_near_zero_instances(
    pilot_rows_without_kurtosis,
):
    _config, rows, _summary = pilot_rows_without_kurtosis

    near_zero = {
        row["instance_id"]
        for row in rows
        if str(row["delta_vd_rule_status"]).startswith("INCONCLUSIVE")
        or str(row["delta_sv_rule_status"]).startswith("INCONCLUSIVE")
    }
    assert {"g8_k3_c001", "g8_k3_c002", "g8_k3_c003"} <= near_zero


def test_pilot_source_does_not_read_confirmatory_outputs():
    source = (REPO_ROOT / "pilot" / "run_power_pilot.py").read_text(encoding="utf-8")

    forbidden = [
        "results/e1_",
        "results/e2_",
        "results/e3_",
        "results/e4_",
        "results/e5_",
        "results/e7_",
        "reproducibility/reference/e",
    ]
    for token in forbidden:
        assert token not in source
