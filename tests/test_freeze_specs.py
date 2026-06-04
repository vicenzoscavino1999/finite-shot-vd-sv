"""Pre-freeze specs must match the executable Level-1 model."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
import numpy as np
import yaml

from experiments._common import log_grid, p_grid
from experiments import e2_c_sv_zero
from ground_truth import compute_lambda2_gaps
from ground_truth import compute_frozen_model_specs as frozen_specs
from ground_truth.instance_ensemble import sector_weight_for_size
from vd_sv import noise

REPO_ROOT = Path(__file__).resolve().parents[1]


def _grids_config() -> dict:
    return yaml.safe_load((REPO_ROOT / "config" / "grids.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def generated_frozen_specs():
    config = _grids_config()
    return (*frozen_specs.generate_frozen_specs(config), config)


def test_declared_grids_match_executable_helpers():
    exps = _grids_config()["experiments"]

    np.testing.assert_allclose(
        exps["e1_quotient_decomposition"]["B_fast"], log_grid(200, 8000, 9), rtol=0, atol=0
    )
    np.testing.assert_allclose(
        exps["e1_quotient_decomposition"]["B_full"], log_grid(200, 30000, 12), rtol=0, atol=0
    )
    np.testing.assert_allclose(
        exps["e2_c_sv_zero"]["B_fast"], log_grid(500, 12000, 8), rtol=0, atol=0
    )
    np.testing.assert_allclose(
        exps["e2_c_sv_zero"]["B_full"], log_grid(500, 40000, 11), rtol=0, atol=0
    )
    np.testing.assert_allclose(
        exps["e2_c_sv_zero"]["p_grid"], p_grid(0.12, 0.25, 3), rtol=0, atol=0
    )
    assert exps["e2_c_sv_zero"]["T_fast"] == e2_c_sv_zero.T_BY_MODE["fast"]
    assert exps["e2_c_sv_zero"]["T_full"] == e2_c_sv_zero.T_BY_MODE["full"]

    for name in ("e3_delta_vd_generator", "e4_delta_sv_firstorder"):
        np.testing.assert_allclose(exps[name]["p_grid_fast"], p_grid(0.01, 0.12, 8), rtol=0, atol=0)
        np.testing.assert_allclose(exps[name]["p_grid_full"], p_grid(0.01, 0.12, 14), rtol=0, atol=0)

    np.testing.assert_allclose(
        exps["e7_certified_crossing"]["R_fast"], log_grid(50, 8000, 12), rtol=0, atol=0
    )
    np.testing.assert_allclose(
        exps["e7_certified_crossing"]["R_full"], log_grid(50, 8000, 18), rtol=0, atol=0
    )


def test_declared_noise_channel_matches_default_model():
    spec = json.loads((REPO_ROOT / "config" / "noise_channel_spec.json").read_text(encoding="utf-8"))
    rule = spec["level1_channel_rule"]
    sizes = _grids_config()["instance_selection"]["sizes"]
    assert rule["seed"] == 1
    for n in sizes:
        channel_spec = spec["level1_channels_by_size"][str(n)]
        channel = noise.heterogeneous_ad_pd(int(n), seed=int(rule["seed"]))
        process_rates = {
            proc.name: np.asarray(rates, dtype=np.float64)
            for proc, rates in channel.processes
        }

        assert channel.n == channel_spec["n_qubits"]
        np.testing.assert_allclose(process_rates["AD"], channel_spec["c_ad"], rtol=0, atol=0)
        np.testing.assert_allclose(process_rates["PD"], channel_spec["c_pd"], rtol=0, atol=0)


def test_lambda2_gap_threshold_is_preregistered_and_nonvacuous():
    config = _grids_config()
    assert float(config["lambda2_gap"]["min_relative_gap"]) >= 0.1


def test_ensemble_has_target_included_per_size(generated_frozen_specs):
    instance_rows, _angle_rows, config = generated_frozen_specs
    selection = config["instance_selection"]
    target = int(selection["n_target_per_size"])
    included_by_size = Counter(
        int(row["size_n"])
        for row in instance_rows
        if row["selection_status"] == "included"
    )

    for n in selection["sizes"]:
        n = int(n)
        assert included_by_size[n] == target
        expected_k = sector_weight_for_size(n, selection["sector_weight_rule"])
        assert {
            int(row["sector_weight"])
            for row in instance_rows
            if int(row["size_n"]) == n
        } == {expected_k}


def test_frozen_instances_reconstruct_to_models(generated_frozen_specs):
    instance_rows, angle_rows, _config = generated_frozen_specs
    for row in instance_rows:
        if row["selection_status"] != "included":
            continue
        model = frozen_specs.reconstruct_model(row, angle_rows)
        assert model.inst.name == row["instance_id"]
        assert model.inst.n == int(row["size_n"])
        assert model.inst.weight == int(row["sector_weight"])
        assert abs(model.mu_star - float(row["mu_star"])) <= 1e-12
        assert abs(frozen_specs._noiseless_cost(model) - float(row["noiseless_cost"])) <= 1e-12


def test_entropy_threshold_bite_is_measured_or_documented(generated_frozen_specs):
    instance_rows, _angle_rows, config = generated_frozen_specs
    diagnostics = frozen_specs._diagnostics_markdown(config, instance_rows)
    i2_rejects = [row for row in instance_rows if row["failing_criterion"] == "I2"]
    if i2_rejects:
        assert "I2 threshold bites" in diagnostics
    else:
        assert "I2 threshold did not reject" in diagnostics


def test_lambda2_gap_rows_cover_included_ensemble(generated_frozen_specs):
    instance_rows, angle_rows, config = generated_frozen_specs
    rows = compute_lambda2_gaps.compute_rows(config, instance_rows, angle_rows)
    included = [row for row in instance_rows if row["selection_status"] == "included"]
    p_values = frozen_specs._declared_p_values(config)

    assert len(rows) == len(included) * len(p_values)
    assert {row["gap_status"] for row in rows} == {"PASS"}
    e6_instances = {row["instance_id"] for row in rows if row["e6_candidate"] == "yes"}
    assert len(e6_instances) == 1
    assert sum(row["e6_candidate"] == "yes" for row in rows) == len(p_values)


def test_selection_is_white_box():
    forbidden = [
        "from experiments",
        "import experiments",
        "sample_vd",
        "sample_sv",
        "sample_direct_mean",
        "from vd_sv.estimators",
        "mse(",
    ]
    for relative in [
        "ground_truth/instance_ensemble.py",
        "ground_truth/compute_frozen_model_specs.py",
    ]:
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
