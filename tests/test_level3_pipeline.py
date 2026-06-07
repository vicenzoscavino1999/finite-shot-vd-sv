from __future__ import annotations

from pathlib import Path

import pytest

from level3.analyze import analyze_archive
from level3.archive import read_archive
from level3.budget import BudgetExceeded, enforce_budget, estimate_budget
from level3.config import Stage1Config
from level3.submit import run_offline_pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ARCHIVE = REPO_ROOT / "level3" / "archive" / "example_offline_counts.json.gz"
FIXTURE_ANALYSIS = REPO_ROOT / "level3" / "archive" / "example_offline_analysis.json"


def test_level3_offline_fixture_is_archived_counts_only():
    assert FIXTURE_ARCHIVE.exists()
    assert FIXTURE_ANALYSIS.exists()

    payload = read_archive(FIXTURE_ARCHIVE)
    assert payload["submission"]["mode"] == "offline_aer_sampler_v2"
    assert payload["submission"]["sampler"] == "SamplerV2"
    assert payload["backend"]["name"] == "AerSyntheticThermalReadoutV1"
    assert payload["experiment"]["instance_id"] == "g6_k2_c000"
    assert payload["experiment"]["n"] == 6
    assert payload["experiment"]["sector_weight"] == 2
    assert len(payload["experiment"]["observable_values_level1_order"]) == 2**6
    assert payload["shots"]["shots_per_circuit"] == 4096
    assert payload["shots"]["total_shots"] == 3 * 4096
    assert [item["label"] for item in payload["circuits"]] == [
        "qaoa_z",
        "readout_calib_0",
        "readout_calib_1",
    ]
    assert all(item["shots"] == 4096 for item in payload["circuits"])


def test_level3_fixture_analysis_reports_sv_bias_reduction():
    result = analyze_archive(FIXTURE_ARCHIVE)
    assert result["analysis_inputs"]["source"] == "archived_counts_only"
    assert result["mu_ideal_noiseless_l2"] == pytest.approx(-0.243431939047, abs=1e-9)
    assert result["sv_reduces_abs_bias_vs_unmitigated"] is True
    assert (
        result["abs_bias"]["sv_readout_mitigated_weight_postselect"]
        < result["abs_bias"]["unmitigated"]
    )


def test_level3_offline_pipeline_is_deterministic(tmp_path):
    config = Stage1Config(
        shots_per_circuit=64,
        max_total_shots=3 * 64,
        archive_dir=tmp_path,
    )
    first_path, _ = run_offline_pipeline(
        config,
        archive_name="first.json.gz",
        created_at_utc="2026-06-07T00:00:00Z",
        confirm_near_cap=True,
    )
    second_path, _ = run_offline_pipeline(
        config,
        archive_name="second.json.gz",
        created_at_utc="2026-06-07T00:00:00Z",
        confirm_near_cap=True,
    )
    assert read_archive(first_path) == read_archive(second_path)

    first_analysis = analyze_archive(first_path)
    second_analysis = analyze_archive(second_path)
    first_analysis["archive_path"] = "<scrubbed>"
    second_analysis["archive_path"] = "<scrubbed>"
    assert first_analysis == second_analysis


def test_level3_budget_guard_rejects_over_cap():
    estimate = estimate_budget(
        circuit_depths=[157, 1, 2],
        shots_per_circuit=4096,
        max_total_shots=4096,
        near_cap_fraction=0.85,
    )
    with pytest.raises(BudgetExceeded, match="exceed"):
        enforce_budget(
            estimate,
            require_near_cap_confirmation=True,
            near_cap_confirmed=True,
        )


def test_level3_budget_guard_requires_near_cap_confirmation():
    estimate = estimate_budget(
        circuit_depths=[157, 1, 2],
        shots_per_circuit=128,
        max_total_shots=3 * 128,
        near_cap_fraction=0.85,
    )
    with pytest.raises(BudgetExceeded, match="confirm-near-cap"):
        enforce_budget(
            estimate,
            require_near_cap_confirmation=True,
            near_cap_confirmed=False,
        )
    enforce_budget(
        estimate,
        require_near_cap_confirmation=True,
        near_cap_confirmed=True,
    )
